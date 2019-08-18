import sys
import bitstring
from .frame import Frame
from hpack import Encoder, Decoder


class HeadersFrame(Frame):
    FRAME_TYPE = "0x01"

    def __init__(self, encoder, decoder):
        super(HeadersFrame, self).__init__()
        self.encoder = encoder
        self.decoder = decoder
        self.end_stream = None
        self.end_headers = None
        self.padded = None
        self.priority = None
        self.padding_length = 0
        self.exclusive = None
        self.stream_dependency = None
        self.priority_weight = None
        self.headers = {}
        self.header_block_fragment = None

    def read_header(self, raw_data):
        super(HeadersFrame, self).read(raw_data)
        self.end_stream = int(self.frame_flags[7])
        self.end_headers = int(self.frame_flags[5])
        self.padded = int(self.frame_flags[4])
        self.priority = int(self.frame_flags[2])

    def read_body(self, raw_data):
        bits = bitstring.ConstBitStream(bytes=raw_data)
        self.padding_length = bits.read("uint:8") if self.padded else 0
        self.exclusive = int(bits.read("bin:1")) if self.priority else None
        self.stream_dependency = bits.read("uint:31") if self.priority else None
        self.priority_weight = bits.read("uint:8") if self.priority else None
        frame_body_offset = self.frame_length * 8
        if self.priority:
            frame_body_offset -= 40
        if self.padded:
            frame_body_offset -= 8
        self.header_block_fragment = self.decoder.decode(
            bits.read(frame_body_offset - (self.padding_length * 8)).bytes
        )
        self.headers = {}
        for header_field in self.header_block_fragment:
            self.headers[header_field[0]] = header_field[1]

    def read(self, raw_data, padding_length=0, exclusive=False, stream_id="0x0"):
        super(HeadersFrame, self).read(raw_data)
        self.end_stream = int(self.frame_flags[7])
        self.end_headers = int(self.frame_flags[5])
        self.padded = int(self.frame_flags[4])
        self.priority = int(self.frame_flags[2])
        self.padding_length = raw_data.read("uint:8") if self.padded else 0
        self.exclusive = int(raw_data.read("bin:1")) if self.priority else None
        self.stream_dependency = raw_data.read("uint:31") if self.priority else None
        self.priority_weight = raw_data.read("uint:8") if self.priority else None
        # Frame body starts from here
        frame_body_offset = self.frame_length * 8
        if self.priority:
            frame_body_offset -= 40
        if self.padded:
            frame_body_offset -= 8
        self.header_block_fragment = self.decoder.decode(
            raw_data.read(frame_body_offset - (self.padding_length * 8)).bytes
        )

        self.headers = {}
        for header_field in self.header_block_fragment:
            self.headers[header_field[0]] = header_field[1]
        return self

    def get_method(self):
        return self.headers[":method"]

    def get_path(self):
        return self.headers[":path"]

    @staticmethod
    def normalize_header_fields(headers):
        return {k.lower(): v for k, v in list(headers.items())}

    def write(
        self,
        stream_id,
        flags={},
        padding_length=0,
        exclusive=1,
        stream_dependency=0,
        priority_weight=255,
        headers={},
        headers_block_fragment=None,
    ):
        encoded_flags = "0 0 0 0 0 0 0 0".split(" ")
        self.end_stream = encoded_flags[7] = int(flags["end_stream"])
        self.end_headers = encoded_flags[5] = int(flags["end_headers"])
        self.padded = encoded_flags[4] = int(flags["padded"])
        if self.padded and padding_length <= 0:
            raise ValueError("if padded flag is set, padding_length cannot be 0.")
        self.priority = encoded_flags[2] = int(flags["priority"])
        if headers and headers_block_fragment:
            raise ValueError("Pass only one of headers or header_block_fragment")
        if headers:
            self.headers = HeadersFrame.normalize_header_fields(headers)
            self.header_block_fragment = self.encoder.encode(self.headers)
        elif headers_block_fragment:
            self.header_block_fragment = headers_block_fragment
        else:
            raise ValueError("Pass headers or header_block_fragment")

        frame_header_format = super(HeadersFrame, self).frame_header_packing_format()
        frame_format = frame_header_format + "," + self._frame_body_packing_format()
        frame_data = super(HeadersFrame, self).write(
            HeadersFrame.FRAME_TYPE,
            len(self.header_block_fragment) + self._frame_metadata_length(),
            encoded_flags,
            stream_id,
        )

        if self.padded:
            frame_data.update({"padding_length": 0})

        if self.priority:
            frame_data.update({"exclusive": str(exclusive)})
            frame_data.update({"stream_dependency": stream_dependency})
            frame_data.update({"weight": priority_weight})

        frame_data.update({"header_block_fragment": self.header_block_fragment})
        return bitstring.pack(frame_format, **frame_data)

    def _frame_body_packing_format(self):
        frame_body_format = ""
        if self.padded:
            frame_body_format += "uint:8=padding_length,"

        if self.priority:
            frame_body_format += "bin:1=exclusive,"
            frame_body_format += "uint:31=stream_dependency,"
            frame_body_format += "uint:8=weight,"
        frame_body_format += "bytes=header_block_fragment"

        return frame_body_format

    def _frame_metadata_length(self):
        length = 0
        if self.padded:
            length += 1
        if self.priority:
            length += 5
        return length
