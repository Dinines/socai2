"""Freeze C3 prefix expectations from a complete real answer, without a recovery parser.

Only stdlib JSON decoding of the complete mother identifies original value spans.
The application under test is neither imported nor called. Prefixes are never
decoded to generate expected values. Business acceptance is checked separately.
"""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def complete_spans(text):
    """Locate only top-level fields and their array items in a complete object."""
    decoder = json.JSONDecoder()
    value = json.loads(text)
    spans = []

    def skip(pos):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        return pos

    def add(path, start, end, parsed, kind):
        assert json.loads(text[start:end]) == parsed
        spans.append({"path": path, "value_span": [start, end], "value_sha256": sha(text[start:end]),
                      "value": parsed, "kind": kind})

    pos = skip(0)
    assert text[pos] == "{"
    pos = skip(pos + 1)
    while text[pos] != "}":
        key, pos = decoder.raw_decode(text, pos)
        pos = skip(pos)
        assert text[pos] == ":"
        start = skip(pos + 1)
        parsed, end = decoder.raw_decode(text, start)
        assert parsed == value[key]
        if isinstance(parsed, list):
            if not parsed:
                add("$." + key, start, end, parsed, "explicit_empty_array")
            child = skip(start + 1)
            for index, expected in enumerate(parsed):
                actual, child_end = decoder.raw_decode(text, child)
                assert actual == expected
                add(f"$.{key}[{index}]", child, child_end, actual, "array_item")
                child = skip(child_end)
                if text[child] == ",":
                    child = skip(child + 1)
        else:
            add("$." + key, start, end, parsed, "scalar")
        pos = skip(end)
        if text[pos] == ",":
            pos = skip(pos + 1)
    return value, spans


def main(out):
    config = json.loads((HERE / "fixture-config.json").read_text())
    batch = ROOT / config["source_batch"]
    calls = json.loads((batch / "calls.json").read_text())
    rows = json.loads((batch / "database.json").read_text())
    call = calls[config["call_index"]]
    assert call["stage"] == config["stage"] and call["state"] == "responded"
    mother = call["response"]["choices"][0]["message"]["content"]
    value, spans = complete_spans(mother)
    assert {key: len(value[key]) for key in config["expected_section_counts"]} == config["expected_section_counts"]
    original = next(a for a in rows["artifacts"] if (a["content_json"] or {}).get("raw") == call["response"])
    request = next(a for a in rows["artifacts"] if a["kind"] == "model_request" and
                   a["content_json"]["payload"]["body"] == call["request"])
    assert original["run_id"] == request["run_id"] == rows["runs"][0]["id"]
    second = next(s for s in spans if s["path"] == "$.findings[1]")
    first = next(s for s in spans if s["path"] == "$.findings[0]")
    inside_second = sum(second["value_span"]) // 2
    assert first["value_span"][1] < inside_second < second["value_span"][1]
    root_end = len(mother.rstrip()) - 1
    assert mother[root_end] == "}"
    boundaries = {inside_second, root_end}
    points = random.Random(config["seed"]).sample([i for i in range(1, len(mother)) if i not in boundaries],
                                                 config["random_points"])
    variants = [("complete-stop", len(mother), "stop"), ("complete-length", len(mother), "length"),
                ("f1-closed-f2-partial", inside_second, "length"), ("root-close-missing", root_end, "stop"),
                ("empty", 0, "stop"), *[(f"random-{i}", cut, "length") for i, cut in enumerate(points, 1)]]
    out.mkdir(exist_ok=False)
    (out / "mother.txt").write_text(mother)
    save(out / "mother-units.json", spans)
    fixtures = []
    for name, cut, finish in variants:
        fragment = mother[:cut]
        (out / (name + ".txt")).write_text(fragment)
        complete = [s for s in spans if s["value_span"][1] <= cut]
        missing = [s["path"] for s in spans if s["value_span"][1] > cut]
        expected = {"name": name, "finish_reason": finish, "cut_offset": cut, "offset_unit": "Unicode_code_point",
                    "cut_utf8_bytes": len(fragment.encode()), "fragment_sha256": sha(fragment),
                    "lexically_complete_original_units": complete, "not_yet_complete_paths": missing,
                    "expected_source": "complete mother + original spans; no prefix recovery parser",
                    "business_acceptance": "must independently apply frozen identity/dependency contract",
                    "dispatch": "only complete followups with satisfied dependencies; no invented action"}
        if name == "f1-closed-f2-partial":
            assert [s["path"] for s in complete] == ["$.summary", *[f"$.members[{i}]" for i in range(4)], "$.findings[0]"]
            expected["must_retain_business_paths"] = [s["path"] for s in complete]
            expected["must_not_retain_paths"] = missing
            expected["dispatch_paths"] = []
        if name == "empty":
            expected.update(expected_delivery="none", dispatch_paths=[], must_retain_business_paths=[])
        save(out / (name + ".expected.json"), expected)
        fixtures.append({key: expected[key] for key in ("name", "cut_offset", "cut_utf8_bytes", "finish_reason", "fragment_sha256")})
    manifest = {"status": "prepared_not_executed", "source_batch": config["source_batch"],
                "source_hashes": {name: hashlib.sha256((batch / name).read_bytes()).hexdigest()
                                  for name in ("calls.json", "database.json")},
                "original_artifact_id": original["id"], "request_artifact_id": request["id"],
                "original_content_path": "$.raw.choices[0].message.content", "run_id": original["run_id"],
                "mother_sha256": sha(mother), "mother_characters": len(mother), "mother_utf8_bytes": len(mother.encode()),
                "seed": config["seed"], "random_algorithm": "random.Random.sample", "random_points": points,
                "python_version": sys.version.split()[0], "complete_units": len(spans), "fixtures": fixtures,
                "remaining_controlled_boundaries": ["whitespace", "escaped_strings", "unterminated_number",
                    "duplicate_keys", "unknown_member", "explicit_empty_vs_missing", "followup_missing_dependency",
                    "single_completion_failure"], "model_calls": 0, "database_calls": 0,
                "tested_recovery_parser_calls": 0}
    save(out / "manifest.json", manifest)
    print(json.dumps({k: manifest[k] for k in ("status", "mother_characters", "complete_units", "random_points")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
