#!/usr/bin/env sh
set -eu

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Fill in SLACK_BOT_TOKEN and SLACK_APP_TOKEN, then rerun."
  exit 1
fi

if grep -q 'your-bot-token\|your-app-token' .env \
  || ! grep -q '^SLACK_BOT_TOKEN=xoxb-' .env \
  || ! grep -q '^SLACK_APP_TOKEN=xapp-' .env; then
  echo "Fill in SLACK_BOT_TOKEN and SLACK_APP_TOKEN in .env before deploying."
  exit 1
fi

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[browser]'
python -m playwright install chromium

set -a
. ./.env
set +a

CONFIG_PATH="${CONFIG_PATH:-$PWD/data/config.yaml}"
if [ "$CONFIG_PATH" = "/data/config.yaml" ]; then
  CONFIG_PATH="$PWD/data/config.yaml"
fi

mkdir -p "$(dirname "$CONFIG_PATH")"
python -m apartment_monitor.cli --config "$CONFIG_PATH" init

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required for background venv deployment. Run manually:"
  echo ". .venv/bin/activate && apartment-monitor --config \"$CONFIG_PATH\" serve"
  exit 1
fi

tmux has-session -t apartment-monitor 2>/dev/null && tmux kill-session -t apartment-monitor
tmux new-session -d -s apartment-monitor "cd '$PWD' && set -a && . ./.env && set +a && . .venv/bin/activate && apartment-monitor --config '$CONFIG_PATH' serve"
echo "Apartment Monitor is running in tmux session apartment-monitor."
echo "Attach with: tmux attach -t apartment-monitor"
