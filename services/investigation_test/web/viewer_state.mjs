// Read lifecycle shared by the page and direct, explicitly controlled checks.
export function businessGate(batch, capabilities) {
  if (!capabilities.investigation_http) return '未配置调查 HTTP 来源。';
  // Direct subject discovery is bound to the configured environment, not a test ledger.
  if (!batch) return null;
  if (batch.mode !== 'live') return '归档批次：只读取登记证据，不查询当前业务环境。';
  if (batch.environment !== capabilities.investigation_http.environment_label)
    return '环境不一致：已阻止业务读取，请使用该批次对应的服务配置。';
  return null;
}
export function active(kind, value) {
  return ({task: ['accepted', 'running'], run: ['pending', 'running'],
    batch: ['planned', 'preparing', 'running']})[kind]?.includes(value) ?? false;
}
export function sameOriginRead(path, origin) {
  const url = new URL(path, origin);
  if (url.origin !== origin || !['/test-api/v1/', '/api/v1/socai2/', '/viewer/config.json']
    .some(prefix => url.pathname.startsWith(prefix))) throw new Error('拒绝非当前服务的读取链接');
  return url;
}
export function pageUrl(path, size, cursor, origin) {
  const url = sameOriginRead(path, origin);
  url.searchParams.set('limit', String(size));
  if (cursor) url.searchParams.set('cursor', cursor); else url.searchParams.delete('cursor');
  return url.pathname + url.search;
}
export function subjectPath(mapping) {
  const collection = {alert: 'alerts', incident: 'incidents', case: 'cases'}[mapping.subject_type];
  if (!collection || !mapping.subject_id) throw new Error('缺少业务主体身份');
  return `/api/v1/socai2/${collection}/${encodeURIComponent(mapping.subject_id)}`;
}
export function subjectListPath(type) {
  const collection = {case: 'cases', incident: 'incidents', alert: 'alerts'}[type];
  const sort = {case: 'business_updated_at', incident: 'last_activity_at', alert: 'event_time'}[type];
  if (!collection) throw new Error('未知业务主体类型');
  return `/api/v1/socai2/${collection}?sort_by=${sort}&sort_order=desc`;
}
export function subjectEntry(type, item) {
  const facts = type === 'case' ? item.case : item.facts;
  if (!facts?.id) throw new Error('主体列表缺少真实 ID');
  return {mapping: {subject_type: type, subject_id: facts.id}, subject: item,
    title: facts.title ?? ({case:'Case 调查', incident:'事件诊断', alert:'告警分诊'}[type])};
}
export function subjectHistory(mapping, items) {
  const seen = new Set();
  return items.map(item => {
    if (item.subject_type !== mapping.subject_type || item.subject_id !== mapping.subject_id || !item.run_id)
      throw new Error('执行目录包含其他主体或缺少 Run 身份');
    return {run: {...item, id:item.run_id}, mapping:{...mapping,run_id:item.run_id,task_id:item.task_id}, url:item.detail_url};
  }).filter(item => !seen.has(item.run.id) && seen.add(item.run.id));
}
export function runPath(mapping, runId = mapping.run_id) {
  return runId ? `${subjectPath(mapping)}/${mapping.subject_type === 'case' ? '' : 'analysis/'}runs/${encodeURIComponent(runId)}` : null;
}
export function boundResults(task, runId) {
  return (task?.results ?? []).filter(result => result.source_run_id === runId);
}
export function resumeVisible(isActive, interrupted, nested) {
  return !nested && (isActive || interrupted);
}
export class ReadScope {
  constructor() { this.generation = 0; this.controllers = new Set(); }
  reset() {
    this.generation++;
    for (const controller of this.controllers) controller.abort();
    this.controllers.clear();
    return this.generation;
  }
  current(generation) { return generation === this.generation; }
  async read(path, seconds, origin, fetcher = fetch) {
    const generation = this.generation;
    const controller = new AbortController();
    this.controllers.add(controller);
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, seconds * 1000);
    try {
      const response = await fetcher(sameOriginRead(path, origin), {
        method: 'GET', signal: controller.signal, cache: 'no-store', credentials: 'omit', redirect: 'error',
      });
      const raw = await response.text();
      if (!this.current(generation)) throw new DOMException('旧选择已取消', 'AbortError');
      if (!response.ok) throw new Error(`HTTP ${response.status}：${raw}`);
      let data;
      try { data = JSON.parse(raw); } catch { data = raw; }
      return {data, raw, observedAt: new Date().toISOString(), url: response.url || String(path)};
    } catch (error) {
      if (timedOut) throw new Error('读取超时：未获得完整响应');
      throw error;
    } finally { clearTimeout(timer); this.controllers.delete(controller); }
  }
}
export class VisiblePoll {
  constructor(delay, visible = () => !document.hidden) { this.delay = delay; this.visible = visible; this.timer = null; }
  stop() { clearTimeout(this.timer); this.timer = null; }
  schedule(isActive, refresh) {
    this.stop();
    if (isActive && this.visible()) this.timer = setTimeout(() => { this.timer = null; refresh(); }, this.delay * 1000);
  }
}
