from http2.frames.frame import Frame
import bitstring

class ContinuationFrame(Frame):
    FRAME_TYPE="0x09"

    def __init__(self):
        self.header_block_fragment = None
    
    def read(self):
        pass
    
    def write(self, header_block_fragment=None, flags={}):
        encoded_flags = "0 0 0 0 0 0 0 0".split(" ")
        self.end_headers = encoded_flags[6] = flags['end_headers']
        self.header_block_fragment = header_block_fragment
        frame_header_format = super(ContinuationFrame, self).frame_header_packing_format()
        frame_format = frame_header_format + "," + self._frame_body_packing_format()
        frame_data = super(ContinuationFrame, self).write(
            ContinuationFrame.FRAME_TYPE,
            len(self.header_block_fragment),
            encoded_flags,
            1
        )
        frame_data.update({"header_block_fragment": self.header_block_fragment})
        return bitstring.pack(frame_format, **frame_data)
    
    def _frame_body_packing_format(self):
        return "bytes=header_block_fragment"