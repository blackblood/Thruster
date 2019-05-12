class Resource:
    def __init__(self, status=None, file_obj=None):
        self.status = status
        self.headers = {}
        self.file_obj = file_obj

    def set_header(self, header):
        self.headers.update(header)
