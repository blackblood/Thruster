import sys
import bitstring
import binascii
from frame import Frame
from hpack import Encoder, Decoder

class HeadersFrame(Frame):
    FRAME_TYPE='0x01'

    def __init__(self, connection_settings, encoder, decoder):
        self.connection_settings = connection_settings
        self.encoder = encoder
        self.decoder = decoder

    def read(self, raw_data, padding_length=0, exclusive=False, stream_id='0x0'):
        Frame.__init__(self, raw_data)
        self.end_stream = self.frame_flags[7]
        self.end_headers = self.frame_flags[5]
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
        self.header_block_fragment = self.decoder.decode(raw_data.read(frame_body_offset - (self.padding_length * 8)).bytes)
        
        self.headers = {}
        for header_field in self.header_block_fragment:
            self.headers[header_field[0]] = header_field[1]
        return self

    def get_method(self):
        return self.headers[":method"]
    
    def get_path(self):
        return self.headers[":path"]
    
    def write(self, flags={}, padding_length=0, exclusive=1, stream_dependency=0, priority_weight=255, headers={}):
        encoded_flags = "0 0 0 0 0 0 0 0".split(" ")
        self.end_stream = encoded_flags[7] = int(flags["end_stream"])
        self.end_headers = encoded_flags[5] = int(flags["end_headers"])
        self.padded = encoded_flags[4] = int(flags["padded"])
        self.priority = encoded_flags[2] = int(flags["priority"])
        self.header_block_fragment = self.encoder.encode(headers)
        self.frame_length = len(self.header_block_fragment)
        frame_header_format = super(HeadersFrame, self).frame_header_packing_format()
        frame_format = frame_header_format + "," + self._frame_body_packing_format()

        frame_data = {
            'frame_type': HeadersFrame.FRAME_TYPE,
            'reserved_bit': '1',
            'frame_length': self.frame_length,
            'flags': "".join(map(lambda x: str(x), encoded_flags)),
            'stream_id': 1,
        }
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
            self.frame_length += 1
        
        if self.priority:
            frame_body_format += "bin:1=exclusive,"
            frame_body_format += "uint:31=stream_dependency,"
            frame_body_format += "uint:8=weight,"
            self.frame_length += 5 
        frame_body_format += "bytes=header_block_fragment"

        return frame_body_format