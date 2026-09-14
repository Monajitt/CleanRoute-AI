"""
Gunicorn configuration optimized for Render Free Web Service (512 MB RAM limit).
Ensures reliable single-worker operation, thread concurrency, Render dynamic PORT binding,
and extended timeout to handle upstream external API latencies.
"""

import os

# Server socket binding (respects Render's dynamic PORT environment variable)
port = os.getenv("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Conservative Worker Configuration for 512 MB RAM
# 1 worker process avoids duplicate Django and module memory footprints.
# 2 gthread threads allow concurrent request servicing with shared memory.
workers = 1
threads = 2
worker_class = "gthread"

# Extended timeouts to prevent false WORKER TIMEOUT kills during upstream API queries
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging to standard output/error for Render console stream
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" (%(L)ss)'
