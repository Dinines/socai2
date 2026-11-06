"""Render the offline case selector for the processing audit."""

from __future__ import annotations

import html
import json


def render_index(records: list[dict], controls_url: str | None = None) -> str:
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    controls = (
        f'<a href="{html.escape(controls_url, quote=True)}">查看受控对照</a>'
        if controls_url else ""
    )
    return _PAGE.replace("<!--controls-->", controls).replace(
        "<!--records-->", payload.replace("<", "\\u003c")
    )


_PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>调查运行记录</title>
<style>
* { box-sizing: border-box }
:root { color-scheme: light; font: 15px/1.55 "Microsoft YaHei",system-ui,sans-serif; color: #18312d; background: #f4f6f5 }
body { margin: 0 }
h1, h2, p { margin: 0 }
h1 { font-size: clamp(1.35rem, 2vw, 1.7rem) }
h2 { font-size: 1.04rem }
a { color: #135e53; text-underline-offset: .2em }
a:focus-visible, iframe:focus-visible { outline: 3px solid #117562; outline-offset: 2px }
header, .section-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .6rem 1rem }
header { padding: .8rem 1.25rem; border-bottom: 1px solid #cfd9d4; background: white }
main { display: grid; grid-template-columns: clamp(21rem, 31vw, 32rem) minmax(0, 1fr); gap: .8rem; padding: .8rem }
section { min-width: 0; border: 1px solid #cdd8d3; background: white }
.section-head { padding: .75rem .9rem; border-bottom: 1px solid #d7dfdb; min-height: 3.2rem }
.list { max-height: calc(100vh - 9rem); overflow: auto }
table { width: 100%; border-spacing: 0; table-layout: fixed; text-align: left }
th, td { padding: .65rem .75rem; vertical-align: top }
th { font-size: .84rem; color: #405c56; font-weight: 600; background: #f1f5f3; position: sticky; top: 0 }
th:last-child { width: 8.7rem }
td { border-bottom: 1px solid #e2e9e5; overflow-wrap: anywhere }
tbody tr:hover { background: #f4f8f6; cursor: pointer }
tr.selected { background: #e8f3ee }
tr.selected td:first-child { box-shadow: inset 3px 0 #247660 }
.case-link { display: block; text-decoration: none }
.case-link:hover strong { text-decoration: underline }
.batch, .case-key { display: block; font-size: .83rem; color: #47605a }
.case-key { font-weight: 700; letter-spacing: .04em }
time { font-variant-numeric: tabular-nums }
.summary { padding: .45rem .9rem; font-size: .88rem; color: #405c56; overflow-wrap: anywhere }
iframe { display: block; width: 100%; height: calc(100vh - 12rem); min-height: 25rem; border: 0; border-top: 1px solid #d7dfdb }
.notice { padding: 1rem }
[hidden] { display: none !important }
@media (max-width: 800px) {
  header { padding: .7rem .85rem }
  main { grid-template-columns: minmax(0, 1fr); padding: .45rem; gap: .55rem }
  .list { max-height: 32vh }
  iframe { height: 72vh; min-height: 22rem }
}
</style>
</head>
<body>
<header><h1>调查运行记录</h1><!--controls--></header>
<main>
  <section aria-labelledby="list-title">
    <div class="section-head"><h2 id="list-title">案例</h2></div>
    <div class="list">
      <table><thead><tr><th scope="col">案例与批次</th><th scope="col">调查启动时间<br>（北京时间）</th></tr></thead>
        <tbody id="case-rows"></tbody>
      </table>
      <p id="no-records" class="notice" hidden>暂无案例记录。</p>
    </div>
  </section>
  <section aria-labelledby="detail-title">
    <div class="section-head"><h2 id="detail-title">阶段输入与输出</h2>
      <a id="open-detail" target="_blank" rel="noopener" hidden>单独打开详情</a>
    </div>
    <p id="selected-summary" class="summary" aria-live="polite"></p>
    <iframe id="case-detail" title="阶段输入与输出" tabindex="0" hidden></iframe>
  </section>
</main>
<noscript><p class="notice">请启用 JavaScript 以选择案例并查看详情。</p></noscript>
<script type="application/json" id="audit-records"><!--records--></script>
<script>
"use strict";
const records = JSON.parse(document.getElementById("audit-records").textContent);
const rows = document.getElementById("case-rows");
let frame = document.getElementById("case-detail");
const direct = document.getElementById("open-detail");
const summary = document.getElementById("selected-summary");
const byId = new Map();
const byKey = new Map();
const rowById = new Map();
const stateLabels = new Map([
  ["unknown", "执行待确认"], ["failed", "失败"], ["completed", "完成"], ["pending", "待执行"]
]);
const clock = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"
});

function timestamp(value) {
  if (!value || !/(?:Z|[+-]\\d{2}:?\\d{2})$/i.test(value)) return null;
  const instant = Date.parse(value);
  return Number.isFinite(instant) ? instant : null;
}

function element(tag, text, className) {
  const item = document.createElement(tag);
  if (text != null) item.textContent = text;
  if (className) item.className = className;
  return item;
}

// Unknown start times follow every dated execution. Tied records retain the input order.
const ordered = records.map(record => ({record, started: timestamp(record.started_at)}));
ordered.sort((a, b) => a.started === b.started ? 0 :
  a.started === null ? 1 : b.started === null ? -1 : b.started - a.started);
for (const {record, started} of ordered) {
  byId.set(record.id, record);
  const legacyKey = record.key.toLowerCase();
  if (!byKey.has(legacyKey)) byKey.set(legacyKey, record);
  const row = rows.insertRow();
  row.dataset.id = record.id;
  rowById.set(record.id, row);
  const link = element("a", null, "case-link");
  link.href = "#" + encodeURIComponent(record.id);
  const displayKey = /^[a-z][0-9]{2}$/i.test(record.key) ? record.key.toUpperCase() : record.key;
  link.append(element("span", displayKey, "case-key"), element("strong", record.title),
              element("span", record.batch, "batch"));
  row.insertCell().append(link);
  const dateCell = row.insertCell();
  if (started !== null) {
    const time = element("time", clock.format(started));
    time.dateTime = record.started_at;
    dateCell.append(time);
  } else {
    dateCell.textContent = record.started_at ? "时间格式或时区未确认" : "未记录启动时间";
  }
}

rows.addEventListener("click", event => {
  const row = event.target.closest("tr");
  if (row && !event.target.closest("a")) location.hash = encodeURIComponent(row.dataset.id);
});

let selectedId;
function selectFromHash() {
  let key = location.hash.slice(1);
  try { key = decodeURIComponent(key); } catch { /* Show the missing-case state. */ }
  const current = key ? byId.get(key) || byKey.get(key.toLowerCase()) : ordered[0]?.record;
  const id = current?.id ?? null;
  if (selectedId === id) return;
  const previous = rowById.get(selectedId);
  if (previous) {
    previous.classList.remove("selected");
    previous.querySelector("a").removeAttribute("aria-current");
  }
  selectedId = id;
  // Replacing the iframe keeps detail navigation out of the parent page's Back history.
  const nextFrame = frame.cloneNode(false);
  nextFrame.hidden = !current;
  if (!current) {
    nextFrame.removeAttribute("src");
    direct.hidden = true;
    direct.removeAttribute("href");
    summary.textContent = key ? "未找到链接指定的案例，请从列表选择。" : "暂无可查看的案例详情。";
  } else {
    const row = rowById.get(id);
    row.classList.add("selected");
    row.querySelector("a").setAttribute("aria-current", "true");
    const stateLabel = stateLabels.get(current.state);
    const stateText = stateLabel ? stateLabel + "（" + current.state + "）" : current.state;
    summary.textContent = [current.title, current.batch, current.runs + " 个 Run",
      current.steps + " 个步骤", stateText || "未记录执行状态"].join(" · ");
    nextFrame.title = current.title + " · " + current.batch + " · 阶段输入与输出";
    nextFrame.src = current.detail;
    direct.href = current.detail;
    direct.hidden = false;
  }
  frame.replaceWith(nextFrame);
  frame = nextFrame;
}

document.getElementById("no-records").hidden = records.length > 0;
window.addEventListener("hashchange", selectFromHash);
selectFromHash();
</script>
</body>
</html>
"""
