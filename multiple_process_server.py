import os
import socket
import time
import re
import glob
import zlib

from datetime import datetime
from http_utils.base import get_http_status_text, get_ext_from_mime_type, get_mime_type_from_ext

SERVER_ADDRESS = (HOST, PORT) = '', 8888
REQUEST_QUEUE_SIZE = 5

class Request():
    def __init__(self, raw_request):
        self.headers = dict()
        raw_request_as_array = raw_request.splitlines()
        # print("raw_request = " + raw_request)
        (self.method, self.path, self.http_version) = raw_request_as_array[0].split(' ')
        for line in raw_request_as_array[1:-1]:
            key, value = map(lambda x: x.strip(), line.split(':', 1))
            self.headers[key] = value
    
    def is_get(self):
        return self.method.upper() == "GET"

    def is_post(self):
        return self.method.upper() == "POST"
    
    def is_put(self):
        return self.method.upper() == "PUT"
    
    def is_delete(self):
        return self.method.upper() == "DELETE"

class ContentNegotiator():
    def __init__(self, request):
        self.request = request
        self.file_path = 'static' + request.path
    
    def get_resource(self):
        for content_type, _ in self.prioritize_content_types(self.request.headers['Accept'])[:-1]:
            file_path_with_ext = self.file_path + get_ext_from_mime_type(content_type)
            if os.path.isfile(file_path_with_ext):
                resource = Resource(status="200", file_obj=open(file_path_with_ext))
                resource.set_header({ 'Content-Type': get_mime_type_from_ext( \
                                re.search(r'\.[a-zA-Z]+', file_path_with_ext.group())) + '; charset=utf-8' })
                resource.set_header({ 'Content-Length': os.stat(file_path_with_ext).st_size })
                resource.set_header({ 'Vary': 'Accept, Accept-Encoding' })
        
        # Could not find any specific file to match the mime type, so pick whatever matches the file name.
        wildcard_file_path = glob.glob(os.path.join(self.file_path, "*.*"))[0]
        if wildcard_file_path:
            resource_file_obj = open(wildcard_file_path)
            resource = Resource(status="200", file_obj=resource_file_obj)
            resource.set_header({ 'Content-Type': get_mime_type_from_ext( \
                                re.search(r'\.[a-zA-Z]+', wildcard_file_path).group()) + '; charset=utf-8' })
            resource.set_header({ 'Content-Length': os.stat(wildcard_file_path).st_size })
            resource.set_header({ 'Vary': 'Accept, Accept-Encoding' })
            return resource
        else:
            return Resource(status="406", file_obj=None)

    def normalize_accept_header(self, accept_header):
        """
            Assigns quality factor 0.01 to */* and image/*, text/* etc
            a quality factor of 0.02 and keeps rest of the values the same.
        """
        partial_header_pattern = re.compile(r'\w+\/\*')
        normalized_accept_header = []
        for header in accept_header.split(','):
            content_type, _, q_factor = header.partition(';')
            if q_factor is None or q_factor == "":
                q_factor = 1.0
            if re.match(partial_header_pattern, content_type) and q_factor == "":
                q_factor = 0.02
            if content_type == "*/*":
                q_factor = 0.01
            normalized_accept_header.append((content_type, q_factor))
        return normalized_accept_header

    def prioritize_content_types(self, accept_header):
        return sorted(self.normalize_accept_header(accept_header), key=lambda x: x[1], reverse=True)

class Response():
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
        self.response_str = "HTTP 1.1 / {status_code} {status_text}\n" \
                            .format(status_code=self.resource.status,
                                    status_text=get_http_status_text(self.resource.status))
    
    def set_headers(self):
        self.headers.update({ 'Connection': 'Closed' })
        self.headers.update({ 'Status': self.resource.status })
        self.headers.update({ 'Date': datetime.today().strftime("%a, %d %b %Y %H:%M:%S") })
        self.headers.update({ 'Server': 'Boomerang/1.0.0' })
    
    def set_response_body(self):
        try:
            if 'gz' in self.request.headers.get('Accept-Encoding'):
                z = zlib.compressobj(-1, zlib.DEFLATED, 31)
                self.body = z.compress(self.resource.file_obj) + z.flush()
                self.headers.update({ 'Content-Encoding': 'gzip' })
        except Exception:
            self.body = self.resource.file_obj.read()
    
    def create_final_response(self):
        self.headers.update(self.resource.headers)
        for index, key in enumerate(self.headers):
            self.response_str += "{key}: {value}".format(key=key, value=self.headers[key])
            if index != len(self.headers) - 1:
                self.response_str += "\n"
        self.response_str += "\r\n\n"
        self.response_str += self.body

class Resource():
    def __init__(self, status=None, file_obj=None):
        self.status = status
        self.headers = {}
        self.file_obj = file_obj
    
    def set_header(self, header):
        self.headers.update(header)

def handle_request(client_connection):
    raw_request = client_connection.recv(1024)
    print(
        'Child PID: {pid}. Parent PID {ppid}'.format(
            pid=os.getpid(),
            ppid=os.getppid(),
        )
    )
    print(raw_request.decode())
    request = Request(raw_request)

    if request.method.upper() == "GET":
        content_negotiator = ContentNegotiator(request)
        resource = content_negotiator.get_resource()
        http_response = Response(request, resource)
    elif request.method.upper() == "POST":
        pass
    elif request.method.upper() == "PUT":
        pass
    elif request.method.upper() == "DELETE":
        pass

    client_connection.sendall(http_response.response_str)


def serve_forever():
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(SERVER_ADDRESS)
    listen_socket.listen(REQUEST_QUEUE_SIZE)
    print('Serving HTTP on port {port} ...'.format(port=PORT))
    print('Parent PID (PPID): {pid}\n'.format(pid=os.getpid()))

    while True:
        client_connection, client_address = listen_socket.accept()
        pid = os.fork()
        if pid == 0:  # child
            listen_socket.close()  # close child copy
            handle_request(client_connection)
            client_connection.close()
            os._exit(0)  # child exits here
        else:  # parent
            client_connection.close()  # close parent copy and loop over

if __name__ == '__main__':
    serve_forever()