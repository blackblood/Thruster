from http2.frames.frame import Frame
import bitstring


class RstStreamFrame(Frame):
    FRAME_TYPE = "0x03"
    NO_ERROR = 0
    PROTOCOL_ERROR = 1
    INTERNAL_ERROR = 2
    FLOW_CONTROL_ERROR = 3
    SETTINGS_TIMEOUT = 4
    STREAM_CLOSED = 5
    FRAME_SIZE_ERROR = 6
    REFUSED_STREAM = 7
    CANCEL = 8
    COMPRESSION_ERROR = 9
    CONNECT_ERROR = "a"
    ENHANCE_YOUR_CALM = "b"
    INADEQUATE_SECURITY = "c"
    HTTP_1_1_REQUIRED = "d"

    def __init__(self):
        self.error_code = None
        self.description_dict = {
            RstStreamFrame.NO_ERROR: "NO ERROR",
            RstStreamFrame.PROTOCOL_ERROR: "PROTOCOL ERROR",
            RstStreamFrame.INTERNAL_ERROR: "INTERNAL ERROR",
            RstStreamFrame.FLOW_CONTROL_ERROR: "FLOW CONTROL ERROR",
            RstStreamFrame.SETTINGS_TIMEOUT: "SETTINGS TIMEOUT",
            RstStreamFrame.STREAM_CLOSED: "STREAM CLOSED",
            RstStreamFrame.FRAME_SIZE_ERROR: "FRAME SIZE ERROR",
            RstStreamFrame.REFUSED_STREAM: "REFUSED STREAM",
            RstStreamFrame.CANCEL: "CANCEL",
            RstStreamFrame.COMPRESSION_ERROR: "COMPRESSION ERROR",
            RstStreamFrame.CONNECT_ERROR: "CONNECT ERROR",
            RstStreamFrame.ENHANCE_YOUR_CALM: "ENHANCE YOUR CALM",
            RstStreamFrame.INADEQUATE_SECURITY: "INADEQUATE SECURITY",
            RstStreamFrame.HTTP_1_1_REQUIRED: "HTTP 1.1 REQUIRED",
        }

    def read_header(self, raw_data):
        super(RstStreamFrame, self).read(raw_data)
    
    def read_body(self, raw_data):
        bits = bitstring.ConstBitStream(bytes=raw_data)
        self.error_code = bits.read("uint:32")
        self.description = self.description_dict[self.error_code]

    def read(self, raw_data):
        super(RstStreamFrame, self).read(raw_data)
        self.error_code = raw_data.read("uint:32")
        self.description = self.description_dict[self.error_code]
        return self

    def write(self, error_stream_id, error_code):
        frame_header_format = super(RstStreamFrame, self).frame_header_packing_format()
        frame_format = frame_header_format + "," + self._frame_body_packing_format()
        frame_data = super(RstStreamFrame, self).write(RstStreamFrame.FRAME_TYPE, 32, "", error_stream_id)
        frame_data.update(
            {"error_code": error_code}
        )
        return bitstring.pack(frame_format, **frame_data)
