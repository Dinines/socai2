"""One JSON field-order counterexample; semantic content remains identical."""
import argparse
import json
from pathlib import Path

from prepare import HERE, complete_spans, save, sha


def main(out):
    mother = (HERE / "fixtures-01/mother.txt").read_text()
    raw = json.loads(mother)
    order = ["summary", "members", "domains", "conflicts", "findings", "questions", "followups"]
    reordered = json.dumps({key: raw[key] for key in order}, ensure_ascii=False)
    assert json.loads(reordered) == raw
    _, units = complete_spans(reordered)
    assert any(domain["finding_ids"] for domain in raw["domains"])
    out.mkdir(exist_ok=False)
    (out / "domains-before-findings.txt").write_text(reordered)
    save(out / "domains-before-findings.expected.json", {
        "name": "domains-before-findings", "finish_reason": "stop", "fragment_sha256": sha(reordered),
        "must_retain_business_paths": [unit["path"] for unit in units], "lexical_units": units,
        "semantic_equal_to": "fixtures-01/complete-stop.txt",
        "expected_quality": "same path/code/action as original order; do not invent missing-finding diagnostics",
        "derivation": "Only change root field order: domains/conflicts before findings; preserve every value",
        "provenance": "controlled field-order variant of real C3; not a new model call"})
    save(out / "manifest.json", {"status": "prepared_not_executed", "mother_sha256": sha(mother),
        "fixture_sha256": sha(reordered), "semantic_values_unchanged": True,
        "model_calls": 0, "database_calls": 0, "product_parser_calls": 0})
    print("Prepared one semantically identical field-order variant")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
