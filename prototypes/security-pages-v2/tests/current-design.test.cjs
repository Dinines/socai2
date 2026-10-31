const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
function load({design=true,saved=null}={}){
 const s={window:{addEventListener(){}},document:{addEventListener(){},querySelector(){return null;}},location:{hash:'#/cases'},localStorage:{getItem:()=>saved},structuredClone,URLSearchParams,clearInterval};vm.createContext(s);
 const files=[...fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)].map(x=>x[1]);
 for(const f of files){if(!design&&f==='design-investigation-data.js')continue;let code=fs.readFileSync(path.join(root,f),'utf8');if(f==='app.js')code=code.replace('readQueueLink();render();\n})();','window.api={store,casePage,investigationView};\n})();');vm.runInContext(code,s);}
 return {...s.window.api,s,M:s.window.investigationWorkspaceModel};
}
test('design materials cover all six views and use valid artifact hashes and fixed inputs',()=>{
 const x=load(),rs=x.M.runs(x.store).filter(r=>r.fixture&&!r.fixtureSet);assert.equal(rs.length,2);
 for(const r of rs){assert.equal(r.recorded,false);assert.ok(r.tools.length>=2);assert.ok(r.report);assert.equal(r.steps.filter(s=>s.adopted).length,4);assert.equal(r.executed.length,0);assert.equal(r.tokens,undefined);assert.equal(r.calls,undefined);for(const a of r.input.alerts)assert.ok(Date.parse(a.last)<=Date.parse(r.started));
  for(const a of r.artifacts){const body=r.artifactBodies[a.id],text=body.format==='json'?JSON.stringify(body.content):body.content;assert.equal(a.sha256,crypto.createHash('sha256').update(text).digest('hex'));assert.equal(a.size_bytes,Buffer.byteLength(text));assert.ok(r.steps.some(s=>s.id===a.event_id));}
  const ids=new Set(r.graphs.attack_path.data.nodes.map(n=>n.id));for(const e of r.graphs.attack_path.data.edges)assert.ok(ids.has(e.source)&&ids.has(e.target));
  for(const view of ['overview','process','tools','graphs','ledger','report']){x.s.location.hash=`#/investigations/${r.id}/${view}`;const html=x.investigationView.workbench();assert.ok(!/Invalid Date|>undefined</.test(html));assert.ok(html.includes(r.title));}
  const original=JSON.stringify(r.input);x.store.alerts.find(a=>a.id===r.alertIds[0]).title='edited current alert';assert.equal(JSON.stringify(x.M.runs(x.store).find(z=>z.id===r.id).input),original);
 }
});
test('adding design materials changes none of the thirteen actual Runs or their source collections',()=>{
 const a=load({design:false}),b=load(),actual=x=>JSON.stringify(x.M.runs(x.store).filter(r=>r.recorded));assert.equal(a.M.runs(a.store).filter(r=>r.recorded).length,13);assert.equal(actual(a),actual(b));
 for(const key of ['alertFlowData','aisoc20RecordedData','persistedCaseData','savedInvestigationRuns'])assert.equal(JSON.stringify(a.s.window[key]),JSON.stringify(b.s.window[key]));
 assert.deepEqual([b.store.alerts.length,b.store.incidents.length,b.store.cases.length,b.M.runs(b.store).length],[78,21,21,18]);
});
test('Case source captions are removed without rewriting raw names, identities or saved edits',()=>{
 const x=load(),original=JSON.stringify(x.store);for(const c of x.store.cases.filter(c=>c.localCollection||c.recordedCase))for(const view of ['overview','case-info','alerts','evidence','activities']){
  x.s.location.hash=`#/cases/${c.id}/${view}`;const html=x.casePage();assert.ok(!/iv-source-notice|AiSOC ·|（本地整理）/.test(html));
 }
 assert.equal(JSON.stringify(x.store),original);
 const c=x.store.cases.find(c=>c.id==='17420');c.title='Analyst edited title';c.tasks=[];
 const y=load({saved:JSON.stringify(x.store)}),edited=y.store.cases.find(row=>row.id===c.id);assert.equal(edited.title,'Analyst edited title');assert.equal(edited.tasks.length,0);
 assert.ok(y.store.cases.find(c=>c.id==='local-aisoc20-1').title.endsWith('（本地整理）'));
});
