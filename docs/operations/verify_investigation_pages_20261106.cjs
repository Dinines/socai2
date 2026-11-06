'use strict';
// Offline readback of the three actual exports through the original page renderer.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '../..');
const pages = path.join(root, 'prototypes/security-pages-v2');
const out = path.join(__dirname, 'evidence/additional-tests-20261106/page-verification.json');
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
function load(data) {
  const s = {window: {addEventListener() {}}, document: {addEventListener() {}}, location: {hash: '#/cases'}, localStorage: {getItem: () => null}, structuredClone, URLSearchParams, clearInterval};
  vm.createContext(s);
  for (const name of ['icons', 'workspace-layout', 'data', 'replayed-alerts', 'alert-detail', 'workspace-model', 'workspace-view', 'investigation-data', 'alert-flow-workspace', 'investigation-graph', 'investigation-workspace', 'case-workflow', 'case-assistant', 'socai2-recorded-import']) {
    vm.runInContext(fs.readFileSync(path.join(pages, name + '.js'), 'utf8'), s);
  }
  s.window.socai2RecordedData = structuredClone(data);
  const original = fs.readFileSync(path.join(pages, 'app.js'), 'utf8');
  const anchor = 'readQueueLink();render();\n})();';
  if (!original.includes(anchor)) throw new Error('Renderer test binding changed');
  vm.runInContext(original.replace(anchor, 'window.api={store,ui,casePage,incidentPage,fullAlert,caseQueueRows};\n})();'), s);
  return {...s.window.api, s};
}
const reports = [];
for (const n of ['01', '02', '03']) {
  const batch = 'local-eval-20261106-' + n;
  const receipt = JSON.parse(fs.readFileSync(path.join(path.dirname(out), batch + '.json')));
  const db = JSON.parse(fs.readFileSync(path.join(root, receipt.export, 'database.json')));
  const generated = path.join(pages, 'socai2-recorded-' + batch + '.js');
  const sandbox = {window: {}}; vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(generated, 'utf8'), sandbox);
  const data = JSON.parse(JSON.stringify(sandbox.window.socai2RecordedData));
  const x = load(data), c = data.cases[0], checks = [], rendered = [];
  const check = (field, passed) => checks.push({field, passed: Boolean(passed)});
  const originalStore = JSON.stringify(x.store);
  check('cases.* preserved as sourceRecord', same(c.sourceRecord, db.cases[0]));
  check('case_alerts links', same(c.alertIds.slice().sort(), data.alerts.map(a => a.id).sort()));
  check('case_incidents links', same(c.incidentIds, data.incidents.map(i => i.id)));
  const assessment = db.case_assessments.find(a => a.id === db.cases[0].current_assessment_id);
  check('adopted conclusion exact', c.assessment.conclusion === assessment.conclusion);
  check('current assessment source exact', same(c.assessment.sourceRecord.assessment, assessment));
  check('case queue determination exact', x.caseQueueRows().find(q => q.id === c.id).determination === assessment.conclusion);
  check('missing independent evidence stays null', c.pageData.evidence.evidence_count === null && c.pageData.evidence.threat_count === null && data.evidence.length === 0);
  check('classification/due remain missing', c.sourceRecord.classification === null && c.due === null);
  for (const a of data.alerts) {
    check('alerts/' + a.sourceAlertId + ' source exact', same(a.sourceRecord, db.alerts.find(row => row.id === a.sourceAlertId)));
    const material = db.alert_materials.find(m => m.alert_id === a.sourceAlertId);
    check('alert_materials/' + material.id + ' raw body retained', same(a.detailMaterial.raw.material, material));
  }
  for (const r of data.runs) {
    check('runs/' + r.sourceRunId + ' source exact', same(r.sourceRecord.run, db.runs.find(row => row.id === r.sourceRunId)));
    check('runs/' + r.sourceRunId + ' steps retained', r.steps.length === db.run_steps.filter(s => s.run_id === r.sourceRunId).length);
    for (const a of r.artifacts) {
      const source = db.artifacts.find(row => row.id === a.sourceArtifactId);
      const {content_json, content_text, ...metadata} = source;
      const body = r.artifactBodies[a.id];
      check('artifacts/' + a.sourceArtifactId + ' metadata exact', same(a.sourceRecord, metadata));
      check('artifacts/' + a.sourceArtifactId + ' body exact', body?.format === 'json' ? same(body.content, content_json) : body?.format === 'text' ? body.content === content_text : content_json == null && content_text == null);
    }
  }
  const baseline = data.runs.find(r => r.investigationKind === 'baseline');
  const result = db.results.find(r => r.source_run_id === baseline.sourceRunId);
  check('results full body retained', same(baseline.sourceResult, result));
  check('graph source retained', baseline.savedGraphArtifactId.endsWith(result.graph_artifact_id));
  check('graph nodes/edges exact counts', baseline.savedGraphContext.nodes.length === receipt.graph[0].nodes && baseline.savedGraphContext.edges.length === receipt.graph[0].edges);
  function render(route, fn) {
    x.s.location.hash = route;
    const html = fn();
    check(route + ' renders', html.length > 100 && !/Invalid Date|>undefined<|>null<|未找到该 Case|未找到该事件/.test(html));
    rendered.push({route, html_sha256: crypto.createHash('sha256').update(html).digest('hex')});
    return html;
  }
  x.ui.caseId = c.id;
  for (const tab of ['case-info', 'story', 'overview', 'investigations', 'alerts', 'attack', 'evidence', 'tasks', 'activities', 'comments']) {
    const html = render('#/cases/' + c.id + '/' + tab, x.casePage);
    if (tab === 'case-info') {
      check('case-info actual current conclusion visible', html.includes(esc(assessment.conclusion)));
      check('case-info links both raw materials', data.alerts.every(a => html.includes('#/alerts/' + a.id + '/raw')));
      check('case-info missing evidence not fake zero', html.includes('独立证据条目') && html.includes('未记录'));
    }
    if (tab === 'alerts') check('case members both visible', data.alerts.every(a => html.includes(esc(a.title))));
  }
  for (const view of ['overview', 'process', 'tools', 'graphs', 'report', 'ledger']) render('#/cases/' + c.id + '/investigations?run=' + baseline.id + '&view=' + view, x.casePage);
  for (const i of data.incidents) {
    x.ui.incidentId = i.id;
    for (const tab of ['summary', 'attack', 'alerts', 'assets', 'activities']) render('#/incidents/' + i.id + '/' + tab, x.incidentPage);
  }
  for (const a of data.alerts) for (const tab of ['overview', 'timeline', 'raw', 'response']) render('#/alerts/' + a.id + '/' + tab, () => x.fullAlert(x.store.alerts.find(row => row.id === a.id)));
  check('rendering does not alter business records', JSON.stringify(x.store) === originalStore);
  reports.push({batch, generated_file: path.relative(root, generated), generated_sha256: hash(generated), database_sha256: receipt.database_sha256, checks, rendered, failures: checks.filter(c => !c.passed)});
}
const output = {created_at: new Date().toISOString(), mode: 'offline_actual_export_original_renderer', browser_check: 'separate', reports, check_count: reports.reduce((n, r) => n + r.checks.length, 0), rendered_count: reports.reduce((n, r) => n + r.rendered.length, 0), failure_count: reports.reduce((n, r) => n + r.failures.length, 0), source_sha256: Object.fromEntries(['app.js','case-workflow.js','socai2-recorded-import.js'].map(f => [f, hash(path.join(pages, f))]))};
fs.writeFileSync(out, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify({out, checks: output.check_count, rendered: output.rendered_count, failure_count: output.failure_count, failures: reports.map(r => ({batch: r.batch, failures: r.failures.slice(0, 3)}))}));
if (output.failure_count) process.exitCode = 1;
