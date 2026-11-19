"""Bounded local HTTP adapter; no external requests or trade execution."""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from strategy import LiquidityBot

BOT = LiquidityBot()
LOCK = threading.Lock()

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/decide':
            self.send_error(404)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 131072:
                self.send_error(413)
                return
            self.connection.settimeout(1)
            obs = json.loads(self.rfile.read(length))
            if not isinstance(obs, dict):
                raise ValueError('object required')
            with LOCK:
                answer = BOT.decide(obs)
            body = json.dumps(answer, allow_nan=False).encode()
        except (ValueError, TypeError, TimeoutError):
            self.send_error(400)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8097)
    args = p.parse_args()
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
