/* V2: read-only Run presentation; fixture material never enriches recorded Runs. */
'use strict';
window.investigationWorkspaceModel = (() => {
  const list=value=>Array.isArray(value)?value:[];
  function tacticTone(){return 'purple';}
  function normalizeRun(row){
    const r={...row};
    const seed=row.fixture&&row.simulation?(window.caseExplorationData?.runs||[]).find(x=>x.id===row.id):null;
    r.investigationKind=row.investigationKind||seed?.investigationKind||null;
    r.trigger=row.trigger||seed?.trigger||null;
    if(r.investigationKind==='baseline'&&row.title==='已保存的关联分析')r.title='基础调查 · 首次分析';
    if(seed&&row.title==='文件传输范围核查（模拟）')r.title=seed.title;
    // Remove the fixture title suffix in the shared view only; retain source records.
    if(row.fixture&&row.simulation&&typeof row.title==='string')r.title=r.title.replace(/（模拟）$/,'');
    for(const field of ['alertIds','steps','tools','artifacts','actions','executed'])r[field]=list(row[field]);
    r.findings=Array.isArray(row.findings)?row.findings:row.findings?[row.findings]:[];
    r.graphs=row.graphs&&typeof row.graphs==='object'?row.graphs:{};
    return r;
  }
  const activeStatuses=new Set(['pending','queued','starting','running','waiting','unknown']);
  function runMetrics(run){
    const numeric=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0?v:null;
    const stamp=v=>v===null||v===undefined||v===''?NaN:typeof v==='number'?v:Date.parse(v);
    const start=stamp(run.started),end=stamp(run.ended);
    const durationMs=!activeStatuses.has(run.status)&&Number.isFinite(start)&&Number.isFinite(end)&&end>=start?end-start:null;
    return {durationMs,toolRecords:list(run.tools).length,calls:numeric(run.calls),tokens:numeric(run.tokens)};
  }
  function humanTasks(c){
    const rows=list(c.tasks),adopted=new Set(rows.map(t=>t.sourceDraftId).filter(Boolean));
    const pending=list(c.investigationDrafts).filter(d=>d.status==='draft'&&!adopted.has(d.id)).map(d=>({id:'pending-task:'+d.id,sourceDraftId:d.id,title:d.objective,description:'核查所选告警和对象，记录确认结果。',owner:'未分配',status:'New',result:'',materials:list(d.materials),sourceRunId:d.sourceRunId||null,referenceContext:{alertIds:list(d.alertIds),entityIds:list(d.entityIds)},createdAt:d.createdAt,completedAt:null}));
    return [...rows,...pending];
  }
  const pendingTasks=c=>humanTasks(c).filter(t=>['New','In progress'].includes(t.status));
  const plain=value=>typeof value==='string'?value:value?.summary||value?.text||'';
  function runOutcome(run){
    const o=run.outcome&&typeof run.outcome==='object'?run.outcome:{},active=activeStatuses.has(run.status);
    const findings=list(run.findings).map(plain).filter(v=>v&&!/^Auto-triage:|^verdict=|^confidence=/i.test(v.trim()));
    return {purpose:o.purpose||run.objective||({'case_created':'建立案件的初始分析','members_changed':'核查成员变化后的案件范围','user_question':'回答用户提出的问题'})[run.trigger]||'本轮目的未单独记录',
      conclusion:active?'调查执行中，尚未形成结论。':o.conclusion||(['failed','error'].includes(run.status)?'本轮执行失败，未形成完整结论。':run.status==='cancelled'?'本轮已取消，未形成完整结论。':'本轮未保存结论'),
      hasConclusion:!active&&!!o.conclusion,findings:list(o.findings).length?list(o.findings).map(plain).filter(Boolean):findings,
      change:o.change||'未记录与此前结果的对比',impact:o.impact||'未记录对案件判断的影响',
      limitations:[...new Set([...list(o.limitations).map(plain),...(run.stop?[run.stop]:[]),...list(run.depth?.unavailable_data).map(plain)].filter(Boolean))],
      basis:list(o.basis).map(plain).filter(Boolean),active};
  }
  function pendingScope(c){const p=c.baselineUpdate||{};return {added:list(p.alertIds).filter(id=>c.alertIds.includes(id)),removed:list(p.removedAlertIds).filter(id=>!c.alertIds.includes(id))};}
  function caseAssessment(store,c){
    const assessment=c.assessment||{},rows=forCase(store,c),members=list(c.alertIds),knownRuns=new Set(rows.map(r=>r.id)),knownTasks=new Set(humanTasks(c).map(t=>t.id));
    const sourceRunIds=list(assessment.sourceRunIds).filter(id=>knownRuns.has(id)),taskIds=list(assessment.taskIds).filter(id=>knownTasks.has(id));
    const scope=list(assessment.alertIds).filter(id=>members.includes(id)),pending=pendingScope(c);
    const inputs=new Set(rows.filter(r=>!activeStatuses.has(r.status)&&r.completion!=='not_escalated').flatMap(r=>r.alertIds));
    const unanalysed=members.filter(id=>!inputs.has(id));
    return {...assessment,conclusion:assessment.conclusion||'尚未形成案件级判断',basis:list(assessment.basis),unresolved:list(assessment.unresolved),scope,sourceRunIds,taskIds,pending,unanalysed,
      hasAssessment:!!assessment.conclusion,uncovered:members.filter(id=>!scope.includes(id))};
  }
  const investigationLabel=r=>r.investigationKind==='baseline'?'基础调查':r.investigationKind==='ai_followup'?'AI 调查':'调查记录';
  function caseRecord(c){
    // Explicit legacy fixture membership is data adaptation, never a page-version switch.
    const reference=window.makeDemoData().cases.some(row=>row.id===c.id);
    const attachments=c.attachments??(reference?[['investigation-notes.txt','调查摘记 · TXT · 1 KB'],['evidence-register.csv','证据索引 · CSV · 2 KB']]:[]);
    return {...c,title:(c.title||'').replace(/（本地整理）$/,''),description:c.description||'汇集成员告警、关联对象与各次调查材料，供继续核查。',attachments:list(attachments)};
  }
  function scopeOf(row){
    if(row.sourceTenantId||row.sourceEnvironment)return [row.sourceEnvironment||'',row.sourceTenantId||''];
    const group=window.alertFlowData?.incidents?.find(i=>i.sourceAlertIds?.includes(row.id));
    if(group)return [group.sourceEnvironment||'',group.sourceTenantId||''];
    return row.persistedRecord?['unknown-recorded',row.id]:['design','design'];
  }
  const sameScope=(a,b)=>JSON.stringify(scopeOf(a))===JSON.stringify(scopeOf(b));
  function graphContext(store,run){
    const inputs=new Set(run.alertIds),library=window.aisoc20RecordedData;
    // Source formats are decoded here. The graph and source-material components are shared.
    const saved=library?.runs?.some(r=>r.id===run.id&&r.sourceEnvironment===run.sourceEnvironment&&r.sourceTenantId===run.sourceTenantId)?library.graph:null;
    if(saved){const edges=saved.edges.filter(e=>inputs.has(e.source)),ids=new Set([...inputs,...edges.map(e=>e.target)]);return {...saved,nodes:saved.nodes.filter(n=>ids.has(n.id)),edges,source:'输入告警的已保存关系'};}
    const path=run.graphs.attack_path,chain=run.graphs.attack_chain,neighborhood=run.graphs.alert_graph;
    if(path?.data?.nodes?.length||chain?.data?.entity_graph?.nodes?.length||neighborhood?.data?.neighbors?.source)return null;
    const members=store.alerts.filter(a=>inputs.has(a.id)&&sameScope(a,run)),ids=new Set(members.flatMap(a=>a.entityIds||[]));
    const assets=store.assets.filter(a=>ids.has(a.id)&&(!a.sourceTenantId&&!a.sourceEnvironment||sameScope(a,run)));
    const available=new Set(assets.map(a=>a.id));
    return {nodes:[...members.map(a=>({id:a.id,kind:'alert',label:a.title})),...assets.map(a=>({id:a.id,kind:a.type,label:a.name}))],edges:members.flatMap(a=>(a.entityIds||[]).filter(id=>available.has(id)).map(id=>({source:a.id,target:id,label:'源告警记录的对象关联'}))),source:'输入告警的关联资料'};
  }
  function runs(store){
    const reference=window.referenceWorkspaces.investigationRecords(store.alerts).map(r=>({
      ...r,recorded:false,status:'completed',completion:r.completion==='部分完成'?'partial':'completed',
      verdict:r.completion==='部分完成'?'needs_review':'reviewed',findings:[r.findings],
      steps:r.steps.map(([name,summary],i)=>({seq:i,name,summary,kind:'阶段记录'})),
      tools:[],graphs:{},artifacts:[],actions:[],executed:[],report:null,
      stop:r.completion==='部分完成'?'未取得完整传输文件清单，需继续核查传输范围。':null
    }));
    const design=new Map((window.designInvestigationRuns||[]).filter(r=>r.fixture&&!r.recorded).map(r=>[r.id,r]));
    const illustrated=reference.map(r=>design.has(r.id)?structuredClone(design.get(r.id)):r);
    const saved=window.savedInvestigationRuns||[];
    return [...illustrated,...(window.alertFlowWorkspace?.runs(saved)||saved),...(window.aisoc20RecordedData?.runs||[]),...(window.persistedCaseData?.runs||[]),...(window.pageShowcaseData?.runs||[]),...(store.caseDemoRuns||[])].map(normalizeRun);
  }
  function forAlerts(store,alerts){const ids=new Set(alerts.map(a=>a.id));return runs(store).filter(r=>r.alertIds.some(id=>ids.has(id)));}
  function forCase(store,c){
    const all=runs(store),sameSource=r=>sameScope(r,c);
    const members=new Set(c.alertIds||[]),references=new Set([...(c.sourceRunIds||[]),...(c.retainedRunIds||[])]);
    return all.filter(r=>sameSource(r)&&(
      r.caseId===c.id ||
      (!!c.sourceCaseId&&r.sourceCaseId===c.sourceCaseId) ||
      references.has(r.id) ||
      ((!r.caseId||r.caseId===c.id)&&r.alertIds.some(id=>members.has(id)))
    ));
  }

  function selected(rows,id){return rows.find(r=>r.id===id)||rows[0]||null;}
  function latestFinished(rows){
    const stamp=r=>{const end=Date.parse(r.ended);return Number.isFinite(end)?end:Number.isFinite(Date.parse(r.started))?Date.parse(r.started):-Infinity;};
    return rows.filter(r=>r.status==='completed'&&r.completion!=='not_escalated').slice().sort((a,b)=>stamp(b)-stamp(a))[0]||null;
  }
  function chain(store,members,seedId,hours=24){
    const seed=members.find(a=>a.id===seedId)||members[0];if(!seed)return {seed:null,rows:[]};
    const ids=new Set(seed.entityIds||[]),stamp=Date.parse(seed.event_time||seed.first);
    return {seed,rows:members.filter(a=>a.id!==seed.id&&!a.persistedRecord&&Math.abs(Date.parse(a.event_time||a.first)-stamp)<=hours*3600000).map(a=>({alert:a,shared:(a.entityIds||[]).filter(id=>ids.has(id))})).filter(x=>x.shared.length).sort((a,b)=>Date.parse(b.alert.event_time||b.alert.first)-Date.parse(a.alert.event_time||a.alert.first))};
  }
  function assessments(store,members){
    const all=runs(store),classifications={'True positive':'true_positive','False positive':'false_positive',Informational:'benign_true_positive'};
    return members.map(alert=>{
      const linked=all.filter(r=>r.alertIds.includes(alert.id));
      // A triage verdict can only be attributed here when the Run has one input.
      const triages=linked.filter(r=>r.alertIds.length===1&&r.triage?.verdict);
      const decision=alert.disposition||classifications[alert.classification]||null;
      const investigations=linked.filter(r=>window.alertFlowWorkspace?window.alertFlowWorkspace.started(r):['partial','completed'].includes(r.completion));
      return {alert,decision,triages,linked,investigations,explanation:alert.detailMaterial?.explanation||null,
        hasDecision:!!decision||triages.length>0,
        needsReview:['needs_review','escalate'].includes(decision)||linked.some(r=>r.completion==='partial'||r.verdict==='needs_review')};
    });
  }
  function coverage(rows){return {total:rows.length,decided:rows.filter(x=>x.hasDecision).length,investigated:rows.filter(x=>x.investigations.length).length,review:rows.filter(x=>x.needsReview).length,unknown:rows.filter(x=>!x.hasDecision).length};}
  function inputEvidence(store,run){const ids=new Set(run.alertIds);return store.evidence.filter(e=>ids.has(e.alertId));}
  function sharedObjects(store,members){
    const sources=new Map();
    for(const alert of members)for(const id of new Set(alert.entityIds||[])){
      if(!sources.has(id))sources.set(id,new Map());sources.get(id).set(alert.id,alert);
    }
    return [...sources].filter(([,alerts])=>alerts.size>1).map(([id,alerts])=>({id,entity:store.assets.find(e=>e.id===id),alerts:[...alerts.values()]})).sort((a,b)=>b.alerts.length-a.alerts.length);
  }
  return {runOutcome,caseAssessment,pendingScope,pendingTasks,tacticTone,normalizeRun,humanTasks,investigationLabel,runMetrics,activeStatuses,caseRecord,graphContext,sameScope,runs,forAlerts,forCase,selected,latestFinished,chain,assessments,coverage,inputEvidence,sharedObjects};
})();

window.createInvestigationWorkspace = function(ctx){
  const {store,esc,I,btn,badge,severity,state,currentRoute,currentCase,scopeAlerts,getAlert,getAsset,navigate,render,downloadFile}=ctx;
  const M=window.investigationWorkspaceModel;
  const names={completed:'已结束',queued:'排队中',running:'运行中',failed:'失败',partial:'部分交付',not_escalated:'未升级调查',needs_review:'待复核',escalate:'需人工跟进',benign:'正常行为',true_positive:'真实威胁',false_positive:'误报',benign_true_positive:'预期活动',reviewed:'已形成调查结果',confirmed_incident:'模型判定为安全事件'};
  const statuses={success:'已返回',empty:'无候选关系',not_linked:'未关联 Case',unavailable:'查询不可用',error:'查询失败'};
  const format=v=>v?new Date(typeof v==='number'?v:String(v).replace(' ','T')).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}):'未记录';
  const json=v=>`<pre class="iv-json">${esc(JSON.stringify(v,null,2))}</pre>`;
  const text=v=>typeof v==='string'?v:JSON.stringify(v);
  const card=(title,body,extra='')=>`<article class="iv-card ${extra}"><h3>${title}</h3>${body}</article>`;
  const no=(title,body='')=>`<div class="iv-empty">${I('search',24)}<strong>${title}</strong>${body?`<p>${body}</p>`:''}</div>`;
  const alertLink=id=>{const a=getAlert(id);return a?`<button class="iv-alert-link" data-action="alert" data-id="${esc(id)}">${I('shield',14)}<span>${esc(a.title)}</span>${severity(a.severity)}</button>`:`<span class="iv-mono">${esc(id)}</span>`;};
  const metric=(label,value,detail='')=>`<div><span>${label}</span><strong>${esc(value??'—')}</strong>${detail?`<small>${esc(detail)}</small>`:''}</div>`;
  const unifiedGraph=window.createUnifiedInvestigationGraph({...ctx,format});
  function route(run,view='overview',extra={}){
    const r=currentRoute(),inCase=r.page==='cases'&&r.id,q=new URLSearchParams(inCase?{run:run.id,view,...extra}:extra);
    return `${inCase?`#/cases/${encodeURIComponent(r.id)}/investigations`:`#/investigations/${encodeURIComponent(run.id)}/${view}`}${q.size?'?'+q:''}`;
  }
  function queryStatus(t){
    let result;try{result=JSON.parse(t.result);}catch{}
    return {unavailable:'资料不可用',empty:'未匹配记录',error:'查询失败'}[result?.status]||(t.success===false?'查询失败':t.resultFormat==='saved_result'?'已保存返回':'已保存返回摘要');
  }
  function references(run,refs){
    if(!Array.isArray(refs))return '';
    return [...new Set(refs.filter(id=>typeof id==='string'))].map(id=>{
      const query=run.tools.find(t=>t.id===id),artifact=run.artifacts.find(a=>a.id===id);
      if(query)return `<a class="iv-reference-link" href="${route(run,'tools',{query:id,from:'process'})}">${I('search',13)}<span>${esc(query.name)}</span><small>${esc(queryStatus(query))}</small></a>`;
      if(artifact)return `<a class="iv-reference-link" href="${route(run,'tools',{artifact:id,from:'process'})}">${I('file',13)}<span>${esc(artifact.kind||id)}</span></a>`;
      return `<span class="iv-unresolved-reference">${esc(id)} · 未保存对应条目</span>`;
    }).join('');
  }
  function nextWork(run,compact=false){
    const gaps=run.depth?.unavailable_data||[];
    if(compact&&(run.actions||[]).length)return `${actionList(run.actions.slice(0,2))}${run.actions.length>2?'<p class="iv-note">更多建议见本次调查。</p>':''}<a class="iv-link" href="${route(run,'report')}">查看建议与执行记录 →</a>`;
    return `${run.stop?`<p>${esc(run.stop)}</p>`:''}${gaps.length?`<div class="iv-tags">${gaps.map(x=>badge(text(x),'amber')).join('')}</div>`:''}${actionList(run.actions||[])||(!run.stop&&!gaps.length?'<p class="iv-muted">暂无已记录的后续建议。</p>':'')}<a class="iv-link" href="${route(run,'report')}">查看建议与执行记录 →</a>`;
  }
  function available(){const r=currentRoute();return r.page==='cases'?M.forCase(store,currentCase()):M.runs(store);}
  function active(){const r=currentRoute(),rows=available();const id=r.page==='investigations'?r.id:new URLSearchParams(r.search).get('run');return id?rows.find(x=>x.id===id):rows[0];}
  function brief(run){return `<span class="iv-run-status">${run.investigationKind?badge(M.investigationLabel(run),'blue'):''}${badge(names[run.status]||run.status)}${badge(run.completion==='completed'?'完整交付':names[run.completion]||(['running','queued','pending','starting','waiting'].includes(run.status)?'尚未交付':'完整性未记录'),run.completion==='partial'?'amber':'blue')}</span>`;}
  function executionMetrics(run){
    const m=M.runMetrics(run),seconds=m.durationMs===null?null:Math.floor(m.durationMs/1000);
    const duration=seconds===null?(M.activeStatuses.has(run.status)?'尚未结束':'未记录'):seconds<60?`${seconds} 秒`:seconds<3600?`${Math.floor(seconds/60)} 分 ${seconds%60} 秒`:`${Math.floor(seconds/3600)} 时 ${Math.floor(seconds%3600/60)} 分`;
    const count=v=>v===null?'未记录':v.toLocaleString();
    return `<dl class="iv-run-metrics" aria-label="本轮执行统计"><div><dt title="本轮开始到结束的总历时，包含等待；不代表模型处理时间">本轮耗时</dt><dd>${duration}</dd></div><div><dt title="已保存的工具查询条目数，不等于完整工具调用总量">工具记录</dt><dd><a href="${route(run,'tools')}">${m.toolRecords} 条</a></dd></div><div><dt>模型调用</dt><dd>${count(m.calls)}</dd></div><div><dt>Tokens</dt><dd>${count(m.tokens)}</dd></div></dl>`;
  }
  function linkedRuns(){
    const rows=currentRoute().page==='cases'?M.forCase(store,currentCase()):M.forAlerts(store,scopeAlerts());return `<div class="iv-root"><div class="iv-heading"><div><h2>${currentRoute().page==='cases'?'调查历史':'关联调查'}</h2><p>查看每轮结果、输入范围与执行用量。</p></div></div>${rows.length?rows.map(r=>`<article class="iv-card iv-run-link">${brief(r)}<h3>${esc(r.title)}</h3><p>${esc((r.findings||[]).map(text).join(' ').slice(0,200))}</p>${executionMetrics(r)}<div class="iv-foot"><span>${r.alertIds.length} 条输入告警 · ${format(r.started)}</span><a class="button primary" href="${route(r)}">打开调查 ${I('external',14)}</a></div></article>`).join(''):no('尚无调查记录','已有告警和上下文仍可在事件中查看。')}</div>`;
  }
  function incidentSummary(){
    const a=scopeAlerts(),rows=M.forAlerts(store,a),entities=new Set(a.flatMap(x=>x.entityIds)),times=a.map(x=>Date.parse(x.event_time||x.first)).filter(Number.isFinite);
    return `<div class="iv-root iv-context-strip"><div><span class="iv-eyebrow">事件上下文</span><strong>告警与已有线索</strong><p>查看关联依据，确定需要调查的范围。</p></div><div class="iv-inline-metrics">${metric('成员告警',a.length)}${metric('关联实体',entities.size)}${metric('发生范围',times.length?`${format(Math.min(...times))} — ${format(Math.max(...times))}`:'—')}${metric('已有调查',rows.length)}</div><a class="button" href="#/incidents/${currentRoute().id}/investigations">查看调查 ${I('chevron',14)}</a></div>`;
  }
  const incidentLink=(tab,query='')=>`#/incidents/${encodeURIComponent(currentRoute().id)}/${tab}${query}`;
  const decisionBadge=value=>badge(names[value]||value||'尚无判定',value==='true_positive'?'red':['needs_review','escalate'].includes(value)?'amber':value?'blue':'');
  function assessmentRows(){return M.assessments(store,scopeAlerts()).sort((a,b)=>Date.parse(b.alert.event_time||b.alert.first)-Date.parse(a.alert.event_time||a.alert.first));}
  function basicRow(row){
    const a=row.alert,exp=row.explanation;
    const triage=row.triages.map(r=>`<div class="iv-assessment-source"><span>AI 首次分诊</span>${decisionBadge(r.triage.verdict)}${r.triage.confidence!=null?`<small>分诊评分 ${Math.round(r.triage.confidence*100)}</small>`:''}<a href="${route(r)}">查看来源</a></div>`).join('');
    return `<tr><td><a class="iv-alert-title" href="#/alerts/${encodeURIComponent(a.id)}/overview">${esc(a.title)}</a><small class="iv-table-meta">${format(a.event_time||a.first)} · ${esc(a.source)}</small></td><td>${severity(a.severity)}<div class="iv-table-meta">${state(a.status)}</div></td><td><div class="iv-assessment-source"><span>当前判定</span>${decisionBadge(row.decision)}</div>${triage}</td><td>${exp?.summary?`<details class="iv-explanation"><summary>告警解释${exp.generatedAt?' · '+format(exp.generatedAt):''}</summary><p>${esc(exp.summary)}</p>${(exp.suggestedActions||[]).map(x=>`<p><b>${esc(x.title||x.description||'建议')}</b>${x.rationale?' · '+esc(x.rationale):''}</p>`).join('')}<a href="#/alerts/${encodeURIComponent(a.id)}/overview">查看告警解释</a></details>`:''}${row.linked.map(r=>`<a class="iv-linked-source" href="${route(r)}">${I('search',12)}<span>${esc(r.title)}<small>${r.alertIds.length} 条输入 · ${r.completion==='completed'?'完整交付':esc(names[r.completion]||'完整性未记录')}</small></span>${I('chevron',12)}</a>`).join('')}${!exp?.summary&&!row.linked.length?'<span class="iv-muted">暂无可回查的基础调查材料</span>':''}</td></tr>`;
  }
  function basicTable(rows){return rows.length?`<div class="iv-table-scroll"><table class="iv-assessment-table"><thead><tr><th>告警与来源</th><th>等级 / 处理状态</th><th>已有判定</th><th>解释与关联调查</th></tr></thead><tbody>${rows.map(basicRow).join('')}</tbody></table></div>`:no('没有符合条件的告警','可切换筛选查看其他成员告警。');}
  function basicInvestigations(){
    const rows=assessmentRows(),c=M.coverage(rows),q=new URLSearchParams(currentRoute().search),filter=q.get('filter')||'all';
    const shown=rows.filter(x=>filter==='decided'?x.hasDecision:filter==='review'?x.needsReview:filter==='unknown'?!x.hasDecision:filter==='investigated'?x.investigations.length:true);
    const filters=[['all','全部告警',c.total],['decided','已有判定',c.decided],['investigated','有关联调查',c.investigated],['review','待继续核查',c.review],['unknown','未记录判定',c.unknown]];
    return `<div class="iv-root"><div class="iv-heading"><div><h2>基础调查汇总</h2><p>逐条查看已有判定、告警解释与关联调查，回到来源核对。</p></div></div><nav class="iv-filter-tabs" aria-label="基础调查筛选">${filters.map(([key,label,n])=>`<a href="${incidentLink('triage','?filter='+key)}" ${filter===key?'aria-current="page"':''}>${label}<b>${n}</b></a>`).join('')}</nav>${basicTable(shown)}<p class="iv-note">关联调查可能包含多条输入；其综合发现请在对应调查中查看。未记录判定不代表尚未开展任何工作。</p></div>`;
  }
  function attackCoverage(alerts,{panel=false}={}){
    const counts=new Map();for(const a of new Map(alerts.map(a=>[a.id,a])).values()){const name=String(a.category||'').trim()||'未分类';counts.set(name,(counts.get(name)||0)+1);}const phases=[...counts];
    if(panel)return `<article class="card case-attack-coverage" aria-label="ATT&CK 阶段覆盖"><div class="card-title"><h3>ATT&CK 阶段覆盖</h3><span class="spacer"></span><button type="button" class="icon-button" aria-label="阶段覆盖说明：按成员告警的战术分类统计，不代表检测覆盖率或攻击成功" title="按成员告警的战术分类统计；数字为告警数，不代表检测覆盖率或攻击成功。">${I('info',14)}</button></div><div class="case-stage-rows">${phases.map(([name,n])=>`<div class="case-stage-row"><span class="tactic-label tactic-tone-${M.tacticTone(name)}">${esc(name)}</span><span><b>${n}</b> 条告警</span></div>`).join('')||'<p class="muted">暂无成员告警</p>'}</div></article>`;
    return `<section class="iv-card iv-attack-coverage" aria-label="ATT&CK 阶段覆盖"><div class="iv-coverage-heading"><h4>ATT&CK 阶段覆盖</h4><button type="button" class="icon-button" aria-label="阶段覆盖说明：按成员告警的战术分类统计，不代表检测覆盖率或攻击成功" title="按成员告警的战术分类统计；数字为告警数，不代表检测覆盖率或攻击成功。">${I('info',14)}</button></div><div class="iv-stage-list">${phases.map(([name,n])=>`<div class="iv-stage-item tactic-tone-${M.tacticTone(name)}"><span>${esc(name)}</span><b>${n}</b><small>告警</small></div>`).join('')||'<span class="iv-muted">暂无成员告警</span>'}</div></section>`;
  }
  function incidentOverview(){
    const a=scopeAlerts(),inc=store.incidents.find(x=>x.id===currentRoute().id),context=ctx.incidentContext(inc),shared=M.sharedObjects(store,a);
    const occurrence=alert=>{const value=alert.event_time??(alert.persistedRecord?null:alert.first);return Number.isFinite(Date.parse(value))?value:null;};
    const timeline=a.slice().sort((x,y)=>{const tx=Date.parse(occurrence(x)),ty=Date.parse(occurrence(y));return (Number.isFinite(ty)?ty:-Infinity)-(Number.isFinite(tx)?tx:-Infinity);});
    const times=a.map(x=>Date.parse(occurrence(x))).filter(Number.isFinite);
    const description=inc.recordedIncident?ctx.incidentSummaryText(inc,a,context.hostNames).description:inc.description;
    const stages=attackCoverage(a);
    const facts=`<div class="iv-incident-facts"><a href="${incidentLink('alerts')}"><span>成员告警</span><strong>${a.length}</strong></a><a href="${incidentLink('assets')}" title="成员告警涉及的主机"><span>涉及资产</span><strong>${context.hostNames.length}</strong></a><span class="iv-occurrence-range"><span>发生范围</span><time>${times.length?`${format(Math.min(...times))} — ${format(Math.max(...times))}`:'未记录'}</time></span></div>`;
    const information=card('事件是什么',`<p class="iv-event-description-text">${esc(description||'尚未填写事件说明。')}</p>${facts}${inc.tags.length?`<div class="iv-event-tags"><span>事件标记</span>${inc.tags.map(t=>badge(t,'blue')).join('')}</div>`:''}`,'iv-event-information');
    const objectLabel=row=>row.entity?`<button class="iv-shared-object" data-action="entity" data-id="${esc(row.id)}" title="查看共同对象 ${esc(row.entity.name)}">${I(row.entity.type,12)}<span>${esc(row.entity.name)}</span></button>`:`<span class="iv-shared-object">${esc(row.id)}</span>`;
    const chronology=`<section class="iv-correlation-timeline" aria-label="告警时间线"><div class="iv-correlation-heading"><h4>告警时间线</h4><span>最新在前</span></div><div class="iv-incident-timeline">${timeline.slice(0,6).map(x=>{const common=shared.filter(row=>row.alerts.some(alert=>alert.id===x.id));return `<div class="timeline-item"><span class="timeline-dot ${x.severity==='高'?'high':''}"></span><div><div class="iv-timeline-meta"><time>${format(occurrence(x))}</time><span>${esc(x.category||'未分类')}</span></div>${alertLink(x.id)}<div class="iv-timeline-common">${common.length?common.map(objectLabel).join(''):'<span class="iv-note">未记录与其他成员共享的对象</span>'}</div></div></div>`;}).join('')||no('暂无成员告警')}</div><a class="iv-link" href="${incidentLink('alerts')}">查看全部 ${a.length} 条告警 →</a></section>`;

    const basis=card('为什么关联在一起',`<p class="iv-note iv-correlation-intro">结合告警发生时间与共同对象，查看成员之间的联系。</p><div class="iv-correlation-layout">${chronology}<section class="iv-correlation-basis" aria-label="共同线索"><div class="iv-correlation-heading"><h4>共同线索</h4><span>${shared.length} 个共享对象</span></div><div class="iv-association-list">${shared.map(row=>`<article><div class="iv-association-object"><span>${esc(({device:'共同主机',user:'共同账号',ip:'共同 IP',file:'共同文件',cloud:'共同资源'})[row.entity?.type]||'共同对象')}</span>${row.entity?`<button class="link-button" data-action="entity" data-id="${esc(row.id)}">${I(row.entity.type,16)} ${esc(row.entity.name)}</button>`:`<code>${esc(row.id)}</code>`}</div><details><summary>${row.alerts.length} 条告警共同涉及</summary><div class="iv-association-alerts">${row.alerts.map(x=>alertLink(x.id)).join('')}</div></details></article>`).join('')||'<p class="iv-muted">尚未记录成员之间的共享对象。</p>'}</div><p class="iv-note iv-basis-caveat">${!inc.recordedIncident&&inc.correlationReason?esc(inc.correlationReason):'共享对象是可核对的共同点；当前记录未提供具体归并规则。'}</p></section></div>`,'iv-incident-basis');
    return `<div class="iv-root iv-incident-home">${stages}${information}${basis}${ctx.incidentCaseCard(inc)}</div>`;
  }

  function queue(){
    const rows=M.runs(store).slice().sort((a,b)=>Number(!!b.recorded)-Number(!!a.recorded));return `<section class="page iv-root"><div class="iv-heading"><div><span class="iv-eyebrow">AI INVESTIGATIONS</span><h1>调查运行</h1><p>按运行查看分析、材料与交付结果。自动调查可以没有 Case。</p></div><a class="button" href="#/cases">返回 Cases</a></div><div class="iv-stats">${metric('运行记录',rows.length)}${metric('部分交付',rows.filter(r=>r.completion==='partial').length)}${metric('未升级调查',rows.filter(r=>r.completion==='not_escalated').length)}${metric('关联 Case',store.cases.filter(c=>M.forCase(store,c).length).length)}</div><div class="iv-run-grid">${rows.map(r=>`<a class="iv-card iv-run-tile" href="#/investigations/${r.id}/overview"><div class="iv-foot">${brief(r)}${I('chevron',17)}</div><h3>${esc(r.title)}</h3><p>${esc((r.findings||[]).map(text).join(' ').slice(0,160)||'查看已保存的运行记录')}</p><div class="iv-foot"><small>${r.alertIds.length} 条输入告警</small><small>${format(r.started)}</small></div><code>${esc(r.id)}</code></a>`).join('')}</div></section>`;
  }
  function inputMaterial(run){
    const evidence=M.inputEvidence(store,run),labels={Malicious:'恶意',Suspicious:'可疑',Clean:'未发现威胁'};
    return evidence.length?`<div class="iv-material-list">${evidence.map(e=>`<div><button data-action="evidence" data-id="${esc(e.id)}">${I('file',14)}<span>${esc(e.name)}</span></button><small>${esc(e.origin)} · ${esc(labels[e.verdict]||e.verdict)}</small><a href="#/alerts/${encodeURIComponent(e.alertId)}/overview">来源告警</a></div>`).join('')}</div>`:'<p class="iv-muted">没有随输入告警关联的证据条目。</p>';
  }
  function incidentMaterials(){
    const alerts=scopeAlerts(),runs=M.forAlerts(store,alerts);
    return `<div class="iv-root"><div class="iv-heading"><div><h2>证据与处置</h2><p>回查源告警资料，以及各次调查保存的查询、分析和响应记录。</p></div></div><div class="iv-stack">${card('源告警资料',alerts.map(a=>`<article class="iv-action-item">${alertLink(a.id)}<p>${esc(a.description||'')}</p><div class="iv-foot"><span>${esc(a.source)} · ${format(a.event_time||a.first)}</span><a href="#/alerts/${encodeURIComponent(a.id)}/raw">查看原始数据</a></div></article>`).join(''))}${card('关联调查材料',runs.map(r=>`<article class="iv-action-item"><h4>${esc(r.title)}</h4>${brief(r)}<p>${r.tools.length} 条查询记录 · ${r.artifacts.length} 份保存材料 · ${r.executed.length} 条已执行动作记录</p><div class="row wrap"><a class="button small" href="${route(r,'tools')}">查询与证据</a><a class="button small" href="${route(r,'report')}">报告与响应</a></div></article>`).join('')||no('尚无关联调查材料'))}<p class="iv-note">源告警对象、查询材料与已定性证据分别核对；建议动作不代表已审批或已执行。</p></div></div>`;
  }
  function incidentRelations(embedded=false){
    const members=scopeAlerts(),g=window.alertFlowWorkspace.relations(store,members);
    return `<div class="iv-root">${embedded?'':`<div class="iv-heading"><div><h2>事件关联关系</h2><p>成员告警报告的主机、账户与线索。点击告警或对象可回查来源。</p></div><a class="button" href="${incidentLink('investigations')}">关联 AI 调查</a></div>`}${relationDiagram(g)}<p class="iv-note">连线来自源告警对象关联，不表示已验证攻击路径；调查时保存的 Chain、Path 与关联范围见对应调查。</p></div>`;
  }
  function actionList(actions){return actions.map(a=>`<div class="iv-action-item"><p>${esc(typeof a==='string'?a:a.description||a.action_type||text(a))}</p>${typeof a==='object'?`${a.target?`<small>目标：${esc(a.target)}</small>`:''}${a.requires_approval?badge('需要审批','amber'):''}${a.rationale?`<details><summary>建议依据</summary><p>${esc(a.rationale)}</p></details>`:''}`:''}</div>`).join('');}
  const stepSummary=s=>s.payload?.step_status==='skipped'?'已跳过 · '+(s.payload.reason||'未执行该步骤'):s.summary;
  function overview(run){
    const findings=run.findings||[],depth=run.depth||{},members=currentRoute().page==='cases'?scopeAlerts().length:null,evidence=M.inputEvidence(store,run),work=(run.steps||[]).filter(s=>s.kind!=='tool_call'),isTriage=run.completion==='not_escalated';
    const outcome=M.runOutcome(run);
    const result=card(isTriage?'本次分诊结果':'本轮调查结论',`<div class="iv-outcome-purpose">${esc(outcome.purpose)}</div><h3 class="iv-outcome-title">${esc(outcome.conclusion)}</h3><div class="iv-foot">${brief(run)}${run.verdict?decisionBadge(run.verdict):''}</div>${outcome.findings.slice(0,3).map(f=>`<p class="iv-finding">${esc(f)}</p>`).join('')}${outcome.basis.length?`<h4>支持依据</h4><ul>${outcome.basis.map(f=>`<li>${esc(f)}</li>`).join('')}</ul>`:''}<div class="iv-result-impact"><div><span>相对已有结果</span><p>${esc(outcome.change)}</p></div><div><span>对案件的影响</span><p>${esc(outcome.impact)}</p></div></div>${outcome.limitations.length?`<div class="iv-result-limits"><b>仍待确认</b><p>${outcome.limitations.map(esc).join('；')}</p></div>`:''}${run.savedAt?`<p class="iv-note">${esc(run.savedBy||'用户')} · ${format(run.savedAt)} 保存本条结论；未自动修改案件判断。</p>`:''}<div class="iv-reading-links"><a href="${route(run,'process')}">查看分析依据 →</a><a href="${route(run,'report')}">查看调查报告与响应 →</a></div>`,'iv-findings-card');
    const materials=card('可核查材料',`<div class="iv-material-counts"><a href="${route(run,'tools')}"><b>${run.tools.length}</b><span>本次查询记录</span></a><a href="${route(run,'tools')}"><b>${run.artifacts.length}</b><span>保存材料</span></a><a href="${route(run,'tools')}"><b>${evidence.length}</b><span>输入关联证据</span></a></div>${run.tools.length?`<h4>本次查询</h4><div class="iv-query-list">${run.tools.slice(0,3).map(t=>`<a href="${route(run,'tools',t.id?{query:t.id,from:'overview'}:{})}">${I('search',14)}<span>${esc(t.name)}</span><small>${format(t.time)}</small>${I('chevron',12)}</a>`).join('')}</div>`:''}${evidence.length?`<h4>输入告警携带的证据</h4>${inputMaterial(run)}`:''}${!run.tools.length&&!evidence.length?'<p class="iv-muted">暂无可展开的查询或输入证据。已有发现和步骤仍可查看。</p>':''}<a class="iv-link" href="${route(run,'tools')}">核对查询返回与材料来源 →</a>`);
    const progress=card('已开展的工作',`${work.length?`<ol class="iv-work-list">${work.slice(-4).map(s=>`<li><i>${I('clock',12)}</i><div><strong>${esc(s.name)}</strong><p>${esc(stepSummary(s)||'已有过程记录')}</p></div></li>`).join('')}</ol>`:'<p class="iv-muted">尚无可回查的步骤记录。</p>'}<a class="iv-link" href="${route(run,'process')}">查看完整分析过程 →</a>`);
    const limitations=run.stop||(depth.unavailable_data||[]).length?card('未完成与待核查',`${run.stop?`<p>${esc(run.stop)}</p>`:''}${(depth.unavailable_data||[]).length?`<h4>尚未取得的资料</h4><div class="iv-tags">${depth.unavailable_data.map(x=>badge(x,'amber')).join('')}</div>`:''}<a class="iv-link" href="${route(run,'tools')}">查看查询范围和返回内容 →</a>`,'iv-warning'):'';
    const response=card('后续处理',`<div class="iv-response-columns"><section><h4>调查建议</h4>${actionList(run.actions)||`<p class="iv-muted">未记录具体建议动作。</p>`}${run.remediation?`<p class="iv-note">调查记录中的处置状态：${esc(run.remediation)}</p>`:''}</section><section><h4>实际执行 <span>${run.executed.length}</span></h4>${run.executed.map(a=>`<p>${esc(text(a))}</p>`).join('')||'<p class="iv-muted">暂无已执行动作记录。</p>'}</section></div><a class="iv-link" href="${route(run,'report')}">查看报告与响应详情 →</a>`);
    const scope=card('本次调查范围',`<div class="iv-pair"><span>输入告警</span><b>${run.alertIds.length}</b></div>${members!==null?`<div class="iv-pair"><span>当前 Case 成员</span><b>${members}</b></div><p class="iv-note">新成员不会自动加入已经结束的调查。</p>`:''}<details class="iv-raw"><summary>查看输入告警</summary>${run.alertIds.map(alertLink).join('')}</details>${run.input?`<details class="iv-raw"><summary>查看本次保存的输入</summary>${json(run.input)}${run.input_summary?`<h4>输入摘要</h4><pre class="iv-tool-result">${esc(run.input_summary)}</pre>`:''}</details>`:''}`);
    const meta=`<details class="iv-card iv-execution"><summary>${I('clock',15)}运行详情与用量 ${I('down',12)}</summary>${executionMetrics(run)}<dl class="iv-definition"><dt>Run ID</dt><dd class="iv-mono">${esc(run.id)}</dd><dt>Run 状态</dt><dd>${esc(names[run.status]||run.status)}</dd><dt>交付完整性</dt><dd>${run.completion==='completed'?'完整交付':esc(names[run.completion]||'未记录')}</dd><dt>Run 开始</dt><dd>${format(run.started)}</dd><dt>Run 结束</dt><dd>${format(run.ended)}</dd><dt>最后记录</dt><dd>${format(run.steps?.at(-1)?.time)}</dd><dt>费用</dt><dd>${run.unpriced?'未定价 · '+run.unpriced+' 次调用':'未提供'}</dd></dl>${run.timeNote?`<p class="iv-note">${esc(run.timeNote)}</p>`:''}</details>`;
    return `<div class="iv-overview"><div class="iv-stack">${result}${materials}${progress}${limitations}${response}</div><aside class="iv-stack">${scope}${run.triage?card('首次分诊',`<div class="iv-pair"><span>判定</span>${decisionBadge(run.triage.verdict)}</div><div class="iv-pair"><span>分诊评分</span><b>${run.triage.confidence!=null?Math.round(run.triage.confidence*100):'—'}</b></div><p class="iv-note">保留初始判断，与本次调查结论分别核对。</p>`):''}${currentRoute().page==='cases'?card('案件跟进',`<a class="iv-follow-link" href="#/cases/${encodeURIComponent(currentRoute().id)}/tasks"><span>人工任务</span><b>${M.pendingTasks(currentCase()).length}</b></a><a class="iv-follow-link" href="#/cases/${encodeURIComponent(currentRoute().id)}/comments"><span>评论与附件</span>${I('chevron',14)}</a>`):''}${meta}</aside></div>`;
  }
  const stageNames={triage:'告警分诊',enrichment:'上下文补充',investigation:'深度调查',attack_path:'攻击路径分析',recon:'侦察分析 · Recon',forensic:'取证分析 · Forensic',responder:'响应分析 · Responder',report:'报告整理'};
  function stages(run){return (run.steps||[]).filter(s=>s.kind==='阶段记录'||s.kind==='graph_step'||['recon','forensic','responder','report'].includes(s.kind));}
  function process(run){
    const rows=stages(run),d=run.depth;
    const conversation=run.conversation?.length?card('已保存的对话',run.conversation.map(m=>`<div class="iv-saved-message"><b>${m.role==='assistant'?'AI 助手':'用户'}</b><small>${format(m.time)}</small><p>${esc(m.text)}</p></div>`).join('')+`<p class="iv-note">保存时的对话快照；后续聊天不会改写本条结论。</p>`):'';
    const snapshot=run.referenceSnapshot,c=store.cases.find(c=>c.id===run.caseId),allowed=c?M.forCase(store,c):[];
    const savedReferences=snapshot?card('分析依据 · 当时的材料',`<p class="iv-note">读取于 ${format(snapshot.capturedAt)}；后续编辑人工任务不会改写此处内容。</p>${(snapshot.runs||[]).map(r=>`<article class="iv-action-item"><h4>${esc(r.title)}</h4><p>${esc(r.outcome?.conclusion||'未保存结论')}</p><small>${r.alertIds.length} 条输入告警 · ${format(r.ended||r.started)}</small>${allowed.some(x=>x.id===r.id)?`<p><a href="#/cases/${encodeURIComponent(c.id)}/investigations?${new URLSearchParams({run:r.id,view:'overview'})}">查看来源调查 →</a></p>`:''}</article>`).join('')}${(snapshot.tasks||[]).map(t=>`<article class="iv-action-item"><h4>${esc(t.title)}</h4><p>${esc(t.result||'当时尚未填写结果')}</p><small>${esc(t.owner||'未分配')} · ${esc(({Completed:'已完成','In progress':'进行中',New:'未开始',Cancelled:'已取消'})[t.status]||t.status)} · ${format(t.completedAt||t.updatedAt||t.createdAt)}</small>${(t.referenceContext?.alertIds||[]).length?`<p>确认范围：${t.referenceContext.alertIds.map(id=>{const a=(run.input?.alerts||[]).find(a=>a.id===id);return esc(a?.title||id);}).join('、')}</p>`:''}${c&&M.humanTasks(c).some(x=>x.id===t.id)?`<p><a href="#/cases/${encodeURIComponent(c.id)}/tasks">查看人工任务当前记录 →</a></p>`:''}</article>`).join('')}`):'';
    const phases=rows.map((s,i)=>{
      const summary=s.payload?.step_status==='skipped'?stepSummary(s):s.adopted?.summary||stepSummary(s);
      return card(`<span class="iv-phase-number">${i+1}</span>${esc(stageNames[s.payload?.node||s.kind]||stageNames[s.name]||s.name)}`,`<p>${esc(summary||'已有阶段记录')}</p>${s.adopted?.evidence_ids?.length?`<div class="iv-analysis-references"><span>阶段引用</span>${references(run,s.adopted.evidence_ids)}</div>`:''}${s.adopted?`<details class="iv-raw"><summary>查看阶段采用结果</summary>${s.summary&&s.summary!==summary?`<p>阶段记录：${esc(s.summary)}</p>`:''}${json(s.adopted)}</details>`:''}<div class="iv-foot"><span>${format(s.time)}</span><span>${esc(s.name)}</span></div>${s.kind==='graph_step'&&s.payload?.step_status!=='skipped'?'<p class="iv-note">节点结束记录；分析内容见本次发现、查询返回与报告。</p>':''}`);
    }).join('')||no('暂无独立阶段记录','已有分诊或其他过程记录可在执行明细中查看。');
    return `<div class="iv-section-title"><div><h3>AI 分析</h3><p>核对已有分析、引用和限制。</p></div><a class="button small" href="${route(run,'ledger')}">执行明细 ${I('chevron',12)}</a></div><div class="iv-analysis-overview"><section class="iv-stack">${conversation}${savedReferences}${phases}</section><aside>${card('限制与下一步',nextWork(run))}</aside></div>${d?.truncated?'<div class="iv-callout">本次调查材料存在截断，请结合查询返回与限制核对。</div>':''}<p class="iv-note">阶段记录不代表证据充分，也不改变本次调查的交付完整性。</p>`;
  }
  function ledger(run){
    const d=run.depth;
    const q=new URLSearchParams(currentRoute().search),kind=q.get('kind')||'',agent=q.get('agent')||'',rows=run.steps.filter(s=>(!kind||s.kind===kind)&&(!agent||s.name===agent));
    return `<div class="iv-section-title"><div><h3>执行明细</h3><p>${rows.length} / ${run.steps.length} 条记录 · 按已有记录顺序展示</p></div><a class="button small" href="${route(run,'process')}">返回 AI 分析</a></div>${d?card('Deep 深度调查',`<div class="iv-stats">${metric('调查轮数',d.iterations)}${metric('查询方向',d.distinct_pivots)}${metric('工具记录',run.tools.length)}${metric('调查截断',d.truncated?'是':'否')}</div>${d.strategy_id?`<div class="iv-pair"><span>调查策略</span><b>${esc(d.strategy_id)}</b></div>`:''}${(d.pivots||[]).length?`<h4>已记录的查询方向</h4><div class="iv-tags">${[...new Set(d.pivots)].map(p=>badge(p,'blue')).join('')}</div>`:''}${d.narrative?`<details class="iv-raw"><summary>查看 Deep 留存内容</summary><pre class="iv-tool-result">${esc(d.narrative)}</pre></details>`:''}${run.stop?`<div class="iv-callout">停止原因：${esc(run.stop)}</div>`:''}<a class="iv-link" href="${route(run,'tools')}">核对查询范围、参数与返回 →</a>`):''}<div class="iv-ledger-controls"><label>记录类型<select data-iv-kind aria-label="记录类型"><option value="">全部类型</option>${[...new Set(run.steps.map(s=>s.kind))].map(k=>`<option value="${esc(k)}" ${k===kind?'selected':''}>${esc(k)}</option>`).join('')}</select></label><label>执行者 / 节点<select data-iv-agent aria-label="执行者或节点"><option value="">全部执行者 / 节点</option>${[...new Set(run.steps.map(s=>s.name))].map(a=>`<option value="${esc(a)}" ${a===agent?'selected':''}>${esc(a)}</option>`).join('')}</select></label></div><div class="iv-timeline">${rows.map(s=>`<details class="iv-step"><summary><span class="iv-step-dot">${I(s.kind==='tool_call'?'search':s.kind==='error'?'alert':'clock',14)}</span><span><strong>${esc(s.name||s.kind)}</strong><small>${esc(stepSummary(s)||s.kind)}</small></span><time>${format(s.time)}</time>${I('down',14)}</summary><div class="iv-step-content"><div class="iv-pair"><span>记录类型</span><code>${esc(s.kind)}</code></div>${s.id?`<div class="iv-pair"><span>记录 ID / seq</span><code>${esc(s.id)} / ${esc(s.seq)}</code></div>`:""}${s.payload&&Object.keys(s.payload).length?json(s.payload):`<p>${esc(s.summary||'未保存该步骤的详细输入输出。')}</p>`}</div></details>`).join('')||no('没有符合筛选条件的记录')}</div><p class="iv-note">按保存内容回查；未保存的提示词、回复或引用不会从报告反推补齐。</p>`;
  }
  function artifactCatalog(run,selectFromURL=true){
    if(!run.artifacts.length)return no('未保存独立工件目录');
    const selected=selectFromURL?new URLSearchParams(currentRoute().search).get('artifact'):null;
    const invalid=selected&&!run.artifacts.some(a=>a.id===selected);
    return `${invalid?no('本次调查中没有该材料','请在下方选择属于当前调查的材料。'):''}<div class="iv-artifacts">${run.artifacts.map(a=>{
      const body=run.artifactBodies?.[a.id];
      const content=body?.mode==='metadata'?`<p class="iv-note">${esc(body.note)}</p>`:body?`<h4>${body.mode==='full'?'已保存内容':'已保存内容节选'}</h4>${body.note?`<p class="iv-note">${esc(body.note)}</p>`:''}${body.format==='json'?json(body.content):`<pre class="iv-tool-result">${esc(body.content)}</pre>`}`:'<p class="iv-note">此处仅有材料目录；可读报告和链图见相应页签。</p>';
      return `<details ${selected===a.id?'open':''}><summary><strong>${esc(a.kind)}</strong><span>${a.size_bytes?.toLocaleString()??'—'} bytes</span>${I('down',12)}</summary><dl class="iv-definition"><dt>工件ID</dt><dd class="iv-mono">${esc(a.id||'未记录')}</dd><dt>原件SHA256</dt><dd class="iv-mono">${esc(a.sha256||'未记录')}</dd><dt>保存时间</dt><dd>${format(a.created_at)}</dd>${a.event_id?`<dt>关联事件记录 ID</dt><dd class="iv-mono">${esc(a.event_id)}</dd>`:''}</dl>${content}</details>`;
    }).join('')}</div>`;
  }
  function tools(run){
    const d=run.depth||{},q=new URLSearchParams(currentRoute().search),selected=q.get('query'),shown=selected?run.tools.filter(t=>t.id===selected):run.tools;
    const back=q.get('from')==='overview'?'overview':'process';
    const selection=selected?`<div class="iv-query-selection"><div><strong>${shown.length?'当前引用的查询':'本次调查中没有该查询'}</strong>${!shown.length?'<p>请查看当前调查的已有查询记录。</p>':''}</div><div class="iv-reading-links"><a href="${route(run,'tools')}">查看本轮全部查询</a><a href="${route(run,back)}">返回${back==='overview'?'调查发现':'AI 分析'}</a></div></div>`:q.has('artifact')?`<div class="iv-reading-links"><a href="${route(run,'process')}">返回 AI 分析</a></div>`:'';
    return `<div class="iv-stats">${metric('工具记录',run.tools.length)}${metric('材料截断',d.truncated?'是':run.depth?'否':'—')}</div>${selection}${(d.coverage_notes||[]).length?card('查询覆盖范围',d.coverage_notes.map(n=>`<p>${esc(n)}</p>`).join('')):''}<div class="iv-tools">${shown.map(t=>card(`${run.tools.indexOf(t)+1}. ${esc(t.name)}`,`<div class="iv-foot"><span>${format(t.time)}</span>${badge(queryStatus(t),t.success===false?'amber':'blue')}</div>${t.id?`<p class="iv-note">查询引用：<span class="iv-mono">${esc(t.id)}</span></p>`:''}<details class="iv-raw"><summary>查询参数</summary>${json(t.args)}</details><h4>返回内容</h4><pre class="iv-tool-result">${esc(t.result||'未保存返回内容')}</pre><p class="iv-note">${t.resultFormat==='saved_result'?'展示当次工具留存的返回内容。':'v1工具记录保留最多200字符摘要；空结果、不可用和查询失败以返回内容为准。'}</p>`)).join('')||(!selected?no('没有可回查的工具记录','不从报告文字补造工具调用。'):'')}</div>${card('输入告警携带的证据',inputMaterial(run))}${card('保存材料目录',artifactCatalog(run))}`;
  }
  const relationNames={CONTAINS_ALERT:'包含告警',OBSERVED_ON:'发生于',INVOLVES_USER:'涉及账户',MAPS_TO:'映射技术',CONTAINS_IOC:'包含线索'};
  function recordedGraphData(ids){
    const g=window.aisoc20RecordedData?.graph||{nodes:[],edges:[]},selected=new Set(ids);
    const edges=g.edges.filter(e=>selected.has(e.source)||selected.has(e.target)),nodeIds=new Set(edges.flatMap(e=>[e.source,e.target]));
    return {generatedAt:g.generatedAt,edges,nodes:g.nodes.filter(n=>nodeIds.has(n.id))};
  }
  function relationDiagram(g,inputIds=[]){
    if(!g.edges.length)return no('暂无保存的关系数据');
    const groups=[g.nodes.filter(n=>['host','user'].includes(n.kind)),g.nodes.filter(n=>n.kind==='alert'),g.nodes.filter(n=>!['host','user','alert'].includes(n.kind))];
    const h=Math.max(...groups.map(g=>g.length))*112+48,positions=new Map();
    groups.forEach((rows,col)=>rows.forEach((n,i)=>positions.set(n.id,{x:[16,310,694][col],y:48+i*(h-48)/rows.length,w:col===1?290:190,col})));
    const line=g.edges.map(e=>{const a=positions.get(e.source),b=positions.get(e.target);if(!a||!b)return '';const left=b.x<a.x,x1=left?a.x:a.x+a.w,x2=left?b.x+b.w:b.x,y1=a.y+32,y2=b.y+32,m=(x1+x2)/2;return `<g><title>${esc(e.label)}</title><path d="M${x1},${y1} C${m},${y1} ${m},${y2} ${x2},${y2}" marker-end="url(#iv-relation-arrow)"/></g>`;}).join('');
    const nodes=g.nodes.map(n=>{const p=positions.get(n.id),type={host:'主机',user:'账户',alert:'告警',technique:'ATT&CK 技术',asset:'IOC / 实体'}[n.kind]||n.kind,label=n.kind==='alert'?n.label.replace(/\s*\[.*?\]$/,''):n.label,chars=Array.from(label),chunk=n.kind==='alert'?20:22,lines=[];for(let i=0;i<chars.length;i+=chunk)lines.push(chars.slice(i,i+chunk).join(''));const body=`<g class="iv-map-node ${inputIds.includes(n.id)?'iv-map-input':''}"><title>${esc(n.label)}</title><rect x="${p.x}" y="${p.y}" width="${p.w}" height="78" rx="8"/><text class="iv-map-type" x="${p.x+13}" y="${p.y+19}">${esc(type)}${inputIds.includes(n.id)?' · 本次输入':''}</text><text x="${p.x+13}" y="${p.y+43}">${lines.slice(0,2).map((l,i)=>`<tspan x="${p.x+13}" dy="${i?17:0}">${esc(l)}</tspan>`).join('')}</text></g>`;return n.kind==='alert'?`<a href="#/alerts/${esc(n.id)}/overview">${body}</a>`:n.entityId?`<g data-action="entity" data-id="${esc(n.entityId)}" role="button" tabindex="0" aria-label="查看 ${esc(n.label)}">${body}</g>`:body;}).join('');
    const labels=new Map(g.nodes.map(n=>[n.id,n.label]));
    return `<div class="iv-relationship-map"><svg viewBox="0 0 900 ${h+20}" role="group" aria-label="已保存的告警与实体关系图"><defs><marker id="iv-relation-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#9bb2c8"/></marker></defs><text class="iv-map-column" x="16" y="24">主机与账户</text><text class="iv-map-column" x="310" y="24">告警</text><text class="iv-map-column" x="694" y="24">技术与线索</text><g class="iv-map-edges">${line}</g>${nodes}</svg></div><details class="iv-raw"><summary>查看 ${g.edges.length} 条原始关系</summary><div class="iv-relations">${g.edges.map(e=>`<p>${esc(labels.get(e.source)||e.source)}<span> — ${esc(relationNames[e.label]||e.label)}（${esc(e.label)}）→ </span>${esc(labels.get(e.target)||e.target)}</p>`).join('')}</div></details>`;
  }
  function flowCaseOverview(){
    const c=currentCase(),members=scopeAlerts(),runs=M.forCase(store,c).slice().sort((a,b)=>{
      const active=r=>M.activeStatuses.has(r.status)?1:0;
      return active(b)-active(a)||(Date.parse(b.started)||0)-(Date.parse(a.started)||0);
    }),assets=new Set(members.flatMap(a=>a.entityIds||[])),tasks=M.humanTasks(c).filter(t=>['New','In progress'].includes(t.status));
    const findingCards=runs.filter(r=>!M.activeStatuses.has(r.status)).slice(0,3).map(r=>{const o=M.runOutcome(r);return card(esc(o.conclusion),`<div class="iv-foot">${brief(r)}<span>${r.alertIds.length} 条本轮输入 · ${format(r.savedAt||r.ended||r.started)}</span></div><p class="iv-outcome-purpose">${esc(o.purpose)}</p>${o.findings.slice(0,2).map(f=>`<p class="iv-finding">${esc(f)}</p>`).join('')}<p class="iv-result-change">${esc(o.change)}</p><p class="iv-note">对案件：${esc(o.impact)}</p><div class="iv-reading-links"><a href="${route(r,'process')}">查看分析依据 ${I('chevron',12)}</a><a href="${route(r)}">查看本次调查</a></div>`,'iv-case-result');}).join('');
    const followRuns=runs.filter(r=>r.stop||(r.actions||[]).length||(r.depth?.unavailable_data||[]).length);
    const followup=card('待确认事项',`${followRuns.slice(0,3).map(r=>`<section class="iv-next-group"><h4>${esc(r.title)}</h4>${nextWork(r,true)}</section>`).join('')}${!followRuns.length?'<p class="iv-muted">暂无已记录的待跟进事项。</p>':''}${followRuns.length>3?`<a class="iv-link" href="#/cases/${encodeURIComponent(c.id)}/investigations">查看其他调查建议 →</a>`:''}`,'iv-case-next');

    return `<div class="iv-root iv-case-home"><div class="iv-heading"><div><h2>调查概览</h2><p>查看调查进展、已有结果和待确认事项。</p></div><a class="button small" href="#/cases/${encodeURIComponent(c.id)}/story">查看案件故事</a></div>${ctx.caseActions?.().currentWork()||''}${M.pendingScope(c).added.length||M.pendingScope(c).removed.length?`<div class="iv-baseline-update"><strong>基础调查待更新</strong><span>${M.pendingScope(c).added.length?'新增 '+M.pendingScope(c).added.length+' 条告警待分析。':''}${M.pendingScope(c).removed.length?'已移出 '+M.pendingScope(c).removed.length+' 条告警，案件范围已调整。':''}已有结果保留原调查范围。</span></div>`:''}<div class="iv-case-scope"><a href="#/cases/${encodeURIComponent(c.id)}/alerts">当前成员 <b>${members.length}</b> 条</a><a href="#/cases/${encodeURIComponent(c.id)}/assets">涉及资产 <b>${assets.size}</b> 个</a><span>已有记录 <b>${runs.length}</b> 次</span></div><p class="iv-case-context">各次结果按原始输入范围查看，当前成员变化不会改写历史调查。</p><div class="iv-case-overview-grid"><section class="iv-stack" aria-label="已有分析结果">${findingCards||no('尚无分析结果','可先查看成员告警与案件材料。')}<a class="iv-history-entry" href="#/cases/${encodeURIComponent(c.id)}/investigations">查看全部调查历史 · ${runs.length} 次 ${I('chevron',12)}</a></section><aside>${ctx.caseActions?.().taskSummary()||''}${followup}</aside></div></div>`;
  }
  function latestCaseGraph(){
    const c=currentCase(),latest=M.latestFinished(M.forCase(store,c).filter(r=>r.graphEligible!==false)),pinned=unifiedGraph.pinnedRunId?.(c)||c.graphExploration?.baseRunId,run=pinned?.startsWith('members-')?null:(pinned&&M.forCase(store,c).find(r=>r.id===pinned))||latest;
    if(!run){const virtual={id:'members-'+c.id,title:'当前成员关系',virtual:true,recorded:false,alertIds:c.alertIds.slice(),graphs:{},steps:[],sourceEnvironment:c.sourceEnvironment,sourceTenantId:c.sourceTenantId,started:scopeAlerts().map(a=>a.event_time||a.first).filter(Boolean).sort().at(-1)};return `<div class="iv-root"><h2>案件关系图</h2><p>${pinned&&latest?'保留探索开始时的成员关系；重置探索后可使用最近已完成调查。':'尚无已完成调查，当前展示成员告警与对象的关联。'}</p>${graphs(virtual,{caseSnapshot:true})}</div>`;}

    const hasEnd=Number.isFinite(Date.parse(run.ended)),missing=scopeAlerts().filter(a=>!run.alertIds.includes(a.id)).length;
    return `<div class="iv-root iv-case-latest-graph"><div class="iv-heading"><div><h2>案件关系图</h2><p>基础关系来自${pinned&&latest?.id!==pinned?(c.graphExploration?'已保存探索的原调查':'当前探索的原调查'):'最近一次已完成调查'}，可沿对象扩展线索。</p></div><a class="button small" href="${route(run,'graphs')}">查看本次调查</a></div><div class="iv-case-graph-source"><div><strong>${esc(run.title)}</strong><span>${hasEnd?'完成':'开始'}时间 ${format(hasEnd?run.ended:run.started)}${hasEnd?'':' · 完成时间未记录'}</span></div>${brief(run)}<span>${run.alertIds.length} 条本次输入</span></div><p class="iv-note">保留本轮调查的原始范围。${missing?`当前另有 ${missing} 条成员告警不在本次输入中。`:''}</p>${graphs(run,{caseSnapshot:true})}</div>`;
  }
  function graphPart(kind,p,run){
    const labels={attack_chain:'攻击链 · Attack Chain',attack_path:'攻击路径 · Attack Path',alert_graph:'关联范围 · Alert Graph'},d=p?.data||{};
    if(!p)return card(labels[kind],no('本次未保存此类材料'));
    const explanation=p.error==='no_linked_case'?'该告警没有关联 Case，因此没有 Case 路径；仍可查看 Alert Graph。':p.status==='empty'?'当前种子与查询范围没有返回候选关系。':p.error?String(p.error):'';
    let body=`<div class="iv-foot">${badge(statuses[p.status]||p.status,p.status==='success'?'blue':'amber')}<span>${esc(p.source||'—')} · ${format(p.queried_at)}</span></div>${explanation?`<p>${esc(explanation)}</p>`:''}`;
    if(kind==='attack_chain')body+=`<div class="iv-pair"><span>候选告警 / 时间窗口</span><b>${d.chain?.length??'—'} / ${esc(d.window||'—')}</b></div>${(d.chain||[]).map(c=>`<div class="iv-chain-item">${getAlert(c.alert_id)?alertLink(c.alert_id):esc(c.title)}<small>${format(c.event_time)} · ${esc(JSON.stringify(c.shared_entities||[]))}</small>${run?.sourceCaseId?badge(run.alertIds.includes(c.alert_id)?'本次 Case 输入':'历史外部候选',run.alertIds.includes(c.alert_id)?'blue':''):''}<small>候选评分 ${c.score??'—'} · 图距离 ${c.distance??'—'}</small></div>`).join('')}`;
    if(kind==='attack_path'&&d.nodes)body+=`<p class="iv-note">${d.nodes.length} 个对象 · ${(d.edges||[]).length} 条已记录关系</p>`+pathGraph(d);
    if(kind==='alert_graph'&&p.status==='success'){
      const n=d.neighbors||{},b=d.blast_radius||{};body+=`<div class="iv-stats">${metric('直接邻居',n.neighbor_count??n.neighbors?.length)}${metric('图可达实体',b.total_affected)}${metric('遍历深度',b.hops)}${metric('范围评分',b.blast_radius_score)}</div><p class="iv-note">图可达范围不等于已确认受害范围。</p><div class="iv-node-grid">${(n.neighbors||[]).map(x=>{const node=x.node||x.neighbor||x,pr=node.properties||{};return `<div><span>${esc(node.label||node.labels?.[0]||'实体')}</span><strong>${esc(pr.indicator_value||pr.hostname||pr.username||pr.value||pr.name||pr.title||node.id||'关联对象')}</strong><small>${esc(x.rel_type||x.relationship||x.relationship_type||x.type||'关联关系')}</small></div>`;}).join('')}</div>`;
    }
    return card(labels[kind],body+`<details class="iv-raw"><summary>查看保存的关系数据</summary>${json(p)}</details>`);
  }
  function pathGraph(data){
    data={...data,nodes:Array.isArray(data.nodes)?data.nodes:[],edges:Array.isArray(data.edges)?data.edges:[]};
    if(data.nodes?.some(n=>n.label==='Case'))return savedCasePath(data);
    const nodes=data.nodes||[],edges=data.edges||[];return `<div class="iv-node-grid">${nodes.map(n=>`<div><span>${esc(n.label||n.type||'实体')}</span><strong>${esc(n.properties?.indicator_value||n.properties?.hostname||n.properties?.username||n.properties?.value||n.properties?.title||n.name||n.id)}</strong></div>`).join('')}</div><div class="iv-relations">${edges.map(e=>`<p><code>${esc(e.source)}</code><span> — ${esc(e.type||e.label||'关联')} → </span><code>${esc(e.target)}</code></p>`).join('')}</div>`;
  }
  function savedCasePath(data){
    const label=n=>{const p=n.properties||{};return p.title||p.hostname||p.username||p.indicator_value||p.technique_id||p.value||n.id;};
    const groups=[data.nodes.filter(n=>n.label==='Case'),data.nodes.filter(n=>n.label==='Alert'),data.nodes.filter(n=>['Host','User'].includes(n.label)),data.nodes.filter(n=>!['Case','Alert','Host','User'].includes(n.label))];
    const h=Math.max(...groups.map(g=>g.length))*108+65,pos=new Map(),xs=[16,254,570,824],ws=[198,270,208,210];
    groups.forEach((rows,col)=>rows.forEach((n,i)=>pos.set(n.id,{x:xs[col],y:52+i*(h-70)/rows.length,w:ws[col]})));
    const edges=data.edges.map(e=>{const a=pos.get(e.source),b=pos.get(e.target);if(!a||!b)return '';const x1=a.x+a.w,x2=b.x,y1=a.y+36,y2=b.y+36,m=(x1+x2)/2;return `<path d="M${x1},${y1} C${m},${y1} ${m},${y2} ${x2},${y2}" marker-end="url(#iv-case-arrow)"><title>${esc(e.type)}</title></path>`;}).join('');
    const nodes=data.nodes.map(n=>{const p=pos.get(n.id),name=label(n),short=name.replace(/^Attack context fixture \d+: /,'').replace('LAB-ATTACKCTX-20261021-','LAB-…-'),chars=Array.from(short),chunk=Math.floor((p.w-24)/7),lines=[];for(let i=0;i<chars.length;i+=chunk)lines.push(chars.slice(i,i+chunk).join(''));const body=`<g class="iv-map-node ${n.label==='Alert'?'iv-map-input':''}"><title>${esc(name)}</title><rect x="${p.x}" y="${p.y}" width="${p.w}" height="82" rx="8"/><text class="iv-map-type" x="${p.x+12}" y="${p.y+19}">${esc({Case:'案件',Alert:'输入告警',Host:'主机',User:'账户',IOC:'IOC 线索',Technique:'ATT&CK 技术'}[n.label]||n.label)}</text><text x="${p.x+12}" y="${p.y+42}">${lines.slice(0,2).map((l,i)=>`<tspan x="${p.x+12}" dy="${i?17:0}">${esc(l)}</tspan>`).join('')}</text></g>`;return n.label==='Alert'&&getAlert(n.id)?`<a href="#/alerts/${esc(n.id)}/overview">${body}</a>`:body;}).join('');
    const labels=new Map(data.nodes.map(n=>[n.id,label(n)]));
    return `<div class="iv-relationship-map"><svg viewBox="0 0 1050 ${h+20}" role="img" aria-label="本次 Case 联合调查保存的路径图"><defs><marker id="iv-case-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#9bb2c8"/></marker></defs>${['案件','输入告警','主机与账户','技术与线索'].map((x,i)=>`<text class="iv-map-column" x="${xs[i]}" y="25">${x}</text>`).join('')}<g class="iv-map-edges">${edges}</g>${nodes}</svg></div><details class="iv-raw"><summary>查看 ${data.edges.length} 条原始关系</summary><div class="iv-relations">${data.edges.map(e=>`<p>${esc(labels.get(e.source)||e.source)}<span> — ${esc(relationNames[e.type]||e.type)}（${esc(e.type)}）→ </span>${esc(labels.get(e.target)||e.target)}</p>`).join('')}</div></details>`;
  }
  const graphKinds=['all','attack_chain','attack_path','alert_graph'];
  let sourceDisclosure=null;
  function sourceDisclosureState(run,mode){
    const r=currentRoute(),key=JSON.stringify([r.page,r.id,run.sourceEnvironment,run.sourceTenantId,run.id]);
    if(sourceDisclosure?.key!==key)sourceDisclosure={key,mode,open:graphKinds.includes(mode)};
    else if(sourceDisclosure.mode!==mode){sourceDisclosure.mode=mode;sourceDisclosure.open=graphKinds.includes(mode);}
    return sourceDisclosure;
  }
  function toggle(el){
    if(!el?.isConnected||!el.hasAttribute?.('data-iv-source-disclosure')||el.getAttribute('data-iv-source-disclosure')!==sourceDisclosure?.key)return false;
    sourceDisclosure.open=el.open;return true;
  }
  function keepGraphMaterialPosition(oldURL,newURL){
    const parse=url=>{const hash=String(url||'').split('#')[1]||'',i=hash.indexOf('?');return {path:i<0?hash:hash.slice(0,i),q:new URLSearchParams(i<0?'':hash.slice(i+1))};};
    const a=parse(oldURL),b=parse(newURL);
    if(a.path!==b.path||!graphKinds.includes(b.q.get('graph'))||a.q.get('graph')===b.q.get('graph'))return false;
    const graphRoute=/^\/investigations\/[^/]+\/graphs$/.test(b.path)||(/^\/cases\/[^/]+\/(investigations|overview)$/.test(b.path)&&b.q.get('view')==='graphs');
    if(!graphRoute)return false;
    a.q.delete('graph');b.q.delete('graph');a.q.sort();b.q.sort();return a.q.toString()===b.q.toString();
  }
  function sourceGraphNavigation(run,mode){
    const selected=graphKinds.includes(mode)?mode:'all';
    return `<nav class="iv-filter-tabs iv-graph-kinds" aria-label="关系分析类型">${[['all','全部关系'],['attack_chain','攻击链 · Chain'],['attack_path','攻击路径 · Path'],['alert_graph','关联范围']].map(([k,n])=>`<a href="${route(run,'graphs',{graph:k})}" ${selected===k?'aria-current="page"':''}>${n}</a>`).join('')}</nav>`;
  }
  function sourceGraphs(run){
    const q=new URLSearchParams(currentRoute().search),requested=q.get('graph'),kinds=['attack_chain','attack_path','alert_graph'],chosen=kinds.includes(requested)?requested:'all';
    return `<p class="iv-note">关联链和图可达范围不自动表示攻击因果或已确认受害范围。</p><div class="iv-stack">${(chosen==='all'?kinds:[chosen]).map(k=>graphPart(k,run.graphs[k],run)).join('')}</div>`;
  }
  function graphs(run,options={}){
    const mode=options.caseSnapshot?'case_snapshot':new URLSearchParams(currentRoute().search).get('graph'),disclosure=options.caseSnapshot?null:sourceDisclosureState(run,mode),context=M.graphContext(store,run);let notice='';
    if(context)notice=options.caseSnapshot?'<p class="iv-note">基础关系取自本轮输入告警保存的对象关联。</p>':'<p class="iv-note">图中包含输入告警的已保存关联资料；关联资料不代表本次运行生成的攻击路径。</p>';
    const skipped=run.steps.some(s=>s.payload?.node==='attack_path'&&s.payload?.step_status==='skipped');
    if(!options.caseSnapshot&&skipped)notice+='<p class="iv-note">攻击路径分析已跳过，保留当时执行记录。</p>';
    const path=run.graphs.attack_path;if(!options.caseSnapshot&&path&&path.status!=='success')notice+=`<p class="iv-note">攻击路径：${esc(statuses[path.status]||path.status)}${path.error==='no_linked_case'?' · 当时未关联 Case':''}。其他来源材料分别保留。</p>`;
    const materials=options.caseSnapshot?'':`<details class="iv-graph-materials" data-iv-source-disclosure="${esc(disclosure.key)}" ${disclosure.open?'open':''}><summary>来源材料与关联范围 · Attack Chain / Attack Path / Alert Graph</summary><div class="iv-stack">${sourceGraphs(run)}</div></details>`;
    return `${options.caseSnapshot?'':`<div class="iv-section-title"><div><h3>调查关系图</h3><p>聚焦告警、共享实体与技术，查看跨告警关联及其依据。</p></div></div>${sourceGraphNavigation(run,mode)}`}${notice}${unifiedGraph.render(run,context,graphKinds.includes(mode)?mode:'all',options)}<p class="iv-note">连线表示已记录关系或候选关联，不表示攻击因果。选择不会修改 Case 成员或调查输入。</p>${materials}`;
  }

  function responseActions(run){
    const proposalId=a=>a&&typeof a==='object'?(a.id||a.action_id):null;
    const receiptId=e=>e&&typeof e==='object'?(e.action_id||e.proposal_id):null;
    const matches=(a,e)=>{const id=proposalId(a);return id!=null&&run.actions.filter(x=>proposalId(x)===id).length===1&&receiptId(e)===id;};
    const receipt=e=>`<div class="iv-response-receipt"><p>${esc(text(e))}</p>${e&&typeof e==='object'?`<details class="iv-raw"><summary>执行记录原文</summary>${json(e)}</details>`:''}</div>`;
    const unassigned=run.executed.filter(e=>!run.actions.some(a=>matches(a,e)));
    const rows=run.actions.map((a,i)=>{
      const structured=a&&typeof a==='object',records=run.executed.filter(e=>matches(a,e)),review=ctx.caseActions?.().responseControls(run,i)||'';
      return `<article class="iv-card iv-response-action" data-response-index="${i}"><h4>${esc(typeof a==='string'?a:a?.description||a?.action_type||text(a))}</h4>${structured?`<p class="iv-response-target"><span>目标</span>${esc(a.target||'未记录')}</p>${a.rationale?`<p>${esc(a.rationale)}</p>`:''}`:''}<div class="iv-response-decision">${review||(structured&&a.requires_approval?badge('需要审批','amber'):structured&&a.requires_approval===false?'<span class="iv-note">无需审批</span>':'<span class="iv-note">未记录审批要求</span>')}</div><div class="iv-response-execution"><strong>执行记录</strong>${records.map(receipt).join('')||`<p class="iv-muted">${run.executed.length?'暂无可对应此动作的执行记录，请核对下方本轮其他执行记录。':'暂无已执行记录。'}</p>`}</div></article>`;
    }).join('');
    return `<section class="iv-response-workspace"><div class="iv-section-title"><div><h3>响应动作 <span>${run.actions.length}</span></h3><p>建议、审阅决定与实际执行分别保留。</p></div></div><div class="iv-response-action-list">${rows||no('本轮未记录响应建议')}</div>${unassigned.length?card('本轮其他执行记录',unassigned.map(receipt).join('')+'<p class="iv-note">这些记录未通过明确动作 ID 对应到上方建议。</p>'):''}</section>`;
  }
  function report(run){return `<div class="iv-section-title"><h3>调查报告</h3>${run.report?btn('下载 Markdown','iv-download',run.id,'small','download'):''}</div>${run.completion==='partial'?`<div class="iv-callout">部分交付 · 请结合停止原因与工具返回核对报告。</div>`:''}${run.report?`<article class="iv-card iv-report"><pre>${esc(run.report)}</pre></article>`:no('本次没有保存报告正文','调查发现和已有步骤仍可查看。')}${responseActions(run)}`;}
  function workbench(){
    const r=currentRoute();if(r.page==='investigations'&&!r.id)return queue();
    const rows=available(),run=active();if(!run)return `<div class="iv-root">${no('没有关联调查运行','可以查看已有告警、材料与人工协作信息。')}<a class="button" href="#/investigations">查看全部调查运行</a></div>`;
    const requested=r.page==='cases'?new URLSearchParams(r.search).get('view'):r.tab,view=['overview','process','tools','graphs','ledger','report'].includes(requested)?requested:'overview';
    return `<div class="iv-root"><div class="iv-heading"><div><h2>调查详情</h2><p>查看关键发现、分析依据与后续处理。</p></div>${r.page==='cases'?`<a class="button" href="#/cases/${encodeURIComponent(r.id)}/overview">返回调查概览</a>`:`<a class="button" href="#/investigations">全部运行 ${I('list',14)}</a>`}</div><div class="iv-run-selector"><label for="iv-run">当前调查</label><select id="iv-run" data-iv-run>${rows.map(x=>`<option value="${esc(x.id)}" ${x.id===run.id?'selected':''}>${esc(x.title)} · ${x.completion==='completed'?'完整交付':names[x.completion]||names[x.status]||'未记录'}</option>`).join('')}</select>${brief(run)}</div>${r.page==='cases'?`<div class="cw-run-actions">${btn('询问本轮结果','ca-run',run.id,'small','sparkles')}${btn('添加人工任务','cw-followup',run.id,'small')}<a class="button small" href="#/cases/${encodeURIComponent(r.id)}/attack">到案件图探索</a></div>`:''}${ctx.caseActions?.().runControls(run)||''}<div class="iv-run-title"><h3>${esc(run.title)}</h3><span class="iv-note">${run.alertIds.length} 条输入告警${run.started?' · '+format(run.started):''}</span></div><nav class="iv-tabs" aria-label="调查运行内容">${[['overview','调查发现'],['process','AI 分析'],['tools','查询与证据'],['graphs','调查关系图'],['report','报告与响应']].map(([k,n])=>`<a href="${route(run,k)}" ${view===k?'aria-current="page"':''} class="${view===k||(view==='ledger'&&k==='process')?'active':''}">${n}${k==='tools'&&run.tools.length?`<span>${run.tools.length}</span>`:''}</a>`).join('')}</nav>${view==='overview'?overview(run):view==='process'?process(run):view==='tools'?tools(run):view==='graphs'?graphs(run):view==='ledger'?ledger(run):report(run)}</div>`;
  }
  function change(el){
    if(unifiedGraph.change(el))return true;
    if(el.hasAttribute('data-iv-run')){const run=available().find(r=>r.id===el.value);if(run){const r=currentRoute(),view=r.page==='cases'?new URLSearchParams(r.search).get('view'):r.tab;navigate(route(run,['overview','process','tools','graphs','ledger','report'].includes(view)?view:'overview'));}return true;}
    if(el.hasAttribute('data-iv-kind')||el.hasAttribute('data-iv-agent')){const run=active();if(run){const q=new URLSearchParams(currentRoute().search);q.set(el.hasAttribute('data-iv-kind')?'kind':'agent',el.value);const target=route(run,'ledger').split('?')[0];if(currentRoute().page==='cases'){q.set('run',run.id);q.set('view','ledger');}navigate(`${target}?${q}`);}return true;}
    return false;
  }
  function handle(action,id){if(unifiedGraph.handle(action,id))return true;if(action!=='iv-download')return false;const run=active();if(run?.id===id&&run.report)downloadFile(`investigation-${id}.md`,run.report,'text/markdown;charset=utf-8');return true;}
  return {attackCoverage,artifactCatalog,flowCaseOverview,latestCaseGraph,workbench,queue,linkedRuns,incidentSummary,incidentOverview,basicInvestigations,incidentMaterials,incidentRelations,change,handle,toggle,keepGraphMaterialPosition};
};
