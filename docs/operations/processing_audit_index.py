"""Static Case-first investigation workbench. All lookups stay inside the published snapshots."""
import html
import json


def render_index(records: list[dict], controls_url: str | None = None) -> str:
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    controls = f'<a href="{html.escape(controls_url, quote=True)}">受控对照 ↗</a>' if controls_url else ""
    return _PAGE.replace("<!--controls-->", controls).replace("<!--records-->", payload)


_PAGE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>调查工作台 · Case 执行记录</title>
<style>
*{box-sizing:border-box}html{color-scheme:light;font:14px/1.55 system-ui,"Microsoft YaHei",sans-serif;color:#1c322f;background:#f3f5f4}
body{margin:0}h1,h2,p{margin:0}a{color:#176459;text-underline-offset:3px}button,select,input{font:inherit}
button,select{cursor:pointer}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #429d89;outline-offset:2px}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px clamp(14px,2.6vw,38px);border-bottom:1px solid #cfdbd6;background:#fff}
.brand,.top nav,.panel-head,.detail-head{display:flex;align-items:center;gap:12px}.brand-mark{width:26px;height:26px;border:1px solid #1e6453;border-radius:7px;background:linear-gradient(90deg,transparent 36%,#d6ece4 36% 42%,transparent 42%),linear-gradient(0deg,transparent 44%,#d6ece4 44% 50%,transparent 50%),#256b59}
h1{font-size:21px;letter-spacing:.03em}h2{font-size:16px}.top nav{font-size:13px}.top nav a,.top summary{color:#365d52}
main{display:grid;grid-template-columns:clamp(270px,24vw,360px) minmax(0,1fr);gap:14px;margin:14px clamp(10px,1.6vw,24px)}
.panel{border:1px solid #d6dfd9;background:white;border-radius:9px;overflow:hidden}.panel-head,.detail-head{justify-content:space-between;padding:14px 16px;border-bottom:1px solid #e1e8e4}
.left{display:flex;flex-direction:column;gap:12px;min-width:0}.list{max-height:47vh;overflow:auto}
table{width:100%;border-collapse:collapse;table-layout:fixed}th{font-size:11px;letter-spacing:.03em;color:#52695f;text-align:left;background:#f6f8f6;font-weight:600}
th,td{padding:9px 12px;border-bottom:1px solid #e5eae7}th:last-child{width:35%}td{overflow-wrap:anywhere}tbody tr:last-child td{border:0}
tbody tr{cursor:pointer}tr.selected{background:#eaf4ee;box-shadow:inset 3px 0 #287454}tr:hover{background:#f1f6f3}
.case-link{text-decoration:none;color:#183e31;display:block}.case-link:hover strong{text-decoration:underline}.case-key{font:600 12px/1.6 Consolas,monospace;color:#396b58;display:block}.batch,.hint,small,.summary{font-size:12px;color:#53695f}
.batch{display:block;overflow-wrap:anywhere}time{color:#40594d;font-size:12px;font-variant-numeric:tabular-nums}
.lookup{padding:14px 16px}.lookup h2{margin-bottom:8px}.lookup form{display:grid;gap:8px}.input-line{display:flex;gap:6px}.input-line input{flex:1;min-width:0}
input,select,button{border:1px solid #c3d0c7;background:#fff;color:#213f33;border-radius:5px;padding:6px 8px}button[type=submit]{background:#235f49;color:#fff;border-color:#235f49}
.lookup label{font-size:13px}.lookup select{padding:3px 5px;margin-left:4px}#lookup-note{overflow-wrap:anywhere;margin-top:7px}
#lookup-options{padding-left:1.2em;overflow-wrap:anywhere}.detail-head{flex-wrap:wrap}.detail-head nav{display:flex;gap:12px;font-size:13px}.summary{padding:6px 16px;background:#f8faf8}
iframe{width:100%;height:calc(100vh - 175px);min-height:26rem;display:block;border:0;border-top:1px solid #d9e2dc}.empty{padding:1rem;color:#556b5f}
dialog{border:1px solid #bfcec4;border-radius:10px;max-width:min(570px,92vw);color:#233f32;padding:20px}dialog::backdrop{background:#17332a60}dialog h2{margin:0 0 12px}dialog pre{background:#f1f5f2;padding:12px;white-space:pre-wrap;overflow-wrap:anywhere}
[hidden]{display:none!important}@media(max-width:780px){main{grid-template-columns:1fr}.list{max-height:30vh}.left{gap:7px}.panel-head,.detail-head,.lookup{padding:9px 12px}.top{padding:9px 12px}.top nav{gap:6px}.top nav a{font-size:12px}iframe{height:70vh;min-height:20rem}}
</style></head><body>
<header class="top"><div class="brand"><span class="brand-mark" aria-hidden="true"></span><h1>调查工作台</h1></div><nav>
<!--controls--><button type="button" id="folder-help">从目录更新</button></nav></header>
<dialog id="folder-guide"><h2>从资料目录更新</h2><p>在项目根目录运行下面的命令，将引号中的路径换成调查导出目录。完成后刷新本页。</p>
<pre>python docs/operations/update_processing_audit.py --folder "调查导出目录"</pre>
<p>可读取带清单的快照或已登记的批次目录。工作台按其中的记录生成步骤日志。</p><form method="dialog"><button>关闭</button></form></dialog>
<main><aside class="left"><section class="panel" aria-labelledby="case-heading"><div class="panel-head"><h2 id="case-heading">Case 调查</h2><span id="case-count" class="hint"></span></div>
<div class="list"><table><thead><tr><th>案件 / 批次</th><th>最近执行更新<br>（北京时间）</th></tr></thead><tbody id="case-rows"></tbody></table><p id="no-records" class="empty" hidden>尚无 Case 调查记录。</p></div></section>
<section class="panel lookup"><h2>告警与事件查询</h2><form id="lookup"><label>按 <select id="subject-kind" aria-label="查询类型"><option value="alert">告警 ID</option><option value="incident">事件 ID</option></select> 查询</label>
<div class="input-line"><input id="subject-id" aria-label="主体 ID" placeholder="粘贴完整 ID" required autocomplete="off" spellcheck="false"><button type="submit">查找</button></div></form><p id="lookup-note" class="hint" role="status"></p><ul id="lookup-options" hidden></ul></section></aside>
<section class="panel"><div class="detail-head"><h2 id="detail-title">Case 执行详情</h2><nav><a id="return-case" hidden>返回 Case</a><a id="open-detail" target="_blank" rel="noopener" hidden>单独打开 ↗</a></nav></div>
<p id="selected-summary" class="summary" aria-live="polite"></p><iframe id="case-detail" title="调查执行详情" hidden></iframe></section></main>
<noscript><p class="empty">请启用 JavaScript 以选择 Case 或按 ID 查询。</p></noscript>
<script type="application/json" id="audit-records"><!--records--></script>
<script>
"use strict";
const field = id => document.getElementById(id);
const records = JSON.parse(field("audit-records").textContent);
const cases = records.filter(record => record.scope_id);
const states = {unknown: "执行待确认", failed: "执行失败", completed: "已完成", running: "执行中", pending_update: "待启动", cancelled: "已取消"};
const delivery = {partial: "部分交付", complete: "完整交付", none: "无交付"};
const clock = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai", month: "2-digit", day: "2-digit", year: "numeric",
  hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"
});

function updated(record) {
  const millis = Date.parse(record.updated_at || record.started_at);
  return Number.isFinite(millis) ? millis : -Infinity;
}
cases.sort((a, b) => updated(b) - updated(a) || a.id.localeCompare(b.id));
const rows = new Map();
let lastCase = cases[0];
let frame = field("case-detail");

function element(tag, text, className) {
  const item = document.createElement(tag);
  if (text != null) item.textContent = text;
  if (className) item.className = className;
  return item;
}
function link(title, url) {
  const anchor = element("a", title);
  anchor.href = url;
  return anchor;
}
for (const record of cases) {
  const row = field("case-rows").insertRow();
  const href = "#" + encodeURIComponent(record.id);
  const anchor = link("", href);
  anchor.className = "case-link";
  if (record.key !== record.batch) anchor.append(element("span", record.key.toUpperCase(), "case-key"));
  anchor.append(element("strong", record.title), element("span", record.batch, "batch"));
  row.insertCell().append(anchor);
  const dateCell = row.insertCell();
  if (Number.isFinite(updated(record))) {
    const time = element("time", clock.format(updated(record)));
    time.dateTime = record.updated_at || record.started_at;
    dateCell.append(time);
  } else {
    dateCell.textContent = "未记录";
  }
  rows.set(record.id, row);
  row.addEventListener("click", event => {
    if (!event.target.closest("a")) location.hash = href;
  });
}
field("case-count").textContent = cases.length + " 个 Case";
field("no-records").hidden = cases.length > 0;
field("folder-help").addEventListener("click", () => field("folder-guide").showModal());

function display(title, summary, url) {
  field("detail-title").textContent = title;
  field("selected-summary").textContent = summary;
  const direct = field("open-detail");
  direct.hidden = !url;
  if (url) direct.href = url;
  else direct.removeAttribute("href");
  if (frame.getAttribute("src") === (url || null)) return;
  // Replace the frame so inspecting another Case does not add iframe history to the back button.
  const next = frame.cloneNode(false);
  next.hidden = !url;
  next.title = title;
  if (url) next.src = url;
  else next.removeAttribute("src");
  frame.replaceWith(next);
  frame = next;
}

function highlight(record) {
  for (const [id, row] of rows) {
    const selected = id === record?.id;
    row.classList.toggle("selected", selected);
    const anchor = row.querySelector("a");
    if (selected) anchor.setAttribute("aria-current", "true");
    else anchor.removeAttribute("aria-current");
  }
}

function showCase(key) {
  const record = key
    ? cases.find(item => item.id === key || item.scope_id === key || item.key.toLowerCase() === key.toLowerCase())
    : cases[0];
  highlight(record);
  if (!record) {
    display("Case 执行详情", key ? "未找到指定的 Case。" : "可使用左侧入口按告警或事件 ID 查询。", null);
    return;
  }
  lastCase = record;
  const summary = [
    record.title, record.batch, (record.logs?.run_count ?? "—") + " 轮 Case 调查",
    states[record.state] || record.state || "未记录执行状态",
    delivery[record.delivery_state] || record.delivery_state
  ];
  display("Case 执行详情", summary.filter(Boolean).join(" · "), record.detail);
}

function showSubject(kind, id, owner) {
  const label = kind === "alert" ? "告警" : "事件";
  field("subject-kind").value = kind;
  field("subject-id").value = id;
  const matches = [];
  for (const record of records) {
    if (owner && record.id !== owner) continue;
    for (const subject of record.subjects || []) {
      if (subject.kind === kind && subject.id.toLowerCase() === id.toLowerCase()) matches.push({record, subject});
    }
  }
  const hit = matches.length === 1 ? matches[0] : null;
  if (hit?.record.scope_id) lastCase = hit.record;
  if (lastCase) {
    field("return-case").href = "#" + encodeURIComponent(lastCase.id);
    field("return-case").hidden = false;
  }
  highlight(hit?.record);
  const note = field("lookup-note");
  if (hit) {
    note.textContent = "已找到" + label + "记录。";
    const source = [hit.subject.title, hit.record.batch, hit.record.key].join(" · ");
    display(label + "执行详情", source, hit.subject.detail);
    return;
  }
  note.textContent = matches.length ? "此 ID 有多个来源，请选择批次。" : "当前已导入的资料中未找到此 ID。";
  const options = field("lookup-options");
  for (const {record, subject} of matches) {
    const choice = element("li");
    const source = [record.batch, record.key, record.title].join(" · ");
    const href = "#" + [kind, subject.id, record.id].map(encodeURIComponent).join("/");
    choice.append(link(source, href));
    options.append(choice);
  }
  options.hidden = matches.length === 0;
  display(label + "查询", note.textContent, null);
}

function route() {
  let parts;
  try {
    parts = location.hash.slice(1).split("/").map(decodeURIComponent);
  } catch {
    parts = ["?"];
  }
  field("lookup-note").textContent = "";
  field("lookup-options").replaceChildren();
  field("lookup-options").hidden = true;
  field("return-case").hidden = true;
  const [key, id, owner] = parts;
  if (id && (key === "alert" || key === "incident")) showSubject(key, id, owner);
  else showCase(key);
}

field("lookup").addEventListener("submit", event => {
  event.preventDefault();
  const id = field("subject-id").value.trim();
  if (!id) {
    field("subject-id").focus();
    return;
  }
  const hash = "#" + field("subject-kind").value + "/" + encodeURIComponent(id);
  if (location.hash === hash) route();
  else location.hash = hash;
});
window.addEventListener("hashchange", route);
route();
</script></body></html>"""
