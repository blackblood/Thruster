import os
import glob
import re
from http.resource import Resource
from http_utils.base import get_ext_from_mime_type, get_mime_type_from_ext


class ContentNegotiator:
    def __init__(self, request):
        self.request = request
        self.file_path = "static" + request.path

    def get_resource(self):
        for content_type, _ in self.prioritize_content_types(
            self.request.headers["Accept"]
        )[:-1]:
            file_path_with_ext = self.file_path + get_ext_from_mime_type(content_type)
            if os.path.isfile(file_path_with_ext):
                resource = Resource(status="200", file_obj=open(file_path_with_ext))
                resource.set_header(
                    {
                        "Content-Type": get_mime_type_from_ext(
                            re.search(r"\.[a-zA-Z]+", file_path_with_ext.group())
                        )
                        + "; charset=utf-8"
                    }
                )
                resource.set_header(
                    {"Content-Length": os.stat(file_path_with_ext).st_size}
                )
                resource.set_header({"Vary": "Accept, Accept-Encoding"})

        # Could not find any specific file to match the mime type, so pick whatever matches the file name.
        wildcard_file_path = glob.glob(os.path.join(self.file_path, "*.*"))[0]
        if wildcard_file_path:
            resource_file_obj = open(wildcard_file_path)
            resource = Resource(status="200", file_obj=resource_file_obj)
            resource.set_header(
                {
                    "Content-Type": get_mime_type_from_ext(
                        re.search(r"\.[a-zA-Z]+", wildcard_file_path).group()
                    )
                    + "; charset=utf-8"
                }
            )
            resource.set_header({"Content-Length": os.stat(wildcard_file_path).st_size})
            resource.set_header({"Vary": "Accept, Accept-Encoding"})
            return resource
        else:
            return Resource(status="406", file_obj=None)

    def normalize_accept_header(self, accept_header):
        """
            Assigns quality factor 0.01 to */* and image/*, text/* etc
            a quality factor of 0.02 and keeps rest of the values the same.
        """
        partial_header_pattern = re.compile(r"\w+\/\*")
        normalized_accept_header = []
        for header in accept_header.split(","):
            content_type, _, q_factor = header.partition(";")
            if q_factor is None or q_factor == "":
                q_factor = 1.0
            if re.match(partial_header_pattern, content_type) and q_factor == "":
                q_factor = 0.02
            if content_type == "*/*":
                q_factor = 0.01
            normalized_accept_header.append((content_type, q_factor))
        return normalized_accept_header

    def prioritize_content_types(self, accept_header):
        return sorted(
            self.normalize_accept_header(accept_header),
            key=lambda x: x[1],
            reverse=True,
        )
