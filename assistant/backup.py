"""주간 백업: 봇 데이터를 zip으로 묶어 구글 드라이브 'ai-assistant-backup' 폴더에 올린다 (최근 N개 유지).

포함: assistant.db(대화·리마인더·서재 쪽 텍스트·사용 기록·쿠폰 목록), memory.md, 기프티콘 이미지 (지출·메모는 Notion에 있음)
제외: 비밀값(.env, 토큰 파일들), 서재 PDF 원본(다시 올리면 됨)
권한: 구글 토큰에 drive.file (봇이 만든 파일에만 접근) — deploy/google_auth.py 다시 실행으로 추가
복구: deploy/restore.py
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

FOLDER = "ai-assistant-backup"
DRIVE_FILE = "https://www.googleapis.com/auth/drive.file"
EXCLUDE = {"google_token.json", "google_youtube_token.json", "ms_token.json", "kakao.json", "client_secret.json"}


def data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data"))


def build_zip(dest: Path, data: Path | None = None) -> tuple[Path, list[str]]:
    """data 폴더에서 백업할 것만 zip으로. DB는 sqlite 백업 API로 일관된 사본을 만든다."""
    data = data or data_dir()
    names = []
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        db = data / "assistant.db"
        if db.exists():
            snap = Path(tmp) / "assistant.db"
            src, dst = sqlite3.connect(db), sqlite3.connect(snap)
            with dst:
                src.backup(dst)
            src.close()
            dst.close()
            z.write(snap, "assistant.db")
            names.append("assistant.db")
        for rel in ["memory.md"]:
            if (data / rel).exists():
                z.write(data / rel, rel)
                names.append(rel)
        for sub in ["coupons"]:
            for f in sorted((data / sub).glob("*")) if (data / sub).exists() else []:
                if f.is_file() and f.name not in EXCLUDE:
                    z.write(f, f"{sub}/{f.name}")
                    names.append(f"{sub}/{f.name}")
        z.writestr("BACKUP_INFO.txt", f"created {datetime.now().isoformat(timespec='seconds')}\nfiles {len(names)}\n"
                                      "비밀값·토큰·서재 PDF는 들어 있지 않아요. 복구: deploy/restore.py\n")
    return dest, names


def _drive():
    from .tools import google
    if not google.TOKEN.exists():
        raise RuntimeError("구글 토큰이 없어요 (deploy/google_auth.py)")
    if not google.has_scope(DRIVE_FILE):
        raise RuntimeError("구글 토큰에 드라이브 쓰기(drive.file) 권한이 없어요 → SSH 터널로 deploy/google_auth.py 다시 실행")
    return google._service("drive", "v3")


def folder_id(svc) -> str:
    q = f"name='{FOLDER}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    hit = svc.files().list(q=q, fields="files(id)", pageSize=1).execute().get("files", [])
    if hit:
        return hit[0]["id"]
    return svc.files().create(body={"name": FOLDER, "mimeType": "application/vnd.google-apps.folder"},
                              fields="id").execute()["id"]


def run(keep: int = 8) -> str:
    """동기 함수 (봇에서는 to_thread로). 결과 한 줄을 돌려준다."""
    from googleapiclient.http import MediaFileUpload

    svc = _drive()
    fid = folder_id(svc)
    name = f"ai-assistant-{datetime.now():%Y%m%d-%H%M}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        path, files = build_zip(Path(tmp) / name)
        size = path.stat().st_size
        svc.files().create(body={"name": name, "parents": [fid]},
                           media_body=MediaFileUpload(str(path), mimetype="application/zip", resumable=True),
                           fields="id").execute()
    olds = svc.files().list(q=f"'{fid}' in parents and trashed=false", orderBy="createdTime desc",
                            fields="files(id,name)", pageSize=100).execute().get("files", [])
    for f in olds[keep:]:
        svc.files().delete(fileId=f["id"]).execute()
    return f"💾 백업 완료: {name} ({size / 1e6:.1f}MB, 파일 {len(files)}개, 최근 {keep}개 유지)"


def download_latest(dest: Path) -> Path:
    from googleapiclient.http import MediaIoBaseDownload

    svc = _drive()
    fid = folder_id(svc)
    files = svc.files().list(q=f"'{fid}' in parents and trashed=false", orderBy="createdTime desc",
                             fields="files(id,name)", pageSize=1).execute().get("files", [])
    if not files:
        raise RuntimeError("드라이브에 백업이 없어요")
    out = dest / files[0]["name"]
    with open(out, "wb") as fh:
        dl = MediaIoBaseDownload(fh, svc.files().get_media(fileId=files[0]["id"]))
        done = False
        while not done:
            _, done = dl.next_chunk()
    return out


def restore(zip_path: Path, data: Path | None = None) -> list[str]:
    """zip을 data 폴더에 푼다. 덮어쓸 파일은 data/restore-backup-<시각>/ 으로 먼저 옮긴다."""
    data = data or data_dir()
    data.mkdir(parents=True, exist_ok=True)
    keep = data / f"restore-backup-{datetime.now():%Y%m%d-%H%M%S}"
    restored = []
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if n == "BACKUP_INFO.txt" or n.endswith("/") or ".." in Path(n).parts or Path(n).is_absolute():
                continue
            target = data / n
            if target.exists():
                (keep / n).parent.mkdir(parents=True, exist_ok=True)
                target.replace(keep / n)
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(n) as src, open(target, "wb") as dst:
                dst.write(src.read())
            restored.append(n)
    return restored
