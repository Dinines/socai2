"""Prepare/run/review an immutable, three-arm A-only experiment."""
import argparse
import copy
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/api"))


def sha(value):
    return hashlib.sha256(value).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def remote(config, request):
    cfg = config["transport"]
    request["transport"] = cfg
    worker = Path(__file__).with_name("remote_worker.py").read_text()
    argv = [cfg["ssh_binary"], "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "UpdateHostKeys=no", "-o", f"ConnectTimeout={cfg['connect_timeout_seconds']}", cfg["ssh_target"],
            shlex.join([cfg["remote_python"], "-c", worker])]
    started = time.monotonic()
    try:
        result = subprocess.run(argv, input=json.dumps(request, ensure_ascii=False), text=True,
                                capture_output=True, timeout=cfg["command_timeout_seconds"], check=False)
    except subprocess.TimeoutExpired:
        return {"state": "transport_unknown_no_retry", "transport_seconds": round(time.monotonic() - started, 6)}
    if result.returncode:
        return {"state": "transport_unknown_no_retry", "exit_code": result.returncode,
                "error": result.stderr[:500], "transport_seconds": round(time.monotonic() - started, 6)}
    value = json.loads(result.stdout)
    value["transport_seconds"] = round(time.monotonic() - started, 6)
    return value


def prepare(config, out):
    from app.socai2 import alert_basic_contract as legacy
    from app.socai2.model_protocol import prepare_request
    from app.socai2.runtime_policy import active_policy
    from .fixtures import packets
    from .input_adapter import prepare as render
    from .output_adapter import schema
    subjects, key, provenance = packets(ROOT, config)
    policy = active_policy()
    gateway = SimpleNamespace(provider=policy.model.protocol, schema_profile=policy.model.schema_profile)
    spec = Path(__file__).with_name("five-field-system.txt").read_text()
    prepared, cells = [], []
    for i, subject in enumerate(subjects):
        start = time.perf_counter()
        compact = render(subject["data"], subject["source_map"], config)
        compact["render_seconds"] = time.perf_counter() - start
        variants = []
        for variant in config["variants"]:
            body = copy.deepcopy(subject["body"])
            body.update(max_tokens=config["output_tokens"], temperature=config["temperature"])
            if variant != "current":
                body["messages"] = [{"role": "system", "content": (legacy.PROMPT if variant == "input_only" else spec)
                                     + "\n" + config["render"]["format_instruction"]},
                                    {"role": "user", "content": compact["user"]}]
                body["response_format"] = (legacy.constrained_response_format(compact["source_map"])
                                           if variant == "input_only" else schema(compact["source_map"]))
            body = prepare_request(gateway, body)
            variants.append({"id": variant, "body": body, "body_sha256": sha(encode(body)),
                             "request_bytes": len(encode(body)), "user_bytes": len(body["messages"][1]["content"].encode())})
        rounds = config["existing_rounds"] if subject["kind"] == "recorded" else config["synthetic_rounds"]
        for r in range(rounds):
            order = config["variants"][((i + r) % 3):] + config["variants"][:((i + r) % 3)]
            for variant in order:
                cells.append({"id": f"{subject['id']}-{variant}-r{r+1}", "sample": subject["id"], "variant": variant, "round": r+1})
        prepared.append({**subject, "prepared": compact, "variants": variants})
    code = sorted(Path(__file__).parent.glob("*.py")) + sorted(Path(__file__).parent.glob("*.txt"))
    code += [ROOT / "services/api/app/socai2/alert_basic_contract.py",
             ROOT / "services/api/app/socai2/stage_answer_review.py", ROOT / config["policy"]]
    bundle = {"status": "prepared_no_generation", "batch": config["batch"], "config": config,
              "provenance": provenance, "code_hashes": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in code},
              "samples": prepared, "cells": cells, "planned_model_calls": len(cells),
              "scope": "frozen A model boundary only; no business Run, DB write, real tool query or production deployment",
              "goal": "classify this alert as malicious, benign, false positive or needs_review with justified evidence",
              "new_model_calls": 0, "retries": 0}
    save(out / "plan-and-packets.json", bundle)
    save(out / "answer-key-not-sent.json", key)
    print(json.dumps({"samples": len(prepared), "planned_model_calls": len(cells),
                      "bytes": [{"sample": s["id"], **{v["id"]: v["user_bytes"] for v in s["variants"]}} for s in prepared]}))


def run(config, out):
    bundle = json.loads((out / "plan-and-packets.json").read_text())
    assert bundle["config"] == config
    assert all(sha((ROOT / p).read_bytes()) == h for p, h in bundle["code_hashes"].items())
    if not (out / "preflight.json").exists():
        preflight = remote(config, {"phase": "preflight"})
        save(out / "preflight.json", preflight)
    else:
        preflight = json.loads((out / "preflight.json").read_text())
    assert preflight.get("state") == "ready", preflight
    save(out / "batch-intent.json", {"started_at": datetime.now(UTC).isoformat(),
                                     "plan_sha256": sha((out / "plan-and-packets.json").read_bytes()),
                                     "planned_model_calls": len(bundle["cells"]), "retries": 0})
    samples = {s["id"]: s for s in bundle["samples"]}
    for cell in bundle["cells"]:
        sample = samples[cell["sample"]]
        request = next(v for v in sample["variants"] if v["id"] == cell["variant"])
        save(out / "calls" / (cell["id"] + "-intent.json"), {"cell": cell, "body_sha256": request["body_sha256"], "attempt": 1})
        result = remote(config, {"phase": "call", "cell": cell["id"], "body": request["body"], "timeout_seconds": config["timeout_seconds"]})
        save(out / "calls" / (cell["id"] + "-result.json"), result)
        print(json.dumps({"cell": cell["id"], "state": result["state"], "seconds": result.get("http_seconds"),
                          "usage": result.get("raw", {}).get("usage")}), flush=True)
        if "unknown" in result["state"]:
            print(json.dumps({"stopped": "uncertain_dispatch_not_retried"}), flush=True)
            return
    after = remote(config, {"phase": "preflight"})
    save(out / "completion.json", {"finished_at": datetime.now(UTC).isoformat(), "after": after,
                                  "runtime_unchanged": after.get("runtime_sha256") == preflight["runtime_sha256"],
                                  "route_unchanged": all(after.get(k) == preflight.get(k) for k in ("model", "upstream_model", "upstream_base"))})


def review(config, out):
    from app.socai2 import alert_basic_contract as legacy
    from app.socai2.baseline_analysis_model import usage
    from app.socai2.stage_answer_review import review_alert
    from .output_adapter import canonical, parse
    import jsonschema
    bundle = json.loads((out / "plan-and-packets.json").read_text())
    samples = {s["id"]: s for s in bundle["samples"]}
    truths = {s["sample"]: s for s in json.loads((out / "answer-key-not-sent.json").read_text())}
    results = []
    for cell in bundle["cells"]:
        path = out / "calls" / (cell["id"] + "-result.json")
        if not path.exists():
            continue
        raw = json.loads(path.read_text())
        row = {**cell, "state": raw["state"], "http_seconds": raw.get("http_seconds"),
               "usage": usage(raw.get("raw")), "wire_schema_valid": None, "accepted": False,
               "parse_error": None, "directional_error": None, "needs_review": None}
        sample = samples[cell["sample"]]
        variant = next(v for v in sample["variants"] if v["id"] == cell["variant"])
        content = None
        if raw["state"] == "response_received":
            try:
                choices = raw["raw"]["choices"]
                assert len(choices) == 1 and choices[0]["finish_reason"] == "stop"
                content = choices[0]["message"]["content"]
                row["answer"] = json.loads(content)
                jsonschema.validate(row["answer"], variant["body"]["response_format"]["json_schema"]["schema"])
                row["wire_schema_valid"] = True
                start = time.perf_counter()
                if cell["variant"] == "input_output":
                    result = parse(content, sample["prepared"])
                else:
                    mapping = sample["source_map"] if cell["variant"] == "current" else sample["prepared"]["source_map"]
                    result = legacy.parse(content, mapping, sample["data"])
                row.update(accepted=True, parsed_output=result.model_dump(mode="json"), parse_seconds=time.perf_counter() - start)
            except Exception as exc:
                row["parse_error"] = getattr(exc, "code", type(exc).__name__)
                if row["wire_schema_valid"] is None:
                    row["wire_schema_valid"] = False
                if content is not None:
                    try:
                        if cell["variant"] == "input_output":
                            converted = json.dumps(canonical(content), ensure_ascii=False)
                            partial, detail = review_alert(converted, sample["prepared"]["source_map"], sample["data"])
                        else:
                            mapping = sample["source_map"] if cell["variant"] == "current" else sample["prepared"]["source_map"]
                            partial, detail = review_alert(content, mapping, sample["data"])
                        row["partial_review"] = detail
                        row["partially_usable_core"] = partial is not None
                    except Exception as partial_error:
                        row["partial_error"] = getattr(partial_error, "code", type(partial_error).__name__)
        if "answer" in row:
            verdict = row["answer"].get("verdict")
            row["needs_review"] = verdict == "needs_review"
            if cell["sample"] in truths:
                truth = truths[cell["sample"]]["direction"]
                row["directional_error"] = (truth == "malicious" and verdict in {"benign", "false_positive"}
                                            or truth == "non_malicious" and verdict == "true_positive")
                row["direction_label"] = truth
                row["exact_label"] = {"benign_true_positive": "benign"}.get(truths[cell["sample"]]["expected"], truths[cell["sample"]]["expected"])
                row["exact_match"] = verdict == row["exact_label"]
        results.append(row)
    save(out / "parsed-results.json", {"results": results, "raw_answers_are_not_rewritten": True,
                                      "semantic_review": "pending_manual_factual_and_evidence_review"})
    for r in results:
        print(json.dumps({k: r.get(k) for k in ("id", "accepted", "parse_error", "needs_review", "directional_error")}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "review"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])
    out = ROOT / config["output"]
    {"prepare": prepare, "run": run, "review": review}[args.phase](config, out)


if __name__ == "__main__":
    main()
