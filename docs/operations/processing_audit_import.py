"""Import one local investigation export into the read-only workbench."""
import json
import re
from pathlib import Path
from uuid import UUID

import export_processing_audit_batch as exporter
import refresh_three_case_replay_20261106 as replay
import update_processing_audit as site
from read_processing_audit_20261106 import TABLES, check_credentials, require

SECRET_TEXT = re.compile(
    r'(?i)"(?:client_secret|refresh_token|id_token|client_key|secret_access_key|private_key)"\s*:\s*"[^"]+'
    r'|-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----'
    r'|\b(?:postgres(?:ql)?(?:\+[a-z]+)?|rediss?)://[^/@\s]+:[^/@\s]+@'
)


def below(root, path):
    """Keep manifest fields, directory links and Windows junctions inside the chosen tree."""
    require(path.resolve().is_relative_to(root), "snapshot path escapes the selected folder")
    return path


def check_value(item):
    # Credentials inside a JSON string (e.g. a tool's raw response) can have
    # escaped quotes in the outer file. Check the unescaped representation too.
    if isinstance(item, dict):
        for key, child in item.items():
            if key.lower() in {"api_key", "api-key", "apikey", "access_token", "refresh_token", "id_token",
                               "client_secret", "client_key", "secret_access_key", "password",
                               "private_key", "authorization"} and child:
                raise ValueError("possible credential in snapshot; inspect before release")
            check_value(child)
    elif isinstance(item, list):
        for child in item:
            check_value(child)
    elif isinstance(item, str):
        check_credentials(item.encode("utf-8"))
        require(not SECRET_TEXT.search(item), "possible credential in snapshot; inspect before release")


def read(root, path, *, checksum=None):
    raw = below(root, path).read_bytes()
    if checksum is not None:
        require(site.sha(raw) == checksum, "snapshot checksum mismatch: " + path.name)
    check_credentials(raw)
    value = json.loads(raw)
    check_value(value)
    return value


def checked_rows(data, tenant, counts):
    require(set(data) == set(TABLES) and all(isinstance(rows, list) for rows in data.values()),
            "expected all 29 database tables (empty tables are arrays)")
    require(counts == {table: len(rows) for table, rows in data.items()}, "snapshot table counts differ")
    known = {}
    for table, rows in data.items():
        ids = set()
        for row in rows:
            require(row.get("tenant_id") == tenant and row["id"] and row["id"] not in ids,
                    f"{table}: unexpected tenant or duplicate identity")
            ids.add(row["id"])
        known[table] = ids
    # Rows are complete for this subject. Other business subjects may be named
    # by external references, but the owner of each execution must be present.
    for table, rows in data.items():
        for row in rows:
            for field, parent in (("alert_id", "alerts"), ("incident_id", "incidents"), ("case_id", "cases"),
                                  ("run_id", "runs"), ("source_run_id", "runs"), ("step_id", "run_steps"),
                                  ("activity_id", "activities")):
                if row.get(field):
                    require(row[field] in known[parent], f"{table}.{field} outside snapshot")
    steps = {s["id"]: s["run_id"] for s in data["run_steps"]}
    for a in data["artifacts"]:
        if a.get("step_id"):
            require(steps[a["step_id"]] == a.get("run_id"), "artifact belongs to a different Run")
    require(all(r.get("case_id") or r.get("alert_id") or r.get("incident_id") for r in data["runs"]),
            "Run without a scoped subject")


def reject_retired_rows(data, tenant):
    if tenant != exporter.TENANT:
        return
    archive = site.EVIDENCE / replay.SOURCE
    cases = {r["case_id"] for r in site.read(archive / "plan.json")["cases"]}
    runs = {r["id"] for c in site.read(archive / "readback/summary.json")["cases"] for r in c["run_states"]}
    require(not any(c["id"] in cases for c in data["cases"]) and not any(r["id"] in runs for r in data["runs"]),
            "snapshot refers to retired Case or Run identities")


def identifier(value):
    require(isinstance(value, str) and str(UUID(value)) == value, "invalid subject UUID")
    return value


def case_alert_ids(data, case_id):
    members = {row["alert_id"] for table in ("case_alerts", "incident_alerts", "run_members", "case_assessment_members",
                                              "result_members") for row in data[table]}
    operations = {a["id"] for a in data["activities"] if a.get("subject_case_id") == case_id
                  and a.get("action") in {"case_members_changed", "case_members_moved_in", "case_members_moved_out"}}
    for target in data["activity_targets"]:
        member_recorded = any(isinstance(target.get(field), dict) and target[field].get("member") is True
                              for field in ("before_value", "after_value"))
        if (member_recorded and target.get("alert_id") and target["activity_id"] in operations
                and target.get("result_state") == "succeeded"):
            members.add(target["alert_id"])
    return members


def page_case(root, folder, plan_folder=None):
    manifest = read(root, folder / "manifest.json")
    require(manifest["schema_version"] == "socai2.page-export.v1", "unsupported page export")
    batch, tenant = manifest["batch_id"], identifier(manifest["tenant_id"])
    require(isinstance(batch, str) and batch and batch not in {replay.REPLAY, replay.SOURCE},
            "reserved or missing processing batch; use its registered readback")
    files = {}
    for entry in manifest["sources"]:
        name, digest = entry["file"], entry["sha256"]
        require(isinstance(name, str) and re.fullmatch(r"[\w.-]+\.json", name, re.ASCII)
                and name not in files and re.fullmatch(r"[0-9a-f]{64}", digest),
                "invalid or duplicate manifest file")
        files[name] = read(root, folder / name, checksum=digest)
    data = files["database.json"]
    checked_rows(data, tenant, manifest["table_counts"])
    reject_retired_rows(data, tenant)
    cid = manifest.get("case_id")
    if cid:
        identifier(cid)
    require(len(data["cases"]) <= 1 and all(c["id"] == cid for c in data["cases"]), "Case scope mismatch")
    require(any(data[t] for t in ("alerts", "incidents", "cases")), "no exported subjects")
    if data["cases"]:
        identity = cid
        require({i["id"] for i in data["incidents"]} == {l["incident_id"] for l in data["case_incidents"]}
                and {a["id"] for a in data["alerts"]} == case_alert_ids(data, cid),
                "case snapshot contains unrelated subjects or missing members")
    else:
        # A planned Case UUID can exist before the Case does. Keep standalone
        # subjects stable across captures and distinct inside the same batch.
        roots = data["incidents"] or data["alerts"]
        require(cid or len(roots) == 1, "an independent export must identify one main alert or incident")
        identity = cid or roots[0]["id"]
        if not cid:
            if data["incidents"]:
                require({a["id"] for a in data["alerts"]} == {m["alert_id"] for m in data["incident_alerts"]},
                        "independent incident snapshot contains unrelated alerts")
            require(not any(r.get("case_id") for r in data["runs"]), "standalone subject has a Case Run")
    plan = {}
    if plan_folder is not None and below(root, plan_folder / "plan.json").is_file():
        source = read(root, plan_folder / "plan.json")
        require(source.get("batch_id", batch) == batch, "plan belongs to another batch")
        plan = source.get("case") or {}
    key = plan.get("key") or (batch if cid else identity)
    extras = {"plan": plan or None, "inputs": plan.get("alerts"), "snapshot_at": manifest.get("exported_at"),
              "page_fields": files.get("case-page-data.json"),
              "page_reads": files.get("three-page-gets.json", files.get("api-responses.json")),
              "receipts": files.get("model-receipts.json")}
    return batch, key, identity, plan.get("title"), data, extras


def registered_cases(root):
    folder = below(root, root / "readback")
    plan = read(root, root / "plan.json")
    summary = read(root, folder / "summary.json")
    hashes = read(root, folder / "files.sha256.json")
    plan_hash = site.sha((root / "plan.json").read_bytes())
    is_replay = plan.get("batch") == replay.REPLAY
    if is_replay:
        require(plan_hash == "6eac8f08e7f858f5f18dc4639fadb57364a354e350ec81b12e96ae154e1d2a61",
                "unrecognized replay plan")
        replay.plans(root)
    else:
        exporter.valid_plan(plan)
    counts = {row["case"]: row["counts"] for row in summary["cases"]}
    require(set(counts) == {row["key"] for row in plan["cases"]} and len(counts) == len(summary["cases"]),
            "registered batch is incomplete")
    optional_files = ["inputs.json", "page-service-readback.json", "receipts/lake-output.json"]
    for card in plan["cases"]:
        key = card["key"]
        for name in ("database.json", "input-freshness.json"):
            rel = f"{key}/{name}"
            value = read(root, folder / rel, checksum=hashes[rel])
            if name == "database.json":
                checked_rows(value, plan["tenant_id"], counts[key])
        optional_files.append(f"readback/{key}/page-fields.json")
        receipts = below(root, root / "receipts" / key)
        for receipt in receipts.glob("*.json"):
            read(root, receipt)
    for rel in optional_files:
        path = below(root, root / rel)
        if path.is_file():
            read(root, path)
    if is_replay:
        yield from replay.verified_cases(root, folder)
        return
    _, payload = exporter.read_local(folder, plan, plan_hash)
    for card in plan["cases"]:
        rows = dict(payload[card["key"]])
        freshness = rows.pop("input_freshness")
        exporter.validate_data(card, rows, plan["batch"])
        runs = {r["id"] for r in rows["runs"] if r["kind"] == "baseline"}
        require({row["run_id"] for row in freshness} == runs and len(freshness) == len(runs),
                "Case freshness directory differs from baseline Runs")
    require({p.parent.name for p in folder.glob("*/database.json")} == set(counts),
            "unregistered subject folder in batch")
    if plan["batch"] != replay.SOURCE:
        for records in payload.values():
            reject_retired_rows(records, plan["tenant_id"])
        yield from site.readback_cases(root)


def folder_cases(root):
    root = Path(root).resolve(strict=True)
    require(root.is_dir(), "select a snapshot directory")
    if below(root, root / "readback").is_dir():
        yield from registered_cases(root)
    elif below(root, root / "manifest.json").is_file():
        yield page_case(root, root)
    elif below(root, root / "cases").is_dir():
        dirs = sorted(p for p in (root / "cases").iterdir() if p.is_dir())
        require(dirs, "no case export directories")
        for directory in dirs:
            yield page_case(root, below(root, directory / "export"), directory)
    elif below(root, root / "exports").is_dir():
        candidates = []
        for p in (root / "exports").glob("*/manifest.json"):
            manifest = read(root, p)
            # A standalone export can omit case_id. Its real main subject still
            # distinguishes this capture from another alert in the same batch.
            subject = manifest.get("case_id") or page_case(root, p.parent)[2]
            candidates.append((site.timestamp(manifest["exported_at"]), p.parent, manifest["batch_id"],
                               subject, manifest["tenant_id"]))
        require(candidates, "no completed snapshots; wait for an export manifest")
        require(len({row[2:] for row in candidates}) == 1, "exports folder mixes different snapshot subjects")
        yield page_case(root, max(candidates)[1], root)
    else:
        raise ValueError("choose a registered batch or a directory containing a page-export manifest")


def import_folder(folder, output):
    root, output = Path(folder).resolve(strict=True), Path(output).resolve()
    require(not output.is_relative_to(root) and not root.is_relative_to(output),
            "keep the published site separate from the source folder")
    cases = list(folder_cases(root))
    for batch, key, identity, title, rows, extras in cases:
        check_value([batch, key, identity, title, rows, extras])
    require(len({(batch, identity) for batch, _, identity, *_ in cases}) == len(cases), "duplicate subject snapshot")
    require(site.existing(output / "index.html") is not None, "upgrade the original workbench before importing")
    retire = []
    if any(c[0] == replay.REPLAY for c in cases):
        original = site.read(site.EVIDENCE / replay.SOURCE / "plan.json")
        for card in original["cases"]:
            key = card["key"]
            rid = site.sha(json.dumps([replay.SOURCE, key], ensure_ascii=False).encode("utf-8"))
            retire.append({"id": rid, "batch": replay.SOURCE, "key": key, "scope_id": card["case_id"]})
    return site.update([root], output, load_cases=lambda selected: cases if selected == root else (),
                       retire_if_absent=retire)
