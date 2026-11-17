"""Freeze Deep expectations from complete real JSON; no application/recovery import.

Offsets are Unicode code points in the exact received content. Only the complete
mother is decoded. Prefix expectations use its independently recorded spans.
"""

import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def spans(text):
    """Locate fields in a fully valid object using the standard JSON decoder."""
    decoder, result = json.JSONDecoder(), {}
    value = json.loads(text)

    def skip(pos):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        return pos

    pos = skip(0)
    assert text[pos] == "{"
    pos = skip(pos + 1)
    while text[pos] != "}":
        key, pos = decoder.raw_decode(text, pos)
        assert key not in result
        pos = skip(pos)
        assert text[pos] == ":"
        start = skip(pos + 1)
        actual, end = decoder.raw_decode(text, start)
        assert actual == value[key]
        result[key] = {"path": "$." + key, "value_span": [start, end], "value_sha256": sha(text[start:end].encode()), "value": actual}
        pos = skip(end)
        if text[pos] == ",":
            pos = skip(pos + 1)
    return result


def main():
    config = json.loads((HERE / "fixture-config.json").read_text())
    batch = ROOT / config["source_batch"]
    index_path = batch / "model-io/index.json"
    index = json.loads(index_path.read_text())
    sources, frozen, originals = [], {}, {}
    for label in ("primary", "comparison"):
        record = next(r for r in index["requests"] if r["stage"] == config["stage"] and r["run_id"] == config[label + "_run_id"])
        assert record["state"] == "received_original" and record["finish_reason"] == "stop"
        files = {}
        for relative, expected in record["files"].items():
            path = batch / "model-io" / relative
            assert sha(path.read_bytes()) == expected
            files[str(path.relative_to(ROOT))] = expected
            frozen[path] = expected
        folder = (batch / "model-io" / next(iter(record["files"]))).parent
        raw = (folder / "output.txt").read_bytes()
        assert sha(raw) == config[label + "_output_sha256"]
        text = raw.decode()
        response = json.loads((folder / "response.json").read_text())
        original = json.loads((folder / "original-artifact.json").read_text())
        request = json.loads((folder / "request-artifact.json").read_text())
        assert response["choices"][0]["message"]["content"] == text
        assert original["content_json"]["raw"] == response
        assert original["content_json"]["request_artifact_id"] == request["id"] == record["request_artifact_id"]
        assert original["id"] == record["original_artifact_id"]
        assert original["run_id"] == request["run_id"] == record["run_id"]
        assert original["step_id"] == request["step_id"] == record["step_id"]
        units = spans(text)
        assert list(units) == ["action", "binding_id", "reason", "answer"]
        assert units["action"]["value"] == "answer" and units["binding_id"]["value"] is None
        assert units["answer"]["value"]["state"] == "unresolved"
        assert units["answer"]["value"]["support_ids"] == units["answer"]["value"]["counter_ids"] == []
        assert units["answer"]["value"]["limitations"]
        originals[label] = text
        sources.append({"role": label, "run_id": record["run_id"], "step_id": record["step_id"], "request_artifact_id": record["request_artifact_id"], "original_artifact_id": record["original_artifact_id"], "output_path": str((folder / "output.txt").relative_to(ROOT)), "output_sha256": sha(raw), "characters": len(text), "utf8_bytes": len(raw), "actual_finish_reason": "stop", "files": files, "top_level_units": units})

    text = originals["primary"]
    units = sources[0]["top_level_units"]
    answer_start, answer_end = units["answer"]["value_span"]
    answer_raw = text[answer_start:answer_end]
    answer_units = spans(answer_raw)
    text_start, text_end = answer_units["text"]["value_span"]
    inside_text = answer_start + (text_start + text_end) // 2
    random_points = random.Random(config["seed"]).sample(range(1, len(text)), config["random_points"])
    assert random_points == [150, 25, 240]
    definitions = [("complete-stop", len(text), "stop"), ("complete-length", len(text), "length"), ("before-answer-value", answer_start, "length"), ("inside-answer-text", inside_text, "length"), ("answer-close-missing", answer_end - 1, "length"), ("root-close-missing", len(text.rstrip()) - 1, "stop"), *[(f"random-{i}", cut, "length") for i, cut in enumerate(random_points, 1)]]
    output = HERE / "prepared"
    output.mkdir(exist_ok=False)
    fixtures = []

    def fixture(name, full, positions, cut, finish, transformation):
        fragment = full[:cut]
        present = {k: v for k, v in positions.items() if v["value_span"][1] <= cut}
        answer = present.get("answer")
        expected = {"complete_fields": list(present), "missing_or_unclosed_fields": [k for k in positions if k not in present], "answer_retained": answer is not None, "answer_value": answer["value"] if answer else None, "answer_source_span": answer["value_span"] if answer else None, "answer_source_sha256": answer["value_sha256"] if answer else None, "non_query_decision_eligible": len(present) == 4, "query_dispatch_count": 0, "automatic_continuation_calls": 0, "c6_role": "prior_analysis" if answer else None, "full_answer_from_mother_may_backfill": False}
        with (output / (name + ".txt")).open("xb") as stream:
            stream.write(fragment.encode())
        fixtures.append({"id": name, "path": "prepared/" + name + ".txt", "transformation": transformation, "cut_offset": cut, "offset_unit": "Unicode_code_point", "received_utf8_bytes": len(fragment.encode()), "received_sha256": sha(fragment.encode()), "controlled_finish_reason": finish, "expected": expected, "execution_status": "not_run"})

    for name, cut, finish in definitions:
        fixture(name, text, units, cut, finish, "exact_original_prefix_or_complete_content")
    reordered = '{\n  "answer": ' + answer_raw + ',\n  "action": "answer",\n  "binding_id": null,\n  "reason": ' + text[slice(*units["reason"]["value_span"])] + '\n}'
    reordered_units = spans(reordered)
    assert reordered_units["answer"]["value"] == units["answer"]["value"]
    assert reordered_units["answer"]["value_sha256"] == units["answer"]["value_sha256"]
    with (output / "answer-first-controlled-mother.txt").open("x") as stream:
        stream.write(reordered)
    fixture("answer-first-controls-missing", reordered, reordered_units, reordered_units["answer"]["value_span"][1] + 1, "length", "controlled_field_reordering_then_prefix; answer_bytes_unchanged; not_real_model_output")
    assert frozen == {path: sha(path.read_bytes()) for path in frozen}
    manifest = {"schema": "socai2.deep-d5a-independent-expectations.v1", "status": "prepared_not_execution_acceptance", "method": "Complete mothers decoded by Python stdlib only; expected complete fields determined from full original spans, never by the application recovery function.", "source_index": {"path": str(index_path.relative_to(ROOT)), "sha256": sha(index_path.read_bytes())}, "sources": sources, "seed": config["seed"], "random_cut_offsets": random_points, "fixtures": fixtures, "query_guard_coverage": "These original responses propose answer, not query; valid query, missing/unknown binding, duplicate/conflicting controls require separate bounded direct cases in the implementation handoff.", "quality": "Original prose not assessed or repaired; controlled prefixes are not new model generations.", "calls": {"new_model": 0, "new_business": 0, "database": 0, "http": 0}, "originals_unchanged": True}
    save(HERE / "preparation.json", manifest)
    print(json.dumps({"status": manifest["status"], "source_count": len(sources), "fixture_count": len(fixtures), "random_cuts": random_points, "cut_offsets": {f["id"]: f["cut_offset"] for f in fixtures}, "retains_answer": [f["id"] for f in fixtures if f["expected"]["answer_retained"]], "new_model_calls": 0}))


if __name__ == "__main__":
    main()
