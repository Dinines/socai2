"""Five frozen inputs, two protocols: C3 dynamic schema capacity, no dispatch."""
import copy
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))

from app.socai2 import baseline_analysis_contract as contract
from app.socai2.baseline_analysis import budget_reason, messages
from app.socai2.baseline_capacity import final_reservation
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_dispatch import offered_bindings
from app.socai2.baseline_evidence_tools import catalog
from app.socai2.baseline_execution_schema import (
    compact_execution_wire,
    execution_format,
)
from app.socai2.baseline_store import digest, encoded
from app.socai2.model_protocol import prepare_request
from app.socai2.structured_output import response_format
from diagnose_socai2_kafka_inputs_20261105 import DIRECTORY
from jsonschema import Draft202012Validator

OUTPUT = ROOT / "docs/operations/evidence/investigation-repair-20261105/execution-schema-capacity-20261105.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [("historical", max(DIRECTORY.glob("database-*.json")))]
    for suffix, stamp in (("a", "20261105T102314778605Z"), ("b", "20261105T104937427659Z")):
        paths.append(("local-" + suffix, ROOT / ".local/local-investigation/validation"
            / ("local-maintenance-20261105" + suffix) / "exports" / stamp / "database.json"))
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for _, p in paths}
    measurements = []
    for label, path in paths:
        db = json.loads(path.read_text())
        runs = [r for r in db["runs"] if r["kind"] == "baseline"
            and (label != "historical" or r["stop_reason"] == "required_model_input_unavailable")]
        for run in runs:
            artifacts = [a for a in db["artifacts"] if a["run_id"] == run["id"] and isinstance(a["content_json"], dict)]
            context = Context.model_validate(next(a["content_json"] for a in artifacts
                if a["schema_version"] == "socai2.baseline-context.v1"))
            prepared = next(a["content_json"] for a in artifacts if a["schema_version"] == "socai2.baseline-model-view.v4")
            material = next((a["content_json"] for a in artifacts if a["content_json"].get("type") == "materials"), None)
            source_catalog = material["catalog"] if material else catalog(context, run["tenant_id"])
            limits = Limits.model_validate(run["limits"]).model_copy(update={"max_tokens": 48000,
                "deadline_at": context.captured_at + timedelta(seconds=120)})
            tools = {a["id"]: a["content_json"] for a in artifacts if a["kind"] == "tool_response"}
            options, bindings, _ = offered_bindings(source_catalog, limits, context.captured_at, [],
                SimpleNamespace(configured=lambda: True))
            prompt, source_map = messages(prepared, context, tools, options)
            bindings = {o["binding_id"]: bindings[o["binding_id"]] for o in options}
            original_format = response_format(contract.ExecutionAnalysis, source_map, members=context.alerts,
                questions=[q.id for q in context.questions], objects=context.scope.object_keys, bindings=bindings)
            dynamic = execution_format(original_format, bindings)
            for protocol in ("chat_completions", "deepseek_responses"):
                gateway = SimpleNamespace(provider=protocol, schema_profile="standard", model="deepseek-flash")
                canonical = {"model": gateway.model, "messages": prompt, "max_tokens": 3000,
                    "temperature": 0, "response_format": original_format}
                original_wire = prepare_request(gateway, canonical)
                candidate = prepare_request(gateway, {**canonical, "response_format": dynamic})
                before_alias = copy.deepcopy(candidate)
                candidate = compact_execution_wire(candidate)
                assert {k: v for k, v in candidate.items() if k not in {"text", "response_format"}} == {
                    k: v for k, v in before_alias.items() if k not in {"text", "response_format"}}
                reservation = final_reservation(gateway, context)
                reason = budget_reason([], limits, len(encoded(candidate)), context.captured_at,
                    reserve_calls=1, reservation=reservation)
                assert reason is None
                schema = (candidate["text"]["format"] if "text" in candidate else candidate["response_format"]["json_schema"])["schema"]
                Draft202012Validator.check_schema(schema)
                rejection = None
                if label == "local-b":
                    rsp = next(a for a in artifacts if a["kind"] == "model_response")
                    value = json.loads(rsp["content_json"]["payload"]["raw"]["output"][0]["content"][0]["text"])
                    rejection = not Draft202012Validator(schema).is_valid(value)
                    assert rejection
                measurements.append({"input": label, "run_id": run["id"], "protocol": protocol,
                    "original_run_budget_unchanged": run["limits"]["max_tokens"], "candidate_budget": 48000,
                    "offered_bindings": len(bindings), "facts_bytes": len(prompt[1]["content"].encode()),
                    "facts_sha256": digest(json.loads(prompt[1]["content"])), "messages_bytes": len(encoded(prompt)),
                    "ordinary_wire_bytes": len(encoded(original_wire)), "dynamic_before_alias_bytes": len(encoded(before_alias)),
                    "dynamic_aliased_wire_bytes": len(encoded(candidate)),
                    "alias_bytes_saved": len(encoded(before_alias)) - len(encoded(candidate)),
                    "final_reserved_units": reservation["conservative_units"],
                    "conservative_total": len(encoded(candidate)) + 3256 + reservation["conservative_units"],
                    "remaining_margin": 48000 - len(encoded(candidate)) - 3256 - reservation["conservative_units"],
                    "admission": reason, "candidate_request_sha256": digest(candidate),
                    "original_b_response_rejected_by_dynamic_wire_schema": rejection})
    after = {str(p.relative_to(ROOT)): sha(p) for _, p in paths}
    assert after == source_hashes and len(measurements) == 10
    sources = [ROOT / p for p in ("services/api/app/socai2/baseline_execution_schema.py",
        "services/api/app/socai2/baseline_analysis.py", "services/api/app/socai2/baseline_analysis_contract.py",
        "services/api/app/socai2/model_protocol.py", "services/api/app/socai2/structured_output.py",
        "services/api/tests/test_socai2_execution_schema.py", "services/api/tests/test_socai2_execution_capacity.py")]
    sources.append(Path(__file__))
    result = {"kind": "offline_dynamic_c3_schema_capacity_not_model_validation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": ".local/conda-envs/socai2/bin/python docs/operations/measure_socai2_execution_schema_20261105.py",
        "frozen_input_sha256_before": source_hashes, "frozen_input_sha256_after": after,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sources}, "measurements": measurements,
        "invariants": ["no facts, prompt text, canonical DTO, runtime validator or budget changed",
            "only v2 C3 uses dynamic query constraints and post-protocol definition aliases",
            "A/I/Deep/C6 wire generation unchanged", "original b response remains rejected; no response rewritten",
            "standard enforces exact query member set with uniqueItems; vllm profile retains local duplicate rejection",
            "no model/DB/service calls or original input writes"],
        "limits": ["frozen five two-member inputs only; not a universal Case capacity guarantee",
            "new c input must pass the same exact request admission before dispatch",
            "provider may violate strict schema; runtime validation and no retry remain mandatory",
            "DeepSeek uses existing full-object anyOf branches and existing protocol inlining; new combination not live-tested"]}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "rows": len(measurements),
        "minimum_margin": min(m["remaining_margin"] for m in measurements),
        "measurements": [{k: m[k] for k in ("input", "protocol", "offered_bindings", "dynamic_aliased_wire_bytes", "remaining_margin")}
            for m in measurements]}))


if __name__ == "__main__":
    main()
