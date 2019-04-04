from frame import Frame
import bitstring

class SettingsFrame(Frame):
	FRAME_TYPE='0x04'
	SETTINGS_HEADER_TABLE_SIZE=1
	SETTINGS_ENABLE_PUSH=2
	SETTINGS_MAX_CONCURRENT_STREAMS=3
	SETTINGS_INITIAL_WINDOW_SIZE=4
	SETTINGS_MAX_FRAME_SIZE=5
	SETTINGS_MAX_HEADER_LIST_SIZE=6

	def __init__(self):
		self.values = {}

	def read(self, raw_data):
		if raw_data:
			super(SettingsFrame, self).read(raw_data)
			self.values = {}
			identifier_length = 16
			value_length = 32
			for _ in range(0, self.frame_length, identifier_length + value_length):
				settings_identifier = raw_data.read("uint:%d" % identifier_length)
				settings_value = raw_data.read("uint:%d" % value_length)

				if settings_identifier == self.SETTINGS_HEADER_TABLE_SIZE:
					self.values["SETTINGS_HEADER_TABLE_SIZE"] = settings_value
				elif settings_identifier == self.SETTINGS_ENABLE_PUSH:
					self.values["SETTINGS_ENABLE_PUSH"] = settings_value
				elif settings_identifier == self.SETTINGS_MAX_CONCURRENT_STREAMS:
					self.values["SETTINGS_MAX_CONCURRENT_STREAMS"] = settings_value
				elif settings_identifier == self.SETTINGS_INITIAL_WINDOW_SIZE:
					self.values["SETTINGS_INITIAL_WINDOW_SIZE"] = settings_value
				elif settings_identifier == self.SETTINGS_MAX_FRAME_SIZE:
					self.values["SETTINGS_MAX_FRAME_SIZE"] = settings_value
				elif settings_identifier == self.SETTINGS_MAX_HEADER_LIST_SIZE:
					self.values["SETTINGS_MAX_HEADER_LIST_SIZE"] = settings_value
				else:
					raise ValueError("Unknown Settings Identifier.")
	
	def write(self, flags={}):
		encoded_flags = "0 0 0 0 0 0 0 0".split(" ")
		self.ack = encoded_flags[0] = int(flags["ack"])
		frame_format = super(SettingsFrame, self).frame_header_packing_format()
		frame_data = super(SettingsFrame, self).write(SettingsFrame.FRAME_TYPE, 0, encoded_flags, 0)
		return bitstring.pack(frame_format, **frame_data)

	@staticmethod
	def get_acknowledgement_frame():
		return SettingsFrame.write(flags={'ack': '1'})
	
	