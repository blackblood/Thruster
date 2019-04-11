import sys
import bitstring

from frame import Frame

class DataFrame(Frame):
    FRAME_TYPE='0x00'

    def __init__(self, settings):
        self.connection_settings = settings
        self.end_stream = None
        self.padded = None
        self.response_body = ""
    
    def read(self):
        pass
    
    def write(self, flags={}, padding_length=0, response_body=""):
        encoded_flags = "0 0 0 0 0 0 0 0".split(" ")
        self.end_stream = encoded_flags[7] = int(flags["end_stream"])
        self.padded = encoded_flags[4] = int(flags["padded"])
        self.response_body = response_body
        frame_header_format = super(DataFrame, self).frame_header_packing_format()
        frame_format = frame_header_format + "," + self._frame_body_packing_format()

        frame_data = super(DataFrame, self).write(
            DataFrame.FRAME_TYPE,
            len(response_body) + self._frame_metadata_length(),
            encoded_flags,
            1
        )

        if self.padded:
            frame_data.update({'padding_length': 0})
        frame_data.update({'response_payload': response_body})
        return bitstring.pack(frame_format, **frame_data)

    def _frame_body_packing_format(self):
        frame_body_format = ""
        if self.padded:
            frame_body_format += "uint:8=padding_length"
        frame_body_format += "bytes=response_payload"
        return frame_body_format
    
    def _frame_metadata_length(self):
        return 1 if self.padded else 0