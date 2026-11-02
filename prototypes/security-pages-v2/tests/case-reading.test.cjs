const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function load(){
 const listeners=new Map(),s={window:{addEventListener(){}},document:{addEventListener(name,fn,capture){listeners.set(name,{fn,capture});}},location:{hash:'#/cases'},localStorage:{getItem:()=>null},structuredClone,URLSearchParams,clearInterval};vm.createContext(s);
 const files=[...fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)].map(m=>m[1]);
 for(const f of files){let code=fs.readFileSync(path.join(root,f),'utf8');if(f==='app.js')code=code.replace('readQueueLink();render();\n})();','window.api={store,ui,casePage,caseQueue,incidentCaseAction,modalMarkup,fullAlert,drawerMarkup,investigationView};\n})();');vm.runInContext(code,s);}
 return {...s.window.api,s,listeners,M:s.window.investigationWorkspaceModel};
}
test('all Case homes share the overview while keeping every Run and stored data unchanged',()=>{
 const x=load(),before=JSON.stringify([x.store,x.M.runs(x.store)]);
 for(const c of x.store.cases){
  x.s.location.hash=`#/cases/${c.id}/overview`;const html=x.casePage();
  assert.ok(html.includes('iv-case-home'));assert.ok(html.includes('人工任务'));assert.ok(!html.includes('iv-run-selector'));
  assert.equal((html.match(/class="case-nav-button /g)||[]).length,10);
  assert.ok(!/Invalid Date|>undefined<|>null</.test(html),c.id);
  for(const r of x.M.forCase(x.store,c))assert.ok(html.includes(`run=${encodeURIComponent(r.id)}`),r.id);
 }
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);
});
test('Case member counts stay separate from frozen inputs and explicit old Run URLs remain valid',()=>{
 const x=load(),c=x.store.cases.find(c=>c.id==='17420'),r=x.M.forCase(x.store,c)[0],frozen=JSON.stringify(r);
 c.alertIds=x.store.alerts.map(a=>a.id);x.s.location.hash=`#/cases/${c.id}/overview`;
 const home=x.casePage();assert.ok(home.includes(`当前成员 <b>${c.alertIds.length}</b>`));assert.ok(home.includes('查看全部调查历史'));x.s.location.hash=`#/cases/${c.id}/investigations`;assert.ok(x.casePage().includes(`run=${r.id}`));
 x.s.location.hash=`#/cases/${c.id}/overview?run=${r.id}&view=tools`;const legacy=x.casePage();assert.ok(legacy.includes('iv-run-selector'));assert.ok(legacy.includes('返回调查概览'));assert.ok(legacy.includes('输入告警携带的证据'));
 assert.equal(JSON.stringify(x.M.forCase(x.store,c).find(row=>row.id===r.id)),frozen);
});
test('analysis references open exactly one same-Run query and preserve unavailable returns',()=>{
 const x=load(),r=x.s.window.pageShowcaseData.runs.find(r=>r.id==='showcase-run-02'),t=r.tools[1],before=JSON.stringify([x.store,r]);
 x.s.location.hash=`#/investigations/${r.id}/process`;let html=x.investigationView.workbench();
 assert.ok(html.includes(`/tools?query=${t.id}&from=process`));assert.ok(html.includes('阶段引用'));assert.ok(html.includes('资料不可用'));
 x.s.location.hash=`#/investigations/${r.id}/tools?query=${t.id}&from=process`;html=x.investigationView.workbench();
 assert.ok(html.includes('当前引用的查询'));assert.ok(html.includes('查看本轮全部查询'));assert.ok(html.includes('返回AI 分析'));
 assert.ok(html.includes(`<h3>2. ${t.name}</h3>`));assert.ok(!html.includes(`<h3>1. ${r.tools[0].name}</h3>`));
 assert.ok(html.includes('未取得完整文件传输清单'));assert.ok(!html.includes('未匹配记录'));
 assert.equal(JSON.stringify([x.store,r]),before);
});
test('foreign references are not linked and invalid query IDs never fall back to another Run',()=>{
 const x=load(),r=x.s.window.pageShowcaseData.runs.find(r=>r.id==='showcase-run-02'),other=x.s.window.pageShowcaseData.runs.find(r=>r.id==='showcase-run-01');
 const foreign=other.tools[0].id;r.steps.find(s=>s.adopted).adopted.evidence_ids.push(foreign,'<img src=x onerror=alert(1)>');
 x.s.location.hash=`#/investigations/${r.id}/process`;let html=x.investigationView.workbench();
 assert.ok(html.includes('未保存对应条目'));assert.ok(!html.includes(`query=${foreign}`));assert.ok(html.includes('&lt;img'));assert.ok(!html.includes('<img src=x'));
 x.s.location.hash=`#/investigations/${r.id}/tools?query=${foreign}`;html=x.investigationView.workbench();
 assert.ok(html.includes('本次调查中没有该查询'));assert.ok(!html.includes(`<h3>1. ${r.tools[0].name}</h3>`));assert.ok(!html.includes(other.report));
});
test('changing Run keeps the detail view and clears old query and artifact selections',()=>{
 const x=load(),runs=x.M.forCase(x.store,x.store.cases.find(c=>c.id==='17420'));
 x.s.location.hash=`#/cases/17420/investigations?run=${runs[0].id}&view=tools&query=old&artifact=old&from=process`;
 x.investigationView.change({value:runs[1].id,hasAttribute:k=>k==='data-iv-run'});
 assert.equal(x.s.location.hash,`#/cases/17420/investigations?run=${runs[1].id}&view=tools`);
 const html=x.casePage();assert.ok(!html.includes('本次调查中没有该查询'));
 for(const title of ['调查发现','AI 分析','查询与证据','调查关系图','报告与响应'])assert.ok(html.includes(`>${title}`),title);
});

test('Case defaults to information first while explicit overview and Run deep links stay available',()=>{
 const x=load(),before=JSON.stringify([x.store,x.M.runs(x.store)]);
 for(const c of x.store.cases){
  x.s.location.hash=`#/cases/${c.id}`;const html=x.casePage(),nav=html.match(/<nav class="case-nav"[\s\S]*?<\/nav>/)[0];
  assert.ok(html.includes('case-context-home'),c.id);assert.ok(!html.includes('iv-case-home'));
  assert.equal(nav.match(/href="([^"]+)"/)[1],`#/cases/${c.id}/case-info`);
  assert.ok(nav.includes(`selected" href="#/cases/${c.id}/case-info" aria-current="page"`));
  assert.equal((nav.match(/class="case-nav-button /g)||[]).length,10);
 }
 const c=x.store.cases.find(c=>c.id==='17420'),r=x.M.forCase(x.store,c)[0];
 x.s.location.hash=`#/cases/${c.id}?run=${r.id}&view=tools`;assert.ok(x.casePage().includes('iv-run-selector'));
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);
});
test('Case stage coverage counts only current members, preserving missing categories and empty state',()=>{
 const x=load();
 for(const c of x.store.cases){
  x.s.location.hash=`#/cases/${c.id}/case-info`;const html=x.casePage(),coverage=html.match(/<article[^>]*aria-label="ATT&CK 阶段覆盖"[\s\S]*?<\/article>/)[0];
  const alerts=x.store.alerts.filter(a=>c.alertIds.includes(a.id)),counts=new Map();for(const a of alerts){const n=String(a.category||'').trim()||'未分类';counts.set(n,(counts.get(n)||0)+1);}
  for(const [name,n] of counts)assert.ok(coverage.replace(/<span class="tactic-label[^"]*">/g,'<span>').includes(`<span>${name}</span><span><b>${n}</b> 条告警</span>`),c.id+' '+name);
  assert.ok(coverage.includes('不代表检测覆盖率或攻击成功'));assert.ok(html.indexOf('ATT&CK 阶段覆盖')>html.indexOf('Case 详细信息'));assert.ok(html.includes('<aside class="stack">'));
 }
 const c=x.store.cases.find(c=>c.id==='17420'),a=x.store.alerts.find(a=>c.alertIds.includes(a.id)),runs=JSON.stringify(x.M.runs(x.store));
 x.s.location.hash=`#/cases/${c.id}`;c.alertIds=[a.id,a.id];a.category='';assert.ok(x.casePage().replace(/<span class="tactic-label[^"]*">/g,'<span>').includes('<span>未分类</span><span><b>1</b> 条告警</span>'));
 a.category='<script>bad</script>';assert.ok(x.casePage().includes('&lt;script&gt;bad&lt;/script&gt;'));assert.ok(!x.casePage().includes('<script>bad'));
 c.alertIds=[];assert.ok(x.casePage().includes('暂无成员告警'));assert.equal(JSON.stringify(x.M.runs(x.store)),runs);
});
test('generic Case entries use information while the explicit AI action still opens overview',()=>{
 const x=load(),c=x.store.cases.find(c=>c.id==='17420'),inc=x.store.incidents.find(i=>i.id===c.incidentId),a=x.store.alerts.find(a=>c.alertIds.includes(a.id));
 x.caseQueue();x.ui.tables.cases.size=100;assert.ok(x.caseQueue().includes(`href="#/cases/${c.id}/case-info"`));assert.ok(x.incidentCaseAction(inc).includes('/case-info'));
 x.ui.modal={type:'choose-case'};assert.ok(x.modalMarkup().includes(`href="#/cases/${c.id}/case-info"`));
 x.ui.drawer={type:'alert',id:a.id};assert.ok(x.drawerMarkup().includes(`href="#/cases/${c.id}/case-info"`));
 x.s.location.hash=`#/alerts/${a.id}/overview`;assert.ok(x.fullAlert(a).includes(`href="#/cases/${c.id}/case-info"`));
 x.s.location.hash=`#/cases/${c.id}/case-info`;assert.ok(x.casePage().replace(/<svg[\s\S]*?<\/svg>/g,'').includes(`href="#/cases/${c.id}/overview">查看调查结果`));
});


test('Case information shares layout and evidence metrics across all sources without inventing conclusions',()=>{
 const x=load(),before=JSON.stringify([x.store,x.M.runs(x.store)]);
 for(const c of x.store.cases){
  x.s.location.hash=`#/cases/${c.id}/case-info`;const html=x.casePage(),ids=new Set(c.alertIds),ev=x.store.evidence.filter(e=>ids.has(e.alertId));
  assert.ok(html.includes('class="copilot-card"'),c.id);assert.ok(html.includes('折叠或展开摘要'));assert.ok(html.includes('当前案件判断'));
  assert.ok(html.includes(`>告警证据</span><b>${ev.length}</b>`));assert.ok(!html.includes('已保存工件'));assert.ok(!html.includes('次部分交付'));
  for(const title of ['成员告警','涉及对象','调查记录','Case 详细信息','ATT&CK 阶段覆盖'])assert.ok(html.includes(title),c.id+title);
  if(!c.assessment?.conclusion)assert.ok(html.includes('尚未形成案件级判断'));
 }
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);
});
test('all Case relationship views use the latest finished Run or identified member fallback without data mutation',()=>{
 const x=load(),before=JSON.stringify([x.store,x.M.runs(x.store)]);
 for(const c of x.store.cases){
  x.s.location.hash=`#/cases/${c.id}/attack`;Object.assign(x.ui.graph,{associated:true,blast:true,path:'potential-u1-c1',selected:'u1',index:99,hidden:new Set(),severity:'',status:'',source:''});
  const html=x.casePage(),r=x.M.latestFinished(x.M.forCase(x.store,c).filter(r=>r.graphEligible!==false));
  for(const bad of ['data-ws-scope','ws-blast','ws-path','潜在影响路径'])assert.ok(!html.includes(bad),c.id+bad);
  if(r){assert.ok(html.includes(`data-run-id="${r.id}"`),c.id);assert.ok(html.includes('最近一次已完成调查'));for(const id of r.alertIds)assert.ok(html.includes(`data-id="${id}"`));}
  else {assert.ok(html.includes('尚无已完成调查'));assert.ok(html.includes('data-investigation-graph'));for(const m of html.matchAll(/data-action="ug-node" data-id="([^"]+)"/g))assert.ok(c.alertIds.includes(m[1])||x.store.assets.some(a=>a.id===m[1])||m[1].startsWith('tech-'));}
 }
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);
});
test('latest finished selection excludes active and triage Runs, orders by end time and labels missing end time',()=>{
 const x=load(),rows=[{id:'old',status:'completed',started:'2026-10-20',ended:'2026-10-21'}, {id:'partial',status:'completed',completion:'partial',started:'2026-10-21',ended:'2026-10-23'}, {id:'running',status:'running',started:'2026-10-30'}, {id:'triage',status:'completed',completion:'not_escalated',ended:'2026-10-31'}];
 assert.equal(x.M.latestFinished(rows).id,'partial');rows[0].ended='2026-10-24';assert.equal(x.M.latestFinished(rows).id,'old');rows.push({id:'fallback',status:'completed',started:'2026-10-25',ended:null});assert.equal(x.M.latestFinished(rows).id,'fallback');assert.equal(x.M.latestFinished(rows.slice(2,4)),null);
 const c=x.store.cases.find(c=>c.id==='17420'),r=x.M.latestFinished(x.M.forCase(x.store,c).filter(r=>r.graphEligible!==false)),history=JSON.stringify(x.M.runs(x.store));
 const source=x.s.window.designInvestigationRuns.find(v=>v.id===r.id);
 assert.ok(source);source.graphs={};source.ended=null;x.s.location.hash='#/cases/17420/attack';const html=x.casePage();
 assert.ok(html.includes(`data-run-id="${r.id}"`));assert.ok(html.includes('完成时间未记录'));assert.ok(html.includes('基础关系取自本轮输入告警保存的对象关联'));assert.ok(!html.includes('workspace-attack'));
 assert.notEqual(JSON.stringify(x.M.runs(x.store)),history);
});
test('graph materials keep native disclosure through redraws and isolate Run and source selection',()=>{
 const x=load(),before=JSON.stringify([x.store,x.M.runs(x.store)]),base='#/cases/17420/investigations?run=INV-20261024-001&view=graphs';
 const tag=html=>html.match(/<details class="iv-graph-materials"[^>]*>/)[0],open=html=>/ open>/.test(tag(html));
 const native=(html,value)=>x.listeners.get('toggle').fn({target:{isConnected:true,open:value,hasAttribute:k=>k==='data-iv-source-disclosure',getAttribute:()=>tag(html).match(/data-iv-source-disclosure="([^"]+)"/)[1].replaceAll('&quot;','"').replaceAll('&amp;','&')}});
 assert.equal(x.listeners.get('toggle').capture,true);
 x.s.location.hash=base;let html=x.casePage();assert.equal(open(html),false);native(html,true);assert.equal(open(x.casePage()),true);
 x.ui.drawer={type:'alert',id:x.store.cases.find(c=>c.id==='17420').alertIds[0]};assert.equal(open(x.casePage()),true);x.ui.drawer=null;assert.equal(open(x.casePage()),true);
 for(const kind of ['attack_chain','attack_path','alert_graph','all']){
  x.s.location.hash=base+'&graph='+kind;html=x.casePage();assert.equal(open(html),true,kind);assert.ok(html.indexOf('aria-label="关系分析类型"')<html.indexOf('data-investigation-graph'));
  native(html,false);assert.equal(open(x.casePage()),false,kind);native(html,true);
 }
 x.s.location.hash=base.replace('INV-20261024-001','INV-20261024-002');assert.equal(open(x.casePage()),false);
 for(const kind of ['attack_chain','attack_path','alert_graph','all']){const y=load();y.s.location.hash='#/investigations/INV-20261024-001/graphs?graph='+kind;assert.equal(open(y.investigationView.workbench()),true);}
 const keep=x.investigationView.keepGraphMaterialPosition;
 assert.equal(keep(base,base+'&graph=attack_path'),true);assert.equal(keep(base+'&graph=attack_path',base+'&graph=all'),true);
 assert.equal(keep(base,base.replace('001','002')+'&graph=attack_chain'),false);assert.equal(keep(base,base.replace('graphs','tools')),false);assert.equal(keep(base,base+'&graph=invalid'),false);
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);
});

test('saved execution metrics preserve unknown and zero and never use Deep stage latency as Run duration',()=>{
 const x=load(),metrics=x.M.runMetrics;
 assert.deepEqual(JSON.parse(JSON.stringify(metrics({status:'completed',started:'2026-11-02T01:00:00Z',ended:'2026-11-02T01:02:10Z',tools:[{},{}],tokens:0,calls:0,depth:{latency_ms:1}}))),{durationMs:130000,toolRecords:2,calls:0,tokens:0});
 for(const row of [{},{started:'bad',ended:'bad'},{started:'2026-11-03',ended:'2026-11-02'},{started:null,ended:null},{status:'running',started:'2026-11-02',ended:'2026-11-03'}])assert.equal(metrics(row).durationMs,null);
 for(const value of [null,undefined,'',-1,NaN,Infinity]){assert.equal(metrics({tokens:value,calls:value}).tokens,null);assert.equal(metrics({tokens:value,calls:value}).calls,null);}
 const before=JSON.stringify([x.store,x.M.runs(x.store)]);
 for(const c of x.store.cases){x.s.location.hash=`#/cases/${c.id}/investigations`;const html=x.casePage();assert.equal((html.match(/aria-label="本轮执行统计"/g)||[]).length,x.M.forCase(x.store,c).length);assert.ok(!/NaN|Invalid Date/.test(html));}
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);
});

test('overview separates AI progress, saved results and human tasks without a draft section',()=>{
 const x=load(),c=x.store.cases.find(c=>c.id==='explore-case-02'),before=JSON.stringify([x.store,x.M.runs(x.store)]);x.s.location.hash=`#/cases/${c.id}/overview`;const html=x.casePage();
 assert.ok(html.indexOf('aria-label="AI 调查进度"')<html.indexOf('aria-label="已有分析结果"'));assert.ok(!html.includes('cw-active-banner'));assert.ok(!html.includes('cw-plans'));assert.ok(!html.includes('本地演示'));assert.ok(html.includes('补充核对服务账号的授权与备份范围'));assert.ok(html.includes('cw-task-summary'));
 const results=html.split('aria-label="已有分析结果">')[1].split('</section><aside>')[0];assert.ok(!results.includes('run=explore-run-03'));assert.ok(results.includes('run=explore-run-02'));assert.ok(results.includes('基础调查'));
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);
});
test('shared overview omits idle progress and projects human work without writing history',()=>{
 const x=load(),before=JSON.stringify([x.store,x.M.runs(x.store)]);
 for(const c of x.store.cases){x.s.location.hash=`#/cases/${c.id}/overview`;const html=x.casePage(),active=x.M.forCase(x.store,c).some(r=>x.M.activeStatuses.has(r.status));assert.equal(html.includes('aria-label="AI 调查进度"'),active,c.id);assert.equal((html.match(/class="iv-card cw-task-summary"/g)||[]).length,1);assert.ok(!html.includes('cw-plans'));assert.ok(!html.includes('当前没有执行中的调查'));}
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);
});

test('reading an older Run still exposes the active Case investigation',()=>{const x=load(),c=x.store.cases.find(c=>c.id==='explore-case-02');for(const route of ['investigations?run=explore-run-02&view=overview','overview?run=explore-run-02&view=overview']){x.s.location.hash=`#/cases/${c.id}/${route}`;const html=x.casePage();assert.ok(html.includes('cw-active-banner'));assert.ok(html.includes('run=explore-run-03'));}});
