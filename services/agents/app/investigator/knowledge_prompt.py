"""Connect default investigation to the existing tenant KB reader and citations."""
from __future__ import annotations

import hashlib
import html
import re
from copy import deepcopy
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from .state import InvestigatorState


async def prefetch_knowledge(state: InvestigatorState) -> None:
    """Read once per Run; retain the exact adopted text and source mapping."""
    if state.knowledge_base_read:
        return
    # Lazy because the existing reader imports the investigator sanitizer.
    from app.context import knowledge_base as kb

    # The Case summary includes IDs, severity and multiple descriptions. The
    # existing full-text endpoint ANDs query words; use the source alert title
    # rather than requiring a runbook to contain Case transport metadata.
    raw = state.raw_alert or {}
    query_text = raw.get("rule_name")
    if not isinstance(query_text, str) or not query_text.strip():
        linked = raw.get("alerts")
        first = linked[0] if isinstance(linked, list) and linked and isinstance(linked[0], dict) else {}
        query_text = first.get("title") or state.alert_summary
    query = kb.query_for(str(query_text))
    try:
        read = (await kb.fetch_runbooks(state.tenant_id, query=query)).as_read()
        read, block = kb.build_prompt_material(read, nonce=uuid4().hex)
    except Exception as exc:  # noqa: BLE001 — a missing source does not erase the alert.
        read = dict(kb.make_read(state.tenant_id, query=query, status="unavailable", reason=type(exc).__name__))
        block = ""
    read["prompt_block"] = block
    read["prompt_sha256"] = hashlib.sha256(block.encode("utf-8")).hexdigest()
    state.knowledge_base_read = read
    state.log_tool_call(
        agent="ReconAgent", tool_name="knowledge_base.fetch_runbooks",
        args={"tenant_id": state.tenant_id, "query": query}, result=deepcopy(read),
        success=read.get("status") in {"success", "no_match"},
    )


def knowledge_prompt_append(state: InvestigatorState) -> str:
    """All four nodes consume the same source material, including read status."""
    if not state.knowledge_base_read:
        return ""
    from app.context.knowledge_base import render_read_status

    return "\n\n".join(part for part in (
        render_read_status(state.knowledge_base_read), state.knowledge_base_read.get("prompt_block", ""),
    ) if part)


def record_knowledge_citations(state: InvestigatorState, agent: str, content: str) -> None:
    """Record actual model markers separately from material offered to it."""
    if not state.knowledge_base_read:
        return
    from app.context.knowledge_base import record_model_citations

    read = state.knowledge_base_read
    record_model_citations(read, content)
    facts = {key: deepcopy(read.get(key, [])) for key in ("model_citations", "unresolvable_citations", "cited_sources")}
    read.setdefault("model_citations_by_agent", {})[agent] = facts
    state.log_tool_call(
        agent=agent, tool_name="knowledge_base.model_citations", args={"agent": agent}, result=facts,
        success=not facts["unresolvable_citations"],
    )


def report_knowledge_references(state: InvestigatorState) -> str:
    """Resolve markers the report actually used; never invent a model citation."""
    facts = state.knowledge_base_read.get("model_citations_by_agent", {}).get("ReportWriterAgent", {})
    rows = facts.get("cited_sources", [])
    lines = []
    def literal(value: object) -> str:
        # Metadata is still tenant-authored text. Render it as literal prose,
        # so appending references cannot inject raw HTML or Markdown links.
        return re.sub(r"([\\`*{}\[\]()#+!|])", r"\\\1", html.escape(str(value), quote=True))
    for row in rows:
        # Text was already sanitized and bounded by the existing KB reader.
        lines.append(
            f"- [{row['marker']}] {literal(row['title'])} — {literal(row.get('source_url') or 'No source URL')}; "
            f"document {row['doc_id']}, chunk {int(row['chunk_index']) + 1}/{row['chunk_total']}; "
            f"content SHA-256 {row.get('content_sha256') or 'unknown'}."
        )
    unresolved = facts.get("unresolvable_citations", [])
    if unresolved:
        lines.append("Unresolved knowledge references: " + ", ".join(f"[{marker}]" for marker in unresolved) + ".")
    return "\n\n## Knowledge references\n" + "\n".join(lines) if lines else ""
