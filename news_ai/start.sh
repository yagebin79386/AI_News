#!/bin/bash
set -e

# Print startup information
echo "Starting News AI specific services..."

# Create log files if they don't exist
echo "Creating log files..."
mkdir -p /var/log/ai
touch /var/log/ai/subscriber_mgt.log && chmod 644 /var/log/ai/subscriber_mgt.log
touch /var/log/ai/subscriber_mgt.err.log && chmod 644 /var/log/ai/subscriber_mgt.err.log
touch /var/log/ai/newsletter_page.log && chmod 644 /var/log/ai/newsletter_page.log
touch /var/log/ai/newsletter_page.err.log && chmod 644 /var/log/ai/newsletter_page.err.log

# Start the subscriber management app with gunicorn
echo "Starting AI subscriber management app..."
cd /app && PYTHONPATH=/app:/app/news_ai gunicorn --bind 127.0.0.1:3000 news_ai.subscriber_mgt:app --timeout 120 > /var/log/ai/subscriber_mgt.log 2> /var/log/ai/subscriber_mgt.err.log &

# Start the newsletter page app with gunicorn
echo "Starting AI newsletter page app..."
cd /app && PYTHONPATH=/app:/app/news_ai gunicorn --bind 127.0.0.1:3001 news_ai.Newsletter_page:app --timeout 120 > /var/log/ai/newsletter_page.log 2> /var/log/ai/newsletter_page.err.log &

echo "News AI specific services started." 