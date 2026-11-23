#!/usr/bin/env bash
# Ubuntu VM(예: Oracle Cloud 무료 Ampere)에서 한 번 실행: bash deploy/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip tzdata
sudo timedatectl set-timezone Asia/Seoul || true
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo "→ .env를 채운 뒤 다시 실행하세요: nano .env"; exit 0; }
mkdir -p data
sed "s#__DIR__#$(pwd)#g; s#__USER__#$(whoami)#g" deploy/assistant.service | sudo tee /etc/systemd/system/ai-assistant.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now ai-assistant
echo "✅ 실행 중. 로그: journalctl -u ai-assistant -f"
