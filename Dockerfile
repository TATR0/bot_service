FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN cat > /etc/supervisor/conf.d/app.conf << 'SUPEOF'
[supervisord]
nodaemon=true
logfile=/dev/null
logfile_maxbytes=0

[program:api]
command=uvicorn api:app --host 0.0.0.0 --port 8080
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:bot]
command=python bot.py
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
SUPEOF

CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
