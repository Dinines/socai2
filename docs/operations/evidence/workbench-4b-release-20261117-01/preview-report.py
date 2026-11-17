"""Temporary loopback-only static rendering for report-link click verification."""
import functools
import http.server
import json
from pathlib import Path

config = json.loads(Path(__file__).with_name('preview-config.json').read_text())
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=config['root'])
http.server.ThreadingHTTPServer((config['host'], config['port']), handler).serve_forever()
