"""A/I initial task registration in the native alert persistence transaction."""
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid5


def load_policy(path=None):
    selected = Path(path or os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"])
    if not selected.is_absolute():
        raise ValueError("explicit analysis task policy required")
    policy = json.loads(selected.read_text())
    for key in ("retry_limit", "retry_delay_seconds"):
        if type(policy[key]) is not int or policy[key] < 0:
            raise ValueError("invalid initial analysis retry policy")
    return policy


def initial_key(alert_id, subject_type="alert"):
    return uuid5(alert_id, "socai2." + subject_type + ".initial-analysis.v1")


async def register_initial(conn, tenant_id, alert_id, now, policy, *, subject_type="alert"):
    """Only called for a newly inserted subject; no replay/backfill/re-triage branch."""
    kind = {"alert": "alert_triage", "incident": "incident_diagnosis"}[subject_type]
    operation = initial_key(alert_id, subject_type)
    identity = uuid5(tenant_id, "socai2.analysis-task:" + str(operation))
    body = {"kind": kind, "subject_type": subject_type, "subject_id": str(alert_id),
            "intent": "initial", "source": "ingress", "submitted_by": None, "request_payload": {}}
    fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode()).hexdigest()
    await conn.execute("""INSERT INTO socai2.analysis_tasks
        (id,tenant_id,kind,subject_type,subject_id,intent,source,operation_key,request_hash,
         request_payload,submitted_at,state,retry_limit,retry_delay_seconds)
        VALUES ($1,$2,$9,$10,$3,'initial','ingress',$4,$5,'{}',$6,'accepted',$7,$8)
        ON CONFLICT (tenant_id,kind,operation_key) DO NOTHING""",
        identity, tenant_id, alert_id, operation, fingerprint, now, policy["retry_limit"], policy["retry_delay_seconds"], kind, subject_type)
    saved = await conn.fetchrow("""SELECT id,request_hash FROM socai2.analysis_tasks
        WHERE tenant_id=$1 AND kind=$3 AND operation_key=$2""", tenant_id, operation, kind)
    if saved is None or saved["request_hash"] != fingerprint:
        raise ValueError("initial_analysis_operation_conflict")
    await conn.execute("""INSERT INTO socai2.analysis_subject_state
        (tenant_id,subject_type,subject_id,registered_at) VALUES ($1,$4,$2,$3)
        ON CONFLICT (tenant_id,subject_type,subject_id) DO NOTHING""", tenant_id, alert_id, now, subject_type)
    return saved["id"]
