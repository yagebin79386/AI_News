# Use a lightweight Python base image
FROM python:3.10-slim

# Set timezone
ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install supervisor and other dependencies
RUN apt-get update && apt-get install -y \
    gnupg2 \
    wget \
    supervisor \
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
RUN mkdir -p /var/log/news_AI && \
    touch /var/log/news_AI_scrape_app.log && chmod 644 /var/log/news_AI_scrape_app.log && \
    touch /var/log/news_AI_categorization_app.log && chmod 644 /var/log/news_AI_categorization_app.log && \
    touch /var/log/news_AI_evaluation_app.log && chmod 644 /var/log/news_AI_evaluation_app.log && \
    touch /var/log/news_AI_generate_app.log && chmod 644 /var/log/news_AI_generate_app.log && \
    touch /var/log/news_AI_send_app.log && chmod 644 /var/log/news_AI_send_app.log

# Copy all project files into the container
COPY . .

# Install supercronic
ADD https://github.com/aptible/supercronic/releases/latest/download/supercronic-linux-amd64 /usr/local/bin/supercronic
RUN chmod +x /usr/local/bin/supercronic

# Create the crontab file for supercronic
RUN echo "# News AI cron jobs with environment variables available from container" > /app/news-ai-crontab && \
    echo "0 17 * * 1,3,5 /usr/local/bin/python3 /app/ScraperNewsLLM.py >> /var/log/news_AI_scrape_app.log 2>&1" >> /app/news-ai-crontab && \
    echo "30 18 * * 1,3,5 /usr/local/bin/python3 /app/categorizationLLM.py >> /var/log/news_AI_categorization_app.log 2>&1" >> /app/news-ai-crontab && \
    echo "20 19 * * 1,3,5 /usr/local/bin/python3 /app/evaluate_articles.py >> /var/log/news_AI_evaluation_app.log 2>&1" >> /app/news-ai-crontab && \
    echo "30 19 * * 1,3,5 /usr/local/bin/python3 /app/generate_newsletter.py >> /var/log/news_AI_generate_app.log 2>&1" >> /app/news-ai-crontab && \
    echo "0 20 * * 1,3,5 /usr/local/bin/python3 /app/Newsletter_send.py >> /var/log/news_AI_send_app.log 2>&1" >> /app/news-ai-crontab

# Configure Nginx
RUN rm /etc/nginx/sites-enabled/default
COPY <<EOF /etc/nginx/sites-available/news_ai
server {
    listen 8085;
    server_name _;

    # Fix for "Contradictory scheme headers" issue
    proxy_set_header X-Forwarded-Proto \$http_x_forwarded_proto;

    # Management app routing
    location /management {
        proxy_pass http://127.0.0.1:3000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$http_x_forwarded_proto;
        proxy_set_header X-Script-Name /management;
    }

    # Newsletter app routing - pass everything after /newsletter/
    location ~ ^/newsletter(/.*|$) {
        proxy_pass http://127.0.0.1:3001\$1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$http_x_forwarded_proto;
        proxy_set_header X-Script-Name /newsletter;
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

# Configure supervisor
RUN echo '[supervisord]\n\
nodaemon=true\n\
user=root\n\
\n\
[program:nginx]\n\
command=nginx -g "daemon off;"\n\
priority=10\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/var/log/nginx.log\n\
stderr_logfile=/var/log/nginx.err.log\n\
\n\
[program:supercronic]\n\
command=/usr/local/bin/supercronic /app/news-ai-crontab\n\
priority=20\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/var/log/supercronic.log\n\
stderr_logfile=/var/log/supercronic.err.log\n\
\n\
[program:subscriber_mgt]\n\
command=gunicorn --bind 127.0.0.1:3000 subscriber_mgt:app --timeout 120\n\
directory=/app\n\
priority=30\n\
autostart=true\n\
autorestart=true\n\
startretries=3\n\
stdout_logfile=/var/log/subscriber_mgt.log\n\
stderr_logfile=/var/log/subscriber_mgt.err.log\n\
\n\
[program:newsletter_page]\n\
command=gunicorn --bind 127.0.0.1:3001 Newsletter_page:app --timeout 120\n\
directory=/app\n\
priority=30\n\
autostart=true\n\
autorestart=true\n\
startretries=3\n\
stdout_logfile=/var/log/newsletter_page.log\n\
stderr_logfile=/var/log/newsletter_page.err.log' > /etc/supervisor/conf.d/supervisord.conf

# Make sure start.sh is executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose the main port
EXPOSE 8085

# Use start.sh as the container entry point
CMD ["/app/start.sh"]
