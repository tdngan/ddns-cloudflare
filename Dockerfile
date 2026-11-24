FROM python:3.11-slim

ENV TZ=Asia/Ho_Chi_Minh PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/

RUN mkdir -p /app/logs /app/data && chown -R $(id -u):$(id -g) /app

# ============================================================
# CRON JOB CONFIGURATION (Environment Variable - LINH HOẠT!)
# Format: minute hour day month weekday command  
# Ví dụ phổ biến: */5 * * * * = mỗi 5 phút, 0 * * * * = mỗi giờ
ENV CRON_EXPR="${CRON_EXPR:-'*/5 * * * *'}"

RUN crontab <<EOF && chmod 644 /etc/crontabs/*
${CRON_EXPR} /usr/bin/python3 /app/scripts/ddns_cloudflare.py >> /app/logs/ddns_cron.log 2>&1
EOF

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f https://api.ipify.org || exit 1

ENV TZ=Asia/Ho_Chi_Minh
CMD ["python", "scripts/ddns_cloudflare.py"]