"""Local API/SQL projection observations; no DB, model or service connections.

ASGI uses the actual alerts router with substituted user/DB dependencies.
Writes below capture SQL against substitutes only. Assertions describe current
behaviour (including defects), not repaired requirements or live acceptance.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/api"))
from fastapi import FastAPI
import httpx
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from app.api.v1.deps import CurrentUser, get_current_user
from app.db.database import get_db
from app.db.rls import get_tenant_db
from app.api.v1.endpoints import alerts as alert_api, feedback
from app.investigation_v2.incident_reader import read_incident
from app.investigation_v2 import related_investigations
from app.models.alert import Alert
from app.models.case import CaseTimeline
from app.services.alert_rail import build_mini_timeline
from app.services.alert_status import is_unresolved
from app.services.override_learning import apply_redisposition
from app.services.memory_poisoning import plan_redisposition, compute_confirmation_token

TENANT, USER, A1, A2, CASE, INCIDENT = [UUID(int=i) for i in (1, 2, 11, 12, 21, 31)]
NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
observations = []


def observe(name, condition, **actual):
    assert condition, name
    observations.append({"name": name, "current_behaviour_confirmed": True, **actual})


def result(*, count=0, rows=(), one=None):
    r = MagicMock()
    r.scalar_one.return_value = count
    r.scalar_one_or_none.return_value = one
    r.all.return_value = list(rows)
    r.scalars.return_value.all.return_value = list(rows)
    return r


def sql(statement):
    compiled = statement.compile(dialect=postgresql.dialect())
    return {"sql": str(compiled), "params": compiled.params}


def alert(identity=A1):
    return Alert(id=identity, tenant_id=TENANT, title="SYNTHETIC page audit", severity="high",
                 status="new", disposition=None, event_time=NOW-timedelta(days=2),
                 first_seen=NOW, last_seen=NOW, updated_at=NOW, created_at=NOW,
                 case_id=None, connector_id=None, external_id="vendor-id",
                 ai_summary=None, ai_recommendations=[], affected_hosts=["host-01"],
                 affected_users=[], affected_ips=[], entities=[], mitre_tactics=["Execution"],
                 mitre_techniques=[], enrichment_data={"socai2_fusion": {"incident_id": str(INCIDENT)}})


async def main():
    db = SimpleNamespace(execute=AsyncMock(), commit=AsyncMock())
    user = CurrentUser(USER, TENANT, "analyst", "synthetic@example.invalid", scopes=["alerts:read", "alerts:write"])
    app = FastAPI()
    app.include_router(alert_api.router, prefix="/api/v1")
    async def actor(): return user
    async def session(): yield db
    app.dependency_overrides[get_current_user] = actor
    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_tenant_db] = session
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://synthetic.invalid") as client:
        async def read_list(params):
            db.execute.reset_mock()
            db.execute.side_effect = [result(), result(), result(), result()]
            response = await client.get("/api/v1/alerts", params=params)
            assert response.status_code == 200, response.text
            return response.json(), [sql(call.args[0]) for call in db.execute.await_args_list]
        _, plain = await read_list({})
        _, searched = await read_list({"search": "a-unique-title-or-id"})
        observe("declared_search_does_not_change_sql_or_parameters", plain == searched, captured_queries=searched)
        _, extra = await read_list({"start": "2026-01-01T00:00:00Z", "end": "2026-02-01T00:00:00Z",
                                    "source": "vendor", "owner": str(USER), "tag": "critical-asset", "ids": str(A1)})
        observe("undeclared_page_filters_are_ignored_by_actual_asgi", plain == extra,
                tested_parameters=["start", "end", "source", "owner", "tag", "ids"], http_status=200)
        _, filtered = await read_list({"severity": "high", "status": "new", "category": "Execution", "page_size": 200})
        fetch = filtered[-1]
        observe("filters_use_raw_single_values_and_sort_uses_ingestion_time",
                "alerts.category =" in fetch["sql"] and "alerts.severity =" in fetch["sql"]
                and "ORDER BY alerts.created_at DESC" in fetch["sql"]
                and "critical" not in fetch["params"].values(),
                fetch=fetch, order_clause=fetch["sql"].split("ORDER BY", 1)[1],
                note="No actual database ordering/row filtering was simulated; this records emitted SQL.")
        db.execute.reset_mock()
        db.execute.side_effect = [result(count=8), result(rows=[("high", 2), ("critical", 1)]),
                                 result(rows=[("new", 2), ("triaged", 1), ("false_positive", 1)]), result(), result()]
        stats = await client.get("/api/v1/alerts/stats", params={"search": "ignored", "severity": "low"})
        stat_queries = [sql(c.args[0]) for c in db.execute.await_args_list]
        observe("overall_stats_available_but_no_actual_investigation_card",
                stats.status_code == 200 and stats.json()["total"] == 8
                and "investigation" not in json.dumps(stats.json()), response=stats.json(), queries=stat_queries)

    close = alert_api.AlertUpdateRequest(status="resolved")
    try:
        alert_api.AlertUpdateRequest(status="resolved", comment="optional note")
    except ValidationError as exc:
        comment_error = str(exc)
    else:
        raise AssertionError("comment unexpectedly accepted")
    observe("manual_close_needs_no_comment_but_supplied_comment_cannot_be_saved_by_patch",
            close.status == "resolved" and "comment" in comment_error,
            allowed_fields=sorted(alert_api.AlertUpdateRequest.model_fields), comment_error=comment_error,
            owner_returned="assigned_to_id" in alert_api.AlertResponse.model_fields)
    observe("legacy_false_positive_status_still_counted_as_unresolved",
            is_unresolved("fp") and is_unresolved("false_positive"),
            fp_unresolved=is_unresolved("fp"), false_positive_unresolved=is_unresolved("false_positive"))

    feedback_writes = []
    for verdict in ("false_positive", "benign_true_positive", "true_positive"):
        fdb = SimpleNamespace(scalar=AsyncMock(return_value=alert()), execute=AsyncMock(return_value=result()),
                              commit=AsyncMock(), rollback=AsyncMock())
        with patch.object(feedback.sla_events, "record_event", new=AsyncMock()) as sla, \
             patch.object(feedback, "record_human_prior", new=AsyncMock(return_value=None)), \
             patch.object(feedback, "record_override", new=AsyncMock(return_value=None)):
            await feedback.submit_alert_override(feedback.AlertOverrideRequest(alert_id=str(A1),
                original_verdict="needs_review", corrected_verdict=verdict), user, fdb)
            stmt = sql(fdb.execute.await_args.args[0])
            feedback_writes.append({"verdict": verdict, **stmt, "sla_event": sla.await_args.kwargs["event_type"]})
    observe("all_feedback_changes_verdict_only_but_records_resolved_sla",
            all("SET disposition=" in item["sql"] and "status=" not in item["sql"]
                and "resolved_at=" not in item["sql"] and item["sla_event"] == "resolved" for item in feedback_writes),
            writes=feedback_writes, note="Memory/priors/SLA side effects substituted; SQL only, no writes to a database.")
    rdb = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(rowcount=1)), commit=AsyncMock())
    plan = plan_redisposition([str(A1), str(A2)], "false_positive")
    try:
        await apply_redisposition(rdb, tenant_id=TENANT, alert_ids=[A1], new_disposition="false_positive",
                                 analyst_id=USER, confirmation_token=plan.confirmation_token)
    except ValueError as exc:
        subset_error = str(exc)
    else:
        raise AssertionError("unmodified full-preview token unexpectedly accepted for subset")
    assert rdb.execute.await_count == 0
    await apply_redisposition(rdb, tenant_id=TENANT, alert_ids=[A1], new_disposition="false_positive",
                             analyst_id=USER, confirmation_token=compute_confirmation_token([str(A1)], "false_positive"))
    update = sql(rdb.execute.await_args.args[0])
    observe("selected_history_apply_requires_selection_token_and_does_not_close",
            "SET disposition=" in update["sql"] and "status=" not in update["sql"],
            subset_error=subset_error, selected_write=update,
            note="Selection-specific token succeeds; reuse of all-candidate token fails. Keep the existing exact-set validation.")

    old = alert()
    idb = SimpleNamespace(execute=AsyncMock(side_effect=[result(rows=[old]), result()]))
    overview = await read_incident(idb, tenant_id=TENANT, incident_id=INCIDENT)
    related = {"items": [{"started_at": NOW+timedelta(hours=1), "completed_at": NOW+timedelta(hours=2)}]}
    with patch.object(related_investigations, "read_related", new=AsyncMock(return_value=related)):
        attached = await related_investigations.attach_related(None, overview)
    observe("incident_business_times_are_not_the_confirmed_page_times",
            overview.first_seen == NOW and overview.first_seen != old.event_time
            and attached.source_updated_at == NOW+timedelta(hours=2),
            member_occurrence=old.event_time, first_seen_returned=overview.first_seen,
            source_updated_before=overview.source_updated_at, source_updated_after=attached.source_updated_at,
            note="attach_related runs only where investigation material is included; source freshness is not business-update time.")

    await timeline_observation()


async def timeline_observation():
    old = alert()
    old.case_id = CASE
    other_comment = CaseTimeline(id=UUID(int=91), tenant_id=TENANT, case_id=CASE, event_type="comment",
                                 content="SYNTHETIC note for another member", created_at=NOW, actor_type="user",
                                 user_id=USER, event_metadata={"alert_id": str(A2)})
    tdb = SimpleNamespace(execute=AsyncMock(side_effect=[result(rows=[other_comment]), result()]))
    timeline = await build_mini_timeline(tdb, old)
    observe("alert_mini_timeline_includes_other_member_case_comment",
            len(timeline) == 1 and timeline[0].payload["alert_id"] == str(A2),
            current_alert_id=str(A1), returned=[x.model_dump(mode="json") for x in timeline],
            case_query=sql(tdb.execute.await_args_list[0].args[0]),
            note="Substitute returns a row allowed by the emitted case-only predicate; no live PG query.")


timeline_only = "--timeline-only" in sys.argv
asyncio.run(timeline_observation() if timeline_only else main())
out = {"scope": "local synthetic ASGI/function/SQL observations; not acceptance; no external service calls",
       "observation_count": len(observations), "observations": observations,
       "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
Path(__file__).with_name("timeline-followup.json" if timeline_only else "observations.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str)+"\n", encoding="utf-8")
print(json.dumps({"observations": len(observations), "confirmed": True}))
