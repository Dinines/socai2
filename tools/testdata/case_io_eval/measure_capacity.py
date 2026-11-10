"""Measure two fixed candidates with /tokenize; never invoke model generation."""
import argparse
import asyncio
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from .audit import ROOT, initialize, read, sha


def save(path, value):
    if path.exists():
        raise ValueError("capacity_receipt_already_exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


async def measure(candidate):
    config = read(candidate / "config.json")
    runtime = initialize(config)
    from app.socai2.baseline_store import StoreError, digest
    from app.socai2.model_protocol import prepare_request
    from app.socai2.runtime_policy import active_policy
    from app.socai2.token_budget import BackendTokenMeter

    from tools.testdata.incident_integration.gateway import TokenizerTransport

    plan = config["token_measurement"]
    runtime["transport"]["command_timeout_seconds"] = plan["command_timeout_seconds"]
    policy = active_policy()
    adapter = SimpleNamespace(provider=policy.model.protocol, schema_profile=policy.model.schema_profile)
    folder = candidate / "token-capacity"
    folder.mkdir(exist_ok=False)
    requests = []
    for name, source in (("before", ROOT / config["comparison_candidate"]), ("after", candidate)):
        canonical_path = source / "candidate-request-not-sent.json"
        body = prepare_request(adapter, read(canonical_path))
        if name == "after":
            assert body == read(source / "prepared-request-not-sent.json")
        requests.append((name, source, body))
        save(folder / f"{name}-prepared-request-not-sent.json", body)
    save(folder / "plan.json", {"generation_calls": 0, "planned_tokenizer_requests": 4,
        "protocol": policy.model.protocol, "schema_profile": policy.model.schema_profile,
        "policy_sha256": policy.sha256, "stage": plan["stage"],
        "ssh_target": runtime["transport"]["ssh_target"], "tokenizer": dict(policy.model.tokenizer),
        "transport_command_timeout_seconds": plan["command_timeout_seconds"],
        "inputs": [{"name": n, "candidate": str(p.relative_to(ROOT)), "wire_sha256": digest(b),
                    "canonical_file_sha256": sha(p / "candidate-request-not-sent.json")} for n, p, b in requests]})
    result = {"captured_at": datetime.now(UTC).isoformat(), "mode": "backend_tokenizer_only", "model_generation_calls": 0,
              "database_connections": 0, "created_cases": 0, "deployment_changes": 0, "measurements": [],
              "limitations": ["not_model_quality_or_latency", "not_end_to_end_case_remaining_budget",
                              "schema_envelope_count_is_conservative_not_provider_usage"]}
    for name, source, body in requests:
        calls = folder / name
        calls.mkdir()
        transport = TokenizerTransport(runtime, calls)
        try:
            receipt = await BackendTokenMeter(policy.model, transport=transport).measure(body, plan["stage"])
            entry = {"name": name, "state": "measured", "receipt": receipt, "tokenizer_requests_attempted": transport.calls}
        except (StoreError, OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
            entry = {"name": name, "state": "failed", "error_type": type(exc).__name__,
                     "reason": str(exc) if isinstance(exc, StoreError) else "tokenizer_transport_or_response_error",
                     "tokenizer_requests_attempted": transport.calls}
        save(folder / f"{name}-result.json", entry)
        result["measurements"].append(entry)
        print(json.dumps({"name": name, "state": entry["state"], "tokenizer_requests_attempted": transport.calls}), flush=True)
        if entry["state"] != "measured":
            break
    result["completed"] = len(result["measurements"]) == 2 and all(r["state"] == "measured" for r in result["measurements"])
    result["tokenizer_requests_attempted"] = sum(r["tokenizer_requests_attempted"] for r in result["measurements"])
    save(folder / "summary.json", result)
    print(json.dumps({"output": str(folder), **result}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(measure(args.candidate.resolve()))


if __name__ == "__main__":
    main()
