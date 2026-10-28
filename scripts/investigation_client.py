"""One explicit investigation/core HTTP request; Bearer token stays in environment."""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", choices=["GET", "POST"])
    parser.add_argument("path", help="API-relative path from a response, including its query if needed")
    parser.add_argument("--base-url", default=os.getenv("AISOC_INVESTIGATION_BASE_URL", "http://127.0.0.1:18010"))
    parser.add_argument("--core-base-url", default=os.getenv("AISOC_CORE_BASE_URL", "http://127.0.0.1:18000"))
    parser.add_argument("--token-env", default="AISOC_API_TOKEN")
    parser.add_argument("--body", type=Path, help="JSON file, with an explicit operation_key for write operations")
    parser.add_argument("--timeout", type=float, default=150)
    args = parser.parse_args()
    path = urlsplit(args.path)
    if path.scheme or path.netloc or path.fragment:
        parser.error("path must be an API-relative path without a fragment")
    if path.path == "/api/v2/investigation" or path.path.startswith("/api/v2/investigation/"):
        base = args.base_url
    elif path.path.startswith("/api/v1/"):
        base = args.core_base_url
    else:
        parser.error("path must begin with /api/v2/investigation/ or /api/v1/")
    parsed_base = urlsplit(base)
    if parsed_base.scheme not in {"http", "https"} or not parsed_base.netloc or parsed_base.username or parsed_base.password or parsed_base.query or parsed_base.fragment or parsed_base.path not in {"", "/"}:
        parser.error("base URL must contain only http(s) scheme and host/port")
    token = os.getenv(args.token_env, "").strip()
    if not token:
        parser.error(f"set {args.token_env} to an existing authorized Bearer token")
    if args.method == "GET" and args.body:
        parser.error("GET does not accept --body")
    try:
        data = json.dumps(json.loads(args.body.read_text(encoding="utf-8-sig")), ensure_ascii=False).encode() if args.body else None
        request = Request(base.rstrip("/") + args.path, data=data, method=args.method,
                          headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            response = build_opener(NoRedirect()).open(request, timeout=args.timeout)
        except HTTPError as exc:
            response = exc
        with response:
            sys.stdout.buffer.write(response.read())
            sys.stdout.buffer.write(b"\n")
            print(f"HTTP {response.status}", file=sys.stderr)
            return 0 if 200 <= response.status < 300 else 1
    except (OSError, ValueError, URLError) as exc:
        print(f"{type(exc).__name__}: request not completed; no automatic retry", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
