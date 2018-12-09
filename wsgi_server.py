import socket
import StringIO
import sys
import datetime
import time

class WSGIServer(object):
	address_family = socket.AF_INET
	socket_type = socket.SOCK_STREAM
	request_queue_size = 1

	def __init__(self, server_name, server_port):
		self.server_name = server_name
		self.server_port = server_port
		self.client_connection = None
		self.headers_set = []

	def set_app(self, application):
		self.application = application

	def handle_request(self):
		try:
			self.request_data = self.client_connection.recv(1024)
			print(''.join('< {line} \n').format(line=line) for line in self.request_data.splitlines())
			self.parse_request(self.request_data)
			env = self.set_env()
			result = self.application(env, self.start_response)
			self.finish_response(result)
		except Exception:
			print("Error occurred in handle_request")

	def parse_request(self, text):
		print("request_line = %s" % self.request_data)
		request_line = text.splitlines()[0]
		request_line = request_line.rstrip('\r\n')
		(self.request_method, self.path, self.request_version) = request_line.split()

	def set_env(self):
		env = {}

		env['wsgi.version'] = (1,0)
		env['wsgi.url_scheme'] = 'http'
		env['wsgi.input'] = StringIO.StringIO(self.request_data)
		env['wsgi.errors'] = sys.stderr
		env['wsgi.multithread'] = False
		env['wsgi.multiprocess'] = False
		env['wsgi.run_once'] = False
		env['REQUEST_METHOD'] = self.request_method
		env['PATH_INFO'] = self.path
		env['SERVER_NAME'] = self.server_name
		env['SERVER_PORT'] = str(self.server_port)

		return env

	def start_response(self, status, response_headers, exc_info=None):
		server_headers = [
			('Date', datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')),
			('Server', 'WSGIServer 0.2')
		]

		self.headers_set = [status, server_headers + response_headers]

	def finish_response(self, result):
		try:
			status, response_headers = self.headers_set
			response = 'HTTP 1.1 / {status}\r\n'.format(status=status)

			for header in response_headers:
				response += '{0}: {1}\r\n'.format(*header)
			response += '\r\n'

			for data in result:
				response += data

			print(''.join('< {line}\n').format(line=line) for line in response.splitlines())
			self.client_connection.sendall(response)
		except Exception:
			print("Exception raised in finish response")