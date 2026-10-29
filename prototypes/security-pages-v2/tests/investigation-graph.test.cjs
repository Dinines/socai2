const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function setup(){const c={window:{},document:{},structuredClone};vm.createContext(c);for(const name of ['persisted-case-data','investigation-graph'])vm.runInContext(fs.readFileSync(path.join(__dirname,'..',name+'.js'),'utf8'),c);const d=c.window.persistedCaseData;return {c,M:c.window.investigationGraphModel,run:structuredClone(d.runs[0]),store:{alerts:structuredClone(d.alerts)}};}
const clean=x=>JSON.parse(JSON.stringify(x));
test('unified graph preserves frozen inputs, candidates, source predicates and missing intermediate edges',()=>{
 const {M,run,store}=setup(),before=JSON.stringify({run,store}),g=M.build(run,store),s=M.defaults();
 assert.equal(g.nodes.length,13);assert.equal(g.edges.length,14);assert.equal(g.inputs.length,3);assert.equal(g.candidates.length,5);
 assert.deepEqual(clean(g.candidates),run.graphs.attack_chain.data.chain.map(c=>c.alert_id));
 const e3=g.nodes.find(n=>n.candidate?.distance===2);assert.ok(e3);assert.equal(g.edges.filter(e=>[e.from,e.to].includes(e3.id)).length,0);
 const shared=g.edges.find(e=>e.sources.some(s=>s.type==='OBSERVED_ON')&&e.sources.some(s=>s.type==='TOUCHES'));assert.ok(shared);assert.equal(shared.sources[0].material,'attack_path');
 assert.equal(M.visible(g,s).nodes.length,10);assert.equal(M.visible(g,s).edges.length,12);assert.equal(JSON.stringify({run,store}),before);
});
test('alert focus is one-hop plus secondary sharing; selecting an edge focuses only that edge',()=>{
 const {M,run,store}=setup(),g=M.build(run,store),s=M.defaults(),a=g.nodes.find(n=>n.code==='A2');
 const pos=clean([...M.positions(g,s).pos]);M.select(g,s,a.id,'alert');let f=M.focus(g,s);assert.equal(f.edgeIds.size,4);assert.equal(f.direct.size,5);assert.equal(f.related.size,7);
 const edge=g.edges.find(e=>e.from===a.id&&e.sources.some(s=>s.type==='OBSERVED_ON'));M.select(g,s,edge.id,'edge');f=M.focus(g,s);assert.equal(f.edgeIds.size,1);assert.equal(f.direct.size,2);assert.deepEqual(clean([...M.positions(g,s).pos]),pos);
 s.entity=false;M.reconcile(g,s);assert.equal(s.selected,null);assert.match(s.message,/已隐藏/);
 M.select(g,s,edge.id,'edge');assert.equal(s.entity,true);assert.equal(M.focus(g,s).edgeIds.size,1);
});
test('external candidate selection and hidden endpoint restore do not change seed or membership',()=>{
 const {M,run,store}=setup(),g=M.build(run,store),s=M.defaults(),before=JSON.stringify(run),edge=g.edges.find(e=>e.layer==='chain');s.entity=false;s.hidden=['ip'];
 M.select(g,s,edge.id,'edge');assert.equal(s.chain,true);assert.equal(s.entity,true);assert.ok(!s.hidden.includes('ip'));assert.equal(M.focus(g,s).edgeIds.size,1);
 assert.equal(g.seed,run.graphs.attack_chain.data.seed_alert_id);assert.equal(JSON.stringify(run),before);
 s.chain=false;M.reconcile(g,s);assert.equal(s.selected,null);
});
test('relational fallback keeps Case-level techniques out of precise alert highlighting',()=>{
 const {M,run,store}=setup();run.graphs.attack_path.source='postgres_fallback';run.graphs.attack_path.fallback=true;
 const g=M.build(run,store);assert.equal(g.caseTech.length,3);assert.equal(g.nodes.filter(n=>n.kind==='tech').length,0);assert.ok(g.edges.every(e=>e.layer!=='tech'));assert.equal(run.graphs.attack_path.data.edges.filter(e=>e.type==='MAPS_TO').length,3);
});
test('tenant mismatch and ambiguous natural keys are not merged',()=>{
 const {M,run,store}=setup();run.graphs.attack_chain.data.tenant_id='other';let g=M.build(run,store);assert.equal(g.candidates.length,0);assert.equal(g.chainMismatch,true);
 run.graphs.attack_chain.data.tenant_id=run.sourceTenantId;const host=run.graphs.attack_path.data.nodes.find(n=>n.label==='Host');run.graphs.attack_path.data.nodes.push({...host,id:'duplicate-host'});
 g=M.build(run,store);assert.ok(g.nodes.some(n=>n.id==='pg:endpoint:'+host.properties.hostname));
 const stranger={...store.alerts[0],title:'WRONG ENV',sourceEnvironment:'other'};store.alerts=[stranger,...store.alerts.slice(1)];g=M.build(run,store);assert.ok(g.nodes.every(n=>n.label!=='WRONG ENV'));
 host.properties.tenant_id='other';g=M.build(run,store);assert.ok(!g.nodes.some(n=>n.id===host.id));
});
test('grouped entities retain endpoint identities and selection counts; presentation never edits source',()=>{
 const {M,run,store}=setup(),g=M.build(run,store),s=M.defaults();s.grouped=true;const a=g.nodes.find(n=>n.code==='A2');M.select(g,s,a.id,'alert');const d=M.display(g,s),group=d.nodes.find(n=>n.id==='group:ip');assert.equal(group.members.length,2);assert.equal(group.members.filter(id=>M.focus(g,s).direct.has(id)).length,1);
 assert.ok(d.edges.some(e=>e.drawTo==='group:ip'));assert.ok(d.edges.every(e=>g.edges.some(raw=>raw.id===e.id&&raw.to===e.to)));
 s.expanded=['ip'];assert.ok(!M.display(g,s).nodes.some(n=>n.id==='group:ip'));
});
test('controller state is isolated per Run and escaped labels cannot become markup',()=>{
 const {c,M,run,store}=setup();const esc=v=>String(v??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));const ui=c.window.createUnifiedInvestigationGraph({store,esc,I:()=>'',severity:esc,state:esc,format:v=>v||'未记录',getAlert:id=>store.alerts.find(a=>a.id===id),render(){}});
 ui.render(run);const g=M.build(run,store),a=g.nodes.find(n=>n.code==='A2');ui.handle('ug-node',a.id);let html=ui.render(run);assert.match(html,/3 条实体关联 · 1 条技术映射/);
 const second={...run,id:'different-run',alertIds:[],graphs:{}};html=ui.render(second);assert.match(html,/全部关系/);assert.ok(!html.includes(a.label));
 const host=run.graphs.attack_path.data.nodes.find(n=>n.label==='Host');host.properties.hostname='<img src=x onerror=attack()>';html=ui.render(run);assert.ok(html.includes('&lt;img'));assert.ok(!html.includes('<img'));
});
