import {active, businessGate, boundResults, pageUrl, runPath, subjectPath, subjectListPath, subjectEntry, subjectHistory, resumeVisible, ReadScope, VisiblePoll} from './viewer_state.mjs';

import {executionFlow, matchingAttempt, matchingExchange, stateLabel, timeLabel} from './execution_flow.mjs';
import {loadCaseSources, readSourceExecution} from './frozen_sources.mjs';
import {classifySources, classifyRunSources, registeredRun, sourceCaption} from './test_sources.mjs';
import {parseRunLink, checkLinkEnvironment, chooseRun, runLinkSearch, checkRunIdentity, linkedSubject} from './viewer_links.mjs';

const $ = id => document.getElementById(id);
const origin = location.origin;
const listScope = new ReadScope(), tabScope = new ReadScope(), detailScope = new ReadScope();
const subjectScope = new ReadScope(), sourceScope = new ReadScope();
let config, caps, poll, batch, tab = 'executions', tabCursor, listCursor, selected = null, tabFilter = null;
let view = 'subjects', subjectType = 'case', subjectCursor = null, currentSubject = null;
let requestedRun = null, reportTarget = null, reportLinkError = null;
const subjects = new Map(), testSources = new Map();
const roundSources = new Map();
const subjectNames = {case:'Case', incident:'事件', alert:'告警'};
const subjectKey = mapping => `${mapping.subject_type}:${mapping.subject_id}`;
let detailObserved = null, tabObserved = null;
let selectedActive = false, interruptedDetail = false, interruptedTab = false, nested = false;
let interruptedSubjects = false;
const value = v => v == null ? '未记录' : typeof v === 'object' ? JSON.stringify(v) : String(v);
function node(tag, text, cls) {
  const el = document.createElement(tag);
  if (text != null) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}
function button(text, action) {
  const b = node('button', text); b.type = 'button';
  b.onclick = async () => {
    b.disabled = true;
    try { await action(); } catch (error) { showError(error); } finally { b.disabled = false; }
  };
  return b;
}
function badge(text) {
  const css = ['failed', 'unknown', 'stale', 'issues_recorded'].includes(text) ? 'bad' :
    ['partial', 'uncertain', 'deferred', 'skipped', 'not_assessed'].includes(text) ? 'warn' : '';
  return node('span', value(stateLabel(text)), `tag ${css}`);
}
function facts(rows) {
  const dl = node('dl', null, 'facts');
  for (const [key, val] of rows) { const pair = node('div'); pair.append(node('dt', key), node('dd', value(val))); dl.append(pair); }
  return dl;
}
function rawDetails(data, title = '查看完整 JSON', open = false) {
  const d = node('details'); d.append(node('summary', title));
  // Large originals are formatted only when explicitly expanded; no truncation.
  d.addEventListener('toggle', () => {
    if (d.open && d.children.length === 1) d.append(node('pre', typeof data === 'string' ? data : JSON.stringify(data, null, 2)));
  });
  d.open=open;
  return d;
}
function card(title, status) {
  const c = node('article', null, 'card'), head = node('div', null, 'section-heading');
  head.append(node('h3', title)); if (status != null) head.append(badge(status)); c.append(head); return c;
}
function lines(title, items) {
  const box = node('div'); box.append(node('h4', title));
  const ul = node('ul', null, 'item-list');
  for (const item of items ?? []) ul.append(node('li', value(item)));
  box.append(ul.children.length ? ul : node('p', '无记录', 'muted')); return box;
}
function notice(text, error = false) { return node('div', text, `notice${error ? ' error' : ''}`); }
function showError(error, observed = selected ? detailObserved : tabObserved) {
  if (error.name === 'AbortError') return;
  const target = batch || currentSubject ? $('read-status') : $('global-error');
  target.hidden = false; target.className = 'notice error';
  target.textContent = `读取失败：${error.message}\n${observed ? `保留上次成功观察（${observed}），以下内容可能已过期。` : '当前选择尚无成功观察。'} 未回落历史快照。`;
}
function observed(at) {
  $('read-status').hidden = false; $('read-status').className = 'read-stamp';
  $('read-status').textContent = `读取时间：${timeLabel(at)} · ${stateLabel(view === 'subjects' ? 'live' : batch?.batch.mode)}`;
}
async function read(scope, path, business = false) {
  if (business) { const reason = businessGate(view === 'subjects' ? null : batch?.batch, caps); if (reason) throw new Error(reason); }
  return scope.read(path, config.request_timeout_seconds, origin);
}
function page(path, cursor) { return pageUrl(path, config.page_size, cursor, origin); }
function stopDetail() {
  poll.stop(); detailScope.reset(); selected = null; selectedActive = false;
  interruptedDetail = false; nested = false; detailObserved = null; $('inspection').hidden = true;
}
function evidenceButtons(ids) {
  const actions = node('div', null, 'actions');
  for (const id of ids ?? []) {
    const item = batch.evidence.find(e => e.id === id);
    if (item) actions.append(button(`证据：${item.label}`, () => selectDetail({kind: 'evidence', item})));
  }
  return actions;
}
function businessView() {
  view = 'subjects'; tab = 'executions';
  $('empty-selection').hidden = true; $('batch-panel').hidden = false;
  $('batch-panel').classList.add('execution-mode'); $('management-panel').hidden = true;
  $('show-executions').setAttribute('aria-pressed','true'); $('show-management').setAttribute('aria-pressed','false');
  $('more-records').hidden = true; $('global-error').hidden = true; $('read-status').hidden = true;
}
function markSubjectSources() {
  for (const group of subjects.values()) {
    group.button.querySelector('.test-execution-mark')?.remove();
    const key=subjectKey(group.mapping),facts=group.subject.facts;
    const direct=group.mapping.subject_type==='alert' && facts?.connector_type &&
      classifySources([facts],[group.mapping.subject_id],config.test_source_prefixes).matched>0;
    const frozen=[...(roundSources.get(key)?.values()??[])].some(r=>r.matched>0);
    const label=direct?'测试数据':frozen?'含测试数据':testSources.has(key)?'关联测试记录':null;
    if(label)group.button.append(node('span',label,'test-execution-mark'));
  }
}
async function loadSubjects(append = false, autoSelect = true) {
  const generation = append ? subjectScope.generation : subjectScope.reset(), type = subjectType;
  if (!append) {
    businessView(); stopDetail(); tabScope.reset(); currentSubject = null;
    subjects.clear(); subjectCursor = null;
    $('subject-list').replaceChildren(node('p','正在读取业务列表…','muted'));
    $('tab-content').replaceChildren();
  }
  $('subject-list-title').textContent = `${subjectNames[type]}列表`;
  document.querySelectorAll('[data-subject-type]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.subjectType===type)));
  let response;
  try { response = await read(subjectScope,page(subjectListPath(type),append ? subjectCursor : null),true); }
  catch(error) {
    if(subjectScope.current(generation)&&!append) {
      $('subject-list').replaceChildren(node('p','列表读取失败，请刷新重试。','muted'));
      $('more-subjects').hidden=true;
    }
    throw error;
  }
  if (!subjectScope.current(generation)) return;
  if (!append) $('subject-list').replaceChildren();
  for (const item of response.data.items) {
    const group = subjectEntry(type,item), key = subjectKey(group.mapping);
    if (subjects.has(key)) continue;
    const b = button('',()=>{clearReportTarget();return openSubject(group);}); b.className='subject-choice'; b.dataset.subjectId=group.mapping.subject_id;
    b.setAttribute('aria-current','false');
    b.append(node('strong',group.title),node('small',group.mapping.subject_id,'identity'));
    group.button=b; subjects.set(key,group); $('subject-list').append(b);
  }
  subjectCursor=response.data.next_cursor; $('more-subjects').hidden=!subjectCursor;
  markSubjectSources();
  if (!subjects.size) {
    $('subject-list').append(node('p',`当前没有${subjectNames[type]}。`,'muted'));
    if(autoSelect)$('tab-content').replaceChildren(notice(`当前环境尚无${subjectNames[type]}记录。此列表直接来自业务 HTTP，不需要测试账本。`));
  } else if (autoSelect && !currentSubject && view === 'subjects') await openSubject(subjects.values().next().value,false);
}
async function openSubject(group, scroll = false, preferredRun = null) {
  businessView(); stopDetail(); const generation=tabScope.reset();
  currentSubject=group;requestedRun=preferredRun;
  document.querySelectorAll('[data-subject-id]').forEach(b=>b.setAttribute('aria-current',String(b===group.button)));
  $('tab-content').replaceChildren(node('p','正在读取对象与执行轮次…','muted'));
  const mapping=group.mapping, path=subjectPath(mapping);
  const results=await Promise.allSettled([
    read(tabScope,path,true),
    allPages(tabScope,`/api/v1/socai2/analysis-runs?subject_type=${mapping.subject_type}&subject_id=${encodeURIComponent(mapping.subject_id)}`),
    allPages(tabScope,`${path}/analysis-tasks`),
  ]);
  if (!tabScope.current(generation)) return;
  const [subjectResult,runResult,taskResult]=results;
  const subject=subjectResult.status==='fulfilled'?subjectResult.value.data:group.subject??{};
  if(subjectResult.status==='fulfilled') {
    const actual=subjectEntry(mapping.subject_type,subject);
    if(subjectKey(actual.mapping)!==subjectKey(mapping))throw new Error('主体详情身份与指定目标不一致');
    group.title=actual.title;
  }
  const history=runResult.status==='fulfilled'?subjectHistory(mapping,runResult.value):[];
  const tasks=taskResult.status==='fulfilled'?taskResult.value:[];
  const summary=card(group.title);
  summary.append(facts([['类型',subjectNames[mapping.subject_type]],['ID',mapping.subject_id],
    ['执行记录',runResult.status==='fulfilled'?`${history.length} 轮`:'读取失败'],
    ['任务记录',taskResult.status==='fulfilled'?tasks.length:'读取失败']]));
  if(subject.member_count!=null)summary.append(node('p',`当前关联 ${subject.member_count} 条告警；每轮以该轮保存的输入为准。`,'muted small'));
  const properties=node('details');properties.append(node('summary','对象属性'),rawDetails(subject,'展开完整对象属性'));summary.append(properties);
  for(const [i,result] of results.entries()) if(result.status==='rejected')
    summary.append(notice(`${['对象属性','执行目录','任务目录'][i]}读取失败：${result.reason.message}。其余已读取内容保留。`,true));
  const taskList=node('details',null,'subject-tasks');taskList.append(node('summary',`任务记录（${taskResult.status==='fulfilled'?tasks.length:'读取失败'}）`));
  for(const task of tasks) {
    const b=button('',()=>selectDetail({kind:'task',mapping:{...mapping,task_id:task.task_id}}));b.className='task-choice';
    const intent={initial:'首轮分析',check:'变化检查',rerun:'重新分析'}[task.intent]??task.intent;
    b.append(node('strong',`${intent} · ${stateLabel(task.status)}`),node('small',`${timeLabel(task.submitted_at)} · ${task.reason_code??(task.latest_run_id?'已有执行':'尚无 Run')}`),node('small',task.task_id,'identity'));taskList.append(b);
  }
  if(!tasks.length)taskList.append(node('p',taskResult.status==='fulfilled'?'当前没有任务记录。':'任务目录未读到，不能推断没有任务。','muted'));
  summary.append(taskList); $('tab-content').replaceChildren(summary);
  tabObserved=new Date().toISOString();observed(tabObserved);
  if(preferredRun && subjectResult.status==='rejected') {
    $('tab-content').append(notice(`指定主体 ${mapping.subject_id} 未读到；目标Run ${preferredRun} 未打开，未改选其他执行。`,true));return;
  }
  if(preferredRun && runResult.status==='rejected') {
    $('tab-content').append(notice(`指定Run ${preferredRun} 的执行目录读取失败；未改选其他轮次。`,true));return;
  }
  let chosen;
  try {chosen=chooseRun(history,preferredRun);}
  catch(error) {$('tab-content').append(notice(error.message,true));return;}
  if(history.length) {
    requestedRun=chosen.run.id;
    await selectDetail({kind:'run',mapping:chosen.mapping,mappings:history.map(h=>h.mapping),url:chosen.url??runPath(chosen.mapping),history,subject,title:group.title,scroll});
  } else {
    $('tab-content').append(notice(runResult.status==='fulfilled'?'尚无实际执行轮次；已受理或无变化跳过的任务仍可从任务记录查看。':'执行目录读取失败，未使用其他对象或旧快照替代。'));
    const waiting=tasks.find(t=>active('task',t.status));
    if(waiting)await selectDetail({kind:'task',mapping:{...mapping,task_id:waiting.task_id},scroll:false});
  }
}
async function openReportTarget(target) {
  businessView();stopDetail();
  $('tab-content').replaceChildren(notice(`报告目标：${subjectNames[target.mapping.subject_type]} ${target.mapping.subject_id} · Run ${target.mapping.run_id}`));
  try {checkLinkEnvironment(target,caps);}
  catch(error) {$('tab-content').append(notice(error.message,true));return;}
  const group=linkedSubject(target,subjects);
  await openSubject(group,false,target.mapping.run_id);
}
function clearReportTarget() {
  reportTarget=null;reportLinkError=null;requestedRun=null;
  window.history.replaceState(null,'',location.pathname);
}
function rememberRun(mapping) {
  if(view!=='subjects'||subjectKey(mapping)!==subjectKey(currentSubject?.mapping??{}))return;
  requestedRun=mapping.run_id;
  const search=runLinkSearch(mapping,caps.investigation_http.environment_label);
  reportTarget=parseRunLink(search);reportLinkError=null;
  window.history.replaceState(null,'',location.pathname+search);
}
async function loadSubjectNavigation() {
  const target=reportTarget,error=reportLinkError,generation=subjectScope.generation+1;
  await loadSubjects(false,!target&&!error).catch(showError);
  if(!subjectScope.current(generation))return;
  if(error) {
    businessView();$('tab-content').replaceChildren(notice(`报告链接无效：${error}。未打开默认执行。`,true),node('p',location.search,'identity'));
  } else if(target)await openReportTarget(target);
}
async function loadTestSources() {
  const generation=sourceScope.reset();
  const rows=await allPages(sourceScope,'/test-api/v1/batches');
  const next=new Map();
  for(const row of rows) {
    if(businessGate(row.batch,caps))continue;
    const record=(await read(sourceScope,row.detail_url)).data;
    const operations=await allPages(sourceScope,record.links.operations);
    const exchangeEvidence=record.evidence.find(e=>e.id==='http-exchanges');
    let exchanges=[];
    if(exchangeEvidence) {
      try { const response=await read(sourceScope,exchangeEvidence.content_url);
        if(response.data.schema==='socai2.test-http-exchanges.v1')exchanges=response.data.exchanges;
      } catch(error) { if(error.name==='AbortError')throw error; }
    }
    for(const op of operations) for(const mapping of op.mappings) {
      const key=subjectKey(mapping);
      if(!next.has(key))next.set(key,{batches:new Set(),exchanges:[],operations:[]});
      const item=next.get(key);item.batches.add(row.batch.id);
      if(!item.operations.includes(op))item.operations.push(op);
      for(const exchange of exchanges)if(!item.exchanges.includes(exchange))item.exchanges.push(exchange);
    }
  }
  if(!sourceScope.current(generation))return;
  testSources.clear();for(const [key,value]of next)testSources.set(key,value);
  markSubjectSources();
  $('test-source-status').textContent=`已读取 ${rows.length} 份测试记录；同一业务对象仅列一次。测试记录不决定业务执行状态。`;
  if(view==='subjects'&&selected?.kind==='run'&&!nested)await refreshDetail();
}
async function loadBatches(append = false) {
  const generation = append ? listScope.generation : listScope.reset();
  const response = await read(listScope, page('/test-api/v1/batches', append ? listCursor : null));
  if (!listScope.current(generation)) return;
  if (!append) $('batch-list').replaceChildren();
  for (const row of response.data.items) {
    const b = button('', () => selectBatch(row.detail_url)); b.className = 'batch-choice'; b.dataset.batch = row.batch.id;
    b.setAttribute('aria-current', String(batch?.batch.id === row.batch.id));
    b.append(node('strong', row.batch.title), node('small', `${stateLabel(row.batch.mode)} · ${stateLabel(row.batch.execution_state)}`));
    $('batch-list').append(b);
  }
  if (!response.data.total) {
    $('batch-list').append(node('p', '尚无已发布测试批次。', 'muted'));
    if(view==='management')$('tab-content').replaceChildren(notice('没有测试记录；仍可从左侧查看业务对象。'));
  }
  listCursor = response.data.next_cursor; $('more-batches').hidden = !listCursor;
  if (view==='management' && !batch && response.data.items.length) await selectBatch(response.data.items[0].detail_url);
}
function renderBatchHeader() {
  $('empty-selection').hidden = true; $('batch-panel').hidden = false;
  $('batch-title').textContent = batch.batch.title;
  $('batch-tags').replaceChildren(...[batch.batch.mode, batch.batch.provenance, batch.batch.execution_state, batch.batch.quality_status].map(badge));
  $('batch-observation').textContent = `${batch.batch.id} · 环境 ${batch.batch.environment} · 账本修订 ${batch.revision} · 更新 ${batch.batch.updated_at}`;
  document.querySelectorAll('[data-batch]').forEach(b => b.setAttribute('aria-current', String(b.dataset.batch === batch.batch.id)));
}
async function selectBatch(url) {
  view='management';
  const refresh = batch?.detail_url === url;
  stopDetail(); const generation = tabScope.reset();
  $('read-status').hidden = true;
  if (!refresh) { tabObserved = null; $('tab-content').replaceChildren(node('p', '正在读取所选批次…', 'muted')); }
  const response = await read(tabScope, url);
  if (!tabScope.current(generation)) return;
  batch = response.data; renderBatchHeader(); await loadTab(tab==='executions'?'cases':tab, false, refresh);
}
function tabPath() {
  const path = batch.links[{quality: 'quality-issues'}[tab] ?? tab];
  return tab === 'operations' && tabFilter ? `${path}?use_case_id=${encodeURIComponent(tabFilter.use_case_id)}` : path;
}
async function loadTab(name, append = false, preserve = false, filter = null) {
  if(name==='executions') { if(currentSubject)return openSubject(currentSubject,false,requestedRun); return loadSubjectNavigation(); }
  view='management';
  if(!batch) { $('test-records').open=true; await loadBatches();return; }
  stopDetail(); const generation = append ? tabScope.generation : tabScope.reset();
  tab = name;
  $('batch-panel').classList.toggle('execution-mode', name === 'executions');
  $('management-panel').hidden = name === 'executions';
  $('show-executions').setAttribute('aria-pressed', String(name === 'executions'));
  $('show-management').setAttribute('aria-pressed', String(name !== 'executions'));
  if (!append && !preserve) tabFilter = filter;
  document.querySelectorAll('[data-tab]').forEach(b => b.setAttribute('aria-selected', String(b.dataset.tab === tab)));
  if (!append) {
    tabCursor = null;
    if (!preserve) { tabObserved = null; $('tab-content').replaceChildren(node('p', '正在读取…', 'muted')); }
  }
  $('more-records').hidden = true;
  try {
    $('tab-help').textContent = {cases:'测试计划：想验证什么，以及实际观察是否符合预期。', operations:'发起记录：每次操作对应的后台任务、尝试和执行。', preparation:'准备记录：测试环境与输入材料是否就绪。', quality:'质量问题：引用错误、正文待核等问题；与执行是否结束分开记录。', evidence:'核对记录：测试过程中保存的回执和证据原件。'}[tab];
    let response;
    if (tab === 'evidence') response = {data: {items: batch.evidence}, observedAt: new Date().toISOString()};
    else response = await read(tabScope, tab === 'preparation' ? tabPath() : page(tabPath(), append ? tabCursor : null));
    if (!tabScope.current(generation)) return;
    const fragment = document.createDocumentFragment();
    if (tab === 'preparation') {
      const p = response.data.preparation, c = card('环境准备与清理记录', p.status);
      c.append(facts([['清理方式', p.cleanup_mode], ['观察时间', p.observed_at]]), node('p', p.summary), lines('资源', p.resources), evidenceButtons(p.evidence_ids)); fragment.append(c);
    } else {
      if (tabFilter && !append) fragment.append(node('h3', `用例 ${tabFilter.id} 的操作`));
      for (const item of response.data.items) {
        if (tab === 'operations' && tabFilter && item.case_id !== tabFilter.id) continue;
        fragment.append(renderLedgerItem(item));
      }
      if (!append && !response.data.items.length) fragment.append(notice('本栏目没有登记记录；不表示业务或质量已通过。'));
      tabCursor = response.data.next_cursor; $('more-records').hidden = !tabCursor;
    }
    if (!append) $('tab-content').replaceChildren(fragment); else $('tab-content').append(fragment);
    tabObserved = response.observedAt; observed(tabObserved); scheduleBatch();
  } catch (error) { if (tabScope.current(generation)) showError(error); }
}
async function allPages(scope, path, identity=null) {
  const generation = scope.generation, items = [], seen = new Set();
  let cursor = null;
  do {
    const response = await read(scope, page(path,cursor), path.startsWith('/api/'));
    if (!scope.current(generation)) throw new DOMException('选择已改变','AbortError');
    if(identity && ['subject_type','subject_id','run_id'].some(key=>response.data[key]!==identity[key]))
      throw new Error('读取目录与指定主体或Run不一致');
    items.push(...response.data.items);
    cursor = response.data.next_cursor;
    if (cursor && seen.has(cursor)) throw new Error('目录分页未向前推进');
    seen.add(cursor);
  } while (cursor);
  return items;
}
function renderLedgerItem(item) {
  if (tab === 'cases') {
    const c = card(`${item.use_case_id} · ${item.scenario_id}`, item.status);
    c.append(node('p', item.id, 'identity'), lines('预期行为', item.expected), lines('实际观察', item.actual));
    c.append(button('查看本用例操作', () => showCaseOperations(item)), evidenceButtons(item.evidence_ids)); return c;
  }
  if (tab === 'operations') return operationCard(item);
  if (tab === 'quality') {
    const c = card(`${item.stage} · ${item.category}`, item.status);
    c.append(facts([['用例', item.case_id], ['Run', item.run_id], ['是否阻断流程', item.affects_flow]]), node('p', item.description, 'prose'), evidenceButtons(item.evidence_ids)); return c;
  }
  const c = card(item.label);
  c.append(facts([['大小（bytes）', item.size], ['SHA256', item.sha256], ['原始来源', item.source_ref]]), button('查看登记原件', () => selectDetail({kind: 'evidence', item}))); return c;
}
function showCaseOperations(testCase) { return loadTab('operations', false, false, testCase); }
function operationCard(item) {
  const c = card(item.intent, item.execution_state);
  c.append(facts([['操作', item.id], ['测试用例', item.case_id], ['发生时间', item.occurred_at]]));
  const reason = businessGate(batch.batch, caps);
  for (const mapping of item.mappings) {
    c.append(node('p', `${mapping.subject_type} · ${mapping.subject_id}`, 'identity'));
    if (reason) { c.append(notice(reason)); continue; }
    const actions = node('div', null, 'actions');
    if (mapping.task_id) actions.append(button('查看任务与尝试', () => selectDetail({kind: 'task', mapping})));
    if (mapping.run_id) actions.append(button('查看本操作 Run', () => selectDetail({kind: 'run', mapping, url: runPath(mapping), task: null})));
    if (!actions.children.length) actions.append(node('p', '尚未登记任务或 Run。', 'muted'));
    c.append(actions);
  }
  c.append(evidenceButtons(item.evidence_ids)); return c;
}
function scheduleBatch() {
  poll.schedule(view==='management' && !selected && batch?.batch.mode === 'live' && active('batch', batch.batch.execution_state), async () => {
    const generation = tabScope.generation;
    try {
      const response = await read(tabScope, batch.detail_url);
      if (!tabScope.current(generation) || selected) return;
      batch = response.data; renderBatchHeader(); await loadTab(tab, false, true);
    } catch (error) { if (tabScope.current(generation)) showError(error); }
  });
}
async function selectDetail(selection) {
  poll.stop(); detailScope.reset(); selected = selection; detailObserved = null;
  selectedActive = false; interruptedDetail = false; nested = false;
  if(selection.kind==='run')rememberRun(selection.mapping);
  $('inspection').hidden = false; $('inspection-title').textContent = {task:'任务与执行尝试',run:'执行详情',result:'调查结果',evidence:'登记测试证据',content:'原件正文'}[selection.kind] ?? '调查记录';
  $('inspection-body').replaceChildren(node('p', '正在读取所选记录…', 'muted'));
  await refreshDetail();
  if (selection.scroll !== false) $('inspection').scrollIntoView({behavior: 'smooth', block: 'start'});
}
async function refreshDetail() {
  const generation = detailScope.reset(), selection = selected;
  if (!selection) return;
  poll.stop(); nested = false; interruptedDetail = false;
  try {
    const response = await fetchSelection(selection);
    if (!detailScope.current(generation)) return;
    const fragment = renderSelection(selection, response);
    $('inspection-body').replaceChildren(fragment); detailObserved = response.observedAt; observed(detailObserved);
    selectedActive = Boolean(response.isActive);
    poll.schedule(response.isActive, refreshDetail);
  } catch (error) { if (detailScope.current(generation)) showError(error, detailObserved); }
}
async function fetchSelection(s) {
  if (s.kind === 'task') {
    const response = await read(detailScope, `${subjectPath(s.mapping)}/analysis-tasks/${s.mapping.task_id}`, true);
    return {...response, isActive: active('task', response.data.status)};
  }
  if (s.kind === 'run') {
    const response = await read(detailScope, s.url, true);
    // Run summaries may be capped; directory links are the only paginated source.
    const directory = s.mapping.subject_type === 'case' ? response.data : (await read(detailScope, `${s.url}/trace`, true)).data;
    checkRunIdentity(s.mapping,response.data,directory);
    const [steps,artifacts]=await Promise.all([allPages(detailScope,directory.steps_url),allPages(detailScope,directory.artifacts_url)]);
    let result=response.data.result;
    let resultUrl;
    if(s.mapping.subject_type==='case') {
      const id=response.data.result_ids?.[0];
      if(id) {resultUrl=`${subjectPath(s.mapping)}/results/${encodeURIComponent(id)}`;result=(await read(detailScope,resultUrl,true)).data.result;}
      if(result && result.source_run_id!==response.data.run.id) throw new Error('结果与当前执行不一致');
    }
    const boundMapping=(s.mappings??[s.mapping]).find(m=>m.run_id===response.data.run.id);
    let task;
    if(boundMapping?.task_id)task=(await read(detailScope,`${subjectPath(s.mapping)}/analysis-tasks/${boundMapping.task_id}`,true)).data;
    if(!matchingAttempt(task,response.data.run.id)) {
      const tasks=await allPages(detailScope,`${subjectPath(s.mapping)}/analysis-tasks`);
      task=tasks.find(t=>matchingAttempt(t,response.data.run.id));
      if(!task) { const candidate=tasks.find(t=>t.latest_run_id===response.data.run.id);if(candidate)task=(await read(detailScope,`${subjectPath(s.mapping)}/analysis-tasks/${candidate.task_id}`,true)).data; }
    }
    const sources=testSources.get(subjectKey(s.mapping))?.exchanges??batch?.exchanges;
    const exchange=matchingExchange(sources??[],s.mapping,response.data.run.id,task?.task_id);
    const upstream=s.mapping.subject_type==='case'?await loadCaseSources({run:response.data.run,artifacts,
      previousUrl:response.data.previous_run_url,readBody:url=>read(detailScope,url,true),readPages:(url,identity)=>allPages(detailScope,url,identity)}):null;
    const sourceClassification=await classifyRunSources({mapping:s.mapping,run:directory.run??response.data.run,artifacts,
      context:upstream?.current?.context,readBody:url=>read(detailScope,url,true),prefixes:config.test_source_prefixes});
    return {...response,directory,steps,artifacts,result,upstream,sourceClassification,context:{task,exchange,resultUrl,runUrl:s.url,observedAt:response.observedAt},isActive:active('run',response.data.run.state)};
  }
  return read(detailScope, s.kind === 'evidence' ? s.item.content_url : s.url, s.kind !== 'evidence');
}
function renderSelection(s, response) {
  const {data} = response, box = node('div');
  if (s.kind === 'task') {
    const c = card(`任务 · ${data.intent}`, data.status);
    c.append(facts([['任务', data.task_id], ['来源', data.source], ['原因', data.reason_code], ['下次重试', data.next_retry_at], ['开始', data.started_at], ['结束', data.ended_at]]));
    if (!data.attempts.length) c.append(notice(data.status === 'accepted' ? '任务已受理，等待产生执行尝试；当前没有 Run。' : '当前任务没有执行尝试或 Run。'));
    box.append(c);
    for (const attempt of data.attempts) {
      const a = card(`第 ${attempt.attempt_no} 次尝试`, attempt.outcome ?? attempt.local_state);
      a.append(facts([['Run', attempt.run_id], ['本地状态', attempt.local_state], ['错误代码', attempt.error_code], ['错误环节', attempt.error_stage], ['可重试', attempt.retryable]]));
      if (attempt.run_url && attempt.run_id) a.append(button('打开此尝试 Run', () => selectDetail({kind:'run', mapping:{...s.mapping,run_id:attempt.run_id}, url:attempt.run_url, task:data})));
      else a.append(node('p', '此尝试尚无关联 Run，保留准备/错误记录。', 'muted'));
      a.append(rawDetails(attempt)); box.append(a);
    }
    if (s.mapping.run_id) box.append(button('打开账本登记 Run', () => selectDetail({kind:'run',mapping:s.mapping,url:runPath(s.mapping),task:data})));
    box.append(rawDetails(data, '查看完整任务记录')); return box;
  }
  if (s.kind === 'run') {
    const run=data.run, header=node('div',null,'execution-heading');
    const key=subjectKey(s.mapping),classification=response.sourceClassification;
    if(!roundSources.has(key))roundSources.set(key,new Map());
    roundSources.get(key).set(run.id,classification);markSubjectSources();
    const caption=sourceCaption(classification,registeredRun(testSources.get(key)?.operations??[],{...s.mapping,run_id:run.id}));
    if(caption)box.append(node('div',caption,'test-execution-mark'));
    if(classification?.state==='unknown')box.append(notice(`测试来源未确认：${classification.reason??'本轮部分告警缺少来源字段'}。其他已读取流程正常展示。`));
    header.append(node('h3',s.title ?? run.title ?? '分析执行'));
    const history=s.history ?? [{run}];
    const label=node('label',s.mapping.subject_type==='alert'?'分诊记录：':`共 ${history.length} 轮 · 查看：`,'run-choice'), select=node('select'); select.setAttribute('aria-label','选择执行轮次');
    const entries=history.filter(item=>item.run);
    for(const [i,item] of entries.entries()) {
      const option=node('option',`${s.mapping.subject_type==='alert' ? '告警分诊' : `第${entries.length-i}轮`} · ${timeLabel(item.run.started_at ?? item.run.requested_at)} · ${stateLabel(item.run.state)}`);
      option.value=item.run.id;option.selected=item.run.id===run.id;select.append(option);
    }
    select.onchange=()=>{
      const entry=history.find(item=>item.run?.id===select.value);
      const mapping={...s.mapping,...entry?.mapping,run_id:select.value};
      selectDetail({...s,mapping,url:entry?.url??runPath(mapping),task:null,scroll:false});
    };
    label.append(select);header.append(label);box.append(header);
    box.append(facts([['执行状态',stateLabel(run.state)],['交付情况',stateLabel(run.delivery_state)],['开始时间',timeLabel(run.started_at)],['结束时间',timeLabel(run.ended_at)]]));
    if(data.input_member_count!=null)box.append(node('p',`本轮输入 ${data.input_member_count} 条告警 · 当前关联 ${data.current_member_count} 条告警`,'scope-summary small'));
    if(data.input_selection) box.append(node('p',`本轮选入 ${data.input_selection.selected_count} / ${data.input_selection.total_member_count} 条成员；实际覆盖 ${data.analysis_coverage?.analyzed_count ?? '未记录'} 条。`,'scope-summary'));
    const ticket=detailScope.generation;
    box.append(executionFlow({run,steps:response.steps,artifacts:response.artifacts,result:response.result,context:response.context,upstream:response.upstream,
      readSource:entry=>readSourceExecution(entry,url=>read(detailScope,url,true),(url,identity)=>allPages(detailScope,url,identity)),
      readBody:url=>read(detailScope,url,true),current:()=>detailScope.current(ticket),onInspect:pauseParentPolling,
      ui:{node,button,facts,rawDetails,notice,resultCard,contentCard}}));
    const extra=node('details',null,'execution-extra');extra.append(node('summary','轮次比较、当前采用与完整记录'));
    if(s.mapping.subject_type==='case') extra.append(comparison(data,run),button('读取当前采用与新鲜度',()=>inlineRead(extra,subjectPath(s.mapping),renderCurrentCase)));
    extra.append(rawDetails(data,'完整执行记录（Run）'));
    for(const [key,label] of [['steps','步骤'],['artifacts','原件']]) if(response.directory[`${key}_url`]) extra.append(button(`查看完整${label}目录`,()=>loadDirectory(extra,response.directory[`${key}_url`],key)));
    box.append(extra);return box;
  }
  if (s.kind === 'result') {
    if (data.result?.source_run_id !== s.runId) throw new Error('结果来源 Run 与选择不一致');
    box.append(resultCard(data.result), comparison(data, data.result), rawDetails(data)); return box;
  }
  if (s.kind === 'evidence') {
    const c = card(s.item.label); c.append(facts([['来源', s.item.source_ref], ['SHA256', s.item.sha256], ['大小（bytes）', s.item.size]]), rawDetails(data, '展开完整登记原件'), download(response.raw, `${s.item.id}.json`)); box.append(c); return box;
  }
  box.append(contentCard(data, response.raw, s.label)); return box;
}
function resultCard(result) {
  const c = card('本轮分析结果', result?.validation_state ?? result?.state);
  if (!result) { c.append(notice('没有保存的结果。')); return c; }
  c.append(facts([['业务判定', stateLabel(result.conclusion_state ?? result.verdict)], ['交付情况', stateLabel(result.delivery_state)], ['结构校验', stateLabel(result.validation_state)]]));
  if(result.error_code) c.append(notice(`结果错误：${result.error_code}`, true));
  c.append(node('p', result.conclusion ?? result.summary ?? result.rationale ?? '未保存结论正文。', 'prose'));
  if (result.closing_note) c.append(node('p', result.closing_note, 'prose'));
  if (result.findings) c.append(lines('发现', result.findings.map(f => f.statement)));
  c.append(rawDetails(result, '查看完整结果及依据')); return c;
}
function comparison(outer, record) {
  const c = card('上一轮比较');
  c.append(node('p', record.comparison_context == null ? '未记录比较上下文。' : record.comparison_context.state === 'initial' ? '首轮 initial：没有上一轮可比较。' : `比较状态：${value(record.comparison_context.state)}`));
  if (record.comparison_context) c.append(facts([['比较原因', record.comparison_context.reason_code],
    ['上一轮 Run', record.comparison_context.previous_run_id], ['比较结果', record.comparison_context.comparison_result_id]]));
  for (const [key,label] of [['previous_run_url','读取上一轮 Run'],['comparison_result_url','读取比较结果']]) if (outer[key]) c.append(button(label, () => inlineRead(c, outer[key], data => rawDetails(data, label))));
  return c;
}
function renderCurrentCase(data) {
  const c = card('当前 Case 采用状态与新鲜度'), assessment = data.current_assessment;
  c.append(facts([['Case', data.case.id], ['当前判断', data.case.current_assessment_id], ['当前成员数', data.member_count], ['采用有效性', assessment?.value?.validity], ['输入新鲜度', assessment?.input_freshness?.state], ['变化原因', assessment?.input_freshness?.reasons]]));
  c.append(rawDetails(assessment, '查看当前判断来源')); return c;
}
async function inlineRead(container, url, renderer) {
  pauseParentPolling();
  const generation = detailScope.generation;
  const response = await read(detailScope, url, true);
  if (!detailScope.current(generation)) return;
  const content = node('div', null, 'content-panel'); content.append(node('p', `观察：${response.observedAt}`, 'body-status'), renderer(response.data)); container.append(content);
}
async function loadDirectory(container, path, kind) {
  pauseParentPolling();
  const generation = detailScope.generation;
  const response = await read(detailScope, page(path), true);
  if (!detailScope.current(generation)) return;
  const box = node('section'); box.append(node('h3', `完整${kind === 'steps' ? '步骤' : '工件'}目录`, 'subheading'));
  const count = node('p', '', 'muted'), items = node('div'); box.append(count, items); container.append(box);
  let loaded = 0;
  function append(data) {
    for (const item of data.items) items.append(kind === 'steps' ? stepCard(item) : artifactCard(item, data));
    loaded += data.items.length; count.textContent = `已读取 ${loaded} / ${data.total} · 观察 ${data.observed_at}`;
    if (data.next_cursor) {
      const more = button(`加载更多${kind === 'steps' ? '步骤' : '工件'}`, async () => {
        const next = await read(detailScope, page(path, data.next_cursor), true);
        if (!detailScope.current(generation)) return;
        more.remove(); append(next.data);
      }); box.append(more);
    }
  }
  append(response.data);
}
function stepCard(item) {
  const c = card(`${item.seq}. ${item.stage_code} · ${item.name}`, item.state);
  c.append(facts([['类型', item.kind], ['步骤', item.id], ['父步骤', item.parent_step_id], ['重试来源', item.retry_of_step_id], ['错误', item.error?.code]]));
  if (item.usage) c.append(facts([['输入 tokens', item.usage.input_tokens], ['输出 tokens', item.usage.output_tokens], ['费用', item.usage.cost], ['计费状态', item.usage.cost_state]]));
  for (const ref of item.artifact_refs ?? []) {
    const a = node('div', null, 'content-panel'); a.append(node('p', `${ref.role} · 来源 ${ref.subject_type} ${ref.subject_id}`, 'identity'), node('p', `Run ${ref.run_id} · 工件 ${ref.artifact_id}`, 'identity'));
    if (ref.content_url) a.append(bodyButton(a, ref.content_url, `${ref.role} 原件`)); c.append(a);
  }
  c.append(rawDetails(item, '查看完整步骤记录')); return c;
}
function artifactCard(item, directory) {
  const c = card(`${item.kind} · ${item.schema_version}`, item.material_state);
  c.append(facts([['工件', item.id], ['所属主体', `${directory.subject_type} ${directory.subject_id}`], ['来源 Run', item.run_id], ['步骤', item.step_id], ['大小（bytes）', item.size_bytes], ['SHA256', item.sha256]]));
  if (item.content_url) c.append(bodyButton(c, item.content_url, item.kind));
  else c.append(notice('目录未返回正文链接。'));
  return c;
}
function bodyButton(container, url, label) {
  const b = button('读取完整正文', async () => {
    pauseParentPolling();
    const generation = detailScope.generation, response = await read(detailScope, url, true);
    if (!detailScope.current(generation)) return;
    container.append(contentCard(response.data, response.raw, label)); b.remove();
  }); return b;
}
function pauseParentPolling() {
  poll.stop(); nested = true;
  if (selectedActive) $('read-status').textContent += ' · 阅读目录/正文期间暂停父 Run 轮询；可手动刷新。';
}
function download(raw, filename) {
  return button('下载完整 HTTP 响应', () => {
    const url = URL.createObjectURL(new Blob([raw], {type:'application/json;charset=utf-8'})), a = node('a');
    a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 0);
  });
}
function contentCard(data, raw, label) {
  const c = node('div', null, 'content-panel'), meta = data.artifact ?? data.metadata ?? {};
  c.append(node('h4', label ?? '完整原件'), facts([['正文可用性', data.availability], ['原始主体', meta.case_id ? `case ${meta.case_id}` : meta.incident_id ? `incident ${meta.incident_id}` : meta.alert_id ? `alert ${meta.alert_id}` : null], ['原始 Run', meta.run_id], ['原件摘要', meta.sha256]]));
  if (data.availability !== 'available') c.append(notice('正文未标记 available；不能据 HTTP 200 认定原件完整可用。'));
  const content = data.content_json;
  if (content?.raw?.choices) for (const choice of content.raw.choices) {
    c.append(facts([['模型结束原因', choice.finish_reason], ['原答序号', choice.index]]), node('pre', choice.message?.content ?? '未记录正文'));
  }
  if (content?.input_selection) c.append(facts([['冻结选入条数', content.input_selection.selected_count], ['冻结总成员数', content.input_selection.total_member_count], ['选入策略', content.input_selection.policy]]));
  for (const [incidentId, context] of Object.entries(content?.incidents ?? {})) {
    const scope = context.diagnosis_scope; if (!scope) continue;
    const source = card('C1 使用的事件诊断来源');
    source.append(facts([['原事件', incidentId], ['原 Run', scope.source_run_id], ['原输入工件', scope.input_artifact_id], ['原事件冻结选入/覆盖', `${scope.input_selection?.selected_count ?? '未记录'} / ${scope.analysis_coverage?.analyzed_count ?? '未记录'}`],
      ['本案选入/覆盖交集', `${scope.case_selected_alert_ids?.length ?? '未记录'} / ${scope.case_covered_alert_ids?.length ?? '未记录'}`], ['冻结输入摘要', scope.source_fingerprint]]));
    if (scope.source_run_id && scope.input_artifact_id) source.append(button('追溯原事件输入', () => loadSource(source, scope, incidentId)));
    c.append(source);
  }
  if (data.content_text != null) c.append(node('pre', data.content_text));
  if (content != null) c.append(rawDetails(content, '展开完整原件内容'));
  c.append(rawDetails(data, '查看完整 HTTP 包装与元数据'), download(raw, `${meta.id ?? 'response'}.json`)); return c;
}
async function loadSource(container, scope, incidentId) {
  const generation = detailScope.generation, path = `/api/v1/socai2/analysis-runs/${encodeURIComponent(scope.source_run_id)}/artifacts`;
  let cursor = null;
  do {
    const response = await read(detailScope, page(path, cursor), true);
    if (!detailScope.current(generation)) return;
    if (response.data.subject_type !== 'incident' || response.data.subject_id !== incidentId || response.data.run_id !== scope.source_run_id) throw new Error('来源目录主体或 Run 不一致');
    const item = response.data.items.find(a => a.id === scope.input_artifact_id);
    if (item) {
      if (item.sha256 !== scope.source_fingerprint) throw new Error('冻结输入摘要与来源工件不一致');
      const body = await read(detailScope, item.content_url, true);
      if (!detailScope.current(generation)) return;
      container.append(notice('以下是原事件的冻结输入，属于跨 Run 业务来源；不表示 Case 上一轮比较。'), contentCard(body.data, body.raw, '原事件冻结输入')); return;
    }
    cursor = response.data.next_cursor;
  } while (cursor);
  throw new Error('完整来源目录中未找到登记的输入工件');
}

async function start() {
  // Bootstrap has no business connection. Subsequent reads use explicit profile timeout.
  const response = await fetch('/viewer/config.json', {cache:'no-store', credentials:'omit'});
  if (!response.ok) throw new Error(`页面配置 HTTP ${response.status}`);
  config = await response.json(); poll = new VisiblePoll(config.poll_interval_seconds);
  caps = (await read(listScope, '/test-api/v1/capabilities')).data;
  try {reportTarget=parseRunLink(location.search);if(reportTarget)subjectType=reportTarget.mapping.subject_type;}
  catch(error) {reportLinkError=error.message;}
  $('service-info').textContent = `测试服务 ${caps.service_version} · 页面 ${caps.viewer_version}\n环境 ${caps.environment_label} · ${caps.investigation_http ? `HTTP 合同 ${caps.investigation_http.contract_sha256}` : '未配置业务 HTTP'}`;
  $('viewer-version').textContent = `调查执行工作台 ${config.viewer_version} · 只读`;
  $('show-executions').onclick = () => loadTab('executions').catch(showError);
  $('show-management').onclick = () => loadTab('cases').catch(showError);
  $('subject-types').onclick = event => {
    const b=event.target.closest('[data-subject-type]');if(!b)return;
    clearReportTarget();subjectType=b.dataset.subjectType;loadSubjects().catch(showError);
  };
  $('reload-subjects').onclick = () => loadSubjectNavigation().catch(showError);
  $('more-subjects').onclick = () => loadSubjects(true).catch(showError);
  $('reload-batches').onclick = () => { loadBatches().catch(showError); loadTestSources().catch(testSourceError); };
  $('more-batches').onclick = () => loadBatches(true).catch(showError);
  $('more-records').onclick = () => loadTab(tab, true);
  $('batch-tabs').onclick = event => { const b = event.target.closest('[data-tab]'); if (b) loadTab(b.dataset.tab); };
  $('refresh-selection').onclick = () => {
    if(view==='subjects')return (currentSubject?openSubject(currentSubject,false,requestedRun):loadSubjectNavigation()).catch(showError);
    return selected?refreshDetail():selectBatch(batch.detail_url).catch(showError);
  };
  $('close-inspection').onclick = () => { stopDetail(); scheduleBatch(); };
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      poll.stop(); interruptedDetail = detailScope.controllers.size > 0; interruptedTab = tabScope.controllers.size > 0;
      interruptedSubjects=subjectScope.controllers.size>0;
      tabScope.reset(); detailScope.reset(); subjectScope.reset();
    } else if(interruptedSubjects) {interruptedSubjects=false;loadSubjectNavigation().catch(showError);}
    else if(view==='subjects'&&interruptedTab&&currentSubject) {interruptedTab=false;openSubject(currentSubject,false,requestedRun).catch(showError);}
    else if (selected && resumeVisible(selectedActive, interruptedDetail, nested)) refreshDetail();
    else if (view==='management' && !selected && batch) {
      if (interruptedTab) { interruptedTab = false; loadTab(tab, false, true); } else scheduleBatch();
    }
  });
  await Promise.allSettled([loadSubjectNavigation().catch(showError),loadBatches().catch(testSourceError),loadTestSources().catch(testSourceError)]);
}
function testSourceError(error) {
  if(error.name==='AbortError')return;
  $('test-source-status').textContent=`测试记录读取失败：${error.message}。业务对象和按冻结告警来源识别的标识仍可独立查阅。`;
}
start().catch(showError);
