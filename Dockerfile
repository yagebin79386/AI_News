# Use a lightweight Python base image
FROM python:3.10-slim

# Set timezone
ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install dependencies (removed supervisor)
RUN apt-get update && apt-get install -y \
    gnupg2 \
    wget \
    libpq-dev \
    gcc \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    fonts-liberation \
    libasound2 \
    vim \
    postgresql-client \
    tzdata \
    nginx \
    --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

# 2) Add Google's official GPG key & repo
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
 && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# 3) Install Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt || { echo "Pip install failed"; exit 1; }

# Create symlink for python command
RUN ln -sf /usr/local/bin/python3 /usr/local/bin/python

# Create log directories and files
RUN mkdir -p /var/log

# Copy app folders structure
COPY news_ai/ /app/news_ai/
COPY news_crypto/ /app/news_crypto/

# Make sure start.sh files are executable
RUN chmod +x /app/news_ai/start.sh
RUN chmod +x /app/news_crypto/start.sh

# Copy root level files
COPY Dockerfile /app/
COPY fly.toml /app/
COPY README.md /app/
COPY requirements.txt /app/
COPY setup_domain.sh /app/
COPY setup_postgres.sql /app/
COPY templates/ /app/templates/

# Make all Python scripts executable
RUN find /app -name "*.py" -exec chmod +x {} \;

# Install supercronic
ADD https://github.com/aptible/supercronic/releases/latest/download/supercronic-linux-amd64 /usr/local/bin/supercronic
RUN chmod +x /usr/local/bin/supercronic

# Create the crontab file for supercronic
COPY my-crontab /app/my-crontab
RUN chmod 0644 /app/my-crontab

# Test supercronic setup during build
RUN echo "* * * * * echo test" > /tmp/test-crontab && \
    /usr/local/bin/supercronic -test /tmp/test-crontab && \
    echo "Supercronic validation successful"

# Configure Nginx
RUN rm /etc/nginx/sites-enabled/default
COPY <<EOF /etc/nginx/sites-available/news_ai
server {
    listen 8085;
    server_name _;

    # Fix for "Contradictory scheme headers" issue
    proxy_set_header X-Forwarded-Proto \$http_x_forwarded_proto;

    # Management app routing
    location /ai/management {
        proxy_pass http://127.0.0.1:3000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$http_x_forwarded_proto;
        proxy_set_header X-Script-Name /ai/management;
    }

    location /crypto/management {
        proxy_pass http://127.0.0.1:3002/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$http_x_forwarded_proto;
        proxy_set_header X-Script-Name /crypto/management;
    }

    # Newsletter app routing - pass everything after /newsletter/
    location ~ ^/ai/newsletter(/.*|$) {
        proxy_pass http://127.0.0.1:3001\$1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$http_x_forwarded_proto;
        proxy_set_header X-Script-Name /ai/newsletter;
    }
    
    location ~ ^/crypto/newsletter(/.*|$) {
        proxy_pass http://127.0.0.1:3003\$1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$http_x_forwarded_proto;
        proxy_set_header X-Script-Name /crypto/newsletter;
    }

    # Health check route for the deployment
    location = /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }

    # Root path redirect to management
    location = / {
        return 301 /management;
    }

    # Prevent accessing directly the nginx default error page
    error_page 404 /404.html;
    location = /404.html {
        root /app/templates;
        internal;
    }
}
EOF

RUN ln -s /etc/nginx/sites-available/news_ai /etc/nginx/sites-enabled/

# Make sure start.sh is executable
COPY app_start.sh /app/app_start.sh
RUN chmod +x /app/app_start.sh

# Expose the main port
EXPOSE 8085

# Use start.sh as the container entry point
CMD ["/app/app_start.sh"]
