from bitstring import ConstBitStream

class Frame():
	def __init__(self, raw_data):
		# Ideally this class should not be dependent on a particular library implementation like bitstring.
		if type(raw_data) != ConstBitStream:
			raise ValueError("Expected bitstring.ConstBitStream object, found: %s" % repr(raw_data))
		
		raw_data.pos = 0
		self.frame_length = raw_data.read("uint:24")
		self.frame_type = raw_data.read("hex:8")
		self.frame_flags = raw_data.read("bin:8")
		raw_data.read("bin:1")
		self.stream_id = raw_data.read("uint:31")