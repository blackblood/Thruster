from bitstring import ConstBitStream, BitStream
from .abstract_frame import AbstractFrame


class Frame(AbstractFrame):
    def __init__(self):
        self.frame_type = None
        self.frame_length = 0
        self.encoded_flags = None
        self.reserved_bit = 1
        self.stream_id = 1

    def read(self, raw_data):
        # Ideally this class should not be dependent on a particular library implementation like bitstring.
        if type(raw_data) not in [ConstBitStream, BitStream]:
            raise ValueError(
                "Expected bitstring.ConstBitStream object, found: %s" % repr(raw_data)
            )

        raw_data.pos = 0
        self.frame_length = raw_data.read("uint:24")
        self.frame_type = raw_data.read("hex:8")
        self.frame_flags = raw_data.read("bin:8")
        self.reserved_bit = raw_data.read("bin:1")
        self.stream_id = raw_data.read("uint:31")

    def write(self, frame_type, frame_length, encoded_flags, stream_id):
        self.encoded_flags = "".join([str(x) for x in encoded_flags])
        self.frame_type = frame_type
        self.frame_length = frame_length
        self.reserved_bit = 1
        self.stream_id = stream_id

        return {
            "frame_type": self.frame_type,
            "reserved_bit": str(self.reserved_bit),
            "frame_length": self.frame_length,
            "flags": self.encoded_flags,
            "stream_id": self.stream_id,
        }

    @staticmethod
    def frame_header_packing_format():
        return "uint:24=frame_length, hex:8=frame_type, bin:8=flags, bin:1=reserved_bit, uint:31=stream_id"
