"""Publish saved investigation test exports to the local 4177 audit page."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from processing_audit_detail import render_case_detail
from processing_audit_index import render_index
from processing_audit_logs import case_log_files
from processing_audit_subjects import prepare_subjects
from read_processing_audit_20261106 import check_credentials

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/operations/evidence"
OUTPUT = ROOT / "deliverables/investigation-validation-20261106/processing-audit"


def read(path):
    return json.loads(path.read_bytes())


def optional(path):
    return read(path) if path.is_file() else None


def json_files(folder):
    return {p.stem: read(p) for p in sorted(folder.glob("*.json"))} or None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def renderer_revision():
    """Invalidate generated UI caches when their renderer changes, not when the DB changes."""
    folder = Path(__file__).parent
    names = ("processing_audit_detail.py", "processing_audit_flow.py", "processing_audit_inspector.py",
             "processing_audit_index.py", "processing_audit_delivery.py", "processing_audit_logs.py",
             "processing_audit_subjects.py")
    return sha(b"".join(name.encode() + b"\0" + (folder / name).read_bytes() for name in names))


def timestamp(value):
    if not value:
        return float("-inf")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"Execution timestamp needs a timezone: {value}")
    return dt.timestamp()


def readback_cases(root):
    plan = optional(root / "plan.json") or {}
    batch = plan.get("batch") or root.name
    cases = {c["key"]: c for c in plan.get("cases", [])}
    inputs = optional(root / "inputs.json") or {}
    pages = optional(root / "page-service-readback.json") or {}
    lake = optional(root / "receipts/lake-output.json") or {}
    snapshot = root / "readback"
    summary = optional(snapshot / "summary.json") or {}
    for name in ("plan", "inputs"):
        digest = summary.get(f"{name}_sha256")
        if digest and sha((root / f"{name}.json").read_bytes()) != digest:
            raise ValueError(f"Snapshot and {name}.json disagree in {root}")
    hashes = optional(snapshot / "files.sha256.json")
    files = sorted(snapshot.glob("*/database.json"))
    if not files:
        raise ValueError(f"No case snapshots in {snapshot}")
    missing = cases.keys() - {f.parent.name for f in files}
    if missing:
        print(f"{batch}: no snapshot yet for {', '.join(sorted(missing))}", file=sys.stderr)
    for f in files:
        key = f.parent.name
        case = cases.get(key, {})
        raw = f.read_bytes()
        if hashes is not None and hashes.get(f"{key}/database.json") != sha(raw):
            raise ValueError(f"Snapshot checksum mismatch: {f}")
        events = {e["event_id"] for e in case.get("lake_events", [])}
        extras = {
            "plan": case or None, "inputs": inputs.get(key), "page_reads": pages.get(key),
            "snapshot_at": (summary.get("snapshot") or {}).get("at"),
            "page_fields": optional(f.parent / "page-fields.json"),
            "receipts": json_files(root / "receipts" / key),
            "lake_rows": [r for r in lake.get("rows", []) if r.get("event_id") in events]
            if events and "rows" in lake else None,
        }
        yield batch, key, key, case.get("title"), json.loads(raw), extras


def page_export(folder, plan_folder):
    manifest = read(folder / "manifest.json")
    if manifest.get("schema_version") != "socai2.page-export.v1":
        raise ValueError(f"Unsupported page export in {folder}")
    raw = (folder / "database.json").read_bytes()
    sums = {item["file"]: item["sha256"] for item in manifest["sources"]}
    if sha(raw) != sums.get("database.json"):
        raise ValueError(f"Snapshot checksum mismatch: {folder}/database.json")
    data = json.loads(raw)
    if any(row.get("id") != manifest.get("case_id") for row in data.get("cases", [])):
        raise ValueError(f"Case identity differs from export manifest: {folder}")
    if any(row.get("tenant_id") != manifest.get("tenant_id") for row in data.get("runs", [])):
        raise ValueError(f"Run tenant differs from export manifest: {folder}")
    plan = optional(plan_folder / "plan.json") or {}
    case = plan.get("case", {})
    batch = manifest["batch_id"]
    key = case.get("key") or batch
    extras = {
        "plan": case or None, "inputs": case.get("alerts"),
        "snapshot_at": manifest.get("exported_at"),
        "page_fields": optional(folder / "case-page-data.json"),
        "page_reads": optional(folder / "three-page-gets.json"),
        "receipts": json_files(plan_folder / "execution"),
        "lake_rows": optional(plan_folder / "lake-readback.json"),
    }
    if extras["page_reads"] is None:
        extras["page_reads"] = optional(folder / "api-responses.json")
    return batch, key, manifest.get("case_id") or key, case.get("title"), data, extras


def cases_from(root):
    if (root / "readback").is_dir():
        yield from readback_cases(root)
    elif (root / "cases").is_dir():
        exports = sorted((root / "cases").glob("*/export/manifest.json"))
        if not exports:
            raise ValueError(f"No exported cases in {root}")
        for file in exports:
            yield page_export(file.parent, file.parent.parent)
    elif (root / "exports").is_dir():
        exports = sorted((root / "exports").glob("*/manifest.json"))
        if not exports:
            raise ValueError(f"No completed exports in {root}")
        # Each driver export is a full snapshot of this test, including its prior Runs.
        yield page_export(exports[-1].parent, root)
    elif (root / "manifest.json").is_file():
        plan_dir = root.parent.parent if root.parent.name == "exports" else root.parent
        yield page_export(root, plan_dir)
    else:
        raise ValueError(f"No supported investigation snapshots under {root}")


def prepare(batch, key, identity, title, data, extras):
    check_credentials(json.dumps([batch, key, title, data, extras], ensure_ascii=False, allow_nan=False).encode())
    for table in ("runs", "run_steps", "artifacts"):
        if not isinstance(data.get(table), list):
            raise TypeError(f"{batch}/{key}: missing {table} array")
    cases = data.get("cases", [])
    if len(cases) > 1:
        raise ValueError(f"{batch}/{key}: expected a single scoped case")
    scope_id = cases[0]["id"] if cases else None
    runs = data["runs"]
    run_ids = {r["id"] for r in runs}
    if len(run_ids) != len(runs) or any(s["run_id"] not in run_ids for s in data["run_steps"]):
        raise ValueError(f"{batch}/{key}: invalid Run/step scope")
    baselines = [r for r in runs if r["kind"] == "baseline"]
    if any(r.get("case_id") != scope_id for r in baselines):
        raise ValueError(f"{batch}/{key}: baseline Run belongs to a different case")
    started = [r for r in baselines if r.get("started_at")]
    latest = max(started, key=lambda r: (timestamp(r["started_at"]), r["id"]), default=None)
    status_run = max(baselines, key=lambda r: (timestamp(r.get("requested_at") or r.get("started_at")), r["id"]),
                     default=None)
    title = title or next((r["title"] for rows in (cases, data.get("incidents", []), data.get("alerts", []))
                           for r in rows if r.get("title")), key)
    extra_values = {k: v for k, v in extras.items() if k != "snapshot_at" and v is not None}
    snapshot_at = extras.get("snapshot_at")
    if snapshot_at:
        timestamp(snapshot_at)  # Local time without an offset cannot order successive snapshots.
    tenants = {r["tenant_id"] for table in ("cases", "alerts", "incidents", "runs")
               for r in data.get(table, ()) if r.get("tenant_id")}
    if len(tenants) > 1:
        raise ValueError("Multiple tenants in a single workbench record")
    record = {
        "id": sha(json.dumps([batch, identity], ensure_ascii=False).encode("utf-8")),
        "batch": batch, "key": key, "title": title, "scope_id": scope_id,
        "tenant_id": next(iter(tenants), None), "snapshot_at": snapshot_at,
        "started_at": latest["started_at"] if latest else None,
        "state": status_run["state"] if status_run else None,
        "delivery_state": status_run.get("delivery_state") if status_run else None,
        "runs": len(runs), "run_ids": sorted(run_ids), "steps": len(data["run_steps"]),
        "artifacts": len(data["artifacts"]),
        "step_ids": sorted(s["id"] for s in data["run_steps"]),
        "artifact_ids": sorted(a["id"] for a in data["artifacts"]),
        "run_states": {r["id"]: r.get("state") for r in runs},
    }
    logs, files = case_log_files(data, batch=batch, key=key)
    subjects = prepare_subjects(record, data)
    record["subjects"] = [subject for subject, _ in subjects]
    record["logs"] = logs
    record["updated_at"] = (logs or {}).get("updated_at") or record["started_at"]
    files.update({subject["detail"]: content for subject, content in subjects})
    body = render_case_detail(key=key, title=title, batch=batch, data=data, extras=extra_values,
                              logs=logs, subjects=record["subjects"]).encode("utf-8")
    record["detail"] = f"cases/{sha(body)}.html"
    files[record["detail"]] = body
    return record, files


def publish_files(output, files):
    base = output.resolve()
    for name, content in files.items():
        target = output / name
        if not target.resolve().is_relative_to(base) or target.is_symlink():
            raise ValueError("Publication path outside workbench")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or target.read_bytes() != content:
            atomic_save(target, content)


def preserves_history(old, new):
    if not old:
        return True
    terminal = {"completed", "failed", "cancelled"}
    return ((not old.get("scope_id") or old["scope_id"] == new["scope_id"])
            and (not old.get("tenant_id") or old["tenant_id"] == new["tenant_id"])
            and (not old.get("snapshot_at") or timestamp(new.get("snapshot_at")) >= timestamp(old["snapshot_at"]))
            and all(set(old.get(field, ())) <= set(new[field]) for field in ("run_ids", "step_ids", "artifact_ids"))
            and old["steps"] <= new["steps"] and old["artifacts"] <= new["artifacts"]
            and all(state not in terminal or new["run_states"].get(rid) == state
                    for rid, state in old.get("run_states", {}).items()))


def atomic_save(path, content):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        name = Path(tmp.name)
        try:
            tmp.write(content)
        except BaseException:
            tmp.close()
            name.unlink(missing_ok=True)
            raise
    try:
        os.replace(name, path)
    finally:
        name.unlink(missing_ok=True)


@contextmanager
def publishing(output):
    # An OS lock releases automatically if a publisher exits, including on Windows.
    lock_name = sha(os.path.normcase(str(output.resolve())).encode("utf-8"))
    with (Path(tempfile.gettempdir()) / f"socai2-audit-{lock_name}.lock").open("a+b") as lock:
        if os.name == "nt":
            import msvcrt
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def existing(index):
    if not index.exists():
        return {}
    html = index.read_text(encoding="utf-8")
    match = re.search(r'<script type="application/json" id="audit-records">(.*?)</script>', html, re.DOTALL)
    if match:
        return {r["id"]: r for r in json.loads(match[1])}
    if "21 调查处理模块 · 逐阶段审计" in html:
        return None
    raise ValueError(f"Unrecognized page at {index}; choose a separate --output")


def retired_records(index):
    if not index.is_file():
        return []
    match = re.search(r'<script type="application/json" id="audit-retired-records">(.*?)</script>',
                      index.read_text(encoding="utf-8"), re.DOTALL)
    return json.loads(match[1]) if match else []


def registry_html(records, output, retired):
    ordered = sorted(records.values(), key=lambda r: (timestamp(r["started_at"]), r["batch"], r["key"]), reverse=True)
    controls = next((name for name in ("controlled-flow.html", "controls.html") if (output / name).is_file()), None)
    comparison = "comparisons/index.html" if (output / "comparisons/index.html").is_file() else None
    html = render_index(ordered, controls_url=controls, comparison_url=comparison)
    if retired:
        body = json.dumps(retired, ensure_ascii=True).replace("<", "\\u003c")
        html = html.replace("</body>", '<script type="application/json" id="audit-retired-records">'
                            + body + "</script></body>", 1)
    return html.encode("utf-8")


def control_view(root, output):
    # This saved comparison uses controlled model/lake replies, separate from the test case registry.
    if root.resolve() != (EVIDENCE / "ie-audit-20261106-a1").resolve():
        return
    folder = root / "contract-controls-02"
    if not (folder / "database.json").is_file():
        return
    view = render_case_detail(
        key="受控验证", title="深查、图谱与交付的受控对照", batch=root.name,
        data=read(folder / "database.json"), extras={"受控执行回执": read(folder / "receipt.json")},
    )
    links = '<p><a href="index.html">返回案例列表</a>'
    if (output / "controls.html").is_file():
        links += ' · <a href="controls.html">查看原对照报告</a>'
    note = '<p>这里的模型答复和日志查询结果由测试指定，用于核对不同分支如何运行。</p>'
    content = view.replace("</header>", note + links + "</p></header>", 1).encode("utf-8")
    path = output / "controlled-flow.html"
    if not path.exists() or path.read_bytes() != content:
        atomic_save(path, content)


def update(roots, output, *, load_cases=cases_from, retire_if_absent=()):
    detail_dir = output / "cases"
    detail_dir.mkdir(parents=True, exist_ok=True)
    index = output / "index.html"
    with publishing(output):
        records = existing(index)
        retired = retired_records(index)
        if retire_if_absent:
            if records is None:
                raise ValueError("migrate the original workbench before importing this replay")
            by_id = {r["id"]: r for r in retired}
            active_scopes = {(r["batch"], r["scope_id"]) for r in records.values()}
            for row in retire_if_absent:
                if row["id"] in records or (row["batch"], row["scope_id"]) in active_scopes:
                    raise ValueError("migrate the previous three records with refresh_three_case_replay_20261106.py publish first")
                previous = by_id.get(row["id"])
                if previous and previous != row:
                    raise ValueError("retired record identity conflict")
                if not previous:
                    retired.append(row)
                    by_id[row["id"]] = row
        retired_ids = {r["id"] for r in retired}
        retired_scopes = {(r["batch"], r["scope_id"]) for r in retired}
        if records is None:
            # On first upgrade recover the three rows even when the first command adds a different batch.
            original = EVIDENCE / "ie-audit-20261106-a1"
            roots = [original, *(p for p in roots if p.resolve() != original.resolve())]
            records = {}
        imported = 0
        additions = []
        control_roots = []
        for root in roots:
            summary = optional(root / "readback/summary.json") or {}
            if load_cases is cases_from and summary.get("publication") == "replace_three_case_replay":
                print(f"{root}: use refresh_three_case_replay_20261106.py publish", file=sys.stderr)
                continue
            count_before = imported
            for case in load_cases(root):
                record, files = prepare(*case)
                if record["id"] in retired_ids or (record["batch"], record["scope_id"]) in retired_scopes:
                    continue
                old = records.get(record["id"])
                if not preserves_history(old, record):
                    raise ValueError(f"{record['batch']}/{record['key']}: snapshot would replace history; "
                                     "use a distinct batch for an independent test")
                additions.append(files)
                records[record["id"]] = record
                imported += 1
            if imported != count_before:
                control_roots.append(root)
        for files in additions:
            publish_files(output, files)
        for root in control_roots:
            control_view(root, output)
        html = registry_html(records, output, retired)
        if not index.exists() or index.read_bytes() != html:
            atomic_save(index, html)
    return imported, len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--batch", type=Path, action="append", help="saved batch or completed page-export directory")
    source.add_argument("--plan", type=Path, help="21 synthetic test plan.json; read its scoped snapshot if missing")
    source.add_argument("--folder", type=Path, help="verify and load a local investigation export folder")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="static site served on 4177")
    args = parser.parse_args()
    try:
        if args.folder:
            from processing_audit_import import import_folder

            imported, total = import_folder(args.folder, args.output)
            print(f"Read {imported} snapshots; {total} registered at {args.output / 'index.html'}")
            return
        if args.plan:
            if args.plan.name != "plan.json" or not args.plan.is_file():
                raise ValueError("--plan must point to the completed test batch's plan.json")
            root = args.plan.parent
            if not (root / "readback").exists():
                from export_processing_audit_batch import export_batch

                export_batch(args.plan, root / "readback")
            roots = [root]
        else:
            roots = args.batch or sorted(p.parent for p in EVIDENCE.glob("*/readback") if p.is_dir())
        if not roots:
            raise ValueError("No saved test batches found")
        imported, total = update(roots, args.output)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Audit page update failed: {exc}\n")
    print(f"Read {imported} case snapshots; {total} case records at {args.output / 'index.html'}")


if __name__ == "__main__":
    main()
