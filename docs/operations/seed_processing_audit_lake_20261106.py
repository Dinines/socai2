"""Populate and read back only three frozen source events for the r3 audit."""
import asyncio
import hashlib
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path("/opt/sting-aisoc-socai2/evidence/ie-audit-20261106-a1")
TENANT = "6aff0ef7-c670-5a84-a2ee-83d73e25b964"
LAKE = "socai2_next_validation"
USER = "socai2_audit_20261106_a1_insert"
IMAGE = "sha256:7218b535ca88c17616f563aa1efb6935f8eedd89e5fed4140ea6c8e4949c0be7"
CH = "sting-infra21-clickhouse-1"


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def record(name, value):
    with (ROOT / name).open("x", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, indent=2)


async def child(packet):
    sys.path.insert(0, "/opt/processor/smoke-fusion")
    from app.services.lake_writer import LakeWriter, event_to_row
    writer = LakeWriter(host=packet["host"], port=packet["port"], database=LAKE, user=USER,
                        password=packet["password"], batch_size=3)
    events = packet["events"]
    expected = [event_to_row(event) for event in events]
    require(len(expected) == 3 and all(r and r["tenant_id"] == TENANT and r["event_id"] == e["event_id"]
            for r, e in zip(expected, events, strict=True)), "source_projection_mismatch")
    await writer.start()
    try:
        require(writer._insert_sql.startswith("INSERT INTO " + LAKE + ".raw_events"), "incorrect_writer_database")
        for event in events:
            require(await writer.write_event(event), "writer_rejected_event")
        require(writer.rows_written == 3 and writer.rows_dropped == writer.flush_failures == 0, "write_unconfirmed")
    finally:
        await writer.stop()
    print("WRITTEN=" + json.dumps({"rows": writer.rows_written}))


def call(argv, *, body=None):
    r = subprocess.run(argv, input=body, text=True, capture_output=True, timeout=60, check=False)
    if r.returncode:
        raise RuntimeError("lake_audit_command_failed_" + argv[0])
    return r.stdout.strip()


def execute(expected_sha):
    require(ROOT.resolve() == ROOT and Path.cwd() == ROOT, "incorrect_evidence_directory")
    data = (ROOT / "plan.json").read_bytes()
    require(hashlib.sha256(data).hexdigest() == expected_sha, "incorrect_plan")
    plan = json.loads(data)
    require(plan["tenant_id"] == TENANT and [len(c.get("lake_events", [])) for c in plan["cases"]] == [1, 2, 0],
            "unexpected_lake_scope")
    events = [e for c in plan["cases"] for e in c.get("lake_events", [])]
    ids = {str(UUID(e["event_id"])) for e in events}
    require(len(ids) == len(events) == 3 and all(e["tenant_id"] == TENANT for e in events), "invalid_identifiers")
    where = f"tenant_id='{TENANT}' AND event_id IN (" + ",".join("'" + i + "'" for i in sorted(ids)) + ")"
    settings = dict(s.split("=", 1) for s in json.loads(call(["docker", "inspect", CH]))[0]["Config"]["Env"] if "=" in s)

    def sql(query):
        return call(["docker", "exec", "-i", CH, "clickhouse-client", "--user", settings.get("CLICKHOUSE_USER", "default"),
                     "--password", settings.get("CLICKHOUSE_PASSWORD", "")], body=query)

    def count(db):
        return int(sql("SELECT count() FROM " + db + ".raw_events WHERE " + where))

    require(count(LAKE) == count("aisoc") == 0, "source_ids_must_be_new")
    require(sql("SELECT count() FROM system.users WHERE name='" + USER + "'") == "0", "writer_exists")
    record("lake-intent.json", {"source_ids": sorted(ids), "new_lake_before": 0, "business_lake_before": 0,
                                "plan_sha256": expected_sha})
    password = secrets.token_hex(32)
    config = dict(s.split("=", 1) for s in (ROOT.parents[1] / "private/processing-handoff/runtime.env").read_text().splitlines()
                  if s and "=" in s)
    packet = {"events": events, "password": password, "host": config["CLICKHOUSE_HOST"], "port": int(config["CLICKHOUSE_PORT"])}
    sql("CREATE USER " + USER + " IDENTIFIED WITH sha256_password BY '" + password + "'")
    try:
        sql("GRANT INSERT ON " + LAKE + ".raw_events TO " + USER)
        args = ["docker", "run", "--rm", "-i", "--pull=never", "--read-only", "--network", "socai2_default",
                "--cap-drop=ALL", "--security-opt=no-new-privileges", "--tmpfs", "/tmp",
                "--mount", "type=bind,src=" + str(Path(__file__).resolve()) + ",dst=/lake.py,readonly",
                "--entrypoint", "python", IMAGE, "-B", "/lake.py", "--child"]
        output = call(args, body=json.dumps(packet))
        require('WRITTEN={"rows": 3}' in output, "writer_receipt_absent")
    finally:
        sql("DROP USER " + USER)
    rows = [json.loads(s) for s in sql("SELECT event_id,tenant_id,toString(event_time,'UTC') AS event_time_utc,"
            "src_hostname,class_uid,activity_id,process_name,file_path,action,outcome,ocsf_json FROM "
            + LAKE + ".raw_events WHERE " + where + " ORDER BY event_id FORMAT JSONEachRow").splitlines()]
    expected = {e["event_id"]: e["ocsf_event"] for e in events}
    require(len(rows) == 3 and {r["event_id"] for r in rows} == ids, "persisted_sources_missing")
    for row in rows:
        value = json.loads(row["ocsf_json"])
        value.pop("_socai2_storage")
        require(value == expected[row["event_id"]] and row["tenant_id"] == TENANT, "source_payload_mismatch")
    require(count("aisoc") == 0 and sql("SELECT count() FROM system.users WHERE name='" + USER + "'") == "0",
            "isolated_route_or_access_cleanup_failed")
    receipt = {"database": LAKE, "writer": "LakeWriter.write_event", "rows": rows, "business_lake_count": 0,
               "temporary_writer_removed": True}
    record("lake-output.json", receipt)
    print(json.dumps({"lake_rows_verified": len(rows), "business_lake_count": 0, "temporary_writer_removed": True}))


if __name__ == "__main__":
    os.umask(0o077)
    if sys.argv[1] == "--child":
        asyncio.run(child(json.load(sys.stdin)))
    else:
        execute(sys.argv[1])
