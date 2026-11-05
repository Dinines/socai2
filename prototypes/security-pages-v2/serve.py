"""Loopback-only preview server; no API, credentials, or external dependencies."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from pathlib import Path
from socketserver import TCPServer
import argparse


class LocalPreviewServer(ThreadingHTTPServer):
    def server_bind(self):
        # The preview never needs reverse DNS, which can delay startup on macOS.
        TCPServer.server_bind(self)
        self.server_name = 'localhost'
        self.server_port = self.server_address[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4174)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    with LocalPreviewServer(('127.0.0.1', args.port), handler) as server:
        print(f'Local: http://127.0.0.1:{args.port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
