import bitstring
from .frame import Frame


class GoAwayFrame(Frame):
    FRAME_TYPE = "0x07"
    PROTOCOL_ERROR = 0x1

    def __init__(self):
        super(GoAwayFrame, self).__init__()

    def read(self, raw_data):
        pass

    def write(self, error_code, last_stream_id):
        frame_header_format = super(GoAwayFrame, self).frame_header_packing_format()
        frame_format = frame_header_format + "," + self._frame_body_packing_format()
        frame_data = super(GoAwayFrame, self).write(GoAwayFrame.FRAME_TYPE, 64, "", 0)
        frame_data.update(
            {"reserved": 1, "last_stream_id": last_stream_id, "error_code": error_code}
        )
        return bitstring.pack(frame_format, **frame_data)

    def _frame_body_packing_format(self):
        return "bin:1=reserved,uint:31=last_stream_id,uint:32=error_code"

    def connection_error_frame(self, last_stream_id):
        return GoAwayFrame().write(GoAwayFrame.PROTOCOL_ERROR, last_stream_id)
