const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function load(){
 const s={window:{addEventListener(){}},document:{addEventListener(){}},location:{hash:'#/cases/17420/overview'},localStorage:{getItem:()=>null},structuredClone,URLSearchParams,clearInterval};vm.createContext(s);
 const files=[...fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)].map(m=>m[1]);
 for(const f of files){let code=fs.readFileSync(path.join(root,f),'utf8');if(f==='app.js')code=code.replace('readQueueLink();render();\n})();','window.api={store,ui,casePage,caseWorkflow,investigationView,modalMarkup,drawerMarkup};\n})();');vm.runInContext(code,s);}
 const x={...s.window.api,s,M:s.window.investigationWorkspaceModel},c=x.store.cases.find(c=>c.id==='17420');x.c=c;x.logs=[];x.saves=0;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 x.W=s.window.createCaseWorkflow({store:x.store,ui:x.ui,esc,btn:(t,a,id)=>`<button data-action="${a}" data-id="${esc(id)}">${esc(t)}</button>`,badge:t=>esc(t),date:t=>t,severity:t=>esc(t),currentCase:()=>c,currentRoute:()=>({page:'cases'}),getAlert:id=>x.store.alerts.find(a=>a.id===id),getAsset:id=>x.store.assets.find(a=>a.id===id),render(){},save(){x.saves++;},toast(){},logActivity:(...args)=>x.logs.push(args),navigate(){}});return x;
}
test('Case objects and evidence aliases keep all recorded materials with ten navigation entries',()=>{
 const x=load(),before=JSON.stringify(x.store);
 for(const c of x.store.cases)for(const tab of ['assets','evidence']){
  x.s.location.hash=`#/cases/${c.id}/${tab}`;const html=x.casePage();assert.ok(html.includes('<h2>对象与证据</h2>'));assert.equal((html.match(/class="case-nav-button /g)||[]).length,10);
  for(const r of x.M.forCase(x.store,c)){assert.ok(html.includes(`run=${r.id}`));for(const a of r.artifacts)if(a.sha256)assert.ok(html.includes(a.sha256));}
 }
 assert.equal(JSON.stringify(x.store),before);
});
test('adding members deduplicates and preserves other Cases, alert records and historical Run inputs',()=>{
 const x=load(),before=JSON.stringify([x.store.alerts,x.M.runs(x.store),x.store.cases.filter(c=>c!==x.c)]),added=x.store.alerts.find(a=>x.W.eligible(x.c,a)&&!x.c.alertIds.includes(a.id));
 const n=x.W.addMembers(x.c,[added.id,added.id,x.c.alertIds[0]]);assert.equal(n,1);assert.equal(x.c.alertIds.filter(id=>id===added.id).length,1);assert.ok(x.c.retainedRunIds.includes('INV-20261024-001'));
 assert.equal(JSON.stringify([x.store.alerts,x.M.runs(x.store),x.store.cases.filter(c=>c!==x.c)]),before);
 const alien=x.store.alerts.find(a=>!x.W.eligible(x.c,a)),state=JSON.stringify(x.c);assert.throws(()=>x.W.addMembers(x.c,[alien.id]),/可关联/);assert.equal(JSON.stringify(x.c),state);
});
test('event selection only expands eligible members and cancellation does not write',()=>{
 const x=load(),before=JSON.stringify(x.store);x.W.handle('cw-add','');x.W.handle('cw-add-mode','events');
 const inc=x.store.incidents.find(i=>x.store.alerts.some(a=>a.incidentId===i.id&&x.W.eligible(x.c,a)&&!x.c.alertIds.includes(a.id)));
 x.W.change({checked:true,hasAttribute:k=>k==='data-cw-event',getAttribute:()=>inc.id});
 const expected=x.store.alerts.filter(a=>a.incidentId===inc.id&&x.W.eligible(x.c,a)&&!x.c.alertIds.includes(a.id)).map(a=>a.id).sort();assert.deepEqual([...x.ui.modal.selected].sort(),[...expected]);
 x.ui.modal=null;assert.equal(JSON.stringify(x.store),before);assert.equal(x.saves,0);
});
test('investigation preparations stay outside Runs and preserve explicit inputs, materials and continuation',()=>{
 const x=load(),r=x.M.forCase(x.store,x.c)[0],before=JSON.stringify(x.M.runs(x.store)),ref=JSON.stringify(['run',r.id]);
 const draft=x.W.saveDraft(x.c,{objective:'核实新增授权资料',alertIds:[x.c.alertIds[0]],materialIds:[ref],sourceRunId:r.id});
 assert.equal(draft.status,'draft');assert.equal(draft.sourceRunId,r.id);assert.equal(draft.materials[0].id,ref);assert.equal(draft.alertIds.length,1);assert.equal(JSON.stringify(x.M.runs(x.store)),before);
 x.W.saveDraft(x.c,{id:draft.id,objective:'调整目标',alertIds:[x.c.alertIds[1]],materialIds:[]});assert.equal(x.c.investigationDrafts.length,1);
 assert.throws(()=>x.W.saveDraft(x.c,{objective:'',alertIds:[]}),/调查目标/);assert.throws(()=>x.W.saveDraft(x.c,{objective:'x',alertIds:['foreign']}),/范围已变化/);
 assert.throws(()=>x.W.saveDraft(x.c,{objective:'x',alertIds:x.c.alertIds,materialIds:['foreign']}),/材料已不可用/);
 x.ui.modal={type:'cw-investigate',draft};assert.match(x.W.modal(),/disabled[^>]*>启动调查/);assert.ok(x.W.modal().includes('保存后进入“待启动调查”'));
});
test('human task completion requires a result and can supply a later preparation without altering analysis',()=>{
 const x=load(),before=JSON.stringify([x.M.runs(x.store),x.store.evidence,x.store.assets]),status=x.c.status;
 assert.throws(()=>x.W.saveTask(x.c,{title:'核实授权',status:'Completed',owner:'Alex Wilber'}),/处理结果/);
 const t=x.W.saveTask(x.c,{title:'核实授权',status:'In progress',owner:'Alex Wilber'});
 x.W.saveTask(x.c,{id:t.id,title:t.title,status:'Completed',owner:t.owner,result:'核对工单 CHG-11，已取得授权记录。'});
 assert.ok(t.completedAt);const completedAt=t.completedAt,createdAt=t.createdAt,count=x.c.tasks.length;
 x.W.handle('cw-task',t.id);assert.ok(x.W.modal().includes(t.result));assert.equal(x.saves,2);
 x.W.saveTask(x.c,{...t,result:'负责人补充确认：仅指定主机的计划维护已授权。',materialIds:t.materials.map(m=>m.id)});
 assert.equal(x.c.tasks.length,count);assert.equal(t.completedAt,completedAt);assert.equal(t.createdAt,createdAt);assert.ok(t.result.includes('补充确认'));
 x.W.saveTask(x.c,{...t,status:'Cancelled',materialIds:t.materials.map(m=>m.id)});x.W.handle('cw-task',t.id);assert.ok(x.W.modal().includes(t.result));
 x.W.saveTask(x.c,{...t,status:'Completed',materialIds:t.materials.map(m=>m.id)});assert.equal(x.c.tasks.length,count);
 const ref=JSON.stringify(['task',t.id]);assert.ok(x.W.materialOptions(x.c).some(m=>m.id===ref));
 const d=x.W.saveDraft(x.c,{objective:'结合授权复核',alertIds:x.c.alertIds,materialIds:[ref]});assert.equal(d.materials[0].result,t.result);
 assert.equal(x.c.status,status);assert.equal(JSON.stringify([x.M.runs(x.store),x.store.evidence,x.store.assets]),before);
});
test('response approval is an independent action decision and never creates execution or resolves objects',()=>{
 const x=load(),r=x.M.forCase(x.store,x.c).find(r=>r.actions.some(a=>a.requires_approval)),i=r.actions.findIndex(a=>a.requires_approval&&a.target),before=JSON.stringify([x.M.runs(x.store),x.store.evidence,x.store.assets,x.c.status]);
 assert.throws(()=>x.W.decide(x.c,r.id,i,'approved',''),/理由/);
 const review=x.W.decide(x.c,r.id,i,'approved','已核对目标，等待维护窗口执行');assert.equal(review.decision,'approved');assert.ok(x.W.responseControls(r).includes('已批准 · 待执行'));
 assert.equal(JSON.stringify([x.M.runs(x.store),x.store.evidence,x.store.assets,x.c.status]),before);
 x.W.decide(x.c,r.id,i,'rejected','业务窗口不合适');assert.ok(x.W.responseControls(r).includes('已拒绝'));
 const e=x.store.evidence.find(e=>e.remediation==='Pending approval');x.ui.drawer={type:'evidence',id:e.id};assert.ok(!x.drawerMarkup().includes('approve-evidence'));
});
test('retained Run history survives later membership edits without changing source-owned Runs',()=>{
 const x=load(),old=x.M.forCase(x.store,x.c).map(r=>r.id),before=JSON.stringify(x.M.runs(x.store));
 x.W.saveDraft(x.c,{objective:'后续核查',alertIds:[x.c.alertIds[0]],materialIds:[]});x.c.alertIds=[];
 for(const id of old)assert.ok(x.M.forCase(x.store,x.c).some(r=>r.id===id));assert.equal(JSON.stringify(x.M.runs(x.store)),before);
});

test('material browsing opens a relevant object and switches only its explicit evidence and source alerts',()=>{
 const x=load(),before=JSON.stringify(x.store),html=x.W.materials();
 assert.match(html,/id="cw-objects-panel" class="cw-material-panel" >/);
 assert.match(html,/aria-pressed="true"[^>]*>.*?hcook@contoso.com/s);
 assert.match(html,/<h3>hcook@contoso.com<\/h3>/);
 const file=x.store.assets.find(a=>a.name==='invoice_2026.pdf.exe');assert.ok(file);
 x.W.handle('cw-material-object',file.id);const selected=x.W.materials().split('aria-label="当前对象详情">')[1].split('<section id="cw-runs-panel"')[0];
 assert.match(selected,/<h3>invoice_2026.pdf.exe<\/h3>/);
 const own=x.store.evidence.filter(e=>e.entityId===file.id&&x.c.alertIds.includes(e.alertId));assert.ok(own.length);
 for(const e of own){assert.ok(selected.includes(`data-id="${e.id}"`));assert.ok(selected.includes(`#/alerts/${e.alertId}/overview`));}
 for(const e of x.store.evidence.filter(e=>e.entityId!==file.id))assert.ok(!selected.includes(`data-id="${e.id}"`));
 for(const a of x.store.alerts.filter(a=>x.c.alertIds.includes(a.id)&&!a.entityIds.includes(file.id)))assert.ok(!selected.includes(`#/alerts/${a.id}/overview`));
 assert.equal(JSON.stringify(x.store),before);assert.equal(x.saves,0);
});
test('material filters never leave unrelated detail, reset works and another Case clears the reading state',()=>{
 const x=load(),before=JSON.stringify(x.store),search=value=>x.W.input({value,hasAttribute:k=>k==='data-cw-material-search'});
 search('invoice_2026');assert.match(x.W.materials(),/<h3>invoice_2026.pdf.exe<\/h3>/);
 search('no-such-object-qa');let html=x.W.materials();assert.match(html,/没有匹配的对象/);assert.ok(!html.includes('aria-label="当前对象详情"><div class="cw-object-detail-heading"'));
 x.W.handle('cw-material-reset','');assert.match(x.W.materials(),/<h3>hcook@contoso.com<\/h3>/);
 x.W.change({value:'file',hasAttribute:k=>k==='data-cw-material-type'});assert.match(x.W.materials(),/<h3>invoice_2026.pdf.exe<\/h3>/);
 x.W.handle('cw-material-view','runs');assert.match(x.W.materials(),/id="cw-runs-panel" class="cw-material-panel" >/);
 x.s.location.hash='#/cases/local-aisoc20-1/evidence';html=x.casePage();assert.equal(x.ui.cwMaterials.caseId,'local-aisoc20-1');assert.equal(x.ui.cwMaterials.query,'');assert.equal(x.ui.cwMaterials.type,'');assert.equal(x.ui.cwMaterials.objectId,null);assert.equal(x.ui.cwMaterials.view,null);
 assert.ok(html.includes('尚无独立证据条目'));assert.ok(html.includes('来源告警'));assert.ok(!html.includes('invoice_2026.pdf.exe'));
 assert.equal(JSON.stringify(x.store),before);assert.equal(x.saves,0);
});
test('unlinked evidence remains accessible and material-only Cases retain per-Run sources without adoption',()=>{
 const x=load(),member=x.c.alertIds[0];x.store.evidence.push({id:'orphan-qa',alertId:member,entityId:'absent-object',name:'独立日志记录',type:'日志'});
 let html=x.W.materials();assert.ok(html.includes('未关联对象的证据'));
 x.W.handle('cw-material-object','__unlinked__');html=x.W.materials();assert.ok(html.includes('<h3>未关联对象的证据</h3>'));assert.ok(html.includes('data-id="orphan-qa"'));assert.ok(html.includes(`#/alerts/${member}/overview`));
 x.c.retainedRunIds=x.M.forCase(x.store,x.c).map(r=>r.id);x.c.alertIds=[];x.ui.cwMaterials=null;
 const before=JSON.stringify(x.store);html=x.W.materials();assert.match(html,/id="cw-runs-panel" class="cw-material-panel" >/);assert.ok(html.includes('原件不自动视为已确认的恶意证据'));
 for(const r of x.M.forCase(x.store,x.c)){assert.ok(html.includes(`run=${r.id}&view=tools`));assert.ok(html.includes(`run=${r.id}&view=report`));}
 x.c.retainedRunIds=[];x.ui.cwMaterials=null;assert.ok(x.W.materials().includes('暂无对象或独立证据'));x.c.retainedRunIds=JSON.parse(before).cases.find(c=>c.id===x.c.id).retainedRunIds;
 assert.equal(JSON.stringify(x.store),before);assert.equal(x.saves,0);
});

test('graph related alert opens a preselected confirmation and only confirmation updates current membership',()=>{
 const x=load(),r=x.M.forCase(x.store,x.c)[0],a=x.store.alerts.find(a=>x.W.eligible(x.c,a)&&!x.c.alertIds.includes(a.id)),before=JSON.stringify(x.store),sources=JSON.stringify([x.M.runs(x.store),x.store.alerts,x.store.cases.filter(c=>c!==x.c)]);
 x.W.handle('cw-add-related',JSON.stringify([r.id,a.id]));assert.equal(x.ui.modal.type,'cw-add');assert.deepEqual([...x.ui.modal.selected],[a.id]);assert.equal(x.saves,0);assert.equal(JSON.stringify(x.store),before);
 x.ui.modal=null;assert.equal(JSON.stringify(x.store),before);x.W.handle('cw-add-related',JSON.stringify([r.id,a.id]));x.W.handle('cw-add-save','');assert.ok(x.c.alertIds.includes(a.id));assert.equal(x.saves,1);assert.equal(x.ui.modal,null);assert.equal(JSON.stringify([x.M.runs(x.store),x.store.alerts,x.store.cases.filter(c=>c!==x.c)]),sources);
});

test('human confirmation needs no work order and task reference choices do not repeat whole source Runs',()=>{
 const x=load(),r=x.M.forCase(x.store,x.c)[0],before=JSON.stringify([x.store,x.M.runs(x.store)]),ref=JSON.stringify(['run',r.id]);
 x.ui.modal={type:'cw-task',sourceRunId:r.id};let html=x.W.modal();
 assert.ok(html.includes('来源调查（可选）'));assert.ok(html.includes('补充参考资料（可选）'));assert.ok(html.includes('无需提供工单或上传附件'));
 assert.ok(!/type="checkbox" name="material" value="\[&quot;run&quot;/.test(html));
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);x.ui.modal=null;
 const task=x.W.saveTask(x.c,{title:'确认正常运维',owner:'Alex Wilber',status:'Completed',result:'已确认是本人执行的正常运维。',materialIds:[],sourceRunId:r.id});
 assert.equal(task.materials.length,0);assert.equal(task.result,'已确认是本人执行的正常运维。');
 x.W.saveTask(x.c,{...task,materialIds:[ref]});x.ui.modal={type:'cw-task',id:task.id};html=x.W.modal();assert.ok(html.includes('type="hidden" name="material"'));assert.equal(task.materials[0].id,ref);
});
