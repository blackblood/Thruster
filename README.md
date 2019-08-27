# Thruster
HTTP/2 Server that just works

This is my attempt at writing a fully functional HTTP 2.0 Server in Python. Its a work in progress right now.
The server supports the ASGI 1.0 specification. Has no dependency on the hyper/h2 (except hpack) and twisted packages.
The HTTP/2 stack is being implemented completely from scratch.
Depends on [bitstring](https://pythonhosted.org/bitstring/) for handling binary data for the HTTP/2 protocol implementation.

## HTTP/2 (Current Status)
- Implementation of most HTTP/2 frames is done. Implemenation of rest of the frames will be done as use cases arise.
- All frames are organized in classes, with the Frame class as the parent.
- ASGI 1.0 is supported. Will be adding support for 2.0 soon.
- Flow Control (To be added)
- Stream prioritization (To be added)
- Works with Django (Tested against Django 1.11 and 2.2)

## Usage
Install the package using pip
- pip3 install thruster

Run the following command:
- thruster --app path_to_your_asgi_app --cert-file path_to_certificate_file --key-file path_to_key_file
- eg: thruster --app mysite --cert-file server_cert.crt --key-file server_key.key

--cert-file is expected to be a .crt file and --key-file is expected to be a .key file. If --cert-file and --key-file options are not passed, thruster will look for server.crt and server.key in the current directory.
--cert-file and --key-file are required for SSL connections and HTTP2 only works with SSL. You can use --help to know about for more options.
If everything goes fine you should see the following output on the terminal.

Serving HTTP on port 8000 ...

The structure of your ASGI application is expected to be something like this. Eg: If you're using django.

root_directory/
	asgi.py
	routing.py
	settings.py
	
asgi.py

```python
import os
import django
from channels.routing import get_default_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()
application = get_default_application()
```

routing.py
```python
from channels.routing import ProtocolTypeRouter

application = ProtocolTypeRouter({})
```

settings.py
```python
ASGI_APPLICATION = 'mysite.routing.application'
```
