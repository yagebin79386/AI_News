#!/bin/bash
set -e

# Print startup information
echo "Starting News AI application..."
echo "Current date: $(date)"

# Log environment variables (just names, not values)
echo "Available environment variables:"
env | cut -d= -f1 | sort

# Start the supervisord process
echo "Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf 