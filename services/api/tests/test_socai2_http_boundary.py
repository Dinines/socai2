"""Direct boundary checks: external routes, legacy imports, independent core."""

import ast
import asyncio
import copy
import importlib
import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "services/api"
PACKAGE = API / "investigation_http"


def imports(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            yield from (item.name for item in node.names)


def test_external_routes_have_no_internal_implementation_imports(caplog):
    forbidden = ("app", "sqlalchemy", "httpx", "aiohttp", "requests")
    for path in (PACKAGE / "external_routes").glob("*.py"):
        assert not [m for m in imports(path) if m.split(".")[0] in forbidden], path.name
    # Reusing core DTOs is allowed only through the explicit contracts boundary;
    # concrete implementations and runtime wiring are restricted to adapters.
    for path in PACKAGE.rglob("*.py"):
        if "adapters" in path.parts or path.name == "contracts.py":
            continue
        assert not [m for m in imports(path) if m.startswith("app.")], path.name
    for path in (API / "app/socai2").glob("*.py"):
        assert not [
            m for m in imports(path) if m.startswith(("investigation_http", "app.api."))
        ], path.name

    # The logging adapter must preserve the real error record and transport
    # contract; neither bypassing this boundary nor dropping logs is a fix.
    from fastapi import HTTPException
    from investigation_http.contracts import StoreError
    from investigation_http.errors import invoke, invoke_record, provide

    def unavailable(code, status):
        raise StoreError(code, status)

    async def async_unavailable(code, status):
        return unavailable(code, status)

    calls = (
        (lambda code, status: provide(unavailable, code, status), False),
        (lambda code, status: asyncio.run(invoke(async_unavailable(code, status))), False),
        (lambda code, status: asyncio.run(invoke_record(async_unavailable(code, status))), True),
    )
    for call, structured in calls:
        for code, status, message in (("service_unavailable", 503, "调查记录读取服务不可用"),
                                      ("run_not_found", 404, "调查记录不存在")):
            caplog.clear()
            with (
                caplog.at_level(logging.ERROR, logger="investigation_http.errors"),
                pytest.raises(HTTPException) as caught,
            ):
                call(code, status)
            assert caught.value.status_code == status
            assert caught.value.detail == (
                {"code": code, "message": message, "context": {}} if structured else code)
            records = [record for record in caplog.records if record.name == "investigation_http.errors"]
            if status < 500:
                assert not records
                continue
            assert len(records) == 1
            record = records[0]
            assert record.levelno == logging.ERROR
            assert record.getMessage() == "http_use_case_failed"
            assert (record.operation, record.stage, record.error_code, record.http_status) == (
                "http_use_case", "http", code, status)
            assert record.exception_type == "StoreError" and record.exc_info is None
            assert record.traceback[0]["exception_type"] == "StoreError"
            assert any(frame["function"] == "unavailable" for frame in record.traceback[0]["frames"])


def normalize_documented_contract_deltas(before, normalized, after):
    """Assert the enumerated published/approved increments, then compare the rest."""
    schemas = normalized["components"]["schemas"]
    original = before["components"]["schemas"]
    current = after["components"]["schemas"]
    uuid = {"type": "string", "format": "uuid"}
    stamp = {"type": "string", "format": "date-time"}
    strings = {"type": "array", "items": {"type": "string"}}

    def nullable(value):
        return {"anyOf": [value, {"type": "null"}]}

    def field(name, shape, description=None):
        value = {**shape, "title": name.replace("_", " ").title()}
        if description is not None:
            value["description"] = description
        return value

    def closed(name, properties, required=None):
        expected = {"type": "object", "additionalProperties": False,
                    "title": name, "properties": properties,
                    "required": list(properties) if required is None else required}
        assert schemas.pop(name) == expected

    # The committed people endpoint and both closed response records.
    people = normalized["paths"].pop("/api/v1/socai2/people")
    assert set(people) == {"get"}
    assert people["get"]["parameters"] == [
        {"name": "q", "in": "query", "required": False,
         "schema": field("q", nullable({"type": "string", "maxLength": 200}))},
        {"name": "user_id", "in": "query", "required": False,
         "schema": field("user_id", nullable(uuid))},
        {"name": "offset", "in": "query", "required": False,
         "schema": field("offset", {"type": "integer", "minimum": 0, "maximum": 100000, "default": 0})},
        {"name": "limit", "in": "query", "required": False,
         "schema": field("limit", {"type": "integer", "minimum": 1, "maximum": 200, "default": 50})},
    ]
    assert people["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/OwnerDirectoryPage"}
    closed("OwnerOption", {"id": field("id", uuid), "username": field("username", {"type": "string"}),
                           "display_name": field("display_name", {"type": "string"})})
    closed("OwnerDirectoryPage", {
        "items": field("items", {"type": "array", "items": {"$ref": "#/components/schemas/OwnerOption"}}),
        "total": field("total", {"type": "integer"}), "offset": field("offset", {"type": "integer"}),
        "limit": field("limit", {"type": "integer"}),
        "next_offset": field("next_offset", nullable({"type": "integer"})),
        "observed_at": field("observed_at", stamp),
    })

    # These alert request classes and their bases are identical to committed
    # main. Batch tags are excluded; the other request fields remain exact.
    selected = schemas.pop("SelectedAlert")
    assert selected["properties"]["expected_row_version"]["description"] == (
        "兼容保留的告警行版本；旧版本不拒绝，按最新行应用本次明确修改。")
    selected["properties"]["expected_row_version"]["description"] = (
        original["SelectedSubject"]["properties"]["expected_row_version"]["description"])
    selected["title"] = "SelectedSubject"
    assert selected == original["SelectedSubject"]
    batch_fields = copy.deepcopy(original["AlertManagementFields"])
    batch_fields["title"] = "AlertBatchManagementFields"
    batch_fields["properties"].pop("tags")
    assert schemas.pop("AlertBatchManagementFields") == batch_fields
    # The single-record fields are flattened into AlertManagementUpdate;
    # reconstruct the old component from that actual schema, not the baseline.
    single_fields = copy.deepcopy(schemas["AlertManagementUpdate"])
    single_fields["title"] = "AlertManagementFields"
    assert set(single_fields.pop("required")) == {"operation_key", "expected_row_version"}
    for name in ("operation_key", "expected_row_version"):
        single_fields["properties"].pop(name)
    assert single_fields == original["AlertManagementFields"]
    schemas["AlertManagementFields"] = single_fields
    for name in ("AlertFeedback", "AlertManagementUpdate"):
        prop = schemas[name]["properties"]["expected_row_version"]
        assert prop["description"] == (
            "兼容保留的页面行版本；告警锁定最新行后仅应用明确修改字段，旧版本不拒绝，以最后成功保存为准。")
        prop["description"] = original[name]["properties"]["expected_row_version"]["description"]
    for name in ("AlertFeedbackBatch", "AlertManagementBatch"):
        prop = schemas[name]["properties"]["items"]
        assert prop["description"] == (
            "仅明确勾选的告警ID；不允许重复，整批保存或拒绝。旧版本不拒绝，未提交字段保持最新值。")
        assert prop["items"] == {"$ref": "#/components/schemas/SelectedAlert"}
        prop["description"] = original[name]["properties"]["items"]["description"]
        prop["items"] = {"$ref": "#/components/schemas/SelectedSubject"}
    changes = schemas["AlertManagementBatch"]["properties"]["changes"]
    assert changes == {"$ref": "#/components/schemas/AlertBatchManagementFields",
                       "description": "应用于所选告警的局部修改；不接受tags，标签仅支持单条修改。"}
    changes["$ref"] = "#/components/schemas/AlertManagementFields"
    changes["description"] = original["AlertManagementBatch"]["properties"]["changes"]["description"]

    # S5 task timing/active-step contracts are committed and intentionally
    # separate from execution outcome. Their parent bindings stay explicit.
    assert current["AnalysisAttemptView"]["properties"]["timing"]["$ref"] == (
        "#/components/schemas/AnalysisAttemptTiming")
    assert current["AnalysisTaskDetail"]["properties"]["timing"]["$ref"] == (
        "#/components/schemas/AnalysisTaskTiming")
    assert current["AnalysisTaskDetail"]["properties"]["active_step"]["anyOf"] == [
        {"$ref": "#/components/schemas/AnalysisActiveStep"}, {"type": "null"}]
    closed("AnalysisAttemptTiming", {
        "queue_seconds": field("queue_seconds", nullable({"type": "number"}),
                               "本次开始减本次首次确认入队；入队未记录或负差为null。"),
        "execution_seconds": field("execution_seconds", nullable({"type": "number"}),
                                   "本次开始至本地结束；本地仍运行则至observed_at，中断未知本地结束为null。"),
        "anomalies": field("anomalies", strings, "时间异常字段码，如queue_seconds_negative；没有为[]。"),
    })
    closed("AnalysisTaskTiming", {
        "total_seconds": field("total_seconds", nullable({"type": "number"}),
                               "原受理至本地任务终态或observed_at的总历时，包含等待。"),
        "pending_queue_seconds": field("pending_queue_seconds", nullable({"type": "number"}),
            "当前待执行尝试首次确认入队至observed_at；未排队、旧时点缺失或历史共享任务为null。"),
        "retry_wait_seconds": field("retry_wait_seconds", nullable({"type": "number"}),
            "当前已安排重试自上次本地结束至observed_at；包含其中排队区间，不可与排队耗时相加。"),
        "anomalies": field("anomalies", strings, "负时差字段码；对应耗时为null，没有为[]。"),
    })
    closed("AnalysisActiveStep", {
        "run_id": field("run_id", uuid, "当前本地执行尝试实际绑定的running Run。"),
        "step_id": field("step_id", uuid, "该Run中真实已开始且未结束的running步骤；最新开始、同刻最大seq优先。"),
        "name": field("name", {"type": "string"}, "保存的步骤名称。"),
        "started_at": field("started_at", stamp, "该步骤实际开始时间。"),
        "elapsed_seconds": field("elapsed_seconds", nullable({"type": "number"}),
                                 "步骤开始至同响应observed_at；负差为null并记录异常。"),
        "anomalies": field("anomalies", strings, "步骤时间异常码；没有为[]。"),
        "url": field("url", {"type": "string"}, "该实际步骤的已有HTTP详情地址。"),
    })

    # SF04/SF06 saved Result/diagnosis verdicts and frozen adoption sources.
    verdict_type = nullable({"type": "string", "enum": ["malicious", "benign", "false_positive", "needs_review"]})
    for name, description in (
        ("DiagnosisView", "Saved model verdict for this diagnosis. Null if absent."),
        ("ResultSummary", "Saved model verdict of this Result, or null."),
        ("ResultView", "Saved model verdict of this Result, or null."),
        ("AssessmentPageView", "Model verdict of the uniquely adopted Result, or null."),
    ):
        assert schemas[name]["properties"].pop("business_verdict") == field(
            "business_verdict", verdict_type, description)
        assert "business_verdict" not in schemas[name]["required"]
    closed("AssessmentSourceReference", {
        "result_id": field("result_id", nullable(uuid)),
        "task_revision_id": field("task_revision_id", nullable(uuid)),
        "artifact_id": field("artifact_id", nullable(uuid)),
        "task_id": field("task_id", nullable(uuid),
                         "Task owning the frozen task_revision_id; null for other source types."),
        "run_id": field("run_id", nullable(uuid),
                        "Run owning artifact_id; null for a Case-level artifact or another source type."),
    }, required=["result_id", "task_revision_id", "artifact_id"])
    assert schemas["CaseDetail"]["properties"]["current_assessment"].pop("description") == (
        "Saved adoption with sources and business_verdict from its unique accepted model Result, or null. "
        "Each source preserves result_id/task_revision_id/artifact_id and adds task_id for the frozen human "
        "revision and run_id for a Run-level artifact; never resolves through the current task version.")

    # Approved Case list and Incident detail migrations in this same change.
    queue = schemas["CaseQueueItem"]
    assert queue["properties"].pop("active_member_count") == field(
        "active_member_count", {"type": "integer", "minimum": 0},
        "正式成员中当前状态为 new 或 in_progress 的告警数。")
    queue["required"].remove("active_member_count")
    assert after["paths"]["/api/v1/socai2/incidents/{incident_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/IncidentDetailView"}
    detail = copy.deepcopy(current["IncidentSubjectView"])
    detail["title"] = "IncidentDetailView"
    for name, target in (("published_diagnosis", "PublishedIncidentDiagnosis"),
                         ("latest_attempt", "IncidentDiagnosisAttempt")):
        detail["properties"][name] = nullable({"$ref": "#/components/schemas/" + target})
        detail["required"].append(name)
    assert schemas.pop("IncidentDetailView") == detail
    closed("PublishedIncidentDiagnosis", {
        "id": field("id", uuid), "source_run_id": field("source_run_id", uuid),
        "summary": field("summary", nullable({"type": "string"})),
        "conclusion": field("conclusion", nullable({"type": "string"})),
        "open_questions": field("open_questions", strings),
    })
    closed("IncidentDiagnosisAttempt", {
        "run_id": field("run_id", uuid), "state": {"$ref": "#/components/schemas/RunState"},
        "delivery_state": {"$ref": "#/components/schemas/Delivery"},
        "stop_reason": field("stop_reason", nullable({"type": "string"})),
    })


def test_external_contract_preserves_compatibility_except_approved_list_delta():
    from app import socai2_main
    from investigation_http.contracts import IncidentSubjectView
    from investigation_http.main import app

    before = json.loads(
        (
            ROOT
            / "docs/operations/evidence/http-boundary-20261113-01/before-openapi.json"
        ).read_text()
    )
    after = app.openapi()
    normalized = copy.deepcopy(after)
    # 3f adds two scoped lake read operations; existing contracts remain exact.
    for path in ("/api/v1/socai2/lake/events/search", "/api/v1/socai2/lake/events/{event_id}/material"):
        normalized["paths"].pop(path)
    for name in list(normalized["components"]["schemas"]):
        if name.startswith("Lake"):
            normalized["components"]["schemas"].pop(name)
    # Confirmed Case allocation delta: four writes replace their old single-case
    # receipts; only relationship GET and event detail gain the new read fields.
    allocation_schemas = normalized["components"]["schemas"]
    # S1 adds only Incident/Case persisted risk; alert facts/derived stay exact.
    for name in ("CaseView", "IncidentFacts"):
        field = allocation_schemas[name]["properties"].pop("risk")
        assert field["anyOf"] == [{"$ref": "#/components/schemas/SubjectRisk"}, {"type": "null"}]
        assert "risk" not in allocation_schemas[name]["required"]
    for name in ("SubjectRisk", "RiskPolicy", "RiskPriorityMap", "RiskInitial", "RiskMember", "RiskCurrent",
                 "RiskSystemPriority", "RiskOpinionLink", "RiskPriorityOverride"):
        allocation_schemas.pop(name)
    derived = allocation_schemas.pop("IncidentDerivedFields")
    assert derived["properties"]["severity_source"]["anyOf"][0]["enum"] == ["manual_override", "member_max", "model", "initial_policy", "unknown"]
    # S3 adds reasoned subject risk edits; Alert requests and all other properties remain exact.
    for name in ("CaseManagementUpdate", "IncidentManagementFields", "IncidentManagementUpdate"):
        props = allocation_schemas[name]["properties"]
        for field in ("priority_value", "priority_reason", "clear_priority_override"):
            assert field in props
            props.pop(field)
        if name == "CaseManagementUpdate":
            assert "anyOf" not in props["severity"] and "default" not in props["severity"]
            props.pop("severity_reason")
            props["severity"] = copy.deepcopy(before["components"]["schemas"][name]["properties"]["severity"])
        else:
            for field in ("severity_override", "severity_override_reason"):
                props[field]["description"] = before["components"]["schemas"][name]["properties"][field]["description"]
    allocation_schemas["IncidentSubjectView"]["properties"]["derived"] = {"$ref": "#/components/schemas/DerivedFields"}
    allocation_schemas.pop("IncidentSubjectPage")
    normalized["paths"]["/api/v1/socai2/incidents"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] = {"$ref": "#/components/schemas/SubjectPage"}
    # Stage7 adds a frozen comparison only to Case views; A/I task and stage
    # schemas still participate in the exact comparison below.
    comparison = allocation_schemas.pop("CaseComparison")
    assert set(comparison["properties"]) == {
        "previous_run_id", "comparison_result_id", "state", "reason_code"}
    assert comparison["properties"]["state"]["enum"] == ["initial", "eligible", "unavailable"]
    for name in ("RunView", "ResultSummary", "ResultView"):
        model = allocation_schemas[name]
        context = model["properties"].pop("comparison_context")
        assert context["anyOf"] == [{"$ref": "#/components/schemas/CaseComparison"}, {"type": "null"}]
        assert context.get("default") is None and "comparison_context" not in model["required"]
    for path, method, model, status in (
        ("/api/v1/socai2/cases", "post", "CaseAllocationReceipt", "201"),
        ("/api/v1/socai2/cases/{case_id}/associations", "post", "CaseAllocationReceipt", "200"),
        ("/api/v1/socai2/cases/{case_id}/members", "put", "CaseReplacementReceipt", "200"),
        ("/api/v1/socai2/cases/{case_id}/members/move", "post", "CaseMoveReceipt", "200"),
    ):
        operation = normalized["paths"][path][method]
        assert operation["responses"][status]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/" + model}
        assert operation["requestBody"] == before["paths"][path][method]["requestBody"]
        assert {"404", "409", "422", "503"} <= set(operation["responses"])
        normalized["paths"][path][method] = copy.deepcopy(before["paths"][path][method])
    assert "pending_run_id" not in allocation_schemas["CaseAllocationReceipt"]["properties"]
    assert "excluded_alert_ids" in allocation_schemas["CaseAllocationReceipt"]["properties"]
    related = normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/related-cases")
    assert set(related) == {"get"}
    assert {p["name"] for p in related["get"]["parameters"]} == {"case_id", "limit", "cursor"}
    continuation = allocation_schemas["CaseView"]["properties"].pop("continuation")
    assert continuation["anyOf"] == [{"$ref": "#/components/schemas/CaseContinuation"}, {"type": "null"}]
    assert "continuation" not in allocation_schemas["CaseView"]["required"]
    incident_view = allocation_schemas.pop("IncidentSubjectView")
    assert incident_view["properties"].pop("case_receiving") == {"$ref": "#/components/schemas/CaseReceiving"}
    incident_view["required"].remove("case_receiving")
    # SF04 adds the saved current-diagnosis verdict to Incident views only;
    # assert its exact contract before normalizing the approved increment.
    verdict = incident_view["properties"].pop("business_verdict")
    assert verdict == {
        "anyOf": [{"enum": ["malicious", "benign", "false_positive", "needs_review"], "type": "string"},
                  {"type": "null"}],
        "description": "Saved model verdict of facts.latest_diagnosis_id, or null.",
        "title": "Business Verdict",
    }
    assert "business_verdict" not in incident_view["required"]
    assert IncidentSubjectView.model_fields["business_verdict"].default is None
    # The committed ATT&CK display contract documents the existing triage
    # field. Normalize only this exact description, including its inheritance.
    triage_description = (
        "最新已发布的分诊评估。attck_mappings 为同一轮已校验映射，无可用映射时为 null。"
        "新鲜度及采用资格独立返回。")
    for model in (allocation_schemas["SubjectView"], incident_view):
        assert model["properties"]["triage"].pop("description") == triage_description
    for name in ("SubjectView", "AlertFacts"):
        assert "business_verdict" not in allocation_schemas[name]["properties"]
        assert allocation_schemas[name] == before["components"]["schemas"][name]
    for path, model in (("/api/v1/socai2/alerts", "SubjectPage"),
                        ("/api/v1/socai2/alerts/{alert_id}", "SubjectView")):
        assert after["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/" + model}
    incident_view["title"] = "SubjectView"
    assert incident_view == before["components"]["schemas"]["SubjectView"]
    for path in ("/api/v1/socai2/incidents/{incident_id}", "/api/v1/socai2/{subject}/{identity}/records/{section}"):
        normalized["paths"][path]["get"] = copy.deepcopy(before["paths"][path]["get"])
    for name in ("AssociationReceipt", "MutationReceipt", "MoveReceipt"):
        before["components"]["schemas"].pop(name)
    for name in ("CaseAllocationReceipt", "CaseAllocation", "CaseMemberRemoval", "CaseReplacementReceipt",
                 "CaseMoveReceipt", "CaseContinuation", "InitialCaseTaskReceipt", "IncidentReceiver",
                 "RelatedCaseItem", "RelatedCasePage", "SharedIncident", "CaseReceiving"):
        allocation_schemas.pop(name)
    # Confirmed target: alert triage is submitted by normal ingress; the
    # external manual execution path is removed, not kept as a second mode.
    alert_execute = "/api/v1/socai2/alerts/{alert_id}/analyze"
    assert alert_execute not in after["paths"]
    assert set(before["paths"].pop(alert_execute)) == {"post"}
    # Case initial execution belongs to the scheduler. Public callers create a
    # Case and read its task, rather than prepare/start a Run themselves.
    for retired in ("/api/v1/socai2/cases/{case_id}/baseline/prepare",
                    "/api/v1/socai2/cases/{case_id}/runs/{run_id}/start"):
        assert retired not in after["paths"]
        assert set(before["paths"].pop(retired)) == {"post"}
    for name in ("PrepareBaseline", "BaselinePreparation", "Start"):
        assert name not in normalized["components"]["schemas"]
        before["components"]["schemas"].pop(name)
    incident_submit = "/api/v1/socai2/incidents/{incident_id}/diagnose"
    operation = normalized["paths"][incident_submit]["post"]
    assert "202" in operation["responses"] and "200" not in operation["responses"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/AnalysisSubmitRequest"}
    assert operation["responses"]["202"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/AnalysisTaskReceipt"}
    submission = normalized["components"]["schemas"].pop("AnalysisSubmitRequest")
    assert set(submission["required"]) == {"operation_key", "mode"}
    assert submission["additionalProperties"] is False
    assert submission["properties"]["mode"]["enum"] == ["check", "rerun"]
    receipt = normalized["components"]["schemas"].pop("AnalysisTaskReceipt")
    assert set(receipt["properties"]) == {"task_id", "subject_type", "subject_id", "status", "status_url"}
    assert receipt["properties"]["status"]["const"] == "accepted"
    info_summary = normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/info-summary")
    assert set(info_summary) == {"get"}
    assert info_summary["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CaseInfoSummary",
    }
    summary = normalized["components"]["schemas"].pop("CaseInfoSummary")
    assert summary["properties"]["object_preview"]["maxItems"] == 4
    normalized["components"]["schemas"].pop("CaseInfoObject")
    case_submit = normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/investigations")
    assert set(case_submit) == {"post", "get"}
    case_lookup = normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/investigations/{run_id}")
    assert set(case_lookup) == {"get"}
    for endpoint, schema in ((case_submit, "CaseInvestigationPage"), (case_lookup, "CaseInvestigationLookup")):
        assert endpoint["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{schema}"
        }
    for name in ("CaseInvestigationCard", "CaseInvestigationPage", "CaseInvestigationLookup",
                 "CaseInvestigationPreview", "CaseInvestigationUsage"):
        normalized["components"]["schemas"].pop(name)
    assert case_submit["post"]["requestBody"] == operation["requestBody"]
    case_responses, incident_responses = (copy.deepcopy(value["responses"])
        for value in (case_submit["post"], operation))
    for responses in (case_responses, incident_responses):
        responses["422"]["content"]["application/json"]["schema"].pop("title")
    assert case_responses == incident_responses
    normalized["paths"][incident_submit]["post"] = copy.deepcopy(before["paths"][incident_submit]["post"])
    before["components"]["schemas"].pop("ExecuteStage")
    # Only event reads gain the confirmed frozen-selection and coverage fields.
    schemas = normalized["components"]["schemas"]
    incident_entry = schemas.pop("IncidentStageEntry")
    for field, model in (("input_selection", "IncidentInputSelection"),
                         ("analysis_coverage", "IncidentAnalysisCoverage")):
        value = incident_entry["properties"].pop(field)
        assert value["anyOf"] == [{"$ref": "#/components/schemas/" + model}, {"type": "null"}]
        assert value.get("default") is None and field not in incident_entry["required"]
    incident_entry["title"] = "StageEntry"
    assert incident_entry == before["components"]["schemas"]["StageEntry"]
    incident_page = schemas.pop("IncidentStagePage")
    incident_page["title"] = "StagePage"
    incident_page["properties"]["current"]["anyOf"][0]["$ref"] = "#/components/schemas/StageEntry"
    incident_page["properties"]["entries"]["items"]["$ref"] = "#/components/schemas/StageEntry"
    for field in ("current", "entries"):
        # Event-only descriptions explain scope; shared alert schemas stay exact.
        incident_page["properties"][field].pop("description", None)
    assert incident_page == before["components"]["schemas"]["StagePage"]
    assert set(schemas.pop("IncidentInputSelection")["properties"]) == {
        "policy", "limit", "order", "captured_at", "total_member_count", "selected_count",
        "omitted_count", "selected_alert_ids", "input_artifact_id"}
    assert set(schemas.pop("IncidentAnalysisCoverage")["properties"]) == {
        "state", "analyzed_count", "unresolved_count", "not_analyzed_count", "covered_alert_ids", "limitations"}
    for path, model in (("/api/v1/socai2/incidents/{incident_id}/analysis", "StagePage"),
                        ("/api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}", "StageEntry")):
        normalized["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"] = {
            "$ref": "#/components/schemas/" + model}
    for kind in ("alerts", "incidents", "cases"):
        for suffix in ("", "/{task_id}"):
            task_read = normalized["paths"].pop(f"/api/v1/socai2/{kind}/{{subject_id}}/analysis-tasks" + suffix)
            assert set(task_read) == {"get"}
            assert {p["name"] for p in task_read["get"]["parameters"]} == (
                {"subject_id", "task_id"} if suffix else {"subject_id", "limit", "cursor"})
    for name in ("AnalysisAttemptView", "AnalysisTaskDetail", "AnalysisUpdateState", "AnalysisTaskPage"):
        normalized["components"]["schemas"].pop(name)
    directory = normalized["paths"].pop("/api/v1/socai2/analysis-runs")
    assert set(directory) == {"get"}
    assert {p["name"] for p in directory["get"]["parameters"]} == {
        "subject_type", "subject_id", "run_kind", "intent", "state", "time_from", "time_to", "limit", "cursor"}
    for name in ("DirectoryResultRef", "RunDirectoryItem", "RunDirectoryStatistics", "RunDirectoryPage"):
        normalized["components"]["schemas"].pop(name)
    # Confirmed lifecycle semantics: actual active work blocks closing, including
    # attempts preparing before a Run exists; a locally ended unknown does not.
    for model, field in (("CaseBlockingRun", "state"), ("CaseManagementView", "blocking_runs"),
                         ("CaseManagementView", "can_close")):
        current = normalized["components"]["schemas"][model]["properties"][field]
        original = before["components"]["schemas"][model]["properties"][field]
        assert {k: v for k, v in current.items() if k != "description"} == {
            k: v for k, v in original.items() if k != "description"}
        current["description"] = original["description"]
    # Approved complete-record reads are an additive target-version contract.
    for suffix in ("steps", "steps/{step_id}", "artifacts"):
        assert set(normalized["paths"].pop("/api/v1/socai2/analysis-runs/{run_id}/" + suffix)) == {"get"}
    for name in ("RunDetailWithDirectories", "ResultDetailWithComparison"):
        model = normalized["components"]["schemas"][name]
        for field in ("previous_run_url", "comparison_result_url"):
            link = model["properties"].pop(field)
            assert link["anyOf"] == [{"type": "string"}, {"type": "null"}]
            model["required"].remove(field)
    result = normalized["components"]["schemas"].pop("ResultDetailWithComparison")
    result["title"] = "ResultDetail"
    assert result == before["components"]["schemas"]["ResultDetail"]
    normalized["components"]["schemas"]["ResultDetail"] = result
    normalized["paths"]["/api/v1/socai2/cases/{case_id}/results/{result_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] = {
        "$ref": "#/components/schemas/ResultDetail"}
    for path, extended, original in (
        ("/api/v1/socai2/cases/{case_id}/runs/{run_id}", "RunDetailWithDirectories", "RunDetail"),
        ("/api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace", "TraceWithDirectories", "TraceView"),
    ):
        model = normalized["components"]["schemas"].pop(extended)
        for field in ("steps_url", "artifacts_url"):
            assert model["properties"].pop(field) == {"title": field.replace("_", " ").title(), "type": "string"}
            model["required"].remove(field)
        model["title"] = original
        assert model == before["components"]["schemas"][original]
        normalized["components"]["schemas"][original] = model
        normalized["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"] = {
            "$ref": "#/components/schemas/" + original}
    for name in ("RunStepView", "RunStepPage", "RunArtifactView", "RunArtifactPage", "ArtifactReference",
                 "RecordError", "RecordErrorDetail", "RecordValidationError", "ArtifactKind", "MaterialState", "StepKind", "StepState"):
        if name not in before["components"]["schemas"]:
            normalized["components"]["schemas"].pop(name)
    assert set(normalized["paths"].pop("/api/v1/socai2/alerts/{alert_id}/same-host-alerts")) == {"get"}
    for name in ("AlertHostMatch", "AlertHostItem", "AlertHostPage"):
        normalized["components"]["schemas"].pop(name)
    assert set(normalized["paths"].pop("/api/v1/socai2/alerts/{alert_id}/review-candidates")) == {"get"}
    for name in ("AlertReviewTactic", "AlertReviewMatch", "AlertReviewCandidate", "AlertReviewScope", "AlertReviewPage"):
        normalized["components"]["schemas"].pop(name)
    assert set(normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/exploration-base")) == {"get"}
    assert set(normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/exploration")) == {"get", "put"}
    for name in ("ExplorationSources", "ExplorationBase", "ExplorationLinkInput", "ExplorationSave", "ExplorationSnapshot", "ExplorationSaved", "JsonValue"):
        normalized["components"]["schemas"].pop(name)
    assert set(normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/exploration-candidates")) == {"get"}
    for name in ("ExplorationObject", "ExplorationMatch", "ExplorationExcludedObject",
                 "ExplorationScope", "ExplorationCandidate", "ExplorationPage"):
        normalized["components"]["schemas"].pop(name)
    assert set(normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/story")) == {"get"}
    assert set(normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/members/{alert_id}/relations")) == {"get"}
    for name in ("StoryEntry", "StoryPage", "RelatedStoryEntry", "RelatedStoryPage", "StorySummary",
                 "InvestigationRef", "InvestigationRelation", "SharedObject", "SharedObjectPage",
                 "MemberInvestigationPage", "CaseMemberRelations"):
        normalized["components"]["schemas"].pop(name)
    adoption = "/api/v1/socai2/cases/{case_id}/results/{result_id}/adopt"
    assert "200" in normalized["paths"][adoption]["post"]["responses"]
    normalized["paths"][adoption] = before["paths"][adoption]
    assert set(normalized["paths"].pop(adoption + "ion-preview")) == {"get"}
    assert set(normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/assessments")) == {"get"}
    for name in ("AdoptedAssessment", "AssessmentHistory", "ResultAdoptionPreview",
                 "ResultAdoptionReceipt", "ResultAdoptionRequest"):
        normalized["components"]["schemas"].pop(name)
    normalized["components"]["schemas"]["AdoptCaseAIResult"] = before["components"]["schemas"]["AdoptCaseAIResult"]
    attachments = normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/attachments")
    assert set(attachments) == {"get", "post"}
    assert set(normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/attachments/{attachment_id}")) == {"get"}
    for name in ("CaseAttachmentCreate", "CaseAttachmentPage", "CaseAttachmentView"):
        normalized["components"]["schemas"].pop(name)
    comments = normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/comments")
    assert set(comments) == {"get", "post"}
    for name in ("CaseCommentCreate", "CaseCommentPage", "CaseCommentView"):
        normalized["components"]["schemas"].pop(name)
    for kind in ("alerts", "incidents", "cases"):
        exported = normalized["paths"].pop("/api/v1/socai2/" + kind + "/export")
        assert set(exported) == {"get"}
        assert "text/csv" in exported["get"]["responses"]["200"]["content"]
    summary = normalized["paths"].pop("/api/v1/socai2/incidents/grouping-summary")
    assert set(summary) == {"get"}
    for name in ("GroupingQuery", "GroupingSummary"):
        normalized["components"]["schemas"].pop(name)
    common = {"time_from", "time_to", "sort_by", "sort_order"}
    subject = common | {"q", "severity", "handling_status", "owner_id", "assignment_state", "cursor"}
    for kind, allowed in (("cases", common), ("alerts", subject), ("incidents", subject)):
        operation = normalized["paths"]["/api/v1/socai2/" + kind]["get"]
        old_names = {p["name"] for p in before["paths"]["/api/v1/socai2/" + kind]["get"]["parameters"]}
        assert {p["name"] for p in operation["parameters"]} - old_names == allowed
        operation["parameters"] = [p for p in operation["parameters"] if p["name"] not in allowed]
    page = normalized["components"]["schemas"]["SubjectPage"]
    for name in ("filtered_total", "next_cursor"):
        page["properties"].pop(name)
        page["required"].remove(name)
    # The owner explicitly removed authentication from the independent app.
    # Normalize only that delta; all business schemas still compare exactly.
    for document in (before, normalized):
        document["paths"] = {p: methods for p, methods in document["paths"].items()
                             if not p.startswith("/api/v1/auth/")}
        document["components"].pop("securitySchemes", None)
        for name in ("UserMeResponse", "LoginRequest", "RefreshRequest", "PreferencesPatch", "TokenResponse"):
            document["components"]["schemas"].pop(name, None)
        for methods in document["paths"].values():
            for operation in methods.values():
                operation.pop("security", None)
                for code in ("401", "403"):
                    operation.get("responses", {}).pop(code, None)
    normalize_documented_contract_deltas(before, normalized, after)
    assert normalized["paths"] == before["paths"]
    assert normalized["components"] == before["components"]
    assert socai2_main.app is app
    from investigation_http.adapters.runtime import configured_database_name

    assert socai2_main.configured_database_name is configured_database_name
    assert not any(path.startswith(("/internal", "/api/v2")) for path in after["paths"])
    assert "app.investigation_v2.query_api" not in sys.modules
    assert "app.investigation_v2.program_start_api" not in sys.modules
    for name in (
        "cases",
        "case_ai",
        "analysis",
        "pages",
        "tasks",
        "stage_execution",
        "subject_management",
    ):
        legacy = importlib.import_module("app.api.v1.endpoints.socai2_" + name)
        external = importlib.import_module("investigation_http.external_routes." + name)
        assert legacy is external


def test_investigation_core_imports_without_external_http_package():
    # A separate process proves the dependency direction, independent of test
    # collection order and previously imported endpoint modules.
    script = """
import importlib.abc, sys
class NoExternalHTTP(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('investigation_http', 'app.api.')):
            raise AssertionError('core imported HTTP: ' + fullname)
sys.meta_path.insert(0, NoExternalHTTP())
from app.socai2.case_service import CaseService
from app.socai2.stage_results import StageResultService
from app.socai2.baseline_executor import BaselineExecutor
from app.socai2.run_records import RunRecordService
from app.socai2.run_directory import RunDirectoryService
assert all((CaseService, StageResultService, BaselineExecutor, RunRecordService, RunDirectoryService))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=API,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_case_initial_execution_has_no_public_prepare_start_bypass():
    from app.socai2.case_service import CaseService
    from fastapi.testclient import TestClient
    from investigation_http import contracts
    from investigation_http.main import app
    from investigation_http.ports import CaseOperations

    identity = "00000000-0000-4000-8000-000000000601"
    client = TestClient(app)
    for suffix in ("baseline/prepare", f"runs/{identity}/start"):
        response = client.post(f"/api/v1/socai2/cases/{identity}/{suffix}", json={})
        assert response.status_code == 404
    for name in ("prepare_baseline", "start_case"):
        assert not hasattr(CaseOperations, name)
        assert callable(getattr(CaseService, name))
    for name in ("PrepareBaseline", "BaselinePreparation", "Start"):
        assert not hasattr(contracts, name)
