"""Create the not-yet-started d Case after its retained, terminal I rejection.

This does not replay first(), I, an ended C, or any previous intent. The frozen
d source/profile and original per-Case/global model limits still apply.
"""
import argparse
import asyncio
import fcntl
import sys
from pathlib import Path
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deploy/local-investigation"))

from config import STATE, TENANT, read_private
from flow_export import export
from flow_fixture import encoded, sha, uid
from validate_flow import Driver


async def run():
    batch = "local-maintenance-20261105d"
    driver = Driver(STATE / "validation" / batch, read_private())
    with (STATE / "validation-dispatch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        await driver.preflight()
        assert not (driver.root / "case-create-request.json").exists(), "Case already dispatched"
        ids = [uuid5(UUID(TENANT), "socai2.stage:" + uid(batch, key)) for key in ("A0", "A1", "I")]
        rows = await driver.pg("SELECT id,state,stop_reason FROM socai2.runs WHERE tenant_id=$1::uuid AND id=ANY($2::uuid[])", UUID(TENANT), ids)
        stages = {r["id"]: r for r in rows}
        assert len(stages) == 3 and all(stages[k]["state"] == "completed" for k in ids[:2])
        assert stages[ids[2]]["state"] == "failed" and stages[ids[2]]["stop_reason"] == "incident_source_scope_not_covered"
        allowance = await driver.budget(4)
        driver.save("case-after-I-failure-intent", {**allowance, "max_model_calls": 4, "retries": 0,
            "plan_sha256": sha((driver.root / "plan.json").read_bytes()),
            "reason": "User requires C6 independently of failed preceding analysis; Case has not yet been created",
            "existing_I_run_retained": str(ids[2]), "script_sha256": sha(Path(__file__).read_bytes())})
        try:
            subjects = driver.read("ingest-subjects")
            created = (await driver.http("case-create", "POST", "/api/v1/socai2/cases", {
                "operation_key": uid(batch, "case"), "title": "Maintenance record review " + batch,
                "incident_ids": [subjects["incident_id"]], "alert_ids": []}))["body"]
            await driver.start_round("C1", created["case_id"], created["pending_run_id"], created["scope_revision"])
            result = {"case_phase_returned": True, "budget": await driver.budget()}
        except Exception as exc:
            result = {"case_phase_returned": False, "exception_type": type(exc).__name__, "retry_allowed": False}
            raise
        finally:
            result["export"] = await export(driver)
            driver.save("case-after-I-failure-receipt", result)
            print(encoded(result).decode(), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.parse_args()
    asyncio.run(run())
