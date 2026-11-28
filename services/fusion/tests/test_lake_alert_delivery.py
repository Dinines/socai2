"""Direct coordination checks; actual PG/CH/Redis verification is on 21."""
import copy
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.services.lake_alert_delivery import (
    DeliveryPolicy,
    LakeAlertDelivery,
    LakeDeliverySource,
    binding_digest,
    decide,
    initial_state,
)
from app.services.lake_alert_receiver import ReceivePolicy, ReceiveResult
from app.services.lake_alert_selection import SelectionPolicy

from .test_lake_alert_selection import ROOT, document, row


@pytest.fixture
def policies():
    selection = SelectionPolicy.load(ROOT / "deploy/aisoc21/lake-alert-selection-4a/selection.example.json")
    receive = ReceivePolicy.load(ROOT / "deploy/aisoc21/lake-alert-receive-4b/receive.example.json")
    delivery = DeliveryPolicy.load(ROOT / "deploy/aisoc21/lake-alert-delivery-4c/delivery.example.json")
    return selection, receive, delivery


class Store:
    """A local orchestration double, not a database or persistence proof."""
    def __init__(self, selection, receive):
        self.binding = binding_digest(selection, receive)
        self.items, self.attempts = [], []
        self.reject_confirmation = False

    @asynccontextmanager
    async def locked(self):
        yield self

    async def register(self, conn, selected):
        for _, decision in selected:
            identity = UUID(decision["delivery_key"])
            if not any(item["id"] == identity for item in self.items):
                self.items.append({"id":identity, "state":initial_state(decision), "lake_ref":decision["lake_ref"], "number":0})

    async def head(self, conn):
        return next((copy.deepcopy(i) for i in self.items if i["state"] not in {"delivered","lake_only","review"}), None)

    async def begin(self, conn, item):
        actual = next(i for i in self.items if i["id"] == item["id"])
        actual["state"] = "receiving";actual["number"] += 1
        return actual["number"]

    async def finish(self, conn, item, number, result, *, recovered):
        if self.reject_confirmation:
            raise ConnectionError("synthetic_confirmation_rejection")
        actual = next(i for i in self.items if i["id"] == item["id"])
        actual["state"] = "delivered" if result.durable else result.state
        self.attempts.append("recovered" if recovered and result.durable else result.state)


def fixture(policies):
    selection, receive, delivery = policies
    originals=[]
    for name in ("lyc-first", "lyc-second"):
        doc=document();doc["metadata"]["uid"]=name
        originals.append(row(doc,selection))
    async def scan():return originals
    source=SimpleNamespace(selection=selection,scan=scan)
    receiver=SimpleNamespace(selection=selection,policy=receive,calls=[],saved={})
    async def take(value, *, decision):
        key=decision["delivery_key"];receiver.calls.append(key)
        result=ReceiveResult("created",alert_id=str(uuid4()),material_id=str(uuid4()))
        receiver.saved[key]=result
        return result
    async def lookup(value, *, decision):
        return receiver.saved.get(decision["delivery_key"],ReceiveResult("absent"))
    receiver.receive,receiver.lookup_receipt=take,lookup
    store=Store(selection,receive)
    return LakeAlertDelivery(source,receiver,store,delivery),receiver,store


@pytest.mark.asyncio
async def test_durable_registration_resumes_without_duplicate_work(policies):
    worker,receiver,store=fixture(policies)
    assert (await worker.cycle(deliver=False)).state=="staged" and receiver.calls==[]
    resumed=LakeAlertDelivery(worker.source,receiver,store,worker.policy)
    assert (await resumed.cycle()).state=="completed"
    prior=(list(receiver.calls),copy.deepcopy(store.items))
    assert (await resumed.cycle()).state=="completed"
    assert (receiver.calls,store.items)==prior


@pytest.mark.asyncio
async def test_failed_receive_stops_then_retries_the_same_head(policies):
    worker,receiver,store=fixture(policies);take=receiver.receive
    first=True
    async def fail_once(value, *, decision):
        nonlocal first
        if first:
            first=False;receiver.calls.append(decision["delivery_key"])
            return ReceiveResult("failed","controlled_receive_rejection")
        return await take(value,decision=decision)
    receiver.receive=fail_once
    assert (await worker.cycle()).state=="blocked"
    assert [i["state"] for i in store.items]==["failed","pending"]
    assert (await worker.cycle()).state=="completed"
    assert receiver.calls[0]==receiver.calls[1] and len(receiver.calls)==3
    assert store.attempts==["failed","created","created"]


@pytest.mark.asyncio
async def test_lost_receive_result_recovers_by_read_only_proof(policies):
    worker,receiver,store=fixture(policies);take=receiver.receive
    async def lost(value, *, decision):
        await take(value,decision=decision)
        return ReceiveResult("unknown","controlled_lost_receipt")
    receiver.receive=lost
    assert (await worker.cycle()).state=="blocked"
    assert [i["state"] for i in store.items]==["unknown","pending"]
    receiver.receive=take
    assert (await worker.cycle()).state=="completed"
    assert len(receiver.calls)==2 and store.attempts==["unknown","recovered","created"]


@pytest.mark.asyncio
async def test_unknown_without_committed_proof_never_reexecutes_or_skips(policies):
    worker,receiver,store=fixture(policies)
    async def unknown(value, *, decision):
        receiver.calls.append(decision["delivery_key"])
        return ReceiveResult("unknown","controlled_unknown")
    receiver.receive=unknown
    assert (await worker.cycle()).state=="blocked"
    assert (await worker.cycle()).state=="blocked"
    assert len(receiver.calls)==1 and [i["state"] for i in store.items]==["unknown","pending"]


@pytest.mark.asyncio
async def test_unconfirmed_ack_keeps_head_and_does_not_repeat_receive(policies):
    worker,receiver,store=fixture(policies);store.reject_confirmation=True
    assert (await worker.cycle()).state=="unknown"
    assert [i["state"] for i in store.items]==["receiving","pending"]
    store.reject_confirmation=False
    assert (await worker.cycle()).state=="completed"
    assert len(receiver.calls)==2 and store.attempts==["recovered","created"]


@pytest.mark.asyncio
async def test_success_return_without_saved_proof_cannot_confirm(policies):
    worker,receiver,store=fixture(policies)
    async def unproven(value, *, decision):
        return ReceiveResult("created",alert_id=str(uuid4()),material_id=str(uuid4()))
    receiver.receive=unproven
    assert (await worker.cycle()).reason=="committed_delivery_not_proven"
    assert [i["state"] for i in store.items]==["unknown","pending"]


def test_scan_conflicts_and_non_alerts_have_durable_distinct_dispositions(policies):
    selection,_,_=policies
    rows=[row(document(),selection),row(document(message="different"),selection),row(document(is_alert=False),selection)]
    assert all(initial_state(d)!="pending" for _,d in decide(rows,selection))
    assert initial_state(decide([row(document(is_alert=False),selection)],selection)[0][1])=="lake_only"


@pytest.mark.parametrize("count,rows", [(100001,[]),(1,[])])
def test_scan_limits_or_missing_rows_fail_before_registration(policies,count,rows):
    selection,_,_=policies
    class Client:
        def execute(self,sql,params,*,settings):
            assert settings["readonly"]==2 and sql.startswith("SELECT")
            return [(count,)] if "uniqExact" in sql else rows
    with pytest.raises(ValueError,match="lake_delivery_scan"):
        LakeDeliverySource(Client(),selection)._scan()


def test_delivery_profile_requires_explicit_limits(policies,tmp_path):
    _,_,policy=policies
    config=copy.deepcopy(policy.body);config.pop("max_deliveries_per_cycle")
    path=tmp_path/'delivery.json';path.write_text(json.dumps(config))
    with pytest.raises(ValueError,match="invalid_delivery_profile"):
        DeliveryPolicy.load(path)
