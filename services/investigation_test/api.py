"""Eight read-only endpoints; the application never publishes or runs tests."""
from typing import Annotated, Literal
from uuid import UUID

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from . import __version__
from .models import (
    BatchListItem,
    BatchStatus,
    BatchView,
    Capabilities,
    CaseStatus,
    EvidenceView,
    Identifier,
    Operation,
    Page,
    PreparationView,
    QualityIssue,
    TestCase,
)
from .store import LedgerError, Store, digest, encoded, paginate

PREFIX = "/test-api/v1"


def query_fields(request, names):
    keys = list(request.query_params.keys())
    if set(keys) - set(names) or any(len(request.query_params.getlist(key)) != 1 for key in keys):
        raise LedgerError("invalid_query", 422)


def batch_item(ledger):
    doc = ledger.document
    return {"revision": ledger.revision, "batch": doc.batch,
        "counts": {name: len(getattr(doc, name)) for name in ("cases", "operations", "quality_issues", "evidence")},
        "detail_url": f"{PREFIX}/batches/{doc.batch.id}"}


def evidence_view(batch_id, item):
    url = f"{PREFIX}/batches/{batch_id}/evidence/{item.id}"
    return {**item.model_dump(mode="json"), "metadata_url": url, "content_url": url + "?format=content"}


def create_app(config, upstream=None, *, transport=None, viewer=None):
    store = Store(config)
    proxy = None
    if upstream is not None:
        from .proxy import ReadProxy
        if upstream.environment_label != config.environment_label:
            raise ValueError("test service and upstream environments differ")
        proxy = ReadProxy(upstream, transport=transport)
    app = FastAPI(title="Investigation test records", version=__version__,
                  lifespan=proxy.lifespan if proxy else None)
    if proxy:
        proxy.mount(app)
    viewer_version = None
    if viewer is not None:
        from .viewer import VIEWER_VERSION, mount
        if viewer.page_size > config.max_limit:
            raise ValueError("viewer page_size exceeds ledger max_limit")
        mount(app, viewer)
        viewer_version = VIEWER_VERSION

    @app.exception_handler(LedgerError)
    async def ledger_error(request, exc):
        return JSONResponse(status_code=exc.status, content={"detail": {"code": exc.code,
            "message": "Test record request could not be completed."}})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse(status_code=422, content={"detail": {"code": "invalid_request",
            "message": "Invalid test record parameter."}})

    @app.get(PREFIX + "/capabilities", response_model=Capabilities)
    def capabilities(request: Request):
        query_fields(request, [])
        observations = [row[0].document.preparation.observed_at for row in store.all()]
        return {"service_version": __version__, "viewer_version": viewer_version,
            "test_api_schema": "socai2.test-api.v1", "document_schema_versions": [1],
            "environment_label": config.environment_label, "read_only": True,
            "investigation_http": proxy.description() if proxy else None,
            "latest_preparation_observed_at": max((v for v in observations if v is not None), default=None)}

    @app.get(PREFIX + "/batches", response_model=Page[BatchListItem])
    def batches(request: Request, environment: str | None = None, status: BatchStatus | None = None,
                limit: Annotated[int | None, Query(ge=1)] = None, cursor: str | None = None):
        query_fields(request, ["environment", "status", "limit", "cursor"])
        rows = [row for row in store.all()
            if (environment is None or row[0].document.batch.environment == environment)
            and (status is None or row[0].document.batch.execution_state == status)]
        rows.sort(key=lambda r: (r[0].document.batch.started_at.timestamp()
            if r[0].document.batch.started_at else float("-inf"), r[0].document.batch.id), reverse=True)
        return paginate([batch_item(r[0]) for r in rows], scope=[request.url.path, environment, status],
            snapshot=digest(encoded([r[2] for r in rows])), limit=limit, cursor=cursor, config=config)

    @app.get(PREFIX + "/batches/{batch_id}", response_model=BatchView)
    def batch(request: Request, batch_id: Identifier):
        query_fields(request, [])
        ledger, _, _ = store.load(batch_id)
        return {**batch_item(ledger), "schema_version": 1,
            "links": {name: f"{PREFIX}/batches/{batch_id}/{name}"
                for name in ("cases", "operations", "preparation", "quality-issues")},
            "evidence": [evidence_view(batch_id, item) for item in ledger.document.evidence]}

    @app.get(PREFIX + "/batches/{batch_id}/cases", response_model=Page[TestCase])
    def cases(request: Request, batch_id: Identifier, scenario_id: str | None = None,
              status: CaseStatus | None = None, limit: Annotated[int | None, Query(ge=1)] = None,
              cursor: str | None = None):
        query_fields(request, ["scenario_id", "status", "limit", "cursor"])
        ledger, _, snapshot = store.load(batch_id)
        items = sorted((c for c in ledger.document.cases if (scenario_id is None or c.scenario_id == scenario_id)
            and (status is None or c.status == status)), key=lambda c: c.id)
        return paginate(items, scope=[request.url.path, scenario_id, status], snapshot=snapshot,
            limit=limit, cursor=cursor, config=config)

    @app.get(PREFIX + "/batches/{batch_id}/operations", response_model=Page[Operation])
    def operations(request: Request, batch_id: Identifier, use_case_id: str | None = None,
                   limit: Annotated[int | None, Query(ge=1)] = None, cursor: str | None = None):
        query_fields(request, ["use_case_id", "limit", "cursor"])
        ledger, _, snapshot = store.load(batch_id)
        selected = {c.id for c in ledger.document.cases if use_case_id is None or c.use_case_id == use_case_id}
        items = sorted((o for o in ledger.document.operations if o.case_id in selected), key=lambda o: o.id)
        return paginate(items, scope=[request.url.path, use_case_id], snapshot=snapshot,
            limit=limit, cursor=cursor, config=config)

    @app.get(PREFIX + "/batches/{batch_id}/preparation", response_model=PreparationView)
    def preparation(request: Request, batch_id: Identifier):
        query_fields(request, [])
        ledger, _, _ = store.load(batch_id)
        return {"schema_version": 1, "revision": ledger.revision, "preparation": ledger.document.preparation}

    @app.get(PREFIX + "/batches/{batch_id}/quality-issues", response_model=Page[QualityIssue])
    def quality(request: Request, batch_id: Identifier, use_case_id: str | None = None, run_id: UUID | None = None,
                limit: Annotated[int | None, Query(ge=1)] = None, cursor: str | None = None):
        query_fields(request, ["use_case_id", "run_id", "limit", "cursor"])
        ledger, _, snapshot = store.load(batch_id)
        selected = {c.id for c in ledger.document.cases if use_case_id is None or c.use_case_id == use_case_id}
        items = sorted((q for q in ledger.document.quality_issues if q.case_id in selected
            and (run_id is None or q.run_id == run_id)), key=lambda q: q.id)
        return paginate(items, scope=[request.url.path, use_case_id, str(run_id) if run_id else None],
            snapshot=snapshot, limit=limit, cursor=cursor, config=config)

    @app.get(PREFIX + "/batches/{batch_id}/evidence/{evidence_id}", response_model=EvidenceView,
             responses={200: {"description": "Metadata by default; registered original bytes with format=content"}})
    def evidence(request: Request, batch_id: Identifier, evidence_id: Identifier,
                 representation: Annotated[Literal["metadata", "content"], Query(alias="format")] = "metadata"):
        query_fields(request, ["format"])
        item, body = store.evidence(batch_id, evidence_id)
        if representation == "content":
            return Response(body, media_type=item.mime_type, headers={
                "Content-Disposition": f'attachment; filename="{item.id}"',
                "X-Content-SHA256": item.sha256, "X-Content-Type-Options": "nosniff"})
        return evidence_view(batch_id, item)

    return app
