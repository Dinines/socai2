"""Case-first investigation workbench with optional local database refresh."""
import html
import json


def render_index(records: list[dict], controls_url: str | None = None, comparison_url: str | None = None) -> str:
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    controls = f'<a href="{html.escape(controls_url, quote=True)}">受控对照 ↗</a>' if controls_url else ""
    comparison = (f'<a href="{html.escape(comparison_url, quote=True)}">告警输入输出对比 ↗</a>'
                  if comparison_url else "")
    return _PAGE.replace("<!--controls-->", controls + comparison).replace("<!--records-->", payload)


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
.live-status,.list-actions{padding:7px 12px}.live-status{color:#53695f;font-size:12px}.live-status:empty{display:none}.list-actions{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}.manual-id{padding:8px 12px;border-top:1px solid #e5eae7}.manual-id summary,#archive>summary{cursor:pointer}#archive .panel-head::after{content:"▸";color:#53695f}#archive[open] .panel-head::after{content:"▾"}#case-count{margin-left:auto}.manual-id form{margin-top:8px}button:disabled{cursor:wait;opacity:.65}
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
<main><aside class="left"><section id="live-panel" class="panel" aria-labelledby="live-heading" hidden><div class="panel-head"><h2 id="live-heading">最近更新的 Case</h2><button type="button" id="refresh-list">刷新</button></div>
<div class="list"><table><thead><tr><th>案件 / Case ID</th><th>更新时间<br>（北京时间）</th></tr></thead><tbody id="live-rows"></tbody></table></div>
<p id="list-status" class="live-status" role="status"></p><div class="list-actions"><small>每 15 秒检查更新</small><button type="button" id="more-cases" hidden>加载更多</button></div>
<details class="manual-id"><summary>按 Case ID 打开</summary><form class="input-line" id="live-search"><input aria-label="Case ID" id="live-id" autocomplete="off" placeholder="输入完整 Case UUID" required spellcheck="false"><button type="submit">打开</button></form></details></section>
<details class="panel" id="archive" open><summary class="panel-head"><h2 id="case-heading">已导出的 Case</h2><span id="case-count" class="hint"></span></summary>
<div class="list"><table><thead><tr><th>案件 / 批次</th><th>最近执行更新<br>（北京时间）</th></tr></thead><tbody id="case-rows"></tbody></table><p id="no-records" class="empty" hidden>尚无 Case 调查记录。</p></div></details>
<section class="panel lookup"><h2>告警与事件查询</h2><form id="lookup"><label>按 <select id="subject-kind" aria-label="查询类型"><option value="alert">告警 ID</option><option value="incident">事件 ID</option></select> 查询</label>
<div class="input-line"><input id="subject-id" aria-label="主体 ID" placeholder="粘贴完整 ID" required autocomplete="off" spellcheck="false"><button type="submit">查找</button></div></form><p id="lookup-note" class="hint" role="status"></p><ul id="lookup-options" hidden></ul></section></aside>
<section class="panel"><div class="detail-head"><h2 id="detail-title">Case 执行详情</h2><nav><a id="return-case" hidden>返回 Case</a><a id="open-detail" target="_blank" rel="noopener" hidden>单独打开 ↗</a></nav></div>
<p id="selected-summary" class="summary" aria-live="polite"></p><p id="case-status" class="live-status" role="status"></p><iframe id="case-detail" title="调查执行详情" hidden></iframe></section></main>
<noscript><p class="empty">请启用 JavaScript 以选择 Case 或按 ID 查询。</p></noscript>
<script type="application/json" id="audit-records"><!--records--></script>
<script>
"use strict";
const field = id => document.getElementById(id);
const online = {enabled: false, listBusy: false, detailBusy: false, active: null, shown: null, depth: 1, cursor: null, items: new Map()};
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
    field("return-case").href = online.enabled && !cases.some(item => item.id === lastCase.id)
      ? "#live/" + encodeURIComponent(lastCase.scope_id) : "#" + encodeURIComponent(lastCase.id);
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
  online.active = null;
  field("case-status").textContent = "";
  if (key === "live" && id && uuid.test(id)) {
    showLive(id.toLowerCase());
  } else if (id && (key === "alert" || key === "incident")) showSubject(key, id, owner);
  else showCase(key);
  markLiveRow();
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
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

async function api(path, options) {
  const response = await fetch("/_workbench/" + path, {cache: "no-store", ...options});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "读取失败，请稍后重试。");
  return result;
}

function markLiveRow() {
  for (const row of field("live-rows").rows) {
    const selected = row.dataset.id === online.active;
    row.classList.toggle("selected", selected);
    if (selected) row.querySelector("a").setAttribute("aria-current", "true");
    else row.querySelector("a").removeAttribute("aria-current");
  }
}

function renderLiveList(items) {
  const body = field("live-rows");
  const focusId = body.contains(document.activeElement) ? document.activeElement.closest("tr")?.dataset.id : null;
  body.replaceChildren();
  for (const item of items.values()) {
    const row = body.insertRow();
    row.dataset.id = item.case_id;
    const href = "#live/" + encodeURIComponent(item.case_id);
    const anchor = link("", href);
    anchor.className = "case-link";
    anchor.append(element("strong", item.title || "未命名 Case"), element("small", item.case_id, "batch"));
    row.insertCell().append(anchor);
    const stamp = Date.parse(item.updated_at);
    row.insertCell().textContent = Number.isFinite(stamp) ? clock.format(stamp) : "未记录";
    row.addEventListener("click", event => { if (!event.target.closest("a")) location.hash = href; });
    if (item.case_id === focusId) anchor.focus({preventScroll: true});
  }
  markLiveRow();
}

async function refreshList(more = false) {
  if (!online.enabled || online.listBusy || document.hidden || (more && !online.cursor)) return;
  online.listBusy = true;
  field("refresh-list").disabled = true;
  field("more-cases").disabled = true;
  try {
    const items = more ? new Map(online.items) : new Map();
    let cursor = more ? online.cursor : null;
    const depth = more ? 1 : online.depth;
    for (let i = 0; i < depth; i++) {
      const page = await api("cases" + (cursor ? "?cursor=" + encodeURIComponent(cursor) : ""));
      for (const item of page.cases) items.set(item.case_id, item);
      cursor = page.next_cursor;
      if (!cursor) break;
    }
    if (JSON.stringify([...items]) !== JSON.stringify([...online.items])) renderLiveList(items);
    online.items = items;
    online.cursor = cursor;
    if (more) online.depth++;
    field("more-cases").hidden = !cursor;
    field("list-status").textContent = items.size ? "" : "当前数据库中还没有 Case。";
    if (!location.hash && items.size) {
      history.replaceState(null, "", "#live/" + encodeURIComponent(items.keys().next().value));
      route();
    }
  } catch (error) {
    field("list-status").textContent = "Case 列表更新失败。" + error.message;
  } finally {
    online.listBusy = false;
    field("more-cases").disabled = false;
    field("refresh-list").disabled = false;
  }
}

function liveSummary(record) {
  return [record.title, record.scope_id, (record.logs?.run_count ?? "—") + " 轮 Case 调查",
    states[record.state] || record.state, delivery[record.delivery_state] || record.delivery_state].filter(Boolean).join(" · ");
}

function showLive(id) {
  online.active = id;
  highlight(null);
  const saved = records.find(r => r.scope_id === id && r.id === online.shown?.record.id)
    || records.find(r => r.scope_id === id);
  if (saved) {
    lastCase = saved;
    display("Case 执行详情", liveSummary(saved), saved.detail);
  } else {
    display("Case 执行详情", online.items.get(id)?.title || id, null);
  }
  if (!online.enabled) {
    field("case-status").textContent = "当前只可浏览已导出的记录。";
    return;
  }
  field("case-status").textContent = "正在读取数据库中的执行记录…";
  refreshDetail();
}

async function refreshDetail() {
  const id = online.active;
  if (!online.enabled || online.detailBusy || document.hidden || !id) return;
  online.detailBusy = true;
  const body = {case_id: id};
  if (online.shown?.record.scope_id === id) body.version = online.shown.version;
  try {
    const result = await api("refresh", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    if (online.active !== id) return;
    const record = result.record;
    // Keep the published relative URLs so switching views and static lookups use the same files.
    const index = records.findIndex(item => item.id === record.id);
    if (index >= 0) records[index] = record;
    else records.push(record);
    lastCase = record;
    online.shown = {record, version: result.version};
    display("Case 执行详情", liveSummary(record), record.detail);
    const stamp = Date.parse(result.snapshot_at);
    field("case-status").textContent = Number.isFinite(stamp) ? "数据库快照 · " + clock.format(stamp) + "（北京时间）" : "已读取数据库记录。";
  } catch (error) {
    if (online.active === id) field("case-status").textContent = "此 Case 更新失败。" + error.message;
  } finally {
    online.detailBusy = false;
    if (online.active && online.active !== id) refreshDetail();
  }
}

function checkUpdates() {
  if (!document.hidden && online.enabled) {
    refreshList();
    refreshDetail();
  }
}

field("live-search").addEventListener("submit", event => {
  event.preventDefault();
  const input = field("live-id");
  const id = input.value.trim();
  if (!uuid.test(id)) {
    input.setCustomValidity("请输入完整的 Case UUID。");
    input.reportValidity();
    return;
  }
  const hash = "#live/" + id.toLowerCase();
  if (location.hash === hash) route();
  else location.hash = hash;
});
field("live-id").addEventListener("input", event => event.target.setCustomValidity(""));
field("more-cases").addEventListener("click", () => refreshList(true));
field("refresh-list").addEventListener("click", checkUpdates);
document.addEventListener("visibilitychange", checkUpdates);

async function connectWorkbench() {
  if (!["http:", "https:"].includes(location.protocol)) return;
  try {
    const status = await api("status");
    online.enabled = Boolean(status.enabled ?? status.configured);
    if (!online.enabled) return;
    field("live-panel").hidden = false;
    if (!location.hash || location.hash.startsWith("#live/")) field("archive").open = false;
    field("list-status").textContent = "正在读取最近的 Case…";
    checkUpdates();
    window.setInterval(checkUpdates, 15000);
  } catch {
    // The same HTML can be opened directly or served as a static export.
  }
}
route();
connectWorkbench();
</script></body></html>"""
