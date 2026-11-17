"""Baseline function bodies vs current readers, identical synthetic DB rows.

Both use current installed dependencies; no actual DB/Run/model calls.
"""
import asyncio
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from unittest.mock import AsyncMock
from uuid import UUID

import sqlglot
from app.investigation_v2 import incident_reader, case_analysis
from app.models.case import Case
from app.services.processing_context import ASSETS
from test_field_alignment_readers import record, result, TENANT, NOW, fixtures

ROOT = Path(__file__).resolve().parents[4]


def baseline(name):
    path = f"services/api/app/investigation_v2/{name}.py"
    source = subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", "show", f"b400fd0:{path}"], cwd=ROOT).decode()
    module = ModuleType(f"app.investigation_v2._baseline_{name}")
    sys.modules[module.__name__] = module
    exec(compile(source, path, "exec"), module.__dict__)
    return module


async def main():
    old_incident, old_case = baseline("incident_reader"), baseline("case_analysis")
    old_case._entities = old_incident._entities
    alert = record()
    alert.first_seen = NOW + timedelta(hours=2)
    triage = fixtures.verdict(1, "Saved triage", at=NOW+timedelta(hours=3))
    triage[1].payload.update(confidence=.94)
    incident_views = []
    for module in (old_incident, incident_reader):
        db = AsyncMock()
        db.execute.side_effect = [result(rows=[alert]), result(rows=[triage])]
        view = await module.read_incident(db, tenant_id=TENANT, incident_id=fixtures.INCIDENT)
        incident_views.append({"source_alert_id": view.members[0].source_alert_id, "first_seen": view.first_seen,
                              "updated_at": getattr(view, "updated_at", None), "source_updated_at": view.source_updated_at,
                              "entities": view.entities, "tactic_counts": getattr(view, "tactic_counts", None),
                              "triage_confidence": getattr(view.members[0].triage, "confidence", None)})
    assert incident_views[0]["source_alert_id"] == "source-1" and incident_views[1]["source_alert_id"] == "connector-record"
    assert incident_views[0]["first_seen"] != incident_views[1]["first_seen"] == NOW
    assert not any(o["type"] == "hash" for o in incident_views[0]["entities"])
    assert any(o["type"] == "hash" for o in incident_views[1]["entities"])
    assert incident_views[1]["triage_confidence"] == .94
    case = Case(id=UUID(int=30), tenant_id=TENANT, title="Case", alert_ids=[alert.id])
    request = case_analysis.CaseAnalysisRequest(operation_key=UUID(int=40), start=NOW-timedelta(hours=1), end=NOW+timedelta(hours=1))
    cases = []
    for module in (old_case, case_analysis):
        async def build():
            db = AsyncMock()
            db.execute.side_effect = [result(one=case), result(rows=[alert]), result(rows=[triage])]
            return await module.case_context(db, TENANT, case.id, request)
        alert.rule_name = "Stored rule"
        context = await build()
        alert.rule_name = "Changed rule"
        changed = await build()
        cases.append({"rule_present": "detection" in context["evidence"][0]["data"],
                      "triage_confidence": context["evidence"][1]["data"].get("confidence"),
                      "rule_change_invalidates_material": module.digest(context) != module.digest(changed)})
    assert not cases[0]["rule_change_invalidates_material"] and cases[1]["rule_change_invalidates_material"]
    sqlglot.parse_one(ASSETS, read="postgres")
    output = {"baseline": "b400fd0 reader function bodies with current dependencies/models",
              "scope": "synthetic row substitutes; no live DB/model/Run", "incident": dict(zip(("before", "after"), incident_views)),
              "case": dict(zip(("before", "after"), cases)), "asset_postgres_sql_parse": "passed"}
    Path(__file__).with_name("before-after.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str)+"\n", encoding="utf-8")
    print("Incident and Case before/after comparisons passed; asset PG query parsed; zero live calls")


asyncio.run(main())
