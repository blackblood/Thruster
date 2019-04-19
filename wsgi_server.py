import socket
import StringIO
import sys
import datetime
import time
import traceback
import bitstring
import ipdb

from hpack import Encoder, Decoder
from http.frames.settings_frame import SettingsFrame
from http.frames.headers_frame import HeadersFrame
from http.frames.continuation_frame import ContinuationFrame
from http.frames.data_frame import DataFrame
from http.frames.rst_frame import RstStreamFrame
from http.frames import utils

class WSGIServer(object):
	address_family = socket.AF_INET
	socket_type = socket.SOCK_STREAM
	request_queue_size = 1

	def __init__(self, server_name, server_port):
		self.server_name = server_name
		self.server_port = server_port
		self.client_connection = None
		self.header_encoder = Encoder()
		self.header_decoder = Decoder()
		self.request_data = ""
		self.headers_set = []

	def set_app(self, application):
		self.application = application

	def handle_request(self):
		try:
			while True:
				self.request_data = self.client_connection.recv(4096)
				self.frame = self.parse_request(self.request_data)
				if self.frame.__class__ == SettingsFrame:
					sent_data = self.client_connection.sendall(SettingsFrame.get_acknowledgement_frame().bytes)
				elif self.frame.__class__ == HeadersFrame:
					env = self.set_env()
					result = self.application(env, self.start_response)
					self.finish_response(result)
				elif self.frame.__class__ == RstStreamFrame:
					raise ValueError("RSTFrame received with error: (%d, %s)" % (self.frame.error_code, self.frame.description))
				else:
					pass
		except Exception:
			print("Error occurred in handle_request")
			print(traceback.format_exc())
	
	def parse_request(self, raw_data):
		if raw_data:
			raw_data = raw_data.replace("PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n", "")
			if not raw_data:
				bits = {}
				self.connection_settings = SettingsFrame().read(raw_data)
				return self.connection_settings
			bits = bitstring.ConstBitStream(bytes=raw_data)
			frame_length = bits.read("uint:24")
			frame_type = bits.read("hex:8")
			if frame_type == '04':
				self.connection_settings = SettingsFrame().read(bits)
				return self.connection_settings
			elif frame_type == '01':
				header_frame = HeadersFrame(self.connection_settings, self.header_encoder, self.header_decoder)
				header_frame.read(bits)
				return header_frame
			elif frame_type == '03':
				rst_frame = RstStreamFrame()
				rst_frame.read(bits)
				return rst_frame

	def set_env(self):
		env = {}

		env['wsgi.version'] = (1,0)
		env['wsgi.url_scheme'] = 'https'
		env['wsgi.input'] = StringIO.StringIO(self.request_data)
		env['wsgi.errors'] = sys.stderr
		env['wsgi.multithread'] = False
		env['wsgi.multiprocess'] = False
		env['wsgi.run_once'] = False
		env['REQUEST_METHOD'] = self.frame.get_method()
		env['PATH_INFO'] = self.frame.get_path()
		env['SERVER_NAME'] = self.server_name
		env['SERVER_PORT'] = str(self.server_port)

		return env

	def start_response(self, status, response_headers, exc_info=None):
		server_headers = {
			'Date': datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
			'Server': 'WSGIServer 0.2'
		}

		server_headers.update({k: v for k, v in response_headers})
		self.headers_set = status, server_headers

	def finish_response(self, result):
		try:
			status, response_headers = self.headers_set
			response_headers[':status'] = status.split(" ")[0]
			headers_frame = HeadersFrame(self.connection_settings, self.header_encoder, self.header_decoder)
			encoded_headers = self.header_encoder.encode(HeadersFrame.normalize_header_fields(response_headers))

			if len(encoded_headers) > self.connection_settings.max_frame_size:
				self.client_connection.sendall(
					headers_frame.write(
						flags={
							'end_stream': '0', 'end_headers': '0', 'padded': '0', 'priority': '1'
						},
						headers_block_fragment=encoded_headers[0:self.connection_settings.max_frame_size]
					).bytes
				)
				for chunk, is_last in utils.get_chunks(encoded_headers, self.connection_settings.max_frame_size):
					self.client_connection.sendall(
						ContinuationFrame().write(
							flags={'end_headers': '1' if is_last else '0'},
							headers_block_fragment=chunk
						).bytes
					)
			else:
				self.client_connection.sendall(
					headers_frame.write(
						flags={
							'end_stream': '0', 'end_headers': '1', 'padded': '0', 'priority': '1'
						},
						headers_block_fragment=encoded_headers[0:self.connection_settings.max_frame_size]
					).bytes
				)
			
			response = ""
			for data in result:
				response += data
			
			data_frame = DataFrame(self.connection_settings)
			try:
				for chunk, is_last in utils.get_chunks(bytearray(response, "utf-8"), self.connection_settings.max_frame_size):
					self.client_connection.sendall(
						data_frame.write(
							flags={'end_stream': '1' if is_last else '0', 'padded': '0'},
							response_body=chunk
						).bytes
					)
			except OSError as e:
				print(e)
		except Exception as exp:
			print(traceback.format_exc())
			print(exp)
			print("Exception raised in finish response")