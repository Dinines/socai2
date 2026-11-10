"""Run one current-prompt pass without dispatching historical comparison arms."""
import argparse
import copy
import os
from pathlib import Path

from tools.testdata.alert_io_eval.evaluate import ROOT, encode, run, save, sha
from tools.testdata.alert_prompt_eval.evaluate import read, review


def prepare(config, out, config_path):
    baseline = ROOT / config["baseline"]
    original = read(baseline / "plan-and-packets.json")
    intent = read(baseline / "batch-intent.json")
    assert sha((baseline / "plan-and-packets.json").read_bytes()) == intent["plan_sha256"]
    assert all(sha((ROOT / p).read_bytes()) == h for p, h in original["code_hashes"].items())
    assert config["variants"] == ["candidate"]
    assert config["existing_rounds"] == config["synthetic_rounds"] == 1
    prompt = (ROOT / config["prompt"]).read_text()
    samples, cells = [], []
    for source in original["samples"]:
        sample = copy.deepcopy(source)
        packet = next(v for v in source["variants"] if v["id"] == "input_output")
        assert sha(encode(packet["body"])) == packet["body_sha256"]
        body = copy.deepcopy(packet["body"])
        assert [m["role"] for m in body["messages"]] == ["system", "user"]
        body["messages"][0]["content"] = prompt
        restored = copy.deepcopy(body)
        restored["messages"][0]["content"] = packet["body"]["messages"][0]["content"]
        assert restored == packet["body"]
        sample["variants"] = [{"id": "candidate", "body": body, "body_sha256": sha(encode(body)),
                               "request_bytes": len(encode(body)),
                               "user_bytes": len(body["messages"][1]["content"].encode())}]
        samples.append(sample)
        cells.append({"id": f"{sample['id']}-candidate-r1", "sample": sample["id"],
                      "variant": "candidate", "round": 1})
    protected = sorted(p for p in baseline.rglob("*") if p.is_file())
    code = [Path(__file__), Path(__file__).with_name("evaluate.py"), config_path,
            ROOT / config["prompt"], ROOT / config["base_config"]]
    bundle = {"status": "prepared_no_generation", "batch": config["batch"], "config": config,
              "samples": samples, "cells": cells, "planned_model_calls": len(cells),
              "scope": "one current-prompt call per frozen sample; no control arm, no business writes",
              "baseline_plan_sha256": intent["plan_sha256"],
              "baseline_files": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in protected},
              "code_hashes": {**original["code_hashes"], **{str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in code}},
              "new_model_calls": 0, "retries": 0}
    out.mkdir(parents=True, exist_ok=False)
    (out / "calls").mkdir()
    save(out / "plan-and-packets.json", bundle)
    save(out / "answer-key-not-sent.json", read(baseline / "answer-key-not-sent.json"))
    save(out / "preparation-checks.json", {"samples": len(samples), "cells": len(cells),
         "current_prompt_only": True, "only_system_changed": True, "control_calls": 0,
         "same_input_schema_parameters_and_parser": True, "system_chars": len(prompt),
         "system_bytes": len(prompt.encode()), "old_evidence_files_protected": len(protected)})
    print(read(out / "preparation-checks.json"))


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
