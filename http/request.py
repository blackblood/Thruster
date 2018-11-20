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