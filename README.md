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
- run-server
