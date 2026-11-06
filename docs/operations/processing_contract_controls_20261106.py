"""Contract controls on IE in an ephemeral loopback-only PostgreSQL and the installed r3 image."""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
import secrets
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

R3 = "sha256:7218b535ca88c17616f563aa1efb6935f8eedd89e5fed4140ea6c8e4949c0be7"
PG_IMAGE = "docker.m.daocloud.io/library/postgres:16-alpine"
RELEASE = Path("/opt/sting-aisoc-socai2/releases/processing-20261106-r3")
NAMES = ["socai2_test_model_view", "test_socai2_baseline_evidence", "test_socai2_baseline_analysis",
         "test_socai2_baseline_deep", "test_socai2_baseline_delivery", "test_socai2_baseline_executor",
         "test_socai2_human_tasks"]
METHODS = {"positive": ("test_socai2_baseline_executor", "test_full_adaptive_queries_reserve_fourth_call_and_deduplicate_questions"),
           "rejected": ("test_socai2_baseline_executor", "test_full_rejected_final_is_retained_without_retry_or_adoption"),
           "human": ("test_socai2_human_tasks", "test_human_frozen_context_and_moved_member_feedback")}
DB, ROLE = "ie_contract", "ie_contract_job"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def call(args, *, body=None, env=None, timeout=100):
    return subprocess.run(args, input=body, env=env, capture_output=True, check=False, timeout=timeout)


def docker(args, *, body=None, env=None):
    result = call(["docker", *args], body=body, env=env, timeout=300)
    if result.returncode:
        raise RuntimeError("isolated docker " + args[0] + " failed: " + result.stderr.decode(errors="replace")[-500:])
    return result.stdout


def in_container(label):
    import asyncio
    from importlib import import_module

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def run():
        dsn = os.environ["DATABASE_URL"]
        assert dsn.startswith("postgresql+asyncpg://ie_contract_job:") and dsn.endswith("@127.0.0.1:5432/ie_contract")
        e = create_async_engine(dsn)
        try:
            async with e.connect() as c:
                assert tuple((await c.execute(text("select current_database(),current_user"))).one()) == (DB, ROLE)
            module, method = METHODS[label]
            items = []
            def record(name, passed, detail):
                # Tracebacks are sanitized on the host before any handoff.
                items.append({"name": name, "passed": passed, "detail": detail})
            await import_module(module).run_checks(e, record, only={method})
            assert len(items) == 1 and items[0]["name"] == method
            print("CONTROL_JSON=" + json.dumps(items[0], default=str))
        finally:
            await e.dispose()
    asyncio.run(run())


def container_ids(name):
    return docker(["ps", "-aq", "--no-trunc", "--filter", "name=^/" + name + "$"]).decode().splitlines()


def run_host(files):
    assert set(files) == {n + ".py" for n in NAMES} | {"control.py"}
    # Pin to the specific database and processing image already present on 21.
    pg_image_id = docker(["image", "inspect", PG_IMAGE, "-f", "{{.Id}}"]).decode().strip()
    assert docker(["image", "inspect", "socai2-processing:processing-20261106-r3", "-f", "{{.Id}}"]).decode().strip() == R3
    manifest_bytes = (RELEASE / "manifest.json").read_bytes()
    assert sha(manifest_bytes) == "268df0811dce6c27cadd61f77cda97835201e24d82a6cf6e9c06c805e7541aa5"
    manifest = json.loads(manifest_bytes)
    tag = "ie-audit-contract-" + secrets.token_hex(5)
    results = {"started_at": now(), "image": R3, "pg_image": pg_image_id, "pg_network": "none",
               "runner_network": "shared with isolated PG, loopback only", "pgdata": "tmpfs",
               "model": "deterministic PipelineGateway / FinalGateway", "lake": "synthetic AdaptiveLake",
               "model_network_calls": 0, "test_files_sha256": {k: sha(v.encode()) for k, v in files.items()},
               "tests": {}, "resource_cleanup": {}}
    with tempfile.TemporaryDirectory(prefix=tag + "-") as tmp, contextlib.ExitStack() as cleanup:
        scratch = Path(tmp)
        for filename, value in files.items():
            file = scratch / filename
            file.write_text(value, encoding="utf-8")
            file.chmod(0o644)
        scratch.chmod(0o755)
        def remove(name, identity):
            own = container_ids(name)
            if own:
                assert own == [identity]
                docker(["rm", "-f", identity])
            results["resource_cleanup"][name] = not container_ids(name)

        secret = secrets.token_hex(24)
        pg_name = tag + "-pg"
        assert not container_ids(pg_name)
        pgid = docker(["run", "-d", "--name", pg_name, "--network", "none", "--pull=never",
                       "--tmpfs", "/var/lib/postgresql/data:rw,nosuid,nodev,size=256m",
                       "--memory=512m", "--pids-limit=128", "-e", "POSTGRES_DB=" + DB,
                       "-e", "POSTGRES_PASSWORD", pg_image_id],
                      env={**os.environ, "POSTGRES_PASSWORD": secrets.token_hex(24)}).decode().strip()
        cleanup.callback(remove, pg_name, pgid)
        assert container_ids(pg_name) == [pgid]
        def pg(sql):
            return docker(["exec", "-i", pgid, "psql", "-XAtq", "-U", "postgres", "-d", DB,
                           "-v", "ON_ERROR_STOP=1"], body=sql.encode()).decode()
        for _ in range(35):
            ready = call(["docker", "exec", pgid, "pg_isready", "-h", "127.0.0.1", "-U", "postgres", "-d", DB])
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("ephemeral PG startup")
        assert pg("select current_database()").strip() == DB
        pg(f"CREATE ROLE {ROLE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS PASSWORD '{secret}';")
        sql_names = ["support.sql", *sorted(p.name for p in (RELEASE / "schema").glob("12[3-6]_*.sql")), "grants.sql"]
        assert len(sql_names) == 6
        for name in sql_names:
            pathname = "schema/" + name
            body = (RELEASE / pathname).read_bytes()
            assert sha(body) == manifest["files"][pathname]["sha256"]
            sql = body.decode()
            if name == "grants.sql":
                sql = sql.replace("socai2_processing_handoff", DB).replace("socai2_processing_job", ROLE)
            pg(sql)
        u, t = "00000000-0000-0000-0000-000000000003", "00000000-0000-0000-0000-000000000001"
        pg(f"""INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
            VALUES('{t}','Synthetic contract','contract','starter',true,'{{}}','{{}}',now(),now());
            INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
            VALUES('{u}','{t}','synthetic-human@example.invalid','contract','!disabled','soc_analyst',true,true,'{{}}',now(),now());""")
        tables = sorted(pg("select tablename from pg_tables where schemaname='socai2'").splitlines())
        assert len(tables) == 29 and all(n.isidentifier() for n in tables)
        def counts():
            return {n: int(v) for n,v in (line.split("|") for line in pg(" UNION ALL ".join(
                f"SELECT '{n}',count(*) FROM socai2.{n}" for n in tables)).splitlines())}
        before = counts()
        assert sum(before.values()) == 0
        # Production r3 omits the tests' JSON Schema library. Restrict the
        # read-only mounts to these existing Debian package directories.
        from importlib import metadata
        deps = ["jsonschema", "pyrsistent", "attr", "attrs"]
        locations = {n:Path("/usr/lib/python3/dist-packages")/n for n in deps}
        assert all(p.resolve() == p and p.is_dir() for p in locations.values())
        results["test_only_packages"] = {n:metadata.version(n) for n in ("jsonschema","pyrsistent","attrs")}
        for label in METHODS:
            name = tag + "-" + label
            assert not container_ids(name)
            args = ["create", "--name", name, "--network=container:" + pgid, "--pull=never",
                    "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only", "--tmpfs", "/tmp",
                    "--memory=1g", "--pids-limit=128", "--mount", f"type=bind,src={scratch},dst=/app/tests,readonly",
                    "-e", "PYTHONPATH=/app:/app/tests:/control-deps", "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "ENVIRONMENT=test",
                    "-e", "DATABASE_URL"]
            for n, p in locations.items():
                args.extend(["--mount", f"type=bind,src={p},dst=/control-deps/{n},readonly"])
            args.extend(["--entrypoint", "python", R3, "/app/tests/control.py", "--inside", label])
            ident = docker(args, env={**os.environ, "DATABASE_URL": f"postgresql+asyncpg://{ROLE}:{secret}@127.0.0.1:5432/{DB}"}).decode().strip()
            cleanup.callback(remove, name, ident)
            raw = call(["docker","start","-a",ident], timeout=250)
            stdout = raw.stdout.decode(errors="replace").replace(secret, "[redacted]")
            lines = [s for s in stdout.splitlines() if s.startswith("CONTROL_JSON=")]
            row = json.loads(lines[-1].split("=", 1)[1]) if lines else {
                "name": METHODS[label][1], "passed": False,
                "detail": raw.stderr.decode(errors="replace").replace(secret,"[redacted]")[-2400:]}
            after = counts()
            row["inserted_rows"] = {n:after[n]-before[n] for n in tables}
            before = after
            results["tests"][label] = row
        # The PG database was created empty in this run and contains synthetic entities only.
        data = {n: json.loads(pg(f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY id),'[]') FROM socai2.{n} t;"))
                for n in tables}
        results["final_counts"] = before
    results["finished_at"] = now()
    return {"receipt": results, "database": data}


def local(out):
    here = Path(__file__).resolve()
    assert not out.exists()
    tests = here.parents[2] / "services/api/tests"
    packet = {n+".py": (tests / (n+".py")).read_text("utf-8") for n in NAMES}
    source = here.read_text(encoding="utf-8")
    packet["control.py"] = source
    # Use stdin for the allowlisted test sources, never a credential file or the workspace.
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "sting-infra21",
           "python3 -c " + shlex.quote(source) + " --host"]
    result = call(cmd, body=json.dumps(packet).encode(),timeout=1000)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-2000:])
    data = json.loads(result.stdout)
    out.mkdir(parents=True)
    for key in ("receipt","database"):
        (out/(key+".json")).write_text(json.dumps(data[key],ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    r = data["receipt"]
    print(json.dumps({"methods":{k:t["passed"] for k,t in r["tests"].items()},
                      "counts":r["final_counts"],"cleaned":r["resource_cleanup"]}))
    return all(t["passed"] for t in r["tests"].values()) and all(r["resource_cleanup"].values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--host",action="store_true")
    modes.add_argument("--inside",choices=METHODS)
    modes.add_argument("--output",type=Path)
    args = parser.parse_args()
    if args.host:
        print(json.dumps(run_host(json.load(sys.stdin))))
    elif args.inside:
        in_container(args.inside)
    else:
        sys.exit(0 if local(args.output) else 1)
