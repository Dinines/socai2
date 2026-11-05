"""Two public-contract probes, no event/Case material or business writes."""
import json
import sys
from copy import deepcopy

import evaluate_socai2_models_20261104 as base

base.OUT = base.ROOT / "docs/operations/evidence/socai2-schema-probe-20261104/m3"
base.REMOTE = "/opt/sting-aisoc-socai2/evidence/next-schema-probe-20261104-m3"
ORIGINAL_RUNNER = base.RUNNER
base.RUNNER = base.OUT / "runner.py"


def packets():
    import jsonschema
    from app.socai2.alert_basic_contract import Answer
    from app.socai2.structured_output import response_format

    schema = response_format(Answer, ["N1_S1"])["json_schema"]["schema"]
    alternative = deepcopy(schema)
    union = alternative["properties"]["decision_basis"]
    assert union == {"anyOf": [{"$ref": "#/$defs/DecisionBasis"}, {"type": "null"}]}
    union.clear()
    union.update(deepcopy(alternative["$defs"]["DecisionBasis"]))
    union["type"] = ["object", "null"]
    answer = {"verdict": "needs_review", "confidence": None, "rationale": "Schema probe only.",
        "explanation": "No event data supplied.", "evidence_ids": ["N1_S1"], "recommendations": [],
        "limitations": ["Not an investigation."], "decision_basis": None}
    examples = [answer, {**answer, "decision_basis": {"kind": "malicious_behavior", "claim": "Schema test.", "source_ids": ["N1_S1"]}},
        {**answer, "decision_basis": {}}, {**answer, "decision_basis": {"kind": "invalid"}},
        {**answer, "decision_basis": "not an object"}]
    for example in examples:
        validators = [jsonschema.Draft202012Validator(s) for s in (schema, alternative)]
        assert validators[0].is_valid(example) == validators[1].is_valid(example)
    cells = []
    for name, variant in (("canonical", schema), ("nullable-object-type", alternative)):
        jsonschema.Draft202012Validator.check_schema(variant)
        body = {"model": "deepseek-flash", "input": [
            {"role": "system", "content": "Return exactly the JSON supplied by the user. This is an output schema compatibility probe, not an investigation."},
            {"role": "user", "content": json.dumps(answer, separators=(",", ":"))}],
            "text": {"format": {"type": "json_schema", "name": "socai2_answer", "strict": True, "schema": variant}},
            "max_output_tokens": 512, "temperature": 0, "reasoning": {"effort": "none"}, "stream": False, "store": False}
        cells.append({"id": name, "backend": "deepseek", "body": body, "body_sha256": base.sha(base.encode(body))})
    return {"batch": "m3-schema-only", "plan": {"max_calls": 2, "retries": 0, "business_materials": False,
        "model": "deepseek-flash", "max_output_tokens_each": 512, "business_writes": 0,
        "purpose": "diagnose structured-output compatibility; no quality verdict"}, "cells": cells,
        "error_helper": (base.ROOT / "services/api/app/socai2/model_errors.py").read_text("utf-8"),
        "schema_examples_equivalent": len(examples), "packets": [],
        "code_hashes": {"services/api/app/socai2/model_errors.py": base.sha((base.ROOT / "services/api/app/socai2/model_errors.py").read_bytes())}}


def prepare():
    base.OUT.mkdir(parents=True, exist_ok=False)
    bundle = packets()
    source = ORIGINAL_RUNNER.read_text("utf-8")
    substitutions = {
        'len(bundle["cells"]) == 12': 'len(bundle["cells"]) == 2',
        '"max_calls": 12': '"max_calls": 2', '"cells": 12': '"cells": 2',
        'for backend in ("small", "deepseek")': 'for backend in ("deepseek",)',
        '"model": "aisoc-investigation" if backend == "small" else "deepseek-flash"}':
            '"model": "aisoc-investigation" if backend == "small" else "deepseek-flash", "error_helper": json.loads((HERE / "plan-and-packets.json").read_text())["error_helper"]}',
        "x=json.load(sys.stdin)": "x=json.load(sys.stdin)\nerror_ns={}\nexec(x['error_helper'],error_ns)",
        "result={'state':'failed_or_unknown_no_retry','error_type':type(exc).__name__}":
            "result={'state':'failed_or_unknown_no_retry','error_type':type(exc).__name__,'transport_error':error_ns['provider_error'](exc,key)}",
    }
    for before, after in substitutions.items():
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    compile(source, "schema-probe-runner", "exec")
    base.RUNNER.write_text(source, encoding="utf-8")
    base.write(base.OUT / "plan-and-packets.json", bundle)
    base.write(base.OUT / "preparation.json", {"packet_sha256": base.sha((base.OUT / "plan-and-packets.json").read_bytes()),
        "runner_sha256": base.sha(base.RUNNER.read_bytes()), "max_calls": 2,
        "no_business_materials": True, "schema_examples_equivalent": bundle["schema_examples_equivalent"]})
    print(json.dumps({"prepared": str(base.OUT), "max_calls": 2, "no_business_materials": True}))


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    else:
        base.main()
