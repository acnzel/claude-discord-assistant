"""백업 복구 (VM에서).

    sudo systemctl stop ai-assistant
    cd ~/ai-assistant
    .venv/bin/python deploy/restore.py --latest          # 드라이브의 최신 백업을 받아 복구
    .venv/bin/python deploy/restore.py 받은파일.zip       # 직접 받은 zip으로 복구
    sudo systemctl start ai-assistant

덮어쓰는 파일은 data/restore-backup-<시각>/ 에 남겨 둬요.
비밀값(.env, 토큰)은 백업에 없으니 새 VM이면 .env 작성과 로그인(google_auth.py, ms_auth.py)을 먼저 하세요.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATA_DIR", str(ROOT / "data"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from assistant import backup  # noqa: E402


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    active = subprocess.run(["systemctl", "is-active", "ai-assistant"], capture_output=True, text=True).stdout.strip()
    if active == "active":
        sys.exit("봇이 실행 중이에요. 먼저: sudo systemctl stop ai-assistant")
    if sys.argv[1] == "--latest":
        tmp = Path(tempfile.mkdtemp())
        zip_path = backup.download_latest(tmp)
        print(f"받음: {zip_path.name}")
    else:
        zip_path = Path(sys.argv[1])
    files = backup.restore(zip_path)
    print(f"✅ 복구: {len(files)}개 파일 → {backup.data_dir()}")
    print("이제: sudo systemctl start ai-assistant")


if __name__ == "__main__":
    main()
