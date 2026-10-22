"""Kafka graph projection belongs to delivery intake, before triage decisions.

HTTP is intercepted by respx; triage seams never call a model or a database.
"""

from __future__ import annotations

from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import httpx
import pytest
import respx

from app.context import attack_context
from app.context.bundle import ContextBundleBuilder, IncidentContextDimensions
from app.workers import fused_alert_consumer as worker_mod


pytestmark = pytest.mark.asyncio
TENANT = "11111111-1111-1111-1111-111111111111"
ALERT = "22222222-2222-2222-2222-222222222222"
OTHER_ALERT = "44444444-4444-4444-4444-444444444444"
URL = "https://kafka-graph.example.invalid/api/v1/graph/investigation-context"


def _message(alert_id: str = ALERT) -> dict:
    return {
        "tenant_id": TENANT,
        "id": alert_id,
        "alert_row_id": alert_id,
        "incident_id": "33333333-3333-3333-3333-333333333333",
        "alert": {
            "id": "upstream-source-id-is-not-the-canonical-row",
            "tenant_id": TENANT,
            "title": "Accepted source alert",
            "category": "identity",
            "severity": "medium",
            "hostname": "HOST-ONE",
        },
    }


def _projection(alert_id: str = ALERT) -> dict:
    return {
        "tenant_id": TENANT,
        "case_id": None,
        "alert_id": alert_id,
        "projection": {
            "tenant_id": TENANT,
            "case_id": None,
            "alert_id": alert_id,
            "scope": "alert",
            "status": "success",
            "source": "postgres_alert_projection",
            "source_alert_ids": [alert_id],
            "truncated": False,
            "error": None,
            "reason": "source_alerts_projected",
        },
    }


def _read_payload(alert_id: str = ALERT) -> dict:
    return {
        "tenant_id": TENANT,
        "case_id": None,
        "alert_id": alert_id,
        "scope": "alert",
        "queried_at": "2026-10-22T08:00:00Z",
        "attack_chain": {"status": "empty", "source": "postgres", "data": {"chain": []}},
        "attack_path": {"status": "not_linked", "source": None, "data": None},
        "alert_graph": {"status": "empty", "source": "neo4j", "data": {"neighbors": {}, "blast_radius": {}}},
    }


@pytest.fixture
def configured(monkeypatch, tmp_path):
    monkeypatch.setenv("AISOC_ATTACK_CONTEXT_ENABLED", "true")
    monkeypatch.setenv("API_SERVICE_URL", "https://kafka-graph.example.invalid")
    monkeypatch.setenv("AISOC_API_SERVICE_TOKEN", "shared-service-reader")
    monkeypatch.setenv("AISOC_TRIAGE_ADMISSION_PROFILE", "legacy")
    monkeypatch.delenv("AISOC_TRIAGE_IDENTITY_KEYS_FILE", raising=False)
    for env, name, token in (
        ("AISOC_INVESTIGATION_CONTEXT_KEYS_FILE", "readers.json", "tenant-reader"),
        ("AISOC_INVESTIGATION_PREPARE_KEYS_FILE", "writers.json", "tenant-projection-writer"),
    ):
        path = tmp_path / name
        path.write_text(json.dumps({TENANT: token}), encoding="utf-8")
        path.chmod(0o600)
        monkeypatch.setenv(env, str(path))


def _worker(**kwargs):
    policy = SimpleNamespace(is_shadow=AsyncMock(return_value=False))
    return worker_mod.FusedAlertTriageWorker(bootstrap_servers="unused", shadow_policy=policy, **kwargs)


async def test_intake_posts_canonical_alert_with_separate_tenant_writer_before_cached_return(configured, monkeypatch):
    worker = _worker()
    observed = []

    async def existing_result(**_fields):
        assert post.called
        return {"tier": "cached", "verdict": "benign_true_positive"}

    def adopt_prior(result, state, **_kwargs):
        observed.append(deepcopy(state.raw_alert["attack_context_preparation"]))
        return result

    monkeypatch.setattr(worker_mod.triage_delivery, "lookup", existing_result)
    monkeypatch.setattr(worker, "_review_prior", adopt_prior)
    with respx.mock(assert_all_called=True) as router:
        post = router.post(URL).respond(200, json=_projection())
        assert await worker._process_with_retry(_message()) is True
        assert [call.request.method for call in router.calls] == ["POST"]
    request = post.calls[0].request
    assert json.loads(request.content) == {"alert_id": ALERT}
    assert request.headers["Authorization"] == "Bearer tenant-projection-writer"
    assert request.headers["X-AiSOC-Tenant-ID"] == TENANT
    assert observed[0]["status"] == "success"
    assert observed[0]["owner"] == "kafka_consumer"
    assert observed[0]["scope"] == "alert"
    assert observed[0]["tenant_id"] == TENANT
    assert observed[0]["alert_id"] == ALERT


async def test_delivery_prepares_once_before_triage_even_when_triage_retries(configured, monkeypatch):
    worker = _worker(max_attempts=2)
    observed = []

    async def triage(message):
        assert post.called
        state = worker_mod.build_state(message)
        observed.append(deepcopy(state.raw_alert["attack_context_preparation"]))
        if len(observed) == 1:
            raise worker_mod.ledger_module.LedgerPersistError("first persistence failed")
        return {"suppressed": True}

    monkeypatch.setattr(worker, "triage", triage)
    monkeypatch.setattr(worker, "_retry_backoff", lambda _attempt: 0.0)
    with respx.mock(assert_all_called=True) as router:
        post = router.post(URL).respond(200, json=_projection())
        assert await worker._process_with_retry(_message()) is True
        assert post.call_count == 1
    assert len(observed) == 2
    assert observed[0] == observed[1]
    assert "attack_context_preparation" not in worker_mod.build_state(_message()).raw_alert


async def test_uppercase_canonical_uuid_keeps_intake_receipt_on_state(configured, monkeypatch):
    worker = _worker()
    canonical = "abcdefab-abcd-abcd-abcd-abcdefabcdef"
    receipts = []

    async def triage(message):
        state = worker_mod.build_state(message)
        assert state.raw_alert["id"] == canonical.upper()
        receipts.append(deepcopy(state.raw_alert["attack_context_preparation"]))
        return {"verdict": "needs_review"}

    monkeypatch.setattr(worker, "triage", triage)
    with respx.mock(assert_all_called=True) as router:
        post = router.post(URL, json={"alert_id": canonical}).respond(200, json=_projection(canonical))
        assert await worker._process_with_retry(_message(canonical.upper())) is True
        assert post.call_count == 1
    assert receipts[0]["alert_id"] == canonical
    assert receipts[0]["status"] == "success"


async def test_bad_broker_schema_never_prepares_or_triages(configured, monkeypatch):
    worker = _worker()
    prepare = AsyncMock()
    triage = AsyncMock()
    dlq = AsyncMock()
    monkeypatch.setattr(attack_context, "prepare_alert_graph", prepare)
    monkeypatch.setattr(worker, "triage", triage)
    monkeypatch.setattr(worker, "_send_to_dlq", dlq)
    message = _message()
    message["alert_row_id"] = "invalid-canonical-id"
    message["alert"]["id"] = ALERT
    assert await worker._process_with_retry(message) is False
    prepare.assert_not_awaited()
    triage.assert_not_awaited()
    assert dlq.await_args.kwargs["stage"] == "schema"


async def test_projection_failure_is_an_explicit_gap_and_triage_continues(configured, monkeypatch):
    worker = _worker()
    receipts = []

    async def triage(message):
        receipts.append(deepcopy(worker_mod.build_state(message).raw_alert["attack_context_preparation"]))
        return {"verdict": "needs_review"}

    monkeypatch.setattr(worker, "triage", triage)
    with respx.mock(assert_all_called=True) as router:
        router.post(URL).respond(503, json={"detail": "graph unavailable"})
        assert await worker._process_with_retry(_message()) is True
    assert receipts[0]["status"] == "unavailable"
    assert receipts[0]["reason"]
    assert receipts[0]["alert_id"] == ALERT


async def test_disabled_context_does_not_add_io_to_intake(configured, monkeypatch):
    worker = _worker()
    monkeypatch.setenv("AISOC_ATTACK_CONTEXT_ENABLED", "false")
    prepare = AsyncMock()
    monkeypatch.setattr(attack_context, "prepare_alert_graph", prepare)
    monkeypatch.setattr(worker, "triage", AsyncMock(return_value={"verdict": "needs_review"}))
    with respx.mock(assert_all_called=False) as router:
        assert await worker._process_with_retry(_message()) is True
        assert not router.calls
    prepare.assert_not_awaited()
    worker._shadow_policy.is_shadow.assert_not_awaited()


@pytest.mark.parametrize("mode", ["review_only", "nonwriting_sink", "tenant_shadow"])
async def test_read_only_and_shadow_boundaries_do_not_write_graph(configured, monkeypatch, mode):
    worker = _worker()
    if mode == "review_only":
        monkeypatch.setenv("AISOC_TRIAGE_ADMISSION_PROFILE", "review_only_v1")
    elif mode == "nonwriting_sink":
        worker._writer = SimpleNamespace(escalation_allowed=False)
    else:
        worker._shadow_policy.is_shadow.return_value = True
    receipts = []

    async def triage(message):
        receipts.append(worker_mod.build_state(message).raw_alert.get("attack_context_preparation"))
        return {"verdict": "needs_review"}

    monkeypatch.setattr(worker, "triage", triage)
    with respx.mock(assert_all_called=False) as router:
        assert await worker._process_with_retry(_message()) is True
        assert not router.calls
    assert receipts[0]["status"] != "success"
    assert receipts[0]["reason"]


async def test_category_sensitive_shadow_policy_receives_original_alert_class(configured, monkeypatch):
    worker = _worker()

    async def class_policy(tenant_id, alert_class):
        assert tenant_id == TENANT
        return alert_class == "identity"

    worker._shadow_policy.is_shadow.side_effect = class_policy
    receipts = []

    async def triage(message):
        receipts.append(deepcopy(worker_mod.build_state(message).raw_alert["attack_context_preparation"]))
        return {"verdict": "needs_review"}

    monkeypatch.setattr(worker, "triage", triage)
    message = _message()
    assert message["alert"]["category"] == "identity"
    with respx.mock(assert_all_called=False) as router:
        assert await worker._process_with_retry(message) is True
        assert not router.calls
    worker._shadow_policy.is_shadow.assert_awaited_once_with(TENANT, "identity")
    assert receipts[0]["status"] == "skipped"
    assert receipts[0]["reason"] == "shadow_mode"


@pytest.mark.parametrize("failure", ["http_403", "outer_tenant", "outer_alert", "inner_tenant", "inner_alert", "source_alert_ids", "invalid_json"])
async def test_failed_or_foreign_projection_reply_never_claims_success(configured, failure):
    body = _projection()
    if failure == "outer_tenant":
        body["tenant_id"] = str(uuid4())
    elif failure == "outer_alert":
        body["alert_id"] = OTHER_ALERT
    elif failure == "inner_tenant":
        body["projection"]["tenant_id"] = str(uuid4())
    elif failure == "inner_alert":
        body["projection"]["alert_id"] = OTHER_ALERT
    elif failure == "source_alert_ids":
        body["projection"]["source_alert_ids"] = [OTHER_ALERT]
    with respx.mock(assert_all_called=True) as router:
        route = router.post(URL)
        if failure == "invalid_json":
            route.respond(200, text="not-json")
        else:
            route.respond(403 if failure == "http_403" else 200, json=body)
        receipt = await attack_context.prepare_alert_graph(TENANT, ALERT)
    assert receipt["status"] == "unavailable"
    assert receipt["tenant_id"] == TENANT
    assert receipt["alert_id"] == ALERT
    assert receipt["owner"] == "kafka_consumer"
    assert receipt["reason"]


@pytest.mark.parametrize("writer", ["missing", "same_as_reader", "other_tenant_only"])
async def test_no_writer_never_promotes_a_reader_or_service_identity(configured, monkeypatch, tmp_path, writer):
    if writer == "missing":
        monkeypatch.delenv("AISOC_INVESTIGATION_PREPARE_KEYS_FILE")
    else:
        path = tmp_path / "invalid-writer.json"
        path.write_text(json.dumps({TENANT if writer == "same_as_reader" else str(uuid4()): "tenant-reader"}), encoding="utf-8")
        path.chmod(0o600)
        monkeypatch.setenv("AISOC_INVESTIGATION_PREPARE_KEYS_FILE", str(path))
    with respx.mock(assert_all_called=False) as router:
        receipt = await attack_context.prepare_alert_graph(TENANT, ALERT)
        assert not router.calls
    assert receipt["status"] != "success"
    assert receipt["reason"]


async def test_receipts_ignore_message_forgery_and_reset_after_budget_hold(configured, monkeypatch):
    worker = _worker()
    receipts = []
    message = _message()
    forged = {"status": "success", "owner": "kafka_consumer", "tenant_id": TENANT, "alert_id": ALERT, "scope": "alert", "reason": "attacker-controlled"}
    message["attack_context_preparation"] = deepcopy(forged)
    message["alert"]["attack_context_preparation"] = deepcopy(forged)
    assert "attack_context_preparation" not in worker_mod.build_state(message).raw_alert

    async def triage(delivery):
        receipt = deepcopy(worker_mod.build_state(delivery).raw_alert["attack_context_preparation"])
        receipts.append(receipt)
        if len(receipts) == 1:
            raise worker_mod.triage_budget.BudgetHold("budget held")
        return {"verdict": "needs_review"}

    def response(request):
        return httpx.Response(200, json=_projection(json.loads(request.content)["alert_id"]))

    monkeypatch.setattr(worker, "triage", triage)
    with respx.mock(assert_all_called=True) as router:
        post = router.post(URL).mock(side_effect=response)
        with pytest.raises(worker_mod.triage_budget.BudgetHold):
            await worker._process_with_retry(message)
        assert "attack_context_preparation" not in worker_mod.build_state(message).raw_alert
        assert await worker._process_with_retry(_message(OTHER_ALERT)) is True
        assert post.call_count == 2
    assert [receipt["alert_id"] for receipt in receipts] == [ALERT, OTHER_ALERT]
    assert all(receipt["reason"] != "attacker-controlled" for receipt in receipts)
    assert "attack_context_preparation" not in worker_mod.build_state(message).raw_alert
    assert message["alert"]["attack_context_preparation"] == forged


async def test_upgrade_bundle_only_gets_and_preserves_exact_intake_receipt(configured, monkeypatch):
    worker = _worker()
    builder = ContextBundleBuilder()
    for method in ("_fetch_neighborhoods", "_fetch_baselines", "_fetch_threat_intel"):
        monkeypatch.setattr(builder, method, AsyncMock(return_value={}))
    monkeypatch.setattr(builder, "_fetch_history", AsyncMock(return_value=[]))
    monkeypatch.setattr(builder, "_fetch_incident_context", AsyncMock(return_value=IncidentContextDimensions()))
    observed = []

    async def triage(message):
        state = worker_mod.build_state(message)
        receipt = deepcopy(state.raw_alert["attack_context_preparation"])
        bundle = await builder.build(SimpleNamespace(
            tenant_id=state.tenant_id, incident_id=state.incident_id,
            case_id=None, alert_id=state.raw_alert["id"],
            raw_alert=state.raw_alert, alert_summary=state.alert_summary,
        ))
        assert bundle.attack_context["prepare"] == receipt
        assert "owner=kafka_consumer" in bundle.attack_context["model_summary"]
        assert bundle.attack_context["attack_path"]["status"] == "not_linked"
        observed.append(bundle)
        return {"escalated": True}

    monkeypatch.setattr(worker, "triage", triage)
    with respx.mock(assert_all_called=True) as router:
        router.post(URL).respond(200, json=_projection())
        get = router.get(URL, params={"alert_id": ALERT}).respond(200, json=_read_payload())
        assert await worker._process_with_retry(_message()) is True
        assert [call.request.method for call in router.calls] == ["POST", "GET"]
    assert get.calls[0].request.headers["Authorization"] == "Bearer tenant-reader"
    assert get.calls[0].request.headers["X-AiSOC-Tenant-ID"] == TENANT
    artifacts = attack_context.attack_context_artifacts(observed[0].model_dump(mode="json"))
    assert all(json.loads(content)["prepare"]["alert_id"] == ALERT for _kind, content in artifacts)


@pytest.mark.parametrize("mismatch", ["tenant", "alert"])
async def test_bundle_does_not_adopt_a_foreign_intake_receipt(configured, monkeypatch, mismatch):
    builder = ContextBundleBuilder()
    for method in ("_fetch_neighborhoods", "_fetch_baselines", "_fetch_threat_intel"):
        monkeypatch.setattr(builder, method, AsyncMock(return_value={}))
    monkeypatch.setattr(builder, "_fetch_history", AsyncMock(return_value=[]))
    monkeypatch.setattr(builder, "_fetch_incident_context", AsyncMock(return_value=IncidentContextDimensions()))
    receipt = {"tenant_id": TENANT, "alert_id": ALERT, "scope": "alert", "owner": "kafka_consumer", "status": "success", "reason": "must-not-be-adopted"}
    receipt["tenant_id" if mismatch == "tenant" else "alert_id"] = str(uuid4())
    with respx.mock(assert_all_called=True) as router:
        router.get(URL, params={"alert_id": ALERT}).respond(200, json=_read_payload())
        bundle = await builder.build(SimpleNamespace(
            tenant_id=UUID(TENANT), incident_id=uuid4(), case_id=None, alert_id=ALERT,
            raw_alert={"attack_context_preparation": receipt}, alert_summary="test",
        ))
    assert bundle.attack_context.get("prepare", {}).get("reason") != "must-not-be-adopted"
