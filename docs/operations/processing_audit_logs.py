"""Write navigable, read-only Case execution logs from the persisted Run, Step and Artifact rows."""
import hashlib
import json
import posixpath
from collections import defaultdict
from datetime import datetime

from processing_audit_detail import ARTIFACT_NAMES, STEP_NAMES, beijing, esc
from processing_audit_flow import SOURCES, STATES, TOOLS

POINTERS = ("input_artifact_id", "output_artifact_id", "reused_artifact_id")
POINTER_LABELS = dict(zip(POINTERS, ("输入", "输出", "复用"), strict=True))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def instant(value):
    if value is None:
        return float("-inf")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.utcoffset() is None:
        raise ValueError(f"Case log timestamp has no timezone: {value}")
    return dt.timestamp()


def latest(values):
    return max((v for v in values if v is not None), key=instant, default=None)


def step_name(row):
    kind = row.get("kind")
    name = row.get("name") or row.get("stage_code") or "步骤"
    if name == "system_closing":
        return "保存系统兜底报告"
    if kind == "tool":
        tool = (row.get("actual_args") or {}).get("tool_name") or name
        return "查询" + SOURCES.get(tool, TOOLS.get(tool, tool))
    return STEP_NAMES.get((row.get("stage_code"), kind), name)


def linked(ref, start):
    """All JSON file references resolve relative to the JSON containing them."""
    return dict(ref, path=posixpath.relpath(ref["path"], start)) if ref and ref["path"] else ref


def state_label(value):
    return STATES.get(value, (value or "未记录",))[0]


def ref_html(ref):
    if not ref:
        return "未绑定工件"
    identity = esc(ref["id"])
    if not ref["path"]:
        return f"{identity}（快照无可读原件）"
    name = ARTIFACT_NAMES.get(ref["kind"], ref["kind"]) or "工件"
    return f'<a href="{ref["path"]}">{esc(name)} · {identity}</a>'


def render_logs(manifest, recent):
    case = manifest["case"]
    page_title = f'{case.get("title") or case["id"]} · Case 运行日志'
    parts = [('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" '
              f'content="width=device-width,initial-scale=1"><title>{esc(page_title)}</title>'),
             ('<style>:root{color-scheme:light}*{box-sizing:border-box}body{margin:0 auto;padding:24px;'
             'max-width:1040px;color:#172f36;font:15px/1.65 system-ui,sans-serif;overflow-wrap:anywhere}'
             'h1,h2{line-height:1.3}h1{font-size:26px}h2{font-size:20px;margin:2rem 0 .5rem}'
             'a{color:#185b79}details{border-bottom:1px solid #d5dee0;padding:.5em 0}summary{cursor:pointer}'
             'time,.dim{color:#435b63}time{font-variant-numeric:tabular-nums}ul{padding-left:1.4em}'
             'dl{display:grid;grid-template-columns:minmax(5em,auto) 1fr;gap:.2em .8em}dd{margin:0}'
             'code{font-size:.9em}pre{white-space:pre-wrap}a:focus-visible,summary:focus-visible{outline:2px solid #127393}'
              '</style><main>'),
             f'<h1>{esc(page_title)}</h1><p>批次 {esc(manifest["batch"])} · Case <code>{esc(case["id"])}</code></p>',
             '<p><a href="manifest.json">打开日志目录清单（JSON）</a></p>']
    open_ids = {(s["run_id"], s["step_id"]) for s in recent}
    for run in manifest["runs"]:
        parts += [f'<section><h2>{esc(run["kind"])} · {esc(state_label(run["state"]))}</h2>',
                  (f'<p>Run <code>{esc(run["id"])}</code> · 最近更新（北京）{esc(beijing(run["updated_at"]))}'
                   f' · <a href="{run["path"]}">运行记录（JSON）</a></p>'),
                  f'<p>交付状态　{esc(state_label(run["delivery_state"]))}</p>']
        if run["stop_reason"]:
            parts.append(f'<p>停止原因　<code>{esc(run["stop_reason"])}</code></p>')
        if not run["steps"]:
            parts.append('<p>本轮尚无已记录步骤。</p>')
        for step in run["steps"]:
            opened = " open" if (run["id"], step["step_id"]) in open_ids else ""
            parts.append(f'<details{opened}><summary>{esc(step["stage_code"] or "")} · {esc(step["label"])} · '
                         f'{esc(state_label(step["state"]))} <time>{esc(beijing(step["updated_at"]))}</time></summary>'
                         f'<p>步骤 {esc(step["seq"])} · <a href="{step["path"]}">查看步骤日志（JSON）</a></p><dl>')
            for field, label in POINTER_LABELS.items():
                parts.append(f'<dt>{label}</dt><dd>{ref_html(step[field])}</dd>')
            if step["other_artifacts"]:
                refs = "<br>".join(ref_html(ref) for ref in step["other_artifacts"])
                parts.append(f'<dt>其他关联工件</dt><dd>{refs}</dd>')
            if step["error"] is not None:
                parts.append(f'<dt>错误或跳过原因</dt><dd><pre>{esc(json.dumps(step["error"], ensure_ascii=False))}'
                             '</pre></dd>')
            parts.append('</dl></details>')
        if run["artifacts"]:
            parts.append(f'<details><summary>本轮工件目录（{run["artifact_count"]} 份）</summary><ul>')
            for ref in run["artifacts"]:
                parts.append(f'<li>{ref_html(ref)} · <time>{esc(beijing(ref["captured_at"]))}</time></li>')
            parts.append('</ul></details>')
        parts.append('</section>')
    parts.append('</main></html>')
    return "".join(parts).encode("utf-8")


def case_log_files(data, *, batch, key):
    """Return registry metadata and immutable, site-relative file bodies for one scoped Case."""
    cases = data.get("cases", [])
    if not cases:
        return None, {}
    if len(cases) != 1:
        raise ValueError("Case log export requires one scoped Case")
    case = cases[0]
    runs = [r for r in data["runs"] if r.get("case_id") == case["id"]]
    if not runs:
        return None, {}

    def verify_tenant(row):
        if row.get("tenant_id") != case.get("tenant_id"):
            raise ValueError("Case log crosses tenant boundary")

    run_ids = {r["id"] for r in runs}
    steps_by_run = defaultdict(list)
    reused_ids = set()
    for step in data["run_steps"]:
        if step["run_id"] in run_ids:
            verify_tenant(step)
            steps_by_run[step["run_id"]].append(step)
            if step.get("reused_artifact_id"):
                reused_ids.add(step["reused_artifact_id"])
    step_owners = {s["id"]: rid for rid, rows in steps_by_run.items() for s in rows}
    if len(run_ids) != len(runs) or len(step_owners) != sum(map(len, steps_by_run.values())):
        raise ValueError("Duplicate Run or Step in Case log")

    files = {}
    refs = {}
    by_step = defaultdict(list)
    by_run = defaultdict(list)
    artifact_rows = {a["id"]: a for a in data["artifacts"]}
    members = {m["alert_id"] for m in data.get("case_alerts", ()) if m.get("case_id") == case["id"]}
    incidents = {m["incident_id"] for m in data.get("case_incidents", ()) if m.get("case_id") == case["id"]}
    for art in sorted(data["artifacts"], key=lambda a: a["id"]):
        owned = art.get("run_id") in run_ids
        reused = (art["id"] in reused_ids and art.get("case_id") in (None, case["id"])
                  and (art.get("case_id") == case["id"] or art.get("alert_id") in members
                       or art.get("incident_id") in incidents))
        if not owned and not reused:
            continue
        verify_tenant(art)
        if art.get("case_id") not in (None, case["id"]):
            raise ValueError("Artifact belongs to a different Case")
        if owned and art.get("step_id") and step_owners.get(art["step_id"]) != art["run_id"]:
            raise ValueError("Artifact Step does not belong to its Run")
        if art["id"] in refs:
            raise ValueError("Duplicate Artifact in Case log")
        path = f"artifacts/{len(refs) + 1:04}.json"
        ref = {"id": art["id"], "kind": art.get("kind"), "run_id": art.get("run_id"), "step_id": art.get("step_id"),
               "captured_at": art.get("captured_at"), "path": path}
        files[path] = json_bytes(art)
        refs[art["id"]] = ref
        if owned:
            by_run[art["run_id"]].append(ref)
            if art.get("step_id"):
                by_step[art["step_id"]].append(ref)

    def pointer(row, field):
        fid = row.get(field)
        if not fid:
            return None
        ref = refs.get(fid, {"id": fid, "path": None})
        original = artifact_rows.get(fid)
        if original and field != "reused_artifact_id" and original.get("run_id") != row.get("run_id", row["id"]):
            raise ValueError("Primary Case log artifact belongs to another Run")
        return ref

    catalog = []
    flat_steps = []
    for i, run in enumerate(sorted(runs, key=lambda r: r["id"]), 1):
        verify_tenant(run)
        rid = run["id"]
        folder = f"runs/{i:03}"
        steps = []
        for step in sorted(steps_by_run[rid], key=lambda s: s["seq"]):
            seq = step["seq"]
            if type(seq) is not int or seq < 0:
                raise ValueError("Invalid Case step sequence")
            path = f"{folder}/steps/{seq:04}.json"
            if path in files:
                raise ValueError("Duplicate Case step sequence")
            pointers = {field: pointer(step, field) for field in POINTERS}
            attached = by_step[step["id"]]
            other = [ref for ref in attached if ref["id"] not in {step.get(k) for k in POINTERS}]
            updated = latest([step.get("started_at"), step.get("ended_at"), *(a["captured_at"] for a in attached)])
            row = {"step_id": step["id"], "run_id": rid, "seq": seq, "label": step_name(step),
                   "stage_code": step.get("stage_code"), "state": step.get("state"), "error": step.get("error"),
                   "updated_at": updated, "path": path, **pointers, "other_artifacts": other}
            steps.append(row)
            files[path] = json_bytes({
                "schema_version": "socai2.audit-step-log.v1", "source_table": "socai2.run_steps",
                "batch": batch, "case_id": case["id"], "label": row["label"], "updated_at": updated, "step": step,
                "artifact_links": {field: linked(ref, folder + "/steps") for field, ref in pointers.items()},
                "other_artifacts": [linked(ref, folder + "/steps") for ref in other],
            })
        steps.sort(key=lambda s: (instant(s["updated_at"]), s["seq"]), reverse=True)
        flat_steps.extend(steps)
        run_artifacts = sorted(by_run[rid], key=lambda a: (instant(a["captured_at"]), a["id"]), reverse=True)
        updated = latest([run.get(n) for n in ("requested_at", "scope_updated_at", "started_at", "ended_at")] +
                         [s["updated_at"] for s in steps] + [a["captured_at"] for a in run_artifacts])
        path = folder + "/run.json"
        catalog.append({"id": rid, "kind": run["kind"], "state": run.get("state"), "updated_at": updated,
                        "delivery_state": run.get("delivery_state"), "stop_reason": run.get("stop_reason"),
                        "path": path, "steps": steps, "artifacts": run_artifacts, "artifact_count": len(run_artifacts)})
        files[path] = json_bytes({
            "schema_version": "socai2.audit-run-log.v1", "source_table": "socai2.runs",
            "batch": batch, "run": run, "input_artifact": linked(pointer(run, "input_artifact_id"), folder),
            "steps": [{"id": s["step_id"], "seq": s["seq"], "state": s["state"],
                       "path": posixpath.relpath(s["path"], folder)} for s in steps],
            "artifacts": [linked(ref, folder) for ref in run_artifacts],
        })

    catalog.sort(key=lambda r: (instant(r["updated_at"]), r["id"]), reverse=True)
    recent = sorted((s for s in flat_steps if s["updated_at"] is not None),
                    key=lambda s: (instant(s["updated_at"]), s["run_id"], s["seq"]), reverse=True)[:3]
    manifest = {"schema_version": "socai2.case-log-directory.v1", "batch": batch, "key": key,
                "case": {"id": case["id"], "title": case.get("title")}, "runs": catalog}
    files["manifest.json"] = json_bytes(manifest)
    files["index.html"] = render_logs(manifest, recent)
    hashes = {name: hashlib.sha256(value).hexdigest() for name, value in files.items()}
    prefix = "logs/" + hashlib.sha256(json_bytes(hashes)).hexdigest() + "/"
    info = {"index": prefix + "index.html", "manifest": prefix + "manifest.json", "run_count": len(catalog),
            "step_count": len(flat_steps), "artifact_count": len(refs), "updated_at": catalog[0]["updated_at"],
            "recent": [{**{k: s[k] for k in ("run_id", "step_id", "label", "state", "updated_at")},
                        "path": prefix + s["path"]} for s in recent]}
    return info, {prefix + path: body for path, body in files.items()}
