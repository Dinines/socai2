"""Single-dispatch matrix phases. Uses the same authenticated application and readback as 01."""
import asyncio
import json
import os
import sys
from uuid import UUID, uuid5

import deployed_pilot_case as pilot
import httpx
from config import TENANT, USER
from flow_fixture import sha, uid
from validate_flow import FlowStopped

CARD = os.environ["MATRIX_CARD"]
SPECS = {"02": ("credential", "local-eval-20261106-02", 7),
         "03": ("impact", "local-eval-20261106-03", 7),
         "04": ("maintenance", "local-maintenance-20261105g", 11)}
SCENARIO, COMPARISON, CAP = SPECS[CARD]
TOTAL_RUNS = 5 if CARD == "04" else 4
OTHER = json.loads(os.environ["MATRIX_OTHER_COUNTS"])
PRIOR = 66 + sum(OTHER.values())
pilot.DB = "socai2_pilot_20261106_" + CARD
pilot.ROLE = "socai2_pilot_api_20261106_" + CARD
pilot.PLAN_SHA = os.environ["MATRIX_PLAN_SHA"]
require = pilot.require


class MatrixDriver(pilot.PilotDriver):
    def __init__(self, client, phase):
        self.client, self.root, self.phase = client, pilot.ROOT, phase
        self.batch = "local-deployed-pilot-20261106-" + CARD
        self.plan = self.read("plan")
        expected = {"batch_id": self.batch, "database": pilot.DB, "campaign": "deployed-matrix-20261106",
                    "tenant_id": TENANT, "actor_user_id": USER, "comparison_batch_id": COMPARISON,
                    "max_model_calls": CAP, "max_runs": TOTAL_RUNS, "retries": 0, "previous_attempts": 66,
                    "additional_attempt_cap": 25, "initial_cumulative_attempts": 66, "global_local_model_call_cap": 91}
        require(__debug__ and sha((self.root/"plan.json").read_bytes()) == pilot.PLAN_SHA and
                all(self.plan.get(k)==v for k,v in expected.items()),"invalid_frozen_matrix_plan")
        require(self.plan["case"]["scenario"] == SCENARIO and self.plan["case"]["backend"] == "deployed"
                and self.plan["case"]["rounds"] == TOTAL_RUNS-3 and self.plan["case"]["max_model_calls"] == CAP,
                "invalid_case_card")
        require(self.plan["model_profile"]["schema_profile"] == "vllm_grammar_v1" and
                self.plan["model_profile"]["protocol"] == "chat_completions" and
                self.plan["baseline_limits"] == {"max_tokens":48000,"max_tool_calls":4,"max_model_calls":4,"seconds":120},
                "model_profile_or_limits_changed")
        history = (self.root/"history-index.json").read_bytes()
        require(sha(history)==self.plan["history_index_sha256"] and json.loads(history)["model_attempts"]==66,
                "archived_baseline_changed")
        require(set(OTHER)==set(SPECS)-{CARD} and all(isinstance(v,int) and 0<=v<=SPECS[c][2] for c,v in OTHER.items()),
                "sibling_accounting_invalid")
        self.stage_ids = [uuid5(UUID(TENANT),"socai2.stage:"+uid(self.batch,k)) for k in ("A0","A1","I")]
        self.cid = uuid5(UUID(TENANT),"socai2.case.create:"+uid(self.batch,"case"))

    async def budget(self, reserve=0):
        rows = await self.pg("""SELECT r.id,r.kind,r.case_id,r.alert_id,r.incident_id,r.state,
            count(s.id) FILTER (WHERE s.kind='model' AND s.state NOT IN ('planned','skipped')) AS calls,
            count(s.id) FILTER (WHERE s.kind='model' AND s.state IN ('running','unknown')) AS unresolved
            FROM socai2.runs r LEFT JOIN socai2.run_steps s ON s.tenant_id=r.tenant_id AND s.run_id=r.id
            WHERE r.tenant_id=$1 GROUP BY r.id""", UUID(TENANT))
        subjects = self.read("ingest-subjects")
        expected = dict(zip(self.stage_ids,[("alert_basic",UUID(a)) for a in subjects["alert_ids"]]
                            +[("incident_diagnosis",UUID(subjects["incident_id"]))],strict=True))
        for row in rows:
            baseline = row["kind"]=="baseline" and row["case_id"]==self.cid
            require(baseline or expected.get(row["id"])==(row["kind"],row["alert_id"] or row["incident_id"]),
                    "foreign_run")
            require(row["calls"] <= (4 if baseline else 1),"per_run_cap")
            if row["unresolved"] or row["state"] in {"unknown","running"}:
                raise FlowStopped("active_or_unknown_pilot_run")
        used = sum(r["calls"] for r in rows)
        require(len(rows)<=TOTAL_RUNS and sum(r["kind"]=="baseline" for r in rows)<=TOTAL_RUNS-3 and
                used+reserve<=CAP and PRIOR+used+reserve<=91,"card_or_global_budget_exceeded")
        return {"archived_attempts":66,"sibling_database_attempts":OTHER,"dedicated_database_attempts":used,
                "attempted_models":PRIOR+used,"reserved_for_phase":reserve,"card_cap":CAP,"global_cap":91}

    async def preflight(self):
        if self.phase != "second":
            return await super().preflight()
        require(CARD=="04" and (self.root/"first-outcome.json").exists(),"no_maintenance_first")
        await self.identity()
        created, _ = self.accepted_first()
        cases = await self.pg("SELECT id FROM socai2.cases WHERE tenant_id=$1",UUID(TENANT))
        runs = await self.pg("SELECT id FROM socai2.runs WHERE tenant_id=$1",UUID(TENANT))
        require(cases==[{"id":self.cid}] and created["case_id"]==str(self.cid) and len(runs)==4,
                "unexpected_state_before_second")
        return {"budget":await self.budget(4)}


async def main(phase):
    async with pilot.api.router.lifespan_context(pilot.api), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=pilot.app,raise_app_exceptions=False),base_url="http://pilot.invalid",
            headers={"Authorization":"Bearer "+os.environ["PILOT_API_KEY"]}) as client:
        driver = MatrixDriver(client,phase)
        if phase=="identity":
            return await driver.identity()
        if phase=="preflight":
            return await driver.preflight()
        outcome = None
        if phase=="export":
            await driver.identity()
        else:
            require(phase=="first" or (phase=="second" and CARD=="04"),"forbidden_phase")
            intent = driver.root/(phase+"-intent.json")
            require(not intent.exists(),"intent_exists_no_replay")
            try:
                outcome = await getattr(driver,phase)()
            except Exception as exc:
                if not intent.exists():
                    raise
                outcome = {"passed":False,"reason":str(exc) if isinstance(exc,FlowStopped) else type(exc).__name__}
            driver.save(phase+"-outcome",outcome)
        readback = await pilot.readback(driver)
        readback["cumulative_attempts"] = PRIOR+readback["model_attempts"]
        return {"outcome":outcome,"readback":readback}


if __name__=="__main__":
    try:
        print("MATRIX_RESULT="+json.dumps(asyncio.run(main(sys.argv[1])),default=str),flush=True)
    except Exception as exc:
        print("MATRIX_RESULT="+json.dumps({"error":str(exc) if isinstance(exc,FlowStopped) else type(exc).__name__}),flush=True)
        raise SystemExit(1) from None
