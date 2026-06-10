#!/usr/bin/env sh
set -eu

CONFIG_PATH="${CONFIG_PATH:-/data/config.yaml}"

mkdir -p "$(dirname "$CONFIG_PATH")"

if [ ! -f "$CONFIG_PATH" ]; then
  cp /app/config.example.yaml "$CONFIG_PATH"
  echo "Initialized $CONFIG_PATH from config.example.yaml"
fi

exec "$@"
