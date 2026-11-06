/* Case-local preparation and human work; no backend execution is performed. */
'use strict';
window.createCaseWorkflow = function(ctx){
  const {store,ui,esc,btn,badge,date,severity,currentCase,currentRoute,getAlert,getAsset,render,save,toast,logActivity,navigate}=ctx;
  const M=window.investigationWorkspaceModel;
  const types={device:'主机',user:'账号',ip:'IP 地址',file:'文件',mailbox:'邮箱',app:'应用',cloud:'云资源',robot:'AI 代理'};
  const id=prefix=>prefix+'-'+Date.now()+'-'+Math.random().toString(36).slice(2,8);
  const url=(c,tab)=>`#/cases/${encodeURIComponent(c.id)}/${tab}`;
  const runUrl=(c,r,view='overview')=>`${url(c,'investigations')}?${new URLSearchParams({run:r,view})}`;
  const members=c=>c.alertIds.map(getAlert).filter(Boolean);
  const runs=c=>M.forCase(store,c);
  const key=(...parts)=>JSON.stringify(parts);
  const source=a=>{
    if(a.sourceEnvironment||a.sourceTenantId)return [a.sourceEnvironment||'',a.sourceTenantId||''];
    const group=window.alertFlowData?.incidents?.find(i=>i.sourceAlertIds?.includes(a.id));
    return group?[group.sourceEnvironment||'',group.sourceTenantId||'']:a.persistedRecord?['unknown-recorded',a.id]:['',''];
  };
  const eligible=(c,a)=>key(...source(a))===key(c.sourceEnvironment||'',c.sourceTenantId||'');
  const retain=c=>{c.retainedRunIds=[...new Set([...(c.retainedRunIds||[]),...runs(c).map(r=>r.id)])];};
  function changed(c,title,type='案件管理'){logActivity(title,type,c.title,c.incidentId,[c.id]);save();}
  function markScopeChange(c,added=[],removed=[]){
    const prior=c.baselineUpdate||{};
    c.baselineUpdate={status:'pending',alertIds:[...new Set([...(prior.alertIds||[]),...added])].filter(id=>c.alertIds.includes(id)),removedAlertIds:[...new Set([...(prior.removedAlertIds||[]),...removed])].filter(id=>!c.alertIds.includes(id)),requestedAt:new Date().toISOString()};
    c.updated=c.baselineUpdate.requestedAt;
  }
  function addMembers(c,ids,incidentIds=[],options={}){
    const selected=[...new Set(ids)].map(getAlert),events=[...new Set(incidentIds)];
    const validEvent=id=>{const rows=store.alerts.filter(a=>a.incidentId===id);return store.incidents.some(i=>i.id===id)&&rows.length&&rows.every(a=>eligible(c,a));};
    if(events.some(id=>!validEvent(id)))throw Error('请选择本案可关联的事件。');
    if((!selected.length&&!events.length)||selected.some(a=>!a||!eligible(c,a)))throw Error('请选择本案可关联的告警。');
    const linked=events.filter(id=>!c.incidentIds?.includes(id)&&c.incidentId!==id),added=selected.filter(a=>!c.alertIds.includes(a.id));
    if(!added.length&&!linked.length){if(options.allowExisting)return 0;throw Error('所选告警已在本案中。');}
    retain(c);c.alertIds=[...new Set([...c.alertIds,...added.map(a=>a.id)])];
    if(added.length)markScopeChange(c,added.map(a=>a.id));
    c.incidentIds=[...new Set([...(c.incidentIds||[]),...(c.incidentId?[c.incidentId]:[]),...events])];
    changed(c,`添加 ${added.length} 条成员告警${linked.length?'，关联 '+linked.length+' 个事件':''}`,'案件关联');return added.length;
  }
  function moveTargets(c,ids){const selected=[...new Set(ids)].map(getAlert);return selected.length&&selected.every(a=>a&&c.alertIds.includes(a.id))?store.cases.filter(t=>t.id!==c.id&&selected.every(a=>eligible(t,a))):[];}
  function moveMembers(c,target,ids){
    const selected=[...new Set(ids)];
    if(!target||!moveTargets(c,selected).some(t=>t.id===target.id))throw Error('请选择同一数据范围内的目标 Case。');
    const added=selected.filter(id=>!target.alertIds.includes(id));retain(c);retain(target);
    c.alertIds=c.alertIds.filter(id=>!selected.includes(id));target.alertIds=[...new Set([...target.alertIds,...selected])];
    markScopeChange(c,[],selected);if(added.length)markScopeChange(target,added);
    logActivity(`移动 ${selected.length} 条告警至 Case ${target.id}`,'案件关联',M.caseRecord(target).title,c.incidentId,[c.id,target.id]);save();return added.length;
  }
  function saveAssistantResult(c,message,messages,fields){
    if(!message||message.role!=='assistant'||message.status!=='completed'||!message.result?.outcome?.conclusion)throw Error('请先取得可保存的分析结论。');
    const recordId='ai-record:'+c.id+':'+message.id,existing=(store.caseDemoRuns||[]).find(r=>r.id===recordId);if(existing)return existing;
    const result=message.result,title=String(fields.title||'').trim(),conclusion=String(fields.conclusion||'').trim();
    if(!title||!conclusion)throw Error('请填写记录标题和结论。');
    const alertIds=[...new Set(result.alertIds||[])];if(alertIds.some(id=>!getAlert(id)||!eligible(c,getAlert(id))))throw Error('返回材料不属于本案数据范围。');
    const allowedRuns=new Set(runs(c).map(r=>r.id)),allowedTasks=new Set(M.humanTasks(c).map(t=>t.id));
    if((result.runIds||[]).some(id=>!allowedRuns.has(id))||(result.taskIds||[]).some(id=>!allowedTasks.has(id)))throw Error('引用资料不属于本案。');
    const question=messages.find(m=>m.id===message.questionId),now=new Date().toISOString();
    const r={id:recordId,caseId:c.id,sourceCaseId:c.id,sourceEnvironment:c.sourceEnvironment,sourceTenantId:c.sourceTenantId,fixture:!!c.fixture,recorded:false,fixtureSet:c.fixtureSet,investigationKind:'ai_followup',trigger:'user_question',title:title.slice(0,180),status:'completed',completion:'completed',verdict:null,started:question?.time||message.time,ended:message.time,savedAt:now,savedBy:ctx.currentUser||'Alex Wilber',alertIds,input:{alerts:structuredClone(message.inputSnapshot||[])},referenceSnapshot:structuredClone(message.referenceSnapshot||null),outcome:{...structuredClone(result.outcome),conclusion:conclusion.slice(0,4000)},findings:structuredClone(result.outcome.findings||[]),references:{runIds:result.runIds||[],taskIds:result.taskIds||[],alertIds},conversation:structuredClone([question,message].filter(Boolean)).map(m=>({role:m.role||'user',text:m.text,time:m.time,context:m.context,result:m.result})),steps:(result.process||[]).map((x,i)=>({seq:i+1,name:x.name,summary:x.detail,kind:'阶段记录',time:message.time})),tools:[],artifacts:[],actions:[],executed:[],graphs:{},graphEligible:false,calls:null,tokens:null,report:conclusion+'\n\n对案件的影响：'+(result.outcome.impact||'未记录'),stop:null};
    (store.caseDemoRuns||=[]).push(r);changed(c,'保存 AI 调查结论：'+r.title,'调查结果');return r;
  }
  function materialOptions(c,includeTasks=true){
    const ids=new Set(c.alertIds),items=store.evidence.filter(e=>(e.alertIds||[e.alertId]).some(id=>ids.has(id))&&(!e.caseId||e.caseId===c.id)).map(e=>({id:key('evidence',e.id),label:e.name,kind:'告警证据',href:url(c,'evidence')}));
    for(const r of runs(c)){
      items.push({id:key('run',r.id),label:r.title,kind:'已有调查',href:runUrl(c,r.id)});
      for(const a of r.artifacts||[])items.push({id:key('artifact',r.id,a.id),label:`${r.title} · ${a.kind}`,kind:'调查材料',href:runUrl(c,r.id,'tools')+'&artifact='+encodeURIComponent(a.id)});
    }
    if(includeTasks)for(const t of c.tasks||[])if(t.status==='Completed'&&t.result)items.push({id:key('task',t.id),label:t.title,kind:'人工结果',href:url(c,'tasks'),result:t.result});
    return items;
  }
  function validMaterials(c,ids,includeTasks=true){const options=materialOptions(c,includeTasks),chosen=[...new Set(ids||[])];if(chosen.some(k=>!options.some(o=>o.id===k)))throw Error('部分材料已不可用，请重新选择。');return chosen.map(k=>({...options.find(o=>o.id===k)}));}
  const activeStatuses=M.activeStatuses;
  function activeRun(c){return runs(c).find(r=>activeStatuses.has(r.status)&&(r.caseId===c.id||r.sourceCaseId===(c.sourceCaseId||c.id)))||null;}
  function validTargets(c,ids){const allowed=new Set(members(c).flatMap(a=>a.entityIds||[])),scoped=store.alerts.filter(a=>eligible(c,a));for(const a of scoped)for(const id of a.entityIds||[])allowed.add(id);const targets=[...new Set(ids||[])];if(targets.some(id=>!allowed.has(id)||!getAsset(id)))throw Error('部分补查对象已不在本案可用范围。');return targets;}
  function saveDraft(c,data){
    const objective=String(data.objective||'').trim(),alertIds=[...new Set(data.alertIds||[])],entityIds=validTargets(c,data.entityIds);
    if(!objective||(!alertIds.length&&!entityIds.length))throw Error('请填写调查目标并至少选择一条成员告警或一个补查对象。');
    if(alertIds.some(id=>!getAlert(id)||!eligible(c,getAlert(id))||(!c.alertIds.includes(id)&&!data.confirmAdd)))throw Error('调查范围已变化，请重新选择当前成员。');
    if(data.sourceRunId&&!runs(c).some(r=>r.id===data.sourceRunId))throw Error('来源调查不属于本案。');
    const start=data.timeStart||null,end=data.timeEnd||null;if((start||end)&&(!Number.isFinite(Date.parse(start))||!Number.isFinite(Date.parse(end))||Date.parse(start)>=Date.parse(end)))throw Error('请填写有效的起止时间，结束时间须晚于开始时间。');
    const materials=validMaterials(c,data.materialIds),existing=data.id?(c.investigationDrafts||[]).find(d=>d.id===data.id):null;
    if(data.id&&!existing)throw Error('未找到该调查方案。');if(existing&&existing.status!=='draft')throw Error('已取消或已启动的草案不能修改。');
    const draft={id:existing?.id||id('plan'),objective,alertIds,entityIds,materials,sourceRunId:data.sourceRunId||null,graphReference:structuredClone(data.graphReference||existing?.graphReference||null),timeRange:start?{start:new Date(start).toISOString(),end:new Date(end).toISOString()}:null,status:'draft',createdAt:existing?.createdAt||new Date().toISOString(),updatedAt:new Date().toISOString()};
    const additions=alertIds.filter(id=>!c.alertIds.includes(id));retain(c);c.alertIds=[...new Set([...c.alertIds,...additions])];c.investigationDrafts||=[];if(existing)Object.assign(existing,draft);else c.investigationDrafts.push(draft);
    changed(c,(existing?'更新':'保存')+'调查草案（未启动）'+(additions.length?`，加入 ${additions.length} 条成员告警`:''),'调查准备');return draft;
  }
  function cancelDraft(c,draftId){const d=(c.investigationDrafts||[]).find(d=>d.id===draftId);if(!d||d.status!=='draft')throw Error('只有待启动草案可以取消。');d.status='cancelled';d.cancelledAt=d.updatedAt=new Date().toISOString();changed(c,'取消调查草案：'+d.objective,'调查准备');}
  function startSimulation(c,draftId){
    if(!c.simulation)throw Error('调查执行服务尚未接入。');if(activeRun(c))throw Error('本案已有执行中或待确认的调查，请先查看该轮进度。');
    const d=(c.investigationDrafts||[]).find(d=>d.id===draftId);if(!d||d.status!=='draft')throw Error('该草案已取消或已启动。');
    if(d.alertIds.some(id=>!c.alertIds.includes(id)||!getAlert(id)))throw Error('草案告警已移出本案，请先重新保存范围。');validTargets(c,d.entityIds);
    const rows=d.alertIds.map(getAlert),targetIds=[...new Set([...rows.flatMap(a=>a.entityIds||[]),...(d.entityIds||[])])],now=new Date().toISOString();
    const snapshot={alertIds:d.alertIds.slice(),entityIds:(d.entityIds||[]).slice(),materials:structuredClone(d.materials),graphReference:structuredClone(d.graphReference||null),objective:d.objective,timeRange:structuredClone(d.timeRange||null),alerts:structuredClone(rows),targets:structuredClone(targetIds.map(getAsset).filter(Boolean))};
    const r={id:id('SIM'),caseId:c.id,sourceCaseId:c.id,sourceEnvironment:c.sourceEnvironment,sourceTenantId:c.sourceTenantId,fixture:true,fixtureSet:'case-exploration-20261102',recorded:false,simulation:true,title:d.objective,alertIds:d.alertIds.slice(),input:{alerts:structuredClone(rows)},snapshot,status:'queued',completion:null,verdict:null,phase:0,started:now,ended:null,findings:[],steps:[{seq:1,name:'等待开始（模拟）',summary:'演示输入已冻结，尚未查询或分析。',kind:'阶段记录',time:now}],tools:[],graphs:{},artifacts:[],actions:[],executed:[],report:null,stop:null};
    store.caseDemoRuns||=[];store.caseDemoRuns.push(r);d.status='started';d.runId=r.id;d.updatedAt=now;changed(c,'模拟启动调查：'+d.objective,'调查演示');return r;
  }
  function advanceSimulation(c,runId){
    const r=(store.caseDemoRuns||[]).find(r=>r.id===runId&&r.caseId===c.id&&r.simulation);if(!c.simulation||!r||!activeStatuses.has(r.status))throw Error('当前调查不能模拟推进。');
    const phase=(r.phase||0)+1,now=new Date().toISOString();r.phase=phase;r.status=phase>=3?'completed':'running';
    const names=['等待开始','查询选定范围','核对关联材料','演示结束'];r.steps.push({seq:r.steps.length+1,name:names[Math.min(phase,3)]+'（模拟）',summary:phase>=3?'演示流程结束，未调用模型或执行响应。':'模拟阶段变化，真实调查服务未连接。',kind:'阶段记录',time:now});
    if(phase>=3){r.ended=now;r.completion='partial';r.stop='本轮为本地交互演示，未执行真实查询或模型分析。';r.findings=['演示流程已结束；待接入调查服务后形成实际结论。'];if(r.snapshot){const snap=r.snapshot;r.graphs={attack_path:{status:'success',source:'演示冻结范围的告警对象记录',queried_at:r.started,data:{nodes:[...snap.alerts.map(a=>({id:a.id,label:'Alert',properties:{source_alert_id:a.id,title:a.title,event_time:a.event_time||a.first}})),...snap.targets.map(a=>({id:a.id,kind:a.type,name:a.name}))],edges:snap.alerts.flatMap(a=>(a.entityIds||[]).map(id=>({source:a.id,target:id,type:'INVOLVES'})))}}};}}
    changed(c,'模拟调查阶段：'+names[Math.min(phase,3)],'调查演示');return r;
  }
  function activeBanner(){const c=currentCase(),r=activeRun(c);return r?`<div class="cw-active-banner" role="status"><span class="cw-active-dot"></span><div><strong>调查${({queued:'排队中',pending:'等待启动',starting:'启动中',waiting:'等待继续',unknown:'状态待确认'})[r.status]||'执行中'} · ${esc(r.title)}</strong><small>本轮按启动时的告警范围执行。</small></div><a class="button small" href="${runUrl(c,r.id)}">查看进度</a></div>`:'';}
  function runControls(){return ''; }
  function openGraphAdoption(ids){const c=currentCase(),selected=[...new Set(ids)].filter(id=>!c.alertIds.includes(id)&&getAlert(id)&&eligible(c,getAlert(id)));if(!selected.length)throw Error('请选择尚未加入本案的告警。');open('cw-add',{mode:'alerts',selected,selectedEvents:[],query:'',returnTo:url(c,'attack')});}
  function prepareFromGraph(data){open('cw-investigate',{sourceRunId:data.sourceRunId,fromGraph:true,draft:{...data,objective:'',materials:[]}});}
  function prepareFromAlert(caseId,alertId){
    const c=store.cases.find(c=>c.id===caseId),a=getAlert(alertId);
    if(!c||!a||!c.alertIds.includes(alertId)||!eligible(c,a)){toast('当前告警不在所选 Case 的可用范围中');return false;}
    ui.pendingAlertPreparation={caseId,alertId};navigate(url(c,'overview'));return true;
  }
  function consumeAlertPreparation(){
    const pending=ui.pendingAlertPreparation;if(!pending)return;
    delete ui.pendingAlertPreparation;
    const route=currentRoute(),c=store.cases.find(c=>c.id===pending.caseId),a=getAlert(pending.alertId);
    if(route.page==='cases'&&route.id===pending.caseId&&c&&a&&c.alertIds.includes(a.id)&&eligible(c,a))ctx.assistant?.().open({alertIds:[a.id]});
  }
  function saveTask(c,data){
    const title=String(data.title||'').trim(),result=String(data.result||'').trim(),status=data.status||'New';
    if(!title)throw Error('请填写跟进事项。');if(!['New','In progress','Completed','Cancelled'].includes(status))throw Error('请选择有效任务状态。');
    if(status==='Completed'&&!result)throw Error('完成任务前，请填写处理结果。');
    const existing=data.id?M.humanTasks(c).find(t=>t.id===data.id):null;if(data.id&&!existing)throw Error('未找到该任务。');
    if(data.sourceRunId&&!runs(c).some(r=>r.id===data.sourceRunId))throw Error('来源调查不属于本案。');
    const materials=validMaterials(c,data.materialIds,false),owner=String(data.owner||'未分配');
    if(!store.people.includes(owner)&&owner!==existing?.owner)throw Error('请选择有效负责人。');
    const task={id:existing?.id||id('task'),sourceDraftId:existing?.sourceDraftId||null,createdAt:existing?.createdAt||new Date().toISOString(),updatedAt:new Date().toISOString(),title,description:String(data.description||'').trim(),owner,due:data.due||'',status,result,materials,sourceRunId:data.sourceRunId||null,referenceContext:data.referenceContext?ctx.assistant().normalize(c,data.referenceContext):existing?.referenceContext||null,completedAt:status==='Completed'?(existing?.completedAt||new Date().toISOString()):null};
    retain(c);c.tasks||=[];const stored=c.tasks.find(t=>t.id===task.id);if(stored)Object.assign(stored,task);else c.tasks.push(task);
    changed(c,(existing?'更新人工任务：':'添加人工任务：')+title,'任务');return task;
  }
  function decide(c,runId,index,decision,reason){
    const run=runs(c).find(r=>r.id===runId),action=run?.actions?.[index];
    if(!action||typeof action!=='object'||!action.requires_approval||!action.target)throw Error('该动作缺少可审批的目标或要求。');
    if(!['approved','rejected'].includes(decision)||!String(reason||'').trim())throw Error('请选择决定并填写理由。');
    const review={runId,index,proposal:JSON.stringify(action),decision,reason:String(reason).trim(),reviewer:ctx.currentUser||'Alex Wilber',time:new Date().toISOString()};
    retain(c);c.responseReviews||={};c.responseReviews[key(runId,index)]=review;
    changed(c,`${decision==='approved'?'批准（待执行）':'拒绝'}响应建议：${action.description||action.action_type}`,'响应审阅');return review;
  }
  function reviewFor(c,r,i){const x=c.responseReviews?.[key(r.id,i)];return x?.proposal===JSON.stringify(r.actions[i])?x:null;}
  function responseControls(r,index){
    if(currentRoute().page!=='cases'||r.recordedImport)return '';
    const c=currentCase();
    return r.actions.map((a,i)=>{
      if((index!==undefined&&index!==i)||!a||typeof a!=='object'||!a.requires_approval)return '';
      const review=reviewFor(c,r,i);return `<div class="cw-action-review"><div>${review?`${badge(review.decision==='approved'?'已批准 · 待执行':'已拒绝',review.decision==='approved'?'blue':'')}<p>${esc(review.reason)}</p><small>${esc(review.reviewer)} · ${date(review.time,true)}</small>`:badge(a.target?'待审阅':'缺少目标 · 暂不可审阅','amber')}</div>${a.target?btn(review?'查看 / 调整决定':'审阅动作','cw-review',key(r.id,i),'small'):''}</div>`;
    }).join('');
  }
  function toolbar(){if(currentCase().recordedImport)return '<span class="iv-note">实际执行导出 · 只读回查</span>';return `${btn('添加告警 / 事件','cw-add','','','plus')}${btn('询问 AI','ca-open','','primary','sparkles')}`;}
  function currentWork(){
    const c=currentCase(),r=activeRun(c);if(c.recordedImport){const pending=runs(c).filter(x=>x.status==='pending_update');return `${r?`<section class="cw-current-work"><strong>${esc(r.title)} · ${esc(r.status==='unknown'?'执行状态待确认':'执行中')}</strong><a href="${runUrl(c,r.id)}">查看记录</a></section>`:''}${pending.map(x=>`<section class="cw-current-work"><strong>${esc(x.title)} · 待启动，尚未执行</strong><a href="${runUrl(c,x.id)}">查看冻结记录</a></section>`).join('')}`;}if(!r)return '';
    const label=({pending:'等待启动',queued:'排队中',starting:'启动中',running:'执行中',waiting:'等待继续',unknown:'状态待确认'})[r.status]||'状态待确认';
    return `<section class="cw-current-work" aria-label="AI 调查进度"><div><div class="cw-current-heading"><span>${esc(M.investigationLabel(r))}进度</span>${badge(label,'blue')}</div><strong>${esc(r.title)}</strong><p class="muted">${r.alertIds.length} 条输入告警 · ${date(r.started,true)}</p></div><a class="button small" href="${runUrl(c,r.id)}">查看进度</a></section>`;
  }
  function plans(){
    const c=currentCase(),rows=c.investigationDrafts||[],active=activeRun(c),waiting=rows.filter(d=>d.status==='draft'),past=rows.filter(d=>d.status!=='draft');
    const row=d=>`<div class="cw-plan-row"><div><strong>${esc(d.objective)}</strong><p class="muted">${(d.alertIds||[]).length} 条告警${d.entityIds?.length?' · '+d.entityIds.length+' 个补查对象':''}${d.status==='draft'?'':' · '+({cancelled:'已取消',started:'已启动'}[d.status]||esc(d.status))}</p></div><div class="cw-plan-actions">${btn(d.status==='draft'?'查看 / 调整':'查看安排','cw-plan',d.id,'small')}${d.status==='draft'?btn('取消安排','cw-plan-cancel',d.id,'small')+(c.simulation?`<button class="button primary small" data-action="cw-simulate-start" data-id="${esc(d.id)}" ${active?'disabled title="待当前调查结束后启动"':''}>启动调查</button>`:''):d.runId?`<a class="button small" href="${runUrl(c,d.runId)}">查看调查</a>`:''}</div></div>`;
    return `<details class="iv-card cw-plans"><summary><span>待启动调查</span><span class="cw-plan-count">${waiting.length}</span></summary><p class="iv-note">已保存调查目标和范围，尚未执行。可调整后启动，或取消安排。</p>${waiting.map(row).join('')||'<p class="muted">暂无待启动的调查。</p>'}${active&&waiting.length?'<p class="iv-note">待当前调查结束后，可启动下一轮。</p>':''}<div class="cw-plan-create">${btn('新建调查安排','cw-investigate','','small')}</div>${past.length?`<details class="cw-past-plans"><summary>已启动 / 已取消 · ${past.length}</summary>${past.map(row).join('')}</details>`:''}</details>`;
  }
  function taskSummary(){const c=currentCase(),rows=M.humanTasks(c),pending=rows.filter(t=>['New','In progress'].includes(t.status));return `<article class="iv-card cw-task-summary"><div class="cw-plan-header"><h3>人工任务 <span class="muted">${pending.length}</span></h3>${c.recordedImport?'':btn('新建任务','cw-task','','small')}</div>${pending.slice(0,3).map(t=>`<div class="cw-summary-task"><a href="${url(c,'tasks')}">${esc(t.title)}</a><small>${esc(t.owner||'未分配')} · ${t.status==='New'?'未开始':'进行中'}</small></div>`).join('')||'<p class="muted">暂无待跟进的人工任务。</p>'}<a class="iv-link" href="${url(c,'tasks')}">查看全部人工任务 →</a></article>`;}
  const refLinks=items=>(items||[]).map(m=>`<a href="${esc(m.href)}">${esc(m.kind)} · ${esc(m.label)}</a>`).join('');
  function materialState(){
    const caseId=currentCase().id;
    if(ui.cwMaterials?.caseId!==caseId)ui.cwMaterials={caseId,view:null,objectId:null,query:'',type:''};
    return ui.cwMaterials;
  }
  function materialContext(){
    const c=currentCase(),alerts=[...new Map(members(c).map(a=>[a.id,a])).values()],ids=new Set(alerts.map(a=>a.id));
    const evidence=store.evidence.filter(e=>(e.alertIds||[e.alertId]).some(id=>ids.has(id))&&(!e.caseId||e.caseId===c.id));
    const objects=[...new Set(alerts.flatMap(a=>a.entityIds||[]))].map(getAsset).filter(Boolean).map(object=>({
      object,alerts:alerts.filter(a=>a.entityIds?.includes(object.id)),evidence:evidence.filter(e=>(e.entityIds||[e.entityId]).includes(object.id))
    })).sort((a,b)=>b.alerts.length-a.alerts.length||b.evidence.length-a.evidence.length);
    return {c,alerts,evidence,objects,orphan:evidence.filter(e=>!objects.some(x=>(e.entityIds||[e.entityId]).includes(x.object.id))),runs:runs(c)};
  }
  function materials(){
    const d=materialContext(),s=materialState(),q=s.query.trim().toLowerCase();
    const matched=d.objects.filter(x=>(!s.type||x.object.type===s.type)&&(!q||[x.object.name,x.object.id,...x.evidence.flatMap(e=>[e.name,e.type,e.threat])].join(' ').toLowerCase().includes(q)));
    const orphan=d.orphan.filter(e=>!q||[e.name,e.type,e.threat].join(' ').toLowerCase().includes(q));
    const showOrphan=!s.type&&orphan.length>0;
    const selected=matched.find(x=>x.object.id===s.objectId)||matched[0];
    const orphanSelected=showOrphan&&(s.objectId==='__unlinked__'||!selected);
    const view=s.view||(!d.objects.length&&!d.orphan.length&&d.runs.length?'runs':'objects');
    const glyph=(type,size=18)=>ctx.I?.(type,size)||'';
    const alertHref=a=>`#/alerts/${encodeURIComponent(a.id)}/overview`;
    const sourceTime=a=>date(a.event_time||(a.persistedRecord?null:a.first),true);
    const evidenceCard=e=>{
      const a=getAlert(e.alertId),verdict=({Malicious:'恶意',Suspicious:'可疑',Clean:'未发现威胁'})[e.verdict]||e.verdict;
      return `<article class="cw-evidence-card"><div class="cw-evidence-title"><span class="cw-material-icon">${glyph('file')}</span><button class="link-button" data-action="evidence" data-id="${esc(e.id)}">${esc(e.name)}</button>${verdict?badge(verdict,e.verdict==='Malicious'?'red':e.verdict==='Suspicious'?'amber':''):badge('未判定')}</div><p class="cw-evidence-description">${[e.type,e.origin,e.threat].filter(Boolean).map(esc).join(' · ')}</p><div class="cw-evidence-source"><span>来源告警</span>${a?`<a href="${alertHref(a)}">${esc(a.title)}</a><small>${sourceTime(a)}</small>`:'<span>未找到来源告警</span>'}</div></article>`;
    };
    const alertRow=a=>`<div class="cw-source-alert"><span class="cw-source-shield">${glyph('shield',15)}</span><div><a href="${alertHref(a)}">${esc(a.title)}</a><small>${sourceTime(a)}${a.source?' · '+esc(a.source):''}</small></div>${severity(a.severity)}</div>`;
    const relatedRuns=selected?d.runs.filter(r=>r.alertIds.some(id=>selected.alerts.some(a=>a.id===id))):[];
    const runLink=r=>`<a class="cw-related-run" href="${runUrl(d.c,r.id,'tools')}"><span>${glyph('search',16)}<strong>${esc(r.title)}</strong></span><small>${r.alertIds.length} 条本轮输入 · ${r.tools.length} 条查询</small><span class="cw-link-label">查看材料 →</span></a>`;
    let detail='';
    if(orphanSelected){
      detail=`<div class="cw-object-detail-heading"><span class="cw-material-icon large">${glyph('file',22)}</span><div><h3>未关联对象的证据</h3><p>${orphan.length} 项记录 · 可沿来源告警核查</p></div></div><section class="cw-detail-section"><div class="cw-section-title"><h4>证据条目</h4><span>${orphan.length} 项</span></div>${orphan.map(evidenceCard).join('')}</section>`;
    }else if(selected){
      const o=selected.object,related=selected.alerts.slice().sort((a,b)=>(Date.parse(b.event_time||b.first)||0)-(Date.parse(a.event_time||a.first)||0));
      detail=`<div class="cw-object-detail-heading"><span class="cw-material-icon large">${glyph(o.type,22)}</span><div><span class="cw-object-kind">${esc(types[o.type]||o.type)}</span><h3>${esc(o.name)}</h3><p>${related.length} 条成员告警涉及此对象</p></div></div><div class="cw-object-facts"><span>风险等级 ${o.risk?severity(o.risk):'未记录'}</span>${o.domain||o.provider||o.department?`<span>${esc(o.domain||o.provider||o.department)}</span>`:''}${o.inventory===false?`<span>${o.recordedImport?esc(({not_checked:'源对象尚未核对库存',matched:'源对象已匹配库存',unmatched:'源对象未匹配库存'})[o.sourceRecord?.asset_match_state]||o.sourceRecord?.asset_match_state||'库存匹配未记录'):'未关联库存'}</span>`:''}</div><section class="cw-detail-section"><div class="cw-section-title"><h4>证据条目</h4><span>${selected.evidence.length} 项</span></div>${selected.evidence.map(evidenceCard).join('')||`<div class="cw-material-empty"><strong>尚无独立证据条目</strong><p>可先查看下方来源告警${relatedRuns.length?'，或查看相关调查的查询与保存材料':'，核对已记录的对象信息'}。</p></div>`}</section><section class="cw-detail-section"><div class="cw-section-title"><h4>来源告警</h4><span>${related.length} 条</span></div>${related.slice(0,3).map(alertRow).join('')}${related.length>3?`<details class="cw-more-alerts"><summary>展开其余 ${related.length-3} 条告警</summary>${related.slice(3).map(alertRow).join('')}</details>`:''}</section>${relatedRuns.length?`<section class="cw-detail-section"><div class="cw-section-title"><h4>相关调查</h4><span title="包含该对象来源告警的调查，不代表模型已经采用对象或证据">${relatedRuns.length} 次</span></div>${relatedRuns.map(runLink).join('')}</section>`:''}`;
    }else detail=`<div class="cw-material-empty large"><span class="cw-material-icon large">${glyph('search',24)}</span><h3>${q||s.type?'没有匹配的对象':'暂无对象或独立证据'}</h3><p>${q||s.type?'调整名称或类型，查看本案其他材料。':'成员告警尚未关联对象，可在调查材料中查看已保存记录。'}</p>${q||s.type?btn('清除筛选','cw-material-reset','','small'):d.runs.length?btn('查看调查材料','cw-material-view','runs','small'):''}</div>`;
    const objectPanel=`<section id="cw-objects-panel" class="cw-material-panel" ${view!=='objects'?'hidden':''}><div class="cw-material-browser"><aside class="cw-object-browser" aria-label="案件对象"><div class="cw-material-toolbar"><label class="cw-material-search">${glyph('search',16)}<input id="cw-material-search" type="search" aria-label="搜索对象或证据" placeholder="搜索对象名称或证据" value="${esc(s.query)}" data-cw-material-search></label><select aria-label="对象类型" data-cw-material-type><option value="">全部类型</option>${[...new Set(d.objects.map(x=>x.object.type))].map(type=>`<option value="${esc(type)}" ${s.type===type?'selected':''}>${esc(types[type]||type)}</option>`).join('')}</select>${q||s.type?btn('清除筛选','cw-material-reset','','quiet small'):''}</div><div class="cw-object-list-label"><strong>案件对象 <span>${matched.length}</span></strong><small>按关联告警数排序</small></div><div class="cw-object-options">${matched.map(x=>`<button class="cw-object-option ${!orphanSelected&&selected?.object.id===x.object.id?'selected':''}" data-action="cw-material-object" data-id="${esc(x.object.id)}" aria-pressed="${!orphanSelected&&selected?.object.id===x.object.id}"><span class="cw-material-icon">${glyph(x.object.type)}</span><span><small>${esc(types[x.object.type]||x.object.type)}</small><strong>${esc(x.object.name)}</strong><span>${x.alerts.length} 条告警 · ${x.evidence.length} 项证据</span></span></button>`).join('')||'<p class="cw-list-empty">没有匹配的对象</p>'}${showOrphan?`<button class="cw-object-option cw-orphan-option ${orphanSelected?'selected':''}" data-action="cw-material-object" data-id="__unlinked__" aria-pressed="${!!orphanSelected}"><span class="cw-material-icon">${glyph('file')}</span><span><strong>未关联对象的证据</strong><span>${orphan.length} 项记录</span></span></button>`:''}</div></aside><article class="cw-object-detail" aria-label="当前对象详情">${detail}</article></div></section>`;
    const completion=r=>({completed:'完整交付',partial:'部分交付',not_escalated:'仅分诊'})[r.completion]||'完整性未记录';
    const materialPanel=`<section id="cw-runs-panel" class="cw-material-panel" ${view!=='runs'?'hidden':''}><div class="cw-material-intro"><h3>按调查查看材料</h3><p>查询、报告和原始记录保留各轮的输入范围。原件不自动视为已确认的恶意证据。</p></div><div class="cw-material-runs">${d.runs.map(r=>`<article class="card cw-material-run"><div class="cw-run-heading"><div><h3>${esc(r.title)}</h3><p>${r.alertIds.length} 条本轮输入 · ${date(r.started,true)}</p></div>${badge(completion(r),r.completion==='partial'?'amber':'')}</div><div class="cw-run-material-links"><a href="${runUrl(d.c,r.id,'tools')}">${glyph('search',17)}<span>查询与材料 <b>${r.tools.length} 条查询</b></span><span>→</span></a><a href="${runUrl(d.c,r.id,'report')}">${glyph('file',17)}<span>报告与响应 <b>${r.report?'已有报告':'查看已有记录'}</b></span><span>→</span></a></div><div class="cw-section-title"><h4>保存材料</h4><span>${r.artifacts.length} 份</span></div>${r.artifacts.length?ctx.catalog?.(r)||'':'<p class="muted">未保存独立材料目录。</p>'}</article>`).join('')||'<div class="cw-material-empty large"><h3>暂无关联调查材料</h3><p>本案对象与来源告警仍可在“按对象查看”中核对。</p></div>'}</div></section>`;
    return `<div class="iv-root cw-material-workspace"><div class="iv-heading"><div><h2>对象与证据</h2><p>选择对象，查看相关证据和来源告警。</p></div><div class="cw-material-overview"><span><b>${d.objects.length}</b> 个对象</span><span><b>${d.c.recordedImport?(d.c.pageData?.evidence?.evidence_count==null?'未记录':`${d.c.pageData.evidence.evidence_count}${d.c.pageData.evidence.state==='partial'?'（部分）':''}`):d.evidence.length}</b> ${d.c.recordedImport?'项独立证据条目':'项告警证据'}</span><span><b>${d.runs.reduce((n,r)=>n+r.artifacts.length,0)}</b> 份调查材料</span></div></div><div class="cw-material-views" role="group" aria-label="材料查看方式"><button data-action="cw-material-view" data-id="objects" aria-pressed="${view==='objects'}" aria-controls="cw-objects-panel">按对象查看</button><button data-action="cw-material-view" data-id="runs" aria-pressed="${view==='runs'}" aria-controls="cw-runs-panel">调查材料 <span>${d.runs.length} 次调查</span></button></div>${objectPanel}${materialPanel}</div>`;
  }
  function recordedTask(t){
    const facts=r=>`<p class="iv-note">版本 ${esc(r.revisionNumber??'未记录')} · 实际完成：${esc(r.completedBy||'未记录')} / ${date(r.completedAt,true)}；本次修改：${esc(r.changedBy||'未记录')} / ${date(r.updatedAt,true)}</p><details class="iv-raw"><summary>确认范围与版本原件</summary><pre class="iv-json">${esc(JSON.stringify({scope:r.resultScope,revision:r.sourceRecord?.revision},null,2))}</pre></details>`;
    return `${facts(t)}<details class="iv-raw"><summary>历史版本 · ${(t.revisionHistory||[]).length}</summary>${(t.revisionHistory||[]).map(r=>`<article class="iv-action-item"><h4>${esc(r.title)}</h4><p>${esc(r.result||'未填写结果')}</p>${facts(r)}</article>`).join('')}</details>`;
  }
  function tasks(){
    const c=currentCase(),rows=M.humanTasks(c);
    return `<div class="iv-root"><div class="iv-heading"><div><h2>人工任务</h2><p>由人确认业务背景或补充 AI 无法取得的信息。</p></div>${c.recordedImport?'<span class="iv-note">只读历史记录</span>':btn('添加任务','cw-task','','primary','plus')}</div><div class="cw-task-list">${rows.map(t=>`<article class="iv-card"><div class="cw-task-header"><div><h3>${esc(t.title)}</h3><small>${esc(t.owner)} · ${t.due?'截止 '+esc(t.due.replace('T',' ')):'未设置期限'}</small></div><div class="cw-task-actions">${badge(({New:'未开始','In progress':'进行中',Completed:'已完成',Cancelled:'已取消'})[t.status]||t.status)}${t.recordedImport?'':btn('编辑','cw-task',t.id,'small','edit')}</div></div>${t.description?`<p>${esc(t.description)}</p>`:''}${t.result?`<div class="cw-task-result"><b>处理结果</b><p>${esc(t.result)}</p></div>`:t.status==='Completed'?'<p class="muted">历史任务未记录处理结果。</p>':''}${t.recordedImport?recordedTask(t):''}</article>`).join('')||'<div class="iv-empty">暂无人工任务事项。</div>'}</div></div>`;
  }
  function field(label,name,value='',textarea=false){return `<label class="cw-field">${label}${textarea?`<textarea name="${name}" rows="3" maxlength="4000">${esc(value)}</textarea>`:`<input name="${name}" value="${esc(value)}" maxlength="180">`}</label>`;}
  function materialPicker(c,selected=[],includeTasks=true,sourceRunId=''){
    const sourceKey=key('run',sourceRunId),options=materialOptions(c,includeTasks).filter(o=>includeTasks||(!o.id.startsWith('["run",')||selected.includes(o.id))&&o.id!==sourceKey);
    return `<details class="cw-picker"><summary>${includeTasks?'选择参考材料（可选）':'补充参考资料（可选）'}</summary><p class="iv-note">${includeTasks?'选择本次调查要参考的已有结果、证据或人工记录。':'来源调查用于回查任务出处，无需重复选择。这里可附上具体证据或查询材料，供负责人阅读；不触发 AI 调查。'}</p>${!includeTasks&&selected.includes(sourceKey)?`<input type="hidden" name="material" value="${esc(sourceKey)}">`:''}<div class="cw-checklist">${options.map(o=>`<div class="cw-reference-option"><label><input type="checkbox" name="material" value="${esc(o.id)}" ${selected.includes(o.id)?'checked':''}><span>${esc(o.label)}<small>${esc(o.kind)}</small></span></label><a href="${esc(o.href)}" target="_blank" rel="noopener" aria-label="查看资料：${esc(o.label)}">查看</a></div>`).join('')||'<p>暂无补充资料，可直接填写确认结果。</p>'}</div></details>`;
  }
  function addOptions(m){
    const c=currentCase(),q=(m.query||'').trim().toLowerCase(),eligibleAlerts=store.alerts.filter(a=>eligible(c,a)),selected=new Set(m.selected||[]);
    const row=a=>`<label class="cw-alert-choice"><input type="checkbox" data-cw-alert="${esc(a.id)}" ${selected.has(a.id)?'checked':''} ${c.alertIds.includes(a.id)?'disabled':''}><span><b>${esc(a.title)}</b><small>${esc(a.id)} · ${date(a.event_time||a.first,true)} · ${esc(a.source||'')}</small>${c.alertIds.includes(a.id)?badge('已在本案'):store.cases.some(other=>other.id!==c.id&&other.alertIds.includes(a.id))?'<small>已关联其他 Case；添加不会移动原成员。</small>':''}</span>${severity(a.severity)}</label>`;
    if(m.mode==='events')return store.incidents.map(i=>({i,rows:eligibleAlerts.filter(a=>a.incidentId===i.id)})).filter(({i,rows})=>rows.length&&(!q||(i.title+' '+i.id+' '+rows.map(a=>a.title).join(' ')).toLowerCase().includes(q))).map(({i,rows})=>{const fresh=rows.filter(a=>!c.alertIds.includes(a.id));return `<details class="cw-event-choice"><summary><label><input type="checkbox" data-cw-event="${esc(i.id)}" ${c.incidentIds?.includes(i.id)||m.selectedEvents?.includes(i.id)?'checked':''} ${c.incidentIds?.includes(i.id)?'disabled':''}><strong>${esc(i.title)}</strong></label><span>${rows.length} 条告警</span></summary>${rows.map(row).join('')}</details>`;}).join('')||'<p class="iv-empty">没有可关联的事件。</p>';
    return eligibleAlerts.filter(a=>!q||(a.title+' '+a.id).toLowerCase().includes(q)).map(row).join('')||'<p class="iv-empty">没有匹配的告警。</p>';
  }
  function modal(){
    const m=ui.modal;if(!m?.type?.startsWith('cw-'))return '';const c=currentCase();let title='',body='',footer='';
    if(m.type==='cw-add'){
      title='添加告警 / 事件';body=`<div class="case-mode-tabs">${btn('按告警选择','cw-add-mode','alerts',m.mode==='alerts'?'primary':'')}${btn('按事件选择','cw-add-mode','events',m.mode==='events'?'primary':'')}</div><input id="cw-add-search" class="cw-search" type="search" aria-label="搜索告警或事件" placeholder="搜索名称或 ID" value="${esc(m.query||'')}" data-cw-add-search><p>已选择 <b>${m.selected.length}</b> 条新增告警${m.selectedEvents?.length?` · ${m.selectedEvents.length} 个事件`:""}；重复成员自动去重。</p><div class="cw-checklist cw-add-list">${addOptions(m)}</div>`;footer=btn('添加到本案','cw-add-save','','primary');
    }else if(m.type==='cw-investigate'){
      const d=m.draft||{},r=runs(c).find(r=>r.id===m.sourceRunId),selected=d.alertIds||c.alertIds,readonly=!!d.id&&d.status!=='draft',outside=selected.filter(id=>!c.alertIds.includes(id)&&getAlert(id)),options=[...new Map([...members(c),...(m.fromGraph?outside.map(getAlert):[])].map(a=>[a.id,a])).values()];
      title=readonly?d.status==='cancelled'?'已取消的调查安排':'已启动的调查安排':d.id?'调整待启动调查':'新建调查安排';
      body=`<form id="cw-plan-form"><fieldset ${readonly?'disabled':''}>${field('调查目标','objective',d.objective||'',true)}${r?`<p>接续：<a href="${runUrl(c,r.id)}">${esc(r.title)}</a></p>`:''}<h3>本次调查范围</h3><div class="cw-checklist">${options.map(a=>`<label><input type="checkbox" name="alert" value="${esc(a.id)}" ${selected.includes(a.id)?'checked':''}><span>${esc(a.title)}<small>${date(a.event_time||a.first,true)}${!c.alertIds.includes(a.id)?' · 保存时加入本案':''}</small></span>${severity(a.severity)}</label>`).join('')||'<p>暂无选定告警，可选对象作为补查目标。</p>'}</div>${(d.entityIds||[]).length?`<h3>补查对象</h3><div class="cw-checklist">${d.entityIds.map(id=>`<label><input type="checkbox" name="entity" value="${esc(id)}" checked><span>${esc(getAsset(id)?.name||id)}</span></label>`).join('')}</div>`:''}${outside.length?`<p class="notice warning">选中了 ${outside.length} 条案外告警。确认保存时加入本案；关闭表单不改变成员。</p>`:''}<details class="cw-picker"><summary>调查时间范围（可选）</summary><div class="cw-form-grid"><label class="cw-field">开始时间（UTC）<input type="datetime-local" name="timeStart" value="${esc(d.timeRange?.start?.slice(0,16)||'')}"></label><label class="cw-field">结束时间（UTC）<input type="datetime-local" name="timeEnd" value="${esc(d.timeRange?.end?.slice(0,16)||'')}"></label></div></details>${materialPicker(c,d.materials?.map(x=>x.id)||m.materialIds||[])}</fieldset></form><p class="cw-boundary">${readonly?'安排记录保留；取消不会移除已加入的成员或停止其他调查。':'保存后进入“待启动调查”，点击“启动调查”后才开始执行。'}</p>`;
      footer=readonly?'':btn(outside.length&&m.fromGraph?'加入并保存安排':'保存安排','cw-plan-save','','primary')+(c.simulation?'':'<button class="button" disabled title="调查执行服务尚未接入">启动调查</button>');
    }else if(m.type==='cw-task'){
      const t=M.humanTasks(c).find(t=>t.id===m.id)||{},selected=t.materials?.map(x=>x.id)||[];
      title=t.id?'编辑人工任务':'添加人工任务';body=`<form id="cw-task-form">${field('任务事项','title',t.title||m.title||'')}${field('工作说明','description',t.description||m.description||'',true)}${(t.referenceContext||m.referenceContext)?`<div class="cw-task-context"><h3>需要确认的范围</h3><div class="cw-reference-links">${ctx.assistant?.().referenceLinks(c,t.referenceContext||m.referenceContext)||''}</div></div>`:''}<div class="cw-form-grid"><label class="cw-field">负责人<select name="owner">${[...new Set([t.owner,...store.people].filter(Boolean))].map(p=>`<option ${p===(t.owner||'未分配')?'selected':''}>${esc(p)}</option>`).join('')}</select></label><label class="cw-field">截止时间<input name="due" type="datetime-local" value="${esc(t.due||'')}"></label><label class="cw-field">状态<select name="status">${[['New','未开始'],['In progress','进行中'],['Completed','已完成'],['Cancelled','已取消']].map(([v,n])=>`<option value="${v}" ${(t.status||'New')===v?'selected':''}>${n}</option>`).join('')}</select></label><label class="cw-field">来源调查（可选）<select name="sourceRunId"><option value="">未关联</option>${runs(c).map(r=>`<option value="${esc(r.id)}" ${(t.sourceRunId||m.sourceRunId)===r.id?'selected':''}>${esc(r.title)}</option>`).join('')}</select></label></div>${field('确认 / 处理结果（完成时填写）','result',t.result||'',true)}<p class="iv-note">可直接记录人工确认，例如“已确认是本人执行的正常运维”。无需提供工单或上传附件。</p>${materialPicker(c,selected,false,t.sourceRunId||m.sourceRunId)}</form>`;footer=btn('保存任务','cw-task-save','','primary');
    }else if(m.type==='cw-review'){
      const r=runs(c).find(r=>r.id===m.runId),a=r?.actions?.[m.index];if(!a)return '';
      const review=reviewFor(c,r,m.index);title='审阅响应动作';body=`<h3>${esc(a.description||a.action_type)}</h3><p><b>目标：</b>${esc(a.target)}</p><p><b>依据：</b>${esc(a.rationale||'未提供具体依据，请先核查来源材料。')}</p><a href="${runUrl(c,r.id,'report')}">查看来源报告</a><form id="cw-review-form"><label class="cw-field">决定<select name="decision"><option value="">请选择</option><option value="approved" ${review?.decision==='approved'?'selected':''}>批准，待执行</option><option value="rejected" ${review?.decision==='rejected'?'selected':''}>拒绝</option></select></label>${field('决定理由 / 影响核对','reason',review?.reason||'',true)}</form><p class="cw-boundary">当前只保存本地审阅决定，不执行隔离、封禁或账号变更。</p>`;footer=btn('保存决定','cw-review-save','','primary');
    }
    return `<div class="modal-backdrop"><section class="modal cw-modal" role="dialog" aria-modal="true" aria-label="${esc(title)}"><header class="modal-header"><h2>${esc(title)}</h2>${btn('关闭','close-modal')}</header><div class="modal-content">${body}<div id="cw-error" class="form-error" role="alert">${esc(m.error||'')}</div></div><footer class="modal-footer">${btn('取消','close-modal')}${footer}</footer></section></div>`;
  }
  function open(type,props={}){ui.modal={type,...props};render();}
  function handle(action,value){
    if(!action.startsWith('cw-'))return false;const c=currentCase(),m=ui.modal;
    if(currentRoute().page!=='cases')return true;
    if(c.recordedImport&&!['cw-material-view','cw-material-object','cw-material-reset'].includes(action)){toast('此为实际执行导出，只读回查；未向服务保存或发起调查。');return true;}
    try{
      if(action==='cw-material-view'){if(['objects','runs'].includes(value)){materialState().view=value;render();}}
      else if(action==='cw-material-object'){materialState().objectId=value;render();}
      else if(action==='cw-material-reset'){Object.assign(materialState(),{query:'',type:'',objectId:null});render();}
      else if(action==='cw-add')open('cw-add',{mode:'alerts',selected:[],selectedEvents:[],query:''});
      else if(action==='cw-add-related'){const [runId,alertId]=JSON.parse(value),a=getAlert(alertId);if((runId&&!runs(c).some(r=>r.id===runId))||!a||!eligible(c,a)||c.alertIds.includes(alertId))throw Error('该告警当前不可加入本案。');const route=currentRoute();open('cw-add',{mode:'alerts',selected:[alertId],query:a.title,returnTo:url(c,route.tab||'attack')+(route.search?'?'+route.search:'')});}
      else if(action==='cw-add-mode'){m.mode=value;render();}
      else if(action==='cw-add-save'){const n=addMembers(c,m.selected,m.selectedEvents||[]),back=m.returnTo;ui.modal=null;if(back){navigate(back);render();}else navigate(url(c,'alerts'));toast(n?`已加入 ${n} 条告警，基础调查待更新`:'已关联事件，成员告警未变化');}
      else if(action==='cw-investigate')open('cw-investigate');
      else if(action==='cw-continue')ctx.assistant?.().open({runId:value});
      else if(action==='cw-plan'){const d=(c.investigationDrafts||[]).find(d=>d.id===value);if(d)open('cw-investigate',{draft:d,sourceRunId:d.sourceRunId});}
      else if(action==='cw-task-investigate'){const t=(c.tasks||[]).find(t=>t.id===value);if(t?.result)ctx.assistant?.().open({taskId:value});}
      else if(action==='cw-plan-cancel'){cancelDraft(c,value);render();toast('调查安排已取消，成员和执行中的调查不变');}
      else if(action==='cw-simulate-start'){const r=startSimulation(c,value);navigate(runUrl(c,r.id));toast('调查已进入等待队列');}
      else if(action==='cw-simulate-next'){advanceSimulation(c,value);render();}
      else if(action==='cw-plan-save'){const f=new FormData(document.getElementById('cw-plan-form'));saveDraft(c,{id:m.draft?.id,objective:f.get('objective'),alertIds:f.getAll('alert'),materialIds:f.getAll('material'),sourceRunId:m.sourceRunId,entityIds:f.getAll('entity'),timeStart:f.get('timeStart')?f.get('timeStart')+'Z':null,timeEnd:f.get('timeEnd')?f.get('timeEnd')+'Z':null,confirmAdd:!!m.fromGraph,graphReference:m.draft?.graphReference});ui.modal=null;navigate(url(c,'overview'));toast('已保存到待启动调查');}
      else if(action==='cw-task')open('cw-task',{id:value});
      else if(action==='cw-followup')open('cw-task',{sourceRunId:value});
      else if(action==='cw-task-save'){const f=new FormData(document.getElementById('cw-task-form'));saveTask(c,{...Object.fromEntries(f),id:m.id,referenceContext:m.referenceContext||M.humanTasks(c).find(t=>t.id===m.id)?.referenceContext,materialIds:f.getAll('material')});ui.modal=null;navigate(url(c,'tasks'));toast('人工任务已保存');}
      else if(action==='cw-review'){const [runId,index]=JSON.parse(value);open('cw-review',{runId,index});}
      else if(action==='cw-review-save'){const f=new FormData(document.getElementById('cw-review-form'));decide(c,m.runId,m.index,f.get('decision'),f.get('reason'));ui.modal=null;render();toast('审阅决定已保存，未执行响应');}
    }catch(error){if(m){m.error=error.message;const el=document.getElementById('cw-error');if(el)el.textContent=error.message;}else toast(error.message);}
    return true;
  }
  function input(el){if(el.hasAttribute('data-cw-add-search')){ui.modal.query=el.value;render();return true;}if(el.hasAttribute('data-cw-material-search')){materialState().query=el.value;render();return true;}return false;}
  function change(el){
    if(el.hasAttribute('data-cw-material-type')){materialState().type=el.value;render();return true;}
    const m=ui.modal,c=currentCase();if(m?.type!=='cw-add')return false;
    if(el.hasAttribute('data-cw-alert')||el.hasAttribute('data-cw-event')){
      const ids=el.hasAttribute('data-cw-alert')?[el.getAttribute('data-cw-alert')]:store.alerts.filter(a=>a.incidentId===el.getAttribute('data-cw-event')&&eligible(c,a)&&!c.alertIds.includes(a.id)).map(a=>a.id);
      if(el.hasAttribute('data-cw-event')){const eventId=el.getAttribute('data-cw-event');m.selectedEvents=el.checked?[...new Set([...(m.selectedEvents||[]),eventId])]:(m.selectedEvents||[]).filter(id=>id!==eventId);}
      else if(!el.checked){const a=getAlert(el.getAttribute('data-cw-alert'));m.selectedEvents=(m.selectedEvents||[]).filter(id=>id!==a?.incidentId);}
      m.selected=el.checked?[...new Set([...m.selected,...ids])]:m.selected.filter(x=>!ids.includes(x));render();return true;
    }return false;
  }
  function submit(form){if(!['cw-plan-form','cw-task-form','cw-review-form'].includes(form.id))return false;handle({'cw-plan-form':'cw-plan-save','cw-task-form':'cw-task-save','cw-review-form':'cw-review-save'}[form.id],'');return true;}
  return {openGraphAdoption,openPreparation:props=>open('cw-investigate',props),openHumanTask:props=>open('cw-task',props),askContext:value=>ctx.assistant?.().open(value),activeRun,activeBanner,currentWork,runControls,cancelDraft,startSimulation,advanceSimulation,prepareFromGraph,prepareFromAlert,consumeAlertPreparation,caseScope:a=>{const [sourceEnvironment,sourceTenantId]=source(a);return {sourceEnvironment,sourceTenantId};},toolbar,plans,taskSummary,materials,tasks,modal,responseControls,handle,input,change,submit,addMembers,moveTargets,moveMembers,saveAssistantResult,saveDraft,saveTask,decide,eligible,materialOptions};
};
