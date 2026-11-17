"""Direct boundary checks: external routes, legacy imports, independent core."""

import ast
import copy
import importlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "services/api"
PACKAGE = API / "investigation_http"


def imports(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            yield from (item.name for item in node.names)


def test_external_routes_have_no_internal_implementation_imports():
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


def test_external_contract_preserves_compatibility_except_approved_list_delta():
    from app import socai2_main
    from investigation_http.main import app

    before = json.loads(
        (
            ROOT
            / "docs/operations/evidence/http-boundary-20261113-01/before-openapi.json"
        ).read_text()
    )
    after = app.openapi()
    normalized = copy.deepcopy(after)
    # Confirmed Case allocation delta: four writes replace their old single-case
    # receipts; only relationship GET and event detail gain the new read fields.
    allocation_schemas = normalized["components"]["schemas"]
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
    case_submit = normalized["paths"].pop("/api/v1/socai2/cases/{case_id}/investigations")
    assert set(case_submit) == {"post"}
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
    for name in ("StoryEntry", "StoryPage"):
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
