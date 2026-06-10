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

DOCKER_CMD="${DOCKER_CMD:-docker}"
if ! $DOCKER_CMD info >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1 && sudo -n docker info >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
  else
    echo "Docker daemon is not reachable. Start Docker or set DOCKER_CMD."
    exit 1
  fi
fi

if $DOCKER_CMD compose version >/dev/null 2>&1; then
  COMPOSE="$DOCKER_CMD compose -f compose.yaml"
elif command -v docker-compose >/dev/null 2>&1 && docker-compose -f compose.yaml ps >/dev/null 2>&1; then
  COMPOSE="docker-compose -f compose.yaml"
else
  COMPOSE=""
fi

if [ -n "$COMPOSE" ]; then
  $COMPOSE build
  $COMPOSE up -d
  $COMPOSE logs -f apartment-monitor
else
  mkdir -p data
  $DOCKER_CMD build -t apartment-monitor:latest .
  if $DOCKER_CMD container inspect apartment-monitor >/dev/null 2>&1; then
    $DOCKER_CMD rm -f apartment-monitor
  fi
  $DOCKER_CMD run -d \
    --restart unless-stopped \
    --name apartment-monitor \
    --env-file .env \
    -e CONFIG_PATH=/data/config.yaml \
    -v "$PWD/data:/data" \
    apartment-monitor:latest
  $DOCKER_CMD logs -f apartment-monitor
fi
