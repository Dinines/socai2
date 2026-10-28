"""API-relative navigation for saved Case reports; no data or execution access."""
from urllib.parse import quote


def analysis_urls(case_id, run_id):
    base = f"/api/v2/investigation/cases/{case_id}/investigations/{run_id}"
    return {"result_url": base, "steps_url": f"{base}/steps", "report_url": f"{base}/report",
            "evidence_url": f"{base}/evidence", "execution_url": f"/api/v2/investigation/executions/{run_id}"}


def evidence_url(case_id, run_id, evidence_id, row_index=None):
    url = f"{analysis_urls(case_id, run_id)['evidence_url']}/{quote(evidence_id, safe='')}"
    return url if row_index is None else f"{url}/rows/{row_index}"


def citation_links(case_id, run_id, evidence_ids):
    return ", ".join(f"[{identity}]({evidence_url(case_id, run_id, identity)})" for identity in evidence_ids) or "无"


def evidence_index(case_id, run_id, result):
    return [{"evidence_id": item["evidence_id"], "kind": item["kind"], "tool": item.get("tool"),
             "available": item.get("available"), "row_count": len(item.get("rows", [])),
             "detail_url": evidence_url(case_id, run_id, item["evidence_id"])} for item in result.get("evidence", [])]


def report_navigation(case_id, run_id, result):
    if result is None:
        return None
    report = result.get("report", {})
    navigation = {section: [{"index": index, "evidence_links": [
        {"evidence_id": ref, "url": evidence_url(case_id, run_id, ref)} for ref in item.get("evidence_ids", [])]}
        for index, item in enumerate(report.get(section, []))]
        for section in ("findings", "member_assessments", "relationships", "open_questions")}
    navigation["timeline"] = [{"index": index, "evidence_url": evidence_url(case_id, run_id, item["evidence_id"]),
        "row_url": evidence_url(case_id, run_id, item["evidence_id"], item["row_index"])
                   if item.get("row_index") is not None else None}
        for index, item in enumerate(report.get("timeline", []))]
    navigation["evidence"] = evidence_index(case_id, run_id, result)
    return navigation
