"""Direct sample export tests use synthetic documents only."""
import json
from decimal import Decimal
from pathlib import Path

import pytest
from app.services.receipt_json import encoded
from export_opensearch_target_json import loads
from sample_opensearch_classes import pretty, sample, select_one


def page(cls, **changes):
    result = {"timed_out": False, "_shards": {"total": 1, "successful": 1, "failed": 0},
        "hits": {"hits": [{"_index": "synthetic-index", "_id": f"synthetic-{cls}",
            "_source": {"kafka": {"partition": 0, "offset": cls}, "ocsf": {"class_uid": cls,
                "metadata": {"uid": "synthetic-id"}, "number": 2**70, "precise": Decimal('1.234567890123456789'),
                "values": [False, 0, None, [], {"text": "</pre><script>bad()</script>"}]}}}]}}
    result.update(changes)
    return result


def test_full_json_per_class_readback_and_actual_local_page(tmp_path, capsys):
    profile = json.loads((Path(__file__).parent / "evidence/class-samples-tool-design-5a-20261120-01/profile.json").read_text())
    profile.update(index="synthetic-index", output_directory=str(tmp_path / "samples"))
    requests = []

    def request(query):
        requests.append(query)
        return encoded(page(query["query"]["term"]["ocsf.class_uid"])).encode()

    assert sample(profile, request=request) == 0
    root = Path(profile["output_directory"])
    assert {q["query"]["term"]["ocsf.class_uid"] for q in requests} == {c["class_uid"] for c in profile["classes"]}
    assert all(q["size"] == 1 and q["_source"] is True and q["track_total_hits"] is False for q in requests)
    for card in profile["classes"]:
        cls = card["class_uid"]
        assert loads((root / "ocsf" / f"class-{cls}.json").read_text()) == page(cls)["hits"]["hits"][0]["_source"]["ocsf"]
    actual_html = (root / "index.html").read_text()
    assert "synthetic-id" in actual_html and "&lt;script&gt;" in actual_html and "<script>bad()" not in actual_html
    assert "synthetic-id" not in capsys.readouterr().out
    assert loads(pretty({"decimal": Decimal('0.0000000000000000001'), "integer": 2**100})) == {"decimal": Decimal('0.0000000000000000001'), "integer": 2**100}


def test_wrong_class_duplicate_or_incomplete_response_is_rejected():
    good = page(5001)
    seen = set()
    select_one(good, index="synthetic-index", cls=5001, seen=seen)
    for bad, target in [(good, 5001), (page(2004), 5001), (page(5001, timed_out=True), 5001),
                        (page(5001, _shards={"total": 2, "successful": 1, "failed": 1}), 5001),
                        (page(5001, hits={"hits": []}), 5001)]:
        with pytest.raises(ValueError):
            select_one(bad, index="synthetic-index", cls=target, seen=seen)


def test_missing_class_preserves_failure_without_marking_complete(tmp_path, capsys):
    profile = json.loads((Path(__file__).parent / "evidence/class-samples-tool-design-5a-20261120-01/profile.json").read_text())
    profile.update(index="synthetic-index", output_directory=str(tmp_path / "failed"))
    assert sample(profile, request=lambda _: encoded(page(5001, hits={"hits": []})).encode()) == 2
    status = json.loads(capsys.readouterr().out)
    assert status["execution"] == "incomplete" and status["all_requested_classes_sampled"] is False
    assert (Path(profile["output_directory"]) / "failure.json").exists()
