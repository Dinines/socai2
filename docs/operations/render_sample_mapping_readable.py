"""Render an existing private mapping report in plain language; no new analysis."""
import argparse
import html
import json
import os
from pathlib import Path

from audit_sample_field_mapping import digest, loads, pretty

LABELS = {
    "metadata.uid": "日志编号", "device.uid": "设备编号", "device.hostname": "设备主机名",
    "device.ip": "设备IP", "time": "日志发生时间（毫秒原值）", "class_uid": "日志类别",
    "device.name": "设备名称", "device.type_id": "设备类型编号", "device.os": "设备系统信息",
}
USES = {
    "metadata.uid": "沿用这个UID识别同一条日志、去重并关联原文。数据库用source_event_id保存它，不要求上游再提供一个日志ID。",
    "device.uid": "用于关联资产库中的设备；需要核对资产库采用哪个设备标识。多条日志可以属于同一设备。",
    "device.hostname": "用于按设备查找日志，也可辅助匹配资产；仍需保留它是设备主机名的含义。",
    "device.ip": "用于按设备地址查找日志、辅助匹配资产；地址变化或复用时需要其他标识帮助确认。",
    "time": "用于按事件发生时间检索。这与数据何时存入数据库是两个时间。",
    "device.name": "设备详情由资产库提供；这条日志可保留当时报告的设备名称。",
    "device.type_id": "按对应版本的类型定义解释，设备详情由资产库提供。",
    "device.os": "设备详情由资产库提供；这条日志可保留当时报告的系统信息。",
}
INVENTORY_FIRST = ("metadata.uid", "device.uid", "device.hostname", "device.ip", "time",
                   "device.name", "device.type_id", "device.os")


def displayed_value(shape):
    status = shape["state"]
    if status == "missing":
        return "<span class='muted'>这条日志没有提供</span>"
    if status == "blocked_parent":
        return "<span class='muted'>上层字段不是对象，无法从这个位置读取</span>"
    if status == "null":
        return "<span class='muted'>字段存在，值为 null（未填写）</span>"
    value = shape["value"]
    if value == "":
        return "<span class='muted'>空字符串（未填写内容）</span>"
    if value == []:
        return "<span class='muted'>空列表 []（没有列出条目）</span>"
    if value == {}:
        return "<span class='muted'>空对象 {}（没有列出属性）</span>"
    text = value if isinstance(value, str) else pretty(value)
    content = "<pre>" + html.escape(text) + "</pre>"
    if isinstance(value, (dict, list)):
        return "<details><summary>展开日志提供的具体内容</summary>" + content + "</details>"
    return content


def table(items):
    parts = ["<div class='scroll'><table><thead><tr><th>要了解什么</th><th>日志提供的内容</th>",
             "<th>我们如何使用</th></tr></thead><tbody>"]
    for item in items:
        path = item["path"]
        label = LABELS.get(path, item["purpose"])
        explanation = USES.get(path, item["proposal"])
        parts += ["<tr><td><strong>" + html.escape(label) + "</strong><br><small>" + html.escape(path) + "</small></td>",
                  "<td>" + displayed_value(item["root"]) + "</td><td>" + html.escape(explanation)]
        if item["conflict"]:
            parts.append("<p class='attention'>日志正文与补充材料里的值不同，需要核对；这次保留两份。</p>")
        elif item["root"]["state"] == "present" and not item["shape_valid"]:
            parts.append("<p class='attention'>这个值的格式需要进一步核对，暂不能按预期格式直接使用。</p>")
        if item["partial"]["state"] not in {"missing", "blocked_parent"}:
            parts += ["<details><summary>补充材料中另有记录</summary>", displayed_value(item["partial"]),
                      "<small>是否采用还要核对来源标记、格式及冲突；不自动合并。</small></details>"]
        parts.append("</td></tr>")
    return "\n".join([*parts, "</tbody></table></div>"])


def developer_details(result):
    columns = {name: value for item in result["requirements"] for name, value in item["lake_output"].items()}
    parts = ["<h3>第一步：准备保存到数据库</h3>",
             "<p>下面是当前入湖适配函数算出的列值。本次只在本机计算，没有重新写入或查询ClickHouse。</p>",
             "<table><tr><th>数据库字段</th><th>准备保存的值</th></tr>"]
    for name, value in columns.items():
        parts.append("<tr><td>" + html.escape(name) + "</td><td><pre>" + html.escape(pretty(value)) + "</pre></td></tr>")
    parts += ["</table><h3>第二步：取证后提取给调查分析的内容（C4）</h3>",
              "<p>下面是当前字段提取函数的本机输出。它与数据库保存内容是不同环节；这里没有执行真实取证查询或模型分析。</p>"]
    if result["existing_tool"] is None:
        parts.append("<p>这一类尚无对应的湖取证工具；这些值仅展示现有提取函数会输出什么。</p>")
    parts.append("<table><tr><th>调查字段</th><th>提取的内容</th><th>取自哪里</th></tr>")
    for field in result["current_c4_projection"]["fields"]:
        parts.append("<tr><td>" + html.escape(field["name"]) + "</td><td><pre>" + html.escape(pretty(field["value"]))
                     + "</pre></td><td>" + html.escape(field["source_path"])
                     + ("<p class='attention'>有冲突，需核对。</p>" if field["conflict"] else "") + "</td></tr>")
    if not result["current_c4_projection"]["fields"]:
        parts.append("<tr><td colspan='3'>当前函数没有提取出业务字段；这不代表原文未保存。</td></tr>")
    return "\n".join([*parts, "</table>"])


def render_readable(report):
    parts = ["<!doctype html><html lang='zh-CN'><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\">",
        "<title>日志字段对照 · 简明版</title>",
        ("<style>body{font:16px/1.7 system-ui;color:#1e293b;background:#fafbfc;margin:32px auto;max-width:1180px;padding:0 20px}"
         "header,article{background:white;border:1px solid #dbe2ec;border-radius:12px;padding:24px;margin:20px 0}"
         "table{width:100%;border-collapse:collapse}th{text-align:left;background:#f1f5f9}td,th{padding:14px;border-bottom:1px solid #e2e8f0;vertical-align:top}"
         "td:first-child{width:22%}td:nth-child(2){width:36%}small,.muted{color:#64748b}small{overflow-wrap:anywhere}"
         "pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.55 monospace;margin:0;max-height:420px;overflow:auto}"
         "summary{cursor:pointer;color:#315fa2;padding:8px 0}.attention{color:#92400e}.tip{background:#eef5ff;padding:14px;border-radius:8px}"
         "a{color:#245dab}nav{display:flex;flex-wrap:wrap;gap:8px}nav a{padding:5px 10px;background:#edf2f8;border-radius:6px}"
         ".scroll{overflow-x:auto}details{margin:10px 0}h1{font-size:28px}h2{font-size:23px}</style>"),
        "<header><h1>日志提供了什么，我们怎么用</h1>",
        "<p>先看字段用途和日志原值，再讨论怎么接入调查。字段路径放在名称下面，开发诊断放在详情中。</p>",
        ("<p class='tip'><strong>日志编号 metadata.uid</strong> 标识这一条日志；"
         "<strong>设备编号 device.uid</strong> 标识日志涉及的设备。沿用已有UID即可，无需因为报告写了“稳定ID”再造一个字段。</p>"),
        "<details><summary>上一版的 state、type、入湖列、C4 输出是什么意思？</summary><ul>",
        "<li><code>state</code> 是报告标注的字段状态；<code>present</code> 表示有值。它不是UID。</li>",
        "<li><code>type</code> 是报告识别的值类型；<code>string</code> 表示文本。真正的原值在 <code>value</code> 中，本页直接显示原值。</li>",
        "<li>入湖列：程序准备写入ClickHouse的字段。例如 metadata.uid 对应 source_event_id。上一版展示的是本机适配结果，并非重新查库。</li>",
        "<li>C4 输出：调查取证查询后，程序提取给后续分析使用的内容。日志编号主要用于后台关联，未列入某个业务字段不等于没有保存。</li>",
        "</ul></details><small>本机私有样本，每类一条。展示调整不改变映射规则，不代表整个类别都具备这些字段。</small></header><nav>"]
    for card in report["classes"]:
        parts.append(f"<a href='#c{card['class_uid']}'>{card['class_uid']} {html.escape(card['name'])}</a>")
    parts.append("</nav>")
    for card in report["classes"]:
        cls = card["class_uid"]
        items = card["analysis"]["requirements"]
        parts += [f"<article id='c{cls}'><h2>{cls} · {html.escape(card['name'])}</h2>",
                  "<p>" + html.escape(card["question"]) + "</p>"]
        if cls == 5001:
            by_path = {item["path"]: item for item in items}
            parts += ["<p>先看下面这些设备记录字段。设备详情由资产库负责，这里核对日志编号及与设备的关联。</p>",
                      table([by_path[path] for path in INVENTORY_FIRST if path in by_path]),
                      "<details><summary>查看更多通用字段</summary>",
                      table([item for item in items if item["path"] not in INVENTORY_FIRST]), "</details>"]
        else:
            parts.append(table(items))
        parts += ["<details><summary>开发详情：先看保存，再看调查使用</summary>", developer_details(card["analysis"]),
                  f"<p><a href='index.html#c{cls}'>原版完整诊断</a> · ",
                  f"<a href='originals/class-{cls}.json'>完整日志 JSON</a></p>",
                  "<p>开发对照保留当前入湖列、取证字段、拒绝原因和逐项差距；本页“如何使用”是用途与方案说明。</p></details></article>"]
    return "\n".join([*parts, "</html>"])


def write_readable(profile):
    os.umask(0o077)
    try:
        source = Path(profile["report_directory"])
        manifest = loads((source / "manifest.json").read_text())
        before = {path: digest(source / path) for path in manifest["files"]}
        if before != manifest["files"]:
            raise ValueError("source_changed")
        report = loads((source / "mapping-analysis.json").read_text())
        page = render_readable(report)
        output = source / profile["output_filename"]
        with output.open("x") as stream:
            stream.write(page)
        if output.read_text() != page or before != {path: digest(source / path) for path in before}:
            raise ValueError("readback_or_preservation_failed")
    except Exception:  # noqa: BLE001 -- values and derived results stay private.
        print('{"readable_page":"incomplete"}')
        return 2
    print(json.dumps({"readable_page": "saved_and_read_back", "original_report_unchanged": True,
                      "business_mapping_changed": False, "raw_data_disclosed_to_codex": False}))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    raise SystemExit(write_readable(json.loads(Path(args.profile).read_text())))
