import os
import ssl
import socket
import signal
import traceback
import asyncio
import sys
import argparse

from worker import Worker
from datetime import datetime
from http_utils.base import (
    get_http_status_text,
    get_ext_from_mime_type,
    get_mime_type_from_ext,
)
from pysigset import suspended_signals

class MasterWorker:
    def __init__(self, app, host, port, request_queue_size):
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile="certificate.pem", keyfile="key.pem")
        ssl_context.set_alpn_protocols(["h2", "spdy/2", "http/1.1"])
        self.ssl_context = ssl_context
        self.pid = os.getpid()
        self.APP = app
        self.HOST = host
        self.PORT = port
        self.REQUEST_QUEUE_SIZE = request_queue_size
        print(("Serving HTTP on port {port} ...".format(port=self.PORT)))

    def shutdown_workers(self, signum, frame):
        print(("shutting down pid: %d" % os.getpid()))
        os._exit(0)

    async def run(self):
        signal.signal(signal.SIGINT, self.shutdown_workers)
        server = await asyncio.start_server(self.set_up_producer_consumer, self.HOST, self.PORT, family=socket.AF_INET, ssl=self.ssl_context, reuse_address=True, backlog=self.REQUEST_QUEUE_SIZE)
        await server.wait_closed()
    
    async def set_up_producer_consumer(self, stream_reader, stream_writer):
        worker = Worker(socket.getfqdn(self.HOST), self.PORT)
        sys.path.insert(0, self.APP)
        module = __import__(self.APP.split("/")[-1], globals(), locals(), ["asgi"], 0)
        worker.application = module.asgi.application
        worker.frame_queue = asyncio.Queue()
        worker.socket_reader = stream_reader
        worker.socket_writer = stream_writer
        t1 = asyncio.create_task(worker.get_frame())
        t2 = asyncio.create_task(worker.handle_request())
        await asyncio.wait([t1, t2])
    

def serve_forever():
    parser = argparse.ArgumentParser(prog="HTTP/2 ASGI compatible web server for python.")
    parser.add_argument("--app", metavar="app", help="path to your ASGI Application")
    parser.add_argument("--host", metavar="host", help="Host IP Address", default="127.0.0.1")
    parser.add_argument("--port", metavar="port", type=int, help="Port Number", default=8000)
    parser.add_argument("--queue-size", metavar="queue_size", type=int, help="Request Queue Size", default=100)
    arguments = parser.parse_args()
    master_worker = MasterWorker(arguments.app, arguments.host, arguments.port, arguments.queue_size)
    asyncio.run(master_worker.run())

if __name__ == "__main__":
    serve_forever()
