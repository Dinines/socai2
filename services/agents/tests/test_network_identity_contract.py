"""A1 actual v2 API/caller/evidence seams with mocked CH/HTTP; no services."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
import unittest

import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/agents"))
from app.investigation_v2.activity_records import bind_activity_records
from app.investigation_v2.evidence_view import build_evidence_view
from app.investigation_v2.fixed_recon import evaluate_alert_recon
from app.investigation_v2.question_deep import QuestionTask, admit_deep_query, DeepRequestRejected
from app.investigation_v2.scope import (CheckedAlert, CheckedMemberSnapshot, SourceField,
                                      TenantPrincipal, UTCWindow, initialize_scope)
from test_business_profile_contract import bind
from test_evidence_view_contract import TENANT, ALERT, EVENT, CURRENT_RUN, START, FILTERS, PARAMS, material

CASES = (
    ("ipv4", "192.0.2.70", "198.51.100.70", "192.0.2.70", "198.51.100.70"),
    ("mapped_hex", "::ffff:c000:246", "::ffff:c633:6446", "192.0.2.70", "198.51.100.70"),
    ("mapped_dotted", "::ffff:192.0.2.70", "::ffff:198.51.100.70", "192.0.2.70", "198.51.100.70"),
    ("ipv6", "2001:db8::70", "2001:db8::71", "2001:db8::70", "2001:db8::71"),
    ("ipv6_expanded", "2001:0DB8:0000:0000:0000:0000:0000:0070",
     "2001:0DB8:0000:0000:0000:0000:0000:0071", "2001:db8::70", "2001:db8::71"),
)


def api_result(source: str, dest: str) -> dict:
    # Each service has a different top-level app package: execute real API logic
    # in its own interpreter, replacing only its CH transport.
    code = r'''
import asyncio,json,sys
from unittest.mock import AsyncMock,patch
sys.path[:0]=['services/api/tests','services/api']
from test_investigation_records import row,response,TENANT,ARGS
from app.investigation_v2 import records
args=json.load(sys.stdin)
async def main():
    source=row(src_hostname='fixture-host',source_ip=args['source_ip'],dest_ip=args['dest_ip'],
               raw='{"source":"fixture"}',ocsf='{"class_uid":4001}')
    with patch('socket.socket.connect',side_effect=AssertionError('offline contract')):
        with patch.object(records,'execute_lake_query',AsyncMock(return_value=response([source]))):
            result=await records.activity_records(TENANT,**{**ARGS,'hostname':'fixture-host',**args})
    print(json.dumps(result.as_dict()))
asyncio.run(main())
'''
    run = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True,
                         text=True, encoding="utf-8", check=True,
                         input=json.dumps(dict(source_ip=source, dest_ip=dest)))
    return json.loads(run.stdout)


def checked_scope(source: str, dest: str):
    filters = {**FILTERS, "source_ip": source, "dest_ip": dest}
    paths = dict(hostname="hostname", source_ip="src_ip", dest_ip="dst_ip",
                 dst_port="raw_event.telemetry[0].dst_port", protocol="raw_event.telemetry[0].protocol")
    fields = tuple(SourceField(key, "pg.checked", paths[key], value) for key, value in filters.items())
    fields += (SourceField("source_event_ids", "pg.checked", "source_event_ids", (str(EVENT),)),)
    member = CheckedAlert(TENANT, ALERT, "pg.checked", "checked-membership", **filters,
                          source_event_ids=(EVENT,), fields=fields)
    return initialize_scope(principal=TenantPrincipal(frozenset({TENANT}), "verified-service", True),
                            tenant_id=TENANT, run_id=CURRENT_RUN,
                            snapshot=CheckedMemberSnapshot("pg.checked-members", 1, (member,)),
                            window=UTCWindow(START, START + timedelta(minutes=5)))


def retained(payload):
    return replace(material(payload), source_run_id=CURRENT_RUN)


class NetworkIdentityContractTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.replies = {case[0]: api_result(case[1], case[2]) for case in CASES}

    async def call(self, context, reply, **changes):
        calls = []

        def handler(request):
            calls.append(json.loads(request.content))
            return httpx.Response(200, json=reply)

        tool = bind_activity_records(context, "Q1", ALERT, api_url="https://offline.invalid",
                                     service_token="fake-contract-token", transport=httpx.MockTransport(handler))
        member = context.member_snapshot.selected[0]
        args = {key: getattr(member, key) for key in FILTERS}
        args.update({key: PARAMS[key] for key in ("start", "end", "limit")})
        result = await tool.fn(**{**args, **changes})
        return result, calls

    async def test_actual_api_caller_evidence_and_facts_accept_all_address_forms(self):
        for label, source, dest, normalized_source, normalized_dest in CASES:
            with self.subTest(case=label):
                context = checked_scope(source, dest)
                member = context.member_snapshot.selected[0]
                self.assertEqual((member.source_ip, member.dest_ip), (normalized_source, normalized_dest))
                self.assertEqual(next(f.value for f in member.fields if f.parameter == "source_ip"), source)
                payload, calls = await self.call(context, self.replies[label], source_ip=source, dest_ip=dest)
                self.assertEqual(payload["status"], "ok")
                self.assertEqual(calls[0]["args"]["source_ip"], normalized_source)
                self.assertEqual(calls[0]["args"]["dest_ip"], normalized_dest)
                before = deepcopy(payload)
                evidence = build_evidence_view(context, payload, retained(payload), 1)
                result = evaluate_alert_recon(bind(context), evidence, current_snapshot_ref=evidence.snapshot_ref)
                self.assertEqual(payload, before)
                self.assertEqual(result["scope_readiness"], "ready")
                self.assertEqual((result["nature"], result["authorization"]), ("unresolved", "unknown"))
                self.assertEqual(evidence.model_view["events"][0]["version"], payload["rows"][0]["content_hash"])

    async def test_equivalent_reply_parameters_and_caller_receipt_keep_original_hashes(self):
        context = checked_scope("192.0.2.70", "198.51.100.70")
        reply = deepcopy(self.replies["ipv4"])
        reply["query_receipt"]["parameters"].update(source_ip="::ffff:c000:246", dest_ip="::ffff:c633:6446")
        payload, _ = await self.call(context, reply)
        self.assertEqual(payload["status"], "ok")
        payload["caller_receipt"]["request_parameters"]["source_ip"] = "::ffff:192.0.2.70"
        before = deepcopy(payload)
        evidence = build_evidence_view(context, payload, retained(payload), 1)
        self.assertEqual(payload, before)
        self.assertEqual(evidence.model_view["events"][0]["version"], reply["rows"][0]["content_hash"])

    async def test_different_or_nonmapped_compatible_arguments_never_dispatch(self):
        context = checked_scope("192.0.2.70", "198.51.100.70")
        for bad in ("192.0.2.71", "::c000:246", "not-an-ip", 3221226054, None):
            with self.subTest(address=bad):
                result, calls = await self.call(context, self.replies["ipv4"], source_ip=bad)
                self.assertEqual(result["status"], "rejected")
                self.assertFalse(result["caller_receipt"]["http_attempted"])
                self.assertEqual(calls, [])

    async def test_different_reply_address_or_tenant_is_rejected(self):
        context = checked_scope("192.0.2.70", "198.51.100.70")
        for key, bad in (("source_ip", "192.0.2.71"), ("dest_ip", "::c633:6446"),
                         ("tenant_id", "11111111-1111-4111-8111-111111111111")):
            with self.subTest(key=key):
                reply = deepcopy(self.replies["ipv4"])
                reply["query_receipt"]["parameters"][key] = bad
                result, _ = await self.call(context, reply)
                self.assertEqual(result["reason"], "query_response_contract_mismatch")

    def test_original_source_values_cannot_claim_a_different_address(self):
        member = checked_scope("192.0.2.70", "198.51.100.70").member_snapshot.selected[0]
        for bad in ("192.0.2.71", "::c000:246"):
            fields = tuple(replace(f, value=bad) if f.parameter == "source_ip" else f for f in member.fields)
            with self.subTest(value=bad), self.assertRaises(ValueError):
                replace(member, fields=fields)

    async def test_source_hash_tampering_is_not_hidden_by_address_aliases(self):
        context = checked_scope("::ffff:c000:246", "::ffff:c633:6446")
        payload, _ = await self.call(context, self.replies["mapped_hex"])
        self.assertEqual(payload["status"], "ok")
        payload["rows"][0]["raw_payload"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash_mismatch"):
            build_evidence_view(context, payload, retained(payload), 1)

    async def test_evidence_rejects_different_query_and_caller_addresses(self):
        context = checked_scope("192.0.2.70", "198.51.100.70")
        original, _ = await self.call(context, self.replies["ipv4"])
        for receipt in ("query_receipt", "caller_receipt"):
            payload = deepcopy(original)
            key = "parameters" if receipt == "query_receipt" else "request_parameters"
            payload[receipt][key]["source_ip"] = "192.0.2.71"
            with self.subTest(receipt=receipt), self.assertRaisesRegex(ValueError, "query_field_outside_scope"):
                build_evidence_view(context, payload, retained(payload), 1)

    def test_deep_aliases_have_one_fingerprint_and_cannot_repeat(self):
        context = checked_scope("::ffff:c000:246", "::ffff:c633:6446")
        task = QuestionTask(context, "Q1", ALERT, "address_check")
        proposal = dict(action="query", tool="activity_records", parameters=task.query_defaults,
                        reason="Check the attributable observation.")
        first = admit_deep_query(task, proposal)
        alternate = deepcopy(proposal)
        alternate["parameters"].update(source_ip="::ffff:192.0.2.70", dest_ip="198.51.100.70")
        second = admit_deep_query(task, alternate)
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(second.parameters["source_ip"], "192.0.2.70")
        with self.assertRaisesRegex(DeepRequestRejected, "duplicate_query"):
            admit_deep_query(task, alternate, seen_queries=frozenset({first.fingerprint}))


if __name__ == "__main__":
    unittest.main()
