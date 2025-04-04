#!/bin/bash
set -e

# Print startup information
echo "Starting News AI application..."
echo "Current date: $(date)"

# Log environment variables (just names, not values)
echo "Available environment variables:"
env | cut -d= -f1 | sort

# Ensure crontab file has correct permissions
echo "Setting up crontab file..."
ls -la /app/my-crontab
chmod 644 /app/my-crontab

# Start nginx in the background
echo "Starting nginx..."
nginx -g "daemon on;" > /var/log/nginx.log 2> /var/log/nginx.err.log

# Start supercronic with more visibility and proper environment
echo "Starting supercronic for cron jobs..."
export SUPERCRONIC_DEBUG=1
/usr/local/bin/supercronic -debug /app/my-crontab > /var/log/supercronic.log 2>&1 &
SUPERCRONIC_PID=$!
echo "Supercronic started with PID: $SUPERCRONIC_PID"

# Start the specific application services
echo "Starting application-specific services..."
bash /app/news_ai/start.sh &
sleep 5
bash /app/news_crypto/start.sh &


# Keep the container running
echo "All services started. Container is now running..."
# Display some initial supercronic logs to verify startup
sleep 5
echo "Initial supercronic logs:"
cat /var/log/supercronic.log
echo "Starting log tail for monitoring..."
tail -f /var/log/supercronic.log 