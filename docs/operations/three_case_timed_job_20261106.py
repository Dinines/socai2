"""A single read-only-mounted r3 job for the three frozen r300 synthetic cases.

The actor, DB, lake, code and published artifacts come from the installed
processor. The run policy is explicit and belongs only to this experiment.
The private upstream bearer is supplied once via stdin, never in arguments.
"""
import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid5

import httpx
import processing_job as processor
from app.core.airgap import enforce_airgap_for_url
from app.core.config import settings
from app.db.database import AsyncSessionLocal, engine
from app.services.llm_safety import safe_chat_completions_request
from app.socai2.baseline_analysis_model import MAX_OUTPUT_TOKENS, TenantChatGateway
from app.socai2.baseline_contracts import FULL_EXECUTOR_VERSION, Actor, Limits, Start
from app.socai2.baseline_executor import BaselineExecutor
from app.socai2.baseline_store import A, R, StoreError, digest
from app.socai2.case_relations import CI, incident_selection
from app.socai2.case_service import CaseService
from app.socai2.model_errors import ModelCallError, provider_error
from app.socai2.stage_results import StageResultService
from sqlalchemy import select

BATCH = "ie-audit-20261106-r300"
PLAN = Path("/opt/r300/plan.json")
PLAN_SHA = "6eac8f08e7f858f5f18dc4639fadb57364a354e350ec81b12e96ae154e1d2a61"
TENANT = UUID("6aff0ef7-c670-5a84-a2ee-83d73e25b964")
ALIAS = "aisoc-investigation"
SERVED = "aisoc-test-investigation"
UPSTREAM = "http://192.168.1.43:8000/v1"
CALL_SECONDS = 300
STAGE_SECONDS = 360
CASE_SECONDS = 1260
POLICY = "socai2.three-case-20261106-r300.v1"
require = processor.require


def card_for(args):
    raw = PLAN.read_bytes()
    require(hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == PLAN_SHA, "plan_hash_mismatch")
    plan = json.loads(raw)
    require(plan["batch"] == BATCH and UUID(plan["tenant_id"]) == TENANT, "plan_identity_mismatch")
    card = next(row for row in plan["cases"] if row["key"] == args.card)
    if args.command == "preflight":
        require(all(value is None for value in (args.subject, args.operation_key, args.run_id, args.scope_revision)),
                "unexpected_argument")
        return card
    require(args.operation_key is not None, "operation_key_required")
    if args.command == "alert":
        require(str(args.subject) in card["alert_ids"], "unplanned_alert")
        index = card["alert_ids"].index(str(args.subject))
        expected = card["operation_keys"]["alerts"][index]
    elif args.command == "incident":
        require(args.subject in (None, UUID(card["incident_id"])), "unplanned_incident")
        expected = card["operation_keys"]["incident"]
    else:
        require(args.subject in (None, UUID(card["case_id"])) and args.run_id and args.scope_revision == 1,
                "unplanned_case_or_scope")
        expected = card["operation_keys"]["start"]
    require(str(args.operation_key) == expected, "unplanned_operation")
    if args.command != "case-start":
        require(args.run_id is None and args.scope_revision is None, "unexpected_run_or_scope")
    return card


def read_key(reader):
    data = reader.read(4097)
    value = data.removesuffix(b"\n").removesuffix(b"\r")
    require(0 < len(value) <= 4094 and all(32 < c < 127 for c in value), "invalid_upstream_input")
    return value.decode("ascii")


def limits_for(kind, now):
    full = kind == "baseline"
    alert = kind == "alert_basic"
    require(kind in {"baseline", "alert_basic", "incident_diagnosis"}, "unplanned_run_kind")
    return Limits(max_model_calls=4 if full else 1, max_tokens=48000 if full else 24000,
                  max_tool_calls=4 if full else 3 if alert else 0, max_rows_per_query=200 if full or alert else 0,
                  deadline_at=now + timedelta(seconds=CASE_SECONDS if full else STAGE_SECONDS), policy_version=POLICY)


def utcnow():
    return datetime.now(timezone.utc)


class TimedGateway(TenantChatGateway):
    def __init__(self, key, max_calls, records):
        self.key, self.max_calls, self.records = key, max_calls, records

    async def configure(self, service, tenant):
        require(tenant == TENANT and await super().configure(service, tenant), "model_configuration_unavailable")
        require(self.config.base_url.rstrip("/") == "http://litellm:4000/v1" and self.model == ALIAS
                and self.provider == "chat_completions" and self.schema_profile == "vllm_grammar_v1",
                "original_model_configuration_mismatch")
        return True

    async def complete(self, body, timeout):
        require(set(body) == {"model", "messages", "max_tokens", "response_format", "temperature"}
                and body["model"] == ALIAS and body["max_tokens"] == MAX_OUTPUT_TOKENS == 3000,
                "unexpected_model_request")
        require(len(self.records) < self.max_calls and timeout > 0, "model_allowance_exhausted")
        seconds = min(CALL_SECONDS, timeout)
        url = UPSTREAM + "/chat/completions"
        enforce_airgap_for_url(url)
        started = utcnow()
        record = {"schema": body["response_format"]["json_schema"]["name"], "ordinal": len(self.records) + 1,
                  "started_at": started.isoformat(), "actual_deadline_at": (started + timedelta(seconds=seconds)).isoformat(),
                  "executor_remaining_seconds": timeout, "timeout_seconds": seconds, "upstream_model": SERVED,
                  "max_tokens": body["max_tokens"], "application_body_sha256": digest(body), "sent": False}
        self.records.append(record)

        async def record_wire(request):
            sent = json.loads(request.content)
            require(str(request.url) == url and sent == {**body, "model": SERVED}, "wire_differs_from_frozen_input")
            record.update(sent=True, wire_body_sha256=digest(sent))

        before = time.monotonic()
        try:
            async with asyncio.timeout(seconds), httpx.AsyncClient(
                follow_redirects=False, trust_env=False, event_hooks={"request": [record_wire]},
            ) as client:
                response = await safe_chat_completions_request(api_key=self.key, url=url, client=client,
                    model=SERVED, messages=body["messages"], timeout=seconds, max_tokens=body["max_tokens"],
                    temperature=body["temperature"], response_format=body["response_format"])
            record["transport"] = "response_received"
            return response
        except (httpx.HTTPError, TimeoutError) as exc:
            details = provider_error(exc, self.key)
            record.update(transport=type(exc).__name__, http_status=details["http_status"])
            raise ModelCallError(details) from None
        finally:
            record.setdefault("transport", "interrupted_before_response")
            record.update(ended_at=utcnow().isoformat(), elapsed_seconds=round(time.monotonic() - before, 3))


class TimedStages(StageResultService):
    """Use the standard claim with a persisted deadline for this operation."""
    async def begin(self, tenant_id, kind, identity, operation_key, *, producer, limits, requested_by=None):
        require(limits is None, "unexpected_stage_limits")
        run_id = uuid5(tenant_id, "socai2.stage:" + str(operation_key))
        async with self.transaction(tenant_id, readonly=True) as store:
            earlier = await store.one(select(R.c.limits).where(*store.where(R, R.c.id == run_id)))
            if earlier:
                limits = Limits.model_validate(earlier["limits"])
                require(limits.policy_version == POLICY, "existing_run_policy_mismatch")
            else:
                limits = limits_for(kind, await store.now())
        return await super().begin(tenant_id, kind, identity, operation_key, producer=producer,
                                   limits=limits, requested_by=requested_by)


async def source_check(service, tenant, card, *, run_id=None):
    expected = set(map(UUID, card["alert_ids"]))
    incident_id, case_id = UUID(card["incident_id"]), UUID(card["case_id"])
    async with service.transaction(tenant, readonly=True) as store:
        _, members = await incident_selection(store, [incident_id])
        found = (await store.db.execute(select(A.c.id).where(*store.where(A, A.c.id.in_(expected),
            A.c.source_namespace == "fusion.v1")))).scalars().all()
        require(members == expected == set(found), "source_members_mismatch")
        if run_id is not None:
            linked = (await store.db.execute(select(CI.c.incident_id).where(
                *store.where(CI, CI.c.case_id == case_id)))).scalars().all()
            prepared = await store.receipt(case_id, UUID(card["operation_keys"]["prepare"]), "baseline_prepared")
            require(await store.members(case_id) == expected and set(linked) == {incident_id} and prepared
                    and prepared["outcome"]["pending_run_id"] == str(run_id)
                    and prepared["outcome"]["scope_revision"] == 1, "case_prepare_scope_mismatch")


async def execute(args, records):
    card = card_for(args)
    key = read_key(sys.stdin.buffer)
    database, role, tenant, actor_id = await processor.verify_target()
    require((database, role, tenant) == ("socai2_processing_handoff", "socai2_processing_job", TENANT),
            "processing_identity_mismatch")
    require(settings.AISOC_AIRGAPPED and set(settings.AISOC_AIRGAP_ALLOWLIST) == {"litellm", "192.168.1.43"}
            and os.getenv("SOCAI2_MODEL_SCHEMA_PROFILE") == "vllm_grammar_v1", "timed_airgap_mismatch")
    gateway = TimedGateway(key, 4 if args.command == "case-start" else 1, records)
    cases = CaseService(AsyncSessionLocal)
    await gateway.configure(cases, tenant)
    await source_check(cases, tenant, card, run_id=args.run_id)
    if args.command == "preflight":
        check = await processor.check_dependencies(gateway.config)
        url = UPSTREAM + "/models"
        enforce_airgap_for_url(url)
        async with httpx.AsyncClient(follow_redirects=False, trust_env=False, timeout=10) as client:
            response = await client.get(url, headers={"Authorization": "Bearer " + key})
            response.raise_for_status()
            require(any(m.get("id") == SERVED for m in response.json()["data"]), "upstream_model_not_listed")
        return {"check": "timed_sources_and_original_dependencies", "database": database, "model_calls": 0, **check}
    stage = args.command in {"alert", "incident"}
    user = await processor.principal(tenant, actor_id, "alerts:write" if stage else "cases:write")
    if stage:
        stages = TimedStages(AsyncSessionLocal)
        if args.command == "alert":
            return await stages.execute_alert(tenant, args.subject, args.operation_key, gateway=gateway,
                                              requested_by=user.user_id)
        return await stages.execute_incident(tenant, UUID(card["incident_id"]), args.operation_key,
                                             gateway=gateway, requested_by=user.user_id)

    actor = Actor(user_id=user.user_id, name=user.email)
    case_id = UUID(card["case_id"])
    async with cases.transaction(tenant, readonly=True) as store:
        await cases.actor(store, actor)
        limits = limits_for("baseline", await store.now())
    start = Start(expected_scope_revision=args.scope_revision, operation_key=args.operation_key,
                  window_start=card["window_start"], window_end=card["window_end"])
    # The public start_full adapter enforces its 120s HTTP policy. The original
    # claim, single active slot and full executor are used with this job's policy.
    await cases.start(tenant, case_id, args.run_id, start, actor=actor, limits=limits,
                      executor_version=FULL_EXECUTOR_VERSION, executor=BaselineExecutor(cases, tenant, gateway=gateway))
    return processor.case_start_receipt(await cases.read_run(tenant, case_id, args.run_id))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "alert", "incident", "case-start"))
    parser.add_argument("--card", choices=("m01", "s02", "u03"), required=True)
    parser.add_argument("--subject", type=UUID)
    parser.add_argument("--operation-key", type=UUID)
    parser.add_argument("--run-id", type=UUID)
    parser.add_argument("--scope-revision", type=int)
    args = parser.parse_args()
    records = []

    async def run():
        try:
            return await execute(args, records)
        finally:
            await engine.dispose()

    try:
        result = asyncio.run(run())
        code = 2 if result.get("state") in {"unknown", "failed", "cancelled", "running", "pending_update"} else 0
    except Exception as exc:  # noqa: BLE001 -- report a stable code without raw provider or environment details
        reason = type(exc).__name__
        if isinstance(exc, StoreError):
            reason = exc.code
        elif isinstance(exc, processor.Refused):
            reason = str(exc)
        result, code = {"error": reason}, 1
    result.update(batch=BATCH, card=args.card, command=args.command, subject=args.subject,
                  operation_key=args.operation_key, requested_run_id=args.run_id, policy=POLICY,
                  per_model_timeout_seconds=CALL_SECONDS, stage_wall_seconds=STAGE_SECONDS,
                  case_wall_seconds=CASE_SECONDS, calls=records)
    print(json.dumps(result, ensure_ascii=False, default=str))
    return code


if __name__ == "__main__":
    sys.exit(main())
