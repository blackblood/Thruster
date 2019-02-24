import socket
import StringIO
import sys
import datetime
import time
import traceback
import bitstring
import struct
import binascii

from hpack import Decoder
from http.frames.settings_frame import SettingsFrame

class WSGIServer(object):
	address_family = socket.AF_INET
	socket_type = socket.SOCK_STREAM
	request_queue_size = 1

	def __init__(self, server_name, server_port):
		self.server_name = server_name
		self.server_port = server_port
		self.client_connection = None
		self.request_data = ""
		self.headers_set = []

	def set_app(self, application):
		self.application = application

	def handle_request(self):
		try:
			self.request_data = self.client_connection.recv(4096)
			print(self.request_data)
			# recv_data = self.client_connection.recv(1024)
			# while recv_data:
			# 	print(recv_data)
			# 	self.request_data += recv_data
			# 	recv_data = self.client_connection.recv(1024)
			import ipdb; ipdb.set_trace()
			settings_frame = self.parse_request(self.request_data)
			if settings_frame:
				sent_data = self.client_connection.sendall(settings_frame.bytes)
				if sent_data == None:
					print("all data has been sent.")
				else:
					print("still sending")
					print(sent_data)
					print("still sending end")
			return None
			env = self.set_env()
			result = self.application(env, self.start_response)
			self.finish_response(result)
		except Exception:
			print("Error occurred in handle_request")
			print(traceback.format_exc())
	
	def parse_request(self, raw_data):
		if raw_data:
			raw_data = raw_data.replace("PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n", "")
			bits = bitstring.ConstBitStream(hex=binascii.hexlify(raw_data))
			frame_length = bits.read("uint:24")
			frame_type = bits.read("hex:8")
			if frame_type == '04':
				settings_frame = SettingsFrame(bits)
				ack_frame = SettingsFrame.get_acknowledgement_frame()
				return ack_frame

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
			try:
				self.client_connection.sendall(response)
			except OSError as e:
				print(e)
		except Exception:
			print("Exception raised in finish response")