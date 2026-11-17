"""Regenerate the eleven existing records and read their saved data back, without business calls."""
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "docs/operations"))
import update_processing_audit as audit
from processing_audit_delivery import run_delivery

HERE = Path(__file__).parent
EVIDENCE = HERE.parent
SOURCE_NAMES = [
    "fixed-investigation-20261114-01/flow/C01/export",
    "fixed-investigation-20261114-01/flow/C02/export",
    "fixed-investigation-20261114-01/flow/C03/export",
    "stage1-ai-retention-20261114-01/attempt-02",
    "stage1-ai-retention-20261114-01/attempt-03",
    "stage1-case-retention-20261114-01/attempt04-readback/audit-export",
    "stage1-c3-contract-20261114-01/attempt01",
    "stage1-c3-completion-20261114-01/attempt04",
    "stage1-followup-routing-20261114-01/attempt01",
    "stage1-followup-routing-20261114-01/attempt02",
    "stage1-original-retention-20261114-01/attempt03",
]


class Originals(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.reading = False
        self.buffer = []
        self.records = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "pre" and "data-record-json" in dict(attrs):
            self.reading = True
            self.buffer = []

    def handle_data(self, text):
        if self.reading:
            self.buffer.append(text)

    def handle_endtag(self, tag):
        if tag == "pre" and self.reading:
            self.records.append(json.loads("".join(self.buffer)))
            self.reading = False


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = [EVIDENCE / name for name in SOURCE_NAMES]
    before = {str(p.relative_to(ROOT)): digest(p) for folder in sources for p in
              (folder / "database.json", folder / "manifest.json")}
    old = audit.existing(audit.OUTPUT / "index.html")
    # Renderers produce new HTML filenames; old generated pages and all raw exports remain.
    imported, total = audit.update(sources, audit.OUTPUT)
    current = audit.existing(audit.OUTPUT / "index.html")
    assert imported == total == 11 and old.keys() == current.keys()
    checks = []
    for folder in sources:
        case = next(audit.cases_from(folder))
        record, _ = audit.prepare(*case)
        data = case[4]
        path = audit.OUTPUT / record["detail"]
        page = path.read_text()
        records = Originals(page).records
        actual = {r["id"]: r for r in records}
        expected = [r for table in ("runs", "run_steps", "artifacts") for r in data[table]]
        assert len(actual) == len(expected)
        assert all(actual[r["id"]] == r for r in expected)
        views = json.loads(re.search(r'id="inspector-data">(.*?)</script>', page, re.DOTALL)[1])["runs"]
        assert views == {r["id"]: run_delivery(r, data) for r in data["runs"]}
        assert old[record["id"]]["run_states"] == record["run_states"]
        assert old[record["id"]]["artifact_ids"] == record["artifact_ids"]
        checks.append({"source": str(folder.relative_to(ROOT)), "detail": record["detail"],
                       "runs": len(data["runs"]), "steps": len(data["run_steps"]),
                       "artifacts": len(data["artifacts"]), "results": sum(len(v["results"]) for v in views.values()),
                       "originals_equal": True, "same_run_delivery_equal": True,
                       "run_states_unchanged": True, "html_sha256": digest(path)})
    assert before == {name: digest(ROOT / name) for name in before}
    result = {"checks": checks, "source_hashes": before, "source_hashes_unchanged": True,
              "registry_before": len(old), "registry_after": total, "model_calls": 0,
              "business_writes": 0, "renderer_revision": audit.renderer_revision(),
              "quality": "NOT_PASSED", "actual_4177_published": False}
    (HERE / "snapshot-readback.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"records": total, "runs": sum(c["runs"] for c in checks),
                      "artifacts": sum(c["artifacts"] for c in checks), "originals_equal": True}))


if __name__ == "__main__":
    main()
