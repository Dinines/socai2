"""Direct offline checks for one-shot POST and per-request saved model export."""

import importlib.util
import io
import json
import tempfile
from pathlib import Path
from uuid import uuid4

E = Path(__file__).resolve().parent
R = E.parents[3]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, E / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    http = module("fullflow_http", "http-action.py")
    exporter = module("fullflow_export", "export-models.py")
    checks = []
    calls = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "out").mkdir()
        (root / "profile.json").write_text(
            json.dumps(
                {"http_base": "http://unused.invalid", "timeouts": {"http_seconds": 1}}
            )
        )
        request = {
            "method": "POST",
            "path": "/api/v1/socai2/cases",
            "body": {
                "operation_key": str(uuid4()),
                "title": "主机活动关联调查",
                "alert_ids": [str(uuid4())],
            },
        }

        def unknown(*args, **kwargs):
            calls.append((args, kwargs))
            raise TimeoutError("controlled offline transport")

        result = http.execute(root, "create-whole", request, unknown)
        assert result["outcome"] == "unknown" and len(calls) == 1
        assert (root / "out/intent-create-whole.json").exists()
        checks.append("POST_intent_and_unknown_preserved_before_return")
        try:
            http.execute(root, "create-whole", request, unknown)
        except (AssertionError, FileExistsError):
            checks.append("same_phase_unknown_cannot_repeat_POST")
        else:
            raise AssertionError("unknown POST repeated")
        assert len(calls) == 1
        source = (
            R
            / "docs/operations/evidence/ai-case-chain-d4c-20261116-01/real-01/database.json"
        )
        original = source.read_bytes()
        report = exporter.export(
            source, root / "model-export", ["tenant_uid", "fixture"]
        )
        assert report["request_count"] == report["received_original_count"] == 9
        assert report["usage_unknown_requests"] == 0 and source.read_bytes() == original
        for row in report["requests"]:
            assert not row["input_observations"]
            folder = next(
                p.parent
                for p in (root / "model-export").rglob("request.json")
                if row["request_artifact_id"] in p.parent.name
            )
            saved = json.loads((folder / "original-artifact.json").read_text())
            assert (folder / "output.txt").read_text() == saved["content_json"]["raw"][
                "choices"
            ][0]["message"]["content"]
        checks.append("nine_historical_requests_keep_distinct_originals_and_exact_text")
        # Make an explicitly controlled same-step variant from saved D3 requests.
        d3 = (
            R
            / "docs/operations/evidence/c3-unit-continuation-d3-20261116-01/pg-http-01/database.json"
        )
        if d3.exists():
            saved_bytes = d3.read_bytes()
            variant = json.loads(saved_bytes)
            rows = variant.get("rows", variant)
            requests = [a for a in rows["artifacts"] if a["kind"] == "model_request"]
            assert len(requests) >= 2
            first_step = requests[0]["step_id"]
            requests[1]["step_id"] = first_step
            for artifact in rows["artifacts"]:
                content = artifact.get("content_json") or {}
                if content.get("request_artifact_id") == requests[1]["id"]:
                    artifact["step_id"] = first_step
            variant_path = root / "controlled-same-step.json"
            variant_path.write_text(json.dumps(variant))
            report = exporter.export(variant_path, root / "supplement-export", [])
            counts = {}
            for row in report["requests"]:
                counts[row["step_id"]] = counts.get(row["step_id"], 0) + 1
            assert max(counts.values()) >= 2
            assert report["request_count"] == report["received_original_count"]
            assert d3.read_bytes() == saved_bytes
            checks.append("controlled_same_step_requests_not_overwritten")
        else:
            raise AssertionError("required saved supplement fixture missing")

        class Response(io.StringIO):
            status = 201

        reply = http.execute(
            root,
            "create-single",
            {**request, "body": {**request["body"], "operation_key": str(uuid4())}},
            lambda *a, **kw: Response(json.dumps({"primary_case_id": str(uuid4())})),
        )
        assert reply["response"]["status"] == 201
        checks.append("formal_create_contract_needs_no_old_quality_gate")
    result = {
        "status": "passed_offline",
        "checks": checks,
        "transport": "controlled in-memory only",
        "fixture": "historical saved D4c/D3 evidence; not new batch execution",
        "new_HTTP_requests": 0,
        "new_model_calls": 0,
        "new_database_connections": 0,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
