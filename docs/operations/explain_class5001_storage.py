"""One private 5001 explanation using a real, exact-version lake readback."""
import argparse
import html
import ipaddress
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from audit_sample_field_mapping import (
    at,
    digest,
    ingress,
    loads,
    pretty,
    require,
    save,
    state,
)
from render_sample_mapping_readable import displayed_value

# Business interpretation is confined to these known contract paths. Other keys
# remain visible for local review, with no invented meaning.
FIELDS = [
    ("metadata.uid", "日志编号", "source_event_id", "已有UID继续用于去重和关联原文，无需再造一个日志编号。"),
    ("time", "日志发生时间", "event_time", "使用发生时间检索；与入湖时间分开。"),
    ("class_uid", "日志类别", "class_uid", "5001按设备库存记录处理，类别本身不表示告警。"),
    ("device.uid", "设备编号", None, "值得补到资产关联输入：用它连接资产库。先核资产库设备键和唯一范围，不必为展示就新增数据库列。"),
    ("device.hostname", "设备主机名", "device_hostname", "复用现有设备主机名查询；保持device角色。"),
    ("device.ip", "设备IP", "device_ip", "复用现有设备IP查询；与源/目标端点分开。"),
    ("device.network_interfaces", "设备网络接口", None, "资产关联需要多IP/MAC时值得逐接口提取，保留同一接口内关系；不把首个接口直接当主IP。"),
    ("device.name", "设备名称", None, "设备详情由资产库提供；日志保留当时观察，需要历史对照时再提取。"),
    ("device.type_id", "设备类型编号", None, "设备详情由资产库提供；需要历史类型时按标准枚举解释，不根据编号猜设备。"),
    ("device.os", "系统信息", None, "设备详情由资产库提供；只有调查需要当时系统信息时才补历史观察读取。"),
    ("metadata.product", "日志来源产品", None, "用于解释记录来自哪个产品；作为来源背景读取，不代替资产归属。"),
    ("activity_id", "记录的动作编号", "activity_id", "需要说明库存动作时按5001的枚举解释；不按其他类别的同号动作解释。"),
    ("status_id", "记录的状态编号", None, "若调查需要状态，补明确的类内枚举投影；不从缺失状态推定成功。"),
    ("severity_id", "来源等级", "severity_id", "保留上游等级，不当成我方调查结论。"),
    ("is_alert", "来源告警标记", "is_alert", "保留true/false；普通库存上下文不要求为true。"),
    ("raw_data", "原始厂商材料", "raw_payload", "保留追溯；先用规范字段，未知业务内容需要理解后再选取，不整包交给分析模型。"),
]


def same_column(path, original, saved):
    if path == "device.ip":
        def address(value):
            parsed = ipaddress.ip_address(value)
            return parsed.ipv4_mapped or parsed if isinstance(parsed, ipaddress.IPv6Address) else parsed
        return address(original) == address(saved)
    if path == "time":
        stamp = datetime.fromisoformat(saved)
        stamp = stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp
        return type(original) is int and ingress.datetime_milliseconds(stamp) == original
    if path == "is_alert":
        return type(original) in {bool, int} and original in (0, 1) and type(saved) is int and int(original) == saved
    if path == "raw_data" and not isinstance(original, str):
        return ingress.tagged(original) == ingress.tagged(loads(saved))
    return ingress.tagged(original) == ingress.tagged(saved)


def compare(original, response):
    rows = response["rows"]
    require(len(rows) <= 1, "unexpected_readback_rows")
    row = rows[0] if rows else None
    retained = None
    if row:
        retained, _, _, _ = ingress.decode(row["ocsf_json"].encode())
    complete = retained is not None and ingress.tagged(original) == ingress.tagged(retained)
    fields, absent = [], []
    for path, label, column, advice in FIELDS:
        value = at(original, path)
        actual_path = path
        if value is ingress.ABSENT:
            value = at(original, "unmapped.spirithub.partial_fields." + path)
            if value is not ingress.ABSENT and value is not ingress.BLOCKED:
                actual_path = "unmapped.spirithub.partial_fields." + path
                advice = "补充材料里有这个值；先核明确partial标记、类型和与根字段的冲突，再用于关联或查询。"
        shape = state(value)
        if shape["state"] != "present":
            absent.append({"path": path, "label": label, "state": shape["state"]})
            continue
        match = None
        if row and column:
            try:
                match = same_column(path, value, row[column])
            except (TypeError, ValueError, KeyError):
                match = False
        if not row:
            storage = "本次精确查询未找到该版本，尚不能证明这条样本已落湖。"
        elif not complete:
            storage = "查到记录，但完整JSON未通过一致性核对，暂不认定保存完整。"
        elif column and match:
            storage = "完整JSON已核对保留；同时已提取到查询字段 " + column + "，值一致。"
        elif column:
            storage = "完整JSON已保留；查询字段 " + column + " 与该原值不一致，需要核映射。"
            advice = "先修这一字段的提取或角色对应，再核查询读回。原文不改。"
        else:
            storage = "已保留在完整JSON中；当前没有单独的公共查询列。"
        fields.append({"path": path, "actual_path": actual_path, "label": label, "source": shape,
                       "column": column, "column_match": match, "saved_column_value": row.get(column) if row and column else None,
                       "storage": storage, "advice": advice})
    covered = {tuple(f["actual_path"].split(".")) for f in fields}

    def remaining(value, path=()):
        if path in covered:
            return []
        if isinstance(value, dict) and value:
            return [entry for key, child in value.items() for entry in remaining(child, (*path, key))]
        if isinstance(value, list) and value:
            return [entry for index, child in enumerate(value) for entry in remaining(child, (*path, index))]
        label = "$" + "".join("[" + ingress.json_text(segment) + "]" for segment in path)
        return [{"path": label, "source": state(value)}]

    return {"record_found": bool(row), "complete_json_equal": complete, "fields": fields,
            "absent": absent, "other_fields": remaining(original)}


def render(original, result):
    esc = html.escape
    status = ("这条日志的同一UID和内容版本已在3e隔离测试湖找到，完整JSON内容与下载样本一致。"
              if result["complete_json_equal"] else "本次尚未证明这条样本已完整保存在指定湖中，请以各行状态为准。")
    parts = ["<!doctype html><html lang='zh-CN'><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\">",
        "<title>5001：提供了什么、存了什么、还需补什么</title>",
        ("<style>body{font:16px/1.65 system-ui;max-width:1200px;padding:24px;margin:auto;color:#203047}"
         "table{width:100%;border-collapse:collapse}th,td{padding:14px;border:1px solid #dce2eb;vertical-align:top;text-align:left}"
         "th{background:#f0f5fa}td:first-child{width:38%}pre{font:13px/1.5 monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:450px;overflow:auto}"
         "small,.muted{color:#637387}summary{cursor:pointer;padding:10px 0;color:#275da2}.note{background:#eef5ff;padding:16px}a{color:#275da2}</style>"),
        "<h1>只看这一条5001设备库存日志</h1><p class='note'>" + status + "</p>",
        "<p>第一列只列这条日志实际提供且有内容的字段。第二列来自实际ClickHouse读取，不使用前轮本机试算代替。第三列说明是否值得继续提取。</p>",
        "<p>日志编号沿用metadata.uid；设备编号用于关联资产库。完整JSON已保存、单独查询列已映射、调查工具已接通，是三个分别核对的事项。</p>",
        "<table><tr><th>日志实际提供了什么</th><th>我们已经保存了什么</th><th>还需要补什么 / 怎么用</th></tr>"]
    for field in result["fields"]:
        parts += ["<tr><td><strong>" + esc(field["label"]) + "</strong><br><small>" + esc(field["actual_path"]) + "</small>",
                  displayed_value(field["source"]), "</td><td>" + esc(field["storage"]),
                  ("<details><summary>数据库里的列值</summary><pre>" + esc(pretty(field["saved_column_value"])) + "</pre></details>"
                   if field["column"] and result["record_found"] else ""),
                  "</td><td>" + esc(field["advice"]) + "</td></tr>"]
    parts += ["</table><p><strong>工具边界：</strong>当前没有独立5001取证工具。资产详情由资产库提供；先把事件与资产对应好，再按调查需要决定是否读取历史库存观察。</p>",
              "<details><summary>这条日志未提供或未填写的候选字段</summary><ul>"]
    labels = {"missing": "没有提供", "null": "值为null", "empty": "内容为空", "blocked_parent": "上层结构不能按该路径读取"}
    for field in result["absent"]:
        parts.append("<li>" + esc(field["label"] + "（" + field["path"] + "）：" + labels[field["state"]]) + "</li>")
    parts += ["</ul><p>缺少候选字段不自动构成数据缺陷，只有具体调查能力需要时才补齐。</p></details>",
              "<details><summary>其它实际提供的字段（尚未逐项解释业务用途）</summary>",
              "<p>" + ("这些字段也已包含在核对一致的完整JSON中。" if result["complete_json_equal"] else "这些字段的湖内保存尚未证实。")
              + "需要先理解用途再决定提取规则。</p><table><tr><th>原文位置</th><th>日志内容</th></tr>"]
    for field in result["other_fields"]:
        parts += ["<tr><td>" + esc(field["path"]) + "</td><td>" + displayed_value(field["source"]) + "</td></tr>"]
    parts += ["</table></details><details><summary>查看完整原始JSON</summary><pre>",
              esc(pretty(original)), "</pre></details>",
              "<p><a href='conclusions-for-review.json'>不含原值的结论待审清单</a> · <a href='original.json'>原始JSON</a></p>",
              "<small>本机私有材料；仅核这一条记录。目标为既有3e隔离测试湖，正式持续消费和新工具并未因此发布。未写业务库或调用模型。</small></html>"]
    return "\n".join(parts)


def build(config):
    os.umask(0o077)
    root = Path(config["output_directory"])
    try:
        sample = Path(config["sample_file"])
        manifest = loads(Path(config["sample_manifest"]).read_text())
        before = digest(sample)
        require(before == manifest["files"]["ocsf/class-5001.json"], "sample_changed")
        original, _, _, version = ingress.decode(sample.read_bytes())
        require(original["class_uid"] == 5001, "wrong_sample_class")
        response = loads((root / "result.json").read_text())
        require(response["execution"] == "completed" and response["database"] == config["database"], "read_scope_mismatch")
        require(response["parameters"]["source_version"] == version and response["parameters"]["source_event_id"] == at(original, "metadata.uid"), "sample_version_mismatch")
        result = compare(original, response)
        save(root / "analysis.json", result)
        save(root / "original.json", original)
        # Standard allowlisted paths and states only; still requires user review.
        review = {"class_uid": 5001, "record_found": result["record_found"], "complete_json_equal": result["complete_json_equal"],
                  "fields": [{k: f[k] for k in ("path", "column", "column_match", "advice")} for f in result["fields"]],
                  "unavailable_fields": result["absent"], "contains_raw_values": False}
        save(root / "conclusions-for-review.json", review)
        page = render(original, result)
        with (root / "index.html").open("x") as stream:
            stream.write(page)
        require((root / "index.html").read_text() == page and digest(sample) == before, "report_readback_or_input_changed")
        save(root / "manifest.json", {"files": {p.name: digest(p) for p in root.iterdir() if p.is_file()}})
    except Exception as exc:  # noqa: BLE001 -- no raw values or derived conclusions in stdout.
        save(root / "local-failure.json", {"exception_type": type(exc).__name__})
        print('{"explanation":"incomplete"}')
        return 2
    print('{"explanation":"saved_and_read_back","source_unchanged":true,"raw_data_disclosed_to_codex":false}')
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    raise SystemExit(build(json.loads(Path(args.profile).read_text())))
