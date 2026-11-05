"""Single-Case, short-lived loopback proxy ON 21; API credentials never leave 21.

Only a local relay holding an ephemeral nonce may call this proxy. The nonce is
provided through stdin, never printed or persisted. Machine execution is denied.
"""
import argparse
import hashlib
import hmac
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

from repair_acceptance_remote_20261105 import (
    bootstrap,
    card,
    core_gate,
    semantic_gate,
    sha,
    verify_runtime,
)

UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def allowed(method, target, case_id, task_id=None):
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or parsed.fragment or "%" in parsed.path or "//" in parsed.path:
        return False
    base = "/api/v1/socai2/cases/" + str(UUID(case_id))
    if not (parsed.path == base or parsed.path.startswith(base + "/")):
        return False
    suffix = parsed.path[len(base):]
    if method == "POST":
        return suffix == "/tasks" and not parsed.query and task_id is None
    if method == "PUT":
        return task_id is not None and suffix == "/tasks/" + task_id and not parsed.query
    if method != "GET":
        return False
    patterns = [r"", r"/history", r"/tasks", rf"/tasks/{UUID_PATTERN}",
        rf"/tasks/{UUID_PATTERN}/revisions", rf"/tasks/{UUID_PATTERN}/revisions/{UUID_PATTERN}",
        rf"/runs/{UUID_PATTERN}", rf"/results/{UUID_PATTERN}",
        rf"/runs/{UUID_PATTERN}/(?:artifacts|materials)/{UUID_PATTERN}"]
    if not any(re.fullmatch(pattern, suffix) for pattern in patterns):
        return False
    query = parse_qs(parsed.query, keep_blank_values=True)
    keys = {"limit", "cursor"} if suffix == "/history" else {"limit", "offset"} if suffix == "/tasks" or suffix.endswith("/revisions") else set()
    if set(query) - keys or any(len(values) != 1 for values in query.values()):
        return False
    try:
        return ("limit" not in query or 1 <= int(query["limit"][0]) <= 50) and (
            "offset" not in query or 0 <= int(query["offset"][0]) <= 1000) and (
            "cursor" not in query or len(query["cursor"][0]) <= 1024)
    except ValueError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["deepseek", "small"], required=True)
    parser.add_argument("--read-only", action="store_true")
    args = parser.parse_args()
    handshake = json.loads(sys.stdin.readline())
    nonce = handshake["session_nonce"]
    assert isinstance(nonce, str) and 40 <= len(nonce) <= 128
    ttl = handshake.get("ttl_seconds", 900)
    assert isinstance(ttl, int) and 60 <= ttl <= 900
    plan, release, service = bootstrap()
    core_gate(plan)
    verify_runtime(plan, release, service, args.backend)
    _, helper, _, _ = card(plan, release, service, args.backend)
    created = helper.read("case-create-response")["body"]
    case_id = created["case_id"]
    previous = helper.accepted_first_result(case_id)
    from repair_acceptance_remote_20261105 import HERE
    semantic_gate(helper.read("semantic-review"), previous, sha(HERE / "plan.json"),
        sha(helper.ROOT / "C1-result-0-response.json"))
    session_prefix = "page-read-" + uuid4().hex if args.read_only else "page-session"
    helper.save(session_prefix + "-start", {"case_id": case_id, "backend": args.backend, "read_only": args.read_only,
        "ttl_seconds": ttl, "max_requests": 150, "max_write_attempts": 0 if args.read_only else 3,
        "scope": "single Case GET, one H creation and its edits; no start/prepare or cross-Case access"})
    deadline = time.monotonic() + ttl
    state = {"requests": 0, "write_attempts": 0, "task_id": None, "create_attempted": False,
        "writes": [], "denied": 0}
    lock = threading.Lock()

    def upstream(method, path, body=None):
        request = urllib.request.Request("http://127.0.0.1:18020" + path, data=body, method=method,
            headers={"Authorization": "Bearer " + helper.IDENTITY["api_key"], "Content-Type": "application/json"})
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
                return response.status, response.read(8 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(1024 * 1024)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args):
            return

        def respond(self, code, body):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

        def dispatch(self):
            with lock:
                valid = (time.monotonic() < deadline and state["requests"] < 150
                    and hmac.compare_digest(self.headers.get("X-Repair-Session", ""), nonce)
                    and allowed(self.command, self.path, case_id, state["task_id"]))
                writing = self.command in {"POST", "PUT"}
                valid = valid and not (writing and args.read_only)
                valid = valid and (not writing or state["write_attempts"] < 3)
                valid = valid and not (self.command == "POST" and state["create_attempted"])
                if not valid:
                    state["denied"] += 1
                    return self.respond(403, b'{"detail":"repair_page_scope_denied"}')
                state["requests"] += 1
                body = None
                if writing:
                    if self.headers.get("Transfer-Encoding") or not self.headers.get("Content-Length", "").isdigit():
                        return self.respond(400, b'{"detail":"invalid_body_length"}')
                    size = int(self.headers["Content-Length"])
                    if not 0 < size <= 65536:
                        return self.respond(413, b'{"detail":"body_too_large"}')
                    body = self.rfile.read(size)
                    try:
                        json.loads(body)
                    except (ValueError, UnicodeDecodeError):
                        return self.respond(400, b'{"detail":"invalid_json_body"}')
                    state["write_attempts"] += 1
                    if self.command == "POST":
                        state["create_attempted"] = True  # no retry after uncertain create
                try:
                    status, raw = upstream(self.command, self.path, body)
                    if len(raw) > 8 * 1024 * 1024:
                        raise ValueError("response exceeds bridge limit")
                    if writing:
                        result = json.loads(raw)
                        if status == 200:
                            task = result["task"]
                            assert task["case_id"] == case_id
                            state["task_id"] = task["id"]
                        state["writes"].append({"method": self.command, "path": self.path, "status": status,
                            "body": json.loads(body), "response": result})
                    self.respond(status, raw)
                except Exception:  # noqa: BLE001 -- never disclose connection credentials
                    self.respond(503, b'{"detail":"repair_page_upstream_unknown_do_not_repeat"}')

        do_GET = dispatch
        do_POST = dispatch
        do_PUT = dispatch
        do_DELETE = dispatch
        do_PATCH = dispatch
        do_OPTIONS = dispatch

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = False
    timer = threading.Timer(ttl, server.shutdown)
    timer.daemon = True
    timer.start()
    threading.Thread(target=lambda: (sys.stdin.read(), server.shutdown()), daemon=True).start()
    print(json.dumps({"ready": True, "remote_port": server.server_port, "case_id": case_id,
        "ttl_seconds": ttl, "backend": args.backend, "read_only": args.read_only}), flush=True)
    try:
        server.serve_forever(poll_interval=.2)
    finally:
        timer.cancel()
        server.server_close()
        with lock:
            try:
                if state["task_id"]:
                    status, raw = upstream("GET", "/api/v1/socai2/cases/" + case_id + "/tasks/" + state["task_id"])
                    if status == 200:
                        task = json.loads(raw)
                        helper.save("page-H-task", task)
                        state["final_task_sha256"] = digest_json(task)
                        state["final_revision_id"] = task["current_revision_id"]
                    else:
                        state["final_read_failed"] = True
            except Exception:  # noqa: BLE001 -- close receipt must survive a failed final read
                state["final_read_failed"] = True
            helper.save(session_prefix + "-end", {**state, "case_id": case_id, "closed": True, "read_only": args.read_only,
                "credentials_exported": False})


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 -- keep private upstream connection data on 21
        print(json.dumps({"failed": True, "detail": "page proxy failed; inspect server-side session receipt"}), flush=True)
        sys.exit(1)
