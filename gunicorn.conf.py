# ============================================
# Gunicorn Configuration for Production
# ============================================
# This file configures gunicorn for optimal performance
# on Render.com and similar platforms
# ============================================

import os
import multiprocessing

# Server socket
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:5000')
backlog = 2048

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'  # For Flask-RESTful, sync works well
worker_connections = 1000
timeout = int(os.getenv('GUNICORN_TIMEOUT', 120))  # 2 minutes for database operations
keepalive = 5
graceful_timeout = 30

# Process naming
proc_name = 'deliveroo-api'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
errorlog = '-'
accesslog = '-'
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Preload app for memory efficiency with multiple workers
preload_app = True

# For debugging - disable in production
def on_starting(server):
    """Called just before master process is initialized."""
    pass

def on_reload(server):
    """Called to recycle workers during reload."""
    pass

def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    pass

def worker_abort(worker):
    """Called when a worker receives SIGABRT."""
    pass

# ============================================
# Performance Tuning Notes:
# - workers: Start with CPU*2+1, monitor memory usage
# - timeout: Higher value needed for slow DB connections
# - preload_app: Reduces memory usage, good for small apps
# - Keep worker count reasonable for Render's limits
# ============================================

