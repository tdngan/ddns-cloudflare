#!/bin/bash
set -e

# 1. Read the schedule from env (default every 5 minutes); strip stray quotes
CRON_EXPR="${CRON_EXPR:-*/5 * * * *}"
CRON_EXPR="$(echo "$CRON_EXPR" | sed -e "s/^['\"]//" -e "s/['\"]$//")"

# 2. Save container env vars so cron jobs can load them (cron starts with an empty env)
declare -px > /app/container.env
chmod 600 /app/container.env

# 3. Create the crontab at runtime (Debian: /etc/cron.d, needs the user column, no dot in name)
cat > /etc/cron.d/ddns <<EOF
SHELL=/bin/bash
${CRON_EXPR} root . /app/container.env; cd /app && /usr/local/bin/python scripts/ddns_cloudflare.py >> /proc/1/fd/1 2>&1
EOF
chmod 0644 /etc/cron.d/ddns

echo "[start] Schedule: ${CRON_EXPR}"

# 4. Run once immediately so DNS is updated at startup
/usr/local/bin/python scripts/ddns_cloudflare.py || true

# 5. Run cron in the FOREGROUND as the main process, so the container stays alive
exec cron -f