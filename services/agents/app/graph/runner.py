"""Shared, durable investigation-graph runner (issue #569).

Both the Kafka auto-triage worker and the manual investigations API run the
*same* orchestration through here, so escalated alerts flow through one
implementation instead of two divergent ones:

* the manual API runs the FULL graph (auto-triage → triage → enrichment →
  investigation → attack-path) via :func:`run_full_investigation`;
* the auto-triage worker, having already produced a governed verdict, runs the
  post-triage escalation subgraph via :func:`run_escalation`.

Every node transition is recorded to the Investigation Ledger (append-only,
``ON CONFLICT (run_id, seq) DO NOTHING``), so a restart mid-investigation
re-runs idempotently — it never loses or duplicates the run. A wall-clock
budget bounds the run; a token budget is enforced upstream by the
``CostGovernor`` and a tool-call budget by the ReAct loop's ``max_iters``.
"""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
import os
import time
from dataclasses import dataclass

import structlog

from app.agents.dispositions import NEEDS_REVIEW
from app.core.cost_telemetry import CostTracker, current_cost_tracker
from app.investigator import ledger as ledger_module
from app.models.state import AgentStatus, InvestigationState

logger = structlog.get_logger()


@dataclass(frozen=True)
class InvestigationBudget:
    """Resource envelope for one investigation (issue #569)."""

    max_seconds: float = 120.0
    max_tokens: int = 20_000
    max_tool_calls: int = 8


_ACTIVE_BUDGET: ContextVar[InvestigationBudget | None] = ContextVar("aisoc_graph_budget", default=None)


def current_investigation_budget() -> InvestigationBudget | None:
    """The existing runner's limits, visible to its nested model loop only."""
    return _ACTIVE_BUDGET.get()


def default_budget() -> InvestigationBudget:
    return InvestigationBudget(
        max_seconds=float(os.getenv("AISOC_INVESTIGATION_MAX_SECONDS", "120")),
        max_tokens=int(os.getenv("AISOC_MAX_TOKENS_PER_ALERT", "20000")),
        max_tool_calls=int(os.getenv("AISOC_INVESTIGATION_MAX_TOOL_CALLS", "8")),
    )


def _budget_exhausted(budget: InvestigationBudget) -> str | None:
    """Why this run must stop now, or None if it may continue.

    Reads the active `CostTracker`, which every LLM call records into
    through the contract layer, so this sees real spend rather than an
    estimate. No tracker bound means no measurement, and an unmeasured run
    is allowed to continue: refusing on the absence of telemetry would stop
    every run in a deployment that has not configured it.
    """
    tracker = current_cost_tracker()
    if tracker is None:
        return None
    if budget.max_tokens and tracker.tokens_used >= budget.max_tokens:
        return f"token budget exhausted ({tracker.tokens_used} of {budget.max_tokens})"
    if budget.max_tool_calls and tracker.calls_made >= budget.max_tool_calls:
        return f"model-call budget exhausted ({tracker.calls_made} of {budget.max_tool_calls})"
    return None


async def _run(
    graph,  # noqa: ANN001 — a compiled LangGraph
    state: InvestigationState,
    *,
    budget: InvestigationBudget | None,
    persist: bool,
    seq_start: int,
) -> InvestigationState:
    budget = budget or default_budget()
    tenant_ref = str(state.tenant_id)
    state_dict = state.to_dict()
    merged: dict = dict(state_dict)
    tracker = current_cost_tracker()
    tracker_start = tracker.calls_made if tracker is not None else 0
    exchange_start = len(state.llm_exchanges)

    tenant_uuid = await ledger_module.resolve_tenant(tenant_ref) if persist else None
    if persist:
        # Idempotent — start_run ON CONFLICT DO NOTHING (the worker may have
        # already opened this run when it persisted the triage verdict).
        await ledger_module.start_run(
            run_id=state.run_id,
            case_id=str(state.incident_id),
            tenant_ref=tenant_ref,
            alert_summary=state.alert_summary or "",
            raw_alert=state.raw_alert or {},
            model_used="graph:investigation",
        )

    seq = seq_start
    timed_out = False
    graph_error = None
    budget_reason: str | None = None
    deep_partial = False
    # Wall clock for the step about to be streamed. Every `graph_step` row
    # carried `duration_ms: 0` because the argument was simply never passed
    # (issue #1276), so the ledger reported that each node of an escalation
    # took no time — a confident zero for a measurement nobody made, which
    # is the shape this project treats as worse than an absent one.
    step_started = time.monotonic()
    budget_token = _ACTIVE_BUDGET.set(budget)
    try:
        async with asyncio.timeout(budget.max_seconds):
            async for step in graph.astream(state_dict):
                if not isinstance(step, dict):
                    continue
                for node, out in step.items():
                    seq += 1
                    if isinstance(out, dict):
                        merged.update(out)
                    now = time.monotonic()
                    elapsed_ms = round((now - step_started) * 1000)
                    step_started = now
                    if tenant_uuid is not None:
                        await ledger_module.record_event(
                            run_id=state.run_id,
                            tenant_id=tenant_uuid,
                            seq=seq,
                            kind="graph_step",
                            agent=str(node),
                            summary=f"graph node '{node}' completed",
                            payload={"node": str(node)},
                            duration_ms=elapsed_ms,
                        )

                # Checked **inside** the loop, once per streamed step, after
                # that step's work is recorded. The token and model-call
                # budgets were declared on `InvestigationBudget` and enforced
                # nowhere: only `max_seconds` had a reader, and the module
                # docstring said tokens were "enforced upstream by the
                # CostGovernor", which charges a window across runs rather
                # than bounding this one. A single run could therefore spend
                # any number of tokens inside its two minutes.
                budget_reason = _budget_exhausted(budget)
                if budget_reason is not None:
                    logger.warning(
                        "investigation.budget_exhausted",
                        run_id=str(state.run_id),
                        reason=budget_reason,
                    )
                    break
                depth = merged.get("investigation_depth") or {}
                deep_partial = isinstance(depth, dict) and any(depth.get(key) for key in (
                    "truncated", "over_budget", "cost_capped", "error",
                ))
                if deep_partial:
                    # Do not run attack-path scoring over an unfinished
                    # investigation and overwrite its explicit review result.
                    break
    except TimeoutError:
        timed_out = True
        logger.warning("investigation.budget_timeout", run_id=str(state.run_id), max_seconds=budget.max_seconds)
    except Exception as exc:
        graph_error = type(exc).__name__
        logger.warning("investigation.graph_failed", run_id=str(state.run_id), error=graph_error)
    finally:
        _ACTIVE_BUDGET.reset(budget_token)

    try:
        result = InvestigationState.model_validate(merged)
    except Exception as exc:  # noqa: BLE001 — never let a mapping error lose the run
        logger.warning("investigation.state_rebuild_failed", run_id=str(state.run_id), error=str(exc))
        result = state

    if timed_out:
        result.budget_exhausted = True
        result.budget_exhausted_reason = f"wall-clock budget exhausted ({budget.max_seconds}s)"
        result.add_finding(f"Investigation budget ({budget.max_seconds}s) exceeded — partial results, escalating.")
        if not result.verdict:
            result.verdict = NEEDS_REVIEW
        if result.status is AgentStatus.COMPLETED:
            result.status = AgentStatus.RUNNING

    if budget_reason:
        # A labelled state that routes to a human, never a verdict. An
        # investigation that stopped early has not reached a conclusion, and
        # reporting whatever the model last said as the answer is how a
        # truncated run becomes a confident wrong disposition.
        result.add_finding(f"Investigation stopped: {budget_reason}. Partial results, escalating to an analyst.")
        result.budget_exhausted = True
        result.budget_exhausted_reason = budget_reason
        result.verdict = NEEDS_REVIEW
        if result.status is AgentStatus.COMPLETED:
            result.status = AgentStatus.RUNNING

    if deep_partial:
        result.verdict = NEEDS_REVIEW
        if result.status is AgentStatus.COMPLETED:
            result.status = AgentStatus.RUNNING

    if graph_error:
        result.error = f"Graph execution failed ({graph_error}); partial results."
        result.add_finding(result.error)
        result.verdict = NEEDS_REVIEW
        result.status = AgentStatus.FAILED

    if persist:
        if (result.run_id != state.run_id or result.tenant_id != state.tenant_id
                or tenant_uuid != result.tenant_id):
            raise ledger_module.LedgerPersistError("Graph result identity changed or tenant unresolved")
        from app.orchestrator.report import render_router_report

        completion = "partial" if timed_out or budget_reason or deep_partial or result.error or result.status in {
            AgentStatus.FAILED, AgentStatus.CANCELLED,
        } else "completed"
        report_md, report_html = render_router_report(result, info={"topology": "investigation_graph"})
        await ledger_module.persist_graph_result(
            run_id=result.run_id, tenant_id=tenant_uuid, seq=seq + 1,
            state=result.to_dict(), exchanges=result.llm_exchanges[exchange_start:],
            report_md=report_md, report_html=report_html, completion=completion,
        )
        usage = {}
        if tracker is not None:
            if (current_cost_tracker() is not tracker or result.run_id != state.run_id
                    or result.tenant_id != state.tenant_id or tracker.run_id != str(result.run_id)
                    or tracker.tenant_id != str(result.tenant_id)):
                raise ledger_module.LedgerPersistError("Graph usage tracker identity changed")
            # Reuse the existing summary logic for only the records observed
            # inside this graph; an outer tracker's earlier calls are not a
            # second graph charge. This local view is never flushed itself.
            observed = CostTracker(run_id=tracker.run_id, tenant_id=tracker.tenant_id, persist=False)
            observed._records.extend(tracker._records[tracker_start:])
            summary = observed.summary()
            usage = {
                "total_tokens": summary["total_tokens"],
                "total_cost_usd": summary["measured_cost_usd"],
                "measured_call_count": summary["measured_call_count"],
                "estimated_cost_usd": summary["estimated_cost_usd"],
                "estimated_call_count": summary["estimated_call_count"],
                "unpriced_call_count": summary["unpriced_call_count"],
                "add_usage": True,
                "graph_usage_seq": seq + 2,
                "resolved_models": summary["resolved_models"],
            }
        await ledger_module.complete_run(
            run_id=result.run_id,
            tenant_id=tenant_uuid or result.tenant_id,
            # A post-triage graph shares an already completed first triage
            # Run. Keep that recovery status; graph_result separately says
            # completed/partial. A standalone full graph has no such verdict.
            status="failed" if completion == "partial" and seq_start == 0 else "completed",
            error=result.error,
            iterations=result.iteration_count,
            **usage,
        )
    return result


async def run_full_investigation(
    state: InvestigationState,
    *,
    budget: InvestigationBudget | None = None,
    persist: bool = True,
) -> InvestigationState:
    """Run the FULL graph (auto-triage → … → attack-path). Manual API entry."""
    from app.graph.workflow import investigation_graph  # noqa: PLC0415 — avoid import cycle

    return await _run(investigation_graph, state, budget=budget, persist=persist, seq_start=0)


async def run_escalation(
    state: InvestigationState,
    *,
    budget: InvestigationBudget | None = None,
    persist: bool = True,
    seq_start: int = 1,
) -> InvestigationState:
    """Run the post-triage escalation subgraph (triage → … → attack-path).

    Used by the auto-triage worker after it has produced (and persisted) a
    governed verdict. ``seq_start`` defaults to 1 so the recorded graph steps
    follow the worker's ``triage_verdict`` event (seq 1) without colliding.
    """
    from app.graph.workflow import escalation_graph  # noqa: PLC0415 — avoid import cycle

    return await _run(escalation_graph, state, budget=budget, persist=persist, seq_start=seq_start)
