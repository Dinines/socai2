"""Historical audit counterexamples at 7b7bb6b, not future regression expectations.

Run from any directory with the project's Python. Uses existing synthetic test
builders and mocked CH/HTTP only; emits JSON and never writes business state.
After fixes, retain this observation and add normal regression tests separately.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.dont_write_bytecode = True


def api_reply() -> dict:
    # Separate processes avoid merging the API and Agents' different app packages.
    source = r'''
import asyncio,json,sys
from unittest.mock import AsyncMock,patch
sys.path[:0]=['services/api/tests','services/api']
from test_investigation_records import row,response,TENANT,ARGS
from app.investigation_v2 import records
async def main():
    args={**ARGS,'hostname':'fixture-host',
          'source_ip':'::ffff:c000:246','dest_ip':'::ffff:c633:6446'}
    with patch('socket.socket.connect',side_effect=AssertionError('offline audit')):
        with patch.object(records,'execute_lake_query',
            AsyncMock(return_value=response([row(src_hostname='fixture-host')]))):
            result=await records.activity_records(TENANT,**args)
    print(json.dumps(result.as_dict()))
asyncio.run(main())
'''
    proc = subprocess.run([sys.executable, "-B", "-c", source], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(proc.stdout)


async def caller_observations(reply: dict) -> dict:
    import httpx
    from test_activity_records_caller import TENANT, ALERT, EVENT, RUN, START, ARGS, FILTERS, context
    from app.investigation_v2.scope import (CheckedAlert, CheckedMemberSnapshot, SourceField,
                                          TenantPrincipal, UTCWindow, initialize_scope)
    from app.investigation_v2.activity_records import bind_activity_records

    fields = {**FILTERS, "source_ip": "::ffff:c000:246", "dest_ip": "::ffff:c633:6446"}
    paths = dict(hostname="hostname", source_ip="src_ip", dest_ip="dst_ip",
                 dst_port="raw_event.telemetry[0].dst_port", protocol="raw_event.telemetry[0].protocol")
    refs = tuple(SourceField(k, "pg.checked", paths[k], v) for k, v in fields.items())
    refs += (SourceField("source_event_ids", "pg.checked", "source_event_ids", (str(EVENT),)),)
    member = CheckedAlert(TENANT, ALERT, "pg.checked", "verified-tenant-membership", **fields,
                          source_event_ids=(EVENT,), fields=refs)
    ctx = initialize_scope(principal=TenantPrincipal(frozenset({TENANT}), "verified-service", True),
                           tenant_id=TENANT, run_id=RUN,
                           snapshot=CheckedMemberSnapshot("pg.read", 1, (member,)),
                           window=UTCWindow(START, START + timedelta(minutes=5)))
    outputs = {}
    for label, scope, args in (("mapped", ctx, {**ARGS, **fields}), ("ipv4", context(), ARGS)):
        tool = bind_activity_records(scope, "Q1", ALERT, api_url="https://offline.invalid",
                                     service_token="fake-audit-token",
                                     transport=httpx.MockTransport(lambda request: httpx.Response(200, json=reply)))
        with patch("socket.socket.connect", side_effect=AssertionError("offline audit")):
            result = await tool.fn(**args)
        outputs[label] = dict(scope_ip=scope.query_scope.members[0].source_ip,
                              status=result["status"], reason=result.get("reason"),
                              mock_http_attempted=result["caller_receipt"]["http_attempted"])
    return dict(api_status=reply["status"], api_ip=reply["query_receipt"]["parameters"]["source_ip"],
                api_rows=reply["row_count"], caller=outputs)


def pure_observations() -> dict:
    from test_evidence_view_contract import scope, view, query, record
    from test_business_profile_contract import bind
    from app.investigation_v2.fixed_recon import evaluate_alert_recon

    ctx, payload = scope(), query()
    for params in (payload["query_receipt"]["parameters"], payload["caller_receipt"]["request_parameters"]):
        params["start"] = "2026-10-23T10:01:00.000000+00:00"
        params["end"] = "2026-10-23T10:01:00.000001+00:00"
    ev = view(payload, ctx)
    result = evaluate_alert_recon(bind(ctx), ev, current_snapshot_ref=ev.snapshot_ref)
    window = dict(frozen_seconds=300, query_window=ev.model_view["query"]["coverage"]["window"],
                  scope_readiness=result["scope_readiness"], stop_reason=result["stop_reason"],
                  blocking_gaps=result["blocking_gaps"], coverage_gaps=result["coverage_gaps"],
                  review_required=result["handoff"]["review_required"])
    excerpts = []
    for label, text in (("ascii_512", "x" * 512), ("quotes_512", '"' * 512),
                        ("backslashes_512", "\\" * 512), ("utf8_510", "\u4e2d" * 170)):
        try:
            ev = view(query([record(text, event_id=UUID(int=i + 1)) for i in range(10)]), ctx)
            result = evaluate_alert_recon(bind(ctx), ev, current_snapshot_ref=ev.snapshot_ref)
            excerpts.append(dict(case=label, scope_readiness=result["scope_readiness"],
                                 model_bytes=len(json.dumps(ev.model_view, sort_keys=True, ensure_ascii=False,
                                                          separators=(",", ":")).encode("utf-8"))))
        except ValueError as exc:
            excerpts.append(dict(case=label, error=type(exc).__name__, reason=str(exc)))
    try:
        long_ctx = scope("x" * 513)
        bind(long_ctx)
        view(query(), long_ctx)
        long_alert = dict(accepted=True)
    except ValueError as exc:
        long_alert = dict(error=type(exc).__name__, reason=str(exc))
    return dict(subwindow=window, optional_excerpt_capacity=excerpts, long_alert_text=long_alert)


def main() -> None:
    reply = api_reply()
    sys.path[:0] = [str(ROOT / "services/agents/tests"), str(ROOT / "services/agents")]
    ips = asyncio.run(caller_observations(reply))
    with patch("socket.socket.connect", side_effect=AssertionError("offline audit")):
        observations = pure_observations()
    print(json.dumps(dict(schema="investigation_design_audit_probe.v1",
                          audited_revision="7b7bb6bf67286a13b97002b998366cd2468a4036",
                          mode="offline_actual_code_with_mock_ch_and_http",
                          business_network_calls=0, model_calls=0, business_writes=0,
                          mapped_ipv6=ips, **observations), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
