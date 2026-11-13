"""Versioned C1 copies of the selected A Run's receipts; no tool calls or DDL."""
from sqlalchemy import text

from .stage_inputs import QUERY_RECEIPTS_VERSION, freshness_sql

VERSION = "socai2.case-queries.v1"


def query_rows_sql(alert_sql, run_sql):
    # Callers supply only server-owned SQL fragments, never request strings.
    return f"""SELECT coalesce(jsonb_agg(to_jsonb(receipt) ORDER BY receipt.step_id,receipt.id),'[]'::jsonb)
      FROM (SELECT f.id,f.tenant_id,f.alert_id,f.run_id,f.step_id,f.kind,f.schema_version,
         f.content_json,f.sha256,f.size_bytes,f.material_state,f.blob_ref,
         s.output_artifact_id,s.kind AS step_kind,s.state AS step_state,r.state AS source_run_state
       FROM socai2.artifacts f JOIN socai2.run_steps s ON s.tenant_id=f.tenant_id
         AND s.run_id=f.run_id AND s.id=f.step_id AND s.output_artifact_id=f.id
       JOIN socai2.runs r ON r.tenant_id=f.tenant_id AND r.id=f.run_id AND r.alert_id=f.alert_id
       WHERE f.tenant_id=:tenant AND f.alert_id=CAST({alert_sql} AS uuid)
         AND f.run_id=CAST({run_sql} AS uuid) AND f.kind='tool_response' AND s.kind='tool'
         AND r.kind='alert_basic' AND r.state='completed') receipt"""


def capture_sql(base):
    queries = query_rows_sql("v.key", "v.value->'triage'->>'source_run_id'")
    return f"""SELECT jsonb_set(captured.body,'{{alerts}}',coalesce((
      SELECT jsonb_object_agg(v.key,v.value || jsonb_build_object(
        'triage_run_state',(SELECT r.state FROM socai2.runs r WHERE r.tenant_id=:tenant
          AND r.id=CAST(v.value->'triage'->>'source_run_id' AS uuid) AND r.alert_id=CAST(v.key AS uuid)
          AND r.kind='alert_basic'),
        'queries',CASE WHEN v.value->>'triage_freshness'='current'
          AND v.value->'triage'->'input_material_id'=v.value->'alert'->'latest_material_id'
          THEN ({queries}) ELSE '[]'::jsonb END) ORDER BY v.key)
      FROM jsonb_each(captured.body->'alerts') v),'{{}}'::jsonb))
      || jsonb_build_object('query_receipts_version','{VERSION}') FROM ({base}) captured(body)"""


def source(context):
    """Validate the frozen extension through the existing shared A receipt contract."""
    from .baseline_store import StoreError
    from .incident_query_receipts import receipts

    version = context.get("query_receipts_version")
    if version is None:
        if any(item.get("queries") for item in context["alerts"].values()):
            raise StoreError("case_queries_without_version", 422)
        return {}
    if version != VERSION:
        raise StoreError("case_query_version_unsupported", 422)
    output = {"query_receipts_version": QUERY_RECEIPTS_VERSION, "members": [],
              "triage_validation": {}, "triage_queries": {}}
    for aid, item in context["alerts"].items():
        triage = item.get("triage")
        output["members"].append({"alert": item["alert"], "triage": triage})
        usable = bool(triage and item.get("triage_usable") is True and item.get("triage_freshness") == "current"
                      and item.get("triage_run_state") == "completed"
                      and triage.get("input_material_id") == item["alert"].get("latest_material_id"))
        queries = item.get("queries", [])
        if not isinstance(queries, list) or queries and not usable:
            raise StoreError("case_query_pairing_invalid", 422)
        if usable:
            output["triage_validation"][aid] = {"usable": True, "triage_id": triage["id"],
                "source_run_id": triage["source_run_id"]}
            output["triage_queries"][aid] = queries
        for row in queries:
            if (not row.get("step_id") or row.get("output_artifact_id") != row.get("id")
                    or row.get("step_kind") != "tool" or row.get("source_run_state") != "completed"
                    or row.get("step_state") not in {"completed", "failed", "skipped"}):
                raise StoreError("case_query_execution_pairing_invalid", 422)
    receipts(output)
    return output


def roles(context):
    from .baseline_enrichment import citation_roles

    source(context)
    result = {}
    for aid, item in context["alerts"].items():
        for index, row in enumerate(item.get("queries", [])):
            base = f"$.alerts.{aid}.queries.{index}.content_json"
            result[base] = "execution_receipt"
            result.update({base + path[1:]: role for path, role in citation_roles(row["content_json"]).items()})
    return result


def freshness_statement():
    queries = query_rows_sql("v.key", "v.value->'triage'->>'source_run_id'")
    current_a = freshness_sql("alert_basic", "v.key", "SELECT v.value->'triage'->>'source_run_id'")
    return f"""WITH frozen AS MATERIALIZED (
      SELECT f.content_json AS body FROM socai2.artifacts f JOIN socai2.runs r
        ON r.tenant_id=f.tenant_id AND r.id=f.run_id AND r.case_id=f.case_id
      WHERE r.tenant_id=:tenant AND r.id=:run AND r.kind='baseline'
        AND f.kind='source_snapshot' AND f.material_state='complete'
        AND f.schema_version='socai2.baseline-context.v1'
      ORDER BY f.captured_at,f.id LIMIT 1
    ), checked AS (
      SELECT socai2.baseline_input_freshness(:tenant,:run) AS base,
        CASE WHEN body->>'query_receipts_version' IS NULL THEN NULL
          WHEN body->>'query_receipts_version'<>'{VERSION}' THEN 'case_query_version_unsupported'
          WHEN EXISTS(SELECT 1 FROM jsonb_each(body->'alerts') v WHERE
            (v.value->>'triage_usable'='true' AND ({current_a})<>'current')
            OR (v.value->>'triage_usable'='true' AND NOT EXISTS(
              SELECT 1 FROM socai2.runs ar WHERE ar.tenant_id=:tenant
                AND ar.id=CAST(v.value->'triage'->>'source_run_id' AS uuid)
                AND ar.alert_id=CAST(v.key AS uuid) AND ar.kind='alert_basic' AND ar.state='completed'))
            OR coalesce(v.value->'queries','[]'::jsonb) IS DISTINCT FROM
              CASE WHEN v.value->>'triage_usable'='true' THEN ({queries}) ELSE '[]'::jsonb END)
            THEN 'paired_alert_queries_changed' END AS extra FROM (SELECT (SELECT body FROM frozen) AS body) f
    ) SELECT CASE WHEN extra IS NULL THEN base ELSE base || jsonb_build_object(
        'state',CASE WHEN base->>'state'='unverified' OR extra='case_query_version_unsupported'
          THEN 'unverified' ELSE 'stale' END,
        'reasons',coalesce(base->'reasons','[]'::jsonb)||jsonb_build_array(extra)) END FROM checked"""


async def input_freshness(db, tenant_id, run_id):
    return (await db.execute(text(freshness_statement()), {"tenant": tenant_id, "run": run_id})).scalar_one()
