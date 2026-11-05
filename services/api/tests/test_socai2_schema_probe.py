"""m3 is a schema-only experiment; no network or business material in these checks."""
import ast
import io
import json
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
from app.socai2.alert_basic_contract import Answer
from app.socai2.structured_output import response_format
from test_socai2_model_errors import http_error

ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = ROOT / "docs/operations/evidence/socai2-schema-probe-20261104/m3"


def bundle():
    return json.loads((DIRECTORY / "plan-and-packets.json").read_text("utf-8"))


def test_probe_preserves_all_body_fields_except_nullable_schema_representation():
    data = bundle()
    assert data["plan"]["max_calls"] == len(data["cells"]) == 2 and data["plan"]["retries"] == 0
    first, second = [deepcopy(c["body"]) for c in data["cells"]]
    schema = first["text"]["format"]["schema"]
    assert schema == response_format(Answer, ["N1_S1"])["json_schema"]["schema"]
    alternate = second["text"]["format"]["schema"]
    expected = deepcopy(schema["$defs"]["DecisionBasis"])
    expected["type"] = ["object", "null"]
    assert alternate["properties"]["decision_basis"] == expected
    alternate["properties"]["decision_basis"] = deepcopy(schema["properties"]["decision_basis"])
    assert first == second
    assert first["max_output_tokens"] == 512 and first["reasoning"] == {"effort": "none"}
    assert "tools" not in first and first["model"] == "deepseek-flash"
    assert set(json.loads(first["input"][1]["content"])["evidence_ids"]) == {"N1_S1"}


def test_probe_object_null_and_invalid_shapes_have_same_schema_result():
    cells = bundle()["cells"]
    validators = [jsonschema.Draft202012Validator(c["body"]["text"]["format"]["schema"]) for c in cells]
    answer = json.loads(cells[0]["body"]["input"][1]["content"])
    valid = {"kind": "malicious_behavior", "claim": "Schema-only example.", "source_ids": ["N1_S1"]}
    invalid = [False, 5, [], {}, "none", {**valid, "kind": "invalid"}, {**valid, "source_ids": []},
        {**valid, "source_ids": ["N1_S2"]}, {**valid, "claim": "x" * 4001}, {**valid, "unexpected": True}]
    invalid += [{k: v for k, v in valid.items() if k != omitted} for omitted in valid]
    for basis in [None, valid, *invalid]:
        value = {**answer, "decision_basis": basis}
        actual = [v.is_valid(value) for v in validators]
        assert actual == [basis is None or basis == valid] * 2
    missing = {k: v for k, v in answer.items() if k != "decision_basis"}
    assert not any(v.is_valid(missing) for v in validators)


def test_frozen_child_captures_safe_error_once_using_n9_transport_failure_shape():
    tree = ast.parse((DIRECTORY / "runner.py").read_text("utf-8"))
    child = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "CHILD" for t in n.targets))
    data = bundle()
    key = "synthetic-secret-never-display"
    source = {"phase": "call", "backend": "deepseek", "model": "deepseek-flash", "env": {},
        "body": data["cells"][0]["body"], "error_helper": data["error_helper"]}
    call = AsyncMock(side_effect=http_error({"error": {"code": "invalid_schema", "param": "text.format.schema",
        "message": "Schema-only diagnostic " + key}}))
    output = io.StringIO()
    with patch("sys.stdin", io.StringIO(json.dumps(source))), patch.dict("os.environ"), \
            patch("app.services.model_aliases.resolve_base_url", return_value="https://api.deepseek.com"), \
            patch("app.services.model_aliases.resolve_api_key", return_value=key), \
            patch("app.socai2.baseline_analysis_model.TenantChatGateway.complete", call), redirect_stdout(output):
        exec(compile(child, "frozen-m3-child", "exec"), {})  # noqa: S102 -- frozen repository runner, mocked transport
    result = json.loads(output.getvalue())
    assert call.await_count == 1 and key not in output.getvalue()
    assert result["state"] == "failed_or_unknown_no_retry" and result["http_status"] == 400
    assert result["transport_error"]["fields"]["param"] == "text.format.schema"
    assert result["transport_error"]["redacted_fields"] == ["message"]
