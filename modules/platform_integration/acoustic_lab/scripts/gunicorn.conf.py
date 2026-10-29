# 🌐 Acoustic Lab - Gunicorn Production Configuration
# WSP Protocol Compliant WSGI Server for Ubuntu VPS / Google Cloud
# Optimized for educational acoustic processing workloads

import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes (conservative for Phase 1)
workers = min(multiprocessing.cpu_count(), 4)  # Max 4 workers for acoustic processing
worker_class = "sync"  # Synchronous for CPU-bound audio processing
worker_connections = 100  # Lower for focused acoustic workloads
max_requests = 500  # Restart workers to prevent memory leaks
max_requests_jitter = 50
timeout = 60  # Extended for audio processing
keepalive = 10
graceful_timeout = 30

# Logging (production format)
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
accesslog = "/var/log/acoustic-lab/access.log"
errorlog = "/var/log/acoustic-lab/error.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "acoustic-lab"

# Server mechanics
daemon = False
pidfile = "/var/run/acoustic-lab/gunicorn.pid"
user = "acoustic"
group = "acoustic"
tmp_upload_dir = "/var/cache/acoustic-lab/uploads"

# Application
pythonpath = "/var/www/acoustic-lab"
wsgi_app = "modules.platform_integration.acoustic_lab.src.web_app:create_app()"

# Environment
raw_env = [
    "NODE_ENV=production",
    "PYTHONPATH=/var/www/acoustic-lab",
    f"HOME=/home/{user}"
]

# SSL (handled by nginx reverse proxy)
# No direct SSL configuration needed

# Production optimizations
preload_app = True  # Load app before forking workers
worker_tmp_dir = "/dev/shm"  # Use RAM for temp files
sendfile = True  # Optimize static file serving

# Performance monitoring
statsd_host = None  # Enable if using statsd monitoring
statsd_prefix = "acoustic_lab"

# Development overrides (uncomment for debugging)
# reload = True
# reload_engine = "auto"
# spew = True
# workers = 1
# loglevel = "debug"
