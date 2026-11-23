"""구글 OAuth 토큰 발급 (일정 추가·드라이브 검색·캘린더 API 조회용, 한 번만).

준비 (PC 브라우저)
1. console.cloud.google.com → 새 프로젝트 → API 및 서비스 → 라이브러리에서 'Google Calendar API', 'Google Drive API' 사용
2. OAuth 동의 화면(Google 인증 플랫폼): 외부 → 앱 이름·이메일만 입력 → 대상(테스트 사용자)에 내 Gmail 추가
   → 그다음 '앱 게시'(프로덕션)로 전환. 테스트 상태로 두면 토큰이 7일마다 만료됩니다.
   (본인만 쓰면 검수 없이 '확인되지 않은 앱' 경고만 뜨고 → 고급 → 계속 으로 진행 가능)
3. 클라이언트 → 클라이언트 만들기 → 유형 '데스크톱 앱' → JSON 다운로드
4. 그 JSON을 VM으로 복사:  scp client_secret_*.json ubuntu@VM주소:~/ai-assistant/data/client_secret.json

실행 (VM, SSH 터널 사용 — VM엔 브라우저가 없으므로 내 PC 브라우저로 로그인)
  내 PC에서:  ssh -L 8765:localhost:8765 ubuntu@VM주소
  그 SSH 안에서:  cd ~/ai-assistant && .venv/bin/python deploy/google_auth.py
  → 출력된 주소를 PC 브라우저로 열어 로그인·허용 → data/google_token.json 생성 → 봇 재시작
  유튜브(구독 새 영상)는 구글이 다른 권한과 함께 요청하지 못하게 해서 따로:  deploy/google_auth.py --youtube
  Docker로 설치했다면:  docker compose run --rm -p 127.0.0.1:8765:8765 -e OAUTH_BIND_ADDR=0.0.0.0 assistant python deploy/google_auth.py
"""
import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("DATA_DIR", ROOT / "data"))
YOUTUBE = "--youtube" in sys.argv   # 유튜브 권한은 다른 권한과 함께 요청할 수 없어서 따로 한 번 더 로그인한다
SCOPES = (["https://www.googleapis.com/auth/youtube.readonly"] if YOUTUBE else
          ["https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/drive.readonly",
           "https://www.googleapis.com/auth/drive.file",          # 백업·지출 시트 (봇이 만든 파일만)
           "https://www.googleapis.com/auth/contacts.readonly"])  # 주소록 생일
PORT = 8765

secret = next((p for p in (DATA / "client_secret.json", Path("client_secret.json")) if p.exists()), None)
if not secret:
    sys.exit(f"client_secret.json 이 없습니다. {DATA / 'client_secret.json'} 에 두세요.")

flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
print(f"\n아래 주소를 PC 브라우저로 여세요 (PC에서 ssh -L {PORT}:localhost:{PORT} 로 접속 중이어야 함).")
creds = flow.run_local_server(host="localhost", bind_addr=os.environ.get("OAUTH_BIND_ADDR") or None, port=PORT, open_browser=False, prompt="consent", access_type="offline",
                              authorization_prompt_message="{url}\n",
                              success_message="완료! 이 창을 닫고 터미널로 돌아가세요.")
out = DATA / ("google_youtube_token.json" if YOUTUBE else "google_token.json")
out.write_text(creds.to_json())
os.chmod(out, 0o600)
print(f"✅ {out} 생성. 이제: sudo systemctl restart ai-assistant")
if not YOUTUBE:
    print("   유튜브 새 영상 알림도 쓰려면 한 번 더:  .venv/bin/python deploy/google_auth.py --youtube")
