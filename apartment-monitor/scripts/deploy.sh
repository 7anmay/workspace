#!/usr/bin/env sh
set -eu

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Fill in SLACK_BOT_TOKEN and SLACK_APP_TOKEN, then rerun."
  exit 1
fi

if ! grep -q '^SLACK_BOT_TOKEN=xoxb-' .env || ! grep -q '^SLACK_APP_TOKEN=xapp-' .env; then
  echo "Fill in SLACK_BOT_TOKEN and SLACK_APP_TOKEN in .env before deploying."
  exit 1
fi

docker compose build
docker compose up -d
docker compose logs -f apartment-monitor
