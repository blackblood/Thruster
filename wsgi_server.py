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
        self.streams = {}
        self.receiving_headers = False
        self.event_loop = None
        self.frame_queue = asyncio.Queue()
        self.tasks = []

    def set_app(self, application):
        self.application = application

    async def get_frame(self):
        while True:
            print("inside get_frame")
            request_data = await self.event_loop.sock_recv(self.client_connection, 4096)
            print("after receiving socket data")
            frame = self.parse_request(request_data)
            print("frame = %s" % frame)
            if isinstance(frame, DataFrame):
                current_stream = self.streams.get(str(frame.stream_id))
                await current_stream.data_frame_queue.put(frame)
            else:
                await self.frame_queue.put(frame)
            await asyncio.sleep(0)

    async def handle_request(self):
        try:
            while True:
                print("inside handle_request")
                self.frame = await self.frame_queue.get()
                print("self.frame = %s" % self.frame)
                # self.frame_queue.task_done()
                current_stream = self.streams.get(str(self.frame.stream_id))
                if (
                    self.receiving_headers
                    and self.last_stream_id != self.frame.stream_id
                    and type(self.frame) not in [ContinuationFrame]
                ):
                    print("sending go_away frame")
                    self.client_connection.sendall(
                        GoAwayFrame.connection_error_frame(self.last_stream_id).bytes
                    )
                if isinstance(self.frame, SettingsFrame):
                    self.client_connection.sendall(
                        SettingsFrame.get_acknowledgement_frame().bytes
                    )
                elif isinstance(self.frame, HeadersFrame):
                    current_stream = Stream(
                        self.connection_settings,
                        self.header_encoder,
                        self.header_decoder,
                        self.client_connection,
                    )
                    current_stream.stream_id = self.frame.stream_id
                    self.streams[str(current_stream.stream_id)] = current_stream
                    if self.frame.end_headers:
                        current_stream.update_status(Stream.HALF_CLOSED_REMOTE)
                        current_stream.asgi_scope = (
                            asgi_scope
                        ) = self.get_asgi_event_dict(self.frame)
                        current_stream.asgi_app = self.application(asgi_scope)
                        if self.frame.end_stream:
                            await current_stream.asgi_app(
                                current_stream.trigger_asgi_application, current_stream.send_response
                            )
                        else:
                            # self.tasks.append(
                            await current_stream.asgi_app(
                                    current_stream.asgi_more_data, current_stream.send_response
                                )
                            # )
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
                        current_stream.update_status(Stream.HALF_CLOSED_REMOTE)
                        if self.frame.end_stream:
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
                        self.client_connection.sendall(
                            ping_frame.write().bytes
                        )
                else:
                    pass
                self.last_stream_id = self.frame.stream_id
        except Exception:
            print("Error occurred in handle_request")
            print((traceback.format_exc()))

    def parse_request(self, raw_data):
        if raw_data:
            if not self.connection_established:
                raw_data = raw_data[24:]
                self.connection_established = True
            if not raw_data:
                bits = {}
                self.connection_settings = SettingsFrame().read(raw_data)
                return self.connection_settings
            bits = bitstring.ConstBitStream(bytes=raw_data)
            frame_length = bits.read("uint:24")
            frame_type = bits.read("hex:8")
            if frame_type == "04":
                self.connection_settings = SettingsFrame().read(bits)
                return self.connection_settings
            elif frame_type == "01":
                header_frame = HeadersFrame(self.header_encoder, self.header_decoder)
                header_frame.read(bits)
                return header_frame
            elif frame_type == "03":
                rst_frame = RstStreamFrame()
                rst_frame.read(bits)
                return rst_frame
            elif frame_type == "09":
                cont_frame = ContinuationFrame()
                cont_frame.read(bits)
                return cont_frame
            elif frame_type == "00":
                data_frame = DataFrame()
                data_frame.read(bits)
                return data_frame
            elif frame_type == "08":
                window_update_frame = WindowUpdateFrame()
                window_update_frame.read(bits)
                return window_update_frame
            elif frame_type == "06":
                ping_frame = PingFrame()
                ping_frame.read(bits)
                return ping_frame

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