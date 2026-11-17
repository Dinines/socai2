"""Adapt core task reads to external URLs without importing execution dispatch."""
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.analysis_tasks import AnalysisTaskService
from app.socai2.baseline_store import StoreError
from sqlalchemy.exc import DBAPIError

from investigation_http.adapters.run_directory import run_url


def task_view(row):
    kind, identity = row["subject_type"], row["subject_id"]
    detail = {k: value for k, value in row.items() if k not in {"request_payload", "attempts", "results"}}
    detail["status_url"] = f"/api/v1/socai2/{kind}s/{identity}/analysis-tasks/{row['task_id']}"
    detail["request"] = row["request_payload"]
    detail["attempts"] = [{**attempt, "run_url": run_url(kind, identity, attempt["run_id"])
                           if attempt["run_id"] else None} for attempt in row["attempts"]]
    detail["results"] = [{**result, "url": f"/api/v1/socai2/cases/{identity}/results/{result['id']}"
                          if result["result_type"] == "case_result" else run_url(kind, identity, result["source_run_id"])}
                         for result in row["results"]]
    return detail


class AnalysisTaskBackend:
    def __init__(self, sessions, *, policy=None):
        self.reader = AnalysisTaskService(sessions, policy if policy is not None else AnalysisTaskPolicy.load())

    async def detail(self, tenant, kind, identity, task_id):
        try:
            return task_view(await self.reader.read_task(tenant, kind, identity, task_id))
        except DBAPIError:
            raise StoreError("service_unavailable", 503) from None

    async def page(self, tenant, kind, identity, **query):
        try:
            page = await self.reader.list_tasks(tenant, kind, identity, **query)
            return {**page, "items": [task_view(row) for row in page["items"]]}
        except DBAPIError:
            raise StoreError("service_unavailable", 503) from None
