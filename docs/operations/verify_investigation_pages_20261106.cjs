'use strict';
// Offline readback of the three actual exports through the original page renderer.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const pages = path.join(root, 'prototypes/security-pages-v2');
const out = path.join(__dirname, 'evidence/additional-tests-20261106/page-verification.json');
// With --handoff, replay committed snapshots without writing a receipt or using services.
const args = process.argv.slice(2);
const handoff = args.length === 1 && args[0] === '--handoff';
if (args.length && !handoff) throw new Error('Usage: node verify_investigation_pages_20261106.cjs [--handoff]');
const evidence = path.join(__dirname, 'evidence');
const archive = path.join(root, 'deliverables/investigation-validation-20261106/socai2-investigation-tests-20261106.zip');
const pageScripts = handoff ? new Set([...fs.readFileSync(path.join(pages, 'index.html'), 'utf8')
  .matchAll(/<script\b[^>]*\bsrc="\.\/([^"?]+)(?:\?[^"]*)?"/gi)].map(match => match[1])) : null;
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function archivedJson(member, expectedHash) {
  const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
  const raw = execFileSync(python, ['-c',
    'import sys,zipfile; sys.stdout.buffer.write(zipfile.ZipFile(sys.argv[1]).read(sys.argv[2]))',
    archive, member], {maxBuffer: 32 * 1024 * 1024});
  if (crypto.createHash('sha256').update(raw).digest('hex') !== expectedHash) throw new Error('Snapshot hash mismatch: ' + member);
  return JSON.parse(raw.toString('utf8'));
}
function recordedData(file) {
  if (handoff && ![path.basename(file), 'app.js', 'socai2-recorded-import.js'].every(name => pageScripts.has(name))) {
    throw new Error('Page entry does not load the recorded sample and its renderer: ' + path.basename(file));
  }
  const sandbox = {window: {}};
  vm.runInNewContext(fs.readFileSync(file, 'utf8'), sandbox);
  return structuredClone(sandbox.window.socai2RecordedData);
}
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
function load(data) {
  const s = {window: {addEventListener() {}}, document: {addEventListener() {}}, location: {hash: '#/cases'}, localStorage: {getItem: () => null}, structuredClone, URLSearchParams, clearInterval};
  vm.createContext(s);
  for (const name of ['icons', 'workspace-layout', 'data', 'replayed-alerts', 'alert-detail', 'workspace-model', 'workspace-view', 'investigation-data', 'alert-flow-workspace', 'investigation-graph', 'investigation-workspace', 'case-workflow', 'case-assistant', 'socai2-recorded-import']) {
    vm.runInContext(fs.readFileSync(path.join(pages, name + '.js'), 'utf8'), s);
  }
  s.window.socai2RecordedData = structuredClone(data);
  const original = fs.readFileSync(path.join(pages, 'app.js'), 'utf8').replace(/\r\n/g, '\n');
  const anchor = 'readQueueLink();render();\n})();';
  if (!original.includes(anchor)) throw new Error('Renderer test binding changed');
  vm.runInContext(original.replace(anchor, 'window.api={store,ui,casePage,incidentPage,fullAlert,caseQueueRows};\n})();'), s);
  return {...s.window.api, s};
}
const reports = [];
for (const n of ['01', '02', '03']) {
  const batch = 'local-eval-20261106-' + n;
  const receipt = JSON.parse(fs.readFileSync(path.join(path.dirname(out), batch + '.json')));
  const db = handoff ? archivedJson(receipt.export + '/database.json', receipt.database_sha256) : JSON.parse(fs.readFileSync(path.join(root, receipt.export, 'database.json')));
  const generated = path.join(pages, 'socai2-recorded-' + batch + '.js');
  const data = recordedData(generated);
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
  if (handoff) {
    const source = db.case_assessment_sources.find(row => row.tenant_id === c.sourceTenantId &&
      row.case_id === c.sourceCaseId && row.assessment_id === assessment.id && row.result_id === result.id);
    check('adopted assessment links this baseline result', assessment.origin === 'model' &&
      assessment.validity === 'accepted' && assessment.conclusion === result.conclusion &&
      source && c.assessment.sourceRecord.sources.some(row => same(row, source)));
  }
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
    if (handoff && tab === 'investigations') {
      const members = db.case_alerts.filter(row => row.tenant_id === c.sourceTenantId && row.case_id === c.sourceCaseId);
      const incidents = db.case_incidents.filter(row => row.tenant_id === c.sourceTenantId && row.case_id === c.sourceCaseId);
      const expected = db.runs.filter(run => run.tenant_id === c.sourceTenantId && (
        (run.kind === 'baseline' && run.case_id === c.sourceCaseId) ||
        (run.kind === 'alert_basic' && members.some(row => row.alert_id === run.alert_id)) ||
        (run.kind === 'incident_diagnosis' && incidents.some(row => row.incident_id === run.incident_id))));
      const history = x.s.window.investigationWorkspaceModel.forCase(x.store, c);
      check('history contains exactly one C, two A and one I', same(expected.map(r => r.kind).sort(),
        ['alert_basic', 'alert_basic', 'baseline', 'incident_diagnosis']));
      check('history Run identities match database scope', same(history.map(r => r.sourceRunId).sort(),
        expected.map(r => r.id).sort()));
      const links = [...html.matchAll(/href="[^"]*\/investigations\?([^"]+)"/g)]
        .map(match => new URLSearchParams(match[1]))
        .filter(params => params.get('view') === 'overview').map(params => params.get('run'));
      check('rendered history links open these exact Runs', same(links.sort(), history.map(r => r.id).sort()));
    }
    if (handoff && tab === 'attack') {
      const nodes = (html.match(/class="ug-node /g) || []).length;
      const edges = (html.match(/class="ug-hit"/g) || []).length;
      check('case graph renders the source baseline Run', html.includes('data-investigation-graph data-run-id="' + baseline.id + '"'));
      check('rendered graph nodes match saved projection', nodes > 0 && nodes === receipt.graph[0].nodes);
      check('rendered graph edges match saved projection', edges > 0 && edges === receipt.graph[0].edges);
    }
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
function verifyContractPages() {
  const receipt = JSON.parse(fs.readFileSync(path.join(evidence, 'page-data-20261106/summary.json'), 'utf8'));
  const member = receipt.local_readback + '/case-page-data.json';
  const snapshots = archivedJson(member, receipt.sha256[member]);
  const data = recordedData(path.join(pages, 'socai2-recorded-page-data-20261106.js'));
  const x = load(data), queue = x.caseQueueRows(), checks = [], rendered = [];
  const check = (field, passed) => checks.push({field, passed: Boolean(passed)});
  check('four saved contract samples, no Runs', snapshots.length === 4 && data.cases.length === 4 && data.runs.length === 0);
  const classifications = {true_positive: 'True positive', false_positive: 'False positive', informational: 'Informational'};
  for (const {case_id, page_data} of snapshots) {
    const c = data.cases.find(row => row.sourceRecord.id === case_id);
    const row = queue.find(item => item.id === c.id);
    const field = name => case_id + ' ' + name;
    const e = page_data.evidence;
    check(field('queue classification'), row.classification === (classifications[page_data.classification] ?? 'Not set'));
    check(field('queue due time'), page_data.due_at ? Date.parse(row.due) === Date.parse(page_data.due_at) : row.due === '未设置');
    check(field('queue determination'), row.determination === (page_data.determination ?? '未设置'));
    check(field('contract assessment provenance'), page_data.assessment ?
      c.assessment.sourceRecord.assessment.id === page_data.assessment.id && page_data.assessment.origin === 'legacy' :
      !c.assessment && page_data.determination === null);
    check(field('evidence and threats'), c.pageData.evidence.state === e.state &&
      c.pageData.evidence.evidence_count === e.evidence_count && row.threatCount === e.threat_count);
    for (const tab of ['case-info', 'evidence']) {
      const route = '#/cases/' + c.id + '/' + tab;
      x.s.location.hash = route;
      x.ui.caseId = c.id;
      const html = x.casePage();
      check(field(tab + ' renders this case'), html.includes(esc(c.title)) && !/Invalid Date|>undefined<|>null</.test(html));
      if (tab === 'case-info') {
        check(field('rendered evidence count or missing'), html.includes('独立证据条目</span><b>' + (e.evidence_count ?? '未记录') + '</b>'));
        if (page_data.determination) check(field('rendered conclusion'), html.includes(esc(page_data.determination)));
      }
      if (tab === 'evidence') check(field('evidence entries match stored titles'),
        e.entries.every(entry => html.includes(esc(entry.title))));
      rendered.push({route, html_sha256: crypto.createHash('sha256').update(html).digest('hex')});
    }
  }
  return {batch: receipt.batch, checks, rendered, failures: checks.filter(item => !item.passed)};
}
if (handoff) reports.push(verifyContractPages());
const output = {created_at: new Date().toISOString(), mode: handoff ? 'read_only_committed_exports_original_renderer' : 'offline_actual_export_original_renderer', browser_check: 'separate', reports, check_count: reports.reduce((n, r) => n + r.checks.length, 0), rendered_count: reports.reduce((n, r) => n + r.rendered.length, 0), failure_count: reports.reduce((n, r) => n + r.failures.length, 0), source_sha256: Object.fromEntries(['app.js','case-workflow.js','socai2-recorded-import.js'].map(f => [f, hash(path.join(pages, f))]))};
if (!handoff) fs.writeFileSync(out, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify({out: handoff ? null : out, checks: output.check_count, rendered: output.rendered_count, failure_count: output.failure_count, failures: reports.map(r => ({batch: r.batch, failures: r.failures.slice(0, 3)}))}));
if (output.failure_count) process.exitCode = 1;
