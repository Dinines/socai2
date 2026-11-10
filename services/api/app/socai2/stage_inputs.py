"""Shared A/I input identity SQL; no services or model calls."""
from typing import Literal

Freshness = Literal["current", "stale", "unverified", "unavailable"]
VERSION = "socai2.stage-result.v1"
TRIAGE_VALIDATION_VERSION = "socai2.incident-triage.v1"
QUERY_RECEIPTS_VERSION = "socai2.incident-queries.v1"
# Read the entire input in one statement. Own output pointers and ingestion clocks
# are excluded so publishing a result does not make that result stale immediately.
SOURCE_SQL = """SELECT jsonb_build_object('version',CAST(:version AS text),'kind',CAST(:kind AS text),
 'parent',CASE WHEN :kind='alert_basic' THEN NULL ELSE
   (SELECT to_jsonb(i)-ARRAY['latest_diagnosis_id','row_version','business_updated_at']
    FROM socai2.incidents i WHERE i.tenant_id=:tenant AND i.id=:id) END,
 'members',coalesce((SELECT jsonb_agg(jsonb_build_object(
   'alert',to_jsonb(a)-ARRAY['latest_triage_id','latest_explanation_id','row_version','business_updated_at','source_updated_at'],
   'material',(SELECT to_jsonb(v) FROM socai2.alert_materials v WHERE v.tenant_id=a.tenant_id AND v.alert_id=a.id AND v.id=a.latest_material_id),
   'objects',coalesce((SELECT jsonb_agg(to_jsonb(o) ORDER BY o.id) FROM socai2.alert_objects o
      WHERE o.tenant_id=a.tenant_id AND o.alert_id=a.id AND o.material_id=a.latest_material_id),'[]'::jsonb),
   'triage',CASE WHEN :kind='alert_basic' THEN NULL ELSE (SELECT to_jsonb(t) FROM socai2.alert_assessments t
      WHERE t.tenant_id=a.tenant_id AND t.alert_id=a.id AND t.id=a.latest_triage_id AND t.kind='triage') END,
   'feedback',(SELECT to_jsonb(f) FROM socai2.alert_assessments f WHERE f.tenant_id=a.tenant_id AND f.alert_id=a.id
      AND f.id=a.latest_feedback_id AND f.kind='human_feedback'),
   'membership',CASE WHEN :kind='alert_basic' THEN NULL ELSE (SELECT to_jsonb(l) FROM socai2.incident_alerts l
      WHERE l.tenant_id=a.tenant_id AND l.incident_id=:id AND l.alert_id=a.id) END)
   ORDER BY a.id) FROM socai2.alerts a WHERE a.tenant_id=:tenant AND
   ((:kind='alert_basic' AND a.id=:id) OR (:kind='incident_diagnosis' AND EXISTS
   (SELECT 1 FROM socai2.incident_alerts l WHERE l.tenant_id=a.tenant_id AND l.alert_id=a.id AND l.incident_id=:id)))), '[]'::jsonb))"""


def freshness_sql(kind, subject_sql, run_sql):
    # Only hard-coded server SQL fragments are accepted by callers. Source and
    # frozen input are compared as JSONB in the SAME statement snapshot. Large
    # raw payloads never enter the C1/model result merely to test equality.
    if kind not in {"alert_basic", "incident_diagnosis"}:
        raise ValueError("unsupported stage kind")
    key = "alert_id" if kind == "alert_basic" else "incident_id"
    source = SOURCE_SQL
    if kind == "incident_diagnosis":
        # Old frozen inputs remain comparable under their original contract.
        source = f"SELECT CASE WHEN sf.content_json->>'query_receipts_version'='{QUERY_RECEIPTS_VERSION}' THEN ({incident_source_sql(with_queries=True)}) WHEN sf.content_json->>'triage_validation_version'='{TRIAGE_VALIDATION_VERSION}' THEN ({incident_source_sql()}) ELSE ({SOURCE_SQL}) END"
    source = source.replace(":kind", "'" + kind + "'").replace(":id", "st.sid").replace(":version", "'" + VERSION + "'")
    return f"""COALESCE((SELECT CASE
       WHEN sf.id IS NULL OR sf.material_state<>'complete' OR sf.content_json IS NULL THEN 'unavailable'
       WHEN sf.schema_version<>'{VERSION}' OR sf.content_json->>'version' IS DISTINCT FROM '{VERSION}' THEN 'unverified'
       WHEN sf.content_json->>'kind' IS DISTINCT FROM '{kind}' THEN 'unverified'
       WHEN sf.content_json ? 'triage_validation_version' AND sf.content_json->>'triage_validation_version'<>'{TRIAGE_VALIDATION_VERSION}' THEN 'unverified'
       WHEN sf.content_json ? 'query_receipts_version' AND sf.content_json->>'query_receipts_version'<>'{QUERY_RECEIPTS_VERSION}' THEN 'unverified'
       WHEN sf.content_json=({source}) THEN 'current' ELSE 'stale' END
      FROM (SELECT CAST({subject_sql} AS uuid) AS sid, CAST(({run_sql}) AS uuid) AS rid) st
      JOIN socai2.runs sr ON sr.id=st.rid AND sr.{key}=st.sid
      LEFT JOIN socai2.artifacts sf ON sf.tenant_id=sr.tenant_id
       AND sf.id=sr.input_artifact_id AND sf.run_id=sr.id AND sf.{key}=sr.{key} AND sf.kind='input_snapshot'
      WHERE sr.tenant_id=:tenant AND sr.kind='{kind}'), 'unavailable')"""


def incident_source_sql(*, with_queries=False):
    """Freeze paired A validity and I members in the same statement snapshot.

    No Alert locks: publication retains the established Alert -> Incident order.
    The nested freshness expression uses only the unchanged A source contract.
    """
    fresh = freshness_sql("alert_basic", "a.id", "t.source_run_id")
    sql = f"""SELECT frozen.body || jsonb_build_object(
      'triage_validation_version','{TRIAGE_VALIDATION_VERSION}',
      'triage_validation',coalesce((SELECT jsonb_object_agg(a.id::text,jsonb_build_object(
        'triage_id',t.id,'source_run_id',t.source_run_id,'freshness',f.value,
        'usable',COALESCE(t.id IS NOT NULL AND r.state='completed' AND f.value='current'
          AND t.input_material_id IS NOT DISTINCT FROM a.latest_material_id,false)) ORDER BY a.id)
        FROM jsonb_array_elements(frozen.body->'members') member
        JOIN socai2.alerts a ON a.tenant_id=:tenant AND a.id=CAST(member->'alert'->>'id' AS uuid)
        LEFT JOIN socai2.alert_assessments t ON t.tenant_id=a.tenant_id AND t.alert_id=a.id
          AND t.id=a.latest_triage_id AND t.kind='triage'
        LEFT JOIN socai2.runs r ON r.tenant_id=a.tenant_id AND r.alert_id=a.id
          AND r.id=t.source_run_id AND r.kind='alert_basic'
        CROSS JOIN LATERAL (SELECT {fresh} AS value) f),'{{}}'::jsonb))
      FROM ({SOURCE_SQL}) frozen(body)"""
    if not with_queries:
        return sql
    # One statement snapshot, using the exact adopted and validated A Run.
    # The step/output pointer proves that each artifact is an actual receipt.
    return f"""SELECT paired.body || jsonb_build_object(
      'query_receipts_version','{QUERY_RECEIPTS_VERSION}',
      'triage_queries',coalesce((SELECT jsonb_object_agg(v.key,
        (SELECT coalesce(jsonb_agg(to_jsonb(receipt) ORDER BY receipt.step_id,receipt.id),'[]'::jsonb)
         FROM (SELECT f.id,f.tenant_id,f.alert_id,f.run_id,f.step_id,f.kind,f.schema_version,
                      f.content_json,f.sha256,f.size_bytes,f.material_state,f.blob_ref
               FROM socai2.artifacts f JOIN socai2.run_steps s
                 ON s.tenant_id=f.tenant_id AND s.run_id=f.run_id AND s.id=f.step_id AND s.output_artifact_id=f.id
               WHERE f.tenant_id=:tenant AND f.alert_id=CAST(v.key AS uuid)
                 AND f.run_id=CAST(v.value->>'source_run_id' AS uuid)
                 AND f.kind='tool_response' AND s.kind='tool') receipt)
        ORDER BY v.key) FROM jsonb_each(paired.body->'triage_validation') v
        WHERE v.value->>'usable'='true'),'{{}}'::jsonb))
      FROM ({sql}) paired(body)"""

