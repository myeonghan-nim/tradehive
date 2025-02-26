import multiprocessing
import os

bind = "0.0.0.0:8000"

workers = min(multiprocessing.cpu_count(), int(os.getenv("GUNICORN_WORKERS", 4))) * 2
threads = int(os.getenv("GUNICORN_THREADS", 1))

loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

certfile = "/app/web.crt"
keyfile = "/app/web.key"
