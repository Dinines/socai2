"""Two explicit D3a list-identity/limit fixtures; no receiver imports or execution."""
import argparse
import copy
import json
from pathlib import Path

from prepare import HERE, complete_spans, save, sha


def main(out):
    mother = (HERE / "fixtures-01/mother.txt").read_text()
    raw = json.loads(mother)
    assert [row["id"] for row in raw["findings"]] == ["F1", "F2", "F3", "F4", "F5"]
    out.mkdir(exist_ok=False)
    records = []
    duplicate = copy.deepcopy(raw)
    duplicate["findings"][1]["id"] = "F1"
    excess = copy.deepcopy(raw)
    extra = copy.deepcopy(excess["findings"][4])
    extra["id"] = "F6"
    excess["findings"].append(extra)
    for name, value, keep, reject, code in (
        ("duplicate-finding-id", duplicate, ["$.findings[2]", "$.findings[3]", "$.findings[4]"],
         ["$.findings[0]", "$.findings[1]"], None),
        ("six-findings", excess, [f"$.findings[{i}]" for i in range(5)],
         ["$.findings[5]"], "section_item_limit_exceeded"),
    ):
        text = json.dumps(value, ensure_ascii=False)
        _, spans = complete_spans(text)
        (out / (name + ".txt")).write_text(text)
        expected = {"name": name, "finish_reason": "stop", "fragment_sha256": sha(text),
                    "must_retain_business_paths": keep, "must_not_retain_paths": reject,
                    "expected_delivery": "partial", "expected_invalid_reason": code,
                    "maximum_accepted_findings": 5, "lexical_units": spans,
                    "derivation": "F2 id becomes F1; both conflict items must be isolated" if name.startswith("duplicate")
                    else "Append a copy of F5 as F6; only original sixth item is over the frozen limit",
                    "provenance": "controlled fixture from complete real-02 mother; no new model output",
                    "expected_source": "explicit D3a identity/limit contract; not the tested parser"}
        save(out / (name + ".expected.json"), expected)
        records.append({"name": name, "sha256": sha(text), "original_findings": len(value["findings"]),
                        "retained_findings_expected": len(keep), "invalid_paths": reject})
    manifest = {"status": "prepared_not_executed", "mother_sha256": sha(mother), "fixtures": records,
                "contract": {"duplicate_definition": "isolate all conflicting definitions",
                             "over_finding_limit": "retain first five valid original items; isolate sixth onward; partial with explicit reason"},
                "model_calls": 0, "database_calls": 0, "product_parser_calls": 0}
    save(out / "manifest.json", manifest)
    print(json.dumps({"status": manifest["status"], "fixtures": len(records)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
