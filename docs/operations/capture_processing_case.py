"""Capture committed Case processing rows and optionally refresh the local 4177 workbench."""
import argparse
import asyncio
import hashlib
import json
import math
import os
import sys
import tempfile
from datetime import timezone
from pathlib import Path
from uuid import UUID

import asyncpg
import processing_audit_import as importer
import update_processing_audit as site
from read_processing_audit_20261106 import TABLES, check_credentials, require

RLS = """SELECT current_setting('transaction_read_only')='on'
 AND current_setting('transaction_isolation')='repeatable read'
 AND public.current_tenant_id()=$1
 AND (SELECT bool_and(pg_catalog.row_security_active(('socai2.' || name)::regclass))
      FROM unnest($2::text[]) AS visible(name))"""
SCOPE = """WITH incidents AS (
 SELECT incident_id FROM socai2.case_incidents WHERE tenant_id=$1 AND case_id=$2
), alerts AS (
 SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=$1 AND case_id=$2
 UNION SELECT alert_id FROM socai2.run_members WHERE tenant_id=$1 AND case_id=$2
 UNION SELECT alert_id FROM socai2.case_assessment_members WHERE tenant_id=$1 AND case_id=$2
 UNION SELECT alert_id FROM socai2.result_members WHERE tenant_id=$1 AND case_id=$2
 UNION SELECT alert_id FROM socai2.incident_alerts WHERE tenant_id=$1
       AND incident_id IN (SELECT incident_id FROM incidents)
 UNION SELECT t.alert_id FROM socai2.activities a JOIN socai2.activity_targets t
       ON (a.tenant_id,a.id)=(t.tenant_id,t.activity_id) WHERE a.tenant_id=$1 AND a.subject_case_id=$2
       AND a.action IN ('case_members_changed','case_members_moved_in','case_members_moved_out')
       AND t.alert_id IS NOT NULL AND t.result_state='succeeded'
       AND (t.before_value @> '{"member":true}' OR t.after_value @> '{"member":true}')
), stages AS (
 SELECT id FROM socai2.runs WHERE tenant_id=$1 AND (
 (kind='alert_basic' AND alert_id IN (SELECT alert_id FROM alerts)) OR
 (kind='incident_diagnosis' AND incident_id IN (SELECT incident_id FROM incidents)))
)
SELECT transaction_timestamp() AS captured_at, ARRAY(SELECT alert_id FROM alerts ORDER BY 1) AS alerts,
 ARRAY(SELECT incident_id FROM incidents ORDER BY 1) AS incidents, ARRAY(SELECT id FROM stages ORDER BY 1) AS stages
FROM socai2.cases WHERE tenant_id=$1 AND id=$2"""


def case_query(table):
    """Read one table for the captured Case, its alert members and all related incidents."""
    if table not in TABLES:
        raise ValueError("unsupported capture table")
    runs = "SELECT r.id FROM socai2.runs r WHERE r.tenant_id=s.tenant AND (r.case_id=s.cid OR r.id=ANY(s.stages))"
    subject = "subject_case_id=s.cid OR subject_alert_id=ANY(s.aids) OR subject_incident_id=ANY(s.incident)"
    owners = "t.case_id=s.cid OR t.alert_id=ANY(s.aids) OR t.incident_id=ANY(s.incident)"
    if table == "alerts":
        clause = "t.id=ANY(s.aids)"
    elif table in {"alert_materials", "alert_source_refs", "alert_objects", "alert_assessments"}:
        # Human feedback and imported assessments need not have a source Run.
        clause = "t.alert_id=ANY(s.aids)"
    elif table == "incidents":
        clause = "t.id=ANY(s.incident)"
    elif table in {"incident_alerts", "incident_diagnoses"}:
        clause = "t.incident_id=ANY(s.incident)"
    elif table == "runs":
        clause = "t.id IN (" + runs + ")"
    elif table in {"run_members", "run_steps"}:
        clause = "t.run_id IN (" + runs + ")"
    elif table == "artifacts":
        clause = ("t.run_id IN (" + runs + ") OR t.case_id=s.cid OR (t.run_id IS NULL AND t.alert_id=ANY(s.aids))"
                  " OR (t.run_id IS NULL AND t.incident_id=ANY(s.incident))")
    elif table == "activities":
        clause = subject
    elif table == "activity_targets":
        # A batch activity can have additional targets outside this Case.
        clause = ("t.activity_id IN (SELECT id FROM socai2.activities WHERE tenant_id=s.tenant AND (" + subject + "))"
                  " AND (" + owners + " OR t.run_id IN (" + runs + ")"
                  " OR t.task_id IN (SELECT id FROM socai2.tasks WHERE tenant_id=s.tenant AND case_id=s.cid)"
                  " OR t.result_id IN (SELECT id FROM socai2.results WHERE tenant_id=s.tenant AND case_id=s.cid)"
                  " OR t.comment_id IN (SELECT c.id FROM socai2.comments c WHERE c.tenant_id=s.tenant AND "
                  "(c.case_id=s.cid OR c.alert_id=ANY(s.aids) OR c.incident_id=ANY(s.incident))))")
    elif table in {"comments", "response_links"}:
        clause = owners
    else:
        clause = "t." + ("id" if table == "cases" else "case_id") + "=s.cid"
    return ("WITH scope AS (SELECT $1::uuid tenant,$2::uuid[] aids,$3::uuid[] incident,$4::uuid cid,$5::uuid[] stages) "
            "SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY t.id),'[]'::jsonb) FROM socai2." + table
            + " t CROSS JOIN scope s WHERE t.tenant_id=s.tenant AND (" + clause + ")")


async def capture(connection, tenant, case):
    async with connection.transaction(isolation="repeatable_read", readonly=True):
        await connection.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
        require(await connection.fetchval(RLS, tenant, list(TABLES)), "read-only tenant RLS is required on all 29 tables")
        scope = await connection.fetchrow(SCOPE, tenant, case)
        require(scope is not None, "Case absent or not visible to this tenant")
        args = (tenant, scope["alerts"], scope["incidents"], case, scope["stages"])
        data = {}
        for table in TABLES:
            data[table] = json.loads(await connection.fetchval(case_query(table), *args))
    return scope["captured_at"], data


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def save(folder, tenant, case, at, data, *, verify_history=True):
    """Under the collector lock, publish both files by renaming one complete directory."""
    batch = f"case-{tenant}-{case}"
    identity = {"batch_id": batch, "case_id": str(case), "tenant_id": str(tenant)}
    counts = {t: len(r) for t, r in data.items()}
    importer.checked_rows(data, str(tenant), counts)
    require([r["id"] for r in data["cases"]] == [str(case)], "snapshot belongs to a different Case")
    require({a["id"] for a in data["alerts"]} == importer.case_alert_ids(data, str(case))
            and {i["id"] for i in data["incidents"]} == {r["incident_id"] for r in data["case_incidents"]},
            "capture contains out-of-scope subjects")
    importer.check_value(data)
    body = encode(data)
    check_credentials(body)
    checksum = hashlib.sha256(body).hexdigest()

    folder.mkdir(parents=True, exist_ok=True)
    marker = importer.below(folder, folder / "capture-scope.json")
    if marker.exists():
        require(json.loads(marker.read_bytes()) == identity, "folder belongs to a different capture")
    else:
        require(not any(folder.iterdir()), "first capture requires an empty dedicated folder")
        site.atomic_save(marker, encode(identity))
    exports = importer.below(folder, folder / "exports")
    exports.mkdir(exist_ok=True)
    snapshots = sorted(exports.iterdir())
    latest = snapshots[-1] if snapshots else None
    if verify_history:
        for earlier in snapshots[:-1]:
            saved = importer.read(folder, earlier / "manifest.json")
            require(all(saved.get(k) == v for k, v in identity.items()), "exports contain a different capture")
    if latest is not None:
        previous = importer.read(folder, latest / "manifest.json")
        require(all(previous.get(k) == v for k, v in identity.items()), "exports contain a different capture")
        if previous["source_sha256"] == checksum:
            require(hashlib.sha256(importer.below(folder, latest / "database.json").read_bytes()).hexdigest() == checksum,
                    "stored snapshot checksum mismatch")
            return latest, checksum, False
    timestamp = at.astimezone(timezone.utc)
    destination = exports / timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    require(latest is None or destination.name > latest.name, "capture time must advance")
    manifest = {**identity, "schema_version": "socai2.page-export.v1", "source_environment": "processing",
                "input_kind": "investigation", "exported_at": timestamp.isoformat(), "table_counts": counts,
                "source_sha256": checksum, "sources": [{"file": "database.json", "role": "database", "sha256": checksum}],
                "database_snapshot": "single_readonly_repeatable_read"}
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        stage = Path(tmp) / "snapshot"
        stage.mkdir()
        (stage / "database.json").write_bytes(body)
        (stage / "manifest.json").write_bytes(encode(manifest))
        stage.rename(destination)
    return destination, checksum, True


async def collect(args):
    dsn = os.getenv("SOCAI2_AUDIT_DATABASE_URL")
    require(dsn and dsn.startswith(("postgres://", "postgresql://")), "SOCAI2_AUDIT_DATABASE_URL must be a PostgreSQL URL")
    folder = args.folder.resolve()
    output = args.site.resolve() if args.site else None
    require(not output or (not output.is_relative_to(folder) and not folder.is_relative_to(output)),
            "keep the published site separate from the source folder")
    published = None
    first_capture = True
    while True:
        try:
            with site.publishing(folder):
                connection = await asyncpg.connect(dsn, timeout=10, command_timeout=45)
                try:
                    at, data = await capture(connection, args.tenant, args.case)
                finally:
                    await connection.close(timeout=5)
                path, checksum, changed = save(folder, args.tenant, args.case, at, data, verify_history=first_capture)
                first_capture = False
                if output and checksum != published:
                    importer.import_folder(path, output)
                    published = checksum
                if changed or args.follow is None:
                    print(json.dumps({"snapshot": str(path), "changed": changed, "site": str(output) if output else None},
                                     ensure_ascii=False), flush=True)
        except (OSError, asyncpg.PostgresConnectionError) as exc:
            if args.follow is None:
                raise
            print(f"Capture interrupted ({type(exc).__name__}); retrying after the polling interval.", file=sys.stderr)
        if args.follow is None:
            return
        await asyncio.sleep(args.follow)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", type=UUID, required=True)
    parser.add_argument("--case", type=UUID, required=True)
    parser.add_argument("--folder", type=Path, required=True, help="dedicated directory for this tenant and Case")
    parser.add_argument("--follow", type=float, metavar="SECONDS", help="poll for committed changes until interrupted")
    parser.add_argument("--site", type=Path, help="publish snapshots to this workbench directory")
    args = parser.parse_args()
    if args.follow is not None and (not math.isfinite(args.follow) or args.follow < 1):
        parser.error("--follow must be at least one second")
    try:
        asyncio.run(collect(args))
    except KeyboardInterrupt:
        return 0
    except ValueError as exc:
        # asyncpg URL parsing errors may contain connection arguments. Only surface our own known guards.
        messages = {"SOCAI2_AUDIT_DATABASE_URL must be a PostgreSQL URL", "read-only tenant RLS is required on all 29 tables",
                    "Case absent or not visible to this tenant", "folder belongs to a different capture",
                    "first capture requires an empty dedicated folder", "keep the published site separate from the source folder"}
        print(str(exc) if str(exc) in messages else "Capture rejected; verify the connection, scope and snapshot.", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 -- do not expose DSNs or database text in logs
        print(f"Capture failed ({type(exc).__name__}).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
