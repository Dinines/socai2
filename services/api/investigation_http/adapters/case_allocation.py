"""Allocation transport mapping: business facts stay in the core service."""
from app.socai2.baseline_store import StoreError
from sqlalchemy.exc import DBAPIError


async def allocation_call(call):
    try:
        return await call
    except StoreError as exc:
        code, status = {
            "operation_key_conflict": ("operation_conflict", 409),
            "case_scope_revision_conflict": ("scope_conflict", 409),
            "resolved_case_scope_policy_not_enabled": ("subject_closed", 409),
            "case_incident_members_unavailable": ("empty_scope", 409),
            "case_actor_not_in_tenant": ("service_unavailable", 503),
        }.get(exc.code, (exc.code, exc.status))
        raise StoreError(code, status) from None
    except DBAPIError:
        # Unconfirmed save: reuse the operation key, never report a fake receipt.
        raise StoreError("service_unavailable", 503) from None


def allocation_urls(receipt):
    value = receipt.model_dump(mode="json")
    for item in value["allocations"]:
        item["case_url"] = f"/api/v1/socai2/cases/{item['case_id']}"
        if task := item["initial_task"]:
            task["status_url"] = (f"/api/v1/socai2/cases/{task['subject_id']}"
                                  f"/analysis-tasks/{task['task_id']}")
    return value


def member_change_urls(receipt):
    value = receipt.model_dump(mode="json")
    value["allocation"] = allocation_urls(receipt.allocation)
    return value


def related_case_urls(page):
    value = page.model_dump(mode="json")
    for item in value["items"]:
        item["case_url"] = f"/api/v1/socai2/cases/{item['case_id']}"
    return value
