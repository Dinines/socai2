'use strict';
window.createAlertDetail = function(ctx){
  const {store,esc,date,I,btn,badge,severity,state,entityChip,getAsset,save,render,navigate,toast,breadcrumbs,tabsMarkup}=ctx;
  const verdicts={true_positive:'真实威胁',false_positive:'误报',benign:'正常行为',escalate:'需人工跟进'};
  const card=(title,body)=>`<article class="card detail-card"><div class="card-title"><h3>${title}</h3></div>${body}</article>`;
  const json=v=>`<pre class="detail-json">${esc(JSON.stringify(v,null,2))}</pre>`;
  const link=(a,tab,text)=>`<a href="#/alerts/${a.id}/${tab}">${text}</a>`;
  const field=(label,value)=>`<div><div class="info-label">${label}</div><div class="info-value">${value}</div></div>`;
  const sourceScope=a=>[a.sourceEnvironment||'socai2-21',a.sourceTenantId||a.detailMaterial?.raw?.tenant_id||''].join(':');
  const related=a=>(a.persistedRecord||a.fixture)?store.alerts.filter(x=>(x.persistedRecord||x.fixture)&&sourceScope(x)===sourceScope(a)&&x.id!==a.id&&x.hostNames.some(h=>a.hostNames.includes(h))).sort((x,y)=>Date.parse(y.event_time)-Date.parse(x.event_time)).slice(0,7):store.alerts.filter(x=>x.id!==a.id&&x.category===a.category&&x.source===a.source);
  const similar=a=>(a.persistedRecord||a.fixture)?store.alerts.filter(x=>(x.persistedRecord||x.fixture)&&sourceScope(x)===sourceScope(a)&&x.id!==a.id&&((x.hostNames.some(h=>a.hostNames.includes(h))&&x.tactics.some(t=>a.tactics.includes(t)))||x.iocKeys.some(i=>a.iocKeys.includes(i)))).sort((x,y)=>Date.parse(y.event_time)-Date.parse(x.event_time)).slice(0,5):related(a);
  const recordedRuns=a=>window.investigationWorkspaceModel?.forAlerts(store,[a])||[];
  function recordedExplanation(a){
    if(!a.recordedImport||!a.sourceRecord?.latest_explanation_id)return null;
    for(const run of recordedRuns(a)){
      const artifact=run.artifacts.find(x=>x.sourceArtifactId===a.sourceRecord.latest_explanation_id&&x.kind==='alert_explanation'&&x.sourceRecord?.alert_id===a.sourceAlertId);
      const body=artifact&&run.artifactBodies[artifact.id];if(body?.mode==='full'&&body.format==='json')return {run,artifact,value:body.content};
    }
    return null;
  }
  function explanationBody(a,exp){
    const saved=recordedExplanation(a);
    if(saved)return `<div class="row between"><span class="muted">已保存的告警解释 · ${date(saved.value.generated_at)}</span></div><p>${esc(saved.value.body)}</p><p class="muted">解释属于告警基本分析，不代表案件已形成判断。<a href="#/investigations/${esc(saved.run.id)}/overview">查看分诊与依据</a></p><details><summary>解释原件与来源引用</summary>${json(saved.value)}</details>`;
    if(a.persistedRecord)return `<div class="row between"><span class="muted">Explain · ${exp.generatedAt?date(exp.generatedAt):'—'}</span></div><p>${esc(exp.summary)||'暂无解释内容。'}</p>${exp.suggestedActions.length?`<h4>建议动作</h4>${exp.suggestedActions.map(x=>`<p><b>${esc(x.title)}</b>${x.rationale?`<br>${esc(x.rationale)}`:''}</p>`).join('')}`:''}`;
    return `<div class="row between"><span class="muted">预生成解释 · ${date(exp.generatedAt)}</span></div><p>${esc(exp.summary)}</p><h4>关键证据</h4>${exp.evidence.length?exp.evidence.map(x=>`<p>${esc(x)}</p>`).join(''):'<p class="muted">暂无关联证据。</p>'}<h4>待核实事项</h4><ul>${exp.gaps.map(x=>`<li>${esc(x)}</li>`).join('')||'<li>当前输入范围无待补材料。</li>'}</ul>${(exp.suggestedActions||[]).length?`<h4>建议动作</h4>${exp.suggestedActions.map(x=>`<p><b>${esc(x.title)}</b><br>${esc(x.rationale)}</p>`).join('')}`:''}`;
  }
  const detection=a=>window.socai2RecordedImport?.detectionView(a);
  function detectionScore(value){
    if(value.score!==null)return Number(value.score.toFixed(1))+'/100';
    return ({not_provided:'未提供',not_computed:'未计算',disabled:'未启用',failed:'计算失败',legacy_unverified:'历史值未核实'})[value.confidenceState]||'未记录';
  }
  function attackLabels(a,m){
    const source=detection(a);
    if(!source)return `<p>${badge(a.category,'purple')}</p><p class="muted">${a.persistedRecord||a.fixture?esc((m.techniques||[]).join(' · ')||'尚未提供具体技术编号。'):a.category==='执行'?'T1059.001 · PowerShell':'当前仅记录战术，未提供具体技术编号。'}</p>`;
    return `<p>${source.tactics.map(t=>badge(t,'purple')).join(' ')||'来源未提供战术标签。'}</p><p class="muted">${esc(source.techniques.join(' · ')||'来源未提供技术编号。')}</p><p class="muted">读取来源检测材料的 ATT&CK 标签；不由告警类别推断攻击阶段。</p>`;
  }
  const assets=a=>a.entityIds.map(getAsset).filter(Boolean);
  function upgradeTimeline(a,m){
    if(m.timelineVersion===2)return;
    const time=a.event_time||a.first,at=seconds=>new Date(Date.parse(time)+seconds*1000).toISOString();
    const seed=[{time:at(15),title:'告警被检测到',description:`${a.source} 检测规则命中`},{time:at(40),title:'告警启动调查',description:'自动分诊升级调查，开始核对关联证据'},{time:at(120),title:'告警完成关联取证',description:'已收集当前可用的关联证据；授权记录仍待补充'}];
    const ingested=m.history.find(x=>x.title==='告警入库');if(ingested)ingested.time=at(25);
    if(a.owner!=='未分配')seed.push({time:at(30),title:'告警分配',description:`负责人：${a.owner}`});
    if(a.status==='Resolved')seed.push({time:a.last,title:'告警关闭',description:'处理状态更新为已解决'});
    for(const event of seed){if(!m.runs.length&&['告警启动调查','告警完成关联取证'].includes(event.title))continue;if(!m.history.some(x=>x.title===event.title))m.history.push(event);}
    m.timelineVersion=2;
  }
  function material(a){
    if(a.detailMaterial){
      const m=a.detailMaterial;
      m.history||=[];m.runs||=[];m.raw||={};m.confidence||={score:null,factors:[]};
      if(typeof m.explanation==='string')m.explanation={summary:m.explanation};
      m.explanation||={};m.explanation.evidence||=[];m.explanation.gaps||=[];m.explanation.suggestedActions||=[];
      if(a.persistedRecord||a.fixture)m.responseRecommendations||=[];
      upgradeTimeline(a,m);return m;
    }
    const time=a.event_time||a.first, evidence=store.evidence.filter(e=>e.alertId===a.id);
    const result=a.detailMaterial={
      explanation:{generatedAt:a.last,summary:`${a.description} 当前材料表明检测规则命中，是否构成真实威胁仍需结合授权信息和原始证据核查。`,evidence:evidence.map(e=>e.name),gaps:['资产操作是否经过授权尚待确认','当前材料不足以确定完整影响范围']},
      confidence:{score:80,label:'高',factors:[['来源检测信号',0.35],['实体关联信息',0.30],['上下文完整程度',0.15]]},risk:85,
      raw:{id:a.id,event_time:time,source:a.source,source_ref:`SRC-${a.id}`,category:a.category,title:a.title,description:a.description,entities:assets(a).map(e=>({id:e.id,type:e.type,name:e.name})),tags:[...a.tags]},
      history:[{time,title:'告警发生',description:a.title},{time:a.last,title:'告警入库',description:`接收来自 ${a.source} 的告警`}],
      runs:a.id==='alert-unassigned-case-001'?[]:[{id:`run-demo-${a.id}`,time:a.last,status:'Completed',completion:'partial',stop:'缺少授权与完整源记录，保留已有结果并交接人工。',steps:[{name:'告警分诊',agent:'Triage',status:'Completed',input:{alert_id:a.id},output:{decision:'需要核查',reason:'需结合实体及授权信息'}},{name:'关联证据查询',agent:'Recon',status:'Completed',input:{alert_id:a.id},output:{matched:evidence.length,evidence_ids:evidence.map(e=>e.id)}},{name:'授权核验',agent:'Forensic',status:'Pending',input:{entities:a.entityIds},output:{reason:'授权记录未提供'}}],tools:[{name:'查询关联证据',args:{alert_id:a.id},status:'已返回',result:evidence.map(e=>({id:e.id,name:e.name,verdict:e.verdict}))}],findings:['已核对告警及其关联实体；检测命中不等于恶意行为已确认。'],actions:['核对资产负责人及授权记录','补充源事件后复核告警'],calls:2,tokens:2840,report:null}]
    };upgradeTimeline(a,result);return result;
  }
  const caseChoices={};
  const canPrepare=(c,a)=>!ctx.canPrepareCase||ctx.canPrepareCase(c,a);
  const confirmLabel=choice=>choice.intent==='prepare'?(choice.mode==='new'?'创建并准备调查':'继续准备调查'):(choice.mode==='new'?'创建并关联':'确认关联');
  function openCaseChoice(a,intent='link'){
    const linked=store.cases.filter(c=>c.alertIds.includes(a.id)&&canPrepare(c,a));
    caseChoices[a.id]={mode:'existing',selected:linked.length===1?linked[0].id:'',query:'',intent};
    render();document.getElementById('case-dialog-'+a.id).showModal();
  }
  function caseResults(aid,query=''){
    const selected=caseChoices[aid]?.selected||'',q=query.trim().toLowerCase();
    const a=store.alerts.find(a=>a.id===aid),preparing=caseChoices[aid]?.intent==='prepare';
    const rows=store.cases.filter(c=>canPrepare(c,a)&&(!q||[c.title,c.id].some(v=>String(v).toLowerCase().includes(q)))).sort((a,b)=>Date.parse(b.updated||b.created)-Date.parse(a.updated||a.created));
    const shown=q?rows:rows.slice(0,7);
    return `<p class="muted">${q?`找到 ${rows.length} 个 Case`:`最近活跃的 ${shown.length} 个 Case`}</p><div class="case-choice-list">${shown.map(c=>`<label class="case-choice"><input type="radio" name="caseId" value="${esc(c.id)}" ${selected===c.id?'checked':''}><span><b>${esc(c.localCollection?c.title.replace(/（本地整理）$/, ''):c.title)}</b><small>#${esc(c.id)} · 最近活跃 ${date(c.updated||c.created)}</small></span></label>`).join('')||'<p class="muted">没有匹配的 Case。</p>'}</div>`;
  }
  function caseForm(a){
    const linked=store.cases.filter(c=>c.alertIds.includes(a.id));
    const choice=caseChoices[a.id] ||= {mode:'existing',selected:linked[0]?.id||'',query:''};
    if(linked.length&&choice.mode==='new')choice.mode='existing';
    return `<dialog id="case-dialog-${a.id}" class="case-association-dialog" aria-label="${choice.intent==='prepare'?'选择调查 Case':'关联 Case'}"><header class="row between"><h2>${choice.intent==='prepare'?'选择调查 Case':'关联 Case'}</h2><button type="button" class="icon-button" data-case-close aria-label="关闭Case选择">×</button></header><form id="case-form-${a.id}" data-detail-form="case" data-alert="${a.id}"><input type="hidden" name="caseMode" value="${choice.mode}"><div class="case-mode-tabs" role="tablist" aria-label="Case 关联方式"><button type="button" role="tab" id="case-existing-tab-${a.id}" aria-controls="case-existing-panel-${a.id}" aria-selected="${choice.mode==='existing'}" data-case-mode="existing">关联已有 Case</button><button type="button" role="tab" id="case-new-tab-${a.id}" aria-controls="case-new-panel-${a.id}" aria-selected="${choice.mode==='new'}" data-case-mode="new" ${linked.length?'disabled title="当前告警已关联 Case"':''}>新建 Case</button></div><div data-case-new role="tabpanel" id="case-new-panel-${a.id}" aria-labelledby="case-new-tab-${a.id}" ${choice.mode==='new'?'':'hidden'}><label for="case-title-${a.id}">新 Case 名称</label><input id="case-title-${a.id}" name="title" value="${linked.length?'':esc(a.description)}" maxlength="4000" ${choice.mode==='new'&&!linked.length?'':'disabled'}></div><div data-case-existing role="tabpanel" id="case-existing-panel-${a.id}" aria-labelledby="case-existing-tab-${a.id}" ${choice.mode==='existing'?'':'hidden'}><label for="case-search-${a.id}">搜索 Case</label><input id="case-search-${a.id}" name="caseSearch" type="search" placeholder="搜索 Case 名称或 ID" value="${esc(choice.query)}"><div data-case-results>${caseResults(a.id,choice.query)}</div><p data-case-selected class="muted">已选择：${esc(store.cases.find(c=>c.id===choice.selected)?.title||'尚未选择')}</p></div><footer class="row"><span class="spacer"></span><button type="button" class="button" data-case-close>取消</button><button class="button primary" name="mode" value="link" data-case-confirm>${confirmLabel(choice)}</button></footer></form></dialog>`;
  }
  function setCaseMode(form,mode){
    const linked=store.cases.some(c=>c.alertIds.includes(form.dataset.alert));
    if(mode==='new'&&linked)return;
    caseChoices[form.dataset.alert].mode=mode;form.elements.caseMode.value=mode;
    form.querySelector('[data-case-new]').hidden=mode!=='new';
    form.querySelector('[data-case-existing]').hidden=mode!=='existing';
    form.elements.title.disabled=mode!=='new';
    form.querySelectorAll('[data-case-mode]').forEach(tab=>tab.setAttribute('aria-selected',String(tab.dataset.caseMode===mode)));
    form.querySelector('[data-case-confirm]').textContent=confirmLabel(caseChoices[form.dataset.alert]);
  }
  function overview(a,m){
    const exp=m.explanation,linked=store.cases.filter(c=>c.alertIds.includes(a.id)),sourceDetection=detection(a);
    const props=card('告警属性',`<div class="info-grid">${field('处理状态',state(a.status))}${field('负责人',esc(a.owner))}${field('告警时间',date(a.event_time||a.first))}${field('严重程度',severity(a.severity))}${field('检测源',esc(a.source))}${field('检测类别',esc(a.category))}${sourceDetection?field('来源检测置信度',esc(detectionScore(sourceDetection)))+field('检测评分来源',esc(sourceDetection.scoreSource||'未记录')):''}${field('源记录 ID',esc(a.recordedImport?a.sourceRecord?.source_alert_id||'未记录':m.raw.source_ref||'—'))}${field('租户',esc(a.recordedImport?a.sourceTenantId:m.tenantName||'Contoso'))}${field('告警 ID',esc(a.sourceAlertId||a.id))}${field('资产标签',assets(a).flatMap(e=>e.tags||[]).filter((v,i,l)=>l.indexOf(v)===i).map(t=>badge(t)).join(' ')||'—')}</div>`);
    const matches=related(a),candidates=similar(a);
    return `<div class="full-alert-layout"><div class="stack">${card('发生了什么',explanationBody(a,exp))}${card('关联实体与 IOC',assets(a).map(e=>`<div class="entity-list-item">${entityChip(e)}<span class="spacer"></span>${(e.tags||[]).map(t=>badge(t)).join(' ')}${['ip','file'].includes(e.type)?badge('IOC · 待核验','amber'):''}</div>`).join(''))}${card('MITRE ATT&CK',attackLabels(a,m))}${card('相关告警 / 相似历史',`<p class="muted">${a.persistedRecord||a.fixture?'同一主机最近发生的告警，需逐条复核。':'相同检测源与类别的候选，需逐条复核。'}</p>${matches.slice(0,a.persistedRecord?7:6).map(x=>`<div class="entity-list-item related-alert-row"><a href="#/alerts/${x.id}/overview">${esc(x.title)}</a><span aria-label="威胁等级">${severity(x.severity)}</span><time class="muted" datetime="${esc(x.event_time||x.first)}" title="告警时间">${date(x.event_time||x.first)}</time></div>`).join('')||'<p>暂无匹配告警。</p>'}`)}</div><aside class="stack">${props}${card('Case',`<p>${linked.length?linked.map(c=>`<a href="#/cases/${c.id}/case-info">${esc(c.localCollection?c.title.replace(/（本地整理）$/, ''):c.title)}</a><br><small class="muted">Case ID：${esc(c.sourceCaseId||c.id)}</small>`).join('<br>'):'尚未关联 Case'}</p><button type="button" class="button" data-case-open="${a.id}" ${a.recordedImport?'disabled title="执行导出只读"':''}>关联到</button>`)}${a.recordedImport?card('判定与反馈','<p>此为执行导出的只读记录。告警分诊见关联调查；本页不保存人工反馈或改变源判定。</p>'):card('判定与反馈',`<p>当前判定：<b>${esc(verdicts[a.disposition]||({needs_review:'需人工跟进',benign_true_positive:'正常行为'}[a.disposition])||'尚未判定')}</b></p><form data-detail-form="feedback" data-alert="${a.id}"><p class="muted">AI 的判断是否准确？选择你的判定。</p><div class="verdict-options" role="radiogroup" aria-label="人工判定">${Object.entries(verdicts).map(([v,l])=>`<label class="verdict-option ${v}"><input type="radio" name="verdict" value="${v}" required><span><b>${l}</b><small>${{true_positive:'真实威胁，确认或提高威胁判定',false_positive:'检测误报，应排除威胁',benign:'符合预期的正常或授权行为',escalate:'需要人工进一步跟进'}[v]}</small></span></label>`).join('')}</div><label for="reason-${a.id}">理由 / 交接信息</label><textarea id="reason-${a.id}" name="reason" maxlength="4000" placeholder="记录核查依据">${esc(a.feedbackReason||'')}</textarea><button class="button primary" disabled>保存反馈</button></form>${a.disposition?`<details><summary>复核相似历史告警 (${candidates.length})</summary><form data-detail-form="redisposition" data-alert="${a.id}"><div class="row"><button class="link-button" type="button" data-candidate-check="all">全选</button><button class="link-button" type="button" data-candidate-check="none">清除选择</button></div>${candidates.map(x=>`<label class="check-option"><input type="checkbox" name="ids" value="${x.id}">${esc(x.title)}</label>`).join('')}<button class="button">将当前判定应用到所选</button></form></details>`:''}<p class="muted">保存反馈后，可选择相似历史告警进行复核。</p>`)}</aside></div>`;
  }
  function response(a,m){
    if(!m.responseRecommendations){const host=assets(a).find(e=>e.type==='device');m.responseRecommendations=host?[{action:'隔离主机',target:host.name,reason:'建议核对终端关联活动和业务影响，确认风险后再隔离。',approval:'待审核',execution:'未执行'}]:[];}
    return card('响应详情',m.responseRecommendations.length?m.responseRecommendations.map(r=>`<div class="response-summary"><div><span class="info-label">建议动作</span><h4>${esc(r.action)}</h4></div><div><span class="info-label">目标资产</span><p>${esc(r.target)}</p></div><div><span class="info-label">审批状态</span><p>${badge(r.approval,'amber')}</p></div><div><span class="info-label">执行结果</span><p>${badge(r.execution)}</p></div></div><p class="muted">建议原因：${esc(r.reason)}</p>`).join(''):'<p class="muted">暂无响应建议。</p>')+tracking(a,m);
  }
  function tracking(a,m){
    if(a.recordedImport){
      const runs=recordedRuns(a),names={alert_basic:'告警分诊 A',incident_diagnosis:'事件诊断 I',baseline:'案件调查 C'},states={completed:'已结束',failed:'失败',pending_update:'待启动',running:'运行中',unknown:'状态待确认',cancelled:'已取消'};
      return card('已保存的关联调查',runs.map(r=>`<div class="entity-list-item"><div><a href="#/investigations/${esc(r.id)}/overview">${esc(names[r.investigationKind]||r.title)}</a><p class="muted">${esc(states[r.status]||r.status)} · ${r.completion==='partial'?'部分交付':r.completion==='completed'?'完整交付':'交付完整性未记录'} · ${date(r.started||r.requestedAt)}</p></div></div>`).join('')||'<p>本次导出没有与此告警关联的调查记录。</p>');
    }
    if(m.caseInvestigation){const r=m.caseInvestigation;return card('关联 Case 调查',`<p>本告警属于一次包含 ${r.inputCount} 条告警的联合调查。分析过程与响应建议在对应调查中查看。</p><a class="button" href="#/cases/${esc(r.caseId)}/investigations?run=${esc(r.runId)}&view=overview">查看 Case 联合调查</a>`);}
    return m.runs.map(r=>card('自动处理过程',`<div class="row wrap">${badge(r.id,'blue')}${state(r.status)}${badge(r.completion==='partial'?'部分完成':r.completion==='not_escalated'?'未升级调查':r.completion==='completed'?'完整交付':'尚未交付','amber')}</div><p>记录时间：${date(r.time)}</p>${r.stop?`<div class="notice warning">${esc(r.stop.replace('模拟调查','调查'))}</div>`:''}<h4>处理步骤 (${r.steps.length})</h4>${r.steps.map((s,i)=>`<details class="trace-step"><summary><span>#${i+1} ${esc(s.name)} · ${esc(s.agent)}</span>${state(s.status)}</summary><div class="trace-io"><div><h4>输入</h4>${json(s.input)}</div><div><h4>输出 / 缺口</h4>${json(s.output)}</div></div></details>`).join('')}<details><summary>查询与工具返回 (${r.tools.length})</summary>${r.tools.map(t=>`<h4>${esc(t.name)} · ${esc(t.status)}</h4><div class="trace-io">${json(t.args)}${json(t.result)}</div>`).join('')||'<p>尚无工具调用记录。</p>'}</details><div class="trace-io"><div><h4>调查发现</h4>${r.findings.map(x=>`<p>${esc(x)}</p>`).join('')||'<p>尚无调查发现。</p>'}</div><div><h4>建议动作 · 未执行</h4>${r.actions.map(x=>`<p>${esc(x)}</p>`).join('')||'<p>暂无建议。</p>'}</div></div><p class="muted">${r.calls===null?'模型用量尚未记录':`模型调用 ${r.calls} 次 · ${r.tokens.toLocaleString()} tokens`}</p>${r.report?`<details><summary>调查报告</summary><pre class="detail-json">${esc(r.report)}</pre></details>`:'<p class="muted">暂无已保存的调查报告。</p>'}`)).join('')||card('自动处理过程','暂无 Run 记录。');
  }
  document.addEventListener('change',event=>{const form=event.target.closest('[data-detail-form="feedback"]');if(form&&event.target.name==='verdict')form.querySelector('button[type="submit"],button:not([type])').disabled=false;});
  document.addEventListener('click',event=>{const button=event.target.closest('[data-candidate-check]');if(!button)return;button.closest('form').querySelectorAll('input[name="ids"]').forEach(input=>input.checked=button.dataset.candidateCheck==='all');});
  document.addEventListener('input',event=>{const form=event.target.closest('[data-detail-form="case"]');if(!form||event.target.name!=='caseSearch')return;caseChoices[form.dataset.alert].query=event.target.value;form.querySelector('[data-case-results]').innerHTML=caseResults(form.dataset.alert,event.target.value);});
  document.addEventListener('change',event=>{const form=event.target.closest('[data-detail-form="case"]');if(!form||event.target.name!=='caseId')return;const choice=caseChoices[form.dataset.alert];choice.selected=event.target.value;choice.mode='existing';form.elements.caseMode.value='existing';form.querySelector('[data-case-new]').hidden=true;form.elements.title.disabled=true;form.querySelector('[data-case-selected]').textContent='已选择：'+store.cases.find(c=>c.id===choice.selected).title;});
  document.addEventListener('click',event=>{
    const open=event.target.closest('[data-case-open]');if(open){const a=store.alerts.find(a=>a.id===open.dataset.caseOpen);if(a)openCaseChoice(a);return;}
    const close=event.target.closest('[data-case-close]');if(close){close.closest('dialog').close();return;}
    const modeTab=event.target.closest('[data-case-mode]');if(modeTab&&!modeTab.disabled){setCaseMode(modeTab.closest('form'),modeTab.dataset.caseMode);return;}
    const button=event.target.closest('[data-detail-investigate]');if(button){
      event.preventDefault();const a=store.alerts.find(a=>a.id===button.dataset.detailInvestigate);if(!a)return;
      const linked=store.cases.filter(c=>c.alertIds.includes(a.id)&&canPrepare(c,a));
      if(linked.length===1){ctx.prepareInvestigation(linked[0],a);return;}
      openCaseChoice(a,'prepare');toast(linked.length?'请选择用于本次调查的 Case':'请先创建或关联 Case，再准备调查');
    }
  });
  document.addEventListener('submit',event=>{
    const form=event.target.closest('[data-detail-form]');if(!form)return;event.preventDefault();
    const a=store.alerts.find(x=>x.id===form.dataset.alert);if(!a)return;if(a.recordedImport){toast('此为执行导出的只读记录，未保存修改。');return;}const data=new FormData(form),m=material(a),now=new Date().toISOString();
    if(form.dataset.detailForm==='feedback'){a.disposition=data.get('verdict');a.feedbackReason=data.get('reason').trim();m.history.push({time:now,title:'人工判定更新',description:verdicts[a.disposition]+(a.feedbackReason?'：'+a.feedbackReason:'')});}
    if(form.dataset.detailForm==='redisposition'){const ids=data.getAll('ids'),allowed=similar(a);if(!ids.length){toast('请先选择历史告警');return;}for(const x of allowed.filter(x=>ids.includes(x.id))){x.disposition=a.disposition;material(x).history.push({time:now,title:'人工历史复核',description:`根据 ${a.id} 的反馈更新为${verdicts[a.disposition]}`});}}
    if(form.dataset.detailForm==='case'){
      const choice=caseChoices[a.id],preparing=choice.intent==='prepare';
      if(data.get('caseMode')==='new'&&store.cases.some(c=>c.alertIds.includes(a.id))){toast('当前告警已关联 Case，请选择已有 Case');return;}
      let c=data.get('caseMode')==='existing'?store.cases.find(x=>x.id===choice.selected):null;
      if(data.get('caseMode')==='existing'&&!c){toast('请先选择已有 Case');return;}
      if(c&&!canPrepare(c,a)){toast('请选择同一数据范围内的 Case');return;}
      if(!c){const title=String(data.get('title')||'').trim();if(!title){toast('请填写新 Case 名称');return;}
        c={id:'demo-'+Date.now(),title,severity:a.severity,status:'New',owner:a.owner,priority:null,description:a.description,alertIds:[],incidentId:a.incidentId,incidentIds:a.incidentId?[a.incidentId]:[],incidentCreated:true,critical:false,created:now,updated:now,tags:[],tasks:[],...ctx.caseScope?.(a)};store.cases.push(c);
      }
      const added=!c.alertIds.includes(a.id);
      if(added){m.history.push({time:now,title:'关联 Case',description:c.title});ctx.addMembers(c,[a.id]);}
      caseChoices[a.id]={mode:'existing',selected:c.id,query:'',intent:'link'};
      if(preparing){ctx.prepareInvestigation(c,a);return;}
      render();toast(added?'已关联 Case':'已在此 Case 中');return;
    }
    save();render();toast('已保存记录');
  });
  function renderDetail(a){
    const m=material(a),sourceDetection=detection(a),route=location.hash.split('/')[3],tab=route==='tracking'?'response':['overview','timeline','raw','response'].includes(route)?route:'overview',cases=store.cases.filter(c=>c.alertIds.includes(a.id)),inc=store.incidents.find(i=>i.id===a.incidentId);
    const history=[...m.history,...a.comments.map(c=>({time:c.time,title:'人工评论',description:c.text}))].sort((x,y)=>Date.parse(y.time)-Date.parse(x.time));
    const content=tab==='overview'?overview(a,m):tab==='response'?response(a,m):tab==='raw'?card('原始数据',`<div class="row between"><p>来源：${esc(m.raw.source||a.source||'—')} · 源记录：${esc(m.raw.source_ref||'—')}</p></div>${json(m.raw)}`):card('时间线',history.map(x=>`<div class="story-step"><div class="time">${new Date(x.time).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}).replaceAll('/','-')}</div><h4>${esc(x.title)}</h4><p>${esc(x.description)}</p></div>`).join(''));
    return `<section class="page alert-detail-page">${breadcrumbs([{label:'告警和事件'},{label:'告警',href:'#/alerts'},{label:a.title}])}<div class="title-line"><span class="title-icon">${I('shield',23)}</span><div><h1>${esc(a.title)}</h1><div class="row wrap">${severity(a.severity)}${state(a.status)}${badge(a.category,'blue')}${sourceDetection?badge('来源检测置信度 '+detectionScore(sourceDetection),'blue'):badge('置信度 '+(m.confidence.score??'—')+'/100','green')}<span class="muted">风险评分 ${m.risk??'—'}</span></div></div><div class="page-top-actions"><button class="button" type="button" data-detail-investigate="${a.id}" ${a.recordedImport?'disabled title="执行导出只读"':''}>准备调查</button>${a.recordedImport?'<span class="muted">执行导出 · 只读</span>':btn('管理告警','manage-alert',a.id,'primary','edit')}</div></div><div class="notice detail-relations"><span>${I('link',15)} 此告警属于事件 ${inc?`<a href="#/incidents/${inc.id}/attack">${esc(inc.title)}</a>`:esc(a.incidentId||'尚未关联事件')}</span><span>属于 Case：${cases.length?cases.map(c=>`<a href="#/cases/${c.id}/case-info">${esc(c.localCollection?c.title.replace(/（本地整理）$/, ''):c.title)}</a>`).join('、'):'尚未关联 Case'}</span></div>${tabsMarkup([['overview','概况'],['timeline','时间线'],['raw','原始数据'],['response','响应']],tab,'alerts',a.id)}<div class="alert-detail-content">${content}</div>${caseForm(a)}</section>`;
  }
  renderDetail.prepare=material;return renderDetail;
};
