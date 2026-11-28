"""Attach external resource URLs to the story's saved source identities."""
from app.socai2.case_story import CaseStoryService
from app.socai2.case_story_contracts import RelatedStoryQuery

from .run_directory import result_urls, run_url


def source_url(case_id, kind, identity, task_id, detail):
    case_path = f"/api/v1/socai2/cases/{case_id}"
    if kind == "run":
        return detail
    if kind == "task_revision":
        return f"{case_path}/tasks/{task_id}/revisions/{identity}"
    if kind == "case":
        return f"/api/v1/socai2/cases/{identity}"
    section = {"result": "results", "artifact": "artifacts"}[kind]
    return f"{case_path}/{section}/{identity}"


def investigation_urls(ref, case_id):
    detail = run_url(ref["subject_type"], ref["subject_id"], ref["run_id"])
    relations = []
    for source in ref["relations"]:
        row = {key: value for key, value in source.items() if key != "task_id"}
        row["source_url"] = source_url(case_id, source["source_type"], source["source_id"],
                                       source["task_id"], detail)
        relations.append(row)
    return {**ref, "detail_url": detail, "relations": relations,
            "result_refs": result_urls(ref["result_refs"], ref["subject_id"], detail)}


class CaseStoryBackend(CaseStoryService):
    async def read(self, tenant_id, case_id, query):
        page = await super().read(tenant_id, case_id, query)
        if isinstance(query, RelatedStoryQuery):
            for item in page["items"]:
                if item["investigation_ref"] is not None:
                    item["investigation_ref"] = investigation_urls(item["investigation_ref"], case_id)
        return page

    async def read_member_relations(self, tenant_id, case_id, alert_id, query):
        page = await super().read_member_relations(tenant_id, case_id, alert_id, query)
        objects, investigations = page["shared_objects"], page["investigations"]
        objects["items"] = [
            {**row, "material_url": f"/api/v1/socai2/alerts/{alert_id}/materials/{row['focus_material_id']}"}
            for row in objects["items"]
        ]
        investigations["items"] = [investigation_urls(ref, case_id) for ref in investigations["items"]]
        return page
