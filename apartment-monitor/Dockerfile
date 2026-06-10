FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CONFIG_PATH=/data/config.yaml

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir ".[browser]" \
    && python -m playwright install --with-deps chromium

COPY config.example.yaml ./config.example.yaml
COPY scripts/docker-entrypoint.sh /usr/local/bin/apartment-monitor-entrypoint
RUN chmod +x /usr/local/bin/apartment-monitor-entrypoint

VOLUME ["/data"]

ENTRYPOINT ["apartment-monitor-entrypoint"]
CMD ["apartment-monitor", "--config", "/data/config.yaml", "serve"]
