"""Microsoft To Do 로그인 (VM에서 한 번 실행, 기기 코드 방식 — 브라우저가 없어도 됨).

    cd ~/ai-assistant && .venv/bin/python deploy/ms_auth.py

화면에 나온 주소를 폰/PC 브라우저로 열고 코드를 입력 → 삼성 리마인더와 연결한 그 Microsoft 계정으로 로그인 → 승인.
성공하면 data/ms_token.json 이 생기고, 이후 봇이 알아서 갱신합니다 (90일 넘게 안 쓰면 다시 로그인).
"""
import asyncio
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATA_DIR", str(ROOT / "data"))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from assistant import todo  # noqa: E402


def main():
    if not todo.client_id():
        sys.exit("MS_CLIENT_ID 가 .env 에 없습니다. Azure 앱 등록의 '애플리케이션(클라이언트) ID'를 넣으세요.")
    r = httpx.post(f"{todo.authority()}/devicecode", data={"client_id": todo.client_id(), "scope": todo.SCOPES}, timeout=20)
    if r.status_code != 200:
        sys.exit(f"기기 코드 요청 실패: {r.status_code} {r.text[:300]}\n"
                 "→ 앱 등록 '인증' 메뉴에서 '퍼블릭 클라이언트 흐름 허용'을 '예'로 했는지, 지원 계정 유형에 개인 계정이 포함됐는지 확인하세요.")
    d = r.json()
    print("\n1) 브라우저에서 열기:", d["verification_uri"])
    print("2) 코드 입력:       ", d["user_code"])
    print("3) 삼성 리마인더와 연결한 Microsoft 계정으로 로그인 → 승인\n기다리는 중...", flush=True)

    interval, deadline = int(d.get("interval", 5)), time.time() + int(d.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(interval)
        t = httpx.post(f"{todo.authority()}/token", timeout=20, data={
            "client_id": todo.client_id(), "device_code": d["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
        body = t.json()
        if t.status_code == 200:
            todo.save_token(body)
            break
        err = body.get("error")
        if err == "slow_down":
            interval += 5
        elif err != "authorization_pending":
            sys.exit(f"로그인 실패: {err} {body.get('error_description', '')[:300]}")
    else:
        sys.exit("시간 초과. 다시 실행하세요.")

    print(f"\n✅ 로그인 완료 → {todo.token_path()}")
    lists = asyncio.run(todo.lists())
    print("To Do 목록:")
    for l in lists:
        mark = " (기본)" if l.get("wellknownListName") == "defaultList" else ""
        print(f"  - {l['displayName']}{mark}")
    print("\n삼성 리마인더와 동기화한 목록이 기본 목록이 아니면 config.yaml 의 todo.list_name 에 그 이름을 넣으세요.")
    print("그다음: sudo systemctl restart ai-assistant")


if __name__ == "__main__":
    main()
