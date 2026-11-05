"""Temporary localhost static page + SSH relay; no user API Key in this process.

The browser uses the public marker `local-acceptance`, not a credential. A fresh
relay nonce stays in the two Python processes and is never printed or saved.
Ctrl-C or the TTL closes both proxy and tunnel. This script does not deploy.
"""
import argparse
import json
import mimetypes
import secrets
import shlex
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "prototypes/security-pages-v2"
REMOTE = "/opt/sting-aisoc-socai2/evidence/next-repair-k5-20261105/repair_page_proxy_20261105.py"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=8"]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["deepseek", "small"], required=True)
    parser.add_argument("--ttl-seconds", type=int, default=900)
    parser.add_argument("--read-only", action="store_true")
    args = parser.parse_args()
    assert 60 <= args.ttl_seconds <= 900
    nonce = secrets.token_urlsafe(40)
    process, tunnel, server = None, None, None
    try:
        remote_command = ["python3", REMOTE, "--backend", args.backend] + (["--read-only"] if args.read_only else [])
        process = subprocess.Popen(SSH + ["sting-infra21", shlex.join(remote_command)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        process.stdin.write(json.dumps({"session_nonce": nonce, "ttl_seconds": args.ttl_seconds}) + "\n")
        process.stdin.flush()
        # A bounded startup wait: do not leave the UI waiting indefinitely.
        import selectors
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout=45):
                raise RuntimeError("remote bridge did not become ready")
        ready = json.loads(process.stdout.readline())
        assert ready.get("ready") is True
        port = free_port()
        tunnel = subprocess.Popen(SSH + ["-o", "ExitOnForwardFailure=yes", "-N", "-L",
            f"127.0.0.1:{port}:127.0.0.1:{int(ready['remote_port'])}", "sting-infra21"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        until = time.monotonic() + 10
        while True:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.2):
                    break
            except OSError:
                if time.monotonic() > until or tunnel.poll() is not None:
                    raise RuntimeError("page bridge tunnel did not become ready")
                time.sleep(.1)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *values):
                return

            def setup(self):
                super().setup()
                self.connection.settimeout(10)

            def respond(self, code, body, content_type="application/json"):
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "same-origin")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)

            def dispatch(self):
                origin = f"http://127.0.0.1:{self.server.server_port}"
                if self.headers.get("Host") != urlsplit(origin).netloc:
                    return self.respond(403, b'{"detail":"bridge_host_denied"}')
                if self.path.startswith("/api/"):
                    site, referer = self.headers.get("Sec-Fetch-Site"), self.headers.get("Referer", "")
                    accepted_origin = self.headers.get("Origin") in {None, origin}
                    if (site != "same-origin" or not referer.startswith(origin + "/") or not accepted_origin
                            or self.headers.get("Authorization") != "Bearer local-acceptance"
                            or (self.command != "GET" and self.headers.get("Origin") != origin)):
                        return self.respond(403, b'{"detail":"bridge_origin_denied"}')
                    body = None
                    if self.command in {"POST", "PUT"}:
                        size = self.headers.get("Content-Length", "")
                        if self.headers.get("Transfer-Encoding") or not size.isdigit() or not 0 < int(size) <= 65536:
                            return self.respond(400, b'{"detail":"bridge_body_denied"}')
                        body = self.rfile.read(int(size))
                    request = urllib.request.Request(f"http://127.0.0.1:{port}" + self.path,
                        data=body, method=self.command, headers={"X-Repair-Session": nonce, "Content-Type": "application/json"})
                    try:
                        with urllib.request.urlopen(request, timeout=25) as response:
                            status, raw = response.status, response.read(8 * 1024 * 1024 + 1)
                    except urllib.error.HTTPError as exc:
                        status, raw = exc.code, exc.read(1024 * 1024)
                    except OSError:
                        return self.respond(503, b'{"detail":"bridge_closed_or_upstream_unknown"}')
                    if len(raw) > 8 * 1024 * 1024:
                        return self.respond(502, b'{"detail":"bridge_response_too_large"}')
                    return self.respond(status, raw)
                if self.command != "GET":
                    return self.respond(403, b'{"detail":"bridge_static_read_only"}')
                relative = unquote(urlsplit(self.path).path).lstrip("/") or "index.html"
                path = (STATIC / relative).resolve()
                if (not path.is_relative_to(STATIC) or not path.is_file()
                        or path.suffix.lower() not in {".html", ".js", ".css", ".svg", ".png", ".jpg", ".webp", ".woff", ".woff2", ".ico"}):
                    return self.respond(404, b'{"detail":"static_not_found"}')
                self.respond(200, path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")

            do_GET = dispatch
            do_POST = dispatch
            do_PUT = dispatch
            do_PATCH = dispatch
            do_DELETE = dispatch
            do_OPTIONS = dispatch

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        timer = threading.Timer(args.ttl_seconds, server.shutdown)
        timer.daemon = True
        timer.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        print(json.dumps({"url": origin + "/?data=service#/cases/" + ready["case_id"] + "/tasks",
            "service_base": origin + "/api/v1/socai2", "public_marker": "local-acceptance",
            "marker_is_not_a_credential": True, "ttl_seconds": args.ttl_seconds,
            "read_only": args.read_only,
            "stop": "Ctrl-C closes the bridge and SSH tunnel"}), flush=True)
        try:
            server.serve_forever(poll_interval=.2)
        finally:
            timer.cancel()
    finally:
        if server:
            server.server_close()
        # EOF tells 21 to close and persist its H receipt before we tear down
        # its control connection. The upstream API key is never returned.
        if process:
            if process.stdin:
                process.stdin.close()
            try:
                process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
        if tunnel:
            tunnel.terminate()
            tunnel.wait(timeout=10)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
