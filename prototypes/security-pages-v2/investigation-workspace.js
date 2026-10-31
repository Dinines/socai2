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
    const design=new Map((window.designInvestigationRuns||[]).filter(r=>r.fixture&&!r.recorded).map(r=>[r.id,r]));
    const illustrated=reference.map(r=>design.has(r.id)?structuredClone(design.get(r.id)):r);
    const saved=window.savedInvestigationRuns||[];
    return [...illustrated,...(window.alertFlowWorkspace?.runs(saved)||saved),...(window.aisoc20RecordedData?.runs||[]),...(window.persistedCaseData?.runs||[]),...(window.pageShowcaseData?.runs||[])];
  }
  function forAlerts(store,alerts){const ids=new Set(alerts.map(a=>a.id));return runs(store).filter(r=>r.alertIds.some(id=>ids.has(id)));}
  function forCase(store,c){
    const recorded=c.localCollection||c.recordedCase||(c.incidentCreated&&!!c.sourceTenantId&&!!c.sourceEnvironment);
    const sameSource=r=>r.sourceTenantId===c.sourceTenantId&&r.sourceEnvironment===c.sourceEnvironment;
    const related=forAlerts(store,store.alerts.filter(a=>c.alertIds.includes(a.id))).filter(r=>!recorded||sameSource(r));
    const owned=c.recordedCase?runs(store).filter(r=>r.sourceCaseId===c.sourceCaseId&&r.sourceTenantId===c.sourceTenantId&&r.sourceEnvironment===c.sourceEnvironment):[];
    const collected=c.localCollection?runs(store).filter(r=>c.sourceRunIds?.includes(r.id)&&sameSource(r)):[];
    return [...new Map([...owned,...collected,...related].map(r=>[r.id,r])).values()];
  }
  function selected(rows,id){return rows.find(r=>r.id===id)||rows[0]||null;}
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
  return {runs,forAlerts,forCase,selected,chain,assessments,coverage,inputEvidence,sharedObjects};
})();

window.createInvestigationWorkspace = function(ctx){
  const {store,esc,I,btn,badge,severity,state,currentRoute,currentCase,scopeAlerts,getAlert,getAsset,navigate,render,downloadFile}=ctx;
  const M=window.investigationWorkspaceModel;
  const names={completed:'已结束',running:'运行中',failed:'失败',partial:'部分交付',not_escalated:'未升级调查',needs_review:'待复核',escalate:'需人工跟进',benign:'正常行为',true_positive:'真实威胁',false_positive:'误报',benign_true_positive:'预期活动',reviewed:'已形成调查结果',confirmed_incident:'模型判定为安全事件'};
  const statuses={success:'已返回',empty:'无候选关系',not_linked:'未关联 Case',unavailable:'查询不可用',error:'查询失败'};
  const format=v=>v?new Date(typeof v==='number'?v:String(v).replace(' ','T')).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}):'未记录';
  const json=v=>`<pre class="iv-json">${esc(JSON.stringify(v,null,2))}</pre>`;
  const text=v=>typeof v==='string'?v:JSON.stringify(v);
  const card=(title,body,extra='')=>`<article class="iv-card ${extra}"><h3>${title}</h3>${body}</article>`;
  const no=(title,body='')=>`<div class="iv-empty">${I('search',24)}<strong>${title}</strong>${body?`<p>${body}</p>`:''}</div>`;
  const alertLink=id=>{const a=getAlert(id);return a?`<button class="iv-alert-link" data-action="alert" data-id="${esc(id)}">${I('shield',14)}<span>${esc(a.title)}</span>${severity(a.severity)}</button>`:`<span class="iv-mono">${esc(id)}</span>`;};
  const metric=(label,value,detail='')=>`<div><span>${label}</span><strong>${esc(value??'—')}</strong>${detail?`<small>${esc(detail)}</small>`:''}</div>`;
  const unifiedGraph=window.createUnifiedInvestigationGraph({...ctx,format});
  function route(run,view='overview'){
    const r=currentRoute();return r.page==='cases'&&r.id?`#/cases/${r.id}/investigations?run=${encodeURIComponent(run.id)}&view=${view}`:`#/investigations/${encodeURIComponent(run.id)}/${view}`;
  }
  function available(){const r=currentRoute();return r.page==='cases'?M.forCase(store,currentCase()):M.runs(store);}
  function active(){const r=currentRoute(),rows=available();const id=r.page==='investigations'?r.id:new URLSearchParams(r.search).get('run');return id?rows.find(x=>x.id===id):rows[0];}
  function brief(run){return `<span class="iv-run-status">${badge(names[run.status]||run.status)}${badge(run.completion==='completed'?'完整交付':names[run.completion]||'完整性未记录',run.completion==='partial'?'amber':'blue')}</span>`;}
  function linkedRuns(){
    const rows=currentRoute().page==='cases'?M.forCase(store,currentCase()):M.forAlerts(store,scopeAlerts());return `<div class="iv-root"><div class="iv-heading"><div><h2>${currentRoute().page==='cases'?'调查历史':'关联调查'}</h2><p>查看各次调查的输入范围与已有结果。</p></div></div>${rows.length?rows.map(r=>`<article class="iv-card iv-run-link">${brief(r)}<h3>${esc(r.title)}</h3><p>${esc((r.findings||[]).map(text).join(' ').slice(0,200))}</p><div class="iv-foot"><span>${r.alertIds.length} 条输入告警 · ${format(r.started)}</span><a class="button primary" href="${route(r)}">打开调查 ${I('external',14)}</a></div></article>`).join(''):no('尚无调查记录','已有告警和上下文仍可在事件中查看。')}</div>`;
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
  function incidentOverview(){
    const a=scopeAlerts(),inc=store.incidents.find(x=>x.id===currentRoute().id),context=ctx.incidentContext(inc),shared=M.sharedObjects(store,a);
    const occurrence=alert=>{const value=alert.event_time??(alert.persistedRecord?null:alert.first);return Number.isFinite(Date.parse(value))?value:null;};
    const timeline=a.slice().sort((x,y)=>{const tx=Date.parse(occurrence(x)),ty=Date.parse(occurrence(y));return (Number.isFinite(ty)?ty:-Infinity)-(Number.isFinite(tx)?tx:-Infinity);});
    const times=a.map(x=>Date.parse(occurrence(x))).filter(Number.isFinite),phases=Object.entries(a.reduce((m,x)=>(m[x.category||'未分类']=(m[x.category||'未分类']||0)+1,m),{}));
    const description=inc.recordedIncident?ctx.incidentSummaryText(inc,a,context.hostNames).description:inc.description;
    const stages=`<section class="iv-card iv-attack-coverage" aria-label="ATT&CK 阶段覆盖"><div class="iv-coverage-heading"><h4>ATT&CK 阶段覆盖</h4><button type="button" class="icon-button" aria-label="阶段覆盖说明：按成员告警的战术分类统计，不代表检测覆盖率或攻击成功" title="按成员告警的战术分类统计；数字为告警数，不代表检测覆盖率或攻击成功。">${I('info',14)}</button></div><div class="iv-stage-list">${phases.map(([name,n])=>`<div class="iv-stage-item"><span>${esc(name)}</span><b>${n}</b><small>告警</small></div>`).join('')||'<span class="iv-muted">暂无成员告警</span>'}</div></section>`;
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
    const result=card(isTriage?'本次分诊结果':'关键发现',`<div class="iv-conclusion">${I('sparkles',24)}<div><strong>${esc(names[run.verdict]||run.verdict||'判定未记录')}</strong><span>${isTriage?'本次未升级调查':run.confidence!=null?esc(run.confidenceLabel||'本次调查置信度')+' '+Math.round(run.confidence*100)+'%':'来自本次调查结果'}</span></div>${brief(run)}</div>${findings.length?findings.slice(0,5).map(f=>`<p class="iv-finding">${esc(text(f))}</p>`).join(''):no('尚无调查发现')}${findings.length>5?`<details><summary>展开其余 ${findings.length-5} 条发现</summary>${findings.slice(5).map(f=>`<p>${esc(text(f))}</p>`).join('')}</details>`:''}<a class="iv-link" href="${route(run,'report')}">查看调查报告与响应 →</a>`,'iv-findings-card');
    const materials=card('可核查材料',`<div class="iv-material-counts"><a href="${route(run,'tools')}"><b>${run.tools.length}</b><span>本次查询记录</span></a><a href="${route(run,'tools')}"><b>${run.artifacts.length}</b><span>保存材料</span></a><a href="${route(run,'tools')}"><b>${evidence.length}</b><span>输入关联证据</span></a></div>${run.tools.length?`<h4>本次查询</h4><div class="iv-query-list">${run.tools.slice(0,3).map(t=>`<a href="${route(run,'tools')}">${I('search',14)}<span>${esc(t.name)}</span><small>${format(t.time)}</small>${I('chevron',12)}</a>`).join('')}</div>`:''}${evidence.length?`<h4>输入告警携带的证据</h4>${inputMaterial(run)}`:''}${!run.tools.length&&!evidence.length?'<p class="iv-muted">暂无可展开的查询或输入证据。已有发现和步骤仍可查看。</p>':''}<a class="iv-link" href="${route(run,'tools')}">核对查询返回与材料来源 →</a>`);
    const progress=card('已开展的工作',`${work.length?`<ol class="iv-work-list">${work.slice(-4).map(s=>`<li><i>${I('clock',12)}</i><div><strong>${esc(s.name)}</strong><p>${esc(stepSummary(s)||'已有过程记录')}</p></div></li>`).join('')}</ol>`:'<p class="iv-muted">尚无可回查的步骤记录。</p>'}<a class="iv-link" href="${route(run,'process')}">查看完整分析过程 →</a>`);
    const limitations=run.stop||(depth.unavailable_data||[]).length?card('未完成与待核查',`${run.stop?`<p>${esc(run.stop)}</p>`:''}${(depth.unavailable_data||[]).length?`<h4>尚未取得的资料</h4><div class="iv-tags">${depth.unavailable_data.map(x=>badge(x,'amber')).join('')}</div>`:''}<a class="iv-link" href="${route(run,'tools')}">查看查询范围和返回内容 →</a>`,'iv-warning'):'';
    const response=card('后续处理',`<div class="iv-response-columns"><section><h4>调查建议</h4>${actionList(run.actions)||`<p class="iv-muted">未记录具体建议动作。</p>`}${run.remediation?`<p class="iv-note">调查记录中的处置状态：${esc(run.remediation)}</p>`:''}</section><section><h4>实际执行 <span>${run.executed.length}</span></h4>${run.executed.map(a=>`<p>${esc(text(a))}</p>`).join('')||'<p class="iv-muted">暂无已执行动作记录。</p>'}</section></div><a class="iv-link" href="${route(run,'report')}">查看报告与响应详情 →</a>`);
    const scope=card('本次调查范围',`<div class="iv-pair"><span>输入告警</span><b>${run.alertIds.length}</b></div>${members!==null?`<div class="iv-pair"><span>当前 Case 成员</span><b>${members}</b></div><p class="iv-note">新成员不会自动加入已经结束的调查。</p>`:''}<details class="iv-raw"><summary>查看输入告警</summary>${run.alertIds.map(alertLink).join('')}</details>${run.input?`<details class="iv-raw"><summary>查看本次保存的输入</summary>${json(run.input)}${run.input_summary?`<h4>输入摘要</h4><pre class="iv-tool-result">${esc(run.input_summary)}</pre>`:''}</details>`:''}`);
    const meta=`<details class="iv-card iv-execution"><summary>${I('clock',15)}运行详情与用量 ${I('down',12)}</summary><dl class="iv-definition"><dt>Run ID</dt><dd class="iv-mono">${esc(run.id)}</dd><dt>Run 状态</dt><dd>${esc(names[run.status]||run.status)}</dd><dt>交付完整性</dt><dd>${run.completion==='completed'?'完整交付':esc(names[run.completion]||'未记录')}</dd><dt>Run 开始</dt><dd>${format(run.started)}</dd><dt>Run 结束</dt><dd>${format(run.ended)}</dd><dt>最后记录</dt><dd>${format(run.steps?.at(-1)?.time)}</dd><dt>调用 / Tokens</dt><dd>${run.calls??'—'} / ${run.tokens?.toLocaleString()??'—'}</dd><dt>费用</dt><dd>${run.unpriced?'未定价 · '+run.unpriced+' 次调用':'未提供'}</dd></dl>${run.timeNote?`<p class="iv-note">${esc(run.timeNote)}</p>`:''}</details>`;
    return `<div class="iv-overview"><div class="iv-stack">${result}${materials}${progress}${limitations}${response}</div><aside class="iv-stack">${scope}${run.triage?card('首次分诊',`<div class="iv-pair"><span>判定</span>${decisionBadge(run.triage.verdict)}</div><div class="iv-pair"><span>分诊评分</span><b>${run.triage.confidence!=null?Math.round(run.triage.confidence*100):'—'}</b></div><p class="iv-note">保留初始判断，与本次调查结论分别核对。</p>`):''}${currentRoute().page==='cases'?card('案件跟进',`<a class="iv-follow-link" href="#/cases/${encodeURIComponent(currentRoute().id)}/tasks"><span>跟进任务</span><b>${(currentCase().tasks||[]).filter(t=>t.status!=='Completed').length}</b></a><a class="iv-follow-link" href="#/cases/${encodeURIComponent(currentRoute().id)}/comments"><span>评论与附件</span>${I('chevron',14)}</a>`):''}${meta}</aside></div>`;
  }
  const stageNames={triage:'告警分诊',enrichment:'上下文补充',investigation:'深度调查',attack_path:'攻击路径分析',recon:'侦察分析 · Recon',forensic:'取证分析 · Forensic',responder:'响应分析 · Responder',report:'报告整理'};
  function stages(run){return (run.steps||[]).filter(s=>s.kind==='阶段记录'||s.kind==='graph_step'||['recon','forensic','responder','report'].includes(s.kind));}
  function process(run){
    const rows=stages(run),d=run.depth;
    return `<div class="iv-section-title"><div><h3>AI 阶段分析</h3><p>查看实际开展的分析及其留存结果。</p></div><a class="button small" href="${route(run,'ledger')}">调查记录 ${I('chevron',12)}</a></div><div class="iv-phase-grid">${rows.map((s,i)=>card(`<span class="iv-phase-number">${i+1}</span>${esc(stageNames[s.payload?.node||s.kind]||stageNames[s.name]||s.name)}`,`<p>${esc(stepSummary(s)||'已有阶段记录')}</p>${s.adopted?`<p>${esc(s.adopted.summary||'')}</p><details class="iv-raw"><summary>查看阶段采用结果</summary>${json(s.adopted)}</details>`:''}<div class="iv-foot"><span>${format(s.time)}</span><span>${esc(s.name)}</span></div>${s.kind==='graph_step'&&s.payload?.step_status!=='skipped'?'<p class="iv-note">节点结束记录；分析内容见本次发现、查询返回与报告。</p>':''}`)).join('')||no('暂无独立阶段记录','已有分诊或其他过程记录可在调查记录中查看。')}</div>${d?card('Deep 深度调查',`<div class="iv-stats">${metric('调查轮数',d.iterations)}${metric('查询方向',d.distinct_pivots)}${metric('工具记录',run.tools.length)}${metric('调查截断',d.truncated?'是':'否')}</div>${d.strategy_id?`<div class="iv-pair"><span>调查策略</span><b>${esc(d.strategy_id)}</b></div>`:''}${(d.pivots||[]).length?`<h4>已记录的查询方向</h4><div class="iv-tags">${[...new Set(d.pivots)].map(p=>badge(p,'blue')).join('')}</div>`:''}${d.narrative?`<details class="iv-raw"><summary>查看 Deep 留存内容</summary><pre class="iv-tool-result">${esc(d.narrative)}</pre></details>`:''}${run.stop?`<div class="iv-callout">停止原因：${esc(run.stop)}</div>`:''}<a class="iv-link" href="${route(run,'tools')}">核对查询范围、参数与返回 →</a>`):''}<p class="iv-note">阶段记录不代表证据充分，也不改变本次调查的交付完整性。</p>`;
  }
  function ledger(run){
    const q=new URLSearchParams(currentRoute().search),kind=q.get('kind')||'',agent=q.get('agent')||'',rows=run.steps.filter(s=>(!kind||s.kind===kind)&&(!agent||s.name===agent));
    return `<div class="iv-section-title"><div><h3>调查记录</h3><p>${rows.length} / ${run.steps.length} 条记录 · 按已有记录顺序展示</p></div></div><div class="iv-ledger-controls"><label>记录类型<select data-iv-kind aria-label="记录类型"><option value="">全部类型</option>${[...new Set(run.steps.map(s=>s.kind))].map(k=>`<option value="${esc(k)}" ${k===kind?'selected':''}>${esc(k)}</option>`).join('')}</select></label><label>执行者 / 节点<select data-iv-agent aria-label="执行者或节点"><option value="">全部执行者 / 节点</option>${[...new Set(run.steps.map(s=>s.name))].map(a=>`<option value="${esc(a)}" ${a===agent?'selected':''}>${esc(a)}</option>`).join('')}</select></label></div><div class="iv-timeline">${rows.map(s=>`<details class="iv-step"><summary><span class="iv-step-dot">${I(s.kind==='tool_call'?'search':s.kind==='error'?'alert':'clock',14)}</span><span><strong>${esc(s.name||s.kind)}</strong><small>${esc(stepSummary(s)||s.kind)}</small></span><time>${format(s.time)}</time>${I('down',14)}</summary><div class="iv-step-content"><div class="iv-pair"><span>记录类型</span><code>${esc(s.kind)}</code></div>${s.id?`<div class="iv-pair"><span>记录 ID / seq</span><code>${esc(s.id)} / ${esc(s.seq)}</code></div>`:""}${s.payload&&Object.keys(s.payload).length?json(s.payload):`<p>${esc(s.summary||'未保存该步骤的详细输入输出。')}</p>`}</div></details>`).join('')||no('没有符合筛选条件的记录')}</div><p class="iv-note">按保存内容回查；未保存的提示词、回复或引用不会从报告反推补齐。</p>`;
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
  function tools(run){const d=run.depth||{};return `<div class="iv-stats">${metric('工具记录',run.tools.length)}${metric('Deep轮数',d.iterations)}${metric('查询方向',d.distinct_pivots)}${metric('材料截断',d.truncated?'是':run.depth?'否':'—')}</div>${(d.coverage_notes||[]).length?card('查询覆盖范围',d.coverage_notes.map(n=>`<p>${esc(n)}</p>`).join('')):''}<div class="iv-tools">${run.tools.map((t,i)=>card(`${i+1}. ${esc(t.name)}`,`<div class="iv-foot"><span>${format(t.time)}</span>${badge(t.success===false?'查询失败':t.resultFormat==='saved_result'?'已保存返回':'已保存返回摘要',t.success===false?'amber':'blue')}</div><details class="iv-raw"><summary>查询参数</summary>${json(t.args)}</details><h4>返回内容</h4><pre class="iv-tool-result">${esc(t.result||'未保存返回内容')}</pre><p class="iv-note">${t.resultFormat==='saved_result'?'展示当次工具留存的返回内容。':'v1工具记录保留最多200字符摘要；空结果、不可用和查询失败以返回内容为准。'}</p>`)).join('')||no('没有可回查的工具记录','不从报告文字补造工具调用。')}</div>${card('输入告警携带的证据',inputMaterial(run))}${card('保存材料目录',artifactCatalog(run))}`;}
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
    const c=currentCase(),members=scopeAlerts(),runs=M.forCase(store,c),stats=window.alertFlowWorkspace.caseStats(runs);
    return `<div class="iv-root"><div class="iv-heading"><div><h2>案件调查概览</h2><p>汇集已有分析与待跟进事项，分别保留每次调查的结论和输入范围。</p></div><a class="button" href="#/cases/${c.id}/investigations">调查历史</a></div><div class="iv-stats">${metric('当前成员',members.length,'告警')}${metric('调查记录',stats.runs,`${stats.started} 次进入后续调查`)}${metric('部分交付',stats.partial,`${stats.triage} 次仅分诊`)}${metric('已有工件',stats.artifacts,`${stats.tools} 条工具记录`)}</div><div class="iv-stack">${runs.map(r=>card(esc(r.title),`<div class="iv-foot">${brief(r)}<span>${r.alertIds.length} 条原始输入 · ${format(r.started)}</span></div><div class="iv-pair"><span>首次分诊</span>${decisionBadge(r.triage?.verdict)}<span>评分 ${r.triage?.confidence!=null?Math.round(r.triage.confidence*100):'—'}</span></div><div class="iv-pair"><span>${r.completion==='not_escalated'?'后续调查':'调查结果'}</span>${r.completion==='not_escalated'?'<span>未升级调查</span>':decisionBadge(r.verdict)}</div>${(r.findings||[]).length?`<details><summary>查看已有分析记录</summary>${r.findings.map(f=>`<p>${esc(text(f))}</p>`).join('')}</details>`:''}${r.stop?`<div class="iv-callout">停止原因：${esc(r.stop)}</div>`:''}<p class="iv-note">原始输入：${r.alertIds.map(id=>`${esc(getAlert(id)?.title||id)}${members.some(a=>a.id===id)?'':'（已不在当前成员中）'}`).join('；')}</p><div class="iv-foot"><span>${r.steps.length} 条过程 · ${r.tools.length} 条工具记录 · ${r.artifacts.length} 份工件</span><a class="button primary" href="${route(r)}">查看本次调查</a></div><div class="iv-tags"><a class="button small" href="${route(r,'tools')}">查询与证据</a><a class="button small" href="${route(r,'graphs')}">调查关系图</a><a class="button small" href="${route(r,'report')}">报告与响应</a></div>`)).join('')||no('尚无已引用调查','当前成员材料仍可在案件资料中查看。')}</div><p class="iv-note">原始调查输入不随当前案件成员变化；各次调查的结论、建议与实际执行分别核查。</p></div>`;
  }
  function flowCaseMaterials(){
    const c=currentCase(),members=scopeAlerts(),runs=M.forCase(store,c),stats=window.alertFlowWorkspace.caseStats(runs);
    return `<div class="iv-root"><div class="iv-heading"><div><h2>案件证据与调查材料</h2><p>按来源查看成员告警和已有调查工件，原件不自动视为已确认的恶意证据。</p></div></div><div class="iv-stats">${metric('来源告警',members.length)}${metric('工具记录',stats.tools)}${metric('已保存工件',stats.artifacts)}${metric('已有报告',stats.reports)}</div>${card('当前成员来源',members.map(a=>`<div class="iv-card"><a href="#/alerts/${a.id}/raw">${esc(a.title)}</a><div class="iv-foot">${severity(a.severity)}<span>${format(a.event_time||a.first)} · ${esc(a.source)}</span></div></div>`).join('')||'<p>当前没有成员告警；已引用的调查材料仍保留。</p>')}<div class="iv-stack">${runs.map(r=>card(esc(r.title),`<div class="iv-foot">${brief(r)}<span>${r.alertIds.length} 条原始输入</span></div><div class="iv-tags"><a class="button small" href="${route(r,'tools')}">查看 ${r.tools.length} 条工具记录</a><a class="button small" href="${route(r,'report')}">报告与响应</a></div><p class="iv-note">${r.artifacts.length} 份已保存工件 · ${r.executed.length} 条已执行动作记录</p>${artifactCatalog(r,false)}`)).join('')}</div></div>`;
  }
  function flowCaseRelations(){
    const g=window.alertFlowWorkspace.relations(store,scopeAlerts());
    return `<div class="iv-root"><div class="iv-heading"><div><h2>案件关系图</h2><p>当前成员告警与主机、账户、IP的来源关联。</p></div><a class="button" href="#/cases/${currentCase().id}/overview">查看各次调查</a></div><p class="iv-note">${g.nodes.length} 个对象 · ${g.edges.length} 条来源关系。当前成员变更只影响此图；各次调查的 Chain、Path 和关联范围仍保留当时记录。</p>${relationDiagram(g)}<p class="iv-note">各次调查的攻击路径及执行状态请在对应调查中查看。</p></div>`;
  }
  function caseRelations(){
    const g=recordedGraphData(scopeAlerts().map(a=>a.id));
    return `<div class="iv-root"><div class="iv-heading"><div><h2>案件关系图</h2><p>告警与主机、账户及线索的已记录关系。</p></div></div><p class="iv-note">记录时间 ${format(g.generatedAt)} · 这是案件关联材料，不代表本次调查已执行攻击路径分析或验证攻击因果。</p>${relationDiagram(g)}</div>`;
  }
  function persistedCaseRelations(){
    const c=currentCase(),run=M.runs(store).find(r=>c.sourceRunIds?.includes(r.id));
    return `<div class="iv-root"><div class="iv-heading"><div><h2>案件关系图</h2><p>本次联合调查保存的案件关系。</p></div></div>${run?`<p class="iv-note">保留调查当时的 ${run.alertIds.length} 条输入范围。当前成员变更不会改写历史关系。</p><a class="button" href="${route(run,'graphs')}">查看攻击链、路径与关联范围</a>${graphPart('attack_path',run.graphs.attack_path,run)}`:no('尚无保存的案件关系')}</div>`;
  }
  function recordedGraphs(run,chosen){
    const all=window.aisoc20RecordedData.graph,input=new Set(run.alertIds),inCase=currentRoute().page==='cases';
    const inputEdges=all.edges.filter(e=>input.has(e.source)),shared=new Set(inputEdges.filter(e=>e.label!=='MAPS_TO').map(e=>e.target));
    const ids=inCase?[...new Set([...scopeAlerts().map(a=>a.id),...input])]:[...new Set([...input,...all.edges.filter(e=>shared.has(e.target)).map(e=>e.source)])];
    const g=recordedGraphData(ids),members=ids.map(getAlert).filter(Boolean).sort((a,b)=>Date.parse(a.event_time)-Date.parse(b.event_time));
    const skipped=run.steps.find(s=>s.payload?.node==='attack_path'&&s.payload?.step_status==='skipped');
    const timeline=card('关联告警时序',`<p class="iv-note">按告警发生时间排列。共享对象是关联线索，时间先后不表示攻击因果。</p><div class="iv-recorded-chain">${members.map((a,i)=>{const related=g.edges.filter(e=>e.source===a.id);return `<article><div class="iv-chain-num">${i+1}</div><div><div class="iv-foot"><time>${format(a.event_time)}</time>${badge(input.has(a.id)?'本次输入':'关联告警',input.has(a.id)?'blue':'')}</div><a class="iv-alert-title" href="#/alerts/${a.id}/overview">${esc(a.title)}</a><div class="iv-tags">${related.filter(e=>e.label!=='MAPS_TO').map(e=>badge(g.nodes.find(n=>n.id===e.target)?.label||e.target)).join('')}</div></div></article>`;}).join('')}</div>`);
    const map=card(chosen==='attack_path'?'路径核查线索':'告警与实体关系',`<div class="iv-foot"><span>${g.nodes.length} 个对象 · ${g.edges.length} 条已记录关系</span><span>${format(g.generatedAt)}</span></div>${relationDiagram(g,run.alertIds)}`);
    return `<div class="iv-callout"><b>${skipped?'攻击路径分析已跳过':'本次未保存独立链图结果'}</b><p>${skipped?'当时没有关联 Case，未执行攻击路径遍历。':'保留已知资料，不从报告反推路径。'}下方展示同批告警的已保存关系，不是本次 Run 产生的攻击路径。</p></div><p class="iv-note">${inCase?'范围：本次输入与当前 Case 成员':'范围：本次输入及同批共享主机、账户或 IOC 的告警'}。蓝色标识为本次调查输入；点击告警可回查来源。</p><div class="iv-stack">${chosen==='attack_chain'?timeline+map:map+(chosen==='all'?timeline:'')}</div>`;
  }
  function graphPart(kind,p,run){
    const labels={attack_chain:'攻击链 · Attack Chain',attack_path:'攻击路径 · Attack Path',alert_graph:'关联范围 · Alert Graph'},d=p?.data||{};
    if(!p)return card(labels[kind],no('本次未保存此类材料'));
    const explanation=p.error==='no_linked_case'?'该告警没有关联 Case，因此没有 Case 路径；仍可查看 Alert Graph。':p.status==='empty'?'当前种子与查询范围没有返回候选关系。':p.error?String(p.error):'';
    let body=`<div class="iv-foot">${badge(statuses[p.status]||p.status,p.status==='success'?'blue':'amber')}<span>${esc(p.source||'—')} · ${format(p.queried_at)}</span></div>${explanation?`<p>${esc(explanation)}</p>`:''}`;
    if(kind==='attack_chain')body+=`<div class="iv-pair"><span>候选告警 / 时间窗口</span><b>${d.chain?.length??'—'} / ${esc(d.window||'—')}</b></div>${(d.chain||[]).map(c=>`<div class="iv-chain-item">${getAlert(c.alert_id)?alertLink(c.alert_id):esc(c.title)}<small>${format(c.event_time)} · ${esc(JSON.stringify(c.shared_entities||[]))}</small>${run?.sourceCaseId?badge(run.alertIds.includes(c.alert_id)?'本次 Case 输入':'历史外部候选',run.alertIds.includes(c.alert_id)?'blue':''):''}<small>候选评分 ${c.score??'—'} · 图距离 ${c.distance??'—'}</small></div>`).join('')}`;
    if(kind==='attack_path'&&d.nodes)body+=`<p class="iv-note">${d.nodes.length} 个对象 · ${d.edges.length} 条已记录关系</p>`+pathGraph(d);
    if(kind==='alert_graph'&&p.status==='success'){
      const n=d.neighbors||{},b=d.blast_radius||{};body+=`<div class="iv-stats">${metric('直接邻居',n.neighbor_count??n.neighbors?.length)}${metric('图可达实体',b.total_affected)}${metric('遍历深度',b.hops)}${metric('范围评分',b.blast_radius_score)}</div><p class="iv-note">图可达范围不等于已确认受害范围。</p><div class="iv-node-grid">${(n.neighbors||[]).map(x=>{const node=x.node||x.neighbor||x,pr=node.properties||{};return `<div><span>${esc(node.label||node.labels?.[0]||'实体')}</span><strong>${esc(pr.indicator_value||pr.hostname||pr.username||pr.value||pr.name||pr.title||node.id||'关联对象')}</strong><small>${esc(x.rel_type||x.relationship||x.relationship_type||x.type||'关联关系')}</small></div>`;}).join('')}</div>`;
    }
    return card(labels[kind],body+`<details class="iv-raw"><summary>查看保存的关系数据</summary>${json(p)}</details>`);
  }
  function pathGraph(data){
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
    return `<div class="iv-relationship-map"><svg viewBox="0 0 1050 ${h+20}" role="img" aria-label="本次 Case 联合调查保存的路径图"><defs><marker id="iv-case-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#9bb2c8"/></marker></defs>${['案件','三条输入告警','主机与账户','技术与线索'].map((x,i)=>`<text class="iv-map-column" x="${xs[i]}" y="25">${x}</text>`).join('')}<g class="iv-map-edges">${edges}</g>${nodes}</svg></div><details class="iv-raw"><summary>查看 ${data.edges.length} 条原始关系</summary><div class="iv-relations">${data.edges.map(e=>`<p>${esc(labels.get(e.source)||e.source)}<span> — ${esc(relationNames[e.type]||e.type)}（${esc(e.type)}）→ </span>${esc(labels.get(e.target)||e.target)}</p>`).join('')}</div></details>`;
  }
  function sourceGraphs(run){
    const q=new URLSearchParams(currentRoute().search),requested=q.get('graph'),kinds=['attack_chain','attack_path','alert_graph'],chosen=kinds.includes(requested)?requested:'all';
    let fixture='';if(!run.recorded&&!run.graphs?.attack_path){const members=store.alerts.filter(a=>run.alertIds.includes(a.id)),g=window.referenceWorkspaces.graph(store,members,{grouped:false});fixture=card('输入告警的关联资料',`<p class="iv-note">以下关系来自所选输入告警；本次未保存独立 Chain / Path 服务返回，不能将当前关系当作当次服务快照。</p>${pathGraph({nodes:g.nodes,edges:g.edges})}`);}
    return `<div class="iv-section-title"><div><h3>攻击链与路径分析</h3><p>${run.sourceEnvironment==='aisoc20'?'查看已有告警关系、发生时序与本次路径分析状态。':'查看本次保存的关联告警链、Case 路径与图可达范围。'}</p></div></div><nav class="iv-filter-tabs" aria-label="关系分析类型">${[['all','全部材料'],['attack_chain','攻击链'],['attack_path','攻击路径'],['alert_graph','关联范围']].map(([k,n])=>`<a href="${route(run,'graphs')}${currentRoute().page==='cases'?'&':'?'}graph=${k}" ${chosen===k?'aria-current="page"':''}>${n}</a>`).join('')}</nav><p class="iv-note">关联链和图可达范围不自动表示攻击因果或已确认受害范围。</p><div class="iv-stack">${run.sourceEnvironment==='aisoc20'?recordedGraphs(run,chosen):(chosen==='all'?kinds:[chosen]).map(k=>graphPart(k,run.graphs[k],run)).join('')}${fixture}</div>`;
  }
  function graphs(run){
    const mode=new URLSearchParams(currentRoute().search).get('graph');let context=null,notice='';
    if(run.sourceEnvironment==='aisoc20'){
      const all=window.aisoc20RecordedData.graph,input=new Set(run.alertIds),shared=new Set(all.edges.filter(e=>input.has(e.source)&&e.label!=='MAPS_TO').map(e=>e.target));
      const ids=currentRoute().page==='cases'?[...new Set([...scopeAlerts().map(a=>a.id),...input])]:[...new Set([...input,...all.edges.filter(e=>shared.has(e.target)).map(e=>e.source)])];
      context={...recordedGraphData(ids),source:'AiSOC20历史告警关联资料'};
      const skipped=run.steps.some(s=>s.payload?.node==='attack_path'&&s.payload?.step_status==='skipped');
      notice=`<div class="iv-callout"><b>${skipped?'攻击路径分析已跳过':'本次未保存独立链图结果'}</b><p>下图为本次输入与相关告警的已保存上下文，不是本次 Run 产生的攻击路径。</p></div>`;
    }else if(!run.recorded&&!run.graphs?.attack_path){
      const members=store.alerts.filter(a=>run.alertIds.includes(a.id)),g=window.referenceWorkspaces.graph(store,members,{grouped:false});context={...g,nodes:[...g.nodes,...members.map(a=>({id:a.id,kind:'alert',label:a.title}))],edges:[...g.edges,...members.flatMap(a=>(a.entityIds||[]).filter(id=>g.nodes.some(n=>n.id===id)).map(id=>({source:a.id,target:id,label:'告警关联实体'})))],source:'输入告警的关联资料'};
      notice='<p class="iv-note">以下关系来自输入告警关联资料，本次未保存独立 Chain / Path 服务返回。</p>';
    }
    const path=run.graphs?.attack_path;if(path&&path.status!=='success')notice+=`<p class="iv-note">攻击路径：${esc(statuses[path.status]||path.status)}${path.error==='no_linked_case'?' · 当时未关联 Case':''}。其他来源材料分别保留。</p>`;
    const saved=sourceGraphs(run);
    return `<div class="iv-section-title"><div><h3>调查关系图</h3><p>聚焦告警、共享实体与技术，查看跨告警关联及其依据。</p></div></div>${notice}${unifiedGraph.render(run,context,mode)}<p class="iv-note">连线表示已记录关系或候选关联，不表示攻击因果。选择和筛选不会修改 Case 成员或调查输入。</p><details class="iv-graph-materials" ${mode==='alert_graph'?'open':''}><summary>来源材料与关联范围 · Attack Chain / Attack Path / Alert Graph</summary><div class="iv-stack">${saved}</div></details>`;
  }
  function report(run){return `<div class="iv-section-title"><h3>调查报告</h3>${run.report?btn('下载 Markdown','iv-download',run.id,'small','download'):''}</div>${run.completion==='partial'?`<div class="iv-callout">部分交付 · 请结合停止原因与工具返回核对报告。</div>`:''}${run.report?`<article class="iv-card iv-report"><pre>${esc(run.report)}</pre></article>`:no('本次没有保存报告正文','调查发现和已有步骤仍可查看。')}${card('建议与执行',`<h4>建议动作 (${run.actions.length})</h4>${actionList(run.actions)||'<p class="iv-note">未保存建议动作。</p>'}<h4>实际执行 (${run.executed.length})</h4>${run.executed.map(a=>`<p>${esc(text(a))}</p>`).join('')||'<p class="iv-note">没有已执行动作记录；建议不代表已执行。</p>'}`)}`;}
  function workbench(){
    const r=currentRoute();if(r.page==='investigations'&&!r.id)return queue();
    const rows=available(),run=active();if(!run)return `<div class="iv-root">${no('没有关联调查运行','可以查看已有告警、材料与人工协作信息。')}<a class="button" href="#/investigations">查看全部调查运行</a></div>`;
    const requested=r.page==='cases'?new URLSearchParams(r.search).get('view'):r.tab,view=['overview','process','tools','graphs','ledger','report'].includes(requested)?requested:'overview';
    return `<div class="iv-root"><div class="iv-heading"><div><h2>${r.page==='cases'?'AI 调查':'调查详情'}</h2><p>查看关键发现、分析依据与后续处理。</p></div><a class="button" href="#/investigations">全部运行 ${I('list',14)}</a></div><div class="iv-run-selector"><label for="iv-run">当前调查</label><select id="iv-run" data-iv-run>${rows.map(x=>`<option value="${x.id}" ${x.id===run.id?'selected':''}>${esc(x.title)} · ${x.completion==='completed'?'完整交付':names[x.completion]||'未记录'}</option>`).join('')}</select>${brief(run)}</div><div class="iv-run-title"><h3>${esc(run.title)}</h3><span class="iv-note">${run.alertIds.length} 条输入告警${run.started?' · '+format(run.started):''}</span></div><nav class="iv-tabs" aria-label="调查运行内容">${[['overview','调查发现'],['process','阶段分析'],['tools','查询与证据'],['graphs','调查关系图'],['ledger','调查记录'],['report','报告与响应']].map(([k,n])=>`<a href="${route(run,k)}" ${view===k?'aria-current="page"':''} class="${view===k?'active':''}">${n}${k==='tools'&&run.tools.length?`<span>${run.tools.length}</span>`:''}</a>`).join('')}</nav>${view==='overview'?overview(run):view==='process'?process(run):view==='tools'?tools(run):view==='graphs'?graphs(run):view==='ledger'?ledger(run):report(run)}</div>`;
  }
  function change(el){
    if(unifiedGraph.change(el))return true;
    if(el.hasAttribute('data-iv-run')){const run=available().find(r=>r.id===el.value);if(run){const r=currentRoute(),view=r.page==='cases'?new URLSearchParams(r.search).get('view'):r.tab;navigate(route(run,['overview','process','tools','graphs','ledger','report'].includes(view)?view:'overview'));}return true;}
    if(el.hasAttribute('data-iv-kind')||el.hasAttribute('data-iv-agent')){const run=active();if(run){const q=new URLSearchParams(currentRoute().search);q.set(el.hasAttribute('data-iv-kind')?'kind':'agent',el.value);const target=route(run,'ledger').split('?')[0];if(currentRoute().page==='cases'){q.set('run',run.id);q.set('view','ledger');}navigate(`${target}?${q}`);}return true;}
    return false;
  }
  function handle(action,id){if(unifiedGraph.handle(action,id))return true;if(action!=='iv-download')return false;const run=active();if(run?.id===id&&run.report)downloadFile(`investigation-${id}.md`,run.report,'text/markdown;charset=utf-8');return true;}
  return {flowCaseOverview,flowCaseMaterials,flowCaseRelations,workbench,queue,linkedRuns,incidentSummary,incidentOverview,basicInvestigations,incidentMaterials,incidentRelations,caseRelations,persistedCaseRelations,change,handle};
};
