"""Event selection and semantic update identity, separate from preserved raw inputs."""

SELECTION_VERSION = "socai2.incident-selection.v1"


def selected_source_sql(source_sql, limit_sql):
    # Fragments are server-owned SQL, never caller supplied strings.
    source = source_sql.replace(
        "EXISTS\n   (SELECT 1 FROM socai2.incident_alerts l WHERE l.tenant_id=a.tenant_id AND l.alert_id=a.id AND l.incident_id=:id)",
        "a.id IN (SELECT alert_id FROM picked)")
    return f"""WITH picked AS MATERIALIZED (
        SELECT alert_id,linked_at FROM socai2.incident_alerts
        WHERE tenant_id=:tenant AND incident_id=:id
        ORDER BY linked_at DESC,alert_id ASC LIMIT ({limit_sql})),
      raw AS ({source})
      SELECT raw.jsonb_build_object || jsonb_build_object(
        'selection_version','{SELECTION_VERSION}',
        'input_selection',jsonb_build_object('policy','recently_linked',
          'limit',({limit_sql}),'order','linked_at_desc_alert_id_asc',
          'captured_at',statement_timestamp(),
          'total_member_count',(SELECT count(*) FROM socai2.incident_alerts WHERE tenant_id=:tenant AND incident_id=:id),
          'selected_count',(SELECT count(*) FROM picked),
          'omitted_count',(SELECT count(*) FROM socai2.incident_alerts WHERE tenant_id=:tenant AND incident_id=:id)-(SELECT count(*) FROM picked),
          'selected_alert_ids',coalesce((SELECT jsonb_agg(alert_id ORDER BY linked_at DESC,alert_id ASC) FROM picked),'[]'::jsonb)))
      FROM raw"""


def assessment_sql(value):
    return f"""CASE WHEN {value} IS NULL OR {value}='null'::jsonb THEN NULL ELSE
      jsonb_build_object('verdict',{value}->'verdict','rationale',{value}->'rationale',
        'confidence',{value}->'confidence','score_state',{value}->'score_state',
        'recommendations',coalesce((SELECT jsonb_agg(rec-ARRAY['id','source_refs','source_ids','actor','created_at','updated_at'] ORDER BY ord)
          FROM jsonb_array_elements(COALESCE(NULLIF({value}->'recommendations','null'::jsonb),'[]'::jsonb)) WITH ORDINALITY AS recommendations(rec,ord)), '[]'::jsonb)) END"""


def change_view_sql(body):
    triage = assessment_sql("member->'triage'")
    feedback = assessment_sql("member->'feedback'")
    return f"""jsonb_build_object('version','socai2.incident-change.v1','members',
      coalesce((SELECT jsonb_agg(jsonb_build_object('alert_id',member->'alert'->'id',
        'triage',CASE WHEN {body}->'triage_validation'->(member->'alert'->>'id')->>'usable'='true'
          THEN {triage} ELSE NULL END,'feedback',{feedback}) ORDER BY member->'alert'->>'id')
        FROM jsonb_array_elements({body}->'members') member),'[]'::jsonb))"""


def coverage(source, diagnosis):
    """Only saved validated member decisions establish actual analysis coverage."""
    selection = source.get("input_selection")
    if source.get("selection_version") != SELECTION_VERSION or not isinstance(selection, dict):
        return None
    assessment = (diagnosis or {}).get("delivery_assessment")
    unknown = {"state": "unknown", "analyzed_count": None, "unresolved_count": None,
               "not_analyzed_count": None, "covered_alert_ids": None, "limitations": ["analysis_coverage_unavailable"]}
    if not isinstance(assessment, dict):
        return unknown
    members = assessment.get("member_coverage", {})
    selected = set(selection["selected_alert_ids"])
    expected = members.get("expected_ids", [])
    covered = set(members.get("analyzed_ids", []))
    unresolved = set(assessment.get("review_items", {}).get("unresolved_member_ids", []))
    if set(expected) != selected or len(expected) != len(selected) or not unresolved <= covered <= selected:
        return unknown
    missing = selected - covered
    state = "none" if not covered else "partial" if missing or selection["omitted_count"] else "complete"
    limitations = list(assessment.get("reasons", []))
    if selection["omitted_count"]:
        limitations.append("incident_members_not_selected")
    return {"state": state, "analyzed_count": len(covered - unresolved), "unresolved_count": len(unresolved),
            "not_analyzed_count": len(missing), "covered_alert_ids": sorted(covered), "limitations": limitations}
