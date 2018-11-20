import os
import socket
import signal
import sys

from wsgi_server import WSGIServer as Worker
from datetime import datetime
from pysigset import suspended_signals
from http_utils.base import get_http_status_text, get_ext_from_mime_type, get_mime_type_from_ext
from http.request import Request
from http.response import Response
from http.content_negotiator import ContentNegotiator

SERVER_ADDRESS = (HOST, PORT) = '127.0.0.1', 8888
REQUEST_QUEUE_SIZE = 5

def handle_request(client_connection):
    raw_request = client_connection.recv(1024)
    print(
        'Child PID: {pid}. Parent PID {ppid}'.format(
            pid=os.getpid(),
            ppid=os.getppid(),
        )
    )
    print(raw_request.decode())
    request = Request(raw_request)

    if request.method.upper() == "GET":
        content_negotiator = ContentNegotiator(request)
        resource = content_negotiator.get_resource()
        http_response = Response(request, resource)
    elif request.method.upper() == "POST":
        pass
    elif request.method.upper() == "PUT":
        pass
    elif request.method.upper() == "DELETE":
        pass

    print(http_response.response_str)
    client_connection.sendall(http_response.response_str)

class MasterWorker():
    def __init__(self):
        self.workers = list()
        self.server_name = socket.getfqdn(HOST)
        self.server_port = PORT
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_socket.bind(SERVER_ADDRESS)
        self.listen_socket.listen(REQUEST_QUEUE_SIZE)
        self.pid = os.getpid()
        print('Serving HTTP on port {port} ...'.format(port=PORT))
        print('Parent PID (PPID): {pid}\n'.format(pid=os.getpid()))
    
    def shutdown_workers(self, signum, frame):
        if self.pid != os.getpid():
            print("shutting down pid: %d" % os.getpid())
            os._exit(0)
    
    def create_worker(self):
        r, w = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(w)
            worker = Worker(self.server_name, self.server_port)
            worker.set_app(self.application)
            while True:
                client_connection, client_address = self.listen_socket.accept()
                worker.client_connection = client_connection
                print("handled by pid: %d" % os.getpid())
                worker.handle_request()
            os._exit(0)
        else:
            os.close(r)
            print("Created worker with pid: %d" % pid)
            return pid

    def restart_worker(self, signum, frame):
        if os.WIFEXITED(signum):
            print("Restarting worker...")
            self.create_worker()
        if os.WIFSIGNALED(signum):
            print("signalled")

    def create_worker_pool(self):
        sys.path.insert(0, 'micro_blog')
        module = __import__('micro_blog', globals(), locals(), ['wsgi'], - 1)
        self.application = module.wsgi.application
        signal.signal(signal.SIGINT, self.shutdown_workers)
        signal.signal(signal.SIGCHLD, self.restart_worker)
        for _ in range(5):
            pid = self.create_worker()
        
        with suspended_signals(signal.SIGINT):
            while os.wait() != -1:
                print("child process terminated")
                continue
            print("Exiting...")
            print("Bye Bye!")


def serve_forever():
    master_worker = MasterWorker()
    master_worker.create_worker_pool()

if __name__ == '__main__':
    serve_forever()