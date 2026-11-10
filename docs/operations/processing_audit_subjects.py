"""Build lightweight alert and incident views from the same scoped PG export as the Case."""
import hashlib
import json
from urllib.parse import quote

from processing_audit_delivery import incident_fields
from processing_audit_detail import STEP_NAMES, STYLE, beijing, esc, fields, raw
from processing_audit_flow import SOURCES, STATES, TOOLS
from read_processing_audit_20261106 import check_credentials

NAMES = {"alert": "告警", "incident": "事件"}
TABLE_LABELS = {
    "alerts": "告警基本信息", "incidents": "事件基本信息", "alert_materials": "各版告警材料",
    "alert_source_refs": "来源引用", "alert_objects": "关联对象", "alert_assessments": "分诊与人工反馈",
    "incident_diagnoses": "各版诊断", "incident_alerts": "事件成员关系", "case_alerts": "Case 成员关系",
    "case_incidents": "Case 事件关系", "runs": "执行轮次", "run_steps": "执行步骤", "artifacts": "输入、输出和工件",
    "activities": "操作记录", "activity_targets": "操作影响", "comments": "评论", "response_links": "处置关联",
}


def subject_rows(data, kind, subject):
    """Follow typed subject and run keys within the subject tenant, including unprocessed subjects."""
    sid = subject["id"]
    owner = kind + "_id"
    tenant = subject.get("tenant_id")

    def rows(table):
        return (r for r in data.get(table, ()) if r.get("tenant_id") == tenant)

    own = ("alert_materials", "alert_source_refs", "alert_objects", "alert_assessments", "case_alerts") if kind == "alert" else (
        "incident_diagnoses", "case_incidents")
    result = {kind + "s": [subject]}
    for table in (*own, "incident_alerts", "comments", "response_links"):
        result[table] = [r for r in rows(table) if r.get(owner) == sid]
    wanted_kind = "alert_basic" if kind == "alert" else "incident_diagnosis"
    result["runs"] = [r for r in rows("runs") if r.get(owner) == sid and r.get("kind") == wanted_kind]
    run_ids = {r["id"] for r in result["runs"]}
    result["run_steps"] = [r for r in rows("run_steps") if r.get("run_id") in run_ids]
    result["artifacts"] = [r for r in rows("artifacts") if r.get("run_id") in run_ids
                           or (r.get("run_id") is None and r.get(owner) == sid)]
    result["activity_targets"] = [r for r in rows("activity_targets") if r.get(owner) == sid or r.get("run_id") in run_ids]
    activity_ids = {r["activity_id"] for r in result["activity_targets"]}
    result["activities"] = [r for r in rows("activities") if r.get("subject_" + owner) == sid or r["id"] in activity_ids]
    return result


def route(kind, identity, source):
    parts = (kind, identity, source) if kind else (source,)
    return "../index.html#" + "/".join(quote(str(value), safe="") for value in parts)


def state(value):
    return STATES.get(value, (value or "未记录",))[0]


def run_history(rows):
    runs = sorted(rows["runs"], key=lambda r: (r.get("requested_at") or "", r["id"]), reverse=True)
    if not runs:
        return "<p>此快照没有该主体的执行轮次。</p>"
    parts = []
    for r in runs:
        steps = sorted((s for s in rows["run_steps"] if s["run_id"] == r["id"]),
                       key=lambda s: (s.get("seq") is None, s.get("seq"), s["id"]))
        parts.append(f'<h3>{esc(beijing(r.get("started_at") or r.get("requested_at")))} · {esc(state(r.get("state")))}</h3>')
        parts.append(fields([("执行 ID", r["id"]), ("交付状态", state(r.get("delivery_state"))),
                             ("停止原因", r.get("stop_reason"))]))
        if r["kind"] == "incident_diagnosis":
            result = next((d for d in rows.get("incident_diagnoses", []) if d["source_run_id"] == r["id"]), None)
            parts.append(fields(incident_fields(result)))
        parts.append("<ol>")
        for step in steps:
            name = step.get("name") or step.get("stage_code")
            if step.get("kind") == "tool":
                tool = (step.get("actual_args") or {}).get("tool_name") or name
                name = "查询" + (SOURCES.get(tool) or TOOLS.get(tool) or str(tool))
            else:
                name = STEP_NAMES.get((step.get("stage_code"), step.get("kind")), name)
            err = step.get("error") or {}
            reason = (err.get("code") or err.get("message")) if isinstance(err, dict) else err
            parts.append(f'<li>{esc(name)} · {esc(state(step.get("state")))}'
                         + (f' · {esc(reason)}' if reason else "") + "</li>")
        parts.append("</ol>" if steps else "</ol><p>此轮没有记录步骤。</p>")
    return "".join(parts)


def render_subject(record, kind, subject, rows, neighbors):
    noun = NAMES[kind]
    is_alert = kind == "alert"
    title = subject.get("title") or subject["id"]
    facts = [(noun + " ID", subject["id"]), ("来源系统 ID", subject.get("source_" + kind + "_id")),
             ("处理状态", subject.get("handling_status"))]
    if is_alert:
        facts.extend([("严重性", subject.get("severity")), ("类别", subject.get("category")),
                      ("发生时间（北京）", beijing(subject.get("event_time")))])
    else:
        facts.extend([("成员告警数", len(rows["incident_alerts"])),
                      ("创建时间（北京）", beijing(subject.get("created_at")))])
    parts = ['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             f"<title>{esc(noun)} · {esc(title)}</title><style>{STYLE}</style></head><body><main>",
             f'<header><p class="quiet">{noun} · {esc(record["batch"])} / {esc(record["key"])}</p>',
             f"<h1>{esc(title)}</h1></header>",
             fields(facts),
             "<p>" + esc(subject.get("description") or "") + "</p>"]
    current_id = subject.get("latest_triage_id" if is_alert else "latest_diagnosis_id")
    current = next((r for r in rows["alert_assessments" if is_alert else "incident_diagnoses"]
                    if r["id"] == current_id), None)
    parts.append("<section><h2>" + ("当前已发布分诊" if is_alert else "当前已发布诊断") + "</h2>")
    if current:
        facts = [("判断", current.get("verdict")), ("理由", current.get("rationale"))] if is_alert else [
            ("诊断摘要", current.get("summary"))]
        parts.append(fields([*facts, ("来源执行 ID", current.get("source_run_id"))]))
        if not is_alert:
            parts.append(fields(incident_fields(current)))
    else:
        parts.append("<p>此快照没有已发布的记录。</p>" if not current_id else
                     f"<p>已发布记录 {esc(current_id)} 的原件未包含在此快照中。</p>")
    parts.append("</section>")
    other = "incident" if is_alert else "alert"
    parts.append("<section><h2>" + ("所属事件" if is_alert else "成员告警") + "</h2>")
    for link in rows["incident_alerts"]:
        identity = link[other + "_id"]
        adjacent = neighbors.get((subject.get("tenant_id"), other, identity))
        if adjacent is None:
            parts.append(f"<p>{esc(identity)} · 此快照缺少主体记录</p>")
        else:
            url = route(other, identity, record["id"])
            parts.append(f'<p><a target="_top" href="{esc(url)}">{esc(adjacent.get("title") or NAMES[other])}'
                         f' · <code>{esc(identity)}</code></a></p>')
    if not rows["incident_alerts"]:
        parts.append("<p>此快照没有成员关系。</p>")
    case_links = rows["case_alerts" if is_alert else "case_incidents"]
    if record.get("scope_id") and any(r["case_id"] == record["scope_id"] for r in case_links):
        parts.append(f'<p><a target="_top" href="{esc(route(None, None, record["id"]))}">查看关联 Case 调查过程</a></p>')
    parts.append("</section><section><h2>执行记录</h2>" + run_history(rows) + "</section>")
    if rows["activities"]:
        parts.append("<section><h2>操作记录</h2><ul>")
        for r in sorted(rows["activities"], key=lambda row: (row.get("occurred_at") or "", row["id"]), reverse=True):
            parts.append(f'<li>{esc(beijing(r.get("occurred_at")))} · {esc(r.get("summary") or r.get("action"))}</li>')
        parts.append("</ul></section>")
    parts.append("<section><h2>数据库原始记录</h2>")
    for table, label in TABLE_LABELS.items():
        if table in rows:
            parts.append(raw(f"{label} · {table}（{len(rows[table])} 条）", rows[table]))
    return "".join(parts) + "</section></main></body></html>"


def prepare_subjects(record, data):
    """Return (registry metadata, HTML bytes) per subject for this single source snapshot."""
    subjects = {}
    seen = set()
    for kind in NAMES:
        for subject in data.get(kind + "s", ()):
            identity = subject.get("id")
            if not isinstance(identity, str) or not identity or (kind, identity) in seen:
                raise ValueError("missing or duplicate subject ID in one source snapshot")
            seen.add((kind, identity))
            subjects[subject.get("tenant_id"), kind, identity] = subject
    result = []
    for (tenant, kind, identity), subject in subjects.items():
        rows = subject_rows(data, kind, subject)
        check_credentials(json.dumps(rows, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        body = render_subject(record, kind, subject, rows, subjects).encode("utf-8")
        detail = f"subjects/{hashlib.sha256(body).hexdigest()}.html"
        result.append(({"kind": kind, "id": identity, "tenant_id": tenant,
                        "title": subject.get("title") or identity, "detail": detail}, body))
    return result
