const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),clone=x=>JSON.parse(JSON.stringify(x));
function load({showcase=true,saved=null}={}){
 const handlers={},nodes={'#app':{},'#toast':{classList:{add(){},remove(){}}}};
 const s={window:{addEventListener(){}},document:{addEventListener:(type,fn)=>(handlers[type]||=[]).push(fn),querySelector:q=>nodes[q]||null},location:{hash:'#/incidents'},localStorage:{getItem:()=>saved,setItem(){}},structuredClone,URLSearchParams,clearInterval,clearTimeout,setTimeout:()=>0,FormData:class{constructor(form){this.values=form.values||form;}get(k){return this.values[k]??'';}getAll(k){return [].concat(this.values[k]||[]);}[Symbol.iterator](){return Object.entries(this.values)[Symbol.iterator]();}}};vm.createContext(s);
 const files=[...fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)].map(x=>x[1]);
 for(const f of files){if(!showcase&&f==='page-showcase-data.js')continue;let code=fs.readFileSync(path.join(root,f),'utf8');if(f==='app.js')code=code.replace('readQueueLink();render();\n})();','window.api={store,ui,incidentPage,incidentCases,associateIncidentCase,fullAlert,modalMarkup,drawerMarkup,workspaceView,scopeActivities};\n})();');vm.runInContext(code,s);}
 return {...s.window.api,s,nodes,handlers,d:s.window.pageShowcaseData,M:s.window.investigationWorkspaceModel,click:async(action,id='')=>{for(const fn of handlers.click)await fn({target:{closest:q=>q==='[data-action]'?{dataset:{action,id}}:null},preventDefault(){}});}};
}
test('showcases append coherent records and preserve all original records, Runs and saved edits',()=>{
 const old=load({showcase:false}),x=load();
 for(const key of ['alerts','incidents','assets','cases','evidence','activities','comments'])for(const a of old.store[key])assert.deepEqual(clone(x.store[key].find(row=>row.id===a.id)),clone(a));
 for(const r of old.M.runs(old.store))assert.deepEqual(clone(x.M.runs(x.store).find(row=>row.id===r.id)),clone(r));
 assert.deepEqual([x.store.alerts.length,x.store.incidents.length,x.store.cases.length,x.M.runs(x.store).length],[78,21,21,18]);
 const before=JSON.stringify(x.store);x.s.window.mergePageShowcases(x.store);assert.equal(JSON.stringify(x.store),before);
 const a=x.store.alerts.find(a=>a.fixtureSet);a.title='自定义标题';a.detailMaterial.history=[];
 const inc=x.store.incidents.find(i=>i.fixtureSet);inc.owner='Megan Bowen';inc.status='Resolved';
 const y=load({saved:JSON.stringify(x.store)});assert.equal(y.store.alerts.find(row=>row.id===a.id).title,a.title);assert.equal(y.store.alerts.find(row=>row.id===a.id).detailMaterial.history.length,0);assert.equal(y.store.incidents.find(row=>row.id===inc.id).status,'Resolved');
});
test('scenario membership, relationship evidence, timelines and frozen Run materials are internally consistent',()=>{
 const x=load(),d=x.d,assets=new Set(d.assets.map(a=>a.id)),alerts=new Map(d.alerts.map(a=>[a.id,a]));
 for(const collection of ['incidents','alerts','assets','cases','evidence','activities','runs'])assert.equal(new Set(d[collection].map(a=>a.id)).size,d[collection].length);
 for(const a of d.alerts){assert.ok(d.incidents.some(i=>i.id===a.incidentId));assert.ok(a.entityIds.every(id=>assets.has(id)));assert.ok(a.detailMaterial.raw.source_ref);assert.equal(a.detailMaterial.raw.event_time,a.event_time);assert.ok(a.detailMaterial.techniques.length);assert.ok(a.detailMaterial.history.every(e=>Date.parse(e.time)>=Date.parse(a.first)));}
 for(const e of d.relations){assert.ok(assets.has(e.from)&&assets.has(e.to));for(const id of e.alertIds){assert.ok(alerts.get(id).entityIds.includes(e.from));assert.ok(alerts.get(id).entityIds.includes(e.to));}}
 for(const r of d.runs){assert.equal(r.recorded,false);assert.equal(r.calls,undefined);assert.equal(r.tokens,undefined);assert.equal(r.executed.length,0);assert.ok(Date.parse(r.input.event_time)<=Date.parse(r.started));assert.equal(r.input.id,r.alertIds[0]);assert.equal(r.input.status,'New');assert.ok(Date.parse(r.input.last)<=Date.parse(r.started));assert.equal(r.input.detailMaterial,undefined);assert.equal(r.input.feedbackReason,undefined);
  for(const t of r.tools.filter(t=>t.name==='asset_activity')){const result=JSON.parse(t.result);assert.deepEqual(clone(result.scope),clone(t.args));for(const row of result.records){assert.ok(row.hostnames.every(h=>t.args.hostnames.includes(h)));assert.equal(row.username,t.args.username);assert.ok(Date.parse(row.time)>=Date.parse(t.args.start)&&Date.parse(row.time)<=Date.parse(t.args.end));}}
  const trace=alerts.get(r.alertIds[0]).detailMaterial.runs[0];assert.equal(trace.completion,r.completion);assert.equal(trace.report,r.report);assert.equal(trace.tools.length,r.tools.length);
  for(const a of r.artifacts){const body=r.artifactBodies[a.id],text=body.format==='json'?JSON.stringify(body.content):body.content;assert.equal(a.sha256,crypto.createHash('sha256').update(text).digest('hex'));assert.equal(a.size_bytes,Buffer.byteLength(text));assert.ok(r.steps.some(s=>s.id===a.event_id));}
 }
 const r=x.M.runs(x.store).find(r=>r.id==='showcase-run-01'),input=JSON.stringify(r.input);x.store.alerts.find(a=>a.id===r.alertIds[0]).title='later edit';assert.equal(JSON.stringify(r.input),input);
});
test('all incident and alert tabs expose scenario material and graphs remain inside the current event',()=>{
 const x=load(),before=JSON.stringify(x.store);
 for(const inc of x.d.incidents){
  for(const tab of ['summary','attack','alerts','assets','activities']){x.s.location.hash=`#/incidents/${inc.id}/${tab}`;x.workspaceView.resetScope();const html=x.incidentPage();assert.ok(!/Invalid Date|>undefined<|>null</.test(html));assert.ok(html.includes(inc.title));
   if(tab==='summary'){assert.ok(html.includes(inc.correlationReason));assert.ok(html.includes(inc.caseId?'进入 Case':'事件是什么'));}
   if(tab==='attack'){assert.ok(html.includes('data-action="ws-edge"'));assert.ok(!html.includes('data-ws-scope'));for(const other of x.d.incidents.filter(i=>i.id!==inc.id))for(const a of x.d.alerts.filter(a=>a.incidentId===other.id))assert.ok(!html.includes(`data-action="ws-alert" data-id="${a.id}"`));}
   if(tab==='activities')assert.ok(x.scopeActivities().length>=4);
  }
 }
 for(const a of x.d.alerts)for(const tab of ['overview','timeline','raw','response']){x.s.location.hash=`#/alerts/${a.id}/${tab}`;const html=x.fullAlert(x.store.alerts.find(row=>row.id===a.id));assert.ok(!/Invalid Date|>undefined<|>null</.test(html));if(tab==='raw')assert.ok(html.includes(a.detailMaterial.raw.source_ref));if(tab==='overview')assert.ok(html.includes(a.detailMaterial.techniques[0]));}
 for(const [id,label] of [['showcase-alert-01-1','完整交付'],['showcase-alert-02-1','部分完成'],['showcase-alert-03-1','未升级调查']]){x.s.location.hash=`#/alerts/${id}/response`;const html=x.fullAlert(x.store.alerts.find(a=>a.id===id));assert.ok(html.includes(label));assert.ok(!html.includes('尚未交付'));}
 assert.equal(JSON.stringify(x.store),before);
});
test('unassigned scenario supports event assignment, explicit Case creation and manual resolution',async()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.id==='showcase-incident-02');x.s.location.hash=`#/incidents/${inc.id}/summary`;assert.equal(x.incidentCases(inc).length,0);assert.ok(x.incidentPage().includes('新建 Case'));
 x.nodes['#manage-incidents-form']={title:inc.title,status:'New',owner:'Alex Wilber',tags:'联合核查',note:''};x.ui.modal={type:'manage-incident',id:inc.id};await x.click('save-incidents');assert.equal(inc.status,'In progress');
 const runs=JSON.stringify(x.M.runs(x.store));const c=x.associateIncidentCase(inc,{mode:'new',title:'跨主机访问调查'});assert.deepEqual([...c.alertIds].sort(),Array.from(x.d.alerts.filter(a=>a.incidentId===inc.id),a=>a.id).sort());assert.equal(JSON.stringify(x.M.runs(x.store)),runs);
 x.nodes['#manage-incidents-form']={title:inc.title,status:'Resolved',owner:inc.owner,tags:'联合核查',note:'已核对记录并完成人工处理'};x.ui.modal={type:'manage-incident',id:inc.id};await x.click('save-incidents');assert.equal(inc.status,'Resolved');assert.ok(x.store.alerts.filter(a=>a.incidentId===inc.id).every(a=>a.status==='Resolved'));
});
test('showcase alert feedback and similar-history review stay in the same source scope',()=>{
 const x=load(),a=x.store.alerts.find(a=>a.id==='showcase-alert-02-2'),candidate=x.store.alerts.find(a=>a.id==='showcase-alert-02-3'),actual=x.store.alerts.find(a=>a.persistedRecord),saved=JSON.stringify(actual);
 const submit=(kind,values)=>{const form={dataset:{detailForm:kind,alert:a.id},values};for(const fn of x.handlers.submit)fn({target:{closest:q=>q==='[data-detail-form]'?form:null},preventDefault(){}});};
 submit('feedback',{verdict:'escalate',reason:'等待完整文件清单'});assert.equal(a.disposition,'escalate');assert.ok(a.detailMaterial.history.some(h=>h.title==='人工判定更新'));
 submit('redisposition',{ids:[candidate.id,actual.id]});assert.equal(candidate.disposition,'escalate');assert.equal(JSON.stringify(actual),saved);
});
test('AiSOC saved values remain exact while available source and missing reference are displayed honestly',()=>{
 const x=load(),d=x.s.window.aisoc20RecordedData,before=JSON.stringify(d);
 for(const a of d.alerts){const row=x.store.alerts.find(r=>r.id===a.id);assert.equal(row.detailMaterial.confidence.score,a.detailMaterial.raw.confidence);assert.equal(row.detailMaterial.risk,Math.round(a.detailMaterial.raw.ai_score*100));assert.equal(row.detailMaterial.explanation.summary,'');assert.equal(row.caseId,null);x.s.location.hash=`#/alerts/${a.id}/raw`;const html=x.fullAlert(row);assert.ok(html.includes('来源：showcase-security-sensor · 源记录：—'));}
 assert.deepEqual([...d.alerts.filter(a=>!a.incidentId).map(a=>a.id)],['ef9c21f4-d703-5be8-a6d2-63195e09da36']);assert.equal(JSON.stringify(d),before);
});
