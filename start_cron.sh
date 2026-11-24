#!/bin/sh

# ============================================================
# Start Cron Daemon Script
# Ensures cron service starts when container boots
# ============================================================

echo "Starting Cloudflare DDNS cron daemon..."

# Check if cron is running using ps command (more reliable than pgrep in minimal images)
if ! ps aux | grep -v grep | grep -q "[c]ron"; then
    echo "Cron daemon not running. Starting now..."
    
    # Start cron as a background process
    /usr/sbin/cron -f &
    CRON_PID=$!
    
    echo "Cron started with PID: $CRON_PID"
else
    echo "Cron daemon is already running."
fi

# Wait for cron to be ready (up to 10 seconds)
for i in {1..20}; do
    if ps aux | grep -v grep | grep -q "[c]ron"; then
        echo "Cron daemon started successfully!"
        break
    fi
    
    # Give it some time
    sleep 0.3
done

# Final check
if ! ps aux | grep -v grep | grep -q "[c]ron"; then
    echo "ERROR: Failed to start cron daemon after multiple attempts." >&2
    exit 1
fi

echo "Cron daemon is ready and running!"
exec "$@"
