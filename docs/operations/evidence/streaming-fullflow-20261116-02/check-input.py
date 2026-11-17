"""Use current A/I/C3/Deep/C6 builders on the newly generated business materials."""

import json
import os
from pathlib import Path
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "input"
config = json.loads((OUT.parent / "preparation-config.json").read_text())
assert config["investigation_policy_file"]
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(
    ROOT / config["investigation_policy_file"]
)
from app.socai2 import (
    alert_model_boundary,
    case_followup_input,
    case_model_boundary,
    case_query_snapshot,
    incident_model_boundary,
    runtime_policy,
)
from app.socai2.baseline_context import Context
from app.socai2.stage_inputs import QUERY_RECEIPTS_VERSION

policy = runtime_policy.active_policy()
members = json.loads((OUT / "fusion-projected-materials.json").read_text())


def identity(value):
    return str(uuid5(NAMESPACE_URL, OUT.parent.name + ":" + value))


def write(name, value):
    with (VIEWS / name).open("x") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, default=str)


VIEWS = OUT / "model-views-02"
VIEWS.mkdir(exist_ok=False)


def build_case(selected, label):
    members = selected
    stamp = members[-1]["alert"]["event_time"]
    cid = identity("case-" + label)
    messages = {}
    scope = {
        "kind": "whole_case",
        "alert_ids": [m["alert"]["id"] for m in members],
        "object_keys": [],
        "window_start": members[0]["alert"]["event_time"],
        "window_end": stamp,
        "limitations": [],
    }
    roles = {"$.case": "source_label"}
    alerts = {}
    for member in members:
        aid = member["alert"]["id"]
        alerts[aid] = {
            **member,
            "limitations": [],
            "triage_freshness": "unverified",
            "triage_usable": False,
            "triage_run_state": None,
            "queries": [],
        }
        for name in ("alert", "alert.event_time", "objects", "material"):
            roles["$.alerts." + aid + "." + name] = "source_label"
        roles["$.alerts." + aid + ".membership"] = "execution_receipt"
    raw = {
        "schema_version": "socai2.baseline-context.v1",
        "case_id": cid,
        "captured_at": stamp,
        "scope": scope,
        "case": {
            "id": cid,
            "title": "主机活动调查",
            "scope_revision": 1,
            "state": "open",
        },
        "alerts": alerts,
        "incidents": {},
        "tasks": {},
        "current_assessment": None,
        "assessment_members": [],
        "assessment_sources": [],
        "prior_results": {},
        "adopted_task_revisions": {},
        "adopted_artifacts": {},
        "omissions": [],
        "questions": [
            {
                "id": "activity",
                "text": "这些记录反映了哪些活动及其关联？",
                "scope": scope,
                "evidence_requirements": ["观察记录"],
                "state": "open",
                "answer": None,
                "evidence_refs": [],
                "limitations": [],
            }
        ],
        "citation_roles": roles,
        "query_receipts_version": case_query_snapshot.VERSION,
        "case_input_profile": policy.case_io.identity,
    }
    context = Context.model_validate(raw)
    base = case_model_boundary.build(
        context,
        identity("context"),
        [],
        [],
        {m["alert"]["id"]: m["material"] for m in members},
        execution_time=stamp,
    )
    assert base["ready"], base["reason"]
    assert len(base["case_boundary"]["member_aliases"]) == len(members)
    messages["C3"] = case_model_boundary.messages(base, context, [])[0]
    for stage in ("Deep", "C6"):
        result = case_followup_input.build(
            stage,
            context,
            base,
            {},
            question_id="activity" if stage == "Deep" else None,
        )
        assert result["ready"], result["reason"]
        messages[stage] = result["messages"]
    return {stage + "-" + label: value for stage, value in messages.items()}


messages = {}
with patch(
    "socket.socket", side_effect=AssertionError("offline audit cannot use network")
):
    for index, member in enumerate(members, 1):
        source = {
            "parent": member["alert"],
            "members": [member],
            "query_receipts_version": QUERY_RECEIPTS_VERSION,
            "triage_queries": {},
        }
        messages["A" + str(index)] = alert_model_boundary.build(
            source,
            identity("A" + str(index)),
            [],
            policy.alert_io,
            execution_time=member["alert"]["event_time"],
        )[0]
    for label, selected in (("initial-3", members[:3]), ("update-4", members)):
        source = {
            "parent": {"id": identity("incident"), "title": "主机活动调查"},
            "members": selected,
            "triage_validation": {
                m["alert"]["id"]: {"usable": False} for m in selected
            },
            "query_receipts_version": QUERY_RECEIPTS_VERSION,
            "triage_queries": {},
        }
        messages["I-" + label] = incident_model_boundary.build(
            source,
            identity("I-" + label),
            policy.incident_io,
            execution_time=selected[-1]["alert"]["event_time"],
        )[0]
    for label, selected in (
        ("whole-initial-3", members[:3]),
        ("single-initial-1", members[:1]),
        ("whole-update-4", members),
    ):
        messages.update(build_case(selected, label))
    checks = []
    forbidden = [
        "synthetic",
        "fixture",
        "model-blind",
        "blind-templates",
        config["fixture"]["source_namespace"],
        "expected_disposition",
        "expected_verdict",
        "tenant_uid",
        config["batch_id"],
        "decisive_evidence",
        "s01-ingress",
        "program_classification",
    ]
    for stage, body in messages.items():
        visible = "\n".join(m["content"] for m in body)
        user_visible = "\n".join(m["content"] for m in body if m["role"] == "user")
        hits = [token for token in forbidden if token.lower() in visible.lower()]
        sample_hits = [
            token
            for token in ["授权未知", "malicious-backdoor"]
            if token.lower() in user_visible.lower()
        ]
        checks.append(
            {
                "stage": stage,
                "characters": len(visible),
                "forbidden_hits": hits,
                "sample_answer_hint_hits": sample_hits,
                "system_authorization_guidance_only": "授权未知" in visible
                and "授权未知" not in user_visible,
            }
        )
        write("model-view-" + stage + ".json", body)
    write(
        "model-view-checks.json",
        {
            "checks": checks,
            "model_calls": 0,
            "scope": "actual configured input builders; no fabricated prior model answer",
        },
    )
    assert not any(
        row["forbidden_hits"] or row["sample_answer_hint_hits"] for row in checks
    ), checks
print(json.dumps(checks, ensure_ascii=False))
