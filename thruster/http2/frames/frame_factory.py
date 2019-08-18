import bitstring
from http2.frames.settings_frame import SettingsFrame
from http2.frames.headers_frame import HeadersFrame
from http2.frames.continuation_frame import ContinuationFrame
from http2.frames.data_frame import DataFrame
from http2.frames.rst_frame import RstStreamFrame
from http2.frames.window_update_frame import WindowUpdateFrame
from http2.frames.ping_frame import PingFrame
from http2.frames.goaway_frame import GoAwayFrame

class FrameFactory(object):
    def __init__(self):
        pass

    @staticmethod
    def read_frame(raw_data, header_encoder, header_decoder):
        bits = bitstring.ConstBitStream(bytes=raw_data)
        frame_length = bits.read("uint:24")
        frame_type = bits.read("hex:8")
        
        if frame_type == "04":
            frame = SettingsFrame()
        elif frame_type == "01":
            frame = HeadersFrame(header_encoder, header_decoder)
        elif frame_type == "03":
            frame = RstStreamFrame()
        elif frame_type == "09":
            frame = ContinuationFrame()
        elif frame_type == "00":
            frame = DataFrame()
        elif frame_type == "08":
            frame = WindowUpdateFrame()
        elif frame_type == "06":
            frame = PingFrame()
        elif frame_type == "07":
            frame = GoAwayFrame()
        
        frame.read_header(bits)
        return frame