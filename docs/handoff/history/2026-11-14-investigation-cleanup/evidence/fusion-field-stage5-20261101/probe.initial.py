"""Four local field-projection observations; no Run, model, DB or Tool dispatch.

Uses actual case_context/model_context with substituted DB result rows.
Each observation is saved immediately; failures retain preceding evidence.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/api"))
from app.investigation_v2.case_analysis import CaseAnalysisScope, case_context, model_context, digest
from app.models.alert import Alert
from app.models.case import Case

NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)
TENANT, CASE, ALERT, CONNECTOR, EVENT, RUN = [UUID(int=i) for i in (1, 2, 3, 4, 5, 6)]
observations = []


def save(error=None):
    Path(__file__).with_name("observations.json").write_text(json.dumps({
        "scope": "synthetic local field projections; no external calls; not acceptance",
        "observation_count": len(observations), "observations": observations, "error": error,
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }, ensure_ascii=False, indent=2, default=str)+"\n", encoding="utf-8")


def observe(name, condition, **actual):
    assert condition, name
    observations.append({"name": name, "current_behaviour_confirmed": True, **actual})
    save()


def result(one=None, rows=()):
    r = MagicMock()
    r.scalar_one_or_none.return_value = one
    r.scalars.return_value.all.return_value = list(rows)
    r.all.return_value = list(rows)
    return r


async def main():
    case = Case(id=CASE, tenant_id=TENANT, title="Synthetic field projection", description="Synthetic scope", alert_ids=[ALERT])
    alert = Alert(id=ALERT, tenant_id=TENANT, title="Synthetic received alert", description="Synthetic source description",
        severity="high", status="closed", disposition="benign_true_positive", event_time=NOW,
        connector_id=CONNECTOR, connector_type="crowdstrike", source_event_ids=[str(UUID(int=101))],
        rule_id="received-rule-73", rule_name="Received rule seventy three", external_id="vendor-finding-91",
        mitre_tactics=["Execution", "Persistence"], mitre_techniques=["T1059"], confidence=87,
        confidence_label="high", confidence_rationale=[{"source": "fusion", "description": "received scoring basis"}],
        ai_score=0.96, ai_summary="Earlier triage reason", ai_recommendations=["Check received process evidence"],
        affected_hosts=["host-01"], affected_users=["synthetic-user"], affected_ips=[], entities=[],
        raw_event={"synthetic_note": "This raw object does not duplicate the separate detection columns."},
        enrichment_data={"socai2_fusion": {"incident_id": str(UUID(int=31)),
            "identity": {"source_alert_id": str(UUID(int=71)), "source": "received-original-vendor"},
            "ioc_lookup": {"status": "matched", "matches": [{"value": "a"*64, "source": "synthetic-ti"}]}}})
    triage = SimpleNamespace(id=EVENT, run_id=RUN, ts=NOW-timedelta(minutes=10),
        payload={"verdict": "true_positive", "confidence": 0.96, "rationale": "Earlier triage reason",
                 "auto_closed": False, "findings": ["Received triage finding"], "proposed_actions": ["Check source"]})
    request = CaseAnalysisScope(start=NOW-timedelta(minutes=1), end=NOW+timedelta(minutes=1))
    async def context():
        db = SimpleNamespace(execute=AsyncMock(side_effect=[result(one=case), result(rows=[alert]),
                                             result(rows=[(str(ALERT), triage)])]))
        return await case_context(db, TENANT, CASE, request)

    frozen = await context()
    visible = model_context(frozen)
    a = next(e["data"] for e in frozen["evidence"] if e["kind"] == "alert")
    v = next(e["data"] for e in visible["evidence"] if e["kind"] == "alert")
    expected = ["rule_id", "rule_name", "mitre_tactics", "mitre_techniques", "confidence", "confidence_label",
                "confidence_rationale", "ai_score", "ai_recommendations", "connector_type", "external_id"]
    observe("received_detection_metadata_missing_from_case_and_model_projection",
            all(getattr(alert, key) is not None and key not in a and key not in v for key in expected)
            and "received-original-vendor" not in json.dumps(visible),
            populated_columns=expected, frozen_alert_fields=sorted(a), model_alert_fields=sorted(v),
            fusion_identity_present_in_received_row=True, fusion_ioc_lookup_present_in_received_row=True,
            frozen_context=frozen, model_view=visible)

    t = next(e for e in frozen["evidence"] if e["kind"] == "triage")
    observe("triage_event_is_separate_but_score_and_details_not_projected",
            t["event_id"] == str(EVENT) and t["data"]["verdict"] == "true_positive"
            and a["disposition"] == "benign_true_positive" and "confidence" not in t["data"]
            and "findings" not in t["data"] and "proposed_actions" not in t["data"],
            original_event_payload=triage.payload, frozen_triage=t, current_human_disposition=a["disposition"],
            source_run_and_time_present_in_input={"run_id": str(RUN), "ts": triage.ts},
            note="Event ID remains resolvable, but run/time are not in this frozen triage projection.")

    before = digest({k: value for k, value in frozen.items() if k != "question"})
    alert.rule_name = "Updated received rule name"
    alert.confidence = 33
    changed = await context()
    after = digest({k: value for k, value in changed.items() if k != "question"})
    observe("unprojected_metadata_changes_are_also_absent_from_material_fingerprint",
            before == after, before=before, after=after, changed_columns=["rule_name", "confidence"],
            note="Fingerprint is over consumed material. This does not claim fixed-window lake rows changed or cached queries ran.")

    alert.raw_event = {"class_uid": 1007, "activity_id": 1,
        "process": {"name": "synthetic.exe", "pid": 24601, "cmd_line": "synthetic.exe --observe",
                    "parent_process": {"name": "parent.exe", "pid": 24600}}}
    with_ocsf = await context()
    ocsf_view = model_context(with_ocsf)
    saved_source = next(e["data"]["source_material"]["raw_event"] for e in with_ocsf["evidence"] if e["kind"] == "alert")
    visible_source = next(e["data"]["source_material"]["raw_event"] for e in ocsf_view["evidence"] if e["kind"] == "alert")
    observe("retained_ocsf_business_values_have_no_separate_model_projection_when_raw_blocked",
            json.loads(saved_source["text"])["process"]["pid"] == 24601
            and visible_source["text"] == "" and visible_source["model_omission_reason"] == "llm_input_contract"
            and "24601" not in json.dumps(ocsf_view),
            saved_raw=saved_source, model_raw=visible_source,
            note="Existing guard is preserved. This identifies missing permitted semantic fields, not a request to bypass the guard or ask upstream to alter input.")


try:
    asyncio.run(main())
except Exception as exc:
    save({"type": type(exc).__name__, "message": str(exc)})
    raise
print(json.dumps({"observations": len(observations), "confirmed": True}))
