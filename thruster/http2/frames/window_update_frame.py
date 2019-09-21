import bitstring
from .frame import Frame


class WindowUpdateFrame(Frame):
    FRAME_TYPE = "0x08"

    def __init__(self):
        super(WindowUpdateFrame, self).__init__()
        self.window_increment_size = None

    def read_header(self, raw_data):
        super(WindowUpdateFrame, self).read(raw_data)
        
    def read_body(self, raw_data):
        raw_data = bitstring.ConstBitStream(bytes=raw_data)
        raw_data.read("bin:1")
        self.window_increment_size = raw_data.read("uint:31")

    def write(self, window_increment_size):
        if self.window_increment_size is None:
            self.window_increment_size = window_increment_size
        encoded_flags = "0 0 0 0 0 0 0 0".split(" ")
        frame_header_format = super(WindowUpdateFrame, self).frame_header_packing_format()
        frame_format = frame_header_format + "," + self._frame_body_packing_format()

        frame_data = super(WindowUpdateFrame, self).write(
            WindowUpdateFrame.FRAME_TYPE, 8, encoded_flags, 0
        )
        frame_data.update({ "reserved_bit": '1', "window_increment_size": self.window_increment_size})
        return bitstring.pack(frame_format, **frame_data)
    
    def _frame_body_packing_format(self):
        return "bin:1=reserved_bit, uint:31=window_increment_size"