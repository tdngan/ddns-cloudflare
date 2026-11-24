# ============================================================
# Dockerfile: Cloudflare DDNS Auto Update (CRON LINH HOẠT!)
# Fixed version - solves /etc/crontabs directory issue!
# ============================================================
FROM python:3.11-slim

ENV TZ=Asia/Ho_Chi_Minh PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    cron \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && echo "Asia/Ho_Chi_Minh" > /etc/timezone \
    && ln -fs /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/

RUN mkdir -p /app/logs /app/data && chown -R $(id -u):$(id -g) /app

# ============================================================
# CRON JOB CONFIGURATION (Environment Variable - LINH HOẠT!)
# Format: minute hour day month weekday command  
# Default: */5 * * * * (mỗi 5 phút)
ENV CRON_EXPR="${CRON_EXPR:-'*/5 * * * *'}"

# ============================================================
# SETUP CRON JOB 
# FIXED: Create /etc/crontabs directory explicitly!
# ============================================================
RUN mkdir -p /etc/crontabs \
    && echo "${CRON_EXPR} /usr/bin/python3 /app/scripts/ddns_cloudflare.py >> /app/logs/ddns_cron.log 2>&1" > /etc/crontabs/ddns-cron.conf

# ============================================================
# CRON DAEMON STARTUP SCRIPT
# Ensures cron daemon starts when container boots
# ============================================================
COPY start_cron.sh /usr/local/bin/start_cron.sh
RUN chmod +x /usr/local/bin/start_cron.sh

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f https://api.ipify.org || exit 1

ENV TZ=Asia/Ho_Chi_Minh

# Entrypoint script: start cron daemon, then run main command
ENTRYPOINT ["/usr/local/bin/start_cron.sh"]
CMD ["python", "scripts/ddns_cloudflare.py"]