import os
import ssl
import socket
import signal
import traceback
import sys

from wsgi_server import WSGIServer as Worker
from datetime import datetime
from http_utils.base import get_http_status_text, get_ext_from_mime_type, get_mime_type_from_ext
from http.request import Request
from http.response import Response
from http.content_negotiator import ContentNegotiator
from pysigset import suspended_signals

SERVER_ADDRESS = (HOST, PORT) = '127.0.0.1', 8888
REQUEST_QUEUE_SIZE = 5

class MasterWorker():
	def __init__(self):
		self.workers = list()
		self.server_name = socket.getfqdn(HOST)
		self.server_port = PORT
		self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
		ssl_context.load_cert_chain(certfile='certificate.pem', keyfile='key.pem')
		ssl_context.set_alpn_protocols(['h2', 'spdy/2', 'http/1.1'])
		# ssl_context.check_hostname = False
		self.context = ssl_context
		self.listen_socket.bind(SERVER_ADDRESS)
		self.listen_socket.listen(REQUEST_QUEUE_SIZE)
		self.pid = os.getpid()
		print(('Serving HTTP on port {port} ...'.format(port=PORT)))
		print(('Parent PID (PPID): {pid}\n'.format(pid=os.getpid())))
  
	def shutdown_workers(self, signum, frame):
		print(("shutting down pid: %d" % os.getpid()))
		os._exit(0)
	
	def create_worker_pool(self):
		# sys.path.insert(0, 'mysite/mysite')
		module = __import__('mysite.mysite', globals(), locals(), ['wsgi'], 0)
		self.application = module.wsgi.application
		signal.signal(signal.SIGINT, self.shutdown_workers)
		signal.signal(signal.SIGCHLD, self.restart_worker)
		for _ in range(5):
			pid = self.create_worker()
		
		with suspended_signals(signal.SIGINT):
			try:
				while os.wait() != -1:
					print("child process terminated")
					continue
			except OSError:
				pass
		print("Exiting...")
		print("Bye Bye!")
    
	def create_worker(self):
		pid = os.fork()
		if pid == 0:
			worker = Worker(self.server_name, self.server_port)
			worker.set_app(self.application)
			while True:
				try:
					client_connection, client_address = self.listen_socket.accept()
					worker.client_connection = self.context.wrap_socket(client_connection, server_side=True)
					print(("selected alpn protocol: %s" % worker.client_connection.selected_alpn_protocol()))
					print(("handled by pid: %d" % os.getpid()))
					worker.handle_request()
				except Exception:
					print((traceback.format_exc()))
			os._exit(0)
		else:
			print(("Created worker with pid: %d" % pid))
			return pid

	def restart_worker(self, signum, frame):
		if os.WIFEXITED(signum):
			print("Restarting worker...")
			self.create_worker()
		if os.WIFSIGNALED(signum):
			print("signalled")

def serve_forever():
  	master_worker = MasterWorker()
  	master_worker.create_worker_pool()

if __name__ == '__main__':
  	serve_forever()