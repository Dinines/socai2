/* Shared Case story and conversation presentation. External execution is adapter-owned. */
'use strict';
window.createCaseAssistant=function(ctx){
  const {store,esc,btn,badge,date,severity,I,currentCase,currentRoute,getAlert,getAsset,render,toast}=ctx;
  const M=window.investigationWorkspaceModel,storageKey='aisoc-case-assistant-preview';
  let saved={};try{saved=JSON.parse(localStorage.getItem(storageKey))||{};}catch{}
  const sessions=new Map();let activeKey=null,focusInput=false,scrollEnd=false,focusStory=false;
  const key=c=>JSON.stringify([c.id,c.sourceEnvironment||'',c.sourceTenantId||'']);
  const link=(c,tab)=>`#/cases/${encodeURIComponent(c.id)}/${tab}`;
  const runLink=(c,id)=>link(c,'investigations')+'?'+new URLSearchParams({run:id,view:'overview'});
  const alertLink=id=>`#/alerts/${encodeURIComponent(id)}/overview`;
  const runs=c=>M.forCase(store,c);
  const scopedAsset=(c,id)=>{const a=getAsset(id);return a&&(!a.sourceEnvironment||a.sourceEnvironment===(c.sourceEnvironment||''))&&(!a.sourceTenantId||a.sourceTenantId===(c.sourceTenantId||''))?a:null;};
  const memberAlerts=c=>[...new Set(c.alertIds)].map(getAlert).filter(a=>a&&ctx.workflow().eligible(c,a));
  const stamp=a=>{const value=a.event_time||(a.persistedRecord?null:a.first),n=value?Date.parse(value):NaN;return Number.isFinite(n)?n:null;};
  function storyRows(c){return memberAlerts(c).sort((a,b)=>(stamp(b)??-Infinity)-(stamp(a)??-Infinity)||String(a.id).localeCompare(String(b.id)));}
  function session(){
    const c=currentCase(),k=key(c);
    if(!sessions.has(k))sessions.set(k,{open:false,input:'',context:{},messages:Array.isArray(saved[k])?saved[k].map(m=>m.status==='running'?{...m,status:'failed',error:'上次请求已中断，请重试。'}:m):[],selected:[],focus:null,query:'',severity:'',starterOffered:false,seededInput:null});
    const s=sessions.get(k);if(activeKey!==k){s.open=false;activeKey=k;}return s;
  }
  function normalize(c,value={}){
    const rows=runs(c),run=rows.find(r=>r.id===value.runId),task=M.humanTasks(c).find(t=>t.id===value.taskId);
    const known=memberAlerts(c),objects=new Set(known.flatMap(a=>a.entityIds||[]));
    // Graph candidates are references only: being in context never adopts membership.
    const alerts=[...new Set(value.alertIds||[])].filter(id=>getAlert(id)&&ctx.workflow().eligible(c,getAlert(id)));
    const available=store.alerts.filter(a=>ctx.workflow().eligible(c,a));for(const a of available)for(const id of a.entityIds||[])objects.add(id);
    return {alertIds:alerts,entityIds:[...new Set(value.entityIds||[])].filter(id=>objects.has(id)&&scopedAsset(c,id)),runId:run?.id||null,taskId:task?.id||null};
  }
  function contextItems(c,raw){
    const value=normalize(c,raw),items=[];
    for(const id of value.alertIds)items.push({label:getAlert(id).title,kind:c.alertIds.includes(id)?'告警':'案外线索',href:alertLink(id)});
    for(const id of value.entityIds)items.push({label:getAsset(id).name,kind:'对象',href:link(c,'attack')});
    if(value.runId)items.push({label:runs(c).find(r=>r.id===value.runId).title,kind:'调查',href:runLink(c,value.runId)});
    if(value.taskId)items.push({label:M.humanTasks(c).find(t=>t.id===value.taskId).title,kind:'人工结果',href:link(c,'tasks')});
    return items;
  }
  function suggestedQuestions(c,raw){
    const value=normalize(c,raw),items=contextItems(c,value);
    if(value.taskId)return [{title:'理解任务影响',text:`这个人工任务「${M.humanTasks(c).find(t=>t.id===value.taskId)?.title||'所选任务'}」的结果对案件已有判断有哪些影响？请区分支持、冲突和仍待确认的内容。`},{title:'核对相关证据',text:'请对照这个人工任务的反馈与相关告警、已有调查，说明哪些事实可以相互印证。'},{title:'明确下一步',text:'根据这项人工反馈，还有哪些问题需要继续核查？'}];
    const examples=!items.length?window.caseOutcomeData?.replies[c.id]:null;
    if(examples?.length&&window.caseOutcomeData.cases.some(x=>x.id===c.id&&M.sameScope(x,c)))return [...examples.slice(0,2).map(x=>({title:x.suggestion||x.question,text:x.question})),{title:'梳理整个案件',text:'请梳理当前案件的判断、依据和未解决问题。'}];
    const subject=items.length===1?`「${items[0].label}」`:items.length?'所选材料':`「${M.caseRecord(c).title}」`;
    return [
      {title:'梳理关键发现',hint:'发生了什么，还有哪些待确认问题',text:`请梳理${subject}的关键发现、支持依据和待确认问题。`},
      {title:'理解告警关联',hint:'查看共同对象与活动的先后关系',text:`请解释${subject}中的告警为什么关联在一起，哪些关系已有证据支持？`},
      {title:'明确下一步',hint:'找出当前缺少的证据和核查方向',text:`根据${subject}的已有资料，下一步最需要核查什么？`}
    ];
  }
  function open(value){
    const c=currentCase(),s=session();if(value!==undefined)s.context=normalize(c,value);
    if(!s.messages.length&&((!s.starterOffered&&!s.input)||(value!==undefined&&s.seededInput&&s.input===s.seededInput))){s.input=suggestedQuestions(c,s.context)[0].text;s.seededInput=s.input;}
    s.starterOffered=true;s.open=true;focusInput=true;scrollEnd=true;render();
  }
  function persist(c=currentCase(),s=session()){try{saved[key(c)]=s.messages;localStorage.setItem(storageKey,JSON.stringify(saved));}catch{toast('本机无法保存对话，当前页面仍可查看。');}}
  function excerpts(c,value){
    const scope=normalize(c,value),all=runs(c),ids=[...scope.alertIds,...memberAlerts(c).filter(a=>scope.entityIds.some(id=>a.entityIds?.includes(id))).map(a=>a.id)],hasScope=scope.alertIds.length||scope.entityIds.length,chosen=scope.runId?all.filter(r=>r.id===scope.runId):all.filter(r=>!hasScope||r.alertIds.some(id=>ids.includes(id)));
    const relatedTasks=M.humanTasks(c).filter(t=>t.status==='Completed'&&t.result&&(scope.taskId?t.id===scope.taskId:scope.runId?t.sourceRunId===scope.runId:hasScope?(t.referenceContext?.alertIds||[]).some(id=>ids.includes(id))||(t.referenceContext?.entityIds||[]).some(id=>scope.entityIds.includes(id)):true)).slice(0,3);
    const plain=x=>typeof x==='string'?x:JSON.stringify(x);
    return `<section class="ca-sources">${relatedTasks.map(t=>`<article><span>人工任务 · ${esc(t.title)}</span><small>${esc(t.owner||'未分配')} · ${date(t.completedAt,true)}</small><p>${esc(t.result)}</p><a href="${link(c,'tasks')}">查看人工任务 →</a></article>`).join('')}${chosen.filter(r=>r.findings?.length).slice(0,2).map(r=>`<article><a href="${runLink(c,r.id)}">${esc(r.title)}</a><small>${r.alertIds.length} 条本轮输入 · ${r.completion==='partial'?'部分交付':r.completion==='completed'?'完整交付':'查看原记录'}</small><p>${esc(plain(r.findings[0]))}</p></article>`).join('')||'<p class="muted">当前范围没有已保存的调查发现，可先查看来源告警。</p>'}<small>来源：已有调查与人工任务记录</small></section>`;
  }
  function illustrativeReply(c,question,context){
    const data=window.caseOutcomeData,example=data?.cases.find(x=>x.id===c.id&&M.sameScope(x,c));
    if(!example)return null;
    const sourceRuns=runs(c),sourceTasks=M.humanTasks(c),selectedRun=sourceRuns.find(r=>r.id===context.runId),selectedTask=sourceTasks.find(t=>t.id===context.taskId);
    const explicit=!!(context.alertIds.length||context.entityIds.length||selectedRun||selectedTask);
    const ids=[...new Set([...context.alertIds,...(selectedRun?.alertIds||[]),...(selectedTask?.referenceContext?.alertIds||[]),...memberAlerts(c).filter(a=>context.entityIds.some(id=>a.entityIds.includes(id))).map(a=>a.id),...(!explicit?c.alertIds:[])])];
    const scenario=(data.replies[c.id]||[]).find(x=>new RegExp(x.match).test(question)&&x.alertIds.every(id=>ids.includes(id))&&(!selectedRun||x.runIds.includes(selectedRun.id))&&(!selectedTask||x.taskIds.includes(selectedTask.id)));
    const selected=selectedRun?M.runOutcome(selectedRun):null,a=M.caseAssessment(store,c);
    const fallback=selected?{title:selected.conclusion,outcome:selected,runIds:[selectedRun.id],taskIds:[],alertIds:ids}:!explicit?{title:a.conclusion,outcome:{purpose:question,conclusion:a.conclusion,findings:a.basis,basis:a.basis,change:'梳理当前保存的判断与待确认范围。',impact:'提供已有材料的解释，未修改案件判断。',limitations:a.unresolved},runIds:a.sourceRunIds,taskIds:a.taskIds,alertIds:ids}:{title:'所选范围仍需补充核查',outcome:{purpose:question,conclusion:'所选材料能确认活动线索，尚不足以作出进一步判断',findings:ids.map(id=>getAlert(id)?.description).filter(Boolean),basis:['所选告警的已保存描述'],change:'本次仅核对已选材料，未取得新的日志。',impact:'保留待核查状态，不扩大案件成员或确认受影响范围。',limitations:['当前材料不足以回答更多细节']},runIds:[],taskIds:[],alertIds:ids};
    const result=structuredClone(scenario||fallback);
    result.outcome.purpose=question;
    result.context={alertIds:result.alertIds,runIds:result.runIds,taskIds:result.taskIds};
    result.process=[{name:'读取所选材料',detail:`核对 ${ids.length} 条告警及其已有资料。`},{name:'对照调查与人工反馈',detail:`引用 ${result.runIds.length} 条已有调查、${result.taskIds.length} 项人工任务。`},{name:'整理结论和边界',detail:'保留仍待确认的事项，不自动修改案件判断。'}];
    return result;
  }
  function requestAnswer(c,s,question){
    const inputSnapshot=new Map(store.alerts.filter(a=>ctx.workflow().eligible(c,a)).map(a=>[a.id,structuredClone(a)]));
    const runSnapshot=new Map(runs(c).map(r=>[r.id,{id:r.id,title:r.title,alertIds:r.alertIds.slice(),started:r.started,ended:r.ended,outcome:structuredClone(M.runOutcome(r))}]));
    const taskSnapshot=new Map(M.humanTasks(c).map(t=>[t.id,structuredClone(t)]));
    const requestKey=key(c),pending={id:'answer-'+question.id,role:'assistant',status:'running',text:'正在分析所选材料…',questionId:question.id,time:new Date().toISOString(),context:structuredClone(question.context)};
    s.messages.push(pending);persist(c,s);
    s.pending=Promise.resolve().then(()=>ctx.answer?ctx.answer({caseId:c.id,question:question.text,context:question.context}):illustrativeReply(c,question.text,question.context)).then(result=>{
      if(!result)throw Error('AI 分析服务尚未连接，暂时无法执行此问题，可稍后重试。');
      if(!result.outcome?.conclusion)throw Error('本次未返回可用结论，请重试或补充问题。');
      const eligibleIds=(result.alertIds||[]).filter(id=>getAlert(id)&&ctx.workflow().eligible(c,getAlert(id)));
      if(eligibleIds.length!==(result.alertIds||[]).length)throw Error('返回材料与本案数据范围不一致。');
      if((result.runIds||[]).some(id=>!runs(c).some(r=>r.id===id))||(result.taskIds||[]).some(id=>!M.humanTasks(c).some(t=>t.id===id)))throw Error('返回引用不属于本案。');
      if(eligibleIds.some(id=>!inputSnapshot.has(id)))throw Error('返回材料不在本次请求的资料快照中，请重新提问。');
      if((result.runIds||[]).some(id=>!runSnapshot.has(id))||(result.taskIds||[]).some(id=>!taskSnapshot.has(id)))throw Error('返回引用不在本次请求的资料快照中，请重新提问。');
      pending.referenceSnapshot={capturedAt:question.time,runs:(result.runIds||[]).map(id=>runSnapshot.get(id)),tasks:(result.taskIds||[]).map(id=>taskSnapshot.get(id))};
      pending.inputSnapshot=eligibleIds.map(id=>inputSnapshot.get(id)).filter(Boolean);pending.status='completed';pending.text=result.outcome.conclusion;pending.result=structuredClone(result);pending.time=new Date().toISOString();
    }).catch(error=>{pending.status='failed';pending.error=error.message||'本次分析未完成，请重试。';}).finally(()=>{persist(c,s);s.pending=null;if(key(currentCase())===requestKey){scrollEnd=true;render();}});
    render();
  }
  function send(text){
    const c=currentCase(),s=session(),question=String(text||'').trim();if(!question||s.pending)return false;
    const context=normalize(c,s.context),m={id:'question-'+Date.now()+'-'+Math.random().toString(36).slice(2,6),role:'user',text:question.slice(0,4000),context,time:new Date().toISOString()};
    s.messages.push(m);s.input='';persist(c,s);scrollEnd=true;focusInput=true;
    // Examples use the same response renderer; non-connected real records retain an explicit error.
    if(ctx.answer||window.caseOutcomeData?.cases.some(x=>x.id===c.id&&M.sameScope(x,c)))requestAnswer(c,s,m);
    else {m.status='failed';m.error='AI 分析服务尚未连接，暂时无法执行此问题，可稍后重试。';persist(c,s);render();}
    return true;
  }
  function answerReferences(c,m){const r=m.result||{};return `${(r.runIds||[]).filter(id=>runs(c).some(x=>x.id===id)).map(id=>`<a href="${runLink(c,id)}">${esc(runs(c).find(x=>x.id===id).title)}</a>`).join('')}${(r.taskIds||[]).filter(id=>M.humanTasks(c).some(x=>x.id===id)).map(id=>`<a href="${link(c,'tasks')}">${esc(M.humanTasks(c).find(x=>x.id===id).title)}</a>`).join('')}${(r.alertIds||[]).filter(id=>getAlert(id)&&ctx.workflow().eligible(c,getAlert(id))).map(id=>`<a href="${alertLink(id)}">${esc(getAlert(id).title)}</a>`).join('')}`;}
  function answerCard(c,m,s){
    if(m.status==='running')return `<section class="ca-message ca-message-system"><div class="ca-message-meta">AI 助手</div><div class="ca-bubble" role="status">正在读取材料并分析问题…</div></section>`;
    if(m.status==='failed')return `<section class="ca-message ca-message-system"><div class="ca-bubble ca-error" role="status"><p>${esc(m.error)}</p>${btn('重试','ca-retry',m.questionId,'small')}</div></section>`;
    const o=m.result?.outcome||{},record=runs(c).find(r=>r.id===m.savedRunId);
    return `<section class="ca-message ca-message-system"><div class="ca-message-meta"><span class="ca-avatar">${I('sparkles',14)}</span>AI 助手 <time>${date(m.time,true)}</time></div><div class="ca-bubble ca-answer"><h3>${esc(o.conclusion||m.text)}</h3>${(o.findings||[]).map(x=>`<p>${esc(x)}</p>`).join('')}<div class="ca-answer-impact"><b>对案件的影响</b><p>${esc(o.impact||'未记录')}</p></div>${o.limitations?.length?`<p class="ca-secondary">仍待确认：${o.limitations.map(esc).join('；')}</p>`:''}<details class="ca-reference"><summary>分析过程与依据</summary>${(m.result?.process||[]).map(x=>`<p><b>${esc(x.name)}</b><br>${esc(x.detail)}</p>`).join('')}<div class="ca-answer-links">${answerReferences(c,m)}</div></details>${record?`<div class="ca-saved">已保存到调查记录 · ${date(record.savedAt,true)}<a href="${runLink(c,record.id)}">查看已保存结论 →</a></div>`:s.saveAnswerId===m.id?`<form id="ca-save-form" data-answer="${esc(m.id)}" class="ca-save-form"><label>记录标题<input name="title" maxlength="180" value="${esc(m.result?.title||o.conclusion)}" required></label><label>保存结论<textarea name="conclusion" maxlength="4000" required>${esc(o.conclusion)}</textarea></label><p>${m.result.alertIds.length} 条关联告警 · 同时保留本次对话与材料引用；案件判断保持不变。</p><div>${btn('取消','ca-save-cancel','','small')}<button type="submit" class="button primary small">确认保存</button></div></form>`:btn('保存到调查记录','ca-save',m.id,'small','check')}</div></section>`;
  }
  function referenceLinks(c,value){return value?contextItems(c,value).map(x=>`<a href="${x.href}">${esc(x.kind)} · ${esc(x.label)}</a>`).join(''):'';}
  function panel(){
    const c=currentCase(),s=session();if(!s.open)return '';
    const context=contextItems(c,s.context),active=ctx.workflow().activeRun(c),items=s.messages;
    const sourceLinks=value=>contextItems(c,value).map(x=>`<a href="${x.href}">${esc(x.kind)} · ${esc(x.label)}</a>`).join('');
    const message=m=>m.role==='assistant'?answerCard(c,m,s):`<article class="ca-exchange"><section class="ca-message ca-message-user" aria-label="你的问题"><div class="ca-message-meta">你 <time>${date(m.time,true)}</time></div><div class="ca-bubble"><p>${esc(m.text)}</p>${contextItems(c,m.context).length?`<details class="ca-message-context"><summary>提问范围 · ${contextItems(c,m.context).length} 项材料</summary>${sourceLinks(m.context)}</details>`:'<small class="ca-message-scope">整个案件</small>'}</div><details class="ca-reference ca-question-references"><summary>${I('columns',14)} 参考资料 ${I('down',12)}</summary>${excerpts(c,m.context)}</details>${m.error?`<div class="ca-error" role="status">${esc(m.error)}${btn('重试','ca-retry',m.id,'small')}</div>`:''}</section></article>`;
    const welcome=`<section class="ca-welcome"><div class="ca-welcome-icon">${I('sparkles',24)}</div><h3>想了解这个案件的什么？</h3><p>围绕已有发现、告警关联或待确认的问题提问。</p><small class="ca-welcome-hint">可修改输入框中的问题，或选择下方建议。</small></section>`;
    const suggestions=`<div class="ca-suggestion-bar" aria-label="建议问题"><span>你可以问</span><div class="ca-suggestions">${suggestedQuestions(c,s.context).map(q=>`<button type="button" data-action="ca-suggest" data-id="${esc(q.text)}" title="${esc(q.text)}">${esc(q.title)}</button>`).join('')}</div></div>`;
    const scopeLabel=context.length===1?`${context[0].kind} · ${context[0].label}`:context.length?`${context.length} 项已选材料`:'整个案件';
    return `<aside class="ca-panel" aria-label="案件 AI 助手"><header><div class="ca-heading"><span class="ca-heading-icon">${I('sparkles',19)}</span><h2>AI 助手</h2></div><button type="button" class="ca-close" data-action="ca-close" aria-label="关闭助手">${I('close',18)}</button></header><div class="ca-case" title="${esc(M.caseRecord(c).title)}">${I('briefcase',14)}<span>${esc(M.caseRecord(c).title)}</span></div>${active?`<div class="ca-active">本案已有调查${active.status==='running'?'执行中':'等待结束'} <a href="${runLink(c,active.id)}">查看进度 →</a></div>`:''}<div class="ca-thread" id="ca-thread" role="log" aria-label="案件对话">${items.length?items.map(message).join(''):welcome}</div><form id="ca-question-form" class="ca-composer">${suggestions}<div class="ca-composer-context">${context.length?`<details><summary title="${esc(scopeLabel)}">${I('briefcase',13)}<span>${esc(scopeLabel)}</span>${I('down',12)}</summary><div class="ca-context-popover">${sourceLinks(s.context)}${btn('改为整个案件','ca-context-clear','','small')}</div></details>`:`<span>${I('briefcase',13)} 整个案件</span>`}</div><label for="ca-question">你的问题</label><textarea id="ca-question" rows="3" maxlength="4000" placeholder="输入问题，或选择上方建议…">${esc(s.input)}</textarea><div class="ca-composer-footer"><span>发送后分析所选范围</span><button class="button primary" type="submit" ${s.pending?'disabled':''}>${s.pending?'分析中…':'发送'} ${I('arrow',14)}</button></div></form></aside>`;
  }
  function launcher(){const s=session();return s.open?'':`<div class="ca-launcher">${btn('询问 AI','ca-open','','primary','sparkles')}</div>`;}
  function story(){
    const c=currentCase(),s=session(),all=storyRows(c),known=all.filter(a=>stamp(a)!==null),unknown=all.filter(a=>stamp(a)===null);
    s.selected=s.selected.filter(id=>all.some(a=>a.id===id));
    const match=a=>(!s.severity||({High:'高',Medium:'中',Low:'低',Informational:'信息'})[a.severity]===s.severity||a.severity===s.severity)&&(!s.query||[a.title,...(a.entityIds||[]).map(id=>scopedAsset(c,id)?.name||'')].join(' ').toLowerCase().includes(s.query.toLowerCase()));
    const visible=all.filter(match),chosen=visible.find(a=>a.id===s.focus)||visible[0];
    const timeline=rows=>rows.filter(match).map(a=>`<article class="cs-event ${chosen?.id===a.id?'selected':''}"><div class="cs-event-top"><label><input type="checkbox" data-ca-select="${esc(a.id)}" ${s.selected.includes(a.id)?'checked':''} aria-label="选择告警：${esc(a.title)}"><time>${stamp(a)===null?'时间未记录':date(stamp(a),true)}</time></label><div class="cs-event-tags"><span class="tactic-label tactic-tone-${M.tacticTone(a.category)}">${esc(a.category||'阶段未记录')}</span>${severity(a.severity)}</div></div><button class="cs-event-title" data-action="ca-story-focus" data-id="${esc(a.id)}">${esc(a.title)}</button><div class="cs-event-footer"><div class="cs-entities">${[...new Set(a.entityIds||[])].map(id=>scopedAsset(c,id)).filter(Boolean).slice(0,3).map(e=>`<span>${I(e.type,13)}${esc(e.name)}</span>`).join('')}</div>${btn('围绕此告警提问','ca-alert',a.id,'small')}</div></article>`).join('');
    const records=[...runs(c).map(r=>{const o=M.runOutcome(r);return {id:r.id,kind:M.investigationLabel(r),title:o.conclusion,time:r.savedAt||r.ended||r.started,summary:[o.purpose,...o.findings.slice(0,2)].filter(Boolean).map(x=>/[。！？?!]$/.test(x)?x:x+'。').join(''),impact:o.impact,change:o.change,href:runLink(c,r.id),action:'ca-run',alertIds:r.alertIds,when:r.savedAt?'结论保存':r.ended?'调查结束':'调查开始'};}),...M.humanTasks(c).filter(t=>t.status==='Completed'&&t.result).map(t=>({id:t.id,kind:'人工任务',title:t.title,time:t.completedAt,summary:t.result,href:link(c,'tasks'),action:'ca-result',alertIds:t.referenceContext?.alertIds||[],when:'任务完成'}))];
    const visibleRecords=records.filter(r=>(!s.query||[r.title,r.summary].join(' ').toLowerCase().includes(s.query.toLowerCase())||r.alertIds.some(id=>visible.some(a=>a.id===id)))&&(!s.severity||r.alertIds.some(id=>visible.some(a=>a.id===id))));
    const recordCard=r=>`<article class="cs-event cs-work-record"><div class="cs-event-top"><span>${esc(r.kind)} · ${esc(r.when)}</span><time>${r.time?date(r.time,true):'时间未记录'}</time></div><h4><a href="${r.href}">${esc(r.title)}</a></h4><p>${esc(r.summary)}</p>${r.change?`<p class="cs-record-impact"><b>变化</b> ${esc(r.change)}<br><b>对案件</b> ${esc(r.impact)}</p>`:''}${btn(r.kind==='人工任务'?'询问任务影响':'询问本轮结果',r.action,r.id,'small','sparkles')}</article>`;
    const ordered=[...known.filter(match).map(a=>({time:stamp(a),html:timeline([a])})),...visibleRecords.filter(r=>Number.isFinite(Date.parse(r.time))).map(r=>({time:Date.parse(r.time),html:recordCard(r)}))].sort((a,b)=>b.time-a.time).map(r=>r.html).join('');
    const undatedRecords=visibleRecords.filter(r=>!Number.isFinite(Date.parse(r.time))).map(recordCard).join('');
    const related=chosen?runs(c).filter(r=>r.alertIds.includes(chosen.id)):[];
    const shared=chosen?[...new Set(chosen.entityIds||[])].map(id=>({e:scopedAsset(c,id),n:all.filter(a=>a.id!==chosen.id&&a.entityIds?.includes(id)).length})).filter(x=>x.e&&x.n):[];
    return `<div class="cs-story"><div class="iv-heading"><div><h2>案件故事</h2><p>串联告警活动、调查记录和人工反馈，选择一项继续提问。</p></div><a class="button small" href="${link(c,'investigations')}">查看调查历史</a></div><div class="cs-summary"><div><b>${all.length}</b> 条成员告警 <span>·</span> <b>${new Set(all.flatMap(a=>a.entityIds||[])).size}</b> 个对象</div><span>${known.length?date(stamp(known.at(-1)),true)+' — '+date(stamp(known[0]),true):'发生时间未记录'}</span></div><div class="cs-toolbar"><input id="cs-search" type="search" data-ca-search value="${esc(s.query)}" placeholder="搜索告警、主机或账号" aria-label="搜索故事告警"><select data-ca-severity aria-label="筛选故事严重程度"><option value="">全部严重程度</option>${['高','中','低','信息'].map(v=>`<option value="${v}" ${s.severity===v?'selected':''}>${v}</option>`).join('')}</select><span>${visible.length} / ${all.length} 条</span>${btn('重置','ca-story-reset','','small')}</div><div class="cs-selection"><span>${s.selected.length?'已选择 '+s.selected.length+' 条告警':'可选择一条或多条告警，围绕它们提问'}</span>${s.selected.length?btn('清除选择','ca-selection-clear','','small'):''}${btn(s.selected.length?'询问所选告警':'询问整个案件','ca-story-ask','','primary','sparkles')}</div><div class="cs-layout"><section class="cs-timeline" aria-label="案件告警时间线">${ordered}${unknown.some(match)||undatedRecords?'<h3 class="cs-unknown">时间未记录</h3>'+timeline(unknown)+undatedRecords:''}${!visible.length&&!visibleRecords.length?'<div class="iv-empty">暂无匹配告警，请调整筛选。</div>':''}</section><aside class="cs-details" id="cs-details" tabindex="-1" aria-label="故事告警详情">${chosen?`<h3>活动详情</h3><h4>${esc(chosen.title)}</h4><p>${esc(chosen.description||'尚无进一步说明。')}</p><a href="${alertLink(chosen.id)}">查看告警详情 →</a><h4>与本案其他告警的共同对象</h4>${shared.map(x=>`<p>${esc(x.e.name)}<small>另 ${x.n} 条告警也涉及此对象</small></p>`).join('')||'<p class="muted">当前未记录共同对象。</p>'}<a href="${link(c,'attack')}">查看案件关系图 →</a><h4>包含此告警的调查</h4>${related.map(r=>`<a class="cs-run" href="${runLink(c,r.id)}">${esc(r.title)}<small>${r.completion==='partial'?'部分交付':r.completion==='completed'?'完整交付':'查看原记录'} · ${r.alertIds.length} 条本轮输入</small></a>`).join('')||'<p class="muted">尚无对应调查记录。</p>'}`:'<p class="muted">选择告警后查看详情。</p>'}<p class="cs-note">时序和共同对象提供关联线索，不直接表示攻击因果。</p></aside></div></div>`;
  }
  function handle(action,value){
    if(!action.startsWith('ca-')||currentRoute().page!=='cases'||!currentRoute().id)return false;
    const s=session(),c=currentCase();
    if(action==='ca-open'){open();return true;}
    if(action==='ca-run'){open({runId:value});return true;}
    if(action==='ca-alert'){open({alertIds:[value]});return true;}
    if(action==='ca-result'){open({taskId:value});return true;}
    if(action==='ca-save'){const m=s.messages.find(m=>m.id===value&&m.role==='assistant'&&m.status==='completed');if(m)s.saveAnswerId=m.id;}
    if(action==='ca-save-cancel')s.saveAnswerId=null;
    if(action==='ca-retry'&&!s.pending){const q=s.messages.find(m=>m.id===value&&m.role!=='assistant');if(q){delete q.error;delete q.status;s.messages=s.messages.filter(m=>!(m.questionId===q.id&&m.status==='failed'));requestAnswer(c,s,q);return true;}}
    if(action==='ca-close')s.open=false;
    if(action==='ca-context-clear')s.context={};
    if(action==='ca-suggest'){s.input=value;s.seededInput=null;focusInput=true;}
    if(action==='ca-story-focus'){s.focus=value;s.open=false;focusStory=true;}
    if(action==='ca-story-reset'){s.query='';s.severity='';}
    if(action==='ca-selection-clear')s.selected=[];
    if(action==='ca-story-ask'){open({alertIds:s.selected});return true;}
    render();return true;
  }
  function input(el){if(el.id==='ca-question'){session().input=el.value;session().seededInput=null;return true;}if(el.hasAttribute('data-ca-search')){session().query=el.value;render();return true;}return false;}
  function change(el){const s=session();if(el.hasAttribute('data-ca-select')){const id=el.getAttribute('data-ca-select');s.selected=el.checked?[...new Set([...s.selected,id])]:s.selected.filter(x=>x!==id);render();return true;}if(el.hasAttribute('data-ca-severity')){s.severity=el.value;render();return true;}return false;}
  function submit(form){
    if(form.id==='ca-save-form'){const c=currentCase(),s=session(),m=s.messages.find(x=>x.id===form.dataset.answer);try{const f=new FormData(form),record=ctx.workflow().saveAssistantResult(c,m,s.messages,{title:f.get('title'),conclusion:f.get('conclusion')});m.savedRunId=record.id;s.saveAnswerId=null;persist(c,s);render();toast('结论已保存到调查记录');}catch(error){toast(error.message);}return true;}
    if(form.id!=='ca-question-form')return false;send(session().input);return true;
  }
  function afterRender(){if(focusStory){document.getElementById('cs-details')?.focus();focusStory=false;}if(focusInput){document.getElementById('ca-question')?.focus({preventScroll:true});focusInput=false;}if(scrollEnd){const el=document.getElementById('ca-thread');if(el)el.scrollTop=el.scrollHeight;scrollEnd=false;}}
  return {story,storyRows,panel,launcher,open,send,session,normalize,referenceLinks,handle,input,change,submit,afterRender};
};
