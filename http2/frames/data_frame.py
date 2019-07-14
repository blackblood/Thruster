import sys
import bitstring

from .frame import Frame


class DataFrame(Frame):
    FRAME_TYPE = "0x00"

    def __init__(self):
        self.end_stream = None
        self.padded = None
        self.body = ""

    def read_header(self, raw_data):
        super(DataFrame, self).read(raw_data)
        self.end_stream = int(self.frame_flags[7])
        self.padded = int(self.frame_flags[4])
    
    def read_body(self, raw_data):
        raw_data = bitstring.ConstBitStream(bytes=raw_data)
        if self.padded:
            self.padding_length = raw_data.read("uint:8")
            self.body = raw_data.read(self.frame_length - 1 - self.padding_length).bytes
        else:
            self.body = raw_data.read(self.frame_length * 8).bytes

    def write(self, stream_id, flags={}, padding_length=0, body=""):
        encoded_flags = "0 0 0 0 0 0 0 0".split(" ")
        self.end_stream = encoded_flags[7] = int(flags["end_stream"])
        self.padded = encoded_flags[4] = int(flags["padded"])
        self.body = body
        frame_header_format = super(DataFrame, self).frame_header_packing_format()
        frame_format = frame_header_format + "," + self._frame_body_packing_format()

        frame_data = super(DataFrame, self).write(
            DataFrame.FRAME_TYPE,
            len(self.body) + self._frame_metadata_length(),
            encoded_flags,
            stream_id,
        )

        if self.padded:
            frame_data.update({"padding_length": 0})
        frame_data.update({"response_payload": self.body})
        return bitstring.pack(frame_format, **frame_data)

    def _frame_body_packing_format(self):
        frame_body_format = ""
        if self.padded:
            frame_body_format += "uint:8=padding_length"
        frame_body_format += "bytes=response_payload"
        return frame_body_format

    def _frame_metadata_length(self):
        return 1 if self.padded else 0
