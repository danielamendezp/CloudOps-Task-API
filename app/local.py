"""Loopback-only development server; Docker enables its internal bind explicitly."""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit
os.environ['LOCAL_MODE'] = 'true'
from app.handler import handler

class Adapter(BaseHTTPRequestHandler):
    def dispatch(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 <= length <= 16384:
                self.send_error(413)
                return
            raw = self.rfile.read(length).decode('utf-8')
        except (ValueError, UnicodeError):
            self.send_error(400)
            return
        url = urlsplit(self.path)
        result = handler({'rawPath': url.path, 'rawQueryString': url.query,
                          'requestContext': {'http': {'method': self.command}}, 'body': raw}, None)
        payload = result['body'].encode()
        self.send_response(result['statusCode'])
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
    do_GET = dispatch
    do_POST = dispatch
    do_PATCH = dispatch

if __name__ == '__main__':
    HTTPServer((os.environ.get('BIND_HOST', '127.0.0.1'), int(os.environ.get('PORT', '8080'))), Adapter).serve_forever()
