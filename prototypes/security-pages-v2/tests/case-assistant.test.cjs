const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function load(){
 const local=new Map(),s={window:{addEventListener(){}},document:{addEventListener(){}},location:{hash:'#/cases/explore-case-01/story'},localStorage:{getItem:k=>local.get(k)||null,setItem:(k,v)=>local.set(k,v)},structuredClone,URLSearchParams,clearInterval};vm.createContext(s);
 for(const [,file] of fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)){let code=fs.readFileSync(path.join(root,file),'utf8');if(file==='app.js')code=code.replace('readQueueLink();render();\n})();','window.api={store,ui,casePage,caseWorkflow,caseAssistant};\n})();');vm.runInContext(code,s);}
 const x={...s.window.api,s,local,M:s.window.investigationWorkspaceModel,notices:[]};x.c=x.store.cases.find(c=>c.id==='explore-case-01');
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const common={store:x.store,ui:x.ui,esc,I:()=>'',btn:(t,a,id)=>`<button data-action="${a}" data-id="${esc(id)}">${esc(t)}</button>`,badge:esc,date:v=>v===null?'—':String(v),severity:esc,currentCase:()=>x.c,currentRoute:()=>({page:'cases',id:x.c.id,tab:'story'}),getAlert:id=>x.store.alerts.find(a=>a.id===id),getAsset:id=>x.store.assets.find(a=>a.id===id),render(){},toast:t=>x.notices.push(t)};
 x.common=common;x.W=s.window.createCaseWorkflow({...common,assistant:()=>x.A,save(){throw Error('unexpected business save');},logActivity(){throw Error('unexpected activity');},navigate(){}});
 x.create=()=>s.window.createCaseAssistant({...common,workflow:()=>x.W});x.A=x.create();return x;
}
test('all Cases share the story, assistant and task navigation without writes or duplicate members',()=>{
 const x=load(),before=JSON.stringify(x.store);
 for(const c of x.store.cases){x.c=c;x.s.location.hash=`#/cases/${c.id}/story`;const html=x.casePage();assert.ok(html.includes('案件告警时间线'));assert.ok(html.includes('人工任务'));assert.ok(!html.includes('相似 Cases'));assert.equal((html.match(/class="case-nav-button /g)||[]).length,10);const ids=x.A.storyRows(c).map(a=>a.id);assert.equal(new Set(ids).size,ids.length);assert.deepEqual([...ids].sort(),[...new Set(c.alertIds)].filter(id=>x.store.alerts.some(a=>a.id===id)).sort());assert.ok(!html.includes('Invalid Date'));}
 assert.equal(JSON.stringify(x.store),before);
});
test('story sorts newest occurrence first, retains unknown time and never substitutes saved-alert first timestamp',()=>{
 const x=load(),rows=x.A.storyRows(x.c),a=rows[0],b=rows[1];x.c.alertIds.push(a.id);a.persistedRecord=true;a.event_time=null;a.first='2026-11-02T01:00:00Z';b.event_time='2026-11-03T00:00:00Z';
 const sorted=x.A.storyRows(x.c);assert.equal(sorted[0].id,b.id);assert.equal(sorted.at(-1).id,a.id);assert.equal(sorted.filter(r=>r.id===a.id).length,1);const html=x.A.story();assert.ok(html.indexOf('时间未记录</h3>')>html.indexOf(b.title));
});
test('questions are Case-local preview records and never create tasks, drafts, Runs or member writes',()=>{
 const x=load(),first=x.c,before=JSON.stringify(x.store);x.A.open({alertIds:[first.alertIds[0],first.alertIds[1]]});x.A.send('请补查网络日志');
 assert.equal(x.A.session().messages.length,1);assert.equal(x.local.size,1);assert.ok(x.local.has('aisoc-case-assistant-preview'));assert.equal(JSON.stringify(x.store),before);
 x.c=x.store.cases.find(c=>c.id!==first.id);x.A.open();assert.equal(x.A.session().messages.length,0);assert.equal(x.A.session().context.alertIds,undefined);
 x.c=first;x.A.open();assert.equal(x.A.session().messages.length,1);const restored=x.create();restored.open();assert.equal(restored.session().messages[0].text,'请补查网络日志');assert.equal(JSON.stringify(x.store),before);
});
test('foreign references are rejected and source excerpts stay within selected alert, entity or Run scope',()=>{
 const x=load(),foreign=x.store.alerts.find(a=>!x.W.eligible(x.c,a)),other=x.store.cases.find(c=>c.sourceEnvironment&&c.id!==x.c.id),foreignRun=x.M.forCase(x.store,other)[0];
 const n=x.A.normalize(x.c,{alertIds:[foreign.id],entityIds:foreign.entityIds,runId:foreignRun?.id,taskId:'foreign'});assert.equal(n.alertIds.length,0);assert.equal(n.runId,null);assert.equal(n.taskId,null);for(const id of n.entityIds)assert.ok(x.store.alerts.some(a=>x.W.eligible(x.c,a)&&a.entityIds.includes(id)));
 const a=x.store.alerts.find(a=>x.W.eligible(x.c,a)&&!x.c.alertIds.includes(a.id));x.A.open({alertIds:[a.id]});x.A.send('查看这些线索');const html=x.A.panel();assert.ok(html.includes('案外线索')||html.includes(a.title));assert.ok(html.includes('当前范围没有已保存的调查发现'));assert.ok(!html.includes('终端脚本、账号登录和连接记录共享'));
});
test('questions do not present preparation or human confirmation as a prerequisite for AI execution',()=>{
 const x=load();x.A.open();x.A.send('补查主机网络日志');const html=x.A.panel();assert.ok(!html.includes('ca-prepare'));assert.ok(!html.includes('ca-task'));assert.ok(!html.includes('问题已保留'));assert.ok(!html.includes('ca-message-system'));assert.ok(html.includes('参考资料'));assert.ok(!html.includes('ca-mode'));assert.ok(html.includes('aria-label="建议问题"'));
});
test('question content is escaped and active Runs do not block reading or create a second investigation',()=>{
 const x=load();x.c=x.store.cases.find(c=>x.W.activeRun(c));assert.ok(x.c);const before=JSON.stringify(x.store);x.A.open();x.A.send('<img src=x onerror=alert(1)>');const html=x.A.panel();assert.ok(html.includes('&lt;img'));assert.ok(!html.includes('<img src=x'));assert.ok(html.includes('本案已有调查'));assert.ok(!html.includes('ca-mode'));assert.ok(html.includes('来源：已有调查与人工任务记录'));assert.equal(JSON.stringify(x.store),before);
});
test('story severity filter uses the same Chinese values as current alert records',()=>{
 const x=load();x.A.session().severity='高';const html=x.A.story();assert.ok(html.includes('3 / 3 条'));assert.ok(!html.includes('暂无匹配告警'));assert.ok(html.includes('value="高" selected'));
 x.A.session().severity='低';assert.ok(x.A.story().includes('0 / 3 条'));
});
test('explicitly conflicting asset ownership is rejected in context and story object names',()=>{
 const x=load(),a=x.store.alerts.find(a=>a.id===x.c.alertIds[0]),asset=x.store.assets.find(e=>e.id===a.entityIds[0]);asset.sourceEnvironment='foreign-env';asset.sourceTenantId='foreign-tenant';asset.name='FOREIGN_SECRET';
 assert.equal(x.A.normalize(x.c,{entityIds:[asset.id]}).entityIds.length,0);x.A.open({entityIds:[asset.id]});assert.ok(!x.A.panel().includes('FOREIGN_SECRET'));assert.ok(!x.A.story().includes('FOREIGN_SECRET'));
});
test('manual human task retains linked alert context after explicit save without creating a Run',()=>{
 const x=load(),a=x.store.alerts.find(a=>a.id===x.c.alertIds[0]);let writes=0;
 x.W=x.s.window.createCaseWorkflow({...x.common,assistant:()=>x.A,save(){writes++;},logActivity(){},navigate(){}});
 x.W.openHumanTask({title:'这是不是正常运维？',referenceContext:x.A.normalize(x.c,{alertIds:[a.id],entityIds:[a.entityIds[0]]})});const m=x.ui.modal,before=JSON.stringify(x.M.runs(x.store));
 assert.equal(m.referenceContext.alertIds[0],a.id);assert.ok(x.W.modal().includes(`#/alerts/${a.id}/overview`));assert.equal(writes,0);
 const t=x.W.saveTask(x.c,{title:m.title,description:m.description,owner:'未分配',referenceContext:m.referenceContext});assert.equal(writes,1);assert.equal(t.referenceContext.alertIds[0],a.id);assert.ok(!x.W.tasks().includes(`#/alerts/${a.id}/overview`));x.W.handle('cw-task',t.id);assert.ok(x.W.modal().includes(`#/alerts/${a.id}/overview`));assert.equal(writes,1);assert.equal(JSON.stringify(x.M.runs(x.store)),before);
});

test('story excludes explicitly conflicting member alert sources before reading names, times or shared objects',()=>{
 const x=load(),a=x.store.alerts.find(a=>a.id===x.c.alertIds[0]);a.sourceEnvironment='foreign-env';a.sourceTenantId='foreign-tenant';a.title='FOREIGN_ALERT_TITLE';assert.ok(!x.A.storyRows(x.c).some(row=>row.id===a.id));assert.ok(!x.A.story().includes('FOREIGN_ALERT_TITLE'));assert.equal(x.A.normalize(x.c,{alertIds:[a.id]}).alertIds.length,0);
});

test('initial question is editable, respects selected scope and never submits or overwrites a typed draft',()=>{
 const x=load(),before=JSON.stringify(x.store);x.A.open();assert.ok(x.A.session().input.includes(x.c.title));assert.equal(x.A.session().messages.length,0);assert.equal(x.local.size,0);
 x.A.input({id:'ca-question',value:'我自己的问题'});x.A.handle('ca-close','');x.A.open({alertIds:[x.c.alertIds[0]]});assert.equal(x.A.session().input,'我自己的问题');
 x.A.handle('ca-suggest','请核查这项活动');assert.equal(x.A.session().input,'请核查这项活动');assert.equal(x.A.session().messages.length,0);
 x.A.input({id:'ca-question',value:''});x.A.open();assert.equal(x.A.session().input,'');
 x.A.send('已发送的问题');x.A.open();assert.equal(x.A.session().input,'');assert.equal(x.A.session().messages.length,1);assert.equal(JSON.stringify(x.store),before);
 const y=load(),alert=y.store.alerts.find(a=>a.id===y.c.alertIds[0]);y.A.open({alertIds:[alert.id]});assert.ok(y.A.session().input.includes(alert.title));assert.equal(y.A.session().messages.length,0);
});

test('suggestions persist beside the composer after history is restored and only fill the scoped question',()=>{
 const x=load(),before=JSON.stringify(x.store);x.A.open();x.A.send('已有问题');const a=x.store.alerts.find(a=>a.id===x.c.alertIds[0]);
 x.A=x.create();x.A.open({alertIds:[a.id]});const html=x.A.panel();assert.ok(html.includes('已有问题'));assert.equal((html.match(/data-action="ca-suggest"/g)||[]).length,3);assert.ok(html.indexOf('aria-label="建议问题"')>html.indexOf('<form id="ca-question-form"'));assert.ok(!html.includes('ca-welcome'));
 const question=html.match(/data-action="ca-suggest" data-id="([^"]+)"/)[1];assert.ok(question.includes(a.title));x.A.handle('ca-suggest',question);assert.equal(x.A.session().input,question);assert.equal(x.A.session().messages.length,1);assert.equal(JSON.stringify(x.store),before);
});

test('completed human feedback appears beside investigation records in the story and is scoped into assistant references',()=>{
 const x=load(),a=x.store.alerts.find(a=>a.id===x.c.alertIds[0]);x.c.tasks.push({id:'manual-check',title:'确认备份范围',status:'Completed',owner:'Alex',result:'已确认该时间段为授权备份。',completedAt:'2026-11-02T02:00:00Z',referenceContext:{alertIds:[a.id]}});const before=JSON.stringify(x.store);
 const story=x.A.story();assert.ok(story.includes('调查结束'));assert.ok(story.includes('任务完成'));assert.ok(story.includes('询问任务影响'));const timeline=story.split('aria-label="案件告警时间线">')[1].split('</section>')[0];assert.ok(timeline.indexOf('任务完成')<timeline.indexOf('调查结束'));assert.ok(timeline.indexOf('调查结束')<timeline.indexOf('data-ca-select='));const ordered=x.A.storyRows(x.c);assert.ok(timeline.indexOf(ordered[0].title)<timeline.indexOf(ordered.at(-1).title));x.A.open({taskId:'manual-check'});assert.ok(x.A.panel().includes('理解任务影响'));x.A.send('人工反馈对已有结论有什么影响？');assert.ok(x.A.panel().includes('已确认该时间段为授权备份。'));assert.equal(x.A.session().messages[0].context.taskId,'manual-check');assert.equal(JSON.stringify(x.store),before);
 x.A.open({alertIds:[x.c.alertIds[1]]});x.A.send('查看其他活动');const tail=x.A.panel().split('其他活动').at(-1);assert.ok(!tail.includes('已确认该时间段为授权备份。'));
});
