FROM python:3.11-slim

ENV TZ=Asia/Ho_Chi_Minh PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        cron tzdata procps \
    && rm -rf /var/lib/apt/lists/* \
    && ln -fs /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo "$TZ" > /etc/timezone

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY start_cron.sh /usr/local/bin/start_cron.sh
RUN chmod +x /usr/local/bin/start_cron.sh

# Healthcheck: only check that cron is alive (no external API calls)
HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD pgrep cron > /dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/start_cron.sh"]