import socket
import io
import sys
import datetime
import time
import traceback
import bitstring
import asyncio
import queue

from hpack import Encoder, Decoder
from http2.frames.settings_frame import SettingsFrame
from http2.frames.headers_frame import HeadersFrame
from http2.frames.continuation_frame import ContinuationFrame
from http2.frames.data_frame import DataFrame
from http2.frames.rst_frame import RstStreamFrame
from http2.frames import utils

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
		self.connection_established = False
		self.response_queue = queue.Queue()

	def set_app(self, application):
		self.application = application
	
	async def asgi_more_data(self):
		request_data = self.client_connection.recv(4096)
		frame = self.parse_request(request_data)
		if isinstance(frame, DataFrame):
			asgi_event = {"type": "http.request", "body": frame.body}
			if frame.end_stream:
				asgi_event["more_body"] = False
			else:
				asgi_event["more_body"] = True
			
			return asgi_event
	
	async def trigger_asgi_application(self):
		return { "type": "http.request", "body": b"", "more_body": False }
	
	async def send_response(self, event):
		if event["type"] == "http.response.start":
			headers_frame = HeadersFrame(self.connection_settings, self.header_encoder, self.header_decoder)
			response_headers = {}
			for h in event["headers"]:
				response_headers[h[0]] = h[1]
			response_headers[':status'] = event["status"]
			encoded_headers = self.header_encoder.encode(HeadersFrame.normalize_header_fields(response_headers))
			
			if len(encoded_headers) <= self.connection_settings.max_frame_size:
				self.response_queue.put(
					headers_frame.write(
						flags={
							'end_stream': '0', 'end_headers': '1', 'padded': '0', 'priority': '1'
						},
						headers_block_fragment=encoded_headers[0:self.connection_settings.max_frame_size]
					)
				)	
			else:
				self.response_queue.put(
					headers_frame.write(
						flags={
							'end_stream': '0', 'end_headers': '0', 'padded': '0', 'priority': '1'
						},
						headers_block_fragment=encoded_headers[0:self.connection_settings.max_frame_size]
					)
				)
			
				for chunk, is_last in utils.get_chunks(
					encoded_headers_as_bytes,
					self.connection_settings.max_frame_size,
					offset=self.connection_settings.max_frame_size
				):
					self.response_queue.put(
						ContinuationFrame().write(
							flags={
								'end_stream': '0', 'end_headers': '1' if is_last else '0', 'padded': '0', 'priority': '1'
							},
							headers_block_fragment=chunk
						)
					)
		elif event["type"] == "http.response.body":
			if event["body"]:
				data_frame = DataFrame(self.connection_settings)
				try:
					for chunk, is_last in utils.get_chunks(event["body"], self.connection_settings.max_frame_size):
						self.response_queue.put(
							data_frame.write(
								flags={'end_stream': '1' if is_last and not event["more_body"] else '0', 'padded': '0'},
								body=chunk
							)
						)
				except OSError as e:
					print(e)
			
			while not self.response_queue.empty():
				self.client_connection.sendall(self.response_queue.get().bytes)
		else:
			raise ValueError("Unkown event type: %s" % event["type"])

	def handle_request(self):
		try:
			while True:
				self.request_data = self.client_connection.recv(4096)
				self.frame = self.parse_request(self.request_data)
				if isinstance(self.frame, SettingsFrame):
					self.client_connection.sendall(SettingsFrame.get_acknowledgement_frame().bytes)
					self.connection_established = True
				elif isinstance(self.frame, HeadersFrame):
					if self.frame.end_stream:
						asgi_scope = self.get_asgi_event_dict(self.frame)
						self.asgi_app = self.application(asgi_scope)
						self.event_loop.run_until_complete(self.asgi_app(self.trigger_asgi_application, self.send_response))
					else:
						self.asgi_scope = self.get_asgi_event_dict(self.frame)
				elif isinstance(self.frame, ContinuationFrame):
					if self.frame.end_stream:
						self.asgi_app = self.application(self.asgi_scope)
						self.event_loop.run_until_complete(self.asgi_app(self.trigger_asgi_application, self.send_response))
					else:
						self.asgi_scope["headers"].extend([[k,v] for k,v in self.frame.headers.iteritems()])
				elif isinstance(self.frame, DataFrame):
					pass
				elif isinstance(self.frame, RstStreamFrame):
					raise ValueError("RSTFrame received with error: (%d, %s)" % (self.frame.error_code, self.frame.description))
				else:
					pass
		except Exception:
			print("Error occurred in handle_request")
			print((traceback.format_exc()))
	
	def parse_request(self, raw_data):
		if raw_data:
			if not self.connection_established:
				raw_data = raw_data[24:]
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
			elif frame_type == '09':
				cont_frame = ContinuationFrame()
				cont_frame.read(bits)
				return cont_frame
			elif frame_type == '00':
				data_frame = DataFrame()
				data_frame.read(bits)
				return data_frame

	def set_env(self):
		env = {}

		env['wsgi.version'] = (1,0)
		env['wsgi.url_scheme'] = 'https'
		env['wsgi.input'] = io.StringIO(self.request_data)
		env['wsgi.errors'] = sys.stderr
		env['wsgi.multithread'] = False
		env['wsgi.multiprocess'] = False
		env['wsgi.run_once'] = False
		env['REQUEST_METHOD'] = self.frame.get_method()
		env['PATH_INFO'] = self.frame.get_path()
		env['SERVER_NAME'] = self.server_name
		env['SERVER_PORT'] = str(self.server_port)

		return env
	
	def get_asgi_event_dict(self, frame):
		event_dict = {
			"type": "http",
			"asgi": {
				"version": "2.0",
				"spec_version": "2.1"
			},
			"http_version": "2",
			"method": frame.get_method(),
			"scheme": "https",
			"path": frame.get_path(),
			"query_string": "",
			"headers": [[k.encode("utf-8"),v.encode("utf-8")] for k,v in frame.headers.items()],
		}
		return event_dict

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
			print((traceback.format_exc()))
			print(exp)
			print("Exception raised in finish response")