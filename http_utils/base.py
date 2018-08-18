def get_http_status_text(status_code):
    status_code_text_mapping = {
        '200': 'OK',
        '201': 'CREATED',
        '202': 'ACCEPTED',
        '404': 'NOT FOUND',
        '406': 'NOT ACCEPTABLE'
    }
    return status_code_text_mapping[status_code]

def get_ext_from_mime_type(mime_type):
    mime_type_ext_mapping = {
        'text/plain': '.txt',
        'text/html': '.html',
        'text/css': '.css',
        'text/javascript': '.js',
        'image/png': '.png',
        'image/jpg': '.jpg',
        'application/xml': '.xml',
        'application/xhtml+xml': '.xhtml',
        'image/webp': '.webp',
        'image/apng': '.apng'
    }
    return mime_type_ext_mapping[mime_type]

def get_mime_type_from_ext(ext):
    ext_mime_type_mapping = {
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'text/javascript',
        '.png': 'image/png',
        '.jpg': 'image/jpg',
        '.xml': 'application/xml',
        '.xhtml': 'application/xhtml+xml',
        '.webp': 'image/webp',
        '.apng': 'image/apng'
    }
    return ext_mime_type_mapping[ext]