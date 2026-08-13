"""Gunicorn production defaults; all values can be overridden by environment."""
from __future__ import annotations

import os

bind = "0.0.0.0:8000"
workers = max(1, int(os.getenv("WEB_CONCURRENCY", "3")))
threads = max(1, int(os.getenv("GUNICORN_THREADS", "2")))
worker_class = "gthread"
timeout = max(10, int(os.getenv("GUNICORN_TIMEOUT", "60")))
graceful_timeout = 30
keepalive = 5
max_requests = 2000
max_requests_jitter = 200
worker_tmp_dir = "/tmp"
accesslog = "-"
errorlog = "-"
capture_output = True
