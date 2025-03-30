# Use a lightweight Python base image
FROM python:3.10-slim

# Set timezone
ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install cron & supervisor so we can run multiple processes
RUN apt-get update && apt-get install -y \
    gnupg2 \
    wget \
    cron \
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
RUN pip install --no-cache-dir -r requirements.txt

# Create symlink for python command
RUN ln -sf /usr/local/bin/python3 /usr/local/bin/python

# Create log file
RUN touch /var/log/news_AI_scrape_app.log && chmod 644 /var/log/news_AI_scrape_app.log
RUN touch /var/log/news_AI_categorization_app.log && chmod 644 /var/log/news_AI_categorization_app.log
RUN touch /var/log/news_AI_evaluation_app.log && chmod 644 /var/log/news_AI_evaluation_app.log
RUN touch /var/log/news_AI_generate_app.log && chmod 644 /var/log/news_AI_generate_app.log
RUN touch /var/log/news_AI_send_app.log && chmod 644 /var/log/news_AI_send_app.log

# Copy all project files into the container
COPY . .

# Create crontab file with proper line endings
RUN echo "DATABASE_URL=postgres://postgres:NUizJbF1I6OhHDs@newsai-db.flycast:5432" > /etc/cron.d/news_ai_cron && \
    echo "0 17 * * 1,3,5 root /usr/local/bin/python3 /app/ScraperNewsLLM.py >> /var/log/news_AI_scrape_app.log 2>&1" >> /etc/cron.d/news_ai_cron && \
    echo "30 18 * * 1,3,5 root /usr/local/bin/python3 /app/categorizationLLM.py >> /var/log/news_AI_categorization_app.log 2>&1" >> /etc/cron.d/news_ai_cron && \
    echo "20 19 * * 1,3,5 root /usr/local/bin/python3 /app/evaluate_articles.py >> /var/log/news_AI_evaluation_app.log 2>&1" >> /etc/cron.d/news_ai_cron && \
    echo "30 19 * * 1,3,5 root /usr/local/bin/python3 /app/generate_newsletter.py >> /var/log/news_AI_generate_app.log 2>&1" >> /etc/cron.d/news_ai_cron && \
    echo "0 20 * * 1,3,5 root /usr/local/bin/python3 /app/Newsletter_send.py >> /var/log/news_AI_send_app.log 2>&1" >> /etc/cron.d/news_ai_cron

# Set proper permissions for the cron file
RUN chmod 0644 /etc/cron.d/news_ai_cron

# Configure nginx for path-based routing
RUN echo 'server {\n\
    listen 8083;\n\
    \n\
    location / {\n\
        proxy_pass http://127.0.0.1:8084;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
    \n\
    location /newsletter/ {\n\
        proxy_pass http://127.0.0.1:8085;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_set_header X-Forwarded-Proto $scheme;\n\
    }\n\
}' > /etc/nginx/conf.d/default.conf

# Create supervisor configuration
RUN echo '[supervisord]\n\
nodaemon=true\n\
\n\
[program:cron]\n\
command=cron -f\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/var/log/cron.log\n\
stderr_logfile=/var/log/cron.err.log\n\
\n\
[program:nginx]\n\
command=nginx -g "daemon off;"\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/var/log/nginx.log\n\
stderr_logfile=/var/log/nginx.err.log\n\
\n\
[program:subscriber_mgt]\n\
command=gunicorn --bind 127.0.0.1:8084 subscriber_mgt:app\n\
directory=/app\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/var/log/subscriber_mgt.log\n\
stderr_logfile=/var/log/subscriber_mgt.err.log\n\
\n\
[program:newsletter_page]\n\
command=gunicorn --bind 127.0.0.1:8085 Newsletter_page:app\n\
directory=/app\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/var/log/newsletter_page.log\n\
stderr_logfile=/var/log/newsletter_page.err.log' > /etc/supervisor/conf.d/supervisord.conf

# Expose the main port
EXPOSE 8083

# The main process: run Supervisor in the foreground
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
