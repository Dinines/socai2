"""Read the frozen source identities needed by existing content endpoints."""
from sqlalchemy import select

from app.models import socai2 as m

SOURCES = m.CaseAssessmentSources.__table__
REVISIONS = m.TaskRevisions.__table__
ARTIFACTS = m.Artifacts.__table__


def source_query(*, metadata=True):
    """Keep missing references visible; never resolve through a task's current version."""
    columns = list(SOURCES.c) if metadata else [SOURCES.c.result_id,
        SOURCES.c.task_revision_id, SOURCES.c.artifact_id]
    joined = SOURCES.outerjoin(REVISIONS,
        (REVISIONS.c.tenant_id == SOURCES.c.tenant_id)
        & (REVISIONS.c.case_id == SOURCES.c.case_id)
        & (REVISIONS.c.id == SOURCES.c.task_revision_id)).outerjoin(ARTIFACTS,
        (ARTIFACTS.c.tenant_id == SOURCES.c.tenant_id)
        & (ARTIFACTS.c.case_id == SOURCES.c.case_id)
        & (ARTIFACTS.c.id == SOURCES.c.artifact_id))
    return select(*columns, REVISIONS.c.task_id.label("task_id"),
                  ARTIFACTS.c.run_id.label("run_id")).select_from(joined)


def adopted_result_id(assessment, sources):
    if assessment["origin"] != "model" or assessment["validity"] != "accepted" or len(sources) != 1:
        return None
    ref = sources[0]
    if ref.get("task_revision_id") or ref.get("artifact_id"):
        return None
    return ref.get("result_id")


def adopted_verdict(assessment, result_id, result):
    if (result_id is None or result is None or str(result["id"]) != str(result_id)
            or str(result["case_id"]) != str(assessment["case_id"])
            or str(result["tenant_id"]) != str(assessment["tenant_id"])
            or result["kind"] != "baseline" or result["conclusion_origin"] != "model"
            or result["validation_state"] != "accepted" or result["conclusion_state"] == "unavailable"):
        return None
    return result.get("business_verdict")
