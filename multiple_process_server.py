import os
import ssl
import socket
import signal
import traceback
import asyncio
import sys
import argparse

from wsgi_server import WSGIServer as Worker
from datetime import datetime
from http_utils.base import (
    get_http_status_text,
    get_ext_from_mime_type,
    get_mime_type_from_ext,
)
from pysigset import suspended_signals

SERVER_ADDRESS = (HOST, PORT) = "127.0.0.1", 8888
REQUEST_QUEUE_SIZE = 5


class MasterWorker:
    def __init__(self):
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile="certificate.pem", keyfile="key.pem")
        ssl_context.set_alpn_protocols(["h2", "spdy/2", "http/1.1"])
        self.ssl_context = ssl_context
        self.pid = os.getpid()
        print(("Serving HTTP on port {port} ...".format(port=PORT)))
        print(("Parent PID (PPID): {pid}\n".format(pid=os.getpid())))

    def shutdown_workers(self, signum, frame):
        print(("shutting down pid: %d" % os.getpid()))
        os._exit(0)

    async def run(self):
        signal.signal(signal.SIGINT, self.shutdown_workers)

        server = await asyncio.start_server(self.set_up_producer_consumer, HOST, PORT, family=socket.AF_INET, ssl=self.ssl_context, reuse_address=True)
        await server.wait_closed()

        with suspended_signals(signal.SIGINT):
            try:
                while os.wait() != -1:
                    print("child process terminated")
                    continue
            except OSError:
                pass
        print("Exiting...")
        print("Bye Bye!")
    
    async def set_up_producer_consumer(self, stream_reader, stream_writer):
        worker = Worker(socket.getfqdn(HOST), PORT)
        sys.path.insert(0, self.arguments.app[0])
        module = __import__(self.arguments.app[0], globals(), locals(), ["asgi"], 0)
        worker.application = module.asgi.application
        worker.frame_queue = asyncio.Queue()
        worker.socket_reader = stream_reader
        worker.socket_writer = stream_writer
        t1 = asyncio.create_task(worker.get_frame())
        t2 = asyncio.create_task(worker.handle_request())
        await asyncio.wait([t1, t2])
    

def serve_forever():
    master_worker = MasterWorker()
    parser = argparse.ArgumentParser(prog="HTTP/2 ASGI compatible web server for python.")
    parser.add_argument("--app", nargs=1, help="path to your ASGI Application")
    master_worker.arguments = parser.parse_args()
    asyncio.run(master_worker.run())

if __name__ == "__main__":
    serve_forever()
