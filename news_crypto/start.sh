#!/bin/bash
set -e

# Print startup information
echo "Starting News Crypto specific services..."

# Create log files if they don't exist
echo "Creating log files..."
mkdir -p /var/log/crypto
touch /var/log/crypto/crypto_subscriber_mgt.log && chmod 644 /var/log/crypto/crypto_subscriber_mgt.log
touch /var/log/crypto/crypto_subscriber_mgt.err.log && chmod 644 /var/log/crypto/crypto_subscriber_mgt.err.log
touch /var/log/crypto/crypto_newsletter_page.log && chmod 644 /var/log/crypto/crypto_newsletter_page.log
touch /var/log/crypto/crypto_newsletter_page.err.log && chmod 644 /var/log/crypto/crypto_newsletter_page.err.log

# Start the subscriber management app with gunicorn
echo "Starting Crypto subscriber management app..."
cd /app && PYTHONPATH=/app:/app/news_crypto gunicorn --bind 127.0.0.1:3002 news_crypto.subscriber_mgt:app --timeout 120 > /var/log/crypto/crypto_subscriber_mgt.log 2> /var/log/crypto/crypto_subscriber_mgt.err.log &

# Start the newsletter page app with gunicorn
echo "Starting Crypto newsletter page app..."
cd /app && PYTHONPATH=/app:/app/news_crypto gunicorn --bind 127.0.0.1:3003 news_crypto.Newsletter_page:app --timeout 120 > /var/log/crypto/crypto_newsletter_page.log 2> /var/log/crypto/crypto_newsletter_page.err.log &

echo "News Crypto specific services started." 