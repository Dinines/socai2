"""A single frozen intranet case. All mutations use the original authenticated API."""
import asyncio
import fcntl
import json
import os
import sys
from pathlib import Path
from uuid import UUID, uuid5

import asyncpg
import httpx
from app.socai2_main import app as api
from config import TENANT, USER
from flow_export import export
from flow_fixture import PILOT_BATCH, encoded, sha, uid
from pilot_api import PROFILE_PATH, app
from validate_flow import ConfigurationStopped, Driver, FlowStopped, validate_campaign

DB = "socai2_pilot_20261106_01"
ROLE = "socai2_pilot_api_20261106_01"
GATEWAY = "http://litellm:4000/v1"
MODEL = "aisoc-investigation"
PLAN_SHA = "df836637137521839990723e8969fa209d280c579518e00675f0761627902f1b"
HISTORY_SHA = "dca4db844c946b23e469eaf4c5e6cb9670966aa26776884d9a6e8df61c91c9c5"
ROOT = Path("/pilot")


def require(value, reason):
    if not value:
        raise ConfigurationStopped(reason)


class PilotDriver(Driver):
    def __init__(self, client):
        self.root, self.client, self.batch = ROOT, client, PILOT_BATCH
        self.plan = self.read("plan")
        require(__debug__ and sha((ROOT / "plan.json").read_bytes()) == PLAN_SHA, "invalid_frozen_plan")
        validate_campaign(self.plan, self.batch)
        require(self.plan["database"] == DB and self.plan["tenant_id"] == TENANT and self.plan["actor_user_id"] == USER,
                "wrong_scope")
        history = (ROOT / "history-index.json").read_bytes()
        require(sha(history) == self.plan["history_index_sha256"] == HISTORY_SHA and
                json.loads(history)["model_attempts"] == 63, "prior_attempts_unverified")
        self.stage_ids = [uuid5(UUID(TENANT), "socai2.stage:" + uid(self.batch, k)) for k in ("A0", "A1", "I")]
        self.cid = uuid5(UUID(TENANT), "socai2.case.create:" + uid(self.batch, "case"))

    async def connect(self):
        dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
        return await asyncpg.connect(dsn, timeout=12, command_timeout=30)

    async def http(self, label, method, path, body=None, *, record=True, require_success=True):
        require(path.startswith("/api/v1/socai2/") and ".." not in path and "?" not in path, "unscoped_api_path")
        if record:
            self.save(label + "-request", {"method": method, "path": path, "body": body, "authentication": "pilot_api_key"})
        response = await self.client.request(method, path, json=body)
        try:
            data = response.json()
        except ValueError:
            data = None
        result = {"method": method, "path": path, "status": response.status_code, "body": data}
        if data is None:
            result["unparsed_body"] = {"bytes": len(response.content), "sha256": sha(response.content)}
        if record:
            self.save(label + "-response", result)
        if require_success and not 200 <= response.status_code < 300:
            raise FlowStopped("http_rejected_" + str(response.status_code))
        return result

    async def identity(self):
        identity = (await self.http(None, "GET", PROFILE_PATH, record=False, require_success=False))
        require(identity["status"] == 200 and identity["body"] == self.plan["model_profile"], "api_profile_not_verified")
        require(identity["body"]["base_url_sha256"] == sha(GATEWAY.encode()) and identity["body"]["model"] == MODEL,
                "private_gateway_profile_required")
        async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
            catalog = await client.get(GATEWAY + "/models", headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
        require(catalog.status_code == 200 and any(x["id"] == MODEL for x in catalog.json()["data"]), "gateway_alias_unverified")
        row = (await self.pg("""SELECT current_database() AS database,current_user AS role,
            NOT (SELECT rolbypassrls OR rolsuper FROM pg_roles WHERE rolname=current_user) AS limited,
            current_setting('row_security')='on' AS rls,
            (SELECT count(*) FROM information_schema.tables WHERE table_schema='socai2' AND table_type='BASE TABLE') AS tables,
            to_regprocedure('socai2.baseline_input_freshness(uuid,uuid)') IS NOT NULL AS freshness"""))[0]
        require(row == {"database": DB, "role": ROLE, "limited": True, "rls": True, "tables": 29, "freshness": True},
                "wrong_pilot_pg_role_or_schema")
        return {"profile": identity["body"], "gateway_catalog_match": True, "database": row, "model_calls": 0}

    async def budget(self, reserve=0):
        rows = await self.pg("""SELECT r.id,r.kind,r.case_id,r.alert_id,r.incident_id,r.state,
            count(s.id) FILTER (WHERE s.kind='model' AND s.state NOT IN ('planned','skipped')) AS calls,
            count(s.id) FILTER (WHERE s.kind='model' AND s.state IN ('running','unknown')) AS unresolved
            FROM socai2.runs r LEFT JOIN socai2.run_steps s ON s.run_id=r.id AND s.tenant_id=r.tenant_id
            WHERE r.tenant_id=$1 GROUP BY r.id""", UUID(TENANT))
        subjects = self.read("ingest-subjects")
        expected = dict(zip(self.stage_ids, [("alert_basic", UUID(a)) for a in subjects["alert_ids"]]
                            + [("incident_diagnosis", UUID(subjects["incident_id"]))], strict=True))
        for r in rows:
            stage_ok = r["id"] in expected and (r["kind"], r["alert_id"] or r["incident_id"]) == expected[r["id"]]
            baseline_ok = r["kind"] == "baseline" and r["case_id"] == self.cid
            require(stage_ok or baseline_ok, "foreign_run_in_pilot_database")
            require(r["calls"] <= (4 if baseline_ok else 1), "per_run_attempt_limit")
            if r["state"] in {"unknown", "running"} or r["unresolved"]:
                raise FlowStopped("active_or_unknown_pilot_run")
        used = sum(row["calls"] for row in rows)
        require(len(rows) <= 4 and sum(row["kind"] == "baseline" for row in rows) <= 1 and used + reserve <= 7,
                "pilot_attempt_or_run_cap")
        return {"archived_attempts": 63, "dedicated_database_attempts": used, "attempted_models": 63 + used,
                "reserved_for_phase": reserve, "global_cap": 70}

    async def preflight(self):
        runtime = await self.identity()
        subjects, lake = self.read("ingest-subjects"), self.read("lake-readback")
        require(all(p.get("passed") is True and p["plan_sha256"] == PLAN_SHA for p in (subjects, lake)) and
                subjects["alert_ids"] == self.plan["canonical_alert_ids"] and len(lake["rows"]) == 2 and
                lake["database"] == "socai2_next_validation" and lake["old_lake_count"] == 0, "fusion_proof_invalid")
        for table, ids in (("alerts", subjects["alert_ids"]), ("incidents", [subjects["incident_id"]])):
            actual = await self.pg("SELECT id FROM socai2." + table + " WHERE tenant_id=$1", UUID(TENANT))
            require(sorted(str(row["id"]) for row in actual) == sorted(ids), "foreign_subject_in_pilot_pg")
        members = await self.pg("SELECT alert_id FROM socai2.incident_alerts WHERE tenant_id=$1 AND incident_id=$2",
                                UUID(TENANT), UUID(subjects["incident_id"]))
        require(sorted(str(r["alert_id"]) for r in members) == sorted(subjects["alert_ids"]), "pilot_incident_members_wrong")
        require(not await self.pg("SELECT id FROM socai2.cases WHERE tenant_id=$1", UUID(TENANT)) and
                not await self.pg("SELECT id FROM socai2.runs WHERE tenant_id=$1", UUID(TENANT)), "initial_case_or_run_exists")
        return {**runtime, "budget": await self.budget(7), "fusion_proof": True}


async def readback(driver):
    result = await export(driver)
    folder = Path(result["export_directory"])
    data = json.loads((folder / "database.json").read_bytes())
    base = "/api/v1/socai2"
    paths = ["/alerts", "/incidents", "/cases"] + ["/cases/" + c["id"] + "/page-data" for c in data["cases"]]
    for kind in ("alerts", "incidents"):
        for subject in data[kind]:
            path = "/" + kind + "/" + subject["id"]
            paths += [path, path + "/analysis"]
            if kind == "alerts" and subject.get("latest_material_id"):
                paths.append(path + "/materials/" + subject["latest_material_id"])
            elif kind == "incidents":
                paths.append(path + "/records/members")
            key = "alert_id" if kind == "alerts" else "incident_id"
            for run in data["runs"]:
                if run.get(key) == subject["id"]:
                    paths += [path + "/analysis/runs/" + run["id"] + suffix for suffix in ("", "/trace")]
    for result_row in data["results"]:
        if result_row.get("graph_artifact_id"):
            paths.append("/cases/" + result_row["case_id"] + "/runs/" + result_row["source_run_id"] +
                         "/artifacts/" + result_row["graph_artifact_id"])
    pages = [await driver.http(None, "GET", base + path, record=False, require_success=False) for path in paths]
    manifestpath = folder / "manifest.json"
    manifest = json.loads(manifestpath.read_bytes())
    manifest.update(database=DB, source_environment="21-isolated-deployed-pilot")
    models = []
    artifacts = {a["id"]: a for a in data["artifacts"]}
    for step in data["run_steps"]:
        if step["kind"] != "model" or step["state"] in {"skipped", "planned"}:
            continue
        output = (artifacts.get(step.get("output_artifact_id")) or {}).get("content_json") or {}
        payload = output.get("payload") or output
        models.append({**{k: step.get(k) for k in ("id","run_id","stage_code","state","usage","error",
                                                   "input_artifact_id","output_artifact_id")},
                       "raw": payload.get("raw"), "validation_error": payload.get("validation_error"),
                       "provider_error": payload.get("provider_error")})
    for name, role, value in (("three-page-gets.json","three_page_gets",pages), ("model-receipts.json","model_receipts",models)):
        blob = encoded(value) + b"\n"
        (folder / name).write_bytes(blob)
        manifest["sources"].append({"file": name, "sha256": sha(blob), "role": role})
    manifestpath.write_bytes(encoded(manifest) + b"\n")
    return {"directory": folder.name, "counts": manifest["table_counts"], "model_attempts": len(models),
            "cumulative_attempts": 63 + len(models), "get_status": [r["status"] for r in pages]}


async def main(phase):
    require(__debug__ and phase in {"identity", "preflight", "first", "export"}, "unknown_phase")
    # Exclusive lock spans the whole ASGI call, including the evidence readback.
    with (ROOT / "model-phase.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        async with api.router.lifespan_context(api), httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://pilot.invalid",
                headers={"Authorization": "Bearer " + os.environ["PILOT_API_KEY"]}) as client:
            driver = PilotDriver(client)
            if phase == "identity":
                return await driver.identity()
            if phase == "preflight":
                return await driver.preflight()
            if phase == "export":
                await driver.identity()
                return await readback(driver)
            require(not (ROOT / "first-intent.json").exists(), "first_already_claimed_never_replay")
            try:
                outcome = await driver.first()
            except Exception as exc:
                if not (ROOT / "first-intent.json").exists():
                    raise
                outcome = {"passed": False, "exception_type": type(exc).__name__,
                           "reason": str(exc) if isinstance(exc, FlowStopped) else "post_dispatch_interruption"}
            driver.save("first-outcome", outcome)
            return {"outcome": outcome, "readback": await readback(driver)}


if __name__ == "__main__":
    try:
        print("PILOT_RECEIPT=" + json.dumps(asyncio.run(main(sys.argv[1])), default=str), flush=True)
    except Exception as exc:
        print("PILOT_ERROR=" + json.dumps({"exception_type": type(exc).__name__,
              "code": str(exc) if isinstance(exc, FlowStopped) else "phase_failed"}), flush=True)
        raise SystemExit(1) from None
