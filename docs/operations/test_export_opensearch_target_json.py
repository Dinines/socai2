import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("es_export", Path(__file__).with_name("export_opensearch_target_json.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def page(hits, total=2, **changes):
    return {"_scroll_id": "synthetic-scroll", "timed_out": False, "_shards": {"total": 1, "successful": 1, "failed": 0},
            "hits": {"total": {"value": total, "relation": "eq"}, "hits": hits}, **changes}


def hit(identity, cls):
    return {"_index": "lyc-json-export", "_id": identity, "_source": {"kafka": {"topic": "lyc-json-export"},
        "ocsf": {"class_uid": cls, "value": Decimal("0.123456789012345678901"),
                 "integer": 123456789012345678901234567890, "false": False, "zero": 0,
                 "empty": [], "null": None, "text": "line\nquote\"control\u0001"}}}


def config(tmp_path):
    return {"output_directory": str(tmp_path/"output"), "base_url": "http://localhost:9200", "authentication": "none",
            "index": "lyc-json-export", "target_class_uids": [0, 1001, 4003], "page_size": 1,
            "request_timeout_seconds": 5, "max_response_bytes": 100000, "max_export_bytes": 1000000,
            "max_records": 10, "max_pages": 10, "scroll_keepalive": "1m"}


class Response:
    def __init__(self, value):
        self.raw = module.encoded(value).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self, limit):
        return self.raw[:limit]


class Opener:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.released = False

    def open(self, request, timeout):
        if request.get_method() == "DELETE":
            assert module.loads(request.data)["scroll_id"] == ["synthetic-scroll"]
            self.released = True
            return Response({"succeeded": True})
        if request.full_url.endswith("/_mapping"):
            return Response({"lyc-json-export": {"mappings": {"properties": {"ocsf": {"properties": {"class_uid": {"type": "long"}}}}}}})
        return Response(next(self.pages))


def test_complete_export_keeps_exact_json_and_all_target_files(tmp_path, monkeypatch):
    originals = [hit("one", 0), hit("two", 1001)]
    opener = Opener([page(originals[:1]), page(originals[1:]), page([])])
    monkeypatch.setattr(module, "build_opener", lambda *_: opener)
    policy = config(tmp_path)
    assert module.export(policy) == 0 and opener.released
    root = Path(policy["output_directory"])
    assert module.verify(root)
    for original in originals:
        cls = original["_source"]["ocsf"]["class_uid"]
        assert module.loads((root/f"json/class-{cls}.json").read_text()) == [original["_source"]["ocsf"]]
    assert module.loads((root/"json/class-4003.json").read_text()) == []
    assert len(list((root/"pages").glob("*.json.gz"))) == 3
    (root/"ocsf.ndjson").write_text('{}\n')
    with pytest.raises(ValueError, match="export_file_mismatch"):
        module.verify(root)


@pytest.mark.parametrize("change", [{"timed_out": True}, {"_shards": {"total": 2, "successful": 1, "failed": 1}},
                                   {"hits": {"total": {"value": 10, "relation": "gte"}, "hits": []}}])
def test_partial_search_cannot_be_treated_as_complete(change):
    with pytest.raises(ValueError):
        module.page_hits({**page([]), **change})


def test_duplicate_or_out_of_scope_document_rejected():
    seen = set()
    module.source_document(hit("one", 1001), "lyc-json-export", [1001], seen)
    with pytest.raises(ValueError, match="duplicate_document"):
        module.source_document(hit("one", 1001), "lyc-json-export", [1001], seen)
    with pytest.raises(ValueError, match="outside_target"):
        module.source_document(hit("two", 4003), "lyc-json-export", [1001], seen)


def test_missing_page_preserves_failure_and_releases_only_own_context(tmp_path, monkeypatch):
    opener = Opener([page([hit("one", 1001)]), page([])])
    monkeypatch.setattr(module, "build_opener", lambda *_: opener)
    policy = config(tmp_path)
    assert module.export(policy) == 2 and opener.released
    root = Path(policy["output_directory"])
    assert json.loads((root/"status.json").read_text())["validation"] == "not_passed"
    assert not (root/"manifest.json").exists()
