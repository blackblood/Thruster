import sys
import binascii
import bitstring

from frame import Frame

class DataFrame(Frame):
    FRAME_TYPE='0x00'

    def __init__(self):
        pass
    
    def read(self):
        pass
    
    def write(self, flags={}, padding_length=0, response_body=""):
        encoded_flags = "0 0 0 0 0 0 0 0".split(" ")
        self.end_stream = encoded_flags[7] = int(flags["end_stream"])
        self.padded = encoded_flags[4] = int(flags["padded"])
        frame_header_format = super(DataFrame, self).frame_header_packing_format()
        frame_format = frame_header_format + "," + self._frame_body_packing_format()
        bin_encoded_body = bin(int(binascii.hexlify(response_body), 16))
        frame_length = sys.getsizeof(bin_encoded_body)
        
        frame_data = {
            'frame_type': DataFrame.FRAME_TYPE,
            'reserved_bit': '1',
            'frame_length': frame_length,
            'flags': "".join(map(lambda x: str(x), encoded_flags)),
            'stream_id': 1
        }

        if self.padded:
            frame_data.update({'padding_length': 0})
        frame_data.update({'response_payload': bin_encoded_body})
        return bitstring.pack(frame_format, **frame_data)

    def _frame_body_packing_format(self):
        frame_body_format = ""
        if self.padded:
            frame_body_format += "uint:8=padding_length"
            self.frame_length += 8
        frame_body_format += "bin=response_payload"
        return frame_body_format