"""Local-only node inspector; resolve saved records lazily without duplicating evidence."""

PANEL = """
<aside id="node-inspector" class="node-inspector" aria-labelledby="inspector-title">
<div class="inspector-heading"><span class="inspector-eyebrow">节点详情</span>
<h3 id="inspector-title">选择左侧节点</h3><p id="inspector-context" class="quiet"></p>
<p id="inspector-notice" role="status">点击流程中的阶段、模型或查询，查看实际保存的输入与输出。</p></div>
<div id="inspector-tabs" class="inspector-tabs" aria-label="详情内容" hidden>
<button type="button" data-view="overview" aria-pressed="true">概览与原因</button>
<button type="button" data-view="prompt" aria-pressed="false">提示词</button>
<button type="button" data-view="input" aria-pressed="false">输入</button>
<button type="button" data-view="output" aria-pressed="false">输出</button>
<button type="button" data-view="raw" aria-pressed="false">原始记录</button></div>
<div id="inspector-content" class="inspector-content" tabindex="0" aria-label="节点详情正文"></div>
</aside>
"""

STYLE = """
main.workbench-detail{max-width:1840px;padding-inline:clamp(12px,2vw,32px)}
.flow-workspace{display:grid;grid-template-columns:minmax(360px,5fr) minmax(460px,7fr);gap:24px;align-items:start}
.flow-navigation{min-width:0}.flow-navigation .flow-modules{margin-top:0}
.flow-navigation .flow-choice{display:block}.flow-navigation .flow-choice select{display:block;width:100%;margin-top:4px}
.flow-navigation .flow-lane{grid-template-columns:minmax(130px,36%) minmax(0,1fr);gap:12px;padding-block:7px}
.flow-navigation .flow-branches::before{left:-13px;width:12px}
.flow-navigation .flow-lanes{position:relative}.flow-navigation .flow-lanes::before{content:"";position:absolute;top:22px;bottom:22px;left:calc(18% - 2px);width:2px;background:var(--spine)}
.flow-navigation .flow-lane::after{display:none}
button.flow-node{font-family:inherit;text-align:left;cursor:pointer}
.flow-node:hover,.flow-node:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.flow-node[aria-current=true]{outline:2px solid #173f33;outline-offset:2px;box-shadow:0 0 0 4px #e8f1ed}
.node-inspector{position:sticky;top:16px;min-width:0;border:1px solid #c5d6cc;border-radius:10px;background:#fbfdfb;
display:flex;flex-direction:column;max-height:calc(100vh - 32px);min-height:430px;overflow:hidden}
.inspector-heading{flex-shrink:0;padding:16px 18px 12px;border-bottom:1px solid #d9e5dd;background:#f3f8f5;overflow:auto;max-height:32vh}
.inspector-eyebrow{font-size:11px;letter-spacing:.12em;color:#557565}.inspector-heading h3{font-size:18px;margin:3px 0 6px}
.inspector-heading p{font-size:12px;overflow-wrap:anywhere}.inspector-heading .inspector-failure{color:#8a302b;font-weight:600}
.inspector-tabs{display:flex;flex-shrink:0;flex-wrap:wrap;gap:4px;padding:10px 12px;border-bottom:1px solid #d9e5dd}
.inspector-tabs button,.inspector-related{border:1px solid #c5d6cc;background:white;border-radius:5px;color:#315c4e;padding:5px 9px;font:inherit;font-size:12px;cursor:pointer}
.inspector-tabs button[aria-pressed=true]{background:#234f42;color:white;border-color:#234f42}
.inspector-content{padding:14px 18px 20px;overflow:auto;min-height:0;overflow-wrap:anywhere;font-size:13px}
.inspector-content:empty{padding:0}.inspector-content h4{font-size:14px;margin:16px 0 7px}.inspector-content h4:first-child{margin-top:0}
.inspector-content pre{font-size:12px;max-height:none;margin:6px 0 16px;background:#eef4f0}
.inspector-content dl{grid-template-columns:7em minmax(0,1fr)}.inspector-content a{font-size:12px}
.inspector-related{display:block;width:100%;text-align:left;margin:6px 0}
.inspector-error{border-left:3px solid #c67970;padding:8px 10px;background:#fff0ec;margin:8px 0}
.inspector-error pre{background:transparent;margin-bottom:0;padding:0}
.inspector-empty{padding:14px;background:#f0f5f2;border-radius:6px;color:#536c60}
@media(max-width:980px){.flow-workspace{grid-template-columns:minmax(0,1fr);gap:18px}.node-inspector{position:static;max-height:80vh;min-height:320px}.inspector-heading{max-height:none}.flow-navigation .flow-choice select{width:auto}}
@media(max-width:520px){.flow-navigation .flow-lane{grid-template-columns:minmax(102px,35%) minmax(0,1fr)}.inspector-heading,.inspector-content{padding:12px}.inspector-tabs{padding:8px}.inspector-content dl{grid-template-columns:5.5em minmax(0,1fr)}}
"""

SCRIPT = r"""
const inspector = document.getElementById('node-inspector');
const inspectorTitle = document.getElementById('inspector-title');
const inspectorContext = document.getElementById('inspector-context');
const inspectorNotice = document.getElementById('inspector-notice');
const inspectorTabs = document.getElementById('inspector-tabs');
const inspectorContent = document.getElementById('inspector-content');
const recordElements = [...document.querySelectorAll('[data-record-kind]')];
const artifactElements = new Map(recordElements.filter(el => el.dataset.recordKind === 'artifact').map(el => [el.dataset.recordId, el]));
const stepElements = new Map(recordElements.filter(el => el.dataset.recordKind === 'step').map(el => [el.dataset.recordId, el]));
const parsedRecords = new WeakMap();
let selection = null;
function savedRecord(el) {
    if (!el) return null;
    if (!parsedRecords.has(el)) {
        const pre = el.querySelector(':scope > pre[data-record-json], :scope > details > pre[data-record-json]');
        parsedRecords.set(el, pre ? JSON.parse(pre.textContent) : null);
    }
    return parsedRecords.get(el);
}
function element(tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
}
function display(value) { return typeof value === 'string' ? value : JSON.stringify(value, null, 2); }
function reasonDescription(value) {
    const code = typeof value === 'string' ? value : value?.code;
    return {
        source_member_mismatch: '引用来源的成员范围与声明范围不一致。',
        execution_receipt_is_not_evidence: '把查询或执行回执当作行为依据，未通过证据校验。',
        execution_receipt_not_conclusion_evidence: '把执行回执用于最终结论依据，未通过校验。',
        tool_budget_reserved_for_evidence: '为后续证据补查预留工具预算，本项已跳过。',
        source_not_connected: '该来源未接入，本项未执行。'
    }[code];
}
function block(title, value, parent = inspectorContent) {
    if (value === undefined || value === null) return false;
    parent.append(element('h4', title), element('pre', display(value)));
    return true;
}
function empty(text) { inspectorContent.append(element('p', text, 'inspector-empty')); }
function sourceLink(el) {
    if (!el) return;
    const a = element('a', '定位到完整原件 ↗'); a.href = '#' + el.id;
    inspectorContent.append(a);
}
function linkedArtifact(id) { return savedRecord(artifactElements.get(id)); }
function bodyOf(artifact) { return artifact?.content_json ?? artifact?.content_text; }
function requestBody(artifact) {
    const body = bodyOf(artifact) || {};
    return body.body || body.request || body.payload?.body || body.payload || body;
}
function responsePayload(artifact) {
    const body = bodyOf(artifact) || {};
    return body.payload || body;
}
function knowledgeReceipts(runId) {
    const values = [];
    for (const [id, el] of artifactElements) {
        if (el.dataset.runId !== runId) continue;
        const artifact = linkedArtifact(id), body = bodyOf(artifact);
        if (artifact?.kind !== 'tool_response' || body?.tool_name !== 'knowledge') continue;
        let metadata = body.source_metadata || {};
        for (const [sid, summaryEl] of artifactElements) {
            if (summaryEl.dataset.runId !== runId) continue;
            const summary = bodyOf(linkedArtifact(sid));
            const source = Array.isArray(summary?.sources) && summary.sources.find(s => s.artifact_id === id);
            if (source?.source_metadata) { metadata = source.source_metadata; break; }
        }
        values.push({artifact, body, metadata});
    }
    return values;
}
function showKnowledge(view, row, artifacts) {
    const entry = knowledgeReceipts(row.run_id).find(r => r.artifact.step_id === row.id || r.artifact.id === row.id);
    if (!entry || view === 'raw' || view === 'prompt') return false;
    const {body, metadata} = entry;
    const keys = body.actual_args?.parameters?.selectors || [];
    const purposeKeys = keys.filter(k => k.purpose);
    inspectorContent.append(element('p', '知识用于技术解释、取证指导和历史案例参考；相关度不代表本案事实置信度。', 'quiet'));
    block('未查询的目标', metadata.not_queried_purposes);
    if (!purposeKeys.length) {
        empty('本记录未保存按目标的检索详情。原有参数和结果可在“原始记录”查看。');
        block('实际状态', {state: body.state, error: body.error});
        return true;
    }
    if (view === 'overview') {
        block('本地嵌入与检索', {model: metadata.model, dimension: metadata.dimension,
            method: metadata.retrieval_method, collection: metadata.collection, profile_sha256: metadata.profile_sha256});
        block('实际调用记录', metadata.calls);
        block('错误或未查询原因', metadata.error || metadata.unavailable_reason || body.error);
    }
    for (const key of purposeKeys) {
        const receipt = (metadata.queries || []).find(q => q.object_key === key.object_key);
        inspectorContent.append(element('h4', key.purpose_label || key.purpose));
        if (view === 'overview') {
            block('执行情况', receipt || {state: body.state === 'skipped' ? '未查询' : '未记录目标回执', error: body.error});
            block('用途', key.use);
        } else if (view === 'input') {
            block('实际检索文本', key.value);
            block('材料来源', key.source_paths);
            block('筛选与限制', {filters: key.filters, facets: key.facets, candidate_limit: key.candidate_limit,
                limit: key.limit, score_threshold: key.score_threshold, query_alert_ids: key.alert_ids});
        } else if (view === 'output') {
            const hits = (body.rows || []).filter(r => r.object_key === key.object_key);
            block('候选筛选（相似不等于适用）', receipt?.candidates);
            if (receipt?.outcome === 'filtered') empty('检索有候选，但均因适用条件或来源版本被排除；未继续补搜。');
            if (!hits.length) empty(receipt?.state === 'completed' && receipt.returned_rows === 0 ?
                '该目标查询完成，无符合条件的片段。' : '没有保存命中片段，请结合实际状态查看。');
            for (const hit of hits) {
                if (hit.purpose === 'historical_case_reference') {
                    block('历史来源与版本', hit.record?.history);
                    block('历史分诊（已有判断）', hit.record?.triage);
                    block('历史人工反馈（人工陈述）', hit.record?.feedback);
                }
                block(hit.record?.title || '知识片段', {purpose: hit.purpose_label, use: hit.use,
                    similarity: hit.similarity, document: hit.purpose === 'historical_case_reference' ?
                        {id: hit.record?.id, title: hit.record?.title, source_url: hit.record?.source_url} : hit.record,
                    content_sha256: hit.content_sha256,
                    applicability: hit.applicability,
                    limitations: hit.limitations});
            }
            block('返回范围', receipt);
        }
    }
    sourceLink(artifactElements.get(entry.artifact.id));
    return true;
}
function citationValues(value, path = '$', found = []) {
    if (!value || typeof value !== 'object') return found;
    for (const [key, child] of Object.entries(value)) {
        if (['source_ids','evidence_ids','support_ids','counter_ids'].includes(key) && Array.isArray(child)) {
            for (const id of child) if (typeof id === 'string') found.push({id, path: path + '.' + key});
        } else if (child && typeof child === 'object') citationValues(child, path + '.' + key, found);
    }
    return found;
}
function showKnowledgeUsage(row, requests, responses) {
    if (!requests.length) return;
    const receipts = knowledgeReceipts(row.run_id);
    if (!receipts.length) return;
    const used = [], citations = [];
    let parsed = false;
    for (const response of responses) {
        const raw = responsePayload(response)?.raw;
        for (const choice of raw?.choices || []) {
            try { citations.push(...citationValues(JSON.parse(choice.message.content))); parsed = true; } catch (_) { /* Preserve original output below. */ }
        }
    }
    for (const request of requests) {
        const saved = bodyOf(request), payload = saved?.payload || saved;
        block('本次知识未送入／合并原因', (payload?.omissions || []).filter(o =>
            o.knowledge_identity || o.reason === 'duplicate_knowledge_version'));
        for (const [alias, source] of Object.entries(payload?.source_map || {})) {
            const receipt = receipts.find(r => r.artifact.id === source.ref?.id);
            const match = /^\$\.rows\.(\d+)(?:\.record\.(triage|feedback))?$/.exec(source.ref?.source_path || '');
            if (!receipt || !match) continue;
            const hit = receipt.body.rows?.[Number(match[1])];
            if (!hit) continue;
            used.push({source_id: alias, purpose: hit.purpose_label || hit.purpose || '未记录目标',
                title: hit.record?.title, document_id: hit.record_id, content_sha256: hit.content_sha256,
                historical_source: hit.record?.history?.source, source_role: source.ref?.role,
                merged_query_origins: source.knowledge?.origins,
                referenced_part: match[2] || '完整知识片段',
                retrieved: '已检索到', input: '已进入本次输入', output: citations.some(c => c.id === alias) ?
                    '原答有结构化引用' : parsed ? '未见结构化引用' : '未记录或原答未能解析',
                citation_paths: citations.filter(c => c.id === alias).map(c => c.path),
                artifact_id: receipt.artifact.id, source_path: source.ref.source_path});
        }
    }
    if (used.length) block('本次模型的知识使用关联', used);
    else empty('本轮有知识查询记录，但本次模型输入未找到可定位的知识片段引用。');
    inspectorContent.append(element('p', '此处仅统计 source_ids/evidence_ids/support_ids/counter_ids 数组；正文可能提及来源编号，请结合原答查看。结构化引用不代表校验接受或知识使用合理。', 'quiet'));
}
function relatedArtifacts(row, el) {
    if (el.dataset.recordKind === 'artifact') return [row];
    const ids = new Set([row.input_artifact_id, row.output_artifact_id, row.reused_artifact_id].filter(Boolean));
    for (const [id, item] of artifactElements) {
        if (el.dataset.recordKind === 'step' && item.dataset.stepId === row.id) ids.add(id);
        if (el.dataset.recordKind === 'run' && item.dataset.runId === row.id && !item.dataset.stepId) ids.add(id);
    }
    return [...ids].map(linkedArtifact).filter(Boolean);
}
function modelErrors(row, artifacts, kind) {
    const errors = [];
    if (kind === 'step' && row.error != null) errors.push(['步骤错误 / 跳过原因', row.error]);
    if (kind === 'run' && row.stop_reason != null) errors.push(['本轮停止原因', row.stop_reason]);
    for (const artifact of artifacts) {
        if (artifact.kind !== 'model_response') continue;
        const payload = responsePayload(artifact);
        for (const key of ['validation_error', 'error', 'provider_error', 'transport_error']) {
            if (payload[key] != null) errors.push([key + ' · ' + artifact.id, payload[key]]);
        }
    }
    return errors;
}
function resetInspector() {
    selection = null;
    for (const node of flow.querySelectorAll('[aria-current]')) node.removeAttribute('aria-current');
    inspectorTitle.textContent = '选择左侧节点';
    inspectorContext.textContent = '';
    inspectorNotice.className = '';
    inspectorNotice.textContent = '点击流程中的阶段、模型或查询，查看实际保存的输入与输出。';
    inspectorTabs.hidden = true;
    inspectorContent.replaceChildren();
}
function selectNode(node, target) {
    resetInspector();
    const label = node.textContent.trim();
    const panel = flow.querySelector('.flow-panel:not([hidden])');
    inspectorContext.textContent = flow.querySelector('[data-choice]:not([hidden]) select')?.selectedOptions[0]?.textContent || '';
    inspectorTitle.textContent = label;
    node.setAttribute('aria-current', 'true');
    let el = target ? document.getElementById(target) : null;
    let row = savedRecord(el);
    if (el?.dataset.recordKind === 'artifact' && ['model_request', 'model_response'].includes(row?.kind)) {
        const step = stepElements.get(row.step_id);
        if (step) { el = step; row = savedRecord(el); }
    }
    // Only the currently selected Run can populate this panel.
    if (el && panel?.dataset.runId && (el.dataset.runId || row?.id) !== panel.dataset.runId) {
        inspectorNotice.textContent = '记录不属于当前轮次，请重新选择。'; return;
    }
    if (!row) {
        const states = {
            no_route: '本轮没有分派这条路线，因此没有对应的输入或输出。',
            skipped: '本轮已跳过此节点，未保存可查阅的执行记录。',
            not_applicable: '本轮记录为不适用，没有单独的执行记录。',
            missing: '当前快照未记录此节点。不能据此判断已执行或已成功。'
        };
        inspectorNotice.textContent = states[node.dataset.state] || '此节点没有关联的保存记录。';
        empty('请选择有记录的阶段、模型或查询查看原件。'); return;
    }
    const artifacts = relatedArtifacts(row, el);
    const errors = modelErrors(row, artifacts, el.dataset.recordKind);
    if (node.title && !errors.length) errors.push(['节点记录的原因', node.title]);
    selection = {el, row, artifacts, errors};
    inspectorTabs.hidden = false;
    inspectorNotice.textContent = errors.length ? '存在错误或限制，详见“概览与原因”。输入与输出以实际保存记录为准。' :
        '以下内容来自本轮已保存记录；执行状态与模型结论是否可采用分别查看。';
    inspectorNotice.className = errors.length ? 'inspector-failure' : '';
    showInspectorView('overview');
}
function showInspectorView(view) {
    if (!selection) return;
    for (const button of inspectorTabs.querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.view === view));
    inspectorContent.replaceChildren(); inspectorContent.scrollTop = 0;
    const {el, row, artifacts, errors} = selection;
    const requests = artifacts.filter(a => a.kind === 'model_request');
    const responses = artifacts.filter(a => a.kind === 'model_response');
    if (showKnowledge(view, row, artifacts)) return;
    if (['overview', 'input', 'output'].includes(view)) showKnowledgeUsage(row, requests, responses);
    if (view === 'overview') {
        const facts = element('dl');
        const labels = {id:'记录 ID', stage_code:'流程编号', kind:'类型', state:'执行状态', delivery_state:'交付状态',
            validation_state:'校验状态', returned_rows:'返回行数', started_at:'开始（北京）', ended_at:'结束（北京）', model:'模型', provider:'提供方'};
        for (const [key, label] of Object.entries(labels)) {
            if (row[key] == null) continue;
            let value = display(row[key]);
            if (['started_at', 'ended_at'].includes(key) && !Number.isNaN(Date.parse(row[key]))) {
                value = new Date(row[key]).toLocaleString('zh-CN', {timeZone:'Asia/Shanghai', hour12:false});
            }
            facts.append(element('dt', label), element('dd', value));
        }
        inspectorContent.append(facts);
        for (const [label, value] of errors) {
            const box = element('div', undefined, 'inspector-error'); block(label, value, box);
            const explanation = reasonDescription(value);
            if (explanation) box.append(element('p', explanation));
            inspectorContent.append(box);
        }
        if (!errors.length) inspectorContent.append(element('p', '该记录未保存错误原因；这不代表模型正文质量已经通过。', 'quiet'));
        for (const response of responses) {
            const payload = responsePayload(response);
            block('模型校验明细', payload.validation_diagnostics);
            block('用量', bodyOf(response)?.usage);
        }
        if (row.returned_rows === 0) inspectorContent.append(element('p', '查询完成，返回 0 行；不代表相关行为不存在或已确认安全。', 'quiet'));
        const children = recordElements.filter(child => child.dataset.recordKind === 'step' &&
            (el.dataset.recordKind === 'run' ? child.dataset.runId === row.id : child.dataset.parentStepId === row.id));
        if (children.length) inspectorContent.append(element('h4', '关联步骤'));
        for (const child of children) {
            const button = element('button', child.querySelector('summary').textContent, 'inspector-related');
            button.type = 'button'; button.dataset.inspectTarget = child.id; inspectorContent.append(button);
        }
        sourceLink(el);
    } else if (view === 'prompt') {
        let count = 0;
        for (const request of requests) {
            const body = requestBody(request);
            inspectorContent.append(element('h4', '模型请求 · ' + request.id));
            if (block('系统指令', body.instructions)) count++;
            for (const [i, message] of (Array.isArray(body.messages) ? body.messages : []).entries()) {
                if (['system', 'developer'].includes(message.role)) {
                    block(message.role + ' · 消息 ' + (i + 1), message.content); count++;
                }
            }
            sourceLink(artifactElements.get(request.id));
        }
        if (!count) empty('此节点未保存独立的 system / developer 提示词。阶段节点可通过“概览与原因”进入关联模型调用。');
    } else if (view === 'input') {
        let count = 0;
        if (block('实际调用参数', row.actual_args)) count++;
        for (const request of requests) {
            const body = requestBody(request);
            inspectorContent.append(element('h4', '模型输入 · ' + request.id));
            for (const [i, message] of (Array.isArray(body.messages) ? body.messages : []).entries()) {
                if (!['system', 'developer'].includes(message.role)) {
                    block((message.role || '未标角色') + ' · 消息 ' + (i + 1), message.content ?? message);
                    if (message.tool_calls) block('工具调用', message.tool_calls);
                    count++;
                }
            }
            if (block('输入', body.input)) count++;
            const config = Object.fromEntries(Object.entries(body).filter(([key]) => !['messages', 'input', 'instructions'].includes(key)));
            block('模型参数与输出约束', config);
            sourceLink(artifactElements.get(request.id));
        }
        const input = linkedArtifact(row.input_artifact_id);
        if (input && input.kind !== 'model_request') { block('保存的输入', bodyOf(input)); count++; }
        if (el.dataset.recordKind === 'artifact' && row.kind === 'input_snapshot') {
            block('本轮冻结输入', bodyOf(row)); count++;
        }
        for (const artifact of artifacts.filter(a => a.kind === 'tool_request')) { block('查询请求', bodyOf(artifact)); count++; }
        if (!count) empty('此节点未绑定独立输入工件。输入是否完整需结合关联步骤和本轮冻结材料核对。');
    } else if (view === 'output') {
        let count = 0;
        for (const response of responses) {
            const payload = responsePayload(response);
            const raw = Object.hasOwn(payload, 'raw') ? payload.raw : payload;
            inspectorContent.append(element('h4', '模型原答 · ' + response.id));
            if (raw == null) empty('未保存模型原答，请查看错误回执。');
            else {
                const choices = Array.isArray(raw.choices) ? raw.choices : [];
                if (choices.length) for (const [i, choice] of choices.entries()) {
                    block('原始正文 · 回答 ' + (i + 1), choice.message?.content ?? choice.text);
                    block('结束原因', choice.finish_reason);
                    block('拒绝信息', choice.message?.refusal);
                }
                else block('原始输出', raw);
            }
            block('校验错误', payload.validation_error);
            sourceLink(artifactElements.get(response.id)); count++;
        }
        const output = linkedArtifact(row.output_artifact_id);
        const outputs = new Map();
        if (output && output.kind !== 'model_response') outputs.set(output.id, output);
        if (el.dataset.recordKind === 'artifact' && !['input_snapshot', 'tool_request', 'model_request', 'model_response'].includes(row.kind)) outputs.set(row.id, row);
        for (const artifact of artifacts.filter(a => a.kind === 'tool_response')) outputs.set(artifact.id, artifact);
        for (const artifact of outputs.values()) {
            block('保存的输出 · ' + artifact.kind, bodyOf(artifact)); sourceLink(artifactElements.get(artifact.id)); count++;
        }
        if (!count) empty('此节点未保存独立输出。失败、跳过或未执行都不能当作返回空结果。');
    } else if (view === 'raw') {
        block('完整记录', row); sourceLink(el);
        for (const artifact of artifacts) {
            if (artifact.id === row.id) continue;
            const details = element('details'); details.append(element('summary', artifact.kind + ' · ' + artifact.id));
            details.addEventListener('toggle', () => {
                if (details.open && !details.querySelector('pre')) details.append(element('pre', display(artifact)));
            });
            inspectorContent.append(details);
        }
    }
}
inspectorTabs.addEventListener('click', event => {
    const button = event.target.closest('[data-view]');
    if (button) showInspectorView(button.dataset.view);
});
inspectorContent.addEventListener('click', event => {
    const button = event.target.closest('[data-inspect-target]');
    if (button) selectNode(button, button.dataset.inspectTarget);
});
flow.addEventListener('click', event => {
    const node = event.target.closest('.flow-node');
    if (!node) return;
    event.preventDefault();
    selectNode(node, node.getAttribute('href')?.slice(1));
    if (window.matchMedia('(max-width:980px)').matches) inspector.scrollIntoView({block:'start'});
});
"""
