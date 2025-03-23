#!/bin/bash

PRIVATE_DOMAIN="newsletter.homesmartify.lu"
APP_NAME="news-crypto"  # Replace with your actual Fly.io app name

# Check if the domain exists (for informational purposes only, since adding is deprecated)
if flyctl domains list -a "$APP_NAME" | grep -q "$PRIVATE_DOMAIN"; then
    echo "$PRIVATE_DOMAIN domain already exists on the app"
else
    echo "Domain $PRIVATE_DOMAIN not found. Note: 'flyctl domains add' is deprecated and cannot add new domains."
    echo "Please add the domain manually via the Fly.io dashboard if needed."
fi

# Provision or renew the certificate
echo "Checking certificate for: $PRIVATE_DOMAIN"
if flyctl certs list -a "$APP_NAME" | grep -q "$PRIVATE_DOMAIN"; then
    echo "Certificate for $PRIVATE_DOMAIN has already been provisioned."
else
    echo "Provisioning certificate for $PRIVATE_DOMAIN"
    flyctl certs add -a "$APP_NAME" "$PRIVATE_DOMAIN"
    echo "Certificate is provisioned"
fi