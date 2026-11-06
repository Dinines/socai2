from types import SimpleNamespace
from uuid import uuid4

from app.socai2.baseline_analysis import domain_block
from app.socai2.baseline_analysis_contract import Domain
from app.socai2.baseline_contracts import Scope


def test_member_finding_never_inherits_other_member_objects():
    a, b = uuid4(), uuid4()
    context = SimpleNamespace(scope=Scope(kind="whole_case", alert_ids=[a, b],
        object_keys=["host:APP01", "host:DB01"], window_start=None, window_end=None, limitations=[]))
    finding = SimpleNamespace(id="f1", alert_ids=[a], statement="APP01 activity", state="observed",
        support_ids=["s1"], counter_ids=[], limitations=[])
    domain = Domain(name="identity", applicability="applicable", alert_ids=[a],
        finding_ids=["f1"], reason="member evidence", limitations=[])
    result = domain_block(domain, SimpleNamespace(findings=[finding]), {"s1": {"ref": {"id": "source1"}}}, context)
    assert result["findings"][0]["scope"]["alert_ids"] == [str(a)]
    assert result["findings"][0]["scope"]["object_keys"] == []
    assert context.scope.object_keys == ["host:APP01", "host:DB01"]
