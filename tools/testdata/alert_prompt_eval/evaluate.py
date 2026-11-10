"""Compare two task prompts, preserving frozen input, output schema and model settings."""
import argparse
import copy
import json
import os
import time
from pathlib import Path

from tools.testdata.alert_io_eval.evaluate import ROOT, encode, run, save, sha


def read(path):
    return json.loads(path.read_bytes())


def prepare(config, out, config_path):
    baseline = ROOT / config["baseline"]
    original = read(baseline / "plan-and-packets.json")
    intent = read(baseline / "batch-intent.json")
    assert sha((baseline / "plan-and-packets.json").read_bytes()) == intent["plan_sha256"]
    assert all(sha((ROOT / p).read_bytes()) == h for p, h in original["code_hashes"].items())
    assert read(baseline / "completion.json")["runtime_unchanged"]
    prompt = (ROOT / config["prompt"]).read_text()
    samples, cells = [], []
    for index, source in enumerate(original["samples"]):
        sample = copy.deepcopy(source)
        packet = next(v for v in source["variants"] if v["id"] == "input_output")
        assert sha(encode(packet["body"])) == packet["body_sha256"]
        assert [m["role"] for m in packet["body"]["messages"]] == ["system", "user"]
        variants = []
        for variant in config["variants"]:
            body = copy.deepcopy(packet["body"])
            if variant == "candidate":
                body["messages"][0]["content"] = prompt
            restored = copy.deepcopy(body)
            restored["messages"][0]["content"] = packet["body"]["messages"][0]["content"]
            assert restored == packet["body"], "only system content may change"
            variants.append({"id": variant, "body": body, "body_sha256": sha(encode(body)),
                             "request_bytes": len(encode(body)),
                             "user_bytes": len(body["messages"][1]["content"].encode()),
                             "system_bytes": len(body["messages"][0]["content"].encode()),
                             "system_chars": len(body["messages"][0]["content"])})
        sample["variants"] = variants
        samples.append(sample)
        rounds = config["existing_rounds"] if sample["kind"] == "recorded" else config["synthetic_rounds"]
        for repeat in range(rounds):
            order = config["variants"] if (index + repeat) % 2 == 0 else config["variants"][::-1]
            for variant in order:
                cells.append({"id": f"{sample['id']}-{variant}-r{repeat+1}", "sample": sample["id"],
                              "variant": variant, "round": repeat + 1})
    protected = sorted(p for p in baseline.rglob("*") if p.is_file())
    code = [*Path(__file__).parent.glob("*.py"), ROOT / config["prompt"], config_path,
            ROOT / config["base_config"]]
    bundle = {"status": "prepared_no_generation", "batch": config["batch"], "config": config,
              "samples": samples, "cells": cells, "planned_model_calls": len(cells),
              "scope": "fresh paired five-field calls; only system content differs; no business writes",
              "baseline_plan_sha256": intent["plan_sha256"],
              "baseline_files": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in protected},
              "code_hashes": {**original["code_hashes"], **{str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in code}},
              "new_model_calls": 0, "retries": 0}
    out.mkdir(parents=True, exist_ok=False)
    (out / "calls").mkdir()
    save(out / "plan-and-packets.json", bundle)
    save(out / "answer-key-not-sent.json", read(baseline / "answer-key-not-sent.json"))
    save(out / "preparation-checks.json", {"samples": len(samples), "cells": len(cells),
         "only_system_changed": True, "input_output_schema_parameters_equal": True,
         "old_evidence_files_protected": len(protected), "prompt_sizes": [
             {k: v[k] for k in ("id", "system_bytes", "system_chars")} for v in samples[0]["variants"]]})
    print(json.dumps(read(out / "preparation-checks.json"), ensure_ascii=False))


def review(config, out):
    import jsonschema
    from app.socai2.baseline_analysis_model import usage
    from app.socai2.stage_answer_review import review_alert
    from tools.testdata.alert_io_eval.output_adapter import canonical, parse

    bundle = read(out / "plan-and-packets.json")
    samples = {s["id"]: s for s in bundle["samples"]}
    results = []
    for cell in bundle["cells"]:
        path = out / "calls" / (cell["id"] + "-result.json")
        if not path.exists():
            continue
        raw = read(path)
        sample = samples[cell["sample"]]
        packet = next(v for v in sample["variants"] if v["id"] == cell["variant"])
        row = {**cell, "state": raw["state"], "http_seconds": raw.get("http_seconds"),
               "usage": usage(raw.get("raw")), "wire_schema_valid": None, "accepted": False,
               "parse_error": None}
        content = None
        if raw["state"] == "response_received":
            try:
                choices = raw["raw"]["choices"]
                assert len(choices) == 1 and choices[0]["finish_reason"] == "stop"
                content = choices[0]["message"]["content"]
                row["answer"] = json.loads(content)
                jsonschema.validate(row["answer"], packet["body"]["response_format"]["json_schema"]["schema"])
                row["wire_schema_valid"] = True
                start = time.perf_counter()
                output = parse(content, sample["prepared"])
                row.update(accepted=True, parsed_output=output.model_dump(mode="json"),
                           parse_seconds=time.perf_counter() - start)
            except Exception as exc:
                row["parse_error"] = getattr(exc, "code", type(exc).__name__)
                if row["wire_schema_valid"] is None:
                    row["wire_schema_valid"] = False
                if content is not None:
                    try:
                        _, detail = review_alert(json.dumps(canonical(content), ensure_ascii=False),
                                                 sample["prepared"]["source_map"], sample["data"])
                        row["partial_review"] = detail
                    except Exception as partial_error:
                        row["partial_error"] = getattr(partial_error, "code", type(partial_error).__name__)
        results.append(row)
    save(out / "parsed-results.json", {"results": results, "raw_answers_are_not_rewritten": True,
                                      "semantic_review": "pending_manual_review"})
    assert all(sha((ROOT / p).read_bytes()) == h for p, h in bundle["baseline_files"].items())
    print(json.dumps({"responses": len(results), "schema_passed": sum(r["wire_schema_valid"] is True for r in results),
                      "parser_passed": sum(r["accepted"] for r in results), "old_evidence_unchanged": True}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "review"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    override = read(args.config)
    config = read(ROOT / override["base_config"])
    config.update({k: v for k, v in override.items() if k != "transport_overrides"})
    config["transport"] = {**config["transport"], **override["transport_overrides"]}
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])
    out = ROOT / config["output"]
    if args.phase == "prepare":
        prepare(config, out, args.config.resolve())
    elif args.phase == "run":
        run(config, out)
    else:
        review(config, out)


if __name__ == "__main__":
    main()
