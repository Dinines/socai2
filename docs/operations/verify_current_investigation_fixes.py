"""Offline audit-fix checks and frozen-budget diagnostics. No remote/model calls."""
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/api/tests")]


async def replay():
    from app.socai2 import baseline_delivery_contract as contract
    from app.socai2.baseline_context import Context
    from app.socai2.baseline_reasoning import fit_final_request
    from app.socai2.baseline_store import encoded
    from app.socai2.model_protocol import prepare_request
    from app.socai2.structured_output import response_format
    from diagnose_socai2_kafka_inputs_20261105 import DIRECTORY, one
    path = max(DIRECTORY.glob("database-*.json"))
    db = json.loads(path.read_text("utf-8"))
    results = []
    for run in db["runs"]:
        if run["stop_reason"] != "required_model_input_unavailable":
            continue
        r = await one(db, run)
        p = r["prepared"]
        context = Context.model_validate(next(a["content_json"] for a in db["artifacts"]
            if a["run_id"] == run["id"] and a["schema_version"] == "socai2.baseline-context.v1"))
        body = prepare_request(SimpleNamespace(provider="deepseek_responses", schema_profile="standard"), {
            "model": "deepseek-flash", "messages": p["messages"], "max_tokens": 3000, "temperature": 0,
            "response_format": response_format(contract.Delivery, p["source_map"], members=context.alerts,
                questions=[q.id for q in context.questions], objects=context.scope.object_keys)})
        used = sum(s["usage"]["total_tokens"] for s in db["run_steps"] if s["run_id"] == run["id"] and s["kind"] == "model")
        allowance = 24000 - used - 3000 - 256
        fit_final_request(body, p, allowance)
        results.append({"run_id": run["id"], "ready": p["ready"], "view_bytes": p["bytes"],
            "required_count": r["required_count"], "required_omitted": [v for v in r["required"] if v["omitted"]],
            "complete_request_bytes": len(encoded(body)), "previous_reported_tokens": used,
            "remaining_request_byte_allowance": allowance,
            "dispatch_allowed_by_remaining_budget": len(encoded(body)) <= allowance,
            "omitted_reference_count": len(p["omissions"]), "model_calls": 0})
    return {"source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "cases": results}


def main():
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    out = ROOT / "docs/operations/evidence/current-investigation-audit-20261105" / ("fix-validation-" + stamp)
    out.mkdir(exist_ok=False)
    paths = [*sorted((ROOT / "services/api/app/socai2").glob("*.py")),
        ROOT / "services/api/migrations/125_socai2_baseline_input_freshness.sql",
        ROOT / "services/api/tests/test_socai2_audit_fixes.py"]
    fingerprints = lambda: {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    before = fingerprints()
    names = ["audit_fixes", "model_errors", "traffic_projection", "model_protocol", "structured_output", "followup_budget"]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": os.pathsep.join(str(ROOT / p) for p in ("services/api", "services/api/tests", "docs/operations"))}
    result = subprocess.run([sys.executable, "-m", "pytest",
        *[f"services/api/tests/test_socai2_{name}.py" for name in names], "-q"],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", check=False)
    (out / "pytest.txt").write_text(result.stdout + result.stderr, "utf-8")
    diagnostic = asyncio.run(replay())
    assert fingerprints() == before, "source changed during verification"
    report = {"generated_at": stamp, "offline_only": True, "pytest_exit_code": result.returncode,
        "source_sha256": before, "c6": diagnostic, "new_model_calls": 0,
        "known_limit": "frozen_prior_usage_leaves_insufficient_C6_budget_no_business_result_rewritten"}
    (out / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"evidence": str(out), "pytest": result.stdout.strip().splitlines()[-1], "c6": diagnostic["cases"]}, ensure_ascii=False))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
