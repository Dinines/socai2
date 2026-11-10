"""One real I-boundary call on the approved frozen view; no business writes."""
import argparse
import copy
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

from tools.testdata.alert_io_eval.evaluate import ROOT, encode, run, save, sha

from .fixtures import load
from .input_adapter import prepare as render


def read(path):
    return json.loads(path.read_bytes())


def prepare(config, out, config_path):
    from app.socai2.model_protocol import prepare_request
    from app.socai2.runtime_policy import active_policy

    from .output_adapter import candidate_schema

    assert config["planned_model_calls"] == config["attempts_per_cell"] == 1
    approved = ROOT / config["approved_input"]
    code_hashes = read(approved / "source-fingerprints.json")
    assert all(sha((ROOT / p).read_bytes()) == h for p, h in code_hashes.items())
    sample = load(ROOT, config)
    started = time.perf_counter()
    prepared = render(sample["data"], sample["source_map"], config)
    render_seconds = time.perf_counter() - started
    assert encode(prepared) == encode(read(approved / "input-ledger.json")), "approved_view_changed"
    assert prepared["user"] == (approved / "input-after.txt").read_text()
    body = copy.deepcopy(sample["request"]["body"])
    body["messages"] = [
        {"role": "system", "content": (ROOT / config["system_prompt"]).read_text()},
        {"role": "user", "content": prepared["user"]},
    ]
    body["response_format"] = {"type": "json_schema", "json_schema": {
        "name": "incident_boundary_candidate", "strict": True, "schema": candidate_schema(prepared)}}
    assert body == read(approved / "candidate-request-not-sent.json"), "approved_request_changed"
    policy = active_policy()
    assert policy.model.protocol == "chat_completions"
    gateway = SimpleNamespace(provider=policy.model.protocol, schema_profile=policy.model.schema_profile)
    wire = prepare_request(gateway, body)
    protected = [p for p in approved.rglob("*") if p.is_file()]
    protected.append(ROOT / config["snapshot"])
    sources = [Path(__file__), config_path, ROOT / config["base_config"], ROOT / config["transport_config"],
               ROOT / config["policy"], ROOT / "services/api/app/socai2/model_protocol.py",
               ROOT / "services/api/app/socai2/runtime_policy.py",
               ROOT / "services/api/app/socai2/baseline_analysis_model.py",
               ROOT / "tools/testdata/alert_io_eval/evaluate.py",
               ROOT / "tools/testdata/alert_io_eval/remote_worker.py"]
    code_hashes.update({str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sources})
    variant = {"id": "candidate", "body": wire, "body_sha256": sha(encode(wire)),
               "request_bytes": len(encode(wire)), "user_bytes": len(prepared["user"].encode())}
    subject = {"id": config["sample_id"], "kind": "recorded", "prepared": prepared,
               "variants": [variant], "render_seconds": render_seconds,
               "canonical_schema": body["response_format"]["json_schema"]["schema"],
               "original_usage": sample["response"]["usage"], "original_answer": sample["answer"],
               "original_user_bytes": len(sample["request"]["body"]["messages"][-1]["content"].encode())}
    cell = {"id": f"{config['sample_id']}-candidate-r1", "sample": config["sample_id"], "variant": "candidate", "round": 1}
    bundle = {"status": "prepared_no_generation", "batch": config["batch"], "config": config,
              "samples": [subject], "cells": [cell], "planned_model_calls": 1, "retries": 0,
              "scope": "one current I candidate; frozen existing event; no control arm, queries, business Run or DB writes",
              "source_run_id": sample["run"]["id"], "snapshot_sha256": sample["snapshot_sha256"],
              "schema_profile": policy.model.schema_profile, "code_hashes": code_hashes,
              "baseline_files": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in protected}}
    out.mkdir(parents=True, exist_ok=False)
    (out / "calls").mkdir()
    save(out / "plan-and-packets.json", bundle)
    save(out / "canonical-request.json", body)
    save(out / "preparation-checks.json", {
        "approved_input_and_request_unchanged": True, "planned_model_calls": 1, "retries": 0,
        "members": len(prepared["member_aliases"]), "visible_sources": len(prepared["source_map"]),
        "user_bytes": variant["user_bytes"], "full_wire_bytes": variant["request_bytes"],
        "max_output_tokens": wire["max_tokens"], "schema_profile": policy.model.schema_profile,
        "new_a_receipts_added": 0, "new_business_data": False,
    })
    print(json.dumps(read(out / "preparation-checks.json"), ensure_ascii=False))


def review(config, out):
    from app.socai2.baseline_analysis_model import usage
    from app.socai2.baseline_store import StoreError
    from jsonschema import Draft202012Validator
    from jsonschema import ValidationError as SchemaError
    from pydantic import ValidationError

    from .output_adapter import decode, parse
    from .output_adapter import review as review_partial

    bundle = read(out / "plan-and-packets.json")
    assert config == bundle["config"]
    assert all(sha((ROOT / p).read_bytes()) == h for p, h in bundle["code_hashes"].items())
    subject, cell = bundle["samples"][0], bundle["cells"][0]
    raw = read(out / "calls" / (cell["id"] + "-result.json"))
    row = {**cell, "state": raw["state"], "http_seconds": raw.get("http_seconds"),
           "usage": usage(raw.get("raw")), "wire_schema_valid": None, "canonical_schema_valid": None,
           "accepted": False, "parse_error": None}
    content = None
    if raw["state"] == "response_received":
        try:
            choices = raw["raw"]["choices"]
            assert len(choices) == 1 and choices[0]["finish_reason"] == "stop", "incomplete_response"
            content = choices[0]["message"]["content"]
            row["answer"] = decode(content)
            Draft202012Validator(subject["variants"][0]["body"]["response_format"]["json_schema"]["schema"]).validate(row["answer"])
            row["wire_schema_valid"] = True
            Draft202012Validator(subject["canonical_schema"]).validate(row["answer"])
            row["canonical_schema_valid"] = True
            started = time.perf_counter()
            diagnostics = {}
            output, members = parse(content, subject["prepared"], diagnostics=diagnostics)
            row.update(accepted=True, parsed_output=output.model_dump(mode="json"),
                       validated_members=members, diagnostics=diagnostics,
                       parse_seconds=time.perf_counter() - started)
        except (StoreError, SchemaError, ValidationError, ValueError, AssertionError, KeyError, TypeError) as exc:
            row["parse_error"] = getattr(exc, "code", type(exc).__name__)
            if row["wire_schema_valid"] is None:
                row["wire_schema_valid"] = False
            if content is not None:
                try:
                    _, detail = review_partial(content, subject["prepared"])
                    row["partial_review"] = detail
                except (StoreError, SchemaError, ValidationError, ValueError, KeyError, TypeError) as partial_error:
                    row["partial_error"] = getattr(partial_error, "code", type(partial_error).__name__)
    unchanged = all(sha((ROOT / p).read_bytes()) == h for p, h in bundle["baseline_files"].items())
    assert unchanged
    save(out / "parsed-results.json", {"results": [row], "raw_answers_are_not_rewritten": True,
                                       "old_evidence_unchanged": unchanged, "semantic_review": "pending_manual_review"})
    print(json.dumps({k: row[k] for k in ("state", "http_seconds", "usage", "wire_schema_valid",
                                        "canonical_schema_valid", "accepted", "parse_error")}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "review"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    override = read(args.config)
    config = read(ROOT / override["base_config"])
    config.update({k: v for k, v in override.items() if k != "transport_overrides"})
    config["transport"] = {**read(ROOT / config["transport_config"])["transport"], **override["transport_overrides"]}
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
