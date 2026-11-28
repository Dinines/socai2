"""Compare private OCSF samples with field needs and current pure projections.

Run with PYTHONPATH=services/api. No network, SQL, model, or ingestion writes.
Only fixed execution status is printed; all values and derived results stay local.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "mapping_audit_ingress", REPO / "services/fusion/app/services/lake_ingress.py")
ingress = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ingress
spec.loader.exec_module(ingress)


def loads(value):
    return json.loads(value, parse_float=Decimal, object_pairs_hook=ingress._unique,
                      parse_constant=ingress._nonfinite)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, code):
    if not ok:
        raise ValueError(code)


def json_value(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec="milliseconds")
    if isinstance(value, dict):
        return {key: json_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(child) for child in value]
    if type(value) is float:
        return Decimal(str(value))
    return value


def save(path, value):
    value = json_value(value)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(ingress.json_text(value) + "\n")
    require(ingress.tagged(loads(path.read_text())) == ingress.tagged(value), "json_readback_failed")


def state(value):
    if value is ingress.ABSENT:
        return {"state": "missing"}
    if value is ingress.BLOCKED:
        return {"state": "blocked_parent"}
    kind = {type(None): "null", bool: "boolean", str: "string", int: "integer",
            Decimal: "decimal", list: "array", dict: "object"}[type(value)]
    empty = isinstance(value, (str, list, dict)) and len(value) == 0
    return {"state": "null" if value is None else "empty" if empty else "present", "type": kind, "value": value}


def at(document, path):
    return ingress.nested(document, tuple(path.split(".")))


def expected(value, kinds):
    shape = state(value)
    if "type" not in shape or shape["type"] == "null":
        return False
    return any(shape["type"] == kind or kind == "object_array" and isinstance(value, list)
               and all(isinstance(v, dict) for v in value) for kind in kinds)


def field_sources(projection, path, columns):
    root = "$.ocsf_json." + path
    return [f for f in projection.get("fields", []) if f["source_path"] == root
            or f["source_path"].startswith(root + ".") or f["source_path"].startswith(root + "[")
            or f["source_path"] in {"$." + column for column in columns}]


def inspect_requirement(document, requirement, row, projection):
    path = requirement["path"]
    root = at(document, path)
    fallback = at(document, "unmapped.spirithub.partial_fields." + path)
    marked = at(document, "unmapped.spirithub.mapping_status") == "partial"
    conflict = (root is not ingress.ABSENT and root is not ingress.BLOCKED
                and fallback is not ingress.ABSENT and fallback is not ingress.BLOCKED
                and ingress.tagged(root) != ingress.tagged(fallback))
    allowed = requirement.get("partial_allowed", True)
    selected = fallback if allowed and root is ingress.ABSENT and marked else root
    selected_from = "partial_fields" if allowed and root is ingress.ABSENT and marked else "root"
    valid = expected(selected, requirement["types"])
    fields = field_sources(projection, path, requirement.get("columns", []))
    omissions = [item for item in projection.get("omissions", [])
                 if item["source_path"] == "$.ocsf_json." + path
                 or item["source_path"].startswith("$.ocsf_json." + path + "[")
                 or item["source_path"].startswith("$.ocsf_json." + path + ".")]
    if conflict:
        conclusion = "根与partial不同；保留两者，暂不用于确定性关联"
    elif state(selected)["state"] != "present":
        conclusion = "本样本未提供非空值；是否阻断取决于该项业务用途，非自动判整条无效"
    elif not valid:
        conclusion = "原值存在但形态不符；保留原文，需核具体格式后明确转换规则"
    elif requirement["use"] == "asset":
        conclusion = "交资产库职责核对；此处仅保留事件对象关联，不自动新增库存工具"
    elif requirement["use"] == "internal":
        conclusion = "用于后台身份、筛选或追溯；不要求进入模型业务字段"
    elif fields:
        conclusion = "当前行投影有相关输出；需继续核角色、冲突和实际查询前提"
    else:
        conclusion = "原文有值但此路径未进入当前C4业务投影；候选补映射"
    return {**requirement, "root": state(root), "partial": state(fallback),
            "proposed_selection": {"from": selected_from, **state(selected)}, "shape_valid": valid,
            "conflict": conflict, "lake_output": {c: row[c] for c in requirement.get("columns", [])},
            "c4_output": fields, "c4_omissions": omissions, "assessment": conclusion}


def inventory(value, requirements, path="$"):
    """Exact leaf locations, including array indexes; never combine array elements."""
    if isinstance(value, dict) and value:
        return [leaf for key, child in value.items()
                for leaf in inventory(child, requirements, path + "[" + json.dumps(key, ensure_ascii=False) + "]")]
    if isinstance(value, list) and value:
        return [leaf for index, child in enumerate(value)
                for leaf in inventory(child, requirements, f"{path}[{index}]")]
    matches = [r["path"] for r in requirements
               if path == r["inventory_prefix"] or path.startswith(r["inventory_prefix"] + "[")]
    return [{"path": path, **state(value), "requirement_paths": matches}]


def analyze(document, requirements, profile, position):
    from app.socai2.baseline_evidence_tools import TOOLS, row_projection

    adapted = ingress.adapt_ocsf(ingress.json_text(document).encode(), profile=profile, position=position)
    # This is the ordinary query-row time representation, not an alternative mapper.
    row = json_value(adapted.row)
    projection = row_projection(row)
    checked = [inspect_requirement(document, r, row, projection) for r in requirements]
    inventory_rules = [{**r, "inventory_prefix": "$" + "".join("[" + json.dumps(k) + "]" for k in r["path"].split("."))}
                       for r in requirements]
    return {"upstream_mapping_status": state(at(document, "unmapped.spirithub.mapping_status")),
            "partial_container": state(at(document, "unmapped.spirithub.partial_fields")),
            "ingress_parse_status": row["parse_status"], "ingress_issues": list(adapted.issues),
            "existing_tool": next((name for name, cls in TOOLS.items() if cls == document.get("class_uid")), None),
            "requirements": checked, "leaf_inventory": inventory(document, inventory_rules),
            "current_ingress_row": row, "current_c4_projection": projection}


def pretty(value, level=0):
    if isinstance(value, dict) and value:
        return "{\n" + ",\n".join("  " * (level + 1) + ingress.json_text(k) + ": " + pretty(v, level + 1)
                                    for k, v in value.items()) + "\n" + "  " * level + "}"
    if isinstance(value, list) and value:
        return "[\n" + ",\n".join("  " * (level + 1) + pretty(v, level + 1) for v in value) + "\n" + "  " * level + "]"
    return ingress.json_text(value)


def pre(value):
    return "<pre>" + html.escape(pretty(value)) + "</pre>"


def render(report):
    esc = html.escape
    pieces = ["<!doctype html><html lang='zh-CN'><meta charset='utf-8'>",
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\">",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>实际值、字段需求与当前映射</title>",
        ("<style>body{font:15px/1.6 system-ui;color:#182334;margin:28px auto;padding:0 20px;max-width:1600px}"
         "table{border-collapse:collapse;width:100%}td,th{border:1px solid #cbd3df;padding:9px;vertical-align:top}"
         "pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 monospace;background:#f3f5f8;padding:9px;"
         "max-height:420px;overflow:auto}summary{cursor:pointer;font-weight:600}article{border-top:2px solid #ccd;padding:24px 0}"
         "a{color:#1556ad}.note{background:#fff4d8;padding:14px}.scroll{overflow:auto}small{color:#516075}</style>"),
        "<h1>调查字段需求 × 真实JSON × 当前映射</h1>",
        ("<p class='note'>仅供本机审阅，包含未经脱敏的原值和派生结果。每类一条，不是全类覆盖率。"
         "本次仅运行当前入湖适配和C4行投影函数，未写数据库、未执行查询或模型。"
         "非现有工具类别的C4输出只是代码探查，不表示工具已经接通。</p>"),
        ("<p>先核身份/时间/对象，再核动作、状态和类内材料。设备属性由资产库负责。"
         "缺少可选字段不是错误；0和false不是缺失。上游mapping_status与我方parse_status分别展示。"
         "原始JSON和本次全部输出均保留；折叠不截断文件。</p><nav>")]
    for card in report["classes"]:
        pieces.append(f"<a href='#c{card['class_uid']}'>{card['class_uid']} {esc(card['name'])}</a> · ")
    pieces.append("</nav>")
    for card in report["classes"]:
        result, cls = card["analysis"], card["class_uid"]
        partial = result["upstream_mapping_status"].get("value") == "partial"
        show_partial = partial or result["partial_container"]["state"] == "present"
        pieces += [f"<article id='c{cls}'><h2>{cls} · {esc(card['name'])}</h2>",
            f"<p>{esc(card['question'])}</p><p>现有湖工具：{esc(result['existing_tool'] or '无该类查询入口；下列C4输出仅为代码探查')}。</p>",
            f"<p><a href='originals/class-{cls}.json'>完整原始JSON</a> · <a href='results/class-{cls}.json'>本次完整分析JSON</a></p>"]
        if show_partial:
            pieces.append("<p>原文带partial标记或材料，逐项并列检查；不自动将两侧对象/数组合并。</p>")
        else:
            pieces.append("<p>未标记partial且无非空partial材料；仅查看根字段。缺少partial不是数据缺陷，也不等于完整OCSF规范校验通过。</p>")
        pieces += ["<details><summary>上游状态 / 我方解析状态 / 诊断</summary>",
            pre({k: result[k] for k in ("upstream_mapping_status", "ingress_parse_status", "ingress_issues")}), "</details>",
            "<div class='scroll'><table><tr><th>需要什么 / 路径</th><th>日志实际值与类型</th>",
            "<th>partial原值</th>" if show_partial else "",
            "<th>当前入湖列 / C4输出</th><th>差距及预计调整</th></tr>"]
        for item in result["requirements"]:
            pieces += [f"<tr><td><strong>{esc(item['purpose'])}</strong><br><code>{esc(item['path'])}</code><br>",
                f"<small>用途：{esc(item['use'])}；形态：{esc(', '.join(item['types']))}</small></td><td>{pre(item['root'])}</td>",
                "<td>" + pre(item["partial"]) + "</td>" if show_partial else "",
                "<td>" + pre({"lake_columns": item["lake_output"], "c4_fields": item["c4_output"], "omissions": item["c4_omissions"]}) + "</td>",
                f"<td>{esc(item['assessment'])}<p>{esc(item['proposal'])}</p></td></tr>"]
        pieces += ["</table></div><details><summary>原文全部叶字段（含数组元素位置、尚未纳入需求的字段）</summary>",
            pre(result["leaf_inventory"]), "</details><details><summary>当前C4完整输出</summary>",
            pre(result["current_c4_projection"]), "</details></article>"]
    return "\n".join([*pieces, "</html>"])


def audit(profile, profile_path):
    os.umask(0o077)
    output = Path(profile["output_directory"])
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    passed = False
    try:
        os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(Path(profile["policy_file"]).resolve())
        from app.socai2.runtime_policy import active_policy
        active_policy.cache_clear()
        active_policy()
        source = Path(profile["sample_directory"])
        manifest = loads((source / "manifest.json").read_text())
        before = {path: digest(source / path) for path in manifest["files"]}
        require(before == manifest["files"], "source_manifest_mismatch")
        ingress_config = dict(profile["ingress_profile"])
        ingress_config["topics"] = tuple(ingress_config["topics"])
        ingress_profile = ingress.IngressProfile(**ingress_config)
        position = ingress.KafkaPosition(**profile["position"])
        (output / "originals").mkdir()
        (output / "results").mkdir()
        report = {"version": "socai2.sample-field-mapping-audit.v1", "scope": "local_pure_code_probe_one_per_class", "classes": []}
        for card in profile["classes"]:
            cls = card["class_uid"]
            payload = (source / "ocsf" / f"class-{cls}.json").read_bytes()
            original, _, _, _ = ingress.decode(payload)
            require(original is not None and type(original.get("class_uid")) is int and original["class_uid"] == cls,
                    "sample_class_mismatch")
            requirements = profile["common"] + card["requirements"]
            require(len({r["path"] for r in requirements}) == len(requirements), "duplicate_requirement")
            result = analyze(original, requirements, ingress_profile, position)
            copy = output / "originals" / f"class-{cls}.json"
            copy.write_bytes(payload)
            require(copy.read_bytes() == payload, "original_copy_mismatch")
            save(output / "results" / f"class-{cls}.json", result)
            report["classes"].append({"class_uid": cls, "name": card["name"], "question": card["question"], "analysis": result})
        save(output / "mapping-analysis.json", report)
        page = render(report)
        (output / "index.html").write_text(page)
        require((output / "index.html").read_text() == page, "html_readback_failed")
        require(before == {path: digest(source / path) for path in before}, "source_changed")
        save(output / "manifest.json", {"inputs": before, "profile_sha256": digest(profile_path),
            "files": {str(p.relative_to(output)): digest(p) for p in output.rglob("*") if p.is_file()}})
        passed = True
    except Exception as exc:  # noqa: BLE001 -- never emit values, paths derived from records, or tracebacks.
        save(output / "failure.json", {"exception_type": type(exc).__name__})
    status = {"execution": "completed" if passed else "incomplete", "input_unchanged": passed,
              "local_actual_value_mapping_review_saved_and_read_back": passed,
              "production_mapping_changed": False, "raw_data_disclosed_to_codex": False}
    save(output / "status.json", status)
    print(json.dumps(status))
    return 0 if passed else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    raise SystemExit(audit(loads(Path(args.profile).read_text()), args.profile))
