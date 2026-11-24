#!/bin/sh

# ============================================================
# Start Cron Daemon Script
# This ensures cron service starts when container boots
# ============================================================

echo "Starting Cloudflare DDNS cron daemon..."

# Check if cron is running, if not start it
if ! pgrep -x "cron" > /dev/null 2>&1; then
    echo "Cron daemon not running. Starting now..."
    /usr/sbin/cron -f
fi

# Wait for cron to be ready (up to 5 seconds)
for i in {1..10}; do
    if pgrep -x "cron" > /dev/null 2>&1; then
        echo "Cron daemon started successfully!"
        break
    fi
    sleep 0.5
done

# Check if cron is still not running after wait
if ! pgrep -x "cron" > /dev/null 2>&1; then
    echo "ERROR: Failed to start cron daemon after multiple attempts." >&2
    exit 1
fi

echo "Cron daemon is ready!"
exec "$@"
