"""스스로 개선하는 비서.

1주일치 턴 기록(도구 호출·오류·취소·반복 횟수·토큰, 사용자의 정정·!reset)을 모아
Sonnet이 프롬프트·도구 설명·설정에서 고칠 점을 찾고, 수정안을 자기 저장소에 PR로 올린다.
합치는 건 사용자가 한다 (자동 병합 없음). 고칠 수 있는 파일과 내용은 아래 규칙으로 제한한다.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import time
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml

from .claude_tools import acall_tool
from .tools import dev

log = logging.getLogger("improve")

ALLOWED = re.compile(r"^(assistant/agents\.py|config\.yaml|assistant/tools/[a-z_]+\.py)$")
FORBIDDEN = re.compile(r"environ|API_KEY|_TOKEN\b|SECRET|PASSWORD|subprocess|os\.system|eval\(|exec\(|__import__|\.env\b",
                       re.I)
CORRECTION = re.compile(r"^(아니|그게 아니|틀렸|잘못|다시 해|다시해|그거 말고|아닌데)")
MAX_EDITS = 12

REVIEW_TOOL = {
    "name": "submit_review",
    "description": "주간 분석 결과와 수정안을 제출한다.",
    "input_schema": {"type": "object", "properties": {
        "summary": {"type": "string", "description": "이번 주 요약 3~5줄 (한국어)"},
        "findings": {"type": "array", "items": {"type": "object", "properties": {
            "title": {"type": "string"}, "evidence": {"type": "string", "description": "근거가 된 패턴과 횟수 (사용자 대화 원문 인용 금지)"},
            "fix": {"type": "string"}}, "required": ["title", "evidence"]}},
        "edits": {"type": "array", "description": "정확한 문자열 치환. old는 현재 파일에 정확히 한 번 나와야 한다.",
                  "items": {"type": "object", "properties": {
                      "file": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"},
                      "reason": {"type": "string"}}, "required": ["file", "old", "new", "reason"]}},
    }, "required": ["summary", "findings", "edits"]},
}

PROMPT = """너는 이 디스코드 비서의 유지보수 담당이다. 지난 {days}일 동안의 사용 기록을 보고, 비서가 헤매거나 실패하거나
사용자가 정정·취소·초기화한 패턴을 찾아 **프롬프트·도구 설명·설정**을 고쳐라.

규칙
- 고칠 수 있는 파일: assistant/agents.py, config.yaml, assistant/tools/*.py — 단, 프롬프트 문자열, 도구 설명(description),
  설정값만 고친다. 로직·import·인증·비밀값 관련 코드는 절대 건드리지 않는다.
- 근거가 2회 이상 반복된 패턴에만 수정안을 낸다. 한 번뿐이면 findings에만 적는다.
- 비용: 결과가 같다면 더 싼 모델·더 적은 호출을 선호한다. 모델 이름은 이미 설정에 있는 것만 쓴다.
- old는 아래 파일 내용에서 그대로 복사한 연속된 문자열이어야 하고 파일에서 딱 한 번 나와야 한다. 들여쓰기까지 정확히.
- 사용자 대화 원문은 findings·reason에 인용하지 않는다 (PR에 공개됨). "날씨 질문 3회에서 ~" 처럼 요약한다.
- 기능이나 명령을 바꾸는 수정은 하지 않는다 (사용법 문서 docs/usage.md와 어긋나게 됨).
- 고칠 게 없으면 edits를 비운다. 억지로 만들지 않는다.

## 통계
{stats}

## 문제가 있었던 턴 (최대 25개)
{problems}

## 현재 파일
{files}
"""


# ───────────── 기록 정리 ─────────────
def note_user_message(store, channel_id: str, text: str) -> None:
    """새 메시지가 직전 답변에 대한 정정이면 직전 턴에 표시."""
    if CORRECTION.match(text.strip()):
        store.flag_last_trace(channel_id, "corrected", True)


def collect(store, days: int = 7) -> tuple[dict, list[dict]]:
    traces = store.traces_since(time.time() - days * 86400)
    tools, errs, cancels = Counter(), Counter(), Counter()
    for t in traces:
        for c in t.get("tools", []):
            tools[c["tool"]] += 1
            if c.get("err"):
                errs[c["tool"]] += 1
            if c.get("cancel"):
                cancels[c["tool"]] += 1
    usage = store.usage_since(time.time() - days * 86400)
    stats = {
        "turns": len(traces),
        "modes": dict(Counter(t.get("mode") for t in traces)),
        "avg_api_calls": round(sum(t.get("api_calls", 0) for t in traces) / max(len(traces), 1), 2),
        "avg_sec": round(sum(t.get("sec", 0) for t in traces) / max(len(traces), 1), 1),
        "tool_calls": dict(tools.most_common(30)), "tool_errors": dict(errs), "user_cancels": dict(cancels),
        "corrected_turns": sum(1 for t in traces if t.get("corrected")),
        "reset_after": sum(1 for t in traces if t.get("reset")),
        "hit_round_limit": sum(1 for t in traces if t.get("hit_limit")),
        "tokens_by_role": {f"{r[0]}|{r[1]}{'|batch' if r[2] else ''}": {"in": r[3], "cache_read": r[4], "out": r[6], "calls": r[7]}
                           for r in usage},
    }

    def bad(t):
        return (any(c.get("err") or c.get("cancel") for c in t.get("tools", [])) or t.get("corrected") or t.get("reset")
                or t.get("hit_limit") or t.get("api_calls", 0) >= 6)
    problems = [t for t in traces if bad(t)][-25:]
    return stats, problems


# ───────────── 수정안 검증 ─────────────
def validate_edits(edits: list[dict], files: dict[str, str]) -> tuple[dict[str, str], list[dict], list[str]]:
    """규칙에 맞는 수정만 적용한 새 파일 내용, 적용된 수정, 버린 이유."""
    new_files, applied, rejected = dict(files), [], []
    for e in edits[:MAX_EDITS]:
        f, old, new = e.get("file", ""), e.get("old", ""), e.get("new", "")
        if not ALLOWED.match(f) or f not in new_files:
            rejected.append(f"{f}: 허용되지 않은 파일")
            continue
        if not old or old == new or len(new) > 4000:
            rejected.append(f"{f}: 빈 수정이거나 너무 김")
            continue
        if FORBIDDEN.search(old) or FORBIDDEN.search(new):
            rejected.append(f"{f}: 인증·실행 관련 내용은 수정 불가")
            continue
        if new_files[f].count(old) != 1:
            rejected.append(f"{f}: 바꿀 문자열이 정확히 한 번 나오지 않음")
            continue
        cand = new_files[f].replace(old, new, 1)
        try:
            if f.endswith(".py"):
                compile(cand, f, "exec")
            else:
                yaml.safe_load(cand)
        except Exception as ex:
            rejected.append(f"{f}: 문법 오류 ({type(ex).__name__})")
            continue
        new_files[f] = cand
        applied.append(e)
    return {k: v for k, v in new_files.items() if v != files[k]}, applied, rejected


# ───────────── GitHub ─────────────
async def fetch_files(repo: str) -> dict[str, str]:
    paths = ["assistant/agents.py", "config.yaml"]
    listing = await dev.gh("GET", f"/repos/{repo}/contents/assistant/tools", params={"ref": "main"})
    paths += [x["path"] for x in listing if x["name"].endswith(".py") and x["name"] not in ("__init__.py", "base.py")]
    out = {}
    for p in paths:
        meta = await dev.gh("GET", f"/repos/{repo}/contents/{p}", params={"ref": "main"})
        out[p] = base64.b64decode(meta["content"]).decode("utf-8")
    return out


async def open_pr(repo: str, changed: dict[str, str], title: str, body: str, branch: str) -> str:
    main = await dev.gh("GET", f"/repos/{repo}/git/ref/heads/main")
    await dev.gh("POST", f"/repos/{repo}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": main["object"]["sha"]})
    for path, text in changed.items():
        meta = await dev.gh("GET", f"/repos/{repo}/contents/{path}", params={"ref": branch})
        await dev.gh("PUT", f"/repos/{repo}/contents/{path}", json={
            "message": f"자기 개선: {path}", "branch": branch, "sha": meta["sha"],
            "content": base64.b64encode(text.encode("utf-8")).decode()})
    pr = await dev.gh("POST", f"/repos/{repo}/pulls", json={"title": title, "head": branch, "base": "main", "body": body})
    return pr["html_url"]


# ───────────── 실행 ─────────────
async def run(client, store, cfg: dict, days: int = 7) -> str:
    sc = cfg.get("self_improve") or {}
    repo = sc.get("repo", "Ashegyu/claude-discord-assistant")
    stats, problems = collect(store, days)
    if stats["turns"] < sc.get("min_turns", 10):
        return f"🔧 자기 개선: 지난 {days}일 대화가 {stats['turns']}턴뿐이라 분석을 건너뛰어요."
    files = await fetch_files(repo)
    prompt = PROMPT.format(
        days=days, stats=json.dumps(stats, ensure_ascii=False, indent=1),
        problems=json.dumps(problems, ensure_ascii=False, indent=1)[:40000],
        files="\n\n".join(f"### {p}\n```\n{t}\n```" for p, t in files.items()))
    review = await acall_tool(client, store, sc.get("model", cfg["models"]["deep"]), prompt, REVIEW_TOOL,
                              role="self_improve", max_tokens=16000)
    changed, applied, rejected = validate_edits(review.get("edits", []), files)

    tz = ZoneInfo(cfg["timezone"])
    lines = [f"🔧 **주간 자기 개선** ({stats['turns']}턴 분석)", review.get("summary", "")]
    for f in review.get("findings", [])[:6]:
        lines.append(f"- **{f.get('title')}** — {f.get('evidence', '')[:200]}")
    if not changed:
        lines.append("수정안 없음." + (f" (버린 수정 {len(rejected)}개: {'; '.join(rejected[:3])})" if rejected else ""))
        return "\n".join(lines)[:1900]
    body = "\n".join([
        "## 요약", review.get("summary", ""), "", "## 발견",
        *[f"- **{f.get('title')}** — {f.get('evidence', '')} → {f.get('fix', '')}" for f in review.get("findings", [])],
        "", "## 수정", *[f"- `{e['file']}`: {e['reason']}" for e in applied],
        *(["", "## 적용하지 않은 수정", *[f"- {r}" for r in rejected]] if rejected else []),
        "", "합치면 디스코드에서 `!update`로 반영돼요. 자동 병합되지 않아요.",
        "", "🤖 ai-assistant 자기 개선 (주간)"])
    branch = f"self-improve/{datetime.now(tz):%Y%m%d-%H%M}"
    url = await open_pr(repo, changed, f"자기 개선 {datetime.now(tz):%m/%d}: 수정 {len(applied)}건", body, branch)
    lines.append(f"📬 PR: {url}\n테스트가 통과하면 합치고 `!update` 하세요.")
    return "\n".join(lines)[:1900]
