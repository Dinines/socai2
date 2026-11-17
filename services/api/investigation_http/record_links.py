"""Paths published by the external HTTP application."""


def directory_links(run_id):
    base = f"/api/v1/socai2/analysis-runs/{run_id}"
    return {"steps_url": base + "/steps", "artifacts_url": base + "/artifacts"}


def comparison_links(case_id, context):
    """Link only the core's frozen Case comparison; never select a prior Run."""
    previous = context.previous_run_id if context is not None else None
    result = context.comparison_result_id if context is not None else None
    base = f"/api/v1/socai2/cases/{case_id}"
    return {
        "previous_run_url": f"{base}/runs/{previous}" if previous is not None else None,
        "comparison_result_url": f"{base}/results/{result}" if result is not None else None,
    }


def content_url(subject_type, subject_id, run_id, artifact_id):
    base = f"/api/v1/socai2/{subject_type}s/{subject_id}"
    if run_id is not None:
        base += ("/runs/" if subject_type == "case" else "/analysis/runs/") + str(run_id)
    return base + "/artifacts/" + str(artifact_id)
