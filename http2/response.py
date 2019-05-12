import zlib
from datetime import datetime
from http_utils.base import get_http_status_text


class Response:
    def __init__(self, request, resource):
        self.request = request
        self.resource = resource
        self.response_str = ""
        self.headers = {}
        self.body = ""
        self.set_http_status()
        self.set_headers()
        self.set_response_body()
        self.create_final_response()

    def set_http_status(self):
        self.response_str = "HTTP 1.1 / {status_code} {status_text}\n".format(
            status_code=self.resource.status,
            status_text=get_http_status_text(self.resource.status),
        )

    def set_headers(self):
        self.headers.update({"Connection": "Closed"})
        self.headers.update({"Status": self.resource.status})
        self.headers.update(
            {"Date": datetime.today().strftime("%a, %d %b %Y %H:%M:%S")}
        )
        self.headers.update({"Server": "Boomerang/1.0.0"})

    def set_response_body(self):
        try:
            if "gz" in self.request.headers.get("Accept-Encoding"):
                z = zlib.compressobj(-1, zlib.DEFLATED, 31)
                self.body = z.compress(self.resource.file_obj) + z.flush()
                self.headers.update({"Content-Encoding": "gzip"})
        except Exception:
            self.body = self.resource.file_obj.read()

    def create_final_response(self):
        self.headers.update(self.resource.headers)
        for index, key in enumerate(self.headers):
            self.response_str += "{key}: {value}".format(
                key=key, value=self.headers[key]
            )
            if index != len(self.headers) - 1:
                self.response_str += "\n"
        self.response_str += "\r\n\n"
        self.response_str += self.body
