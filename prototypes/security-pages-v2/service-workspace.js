/* Explicit service mode. Credentials and pending forms live in memory only. */
'use strict';
window.socai2ServiceWorkspace = (() => {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const enc = encodeURIComponent;
  const names = {accepted:'已受理',new:'新建',in_progress:'处理中',resolved:'已解决',unknown:'执行状态待核实',pending_update:'尚未执行',running:'执行中',completed:'已结束',failed:'失败',cancelled:'已取消',not_started:'未开始',none:'未交付',planned:'计划中',skipped:'已跳过',timeout:'超时',partial:'部分交付',complete:'完整交付',unavailable:'不可用',high:'高',medium:'中',low:'低',critical:'严重',info:'信息'};
  const metrics = {awaiting_assignment:'待分配',in_progress:'处理中',high_severity:'高严重程度',awaiting_human:'待人工跟进'};
  const reasons = {scope_changed:'成员范围发生变化',member_versions_changed:'成员材料或分析已更新',incident_context_changed:'事件诊断或成员已更新',human_feedback_changed:'人工确认结果已更新',frozen_context_unavailable:'原始调查依据无法核对',single_baseline_source_unavailable:'无法核对唯一基础调查来源',baseline_active:'已有调查正在执行或状态待核实',empty_scope:'案件没有成员',resolved_case:'案件已解决',not_pending:'本轮不在待启动状态',ready:'可启动'};
  const label = value => names[value] || value || '未提供';
  const date = value => value ? new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'}) : '未提供';
  const path = (cid, suffix='') => '/cases/'+enc(cid)+suffix;
  const href = (cid, tab='case-info', query='') => '#/cases/'+enc(cid)+'/'+tab+(query?'?'+query:'');
  const uuid = () => crypto.randomUUID();
  function analysisTaskPath(receipt,kind,id){
    const expected=`/api/v1/socai2/${kind}s/${enc(id)}/analysis-tasks/${enc(receipt?.task_id)}`;
    if(!receipt?.task_id||receipt.subject_type!==kind||receipt.subject_id!==id||receipt.status_url!==expected)throw Error('分析任务回执身份或读取链接不一致。');
    return expected.slice('/api/v1/socai2'.length);
  }
  function allocationTargets(receipt){
    if(!Array.isArray(receipt?.allocations)||!receipt.allocations.length)throw Error('服务未返回实际案件分配结果。请核对原操作，不要重新建案。');
    const seen=new Set();
    for(const item of receipt.allocations){
      if(!item.case_id||seen.has(item.case_id))throw Error('案件分配身份缺失或重复。');seen.add(item.case_id);
      if(item.initial_task)analysisTaskPath(item.initial_task,'case',item.case_id);
      if(item.created&&!item.initial_task)throw Error('新案件缺少首轮任务回执。');
    }
    return receipt.allocations;
  }
  const localInputTime=value=>value?new Date(new Date(value).getTime()-new Date(value).getTimezoneOffset()*60000).toISOString().slice(0,23):'';
  const sameTimeInput=(entered,original)=>entered?Number.isFinite(Date.parse(entered))&&Date.parse(entered)===Date.parse(original):!original;
  function errorMessage(error) {
    if(error.status===409)return '记录已变化或已有调查占用执行位置。请查看最新记录；输入内容已保留。';
    if(error.status===401)return '登录凭据无效或已过期，请重新连接。';
    if(error.status===403)return '当前账户没有此操作权限。';
    if(error.status===501)return '此功能暂未开放。';
    if(error.status===503)return error.code==='socai2_case_api_not_enabled'?'当前服务尚未开放此功能。':'服务暂时不可用，请刷新执行记录核实操作结果，不要重复启动调查。';
    if(error.status===422)return '提交内容不符合要求，请核对范围、时间和必填项。';
    return error.status ? '服务未完成此请求，请稍后刷新查看。' : '连接失败，无法确认操作结果。请刷新查看，不要重复启动调查。';
  }
  function createClient(base, token, fetcher=window.fetch.bind(window)) {
    const url = new URL(base || '/api/v1/socai2', location.href);
    if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash)throw Error('服务地址应为不含凭据或查询参数的 HTTP 地址。');
    if(url.protocol==='http:'&&!['localhost','127.0.0.1','[::1]'].includes(url.hostname))throw Error('远程服务请使用 HTTPS 地址或本机安全隧道。');
    const root=url.href.replace(/\/$/,'');
    return {async request(suffix,{method='GET',body,query,format='json'}={}) {
      const target=new URL(root+suffix);
      for(const [key,value] of Object.entries(query||{}))if(value!==''&&value!==null&&value!==undefined)target.searchParams.set(key,value);
      let response;
      try { response=await fetcher(target.href,{method,headers:{...(token?{Authorization:'Bearer '+token}:{}),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),cache:'no-store',credentials:'omit',redirect:'error'}); }
      catch { throw Object.assign(Error('连接失败'),{status:0}); }
      let data; try{data=format==='text'&&response.ok?await response.text():await response.json();}catch{throw Object.assign(Error('服务返回不可读取的内容'),{status:response.status||502});}
      if(!response.ok)throw Object.assign(Error('服务请求失败'),{status:response.status,code:typeof data.detail==='string'?data.detail:data.detail?.code||null});
      return data;
    }};
  }
  function assessmentModel(detail) {
    const a=detail.current_assessment;
    if(!a)return {conclusion:'尚未形成案件级判断',freshness:null,covered:0,total:detail.member_count,uncovered:[],sources:[]};
    const state=a.input_freshness?.state||'unverified';
    return {conclusion:a.value?.conclusion||'未提供结论',freshness:state,
      freshnessLabel:{current:'本轮调查依据未变化',stale:'调查依据已更新，需重新调查',unverified:'暂无法核对调查依据'}[state]||'暂无法核对调查依据',
      reasons:(a.input_freshness?.reasons||[]).map(x=>reasons[x]||x),
      covered:(a.members||[]).filter(m=>(detail.members||[]).some(a=>a.alert_id===m.alert_id)).length,
      total:detail.member_count,coverageKnown:!detail.members_truncated&&!a.members_truncated&&a.covers_current_members!==null,uncovered:a.uncovered_current_alert_ids||[],sources:a.sources||[],sourcesTruncated:a.sources_truncated,value:a.value};
  }
  function groupRuns(records) {
    return {active:records.filter(x=>['running','unknown'].includes(x.run.state)),pending:records.filter(x=>x.run.state==='pending_update')};
  }
  function taskPayload(values, selected, existing, caseRevision, operationKey) {
    const nullable=v=>String(v||'').trim()||null;
    const start=nullable(values.window_start),end=nullable(values.window_end);
    if(!!start!==!!end)throw Error('时间窗口应同时填写起点和终点，未知时两项都留空。');
    if(start&&new Date(start)>new Date(end))throw Error('起点不能晚于终点。');
    const objectKeys=String(values.object_keys||'').split('\n').map(x=>x.trim()).filter(Boolean);
    const hasScope=selected.length||objectKeys.length||start||values.state==='completed';
    if(values.state==='completed'&&(!nullable(values.result_text)||!selected.length))throw Error('完成任务须填写确认结果，并明确选择成员告警。');
    if(hasScope&&!selected.length)throw Error('请明确选择确认范围内的成员告警。');
    if(hasScope&&values.kind==='explicit_objects'&&!objectKeys.length)throw Error('按对象确认时至少选择一个对象。');
    let scope=hasScope?{kind:values.kind||'selected_alerts',alert_ids:selected,object_keys:objectKeys,
      window_start:start?new Date(start).toISOString():null,window_end:end?new Date(end).toISOString():null,
      limitations:String(values.limitations||'').split('\n').map(x=>x.trim()).filter(Boolean)}:null;
    const original=existing?.current.result_scope;
    // Preserve immutable confirmation, including timestamp precision and member order,
    // when the user only edits task metadata. A moved member does not alter old facts.
    if(original&&scope&&scope.kind===original.kind&&selected.length===original.alert_ids.length&&selected.every(id=>original.alert_ids.includes(id))
      &&JSON.stringify(scope.object_keys)===JSON.stringify(original.object_keys)&&JSON.stringify(scope.limitations)===JSON.stringify(original.limitations)
      &&sameTimeInput(values.window_start,original.window_start)&&sameTimeInput(values.window_end,original.window_end))scope=JSON.parse(JSON.stringify(original));
    const resultText=existing&&String(values.result_text||'')===String(existing.current.result_text||'')?existing.current.result_text:nullable(values.result_text);
    return {operation_key:operationKey,expected_scope_revision:caseRevision,title:values.title.trim(),description:nullable(values.description),assignee_id:nullable(values.assignee_id),due_at:existing&&sameTimeInput(values.due_at,existing.current.due_at)?existing.current.due_at:values.due_at?new Date(values.due_at).toISOString():null,state:values.state,result_text:resultText,result_scope:scope,
      source_refs:(existing?.current.source_refs||[]).map(({type,id})=>({type,id})),
      ...(existing?{expected_row_version:existing.row_version}:{origin_result_id:nullable(values.origin_result_id),origin_finding_id:null})};
  }
  function taskFactsChanged(body,existing){return !existing||body.result_text!==existing.current.result_text||JSON.stringify(body.result_scope)!==JSON.stringify(existing.current.result_scope)||(body.state==='completed'&&existing.current.state!=='completed');}
  const active = () => new URLSearchParams(location.search).get('data')==='service';
  function start() {
    const state={client:null,queue:null,detail:null,history:null,historyError:'',analysisTasks:null,analysisError:'',tasks:null,run:null,result:null,content:null,revisionPage:null,query:{},queryPage:'cases',activities:null,activityError:'',riskRound:null,riskRoundError:'',incidentRound:null,incidentRoundError:'',recommendationSources:[],otherAssessmentSources:[],resultError:'',loading:false,error:'',notice:'',modal:null,busy:false,epoch:0};
    const risk=window.socai2Risk,recommendations=window.socai2Recommendations,basis=window.socai2Assessment;
    const app=document.querySelector('#app'),I=(name,size=16)=>window.icon(name,size),layout=window.caseWorkspaceLayout;
    const route=()=>{const [p,q='']=location.hash.replace(/^#\/?/,'').split('?'),parts=p.split('/');return {page:parts[0]||'cases',id:parts[1]||'',tab:parts[2]||'case-info',query:new URLSearchParams(q)};};
    const button=(text,action,id='',disabled=false,css='button')=>`<button type="button" class="${css}" data-svc="${action}" data-id="${esc(id)}" ${disabled?'disabled':''}>${({create:'plus',prepare:'sparkles',refresh:'refresh',associate:'plus','new-task':'plus','edit-task':'edit'})[action]?I(({create:'plus',prepare:'sparkles',refresh:'refresh',associate:'plus','new-task':'plus','edit-task':'edit'})[action],15):''}${esc(text)}</button>`;
    const list=(values)=>values?.length?`<ul>${values.map(v=>`<li>${esc(typeof v==='string'?v:v.statement||v.text||v.summary||JSON.stringify(v))}</li>`).join('')}</ul>`:'<p class="muted">未提供</p>';
    const card=(title,body)=>`<section class="iv-card svc-card"><h2>${esc(title)}</h2>${body}</section>`;
    const field=(name,title,value='',type='text')=>`<label class="svc-field">${esc(title)}<input name="${name}" ${type==='datetime-local'?'step="any"':''} type="${type}" value="${esc(value)}" ${name==='title'?'required maxlength="200"':name==='token'?'autocomplete="off"':''}></label>`;
    const area=(name,title,value='')=>`<label class="svc-field">${esc(title)}<textarea name="${name}">${esc(value)}</textarea></label>`;
    const options=(choices,value)=>choices.map(([v,l])=>`<option value="${esc(v)}" ${v===value?'selected':''}>${esc(l)}</option>`).join('');
    const select=(name,title,choices,value='')=>`<label class="svc-field">${title}<select name="${name}">${options(choices,value)}</select></label>`;
    const empty=text=>`<p class="muted">${esc(text)}</p>`;
    const localTime=localInputTime;
    function shell(content) {
      const notices=`${state.notice?`<div class="svc-notice" role="status">${esc(state.notice)}</div>`:''}${state.error?`<div class="svc-error" role="alert">${esc(state.error)} ${button('刷新','refresh')}</div>`:''}`;
      const toolbar=`<span class="environment">服务数据</span>${button('重新连接','disconnect','','', 'button quiet small')}<a class="button quiet small" href="?data=demo#/cases">本地预览</a>${['bell','help','settings'].map(x=>`<button class="icon-button" disabled aria-label="${x==='bell'?'通知':x==='help'?'帮助':'设置'}暂未开放">${I(x,17)}</button>`).join('')}<span class="avatar" title="服务会话">服</span>`;
      return layout.shell({route:route(),service:true,toolbar},notices+content,modal());
    }
    function render() {
      let content;
      if(!state.client)content=`<section class="page cases-queue"><div class="title-line"><h1>Cases</h1></div><article class="card svc-connect"><div class="card-title"><h3>连接调查服务</h3></div><p class="muted">读取与保存服务中的案件。连接凭据仅用于本次页面会话。</p><form data-svc-form="connect">${field('base','服务地址',location.origin+'/api/v1/socai2','url')}${field('token','登录凭据（可信服务可留空）','','password')}<button class="button primary">连接</button></form></article></section>`;
      else if(state.loading)content='<section class="page"><p role="status">正在读取案件记录…</p></section>';
      else {const r=route(); content=r.page==='incidents'?(r.id?incidentView(r):incidentQueueView()):r.page!=='cases'?`<section class="page">${card('此入口暂未开放','<a href="#/cases">返回案件列表</a>')}</section>`:!r.id?queueView():caseView(r);}
      app.innerHTML=shell(content); document.title=(route().page==='incidents'?'事件':'Cases')+' · AiSOC';
    }
    function activityPath(){const r=route();return '/'+r.page+'/'+enc(r.id)+(r.page==='cases'?'/activities':'/records/activities');}
    function analysisTaskView(task){
      if(!task)return empty('任务详情尚未读取，不能据受理回执判断执行结果。');
      const runHref=id=>task.subject_type==='case'?href(task.subject_id,'investigations','run='+enc(id)):risk.runHref('incident',task.subject_id,id);
      const duration=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0?Number(n.toFixed(3))+' 秒':'未记录';
      const at=t=>t?date(t):'未记录';
      const pairs=rows=>rows.map(([k,v])=>`<p><strong>${esc(k)}</strong>：${esc(v)}</p>`).join('');
      const latest=task.attempts?.at(-1),step=task.active_step;
      const phase=task.status==='running'?(!latest?.run_id?'准备阶段，尚无 Run/步骤记录。':step?'当前步骤：'+step.name:'正在执行，尚无活动步骤记录。'):
        task.status==='accepted'?(task.next_retry_at?'等待重试；预约时间不保证实际启动。':'已受理，等待执行。'):
        latest?.outcome==='unknown'?'本地已停止执行，远端结果仍未知。':'';
      const anomalies=[...new Set([...(task.timing?.anomalies||[]),...(step?.anomalies||[]),...(task.attempts||[]).flatMap(x=>x.timing?.anomalies||[])])];
      return `<article class="svc-record"><h3>分析任务 · ${esc(label(task.status))}</h3><p>${esc({initial:'首次分析',check:'检查更新',rerun:'重新分析'}[task.intent]||task.intent)}</p>${phase?`<p>${esc(phase)}</p>`:''}${task.reason_code?`<p>原因：${esc(task.reason_code)}</p>`:''}
        ${pairs([['受理时间',at(task.submitted_at)],['首次确认入队',at(task.first_enqueued_at)],['最近确认入队',at(task.last_enqueued_at)],['首次开始执行',at(task.started_at)],['本地任务结束',at(task.ended_at)],['服务观察时间',at(task.observed_at)],['总历时',duration(task.timing?.total_seconds)],['当前排队等待',duration(task.timing?.pending_queue_seconds)],['当前重试等待（含排队）',duration(task.timing?.retry_wait_seconds)],['下次重试预约',at(task.next_retry_at)]])}
        ${task.execution_shared?empty('历史合并请求：尝试及步骤来自共享执行，受理与入队保留原请求记录。'):''}
        ${step?pairs([['当前步骤',step.name],['步骤开始',at(step.started_at)],['步骤已执行',duration(step.elapsed_seconds)]]):''}
        ${task.attempts?.length?task.attempts.map(x=>`<section><p>尝试 ${x.attempt_no} · ${esc(task.status==='skipped'&&!x.run_id&&x.outcome==='completed'?'检查已结束':label(x.outcome||x.local_state))}${x.run_id?` · <a href="${runHref(x.run_id)}">查看实际Run</a>`:task.status==='skipped'&&x.outcome==='completed'?' · 任务已跳过，未创建 Run；不表示分析成功。':x.local_state==='running'?' · 正在准备，尚无关联 Run。':' · 未创建 Run，保留准备/错误记录。'}</p>${pairs([['本次确认入队',at(x.enqueued_at)],['本次开始',at(x.started_at)],['本地尝试结束',at(x.local_ended_at)],['中断观察时间',at(x.interruption_observed_at)],['本次排队耗时',duration(x.timing?.queue_seconds)],['本次执行耗时',duration(x.timing?.execution_seconds)]])}</section>`).join(''):empty('尚无执行尝试或Run。')}
        ${anomalies.length?`<p role="alert">时间记录异常：${esc(anomalies.join('、'))}；对应耗时未推定为 0。</p>`:''}
        <p class="muted">耗时截至服务观察时间；重试等待包含其中排队区间。任务已结束仅表示流程收尾，交付、结论质量和是否采用以实际结果为准。</p></article>`;
    }
    function analysisTasksView(){
      return card('分析任务',state.analysisError?`<p role="alert">任务读取失败：${esc(state.analysisError)}</p>`:state.analysisTasks?`${state.analysisTasks.items.map(task=>analysisTaskView(task)+button('读取任务详情','analysis-task',task.task_id)).join('')||empty('尚无已受理的分析任务。')}${state.analysisTasks.next_cursor?button('更多分析任务','analysis-more'):''}`:empty('任务目录尚未读取。'));
    }
    async function readAnalysisTask(receipt,kind,id){
      const suffix=analysisTaskPath(receipt,kind,id),task=await read(suffix);
      if(analysisTaskPath(task,kind,id)!==suffix||!['accepted','running','completed','failed','skipped'].includes(task.status))throw Error('任务读回身份或状态不一致。');
      return task;
    }
    async function readAnalysisPage(kind,id,cursor){
      const page=await read('/'+kind+'s/'+enc(id)+'/analysis-tasks',{query:{limit:20,cursor}});
      if(page.subject_type!==kind||page.subject_id!==id||!Array.isArray(page.items))throw Error('任务目录主体不一致。');
      page.items.forEach(task=>analysisTaskPath(task,kind,id));return page;
    }
    async function readAllocatedTasks(m,caseId){
      for(const item of m.targets.filter(x=>!caseId||x.case_id===caseId)){
        try{const detail=await read(path(item.case_id));if(detail.case?.id!==item.case_id)throw Error('案件读回身份不一致。');const task=item.initial_task?await readAnalysisTask(item.initial_task,'case',item.case_id):null;if(state.modal!==m)return;m.reads[item.case_id]={detail,task};}
        catch(error){if(error.obsolete||state.modal!==m)return;m.reads[item.case_id]={error:error.status!==undefined?errorMessage(error):error.message};}
      }
    }
    function activityView(){const r=route();return card('等级与优先级变化',`${state.activityError?`<p role="alert">活动读取失败：${esc(state.activityError)}；未将失败显示为无记录。</p>`:risk.timeline(r.page==='cases'?'case':'incident',r.id,state.activities)}${state.activities?.next_offset!=null?button('更多活动','risk-history-more'):''}`);}
    function incidentQueueView(){
      const q=state.queue;if(!q)return `<section class="page">${empty('事件列表未读取。')}</section>`;
      return `<section class="page"><div class="title-line"><h1>事件</h1>${button('刷新','refresh')}${button('导出当前筛选','export')}</div><form data-svc-form="filter"><div class="svc-filters">${field('q','搜索事件',state.query.q)}${select('severity','严重程度',[['','全部'],...['critical','high','medium','low','info'].map(v=>[v,label(v)])],state.query.severity)}${select('sort_by','排序字段',[['last_activity_at','活动时间'],['severity','严重程度']],state.query.sort_by||'last_activity_at')}${select('sort_order','排序方向',[['desc','降序'],['asc','升序']],state.query.sort_order||'desc')}<button class="button">应用筛选</button>${button('重置筛选','clear-filter')}</div></form><p>${q.total} 个事件</p><div class="svc-table"><table class="data-table"><thead><tr><th>事件</th><th>当前严重程度</th><th>等级来源</th><th>当前优先级</th><th>等级更新时间</th></tr></thead><tbody>${q.items.map(d=>{const x=risk.current('incident',d);return `<tr><td><a href="#/incidents/${enc(d.facts.id)}/case-info">${esc(d.facts.title)}</a></td><td>${severity(x.level)}</td><td>${esc(risk.source(x.source))}</td><td>${esc(x.priority??'未记录')}</td><td>${date(x.risk?.current?.updated_at)}</td></tr>`;}).join('')||'<tr><td colspan="5">没有符合筛选的事件。</td></tr>'}</tbody></table></div>${button('首页','queue-first','',!state.query.cursor)}${button('下一页','queue-next','',!q.next_cursor)}</section>`;
    }
    function incidentView(r){
      const d=state.detail;if(!d)return `<section class="page">${empty('事件未读取。')}</section>`;
      const f=d.facts,entries=state.history?.items||[];
      return `<section class="page"><nav class="breadcrumbs"><a href="#/incidents">事件</a></nav><div class="title-line"><h1>${esc(f.title)}</h1>${button('管理等级与优先级','manage-risk')}${button('检查并更新诊断','prepare')}${button('重新诊断','rerun')}${button('刷新','refresh')}</div>${risk.panel('incident',d)}<nav class="svc-actions"><a href="#/incidents/${enc(f.id)}/case-info">事件属性</a><a href="#/incidents/${enc(f.id)}/activities">变化时间线</a><a href="#/incidents/${enc(f.id)}/investigations">调查轮次</a></nav>${r.tab==='activities'?activityView():r.tab==='investigations'?`${analysisTasksView()}${card('调查轮次',state.historyError?`<p role="alert">轮次目录读取失败：${esc(state.historyError)}</p>`:entries.map(x=>`<p><a href="${risk.runHref('incident',f.id,x.run_id)}">${date(x.started_at||x.requested_at)} · ${esc(label(x.state))}</a></p>`).join('')||empty('尚无执行轮次。'))}${state.history?.next_cursor?button('更多轮次','incident-runs-more'):''}${r.query.has('run')?incidentRoundView()+risk.roundPanel(state.riskRound,state.riskRoundError):''}`:card('事件属性',`<p>处理状态：${esc(label(f.handling_status))}</p><p>${esc(f.description||'未提供事件说明')}</p>${basis.verdict(d.business_verdict)}<p>成员来源最高等级：${esc(risk.level(d.derived?.severity_auto))}（来源汇总）</p>`)}</section>`;
    }
    function incidentRoundView(){
      if(state.incidentRoundError)return card('诊断结果',`<p role="alert">诊断读取失败：${esc(state.incidentRoundError)}</p>`);
      const entry=state.incidentRound;
      const result=entry?.result;
      const reason=result?.error_code||entry?.run?.stop_reason;
      const failure=entry?.run?.state==='failed'?`<p role="status">本轮诊断失败${reason?' · '+esc(reason):''}</p>`:'';
      return card('本轮诊断',failure+(result?`${basis.verdict(result.business_verdict)}<p>${esc(result.diagnosis?.conclusion??result.summary??'本轮暂无诊断正文')}</p>`:empty('本轮尚未保存诊断。')));
    }
    function queueView() {
      const q=state.queue;if(!q)return `<section class="page">${empty('尚未读取到案件。')}</section>`;
      const columns=['案件名称','Case ID','优先级评分','创建时间','负责人','严重程度','等级来源','等级更新时间','状态','标签','成员告警','人工待办','最近更新时间'];
      const rows=q.items.map(row=>{const c=row.case;return `<tr><td><a class="incident-name" href="${href(c.id)}">${esc(c.title)}</a></td><td><span class="svc-id">${esc(c.id)}</span></td><td><span class="priority-pill">${esc(c.priority_value??'—')}</span></td><td>${date(c.created_at)}</td><td>${esc(c.owner_id||c.owner_source_value||(c.assignment_state==='unassigned'?'未分配':'未知'))}</td><td>${severity(c.severity)}</td><td>${esc(risk.source(c.risk?.current?.source||c.severity_source))}</td><td>${date(c.risk?.current?.updated_at)}</td><td>${status(c.handling_status)}</td><td>${(c.tags||[]).map(t=>`<span class="badge">${esc(t)}</span>`).join(' ')||'—'}</td><td>${row.member_count}</td><td>${row.open_task_count}</td><td>${date(c.business_updated_at)}</td></tr>`;}).join('');
      return `<section class="page cases-queue"><div class="title-line"><h1>Cases</h1><div class="page-top-actions"><button class="button quiet" disabled>${I('settings',15)}案件管理设置暂未开放</button></div></div><div class="case-metrics-heading"><span>待处理案件概况</span><span class="muted">本租户有权读取的全部案件，不随表格筛选或分页变化</span></div><div class="case-queue-metrics" aria-label="案件快捷筛选">${Object.entries(metrics).map(([key,title])=>`<button type="button" class="case-list-metric ${state.query.metric===key?'selected':''}" data-svc="metric" data-id="${key}" aria-pressed="${state.query.metric===key}"><span class="case-metric-title">${title}</span><span class="case-metric-value"><b>${q.metrics[key]??'—'}</b><small>个案件</small><span class="spacer"></span>${I('chevron',16)}</span></button>`).join('')}</div><div class="table-card" data-table="cases"><form data-svc-form="filter"><div class="toolbar case-queue-toolbar">${button('创建','create','','','button quiet')}${button('刷新','refresh','','','button quiet')}${button('导出当前筛选','export','','','button quiet')}<span class="spacer"></span><span class="table-tools-count">${q.total} 个案件</span><label class="search-input">${I('search',15)}<input type="search" name="q" value="${esc(state.query.q)}" placeholder="搜索" aria-label="搜索案件名称或完整 ID"></label><button class="button quiet">搜索</button></div><details class="svc-queue-filters"><summary class="filterbar case-filterbar">${I('filter',15)}筛选案件 <span class="muted">${Object.entries(state.query).filter(([k,v])=>v&&!['cursor','q'].includes(k)).length?'已应用筛选':'全部'}</span></summary><div class="svc-filters">${select('handling_status','处理状态',[['','全部'],['new','新建'],['in_progress','处理中'],['resolved','已解决'],['unknown','未知']],state.query.handling_status)}${select('severity','严重程度',[['','全部'],...['critical','high','medium','low','info'].map(x=>[x,label(x)])],state.query.severity)}${select('sort_by','排序字段',[['','默认'],['severity','严重程度'],['business_updated_at','更新时间']],state.query.sort_by)}${select('sort_order','排序方向',[['desc','降序'],['asc','升序']],state.query.sort_order||'desc')}${select('assignment_state','分配状态',[['','全部'],['unassigned','未分配'],['assigned','已分配'],['unresolved','负责人未知']],state.query.assignment_state)}${field('owner_id','负责人 ID（可选）',state.query.owner_id)}<button class="button">应用筛选</button>${button('重置全部','clear-filter','','','button quiet small')}</div></details></form><div class="table-scroll"><table class="data-table"><thead><tr>${columns.map(c=>`<th scope="col">${c}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table>${!q.items.length?empty('没有符合条件的案件。'):''}</div><div class="table-footer"><span>本页 ${q.items.length} 项 / ${q.total} 个匹配案件</span><div class="row">${button('返回首页','queue-first','',!state.query.cursor,'button quiet small')}${button('下一页','queue-next','',!q.next_cursor,'button quiet small')}</div></div></div></section>`;
    }
    function severity(value){return `<span class="severity"><span class="severity-bars ${['critical','high'].includes(value)?'high':value==='medium'?'medium':value==='low'?'low':''}"><i></i><i></i><i></i></span>${esc(label(value))}</span>`;}
    function status(value){return `<span class="state"><i class="dot ${value==='resolved'?'Resolved':value==='in_progress'?'In-progress':value==='new'?'New':''}"></i>${esc(value==='unknown'?'未知':label(value))}</span>`;}
    function runCard(record) {const r=record.run;return `<article class="iv-card iv-run-link"><div class="row wrap"><span class="badge ${r.state==='unknown'?'amber':'blue'}">${esc(label(r.state))}</span><span class="muted">${date(r.started_at||r.requested_at)}</span></div><h3><a href="${href(r.case_id,'investigations','run='+enc(r.id))}">${esc(r.title)}</a></h3><p>${esc(r.purpose||'本轮目的未提供')}</p>${r.state==='pending_update'?empty('尚未执行；请按分析任务的实际状态查看进展。'):''}</article>`;}
    function adoptedSources(d){
      const sources=state.recommendationSources||[],assessment=d.current_assessment;
      return `<section class="svc-adopted-recommendations svc-adopted-basis"><h3>当前采用来源的依据与建议</h3><p class="muted">按当前判断引用的保存来源分别展示；保留原范围，建议不代表已批准或执行。</p>${assessment?basis.coverage(assessment.members,assessment.members_truncated):''}${sources.map(source=>`<article class="saved-recommendation assessment-source"><p class="recommendation-source"><a href="${href(d.case.id,'investigations','result='+enc(source.id)+'&view=report')}">查看来源结果</a> · ${esc(source.id)}</p>${source.error?`<div role="alert">来源读取失败：${esc(source.error)} ${button('重试读取','refresh','','','button small')}</div>`:`<p class="muted recommendation-source">来源轮次：${esc(source.result.source_run_id)}</p>${basis.render(source.result)}<h4>来源结果中的建议</h4>${recommendations.render(source.result.recommendations)}`}</article>`).join('')||empty(assessment?'当前判断未引用Result；不能从其他轮次补值。':'尚未采用案件判断。')}${basis.otherSources(assessment?.sources,state.otherAssessmentSources)}${state.otherAssessmentSources.some(x=>x.error)?button('重试读取来源','refresh','','','button small'):''}${assessment?.sources_truncated?empty('采用来源目录已截断，仅展示已读取的来源。'):''}</section>`;
    }
    function assessmentView(d){
      const c=d.case,a=assessmentModel(d),times=d.members.map(m=>m.event_time).filter(Boolean).sort();
      return `<div class="case-assessment"><p class="case-description">${esc(c.description||'未提供案件说明')}</p><div class="case-assessment-heading"><span>当前案件判断</span></div><h3>${esc(a.conclusion)}</h3>${d.current_assessment?basis.verdict(d.current_assessment.business_verdict):''}${a.freshness?`<p class="iv-note">形成于 ${date(a.value.formed_at)} · ${a.coverageKnown?'适用 '+a.covered+' / '+a.total+' 条当前成员告警':'完整覆盖尚无法核对'}</p><p class="svc-basis ${esc(a.freshness)}">${esc(a.freshnessLabel)}</p>${a.reasons.length?list(a.reasons):''}<p class="iv-note">仅比较已跟踪依据，不保证外部数据全部最新或判断正确。</p>${a.uncovered.length?`<details><summary>未覆盖的成员 (${a.uncovered.length})</summary>${list(a.uncovered)}</details>`:''}<div class="case-assessment-sources">${a.sources.filter(x=>x.result_id).map(x=>`<a href="${href(c.id,'investigations','result='+enc(x.result_id))}">${I('file',12)} 查看判断来源</a>`).join('')}</div>${a.sourcesTruncated?empty('判断来源目录已截断。'):''}`:'<p class="iv-note">已有材料仍可查看，尚未保存案件级判断。</p>'}<div class="case-activity-range"><span>告警活动范围</span><span>${times.length?date(times[0])+' — '+date(times.at(-1)):'发生时间未记录'}</span></div><div class="row wrap"><a class="button primary" href="${href(c.id,'overview')}">${I('sparkles',15)}查看调查结果</a>${a.freshness&&a.freshness!=='current'?button('检查并更新调查','prepare','',state.busy||c.handling_status==='resolved'||!d.member_count):''}<button class="button" disabled>${I('clock',15)}案件故事暂未开放</button></div>${adoptedSources(d)}</div>`;
    }
    function caseInfoView(d){
      const c=d.case,info=(title,value)=>`<div><span class="info-label">${title}</span><div class="info-value">${value}</div></div>`;
      return `<div class="case-context-home"><div class="case-summary-metrics">${[['成员告警',d.member_count,'alerts'],['涉及对象','—',null],['告警证据','—',null],['调查记录',state.history?.items.length+(state.history?.next_cursor?'+':'')||'—','investigations']].map(([title,n,tab])=>tab?`<a class="card" href="${href(c.id,tab)}"><span class="muted">${title}</span><b>${n}</b></a>`:`<div class="card" title="暂未提供统计"><span class="muted">${title}</span><b>${n}</b></div>`).join('')}</div><div class="case-overview-grid"><div class="stack"><article class="copilot-card"><div class="copilot-title"><span class="copilot-icon">${I('sparkles',21)}</span>案件资料摘要</div>${assessmentView(d)}</article><article class="card"><div class="card-title"><h3>成员告警</h3><span class="spacer"></span><a href="${href(c.id,'alerts')}">查看全部</a></div>${d.members.slice(0,4).map(m=>`<div class="entity-list-item">${I('shield',17)}<div style="flex:1;min-width:0">${esc(m.title)}<small class="muted" style="display:block;margin-top:5px">${date(m.event_time)}</small></div>${severity(m.severity)}</div>`).join('')||empty('暂无成员告警')}</article></div><aside class="stack"><article class="card"><div class="card-title"><h3>Case 详细信息</h3></div><div class="info-grid">${info('Case ID',`<span class="svc-id">${esc(c.id)}</span>`)}${info('处理状态',status(c.handling_status))}${info('负责人',esc(c.owner_id||c.owner_source_value||(c.assignment_state==='unassigned'?'未分配':'未知')))}${info('严重程度',severity(c.severity))}${info('等级来源',esc(risk.source(c.risk?.current?.source||c.severity_source)))}${info('创建时间',date(c.created_at))}${info('最近更新',date(c.business_updated_at))}${info('关联事件',d.linked_incidents.map(x=>esc(x.title||x.incident_id)).join('<br>')||'未关联')}${info('结案说明',esc(c.resolution_note||'—'))}</div><div style="margin-top:20px">${button('管理等级与优先级','manage-risk','','','button small')}</div></article><article class="card"><div class="card-title"><h3>人工跟进</h3></div><p class="muted">人工确认保存后，可明确提交检查更新；是否产生新Run由任务实际结果决定。</p><a class="card-link" href="${href(c.id,'tasks')}">查看人工任务 ${I('chevron',12)}</a></article></aside></div></div>`;
    }
    function overviewView(d){
      const g=groupRuns(d.baseline_records),rows=state.history?.items||[];
      return `<div class="iv-root iv-case-home"><div class="iv-heading"><div><h2>调查概览</h2><p>查看调查进展、已有结果和待确认事项。</p></div><div class="svc-actions">${button('检查并更新调查','prepare','',state.busy||d.case.handling_status==='resolved'||!d.member_count,'button small')}${button('重新调查','rerun','',state.busy||d.case.handling_status==='resolved'||!d.member_count,'button small')}</div></div>${analysisTasksView()}<div class="svc-run-sections"><section><h3>正在执行 / 状态待核实</h3>${g.active.length?g.active.map(runCard).join(''):empty('当前没有活跃调查。')}</section><section><h3>尚未执行的Run</h3>${g.pending.length?g.pending.map(runCard).join(''):empty('没有未执行Run；尚无Run的受理请求请查看分析任务。')}</section></div><div class="iv-case-scope"><a href="${href(d.case.id,'alerts')}">当前成员 <b>${d.member_count}</b> 条</a><span>已读取调查记录 <b>${rows.length}${state.history?.next_cursor?'+':''}</b> 次</span></div><p class="iv-case-context">各轮结果保留原始输入范围；当前成员变化不会改写历史调查。</p><div class="iv-case-overview-grid"><section class="iv-stack" aria-label="已有分析结果">${rows.filter(x=>x.result).slice(0,3).map(x=>`<article class="iv-card iv-case-result"><h3>${esc(x.result.conclusion_origin==='model'?x.result.conclusion||'未提供结论':'系统交接：'+x.result.closing_note)}</h3><p class="iv-outcome-purpose">${esc(x.result.purpose)}</p><p class="iv-result-change">${esc(x.result.change_summary||'未提供比较')}</p><div class="iv-foot"><span>${esc(label(x.result.delivery_state))} · ${date(x.recorded_at)}</span><a href="${href(d.case.id,'investigations','result='+enc(x.result.id))}">查看本轮结果 ${I('chevron',12)}</a></div></article>`).join('')||card('尚无正式结果',empty('可查看成员告警与调查执行记录。'))}<a class="iv-history-entry" href="${href(d.case.id,'investigations')}">查看全部调查历史 ${I('chevron',12)}</a></section><aside>${card('当前调查依据',assessmentView(d))}${card('人工跟进',`<p>人工结果单独保存，不自动改写案件判断。</p><a href="${href(d.case.id,'tasks')}">查看人工任务</a>`)}</aside></div></div>`;
    }
    function caseView(r) {
      const d=state.detail;if(!d)return `<section class="page">${empty('未读取到案件。')}</section>`;const c=d.case;
      const directory=[['case-info','案件资料','file'],['story','案件故事','clock'],['overview','调查概览','search'],['investigations','调查历史','clock'],['alerts','成员告警','shield',d.member_count],['attack','案件关系图','graph'],['evidence','对象与证据','file'],['tasks','人工任务','check'],['activities','处理活动','clock'],['comments','评论与附件','comment']];
      const disabled=['story','attack','evidence','comments'];
      const content=r.tab==='activities'?activityView():r.tab==='tasks'?taskView():r.tab==='alerts'?memberView():r.tab==='investigations'?historyView():r.tab==='overview'?overviewView(d):r.tab==='case-info'?caseInfoView(d):card('此功能暂未开放','<p>可从调查历史查看已保存的结果与材料。</p>');
      const header=`<header class="page-header"><nav class="breadcrumbs" aria-label="面包屑"><a href="#/cases">Cases</a>${I('chevron',10)}<span>${esc(c.title)}</span></nav><div class="title-line"><h1>${esc(c.title)}</h1><div class="page-top-actions">${button('添加告警 / 事件','associate')}<button class="button primary" disabled>${I('sparkles',15)}AI问答暂未开放</button>${button('刷新','refresh','','','button quiet small')}<a class="icon-button" href="#/cases" aria-label="切换 Case">${I('list',17)}</a></div></div><div class="metadata">${c.priority_value!=null?`<span class="row"><b class="priority">${esc(c.priority_value)}</b><span class="muted">优先级评分</span></span>`:''}<span>${severity(c.severity)}</span><span>${status(c.handling_status)}</span><span class="row">${I('user',15)}${esc(c.owner_id||c.owner_source_value||(c.assignment_state==='unassigned'?'未分配':'未知'))}</span>${d.linked_incidents.slice(0,2).map(x=>`<span class="badge">关联事件 · ${esc(x.title||x.incident_id)}</span>`).join('')}</div></header>`;
      return layout.caseFrame(header+risk.panel('case',d),layout.caseNavigation(c.id,r.tab==='investigations'&&(r.query.has('run')||r.query.has('result'))?'overview':r.tab,directory,disabled),content);
    }
    function resultContent(result){
      if(!result)return state.resultError?card('结果读取失败',`<div role="alert">${esc(state.resultError)} ${button('重试读取','refresh')}</div><p>未据此判定没有建议。</p>`):card('尚未保存正式结果',empty('请根据本轮执行状态查看已保存的步骤与材料。'));
      const x=result.result;
      return card('本轮结果',`<h3>${esc(x.conclusion_origin==='model'?x.conclusion||'未提供模型结论':'系统交接：'+x.closing_note)}</h3>${basis.verdict(x.business_verdict)}<p class="iv-outcome-purpose">目的：${esc(x.purpose)}</p><div class="iv-foot"><span class="badge ${x.delivery_state==='partial'?'amber':''}">${esc(label(x.delivery_state))}</span><span>${date(x.created_at)}</span></div><h3>变化</h3><p>${esc(x.change_summary||'未提供比较')}</p>${basis.render(x)}<p>交付成员：${result.member_count}</p><details><summary>逐成员交付范围</summary>${json(result.members)}${result.members_truncated?empty('交付成员目录已截断。'):''}</details><h3>本轮建议</h3>${recommendations.render(x.recommendations)}`);
    }
    function executionSummaryView(summary){
      if(!summary)return '<details><summary>本轮能力与限制</summary><p class="muted">未提供本轮能力快照，不能按当前配置推断历史执行能力。</p></details>';
      if(summary.availability!=='available')return `<details><summary>本轮能力与限制</summary><p class="muted">本轮能力快照目前不可读取：${esc(summary.availability||'未提供')}</p></details>`;
      const messages={four_domains_share_one_model_pass:'四个分析视角共用一次模型分析，不表示四个独立调查执行器。','200_members_storage_limit_not_model_capacity_promise':'200 条成员是保存上限，不保证能在单轮中完成全部分析。',host_time_bindings_not_row_to_alert_attribution:'主机与时间窗口匹配不等于每条返回记录都属于某条告警。',enabled_sources_checked_again_before_C3_and_dispatch:'查询能力会在分析前和实际执行前再次核对，启动时可用不等于已经查询。',authentication_requires_frozen_source_hostname:'认证查询需要冻结的来源主机名，缺少主机时无法绑定此类查询。',product_host_details_requires_explicit_crowdstrike_connector:'产品主机详情需要明确的 CrowdStrike 来源连接。',conservative_wire_units_not_provider_token_usage:'输入容量估算与模型实际报告的 tokens 分别记录。',no_automatic_successor_retry_or_task_creation:'不会自动接续下一轮、重试或创建人工任务。',graph_uses_retained_sources_only:'关系图仅使用本轮保留的来源材料。'};
      const toolNames={process_activity:'进程活动',network_connections:'网络连接',authentication_activity:'认证活动',product_host_details:'产品主机详情'},cap=summary.capabilities;
      return `<details><summary>本轮能力与限制</summary>${cap?`<p>启动时可提供的查询：${Array.isArray(cap.offered_tools_at_start)?cap.offered_tools_at_start.length?cap.offered_tools_at_start.map(x=>esc(toolNames[x]||x)).join('、'):'无':'未提供'}</p><p>已绑定查询范围：${cap.binding_count??'未提供'}</p>${list([...(cap.limitations||[]),...(cap.unsupported||[])].map(x=>messages[x]||x))}`:empty('未提供本轮能力范围。')}${list((summary.limitations||[]).map(x=>messages[x]||x))}<details><summary>执行配置原记录</summary>${json({capabilities:summary.capabilities??null,limits:summary.limits??null,final_reservation:summary.final_reservation??null})}</details>${button('查看冻结执行计划','artifact',summary.artifact_id,false,'button small')}</details>`;
    }
    function runWorkbench(){
      const x=state.run,r=x.run,c=state.detail.case,requested=route().query.get('view'),view=['overview','process','tools','graphs','report'].includes(requested)?requested:requested==='ledger'?'process':'overview';
      const runLink=(id,tab)=>href(c.id,'investigations','run='+enc(id)+'&view='+tab);
      let body;
      if(view==='overview')body=resultContent(state.result);
      else if(view==='process')body=card('AI 分析',`<p>冻结成员 ${x.input_member_count} · 当前成员 ${x.current_member_count}</p><div class="iv-inline-metrics"><span>模型调用 ${x.usage.model_calls}</span><span>tokens ${x.usage.total_tokens===null?'已知 '+x.usage.known_total_tokens+'，另有 '+x.usage.unknown_token_calls+' 次用量未知':x.usage.total_tokens}</span><span>查询 ${x.tool_calls}</span></div><h3>执行步骤</h3>${x.steps.map(t=>`<details class="trace-step"><summary><span>${esc(t.stage_code)} · ${esc(t.name)}</span><span>${esc(label(t.state))}</span></summary><p>开始 ${date(t.started_at)} · 结束 ${date(t.ended_at)}</p>${t.input_artifact_id?button('查看输入','artifact',t.input_artifact_id):''}${t.output_artifact_id?button('查看输出','artifact',t.output_artifact_id):''}${t.reused_artifact_id?button('查看复用材料','artifact',t.reused_artifact_id):''}${t.error?json(t.error):''}</details>`).join('')}${x.steps_truncated?empty('步骤目录已截断。'):''}${executionSummaryView(x.execution_summary)}`);
      else if(view==='tools')body=card('查询与证据',`<p>查询 ${x.tool_calls} 次 · 材料保留本轮冻结范围，不等同于已确认的恶意证据。</p><details><summary>本轮冻结成员及读取状态</summary>${json(x.members)}${x.members_truncated?empty('冻结成员目录已截断。'):''}</details><h3>已保存材料</h3><div class="svc-actions">${x.artifacts.map(a=>button(a.kind+' · '+date(a.captured_at),'artifact',a.id)).join('')}${x.members.filter(m=>m.material_id).map(m=>button('冻结告警材料','material',m.material_id)).join('')}</div>${x.artifacts_truncated?empty('材料目录已截断。'):''}`);
      else if(view==='graphs')body=card('调查关系图暂未开放',empty('已保存的原始关系材料可在“查询与证据”核对，当前没有可用的探索保存操作。'));
      else body=resultContent(state.result)+card('报告与响应',`${state.result?.result.report_artifact_id?button('查看已保存报告','artifact',state.result.result.report_artifact_id):empty('未保存独立报告材料。')}<div class="svc-actions"><button class="button" disabled>响应执行暂未开放</button><button class="button" disabled>探索保存暂未开放</button></div>`);
      const runs=[...(state.history?.items||[]).map(x=>x.run),r].filter((x,i,all)=>all.findIndex(y=>x.id===y.id)===i);
      return `<div class="iv-root"><div class="iv-heading"><div><h2>调查详情</h2><p>查看关键发现、分析依据与后续处理。</p></div><a class="button" href="${href(c.id,'overview')}">返回调查概览</a></div><div class="iv-run-selector"><label for="svc-run">当前调查</label><select id="svc-run" data-svc-run>${runs.map(x=>`<option value="${esc(x.id)}" ${x.id===r.id?'selected':''}>${esc(x.title)} · ${esc(label(x.delivery_state))}</option>`).join('')}</select><span class="badge">${esc(label(r.state))}</span><span class="badge ${r.delivery_state==='partial'?'amber':''}">${esc(label(r.delivery_state))}</span></div><div class="cw-run-actions"><button class="button small" disabled>${I('sparkles',15)}AI问答暂未开放</button>${button('添加人工任务','new-task','','','button small')}<button class="button small" disabled>到案件图探索暂未开放</button></div>${r.state==='pending_update'?'<div class="cw-active-banner">本轮尚未执行；请查看分析任务的实际进展。</div>':''}${analysisTasksView()}${r.stop_reason?`<div class="iv-result-limits"><b>${esc(r.stop_reason)}</b><p>${esc(r.stop_detail||'')}</p></div>`:''}<div class="iv-run-title"><h3>${esc(r.title)}</h3><span class="iv-note">${x.input_member_count} 条输入告警 · ${date(r.started_at||r.requested_at)}</span></div><nav class="iv-tabs" aria-label="调查运行内容">${[['overview','调查发现'],['process','AI 分析'],['tools','查询与证据'],['graphs','调查关系图'],['report','报告与响应']].map(([key,title])=>`<a href="${runLink(r.id,key)}" ${view===key?'aria-current="page"':''} class="${view===key?'active':''}">${title}</a>`).join('')}</nav>${risk.roundPanel(state.riskRound,state.riskRoundError)}${body}</div>`;
    }
    function historyView() {
      if(state.run)return runWorkbench();
      const c=state.detail.case,rows=state.history?.items||[];
      return `<div class="iv-root"><div class="iv-heading"><div><h2>调查历史</h2><p>查看每轮结果、输入范围与执行用量。</p></div></div>${analysisTasksView()}${rows.map(x=>`<article class="iv-card iv-run-link"><div class="row wrap"><span class="badge">${esc(label(x.run.state))}</span><span class="badge ${x.run.delivery_state==='partial'?'amber':''}">${esc(label(x.run.delivery_state))}</span></div><h3>${esc(x.run.title)}</h3><p>${esc(x.run.purpose)}</p>${x.result?`<p>${esc(x.result.conclusion_origin==='model'?x.result.conclusion||x.result.closing_note:'系统交接：'+x.result.closing_note)}</p>`:empty('尚未保存正式结果。')}<div class="iv-foot"><span>${date(x.recorded_at)}</span><a class="button primary" href="${href(c.id,'investigations',x.result?'result='+enc(x.result.id):'run='+enc(x.run.id))}">打开调查 ${I('external',14)}</a></div></article>`).join('')||empty('暂无调查记录。')}${button('更多历史','history-more','',!state.history?.next_cursor,'button small')}</div>`;
    }
    const json=value=>`<pre class="detail-json">${esc(JSON.stringify(value,null,2))}</pre>`;
    function taskView() {return `<div class="iv-root"><div class="iv-heading"><div><h2>人工任务</h2><p>由人确认业务背景或补充 AI 无法取得的信息。</p></div>${button('添加任务','new-task','','','button primary')}</div><div class="cw-task-list">${(state.tasks?.items||[]).map(t=>{const x=t.current;return `<article class="iv-card"><div class="cw-task-header"><div><h3>${esc(x.title)}</h3><small>${esc(x.assignee_id||'未分配')} · 截止 ${date(x.due_at)}</small></div><div class="cw-task-actions"><span class="badge">${x.state==='completed'?'已完成':esc(label(x.state))}</span>${button('编辑','edit-task',t.id,false,'button small')}${button('历史版本','task-revisions',t.id,false,'button small')}</div></div><p>${esc(x.description||'')}</p><div class="cw-task-result"><b>处理结果</b><p>${esc(x.result_text||'尚未填写结果')}</p></div><p class="iv-note">完成者 ${esc(x.completed_by||'未提供')} · 完成时间 ${date(x.completed_at)}</p><p class="iv-note">修改者 ${esc(x.changed_by)} · 修改时间 ${date(x.changed_at)}</p>${x.result_scope?`<details><summary>已确认范围</summary>${json(x.result_scope)}</details>`:''}</article>`;}).join('')||empty('暂无人工任务。')}</div>${button('更多任务','tasks-more','',state.tasks?.next_offset==null,'button small')}</div>`;}
    function memberView() {return `${button('添加告警 / 事件','associate')}<form data-svc-form="move-select"><div class="svc-table"><table class="data-table"><thead><tr><th>选择</th><th>成员告警</th><th>严重程度</th><th>发生时间</th></tr></thead><tbody>${state.detail.members.map(m=>`<tr><td><input type="checkbox" name="member" value="${esc(m.alert_id)}" aria-label="选择${esc(m.title)}"></td><td>${esc(m.title)}<small class="svc-id">${esc(m.alert_id)}</small></td><td>${esc(label(m.severity))}</td><td>${date(m.event_time)}</td></tr>`).join('')}</tbody></table></div><button class="button">移动所选成员</button></form>${state.detail.members_truncated?empty('成员列表已截断，未展示的成员不作已选处理。'):''}`;}
    function modal() {
      const m=state.modal;if(!m)return '';
      let title='',body='';
      if(m.kind==='risk'){title='管理等级与优先级';body=risk.panel(m.subjectKind,state.detail)+risk.form(m.subjectKind);}
      else if(m.kind==='task'){
        const x=m.task?.current||{},s=x.result_scope||{};title=m.task?'编辑人工任务':'添加人工任务';
        const members=[...state.detail.members];for(const id of s.alert_ids||[])if(!members.some(a=>a.alert_id===id))members.push({alert_id:id,title:'原确认成员（已不在本案）'});
        body=`<form data-svc-form="task">${field('title','任务事项',x.title)}${area('description','工作说明',x.description)}<div class="svc-two">${field('assignee_id','负责人 ID（可选）',x.assignee_id)}${field('due_at','截止时间（可选）',localTime(x.due_at),'datetime-local')}${select('state','状态',[['not_started','未开始'],['in_progress','进行中'],['completed','已完成'],['cancelled','已取消']],x.state||'not_started')}${select('kind','确认范围',[['selected_alerts','所选成员'],['whole_case','明确全案当前成员'],['explicit_objects','所选成员中的对象']],s.kind||'selected_alerts')}</div>${area('result_text','确认 / 处理结果（完成时填写）',x.result_text)}<fieldset><legend>确认哪些成员</legend>${members.map(a=>`<label class="svc-choice"><input type="checkbox" name="scope_member" value="${esc(a.alert_id)}" ${(s.alert_ids||[]).includes(a.alert_id)?'checked':''}>${esc(a.title)} <small>${esc(a.alert_id)}</small></label>`).join('')}</fieldset><p class="muted">全案确认须明确勾选全部当前成员；不会随以后新增成员扩大范围。</p>${area('object_keys','对象键（按对象确认时必填，每行一项）',(s.object_keys||[]).join('\n'))}<div class="svc-two">${field('window_start','事实窗口起点（可选）',localTime(s.window_start),'datetime-local')}${field('window_end','事实窗口终点（可选）',localTime(s.window_end),'datetime-local')}</div><p class="muted">时间未知时两项都留空，无需填造。人工确认保持所声明范围。</p>${area('limitations','范围限制（可选，每行一项）',(s.limitations||[]).join('\n'))}${!m.task?field('origin_result_id','来源结果 ID（可选）',m.originResult||''):''}<div data-svc-form-error role="alert"></div><button class="button primary">明确保存</button>${button('取消','close')}</form>`;
      }else if(m.kind==='analysis'){title=m.subjectKind==='case'?'提交案件调查':'提交事件诊断';body=`<form data-svc-form="analysis">${select('mode','操作',[['check','检查更新：材料有变化时执行'],['rerun','重新分析：明确生成新的分析轮次']],m.mode)}<p>提交只表示请求已受理；实际执行、Run和结果以任务读回为准。</p><div data-svc-form-error role="alert"></div><button class="button primary">明确提交</button>${button('取消','close')}</form>`;}
      else if(m.kind==='analysis-task'){title='分析任务';body=analysisTaskView(m.task)+button('刷新任务','refresh-analysis-task',m.task.task_id);}
      else if(m.kind==='allocation'){title='实际案件分配';body=`<p>成员已保存。新案首轮按已受理任务执行。</p>${m.targets.map(item=>`<article class="svc-record"><a href="${href(item.case_id,'overview')}">打开${item.created?'新建':'已有'}案件${m.reads[item.case_id]?.detail?'：'+esc(m.reads[item.case_id].detail.case.title):''}</a>${m.reads[item.case_id]?.error?`<p role="alert">独立读取失败：${esc(m.reads[item.case_id].error)}</p>`:item.initial_task?analysisTaskView(m.reads[item.case_id]?.task):empty('本项没有新建首轮任务。')}${button('刷新案件与首轮任务','allocation-task',item.case_id)}</article>`).join('')}`;}
      else if(m.kind==='associate'||m.kind==='create'){title=m.kind==='create'?'创建案件':'添加告警 / 事件';body=`<form data-svc-form="${m.kind}">${m.kind==='create'?field('title','案件名称'):''}<p>选择实际纳入的告警或事件。关联不会从其他案件移走成员。</p><h3>告警</h3><div id="svc-alert-options">${picker(m.alerts,'alert')}</div>${button('更多告警','more-alerts','',!m.alerts?.next_before_id)}<h3>事件</h3><div id="svc-incident-options">${picker(m.incidents,'incident')}</div>${button('更多事件','more-incidents','',!m.incidents?.next_before_id)}<div data-svc-form-error role="alert"></div><button class="button primary">确认${m.kind==='create'?'创建':'添加'}</button>${button('取消','close')}</form>`;}
      else if(m.kind==='move'){title='移动成员';body=`<p>已选 ${m.members.length} 条告警。两案范围同时保存，历史调查保持。</p><form data-svc-form="move">${select('target','目标案件',m.targets.items.filter(x=>x.case.id!==state.detail.case.id).map(x=>[x.case.id,x.case.title]))}${m.targets.next_cursor?button('更多目标案件','more-targets'):''}<div data-svc-form-error role="alert"></div><button class="button primary">确认移动</button>${button('取消','close')}</form>`;}
      else if(m.kind==='revisions'){title='人工任务历史版本';body=(m.originResult?`<p><a href="${href(state.detail.case.id,'investigations','result='+enc(m.originResult))}">查看原调查结果</a></p>`:'')+(m.page.items||[]).map(x=>`<article class="svc-record"><h3>版本 ${x.revision} · ${esc(x.title)}</h3><p>${esc(x.result_text||'未填写结果')}</p><p>完成者 ${esc(x.completed_by||'未提供')} · ${date(x.completed_at)}</p><details><summary>当时范围、参考与修改记录</summary>${json(x)}</details></article>`).join('')+button('更多版本','more-revisions','',m.page.next_offset==null);}
      else {title=m.title||'保存的调查材料';body=`<p>${esc(m.availability||'')}</p>${m.text!=null?`<pre class="detail-json">${esc(m.text)}</pre>`:json(m.data)}`;}
      return `<div class="modal-backdrop svc-modal-backdrop"><section class="modal svc-modal" role="dialog" aria-modal="true" aria-label="${esc(title)}"><div class="svc-actions"><h2>${esc(title)}</h2>${button('关闭','close')}</div>${body}</section></div>`;
    }
    function picker(page,kind){return(page?.items||[]).map(x=>`<label class="svc-choice"><input type="checkbox" name="${kind}" value="${esc(x.facts.id)}">${esc(x.facts.title)} <small>${esc(x.facts.id)}</small></label>`).join('')||empty('本页没有可选记录。');}
    async function read(suffix,options) {
      const epoch=state.epoch,client=state.client;
      const response=await client.request(suffix,options);
      if(epoch!==state.epoch||client!==state.client)throw Object.assign(Error('页面已切换'),{obsolete:true});
      return response;
    }
    async function load() {
      if(!state.client)return render(); const epoch=++state.epoch,r=route();if(state.queryPage!==r.page){state.query={};state.queryPage=r.page;}state.riskRound=null;state.riskRoundError='';state.incidentRound=null;state.incidentRoundError='';state.activityError='';state.historyError='';state.analysisTasks=null;state.analysisError='';state.activities=null;state.recommendationSources=[];state.otherAssessmentSources=[];state.resultError='';state.loading=true;state.error='';render();
      try {
        if(r.page==='incidents'&&!r.id)state.queue=await read('/incidents',{query:{limit:20,...state.query}});
        else if(r.page==='incidents'){
          state.detail=await read('/incidents/'+enc(r.id));if(state.detail.facts?.id!==r.id)throw Error('主体详情身份不一致。');
          state.history=null;try{state.history=await read('/analysis-runs',{query:{subject_type:'incident',subject_id:r.id}});}catch(e){if(e.obsolete)throw e;state.historyError=e.message;}
          if(r.query.has('run')){
            const runId=r.query.get('run');
            try{
              const entry=await read(`/incidents/${enc(r.id)}/analysis/runs/${enc(runId)}`);
              // The incident-scoped endpoint checks subject ownership before returning a StageRunView.
              if(entry.run?.id!==runId||entry.run.kind!=='incident_diagnosis'||
                (entry.result&&entry.result.source_run_id!==runId))throw Error('诊断不属于所选事件或轮次。');
              state.incidentRound=entry;
            }catch(e){if(e.obsolete)throw e;state.incidentRoundError=e.message;}
            if(state.incidentRound){
              try{state.riskRound=await risk.round(read,'incident',r.id,runId,state.incidentRound);}
              catch(e){if(e.obsolete)throw e;state.riskRoundError=e.message;}
            }
          }
        }else if(r.page==='cases'&&!r.id)state.queue=await read('/cases',{query:{limit:20,...state.query}});
        else if(r.page==='cases'){
          const detail=await read(path(r.id)); if(epoch!==state.epoch)return;if(detail.case?.id!==r.id)throw Error('主体详情身份不一致。');state.detail=detail;state.run=null;state.result=null;
          if(r.tab==='tasks')state.tasks=await read(path(r.id,'/tasks'),{query:{limit:20}});
          if(['case-info','overview','investigations'].includes(r.tab)){
            state.history=await read(path(r.id,'/history'),{query:{limit:20}});
            if(['case-info','overview'].includes(r.tab)){
              const sources=await Promise.all(recommendations.resultSources(detail.current_assessment).map(async source=>{
                try{
                  const value=await read(path(r.id,'/results/'+enc(source.result_id)));
                  return {id:source.result_id,result:recommendations.checkResult(value,{caseId:r.id,resultId:source.result_id})};
                }catch(error){if(error.obsolete)throw error;return {id:source.result_id,error:error.message};}
              }));
              if(epoch!==state.epoch)return;state.recommendationSources=sources;
              const references=[...new Map((detail.current_assessment?.sources||[]).filter(x=>!x.result_id).map(x=>[basis.sourceKey(x),x])).values()];
              const other=await Promise.all(references.map(async source=>{
                try{
                  if(source.assessment_id&&source.assessment_id!==detail.current_assessment.value.id)throw Error('来源不属于当前采用记录。');
                  const value=await read(basis.sourcePath(r.id,source));
                  return {source,data:basis.checkSource(value,{caseId:r.id,source})};
                }catch(error){if(error.obsolete)throw error;return {source,error:error.message};}
              }));
              if(epoch!==state.epoch)return;state.otherAssessmentSources=other;
            }
            if(r.query.has('run')){
              state.run=await read(path(r.id,'/runs/'+enc(r.query.get('run'))));
              if(state.run.run?.id!==r.query.get('run')||state.run.run.case_id!==r.id)throw Error('调查不属于所选主体或轮次。');
            }
            const resultId=r.query.get('result')||state.run?.result_ids?.[0];
            if(resultId){
              try{
                const value=await read(path(r.id,'/results/'+enc(resultId)));
                const result=recommendations.checkResult(value,{caseId:r.id,resultId,runId:state.run?.run.id});
                if(!state.run){
                  const run=await read(path(r.id,'/runs/'+enc(result.source_run_id)));
                  if(run.run?.id!==result.source_run_id||run.run.case_id!==r.id)throw Error('调查不属于所选主体或轮次。');
                  state.run=run;
                }
                state.result=value;
              }catch(error){if(error.obsolete||!state.run)throw error;state.resultError=error.message;}
            }
          }
          if(state.run){try{state.riskRound=await risk.round(read,'case',r.id,state.run.run.id,state.run);}catch(e){if(e.obsolete)throw e;state.riskRoundError=e.message;}}
        }
        if(r.id&&['case-info','overview','investigations'].includes(r.tab)){try{state.analysisTasks=await readAnalysisPage(r.page==='cases'?'case':'incident',r.id);}catch(e){if(e.obsolete)throw e;state.analysisError=e.status!==undefined?errorMessage(e):e.message;}}
        if(r.id&&r.tab==='activities'){try{state.activities=await read(activityPath(),{query:{limit:20}});}catch(e){if(e.obsolete)throw e;state.activityError=e.message;}}
      }catch(error){if(epoch===state.epoch){state.error=errorMessage(error);if(!r.id)state.queue=null;else state.detail=null;}}
      if(epoch===state.epoch){state.loading=false;render();}
    }
    async function mutate(suffix,body,method='POST'){if(state.busy)return;state.busy=true;try{return await state.client.request(suffix,{method,body});}finally{state.busy=false;}}
    async function openPicker(kind){const [alerts,incidents]=await Promise.all([read('/alerts',{query:{limit:20}}),read('/incidents',{query:{limit:20}})]);state.modal={kind,alerts,incidents,revision:state.detail?.case.scope_revision,operation:uuid()};render();}
    document.addEventListener('click',async event=>{
      const el=event.target.closest('[data-svc]');if(!el||el.disabled)return;event.preventDefault();const a=el.dataset.svc,id=el.dataset.id,r=route();
      if(state.busy)return;
      try {
        if(a==='disconnect'){state.epoch++;state.client=null;state.modal=null;state.detail=null;state.queue=null;state.notice='';state.error='';render();}
        else if(a==='close'){state.epoch++;state.modal=null;render();}
        else if(a==='refresh')await load();
        else if(a==='manage-risk'){const kind=r.page==='cases'?'case':'incident';state.modal={kind:'risk',subjectKind:kind,id:r.id,revision:risk.current(kind,state.detail).version,operation:uuid(),intent:null,uncertain:false};render();}
        else if(a==='latest-risk'){const m=state.modal;m.latest=await read('/'+r.page+'/'+enc(m.id));const x=risk.current(m.subjectKind,m.latest);document.querySelector('[data-svc-form-error]').innerHTML=`<p>最新版本 ${esc(x.version)} · 等级 ${esc(risk.level(x.level))} · 优先级 ${esc(x.priority??'未记录')}。草稿尚未保存。</p>${button('使用最新版本并保留草稿','accept-risk-version')}`;}
        else if(a==='accept-risk-version'){const m=state.modal;if(!m.latest)return;m.revision=risk.current(m.subjectKind,m.latest).version;m.operation=uuid();m.intent=null;m.uncertain=false;document.querySelector('[data-svc-form-error]').textContent='已更新为最新版本，草稿保持；请核对后再次明确保存。';}
        else if(a==='risk-history-more'){const p=await read(activityPath(),{query:{limit:20,offset:state.activities.next_offset}});state.activities={...p,items:[...state.activities.items,...p.items]};render();}
        else if(a==='incident-runs-more'){const p=await read('/analysis-runs',{query:{subject_type:'incident',subject_id:r.id,cursor:state.history.next_cursor}});state.history={...p,items:[...state.history.items,...p.items]};render();}
        else if(a==='export'){const query={...state.query};delete query.cursor;const text=await read('/'+r.page+'/export',{query,format:'text'});const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download=r.page+'.csv';link.click();URL.revokeObjectURL(url);}
        else if(a==='metric'){state.query={...state.query,metric:state.query.metric===id?'':id,cursor:''};await load();}
        else if(a==='clear-filter'||a==='queue-first'){state.query=a==='clear-filter'?{}:{...state.query,cursor:''};await load();}
        else if(a==='queue-next'){state.query.cursor=state.queue.next_cursor;await load();}
        else if(a==='prepare'||a==='rerun'){state.modal={kind:'analysis',subjectKind:r.page==='cases'?'case':'incident',id:r.id,mode:a==='rerun'?'rerun':'check',operation:uuid(),intent:null,receipt:null};render();}
        else if(a==='analysis-task'){const kind=r.page==='cases'?'case':'incident',receipt=state.analysisTasks.items.find(x=>x.task_id===id);state.modal={kind:'analysis-task',task:await readAnalysisTask(receipt,kind,r.id)};render();}
        else if(a==='refresh-analysis-task'){const m=state.modal,task=await readAnalysisTask(m.task,m.task.subject_type,m.task.subject_id);if(state.modal!==m)return;m.task=task;render();}
        else if(a==='analysis-more'){const old=state.analysisTasks,p=await readAnalysisPage(r.page==='cases'?'case':'incident',r.id,old.next_cursor);state.analysisTasks={...p,items:[...old.items,...p.items]};render();}
        else if(a==='allocation-task'){const m=state.modal;await readAllocatedTasks(m,id);if(state.modal!==m)return;render();}
        else if(a==='new-task'||a==='edit-task'){state.modal={kind:'task',task:a==='edit-task'?state.tasks.items.find(t=>t.id===id):null,originResult:state.result?.result.id||null,revision:state.detail.case.scope_revision,operation:uuid()};render();}
        else if(a==='task-revisions'){state.modal={kind:'revisions',task:id,originResult:state.tasks?.items.find(t=>t.id===id)?.origin_result_id,page:await read(path(r.id,'/tasks/'+enc(id)+'/revisions'),{query:{limit:20}})};render();}
        else if(a==='more-revisions'){const m=state.modal,p=await read(path(r.id,'/tasks/'+enc(m.task)+'/revisions'),{query:{limit:20,offset:m.page.next_offset}});m.page={...p,items:[...m.page.items,...p.items]};render();}
        else if(a==='history-more'||a==='tasks-more'){const key=a==='history-more'?'history':'tasks',old=state[key],p=await read(path(r.id,'/'+key),{query:{limit:20,...(key==='history'?{cursor:old.next_cursor}:{offset:old.next_offset})}});state[key]={...p,items:[...old.items,...p.items]};render();}
        else if(a==='artifact'||a==='material'){const p=await read(path(r.id,'/runs/'+enc(state.run.run.id)+'/'+(a==='artifact'?'artifacts':'materials')+'/'+enc(id)));state.modal={kind:'content',text:a==='artifact'?p.content_text:null,data:a==='artifact'?p.content_json:p,availability:a==='artifact'?p.availability:'本轮冻结材料'};render();}
        else if(a==='associate'||a==='create')await openPicker(a);
        else if(a==='more-alerts'||a==='more-incidents'){const key=a==='more-alerts'?'alerts':'incidents',m=state.modal,p=await read('/'+key,{query:{limit:20,before_id:m[key].next_before_id}});m[key]={...p,items:[...m[key].items,...p.items]};document.querySelector('#svc-'+(key==='alerts'?'alert':'incident')+'-options').insertAdjacentHTML('beforeend',picker(p,key==='alerts'?'alert':'incident'));el.disabled=!p.next_before_id;}
        else if(a==='more-targets'){const m=state.modal,p=await read('/cases',{query:{limit:50,cursor:m.targets.next_cursor}});m.targets={...p,items:[...m.targets.items,...p.items]};document.querySelector('select[name=target]').insertAdjacentHTML('beforeend',options(p.items.filter(x=>x.case.id!==r.id).map(x=>[x.case.id,x.case.title]),''));el.disabled=!p.next_cursor;}
        else if(a==='latest-task'){const m=state.modal,t=await read(path(r.id,'/tasks/'+enc(m.task.id)));document.querySelector('[data-svc-form-error]').innerHTML=`<p>最新版本 ${t.current.revision}，修改于 ${date(t.current.changed_at)}。当前输入尚未保存。</p>${json(t.current)}${button('用最新版本重新编辑','reload-task')}`;m.latest=t;}
        else if(a==='reload-task'){if(window.confirm('放弃当前未保存输入，改用最新版本重新编辑？')){state.detail=await read(path(r.id));state.modal={kind:'task',task:state.modal.latest,revision:state.detail.case.scope_revision,operation:uuid()};render();}}
      }catch(error){if(error.obsolete)return;state.error=errorMessage(error);if(state.modal){const box=document.querySelector('[data-svc-form-error]');if(box)box.textContent=state.error;else render();}else render();}
    });
    document.addEventListener('change',event=>{if(event.target.matches('[data-svc-run]')){const r=route();location.hash=href(r.id,'investigations','run='+enc(event.target.value)+'&view='+enc(r.query.get('view')||'overview'));}});
    document.addEventListener('submit',async event=>{
      const form=event.target.closest('[data-svc-form]');if(!form)return;event.preventDefault();if(state.busy)return;
      const fd=new FormData(form),v=Object.fromEntries(fd),action=form.dataset.svcForm,r=route(),m=state.modal;
      const submits=[...form.querySelectorAll('button[type=submit],button:not([type])')];submits.forEach(x=>x.disabled=true);
      try {
        if(action==='connect'){state.client=createClient(v.base,v.token);form.querySelector('[name=token]').value='';await load();return;}
        if(action==='filter'){state.query={...v,metric:state.query.metric||'',cursor:''};await load();return;}
        if(action==='move-select'){const members=fd.getAll('member');if(!members.length)throw Error('请先选择要移动的成员。');state.modal={kind:'move',members,revision:state.detail.case.scope_revision,operation:uuid(),targets:await read('/cases',{query:{limit:50}})};render();return;}
        if(action==='risk'){
          const body=risk.payload(m.subjectKind,v,m.revision,m.operation),intent=JSON.stringify(body);
          if(m.uncertain&&m.intent!==intent)throw Error('上次保存结果尚未确认；请保持原请求重试确认，或先读取最新版本。');
          if(!m.uncertain&&m.intent&&m.intent!==intent){m.operation=uuid();body.operation_key=m.operation;}
          m.intent=JSON.stringify(body);m.uncertain=true;
          try{await mutate('/'+(m.subjectKind==='case'?'cases':'incidents')+'/'+enc(m.id)+'/management',body,'PATCH');m.uncertain=false;}catch(e){if(e.status>=400&&e.status<500)m.uncertain=false;throw e;}
          if(state.modal!==m||route().id!==m.id)return;state.notice='属性已保存，正在重新读取当前值。';
        }else if(action==='task'){
          const body=taskPayload(v,fd.getAll('scope_member'),m.task,m.revision,m.operation);
          if(taskFactsChanged(body,m.task)&&body.result_scope?.kind==='whole_case'&&(body.result_scope.alert_ids.length!==state.detail.member_count||state.detail.members.some(x=>!body.result_scope.alert_ids.includes(x.alert_id))))throw Error('全案确认须勾选所有当前成员。');
          await mutate(path(r.id,'/tasks'+(m.task?'/'+enc(m.task.id):'')),body,m.task?'PUT':'POST');state.notice='人工结果已保存。需要更新案件判断时，请明确提交检查更新。';
        }else if(action==='analysis'){
          if(!['check','rerun'].includes(v.mode))throw Error('请选择检查更新或重新分析。');
          const body={operation_key:m.operation,mode:v.mode},intent=JSON.stringify(body);
          if(m.intent&&m.intent!==intent)throw Error('上次请求已提交或结果待确认；先核对原请求，勿改意图重发。');
          m.intent=intent;
          if(!m.receipt)m.receipt=await mutate('/'+m.subjectKind+'s/'+enc(m.id)+(m.subjectKind==='case'?'/investigations':'/diagnose'),body);
          if(state.modal!==m||route().id!==m.id)return;
          const task=await readAnalysisTask(m.receipt,m.subjectKind,m.id);
          if(state.modal!==m||route().id!==m.id)return;
          state.modal={kind:'analysis-task',task};state.notice='请求已受理，以下显示独立读取的实际任务状态。';render();return;
        }else if(action==='associate'||action==='create'){
          const selection={alert_ids:fd.getAll('alert'),incident_ids:fd.getAll('incident')};if(!selection.alert_ids.length&&!selection.incident_ids.length)throw Error('请选择告警或事件。');
          const body={operation_key:m.operation,...selection,...(action==='create'?{title:v.title}:{expected_scope_revision:m.revision})},intent=JSON.stringify(body);
          if(m.intent&&m.intent!==intent)throw Error('原分配请求已提交或结果待确认；请核对原请求，勿改意图重发。');m.intent=intent;
          if(!m.receipt)m.receipt=await mutate(action==='create'?'/cases':path(r.id,'/associations'),body);
          if(state.modal!==m)return;
          const allocation={kind:'allocation',targets:allocationTargets(m.receipt),reads:{}};state.modal=allocation;
          await readAllocatedTasks(allocation);if(state.modal!==allocation)return;state.notice='案件成员已按实际分配保存。';await load();return;
        }else if(action==='move'){
          if(!v.target)throw Error('请选择目标案件。');const target=await read(path(v.target));
          await mutate(path(r.id,'/members/move'),{operation_key:m.operation,target_case_id:v.target,expected_source_scope_revision:m.revision,expected_target_scope_revision:target.case.scope_revision,alert_ids:m.members});state.notice='成员移动已保存，两案调查范围已按实际变化更新。';
        }
        state.modal=null;await load();
        if(action==='risk'&&route().id===m.id&&!state.modal){state.notice=state.error?'保存请求已完成，但当前属性读取失败；请刷新核对。':'属性已保存，当前属性已重新读取。';render();}
      }catch(error){if(error.obsolete||(['risk','analysis','associate','create'].includes(action)&&state.modal!==m))return;const message=error.status!==undefined?errorMessage(error):error.message;const box=form.querySelector('[data-svc-form-error]');if(box){box.innerHTML=`<p>${esc(message)}</p>${m?.kind==='risk'&&(error.status===409||m.uncertain)?button('读取最新版本（保留草稿）','latest-risk'):error.status===409&&m?.task?button('查看最新版本','latest-task'):''}`;}else{state.error=message;if(action==='connect')state.client=null;render();}}
      finally{submits.forEach(x=>x.disabled=false);}
    });
    window.addEventListener('hashchange',()=>{state.modal=null;state.notice='';return load();});
    render();
  }
  return {active,start,createClient,taskPayload,taskFactsChanged,localInputTime,assessmentModel,groupRuns,errorMessage,analysisTaskPath,allocationTargets};
})();
