"""Run the fixed pilot in an ephemeral API process on 21, using only approved private services."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

ROOT = Path("/opt/sting-aisoc-socai2/evidence/deployed-pilot-20261106-01")
SOURCE = ROOT / "source"
OUTPUT = ROOT / "analysis"
ORIGINAL = Path("/opt/sting-aisoc-socai2/private/next-20261104/api.env")
DB = "socai2_pilot_20261106_01"
ROLE = "socai2_pilot_api_20261106_01"
API = "socai2-next-api"
PLAN_SHA = "df836637137521839990723e8969fa209d280c579518e00675f0761627902f1b"


def require(test, message):
    if not test:
        raise RuntimeError(message)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def verify_package():
    require(digest((ROOT / "plan.json").read_bytes()) == PLAN_SHA, "frozen_plan_changed")
    plan = json.loads((ROOT / "plan.json").read_bytes())
    inventory = (ROOT / "source-manifest.json").read_bytes()
    canonical = json.dumps(json.loads(inventory), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    require(digest(canonical) == plan["transferred_source_manifest_sha256"], "source_manifest_changed")
    for path, sha in json.loads(inventory).items():
        file = SOURCE / path
        require(file.resolve().is_relative_to(SOURCE) and digest(file.read_bytes()) == sha, "mounted_source_changed")
    for name in ("validate_flow.py", "flow_export.py"):
        require(digest((ROOT / name).read_bytes()) == plan["source_sha256"]["deploy/local-investigation/" + name],
                "frozen_shared_driver_changed")


def stage_files(phase):
    OUTPUT.mkdir(mode=0o700, exist_ok=True)
    names = ["plan.json", "history-index.json"]
    if phase != "identity":
        names += ["ingest-subjects.json", "lake-readback.json"]
    for name in names:
        body = (ROOT / name).read_bytes()
        target = OUTPUT / name
        if not target.exists():
            with target.open("xb") as f:
                f.write(body)
        require(target.read_bytes() == body, "inconsistent_input_" + name)


def environment(info):
    old = dict(r.split("=", 1) for r in info["Config"]["Env"] if "=" in r)
    original = dict(r.split("=", 1) for r in ORIGINAL.read_text().splitlines() if r and not r.startswith("#") and "=" in r)
    private = json.loads((ROOT / "private/pilot-pg.json").read_text())
    require(private["DATABASE"] == DB and private["API_ROLE"] == ROLE and private["PILOT_API_KEY"], "private_identity_mismatch")
    require(old["CLICKHOUSE_USER"] == "socai2_next_reader_20261104" and old["SOCAI2_LAKE_DATABASE"] == "socai2_next_validation",
            "unexpected_lake_reader")
    settings = {"REDIS_URL", "CLICKHOUSE_HOST", "CLICKHOUSE_PORT", "CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD",
                "CLICKHOUSE_DATABASE", "SOCAI2_LAKE_DATABASE", "SECRET_KEY", "JWT_SECRET", "AISOC_CREDENTIAL_KEY",
                "REALTIME_INTERNAL_TOKEN", "AISOC_REALTIME_JWT_SECRET", "METRICS_TOKEN", "PGSSLROOTCERT", "PGSSLMODE",
                "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "AISOC_ALLOW_CLEARTEXT_DB", "PLUGIN_TRUST_MODE"}
    env = {k: old[k] for k in settings if k in old}
    dsn = urlsplit(old["DATABASE_URL"])
    require(dsn.hostname == "192.168.1.21" and private["PG_HOST"] in {"spirithub-postgres-1", dsn.hostname} and
            (dsn.port or 5432) == int(private["PG_PORT"]) == 5432, "pg_endpoint_mismatch")
    authority = ROLE + ":" + quote(private["API_DB_PASSWORD"], safe="") + "@" + dsn.hostname + ":" + str(dsn.port or 5432)
    key = original.get("OPENAI_API_KEY") or original.get("LLM_GATEWAY_API_KEY") or original.get("LITELLM_MASTER_KEY")
    require(key, "private_gateway_token_missing")
    env.update(DATABASE_URL=urlunsplit((dsn.scheme, authority, "/" + DB, dsn.query, "")), SOCAI2_SERVICE_DATABASE_NAME=DB,
               PILOT_API_KEY=private["PILOT_API_KEY"], OPENAI_API_KEY=key, OPENAI_MODEL="aisoc-investigation",
               OPENAI_BASE_URL="http://litellm:4000/v1", SOCAI2_MODEL_PROTOCOL="chat_completions",
               SOCAI2_MODEL_SCHEMA_PROFILE="vllm_grammar_v1", AISOC_AIRGAPPED="true", AISOC_AIRGAP_ALLOWLIST='["litellm"]',
               ENVIRONMENT="production", ENV="production", DEBUG="false", AISOC_DEV_AUTH_BYPASS="false",
               SOCAI2_CASE_API_ENABLED="true", SOCAI2_PAGE_READ_ENABLED="true", SOCAI2_ANALYSIS_READ_ENABLED="true",
               SOCAI2_STAGE_EXECUTION_ENABLED="true", SOCAI2_SOURCE_UEBA_ENABLED="true", SOCAI2_SOURCE_KNOWLEDGE_ENABLED="true",
               SOCAI2_SOURCE_GRAPH_ENABLED="false", SOCAI2_SOURCE_PRODUCT_HOST_ENABLED="false", DATABASE_POOL_SIZE="4",
               DATABASE_MAX_OVERFLOW="2", PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH="/pilot/source/services/api:/pilot/source/deploy/local-investigation:/pilotlib")
    return env


def run(phase):
    verify_package()
    stage_files(phase)
    inspected = subprocess.run(["docker", "inspect", API], capture_output=True, check=True)
    info = json.loads(inspected.stdout)[0]
    require(info["State"]["Running"] and info["Config"]["Image"] == "socai2-next-api:20261104-n15" and
            "socai2_default" in info["NetworkSettings"]["Networks"] and
            all(m["Destination"] == "/run/certs/ca.crt" and not m["RW"] for m in info["Mounts"]), "carrier_changed")
    env = environment(info)
    args = ["docker", "run", "--rm", "--pull=never", "--network", "socai2_default", "--volumes-from", API + ":ro",
            "--user", "0:0", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--read-only", "--tmpfs", "/tmp",
            "-v", str(OUTPUT) + ":/pilot:rw", "-v", str(SOURCE) + ":/pilot/source:ro",
            "-v", str(ROOT / "deployed_pilot_case.py") + ":/pilot-case.py:ro",
            "-w", "/pilot/source/services/api", "--entrypoint", "python"]
    for name in ("flow_export.py", "validate_flow.py"):
        args += ["-v", str(ROOT / name) + ":/pilotlib/" + name + ":ro"]
    for k in env:
        args += ["-e", k]
    args += [info["Image"], "-B", "/pilot-case.py", phase]
    p = subprocess.run(args, env={**os.environ, **env}, capture_output=True)
    receipts = [s for s in p.stdout.decode(errors="replace").splitlines() if s.startswith(("PILOT_RECEIPT=", "PILOT_ERROR="))]
    if not receipts:
        # Print only exception class or diagnostic keys, never the raw private logs.
        import re
        lines = p.stderr.decode(errors="replace").splitlines()
        classes = [m.group(1) for line in lines if (m := re.match(r"^([\w.]+(?:Error|Exception)):", line))]
        raise RuntimeError("container_no_receipt_" + (classes[-1] if classes else "startup"))
    print(json.dumps({"phase": phase, "image_id": info["Image"], "result": json.loads(receipts[-1].split("=", 1)[1])}))
    return p.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["identity", "preflight", "first", "export"])
    parser.add_argument("--dispatch-once", action="store_true")
    args = parser.parse_args()
    if not __debug__ or (args.phase == "first") != args.dispatch_once:
        parser.error("only the first phase needs --dispatch-once")
    try:
        sys.exit(run(args.phase))
    except Exception as exc:
        print(json.dumps({"phase": args.phase, "exception_type": type(exc).__name__,
              "code": str(exc) if type(exc) is RuntimeError else "host_preparation_failed"}))
        sys.exit(1)
