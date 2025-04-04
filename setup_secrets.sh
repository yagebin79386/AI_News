#!/bin/bash

echo "Setting up Fly.io secrets for the News AI application"
echo "----------------------------------------------------"

# Function to prompt for value with optional default
get_value() {
  local prompt="$1"
  local default="$2"
  local value

  if [ -n "$default" ]; then
    read -p "$prompt [$default]: " value
    value="${value:-$default}"
  else
    read -p "$prompt: " value
  fi
  echo "$value"
}

# Check if flyctl is installed
if ! command -v flyctl >/dev/null 2>&1; then
  echo "Error: flyctl is not installed. Please install it first."
  echo "Visit https://fly.io/docs/hands-on/install-flyctl/ for installation instructions."
  exit 1
fi

# Check if logged in
echo "Checking if you're logged in to Fly.io..."
flyctl auth whoami >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "You're not logged in to Fly.io. Please login first:"
  flyctl auth login
fi

# Get app name
APP_NAME=$(get_value "Enter your Fly.io app name" "news-ai-yagebin")

# Set secrets
echo "Setting secrets for app: $APP_NAME"

# Database URL
DB_URL=$(get_value "PostgreSQL Database URL")
flyctl secrets set DATABASE_URL="$DB_URL" --app "$APP_NAME"

# OpenAI API key
OPENAI_KEY=$(get_value "OpenAI API key")
flyctl secrets set OPENAI_API_KEY="$OPENAI_KEY" --app "$APP_NAME"

# Newsletter secret key
NEWSLETTER_KEY=$(get_value "Newsletter secret key" "$(openssl rand -hex 32)")
flyctl secrets set NEWSLETTER_SECRET_KEY="$NEWSLETTER_KEY" --app "$APP_NAME"

# SendGrid API key
SENDGRID_KEY=$(get_value "SendGrid API key")
flyctl secrets set SENDGRID_API_KEY="$SENDGRID_KEY" --app "$APP_NAME"

# Admin email
ADMIN_EMAIL=$(get_value "Newsletter admin email")
flyctl secrets set NEWSLETTER_ADMIN_EMAIL="$ADMIN_EMAIL" --app "$APP_NAME"

# Admin password
ADMIN_PASSWORD=$(get_value "Newsletter admin password")
flyctl secrets set NEWSLETTER_ADMIN_PASSWORD="$ADMIN_PASSWORD" --app "$APP_NAME"

# Google OAuth credentials (optional)
read -p "Do you want to set up Google OAuth? (y/n): " setup_oauth
if [[ "$setup_oauth" == "y" ]]; then
  GOOGLE_ID=$(get_value "Google Client ID")
  flyctl secrets set GOOGLE_CLIENT_ID="$GOOGLE_ID" --app "$APP_NAME"
  
  GOOGLE_SECRET=$(get_value "Google Client Secret")
  flyctl secrets set GOOGLE_CLIENT_SECRET="$GOOGLE_SECRET" --app "$APP_NAME"
fi

echo "----------------------------------------------------"
echo "All secrets have been set for $APP_NAME"
echo "To add a custom domain with HTTPS, use:"
echo "flyctl certs add www.ainewsletter.homesmartify.lu --app $APP_NAME"
echo "Then configure DNS records as instructed by Fly.io"
echo "----------------------------------------------------" 