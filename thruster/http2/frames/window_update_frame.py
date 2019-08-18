import bitstring
from .frame import Frame


class WindowUpdateFrame(Frame):
    FRAME_TYPE = "0x08"

    def __init__(self):
        super(WindowUpdateFrame, self).__init__()
        self.window_increment_size = 0

    def read_header(self, raw_data):
        super(WindowUpdateFrame, self).read(raw_data)
        
    def read_body(self, raw_data):
        raw_data = bitstring.ConstBitStream(bytes=raw_data)
        raw_data.read("bin:1")
        self.window_increment_size = raw_data.read("uint:31")

    def write(self):
        pass
