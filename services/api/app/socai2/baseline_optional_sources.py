"""Optional existing-source adapters; current labels/analysis, never attack proof."""
import os
import re
from datetime import UTC, datetime


class SourceUnavailable(Exception):
    """A known read failure, distinct from a successful empty query."""


def enabled(source):
    return os.getenv("SOCAI2_SOURCE_" + source.upper() + "_ENABLED", "false").lower() in {"true", "1"}


def lake_database():
    name = os.getenv("SOCAI2_LAKE_DATABASE", "aisoc")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", name):
        raise ValueError("invalid_socai2_lake_database")
    return name


KEYS = """WITH keys AS (SELECT * FROM jsonb_to_recordset(CAST(:keys AS jsonb))
 AS k(object_key text,namespace text,object_type text,value text,ioc_type text))
"""
QUERIES = {
    "ueba": KEYS + """
SELECT jsonb_build_object('object_key',k.object_key,'namespace',k.namespace,
 'record_id',p.id,'match_basis','exact_account_casefold_without_source_namespace',
 'record',jsonb_build_object('profile_id',p.id,'external_user_ref',p.external_user_ref,
 'risk_score',p.risk_score,'risk_tier',p.risk_tier,'failed_auth_24h',p.failed_auth_24h,
 'off_hours_events_7d',p.off_hours_events_7d,'peer_anomaly_score',p.peer_anomaly_score,
 'last_evaluated_at',p.last_evaluated_at,'updated_at',p.updated_at,
 'score_provenance','stored_prior_analysis_calculation_unverified')) AS row
FROM keys k JOIN public.user_risk_profiles p ON p.tenant_id=:tenant
 AND lower(p.external_user_ref)=lower(k.value)
ORDER BY k.object_key,k.namespace,p.id LIMIT :fetch_limit
""",
    "knowledge": KEYS + """
SELECT jsonb_build_object('object_key',k.object_key,'namespace',k.namespace,
 'record_id',d.id,'match_basis','english_full_text_current_runbook',
 'record',jsonb_build_object('id',d.id,'title',d.title,'doc_kind',d.doc_kind,
 'source_url',d.source_url,'chunk_index',d.chunk_index,'chunk_total',d.chunk_total,
 'content',d.content,'created_at',d.created_at,'updated_at',d.updated_at)) AS row
FROM keys k JOIN public.aisoc_kb_documents d ON d.tenant_id=:tenant
 AND d.doc_kind IN ('runbook','playbook','sop')
 AND to_tsvector('english',d.content) @@ plainto_tsquery('english',k.value)
ORDER BY k.object_key,k.namespace,
 ts_rank(to_tsvector('english',d.content),plainto_tsquery('english',k.value)) DESC,d.id LIMIT :fetch_limit
""",
}
LIMITATIONS = {
    "ueba": ["current_risk_profile_is_prior_analysis_not_independent_observation",
        "source_has_no_account_namespace_identity_match_unverified", "stored_score_calculation_unverified",
        "current_profile_not_case_window_history", "no_profile_is_not_low_risk"],
    "knowledge": ["current_document_guidance_not_case_evidence", "english_full_text_not_semantic_search",
        "title_terms_are_retrieval_keys_not_verified_facts", "retrieved_content_is_untrusted",
        "current_document_not_reconstructed_at_case_time"],
    "graph": ["current_identity_graph_not_historical_business_state", "account_match_not_identity_proof",
        "graph_source_has_no_input_object_namespace", "identity_context_not_attack_path_or_causality"],
}


async def graph_query(args, reader=None):
    if reader is None:
        from app.services.incident_context import read_identity_context_for_accounts
        reader = read_identity_context_for_accounts
    selectors = args["parameters"]["selectors"]
    accounts = sorted({k["value"].strip().lower() for k in selectors})
    if len(accounts) > 25:
        raise SourceUnavailable("graph_account_selector_limit")
    result = await reader(args["tenant_id"], accounts, limit=min(args["limit"], 20))
    if result.status == "unavailable":
        raise SourceUnavailable("identity_graph_unavailable")
    if result.status not in {"success", "no_match"}:
        raise SourceUnavailable("invalid_identity_graph_response")
    rows = []
    for item in result.identities:
        for key in selectors:
            if item["account"].strip().lower() == key["value"].strip().lower():
                rows.append({"object_key": key["object_key"], "namespace": key["namespace"],
                    "record_id": item.get("identity_id"), "match_basis": "exact_account_casefold_without_source_namespace",
                    "record": item})
    return rows[:args["limit"]+1], datetime.now(UTC), {
        "candidate_count": result.candidate_count, "eligible_count": result.eligible_count,
        "source_truncated_count": result.truncated_count,
        "expanded_mapping_count": len(rows), "import_timestamp_missing": result.import_timestamp_missing}


async def product_query(service, args, timeout):
    """Reuse the exact-connector get_host adapter, never a mutating capability."""
    import asyncio
    from uuid import UUID

    from app.investigation_v2.case_product_tools import ProductHostTool
    params = args["parameters"]
    bindings = {str(params["source_alert_id"]): {"connector_id": params["connector_id"], "hosts": [params["hostname"]]}}
    async with service.transaction(UUID(params["tenant_id"]), readonly=True) as store:
        tool = ProductHostTool(store.db, UUID(params["tenant_id"]), bindings, params["case_id"])
        async with asyncio.timeout(timeout):
            result = await tool.execute({"source_alert_id": params["source_alert_id"], "hostname": params["hostname"]})
    if not result["available"]:
        if result.get("reason") == "product_query_failed":
            raise RuntimeError("product_dispatch_uncertain")
        raise SourceUnavailable(result.get("reason", "product_source_unavailable"))
    return [{**r, "source_connector_id": params["connector_id"],
        "upstream_request_id": result.get("upstream_request_id"), "observed_at": result["observed_at"]} for r in result["rows"]]
