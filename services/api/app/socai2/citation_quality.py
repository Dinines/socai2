"""New execution policy: retain judgments, diagnose references separately.

The raw response is never changed. This record describes a derived version;
strict legacy parsers remain available by omitting the review argument.
"""
import copy

from .baseline_store import digest

VERSION = "socai2.citation-quality.v1"
FIELDS = {"source_ids", "evidence_ids", "support_ids", "counter_ids"}
NOTE = "前序模型分析保留原判断；其引用存在质量问题，不能视为已核实事实。"


def new_review():
    return {"policy": VERSION, "state": "not_checked", "issues": [], "processing": [],
            "references": [], "prose_quality": "not_checked"}


def issue(review, code, path="$", **details):
    review["state"] = "issues_recorded"
    entry = {"code": code, "path": path, "action": "retain_judgment", **details}
    if entry not in review["issues"]:
        review["issues"].append(entry)


def normalize(value, review, path="$", *, fields=FIELDS):
    """Deduplicate only source arrays. Definitions, prose and scope are untouched."""
    value = copy.deepcopy(value)
    def visit(node, at):
        if isinstance(node, list):
            for i, item in enumerate(node):
                visit(item, f"{at}.{i}")
        elif isinstance(node, dict):
            for key, child in node.items():
                loc = f"{at}.{key}"
                if key in fields and isinstance(child, list) and all(isinstance(v, str) for v in child):
                    after = list(dict.fromkeys(child))
                    if after != child:
                        review["processing"].append({"path": loc, "action": "deduplicate_source_list",
                                                    "before": child, "after": after})
                        issue(review, "duplicate_source", loc, source_ids=child)
                        node[key] = after
                else:
                    visit(child, loc)
    visit(value, path)
    return value


def record_references(review, ids, sources, path, owned=None, *, required=True):
    if review is None:
        return
    if review["state"] == "not_checked":
        review["state"] = "checked"
    review["references"].append({"path": path, "source_ids": list(ids), "declared_members": owned,
        "resolved": [{"source_id": sid, "alert_ids": sources[sid].get("alert_ids", []),
                      "ref": sources[sid]["ref"]} for sid in ids if sid in sources],
        "unresolved_ids": [sid for sid in ids if sid not in sources]})
    if required and not ids:
        issue(review, "empty_sources", path, source_ids=[])


def prior_note(source, aid):
    quality = source.get("triage_citation_quality", {}).get(aid, {})
    return NOTE if quality.get("state") == "issues_recorded" else None


def seal(review, original, derived):
    review.update(original_sha256=digest(original), derived_sha256=digest(derived),
                  conclusion_modified=False if derived is not None else None)
    return review
