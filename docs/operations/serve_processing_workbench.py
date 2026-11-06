"""Serve the investigator's workbench on localhost and refresh its Case snapshots on demand."""
import argparse
import json
import os
import shutil
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import processing_workbench_source as source_db
import update_processing_audit as site
from capture_processing_case import save
from processing_audit_import import import_folder
from processing_workbench_retention import prune_publication
from read_processing_audit_20261106 import TENANT

RUNTIME = site.ROOT / ".local/processing-workbench"


class Workbench:
    def __init__(self, source, tenant, output, captures):
        self.source = source
        self.tenant = tenant
        self.output = output.resolve()
        self.captures = captures.resolve()
        if self.output.is_relative_to(self.captures) or self.captures.is_relative_to(self.output):
            raise ValueError("snapshot storage and served files must be separate directories")
        if self.output.is_relative_to(site.OUTPUT) or site.OUTPUT.is_relative_to(self.output):
            raise ValueError("use a separate runtime site for online Case data")
        self.reading_list = threading.Lock()
        self.refreshing = threading.Lock()

    def prepare_site(self):
        if not self.output.exists():
            self.output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=self.output.parent) as temp:
                copied = Path(temp) / "site"
                if self.source == "aisoc":
                    copied.mkdir()
                    (copied / "index.html").write_bytes(site.registry_html({}, copied, []))
                else:
                    shutil.copytree(site.OUTPUT, copied)
                copied.rename(self.output)
        index = self.output / "index.html"
        with site.publishing(self.output):
            records = site.existing(index)
            if records is None or not index.is_file():
                raise ValueError("runtime site must contain a workbench index")
            body = site.registry_html(records, self.output, site.retired_records(index))
            if body != index.read_bytes():
                site.atomic_save(index, body)

    @property
    def enabled(self):
        return self.source in ("21", "aisoc") or bool(os.getenv("SOCAI2_AUDIT_DATABASE_URL"))

    def refresh(self, case):
        folder = self.captures / str(self.tenant) / str(case)
        with site.publishing(folder):
            return self.refresh_locked(folder, case)

    def refresh_locked(self, folder, case):
        receipt_file = folder / "published.json"
        receipt = site.optional(receipt_file) or {}
        index = self.output / "index.html"
        records = site.existing(index)
        record = records.get(receipt.get("record_id"))
        previous = record
        revision = None
        if (record and record["scope_id"] == str(case) and record["tenant_id"] == str(self.tenant)
                and record["detail"] == receipt.get("detail") and (self.output / record["detail"]).is_file()
                and (folder / "exports" / receipt["snapshot"] / "database.json").is_file()):
            revision = receipt.get("revision")
        at, data, new_revision = source_db.read_case_if_changed(self.source, self.tenant, case, revision)
        changed = False
        if data is not None:
            path, version, changed = save(folder, self.tenant, case, at, data)
            if revision is None or changed or receipt["version"] != version:
                import_folder(path, self.output)
                with site.publishing(self.output):
                    records = site.existing(index)
                    manifest = site.read(path / "manifest.json")
                    record = next(r for r in records.values() if r["batch"] == manifest["batch_id"]
                                  and r.get("scope_id") == str(case))
                    prune_publication(self.output, previous, records.values())
            receipt = {"revision": new_revision, "version": version, "record_id": record["id"],
                       "detail": record["detail"], "snapshot": path.name}
            site.atomic_save(receipt_file, json.dumps(receipt).encode())
        return {"case_id": str(case), "changed": changed, "version": receipt["version"], "record_id": record["id"],
                "snapshot_at": record["snapshot_at"], "detail_url": "/" + record["detail"], "record": record}


class Handler(SimpleHTTPRequestHandler):
    timeout = 12
    server_version = "InvestigationWorkbench/1"

    def __init__(self, *args, app, **kwargs):
        self.app = app
        super().__init__(*args, directory=str(app.output), **kwargs)

    def send_json(self, status, body):
        encoded = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(encoded)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "same-origin")
        super().end_headers()

    def log_request(self, code="-", size="-"):
        # Successful polling and static reads would otherwise grow an access log indefinitely.
        if isinstance(code, int) and code >= 400:
            self.log_message("%s returned %s", self.command, code)

    def local_request(self, *, require_origin=False):
        port = self.server.server_port
        host = self.headers.get("Host", "").lower()
        allowed = {f"localhost:{port}", f"127.0.0.1:{port}"}
        if port == 80:
            allowed.update(("127.0.0.1", "localhost"))
        origin = self.headers.get("Origin")
        if (host not in allowed or (origin is not None and origin != "http://" + host)
                or (require_origin and not origin) or self.headers.get("Sec-Fetch-Site") == "cross-site"):
            self.send_json(403, {"error": "请从本机的工作台页面操作。"})
            return False
        return True

    def list_directory(self, path):
        self.send_error(404)

    def send_head(self):
        path = Path(self.translate_path(self.path))
        if not path.resolve().is_relative_to(self.app.output):
            self.send_error(404)
            return None
        return super().send_head()

    def do_HEAD(self):
        if self.local_request():
            super().do_HEAD()

    def do_GET(self):
        if not self.local_request():
            return
        path = urlsplit(self.path)
        if path.path == "/_workbench/status":
            self.send_json(200, {"enabled": self.app.enabled, "source": self.app.source,
                                "tenant_id": str(self.app.tenant)})
        elif path.path == "/_workbench/cases":
            params = parse_qs(path.query, keep_blank_values=True)
            cursor = params.get("cursor", [None])[0]
            if set(params) - {"cursor"} or ("cursor" in params and (
                    len(params["cursor"]) != 1 or not cursor or len(cursor) > 512)):
                self.send_json(400, {"error": "分页参数无效，请重新加载列表。"})
                return
            self.run_query(self.app.reading_list, source_db.list_cases, self.app.source, self.app.tenant, cursor)
        elif path.path.startswith("/_workbench/"):
            self.send_json(404, {"error": "没有这个工作台操作。"})
        else:
            super().do_GET()

    def do_POST(self):
        if not self.local_request(require_origin=True):
            return
        if self.path != "/_workbench/refresh":
            self.send_json(404, {"error": "没有这个工作台操作。"})
            return
        if self.headers.get_content_type() != "application/json":
            self.send_json(415, {"error": "请提交 JSON 格式的 Case ID。"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
            if self.headers.get("Transfer-Encoding") or not 0 < length <= 1024:
                raise ValueError
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or set(payload) - {"case_id", "version"}:
                raise ValueError
            case = UUID(str(payload.get("case_id")))
        except (ValueError, RecursionError):
            self.send_json(400, {"error": "请输入完整的 Case UUID。"})
            return
        self.run_query(self.app.refreshing, self.app.refresh, case)

    def run_query(self, lock, func, *args):
        if not self.app.enabled:
            self.send_json(503, {"error": "工作台尚未配置只读数据库。"})
            return
        if not lock.acquire(blocking=False):
            self.send_json(409, {"error": "工作台正在读取数据，请稍后刷新。"})
            return
        try:
            response = func(*args)
        except Exception as exc:  # noqa: BLE001 -- database and transport exceptions can contain private arguments
            reason = str(exc)
            if isinstance(exc, ValueError) and reason == "Case absent or not visible to this tenant":
                self.send_json(404, {"error": "当前租户找不到这个 Case。"})
            elif isinstance(exc, ValueError) and reason == "invalid cursor":
                self.send_json(400, {"error": "分页参数无效，请重新加载列表。"})
            else:
                self.log_error("workbench read failed (%s)", type(exc).__name__)
                self.send_json(503, {"error": "未能读取或更新记录，请检查只读连接后重试。"})
        else:
            self.send_json(200, response)
        finally:
            lock.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("aisoc", "21", "dsn"), default="aisoc")
    parser.add_argument("--tenant", type=UUID, help="required for a configured DSN")
    parser.add_argument("--site", type=Path)
    parser.add_argument("--captures", type=Path)
    parser.add_argument("--port", type=int, default=4177)
    args = parser.parse_args()
    if args.source == "dsn" and not args.tenant:
        parser.error("provide the authorized tenant UUID for --source dsn")
    if args.source == "21" and args.tenant and args.tenant != UUID(TENANT):
        parser.error("source 21 uses the processing handoff tenant")
    tenant = args.tenant or (source_db.DEFAULT_PRODUCTION_TENANT if args.source == "aisoc" else UUID(TENANT))
    runtime = RUNTIME / "aisoc" / str(tenant) if args.source == "aisoc" else RUNTIME
    app = Workbench(args.source, tenant, args.site or runtime / "site", args.captures or runtime / "captures")
    with ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, app=app)) as http:
        app.prepare_site()
        print(f"http://127.0.0.1:{http.server_port}/", flush=True)
        try:
            http.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
