import multiprocessing
import os


HOST = os.environ.get('HOST', '0.0.0.0')
PORT = os.environ.get('PORT', 8765)


bind = '{}:{}'.format(HOST, PORT)
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'aiohttp.worker.GunicornWebWorker'
max_requests = 100
max_requests_jitter = 50
reload = bool(os.environ.get('RELOAD', False))
capture_output = True
