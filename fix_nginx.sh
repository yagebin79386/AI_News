#!/bin/bash

# This script fixes the Nginx configuration for proper routing
echo "Updating Nginx configuration with correct routing..."

# Create a complete custom Nginx configuration
echo "Creating custom nginx.conf..."
cat > /etc/nginx/nginx.conf << 'EOL'
user www-data;
worker_processes auto;
pid /run/nginx.pid;

events {
    worker_connections 768;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Define the map directive in the http context
    map $http_x_forwarded_proto $proxy_x_forwarded_proto {
        default $http_x_forwarded_proto;
        ""      $scheme;
    }
    
    # Logging settings
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
    
    # Server configuration
    server {
        # Listen on port 8085 on all interfaces
        listen 0.0.0.0:8085 default_server;
        
        # Define server names to respond to
        server_name news-ai-yagebin.fly.dev www.ainewsletter.homesmartify.lu;
        
        # Health check endpoint for Fly.io
        location = /health {
            access_log off;
            add_header Content-Type text/plain;
            return 200 "OK";
        }
        
        # Handle requests to the root path (/) - Subscriber Management
        location / {
            # Forward to the subscriber management app
            proxy_pass http://127.0.0.1:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto;
            proxy_set_header X-Forwarded-Host $host;
        }
        
        # Handle requests to /newsletter - Newsletter Viewing main page
        location = /newsletter {
            # Forward to the newsletter viewing app root
            proxy_pass http://127.0.0.1:3001/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto;
            proxy_set_header X-Forwarded-Host $host;
        }
        
        # Handle requests to /newsletter/X - Newsletter Viewing specific newsletters
        location ~ ^/newsletter/([0-9]+)$ {
            # Forward to the newsletter viewing app with the ID
            proxy_pass http://127.0.0.1:3001/$1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto;
            proxy_set_header X-Forwarded-Host $host;
        }
    }
}
EOL

# Verify Nginx configuration
echo "Testing Nginx configuration..."
nginx -t || {
    echo "ERROR: Nginx configuration test failed!"
    exit 1
}

# Restart Nginx to apply the changes
echo "Restarting Nginx service..."

# Try multiple methods to restart Nginx
NGINX_PID=$(pgrep -f "nginx: master")
if [ -n "$NGINX_PID" ]; then
    echo "Found Nginx master process with PID $NGINX_PID"
    echo "Sending reload signal..."
    nginx -s reload
else
    echo "Nginx master process not found, trying to start it..."
    nginx
fi

# Wait for Nginx to fully start
echo "Waiting for Nginx to start..."
sleep 5

# Simple check if Nginx is running
echo "Checking if Nginx is running..."
if ps -ef | grep -v grep | grep -q "nginx: master"; then
    echo "SUCCESS: Nginx is running"
else
    echo "WARNING: Nginx might not be running correctly"
    ps -ef | grep nginx
fi

echo "Nginx configuration updated and service restarted!"

# Final check - Create a health check file as backup
echo "OK" > /app/health.txt
chmod 644 /app/health.txt 