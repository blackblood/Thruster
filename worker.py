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
from http2.frames.window_update_frame import WindowUpdateFrame
from http2.frames.ping_frame import PingFrame
from http2.frames import utils
from http2.stream import Stream
from http2.frames.frame_factory import FrameFactory


class Worker(object):
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 1

    def __init__(self, server_name, server_port):
        self.server_name = server_name
        self.server_port = server_port
        self.socket_reader = None
        self.socket_writer = None
        self.header_encoder = Encoder()
        self.header_decoder = Decoder()
        self.request_data = ""
        self.headers_set = []
        self.connection_established = False
        self.streams = {}
        self.receiving_headers = False
        self.event_loop = None
        self.tasks = []

    def set_app(self, application):
        self.application = application
    
    async def send_connection_error(self, last_stream_id):
        """
        As per RFC 7540, An endpoint should send a goaway frame and close the TCP
        connection when a connection error is encountered.
        """
        self.socket_writer.write(
            GoAwayFrame.connection_error_frame(last_stream_id).bytes
        )
        await self.socket_writer.drain()
        self.socket_writer.close()
        await self.socket_writer.wait_closed()
    
    async def send_stream_error(self, error_stream, error_code):
        self.socket_writer.write(
            RstStreamFrame().write(error_stream.stream_id, error_code).bytes
        )
        await self.socket_writer.drain()
        error_stream.update_status(Stream.CLOSED)

    async def get_frame(self):
        while True:
            if not self.connection_established:
                connection_preface = await self.socket_reader.read(24)
                self.connection_established = True
            
            request_data = await self.socket_reader.read(9)
            frame = FrameFactory.read_frame(request_data, self.header_encoder, self.header_decoder)
            request_data = await self.socket_reader.read(frame.frame_length)
            frame.read_body(request_data)
            print(frame)
            if frame:
                if isinstance(frame, DataFrame):
                    current_stream = self.streams.get(str(frame.stream_id))
                    if frame.stream_id == 0:
                        await self.send_connection_error(self.last_stream_id)
                    elif current_stream.status not in [Stream.OPEN, Stream.HALF_CLOSED_LOCAL]:
                        await self.send_stream_error(current_stream, RstStreamFrame.STREAM_CLOSED)
                    else:
                        await current_stream.data_frame_queue.put(frame)
                else:
                    await self.frame_queue.put(frame)
            await asyncio.sleep(0)

    async def handle_request(self):
        try:
            while True:
                self.frame = await self.frame_queue.get()
                current_stream = self.streams.get(str(self.frame.stream_id))
                if (
                    self.receiving_headers
                    and self.last_stream_id != self.frame.stream_id
                    and type(self.frame) not in [ContinuationFrame]
                ):
                    await self.send_connection_error(self.last_stream_id)
                # elif current_stream.status == Stream.CLOSED:
#                     # Need to handle the case where frames already in transition are received
#                     await self.send_stream_error(current_stream, RstStreamFrame.STREAM_CLOSED)
                elif isinstance(self.frame, SettingsFrame):
                    self.connection_settings = self.frame
                    self.socket_writer.write(
                        SettingsFrame.get_acknowledgement_frame().bytes
                    )
                    await self.socket_writer.drain()
                elif isinstance(self.frame, HeadersFrame):
                    current_stream = Stream(
                        self.connection_settings,
                        self.header_encoder,
                        self.header_decoder,
                        self.socket_writer,
                    )
                    current_stream.stream_id = self.frame.stream_id
                    current_stream.update_status(Stream.OPEN)
                    self.streams[str(current_stream.stream_id)] = current_stream
                    if self.frame.end_headers:
                        current_stream.asgi_scope = (
                            asgi_scope
                        ) = self.get_asgi_event_dict(self.frame)
                        current_stream.asgi_app = self.application(asgi_scope)
                        if self.frame.end_stream:
                            current_stream.update_status(Stream.HALF_CLOSED_REMOTE)
                            await current_stream.asgi_app(
                                current_stream.trigger_asgi_application, current_stream.send_response
                            )
                        else:
                            await current_stream.asgi_app(
                                    current_stream.asgi_more_data, current_stream.send_response
                                )
                    else:
                        self.receiving_headers = True
                        current_stream.asgi_scope = self.get_asgi_event_dict(self.frame)
                elif isinstance(self.frame, ContinuationFrame):
                    current_stream.asgi_scope["headers"].extend(
                        [[k, v] for k, v in self.frame.headers.iteritems()]
                    )
                    if self.frame.end_headers:
                        current_stream = self.streams[self.frame.stream_id]
                        current_stream.asgi_app = self.application(
                            current_stream.asgi_scope
                        )
                        current_stream.stream_id = self.frame.stream_id
                        if self.frame.end_stream:
                            current_stream.update_status(Stream.HALF_CLOSED_REMOTE)
                            await current_stream.asgi_app(
                                current_stream.trigger_asgi_application, current_stream.send_response
                            )
                        else:
                            await current_stream.asgi_app(
                                current_stream.asgi_more_data, current_stream.send_response
                            )
                elif isinstance(self.frame, RstStreamFrame):
                    print(
                        "RSTFrame received with error: (%d, %s)"
                        % (self.frame.error_code, self.frame.description)
                    )
                elif isinstance(self.frame, WindowUpdateFrame):
                    pass
                elif isinstance(self.frame, PingFrame):
                    if not self.frame.ack:
                        ping_frame = PingFrame()
                        ping_frame.body = self.frame.body
                        self.socket_writer.write(
                            ping_frame.write().bytes
                        )
                        await self.socket_writer.drain()
                else:
                    pass
                self.last_stream_id = self.frame.stream_id
        except Exception:
            print("Error occurred in handle_request")
            print((traceback.format_exc()))

    def get_asgi_event_dict(self, frame):
        event_dict = {
            "type": "http",
            "asgi": {"version": "2.0", "spec_version": "2.1"},
            "http_version": "2",
            "method": frame.get_method(),
            "scheme": "https",
            "path": frame.get_path(),
            "query_string": "",
            "headers": [
                [k.encode("utf-8"), v.encode("utf-8")] for k, v in frame.headers.items()
            ],
        }
        return event_dict