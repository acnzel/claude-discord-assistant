"""카카오 다시 로그인 (VM에서) — 톡캘린더 권한(talk_calendar)을 추가할 때 한 번.

먼저 카카오 개발자 콘솔 → 내 앱 → 카카오 로그인 → 동의항목 → '톡캘린더 및 일정 생성, 조회, 편집/삭제' 를 켜세요.
    cd ~/ai-assistant && .venv/bin/python deploy/kakao_auth.py
1) 출력된 주소를 폰/PC 브라우저로 열고 동의
2) 이동한 주소창(https://localhost/?code=…)의 주소 전체를 복사해 붙여넣기 (페이지는 안 열려도 정상)
3) data/kakao.json 에 새 토큰 저장 → sudo systemctl restart ai-assistant
"""
import json
import os
import sys
import urllib.parse
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
REDIRECT = os.environ.get("KAKAO_REDIRECT_URI", "https://localhost")
key, secret = os.environ.get("KAKAO_REST_API_KEY", ""), os.environ.get("KAKAO_CLIENT_SECRET", "")
if not key:
    sys.exit("KAKAO_REST_API_KEY 가 .env 에 없습니다.")
print("\n아래 주소를 브라우저에서 여세요:\nhttps://kauth.kakao.com/oauth/authorize?" + urllib.parse.urlencode(
    {"client_id": key, "redirect_uri": REDIRECT, "response_type": "code", "scope": "talk_message,talk_calendar"}) + "\n")
raw = input("이동한 주소 전체 또는 code 값: ").strip()
code = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query).get("code", [raw])[0]
data = {"grant_type": "authorization_code", "client_id": key, "redirect_uri": REDIRECT, "code": code}
if secret:
    data["client_secret"] = secret
r = httpx.post("https://kauth.kakao.com/oauth/token", data=data, timeout=20)
if r.status_code != 200:
    sys.exit(f"토큰 발급 실패 ({r.status_code}): {r.text[:300]}")
tok = r.json()
out = Path(os.environ.get("DATA_DIR", ROOT / "data")) / "kakao.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"refresh_token": tok["refresh_token"]}))
os.chmod(out, 0o600)
print(f"✅ 저장: {out}\n   허락된 권한: {tok.get('scope', '?')}\n   이제: sudo systemctl restart ai-assistant")
