"""One corrected schema-only request; independent of the closed m3 batch."""
import json
import sys
from copy import deepcopy
from types import SimpleNamespace

import evaluate_socai2_models_20261104 as base

M3 = base.ROOT / "docs/operations/evidence/socai2-schema-probe-20261104/m3"
base.OUT = base.ROOT / "docs/operations/evidence/socai2-schema-probe-20261104/m4"
base.REMOTE = "/opt/sting-aisoc-socai2/evidence/next-schema-probe-20261104-m4"
base.RUNNER = base.OUT / "runner.py"


def prepare():
    import jsonschema
    from app.socai2.model_protocol import DEEPSEEK_PROTOCOL, prepare_request

    old = json.loads((M3 / "plan-and-packets.json").read_text("utf-8"))
    before = old["cells"][0]["body"]
    fmt = before["text"]["format"]
    canonical = {"model": before["model"], "messages": before["input"], "temperature": before["temperature"],
        "max_tokens": before["max_output_tokens"], "response_format": {"type": "json_schema",
            "json_schema": {k: v for k, v in fmt.items() if k != "type"}}}
    body = prepare_request(SimpleNamespace(provider=DEEPSEEK_PROTOCOL, schema_profile="standard"), canonical)
    expected = deepcopy(before)
    schema = expected["text"]["format"]["schema"]
    schema["properties"]["decision_basis"]["anyOf"][0] = deepcopy(schema["$defs"]["DecisionBasis"])
    assert body == expected
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(json.loads(body["input"][1]["content"]), schema)
    assert body["max_output_tokens"] == 512 and len(base.encode(body)) < 4096
    files = ["services/api/app/socai2/model_protocol.py", "services/api/app/socai2/model_errors.py"]
    bundle = {"batch": "m4-schema-only-corrected", "plan": {"max_calls": 1, "retries": 0,
        "business_materials": False, "model": "deepseek-flash", "max_output_tokens_each": 512,
        "purpose": "verify corrected typed anyOf branch, no investigation-quality claim"},
        "cells": [{"id": "typed-anyof", "backend": "deepseek", "body": body, "body_sha256": base.sha(base.encode(body))}],
        "error_helper": old["error_helper"], "packets": [], "source_m3_packet_sha256": base.sha((M3 / "plan-and-packets.json").read_bytes()),
        "code_hashes": {p: base.sha((base.ROOT / p).read_bytes()) for p in files}}
    source = (M3 / "runner.py").read_text("utf-8")
    for previous, current in [('len(bundle["cells"]) == 2', 'len(bundle["cells"]) == 1'),
            ('"max_calls": 2', '"max_calls": 1'), ('"cells": 2', '"cells": 1')]:
        assert source.count(previous) == 1
        source = source.replace(previous, current)
    compile(source, "frozen-m4-runner", "exec")
    base.OUT.mkdir(parents=True, exist_ok=False)
    base.RUNNER.write_text(source, encoding="utf-8")
    base.write(base.OUT / "plan-and-packets.json", bundle)
    base.write(base.OUT / "preparation.json", {"packet_sha256": base.sha((base.OUT / "plan-and-packets.json").read_bytes()),
        "runner_sha256": base.sha(base.RUNNER.read_bytes()), "max_calls": 1, "no_business_materials": True,
        "only_schema_branch_changed_from_m3": True, "body_bytes": len(base.encode(body))})
    print(json.dumps({"prepared": str(base.OUT), "max_calls": 1, "no_business_materials": True}))


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    else:
        base.main()
