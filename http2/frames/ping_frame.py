import bitstring
from .frame import Frame

class PingFrame(Frame):
    FRAME_TYPE="0x06"

    def __init__(self):
        self.ack = None
        self.body = None
    
    def read_header(self, raw_data):
        super(PingFrame, self).read(raw_data)
        self.ack = int(self.frame_flags[7])
        
    def read_body(self, raw_data):
        raw_data = bitstring.ConstBitStream(bytes=raw_data)
        self.body = raw_data.read(64).bytes
    
    def write(self, ack=1):
        encoded_flags = "0 0 0 0 0 0 0 0".split(" ")
        self.ack = encoded_flags[7] = ack
        frame_header_format = super(PingFrame, self).frame_header_packing_format()
        frame_format = frame_header_format + "," + self._frame_body_packing_format()

        frame_data = super(PingFrame, self).write(
            PingFrame.FRAME_TYPE, 8, encoded_flags, 0
        )
        frame_data.update({"body": self.body})
        return bitstring.pack(frame_format, **frame_data)
    
    def _frame_body_packing_format(self):
        return "bytes=body"