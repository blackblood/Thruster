from http2.frames.frame import Frame
import bitstring


class ContinuationFrame(Frame):
    FRAME_TYPE = "0x09"

    def __init__(self, encoder, decoder):
        self.header_block_fragment = None
        self.headers = {}
        self.end_headers = None
        self.encoder = encoder
        self.decoder = decoder

    def read_header(self, raw_data):
        super(ContinuationFrame, self).read(raw_data)
        self.end_headers = self.frame_flags[5]
    
    def read_body(self, raw_data):
        self.header_block_fragment = self.decoder.decode(raw_data)
        for header_field in self.header_block_fragment:
            self.headers[header_field[0]] = header_field[1]

    def write(self, stream_id, header_block_fragment=None, flags={}):
        encoded_flags = "0 0 0 0 0 0 0 0".split(" ")
        self.end_headers = encoded_flags[6] = flags["end_headers"]
        self.header_block_fragment = header_block_fragment
        frame_header_format = super(
            ContinuationFrame, self
        ).frame_header_packing_format()
        frame_format = frame_header_format + "," + self._frame_body_packing_format()
        frame_data = super(ContinuationFrame, self).write(
            ContinuationFrame.FRAME_TYPE,
            len(self.header_block_fragment),
            encoded_flags,
            stream_id,
        )
        frame_data.update({"header_block_fragment": self.header_block_fragment})
        return bitstring.pack(frame_format, **frame_data)

    def _frame_body_packing_format(self):
        return "bytes=header_block_fragment"
