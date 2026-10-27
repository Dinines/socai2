/* V2: read-only Run presentation; fixture material never enriches recorded Runs. */
'use strict';
window.investigationWorkspaceModel = (() => {
  function runs(store){
    const reference=window.referenceWorkspaces.investigationRecords(store.alerts).map(r=>({
      ...r,recorded:false,status:'completed',completion:r.completion==='部分完成'?'partial':'completed',
      verdict:r.completion==='部分完成'?'needs_review':'reviewed',findings:[r.findings],
      steps:r.steps.map(([name,summary],i)=>({seq:i,name,summary,kind:'阶段记录'})),
      tools:[],graphs:{},artifacts:[],actions:[],executed:[],report:null,
      stop:r.completion==='部分完成'?'未取得完整传输文件清单，需继续核查传输范围。':null
    }));
    return [...reference,...(window.savedInvestigationRuns||[])];
  }
  function forAlerts(store,alerts){const ids=new Set(alerts.map(a=>a.id));return runs(store).filter(r=>r.alertIds.some(id=>ids.has(id)));}
  function selected(rows,id){return rows.find(r=>r.id===id)||rows[0]||null;}
  function chain(store,members,seedId,hours=24){
    const seed=members.find(a=>a.id===seedId)||members[0];if(!seed)return {seed:null,rows:[]};
    const ids=new Set(seed.entityIds||[]),stamp=Date.parse(seed.event_time||seed.first);
    return {seed,rows:members.filter(a=>a.id!==seed.id&&!a.persistedRecord&&Math.abs(Date.parse(a.event_time||a.first)-stamp)<=hours*3600000).map(a=>({alert:a,shared:(a.entityIds||[]).filter(id=>ids.has(id))})).filter(x=>x.shared.length).sort((a,b)=>Date.parse(b.alert.event_time||b.alert.first)-Date.parse(a.alert.event_time||a.alert.first))};
  }
  return {runs,forAlerts,selected,chain};
})();

window.createInvestigationWorkspace = function(ctx){
  const {store,esc,I,btn,badge,severity,state,currentRoute,currentCase,scopeAlerts,getAlert,getAsset,navigate,render,downloadFile}=ctx;
  const M=window.investigationWorkspaceModel;
  const names={completed:'已结束',running:'运行中',failed:'失败',partial:'部分交付',not_escalated:'未升级调查',needs_review:'待复核',true_positive:'真实威胁',false_positive:'误报',benign_true_positive:'预期活动',reviewed:'已形成调查结果'};
  const statuses={success:'已返回',empty:'无候选关系',not_linked:'未关联 Case',unavailable:'查询不可用',error:'查询失败'};
  const format=v=>v?new Date(typeof v==='number'?v:String(v).replace(' ','T')).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}):'未记录';
  const json=v=>`<pre class="iv-json">${esc(JSON.stringify(v,null,2))}</pre>`;
  const text=v=>typeof v==='string'?v:JSON.stringify(v);
  const card=(title,body,extra='')=>`<article class="iv-card ${extra}"><h3>${title}</h3>${body}</article>`;
  const no=(title,body='')=>`<div class="iv-empty">${I('search',24)}<strong>${title}</strong>${body?`<p>${body}</p>`:''}</div>`;
  const alertLink=id=>{const a=getAlert(id);return a?`<button class="iv-alert-link" data-action="alert" data-id="${esc(id)}">${I('shield',14)}<span>${esc(a.title)}</span>${severity(a.severity)}</button>`:`<span class="iv-mono">${esc(id)}</span>`;};
  const metric=(label,value,detail='')=>`<div><span>${label}</span><strong>${esc(value??'—')}</strong>${detail?`<small>${esc(detail)}</small>`:''}</div>`;
  function route(run,view='overview'){
    const r=currentRoute();return r.page==='cases'&&r.id?`#/cases/${r.id}/investigations?run=${encodeURIComponent(run.id)}&view=${view}`:`#/investigations/${encodeURIComponent(run.id)}/${view}`;
  }
  function available(){const r=currentRoute();return r.page==='cases'?M.forAlerts(store,scopeAlerts()):M.runs(store);}
  function active(){const r=currentRoute(),rows=available();const id=r.page==='investigations'?r.id:new URLSearchParams(r.search).get('run');return id?rows.find(x=>x.id===id):rows[0];}
  function brief(run){return `<span class="iv-run-status">${badge(names[run.status]||run.status)}${badge(run.completion==='completed'?'完整交付':names[run.completion]||'完整性未记录',run.completion==='partial'?'amber':'blue')}</span>`;}
  function linkedRuns(){
    const rows=M.forAlerts(store,scopeAlerts());return `<div class="iv-root"><div class="iv-heading"><div><span class="iv-eyebrow">INVESTIGATION LINKS</span><h2>${currentRoute().page==='cases'?'调查历史':'关联调查'}</h2><p>保留每次运行的范围与结果，选择一项查看分析过程。</p></div></div>${rows.length?rows.map(r=>`<article class="iv-card iv-run-link">${brief(r)}<h3>${esc(r.title)}</h3><p>${esc((r.findings||[]).map(text).join(' ').slice(0,200))}</p><div class="iv-foot"><span>${r.alertIds.length} 条输入告警 · ${format(r.started)}</span><a class="button primary" href="${route(r)}">打开调查 ${I('external',14)}</a></div></article>`).join(''):no('尚无调查记录','已有告警和上下文仍可在事件中查看。')}</div>`;
  }
  function incidentSummary(){
    const a=scopeAlerts(),rows=M.forAlerts(store,a),entities=new Set(a.flatMap(x=>x.entityIds)),times=a.map(x=>Date.parse(x.event_time||x.first)).filter(Number.isFinite);
    return `<div class="iv-root iv-context-strip"><div><span class="iv-eyebrow">事件上下文</span><strong>告警与已有线索</strong><p>查看关联依据，确定需要调查的范围。</p></div><div class="iv-inline-metrics">${metric('成员告警',a.length)}${metric('关联实体',entities.size)}${metric('发生范围',times.length?`${format(Math.min(...times))} — ${format(Math.max(...times))}`:'—')}${metric('已有调查',rows.length)}</div><a class="button" href="#/incidents/${currentRoute().id}/investigations">查看调查 ${I('chevron',14)}</a></div>`;
  }
  function incidentChain(){
    const a=scopeAlerts(),q=new URLSearchParams(currentRoute().search),hours=Number(q.get('window'))||24,{seed,rows}=M.chain(store,a,q.get('seed'),hours);
    if(!seed)return `<div class="iv-root">${no('暂无成员告警')}</div>`;
    return `<div class="iv-root"><div class="iv-heading"><div><span class="iv-eyebrow">ATTACK CHAIN</span><h2>关联告警链</h2><p>从种子告警查看共享实体与时间范围内的关联线索。关联不代表已验证攻击因果。</p></div><a class="button" href="#/incidents/${currentRoute().id}/attack">查看关系图</a></div><div class="iv-controls"><label>种子告警<select data-iv-seed aria-label="Chain种子告警">${a.map(x=>`<option value="${x.id}" ${x.id===seed.id?'selected':''}>${esc(x.title)}</option>`).join('')}</select></label><label>前后时间范围<select data-iv-window aria-label="Chain时间窗口">${[1,6,24,72,168].map(h=>`<option value="${h}" ${h===hours?'selected':''}>${h<168?h+' 小时':'7 天'}</option>`).join('')}</select></label></div><div class="iv-chain-seed">${badge('种子','blue')}${alertLink(seed.id)}<span>${format(seed.event_time||seed.first)}</span></div><div class="iv-chain-list">${rows.map((x,i)=>`<article class="iv-chain-row"><div class="iv-chain-num">${i+1}</div><div><div class="iv-foot"><span>${format(x.alert.event_time||x.alert.first)}</span>${badge('共享实体','blue')}</div>${alertLink(x.alert.id)}<p>关联依据：${x.shared.map(id=>`<button data-action="entity" data-id="${id}">${esc(getAsset(id)?.name||id)}</button>`).join(' · ')}</p><small>${esc(x.alert.source)}</small></div></article>`).join('')||no('当前窗口没有候选关系','可以选择其他种子或时间窗口；这不等于已排除攻击。')}</div></div>`;
  }
  function queue(){
    const rows=M.runs(store);return `<section class="page iv-root"><div class="iv-heading"><div><span class="iv-eyebrow">AI INVESTIGATIONS</span><h1>调查运行</h1><p>按运行查看分析、材料与交付结果。自动调查可以没有 Case。</p></div><a class="button" href="#/cases">返回 Cases</a></div><div class="iv-stats">${metric('运行记录',rows.length)}${metric('部分交付',rows.filter(r=>r.completion==='partial').length)}${metric('未升级调查',rows.filter(r=>r.completion==='not_escalated').length)}${metric('关联 Case',store.cases.filter(c=>M.forAlerts(store,store.alerts.filter(a=>c.alertIds.includes(a.id))).length).length)}</div><div class="iv-run-grid">${rows.map(r=>`<a class="iv-card iv-run-tile" href="#/investigations/${r.id}/overview"><div class="iv-foot">${brief(r)}${I('chevron',17)}</div><h3>${esc(r.title)}</h3><p>${esc((r.findings||[]).map(text).join(' ').slice(0,160)||'查看已保存的运行记录')}</p><div class="iv-foot"><small>${r.alertIds.length} 条输入告警</small><small>${format(r.started)}</small></div><code>${esc(r.id)}</code></a>`).join('')}</div></section>`;
  }
  function overview(run){
    const findings=run.findings||[],depth=run.depth||{},members=currentRoute().page==='cases'?scopeAlerts().length:null;
    return `<div class="iv-overview"><div class="iv-stack">${card('调查结果',`<div class="iv-conclusion">${I('search',24)}<div><strong>${esc(names[run.verdict]||run.verdict||'判定未记录')}</strong><span>${run.confidence!=null?'调查置信度 '+Math.round(run.confidence*100)+'%':'结果来自本次保存的调查材料'}</span></div></div>${findings.length?findings.slice(0,5).map(f=>`<p class="iv-finding">${esc(text(f))}</p>`).join(''):no('尚无调查发现')}${findings.length>5?`<details><summary>展开其余 ${findings.length-5} 条发现</summary>${findings.slice(5).map(f=>`<p>${esc(text(f))}</p>`).join('')}</details>`:''}`)}${run.stop?card('停止与交接',`<p>${esc(run.stop)}</p>${(depth.unavailable_data||[]).length?`<p>未取得资料：${depth.unavailable_data.map(esc).join('、')}</p>`:''}<a class="iv-link" href="${route(run,'tools')}">核对工具返回与覆盖范围 →</a>`,'iv-warning'):''}${card('最近记录',run.steps?.length?`<div class="iv-mini-steps">${run.steps.filter(s=>s.kind!=='tool_call').slice(-4).map(s=>`<div><i></i><strong>${esc(s.name)}</strong><span>${esc(s.summary||'已记录')}</span></div>`).join('')}</div><a class="iv-link" href="${route(run,'process')}">查看完整过程 →</a>`:no('暂无步骤记录'))}</div><aside class="iv-stack">${card('本次调查范围',`<div class="iv-pair"><span>输入告警</span><b>${run.alertIds.length}</b></div>${members!==null?`<div class="iv-pair"><span>当前 Case 成员</span><b>${members}</b></div><p class="iv-note">当前成员与本次输入分别展示；新成员不会自动加入已结束的运行。</p>`:''}${run.alertIds.map(alertLink).join('')}${run.input?`<details class="iv-raw"><summary>查看本次保存的输入</summary><p class="iv-note">本次Run保存的告警输入（展示字段），与当前告警页面分别核对。</p>${json(run.input)}${run.input_summary?`<h4>输入摘要</h4><pre class="iv-tool-result">${esc(run.input_summary)}</pre>`:''}</details>`:''}`)}${card('执行信息',`<dl class="iv-definition"><dt>Run 状态</dt><dd>${esc(names[run.status]||run.status)}</dd><dt>交付完整性</dt><dd>${run.completion==='completed'?'完整交付':esc(names[run.completion]||'未记录')}</dd><dt>Run 开始</dt><dd>${format(run.started)}</dd><dt>Run 结束</dt><dd>${format(run.ended)}</dd><dt>最后记录</dt><dd>${format(run.steps?.at(-1)?.time)}</dd><dt>调用 / Tokens</dt><dd>${run.calls??'—'} / ${run.tokens?.toLocaleString()??'—'}</dd><dt>费用</dt><dd>${run.unpriced?'未定价 · '+run.unpriced+' 次调用':'未提供'}</dd></dl>`)}${run.triage?card('首次分诊',`<div class="iv-pair"><span>判定</span><b>${esc(names[run.triage.verdict]||run.triage.verdict)}</b></div><div class="iv-pair"><span>分诊评分</span><b>${run.triage.confidence!=null?Math.round(run.triage.confidence*100):'—'}</b></div><p class="iv-note">首次分诊与后续调查保留各自判断。</p>`):''}</aside></div>`;
  }
  function process(run){return `<div class="iv-section-title"><h3>实际处理过程</h3><span>${run.steps.length} 条记录 · 按记录时间展示</span></div><div class="iv-timeline">${run.steps.map(s=>`<details class="iv-step"><summary><span class="iv-step-dot">${I(s.kind==='tool_call'?'search':'check',14)}</span><span><strong>${esc(s.name||s.kind)}</strong><small>${esc(s.summary||s.kind)}</small></span><time>${format(s.time)}</time>${I('down',14)}</summary><div class="iv-step-content"><div class="iv-pair"><span>记录类型</span><code>${esc(s.kind)}</code></div>${s.payload&&Object.keys(s.payload).length?json(s.payload):`<p>${esc(s.summary||'未保存该步骤的详细输入输出。')}</p>`}</div></details>`).join('')||no('暂无步骤记录')}</div><p class="iv-note">节点记录表示已记载的工作，不据此推算百分比；建议、执行与交付状态分别核对。</p>`;}
  function tools(run){const d=run.depth||{};return `<div class="iv-stats">${metric('工具记录',run.tools.length)}${metric('Deep轮数',d.iterations)}${metric('查询方向',d.distinct_pivots)}${metric('材料截断',d.truncated?'是':run.depth?'否':'—')}</div>${(d.coverage_notes||[]).length?card('查询覆盖范围',d.coverage_notes.map(n=>`<p>${esc(n)}</p>`).join('')):''}<div class="iv-tools">${run.tools.map((t,i)=>card(`${i+1}. ${esc(t.name)}`,`<div class="iv-foot"><span>${format(t.time)}</span>${badge('已保存返回摘要','blue')}</div><h4>实际参数</h4>${json(t.args)}<h4>返回内容</h4><pre class="iv-tool-result">${esc(t.result||'未保存返回内容')}</pre><p class="iv-note">v1工具记录保留最多200字符摘要；空结果、不可用和查询失败以返回内容为准。</p>`)).join('')||no('没有可回查的工具记录','不从报告文字补造工具调用。')}</div>${card('审计材料',run.artifacts.length?`<div class="iv-artifacts">${run.artifacts.map(a=>`<details><summary><strong>${esc(a.kind)}</strong><span>${a.size_bytes.toLocaleString()} bytes</span>${I('down',12)}</summary><dl class="iv-definition"><dt>工件ID</dt><dd class="iv-mono">${esc(a.id)}</dd><dt>SHA256</dt><dd class="iv-mono">${esc(a.sha256)}</dd><dt>保存时间</dt><dd>${format(a.created_at)}</dd></dl></details>`).join('')}</div>`:no('未保存独立工件目录'))}`;}
  function graphPart(kind,p){
    const labels={attack_chain:'Attack Chain · 关联告警链',attack_path:'Attack Path · Case 关系路径',alert_graph:'Alert Graph · 告警关联范围'},d=p?.data||{};
    if(!p)return card(labels[kind],no('本次未保存此类材料'));
    const explanation=p.error==='no_linked_case'?'该告警没有关联 Case，因此没有 Case 路径；仍可查看 Alert Graph。':p.status==='empty'?'当前种子与查询范围没有返回候选关系。':p.error?String(p.error):'';
    let body=`<div class="iv-foot">${badge(statuses[p.status]||p.status,p.status==='success'?'blue':'amber')}<span>${esc(p.source||'—')} · ${format(p.queried_at)}</span></div>${explanation?`<p>${esc(explanation)}</p>`:''}`;
    if(kind==='attack_chain')body+=`<div class="iv-pair"><span>候选告警 / 时间窗口</span><b>${d.chain?.length??'—'} / ${esc(d.window||'—')}</b></div>${(d.chain||[]).map(c=>`<div class="iv-chain-item">${getAlert(c.alert_id)?alertLink(c.alert_id):esc(c.title)}<small>${format(c.event_time)} · ${esc(JSON.stringify(c.shared_entities||[]))}</small></div>`).join('')}`;
    if(kind==='attack_path'&&d.nodes)body+=pathGraph(d);
    if(kind==='alert_graph'&&p.status==='success'){
      const n=d.neighbors||{},b=d.blast_radius||{};body+=`<div class="iv-stats">${metric('直接邻居',n.neighbor_count??n.neighbors?.length)}${metric('图可达实体',b.total_affected)}${metric('遍历深度',b.hops)}${metric('范围评分',b.blast_radius_score)}</div><p class="iv-note">图可达范围不等于已确认受害范围。</p><div class="iv-node-grid">${(n.neighbors||[]).map(x=>{const node=x.node||x.neighbor||x,pr=node.properties||{};return `<div><span>${esc(node.label||node.labels?.[0]||'实体')}</span><strong>${esc(pr.indicator_value||pr.hostname||pr.username||pr.value||pr.name||pr.title||node.id||'关联对象')}</strong><small>${esc(x.rel_type||x.relationship||x.relationship_type||x.type||'关联关系')}</small></div>`;}).join('')}</div>`;
    }
    return card(labels[kind],body+`<details class="iv-raw"><summary>查看保存的关系数据</summary>${json(p)}</details>`);
  }
  function pathGraph(data){
    const nodes=data.nodes||[],edges=data.edges||[];return `<div class="iv-node-grid">${nodes.map(n=>`<div><span>${esc(n.label||n.type||'实体')}</span><strong>${esc(n.properties?.indicator_value||n.properties?.hostname||n.properties?.username||n.properties?.value||n.properties?.title||n.name||n.id)}</strong></div>`).join('')}</div><div class="iv-relations">${edges.map(e=>`<p><code>${esc(e.source)}</code><span> — ${esc(e.type||e.label||'关联')} → </span><code>${esc(e.target)}</code></p>`).join('')}</div>`;
  }
  function graphs(run){
    let fixture='';if(!run.recorded){const members=store.alerts.filter(a=>run.alertIds.includes(a.id)),g=window.referenceWorkspaces.graph(store,members,{grouped:false});fixture=card('输入告警的关联资料',`<p class="iv-note">以下关系来自所选输入告警；本次未保存独立 Chain / Path 服务返回，不能将当前关系当作当次服务快照。</p>${pathGraph({nodes:g.nodes,edges:g.edges})}`);}
    return `<div class="iv-section-title"><div><h3>本次运行的链图材料</h3><p>分别读取已保存的关联链、Case路径和告警图；查看不重新查询或改写原件。</p></div></div><div class="iv-stack">${['attack_chain','attack_path','alert_graph'].map(k=>graphPart(k,run.graphs[k])).join('')}${fixture}</div>`;
  }
  function report(run){return `<div class="iv-section-title"><h3>调查报告</h3>${run.report?btn('下载 Markdown','iv-download',run.id,'small','download'):''}</div>${run.completion==='partial'?`<div class="iv-callout">部分交付 · 请结合停止原因与工具返回核对报告。</div>`:''}${run.report?`<article class="iv-card iv-report"><pre>${esc(run.report)}</pre></article>`:no('本次没有保存报告正文','调查发现和已有步骤仍可查看。')}${card('建议与执行',`<h4>建议动作 (${run.actions.length})</h4>${run.actions.map(a=>`<p>${esc(typeof a==='string'?a:a.description||a.action_type)}</p>`).join('')||'<p class="iv-note">未保存建议动作。</p>'}<h4>实际执行 (${run.executed.length})</h4>${run.executed.map(a=>`<p>${esc(text(a))}</p>`).join('')||'<p class="iv-note">没有已执行动作记录；建议不代表已执行。</p>'}`)}`;}
  function workbench(){
    const r=currentRoute();if(r.page==='investigations'&&!r.id)return queue();
    const rows=available(),run=active();if(!run)return `<div class="iv-root">${no('没有关联调查运行','可以查看已有告警、材料与人工协作信息。')}<a class="button" href="#/investigations">查看全部调查运行</a></div>`;
    const requested=r.page==='cases'?new URLSearchParams(r.search).get('view'):r.tab,view=['overview','process','tools','graphs','report'].includes(requested)?requested:'overview';
    return `<div class="iv-root"><div class="iv-heading"><div><span class="iv-eyebrow">AI INVESTIGATION WORKSPACE</span><h2>${r.page==='cases'?'AI 调查':'调查详情'}</h2><p>核对本次输入、实际分析工作与交付结果。</p></div><a class="button" href="#/investigations">全部运行 ${I('list',14)}</a></div><div class="iv-run-selector"><label for="iv-run">调查运行</label><select id="iv-run" data-iv-run>${rows.map(x=>`<option value="${x.id}" ${x.id===run.id?'selected':''}>${x.id} · ${x.completion==='completed'?'完整交付':names[x.completion]||'未记录'}</option>`).join('')}</select>${brief(run)}</div><div class="iv-run-title"><h3>${esc(run.title)}</h3><span class="iv-mono">${esc(run.id)}</span></div><nav class="iv-tabs" aria-label="调查运行内容">${[['overview','结果与范围'],['process','分析过程'],['tools','工具与证据'],['graphs','Chain / Path'],['report','报告与响应']].map(([k,n])=>`<a href="${route(run,k)}" ${view===k?'aria-current="page"':''} class="${view===k?'active':''}">${n}${k==='tools'?`<span>${run.tools.length}</span>`:''}</a>`).join('')}</nav>${view==='overview'?overview(run):view==='process'?process(run):view==='tools'?tools(run):view==='graphs'?graphs(run):report(run)}</div>`;
  }
  function change(el){
    if(el.hasAttribute('data-iv-run')){const run=available().find(r=>r.id===el.value);if(run)navigate(route(run));return true;}
    if(el.hasAttribute('data-iv-seed')||el.hasAttribute('data-iv-window')){const q=new URLSearchParams(currentRoute().search);q.set(el.hasAttribute('data-iv-seed')?'seed':'window',el.value);navigate(`#/incidents/${currentRoute().id}/chain?${q}`);return true;}return false;
  }
  function handle(action,id){if(action!=='iv-download')return false;const run=active();if(run?.id===id&&run.report)downloadFile(`investigation-${id}.md`,run.report,'text/markdown;charset=utf-8');return true;}
  return {workbench,queue,linkedRuns,incidentSummary,incidentChain,change,handle};
};
