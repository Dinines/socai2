'use strict';
// Read-only comparison and rendering of one saved batch through the original app.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const [folderArg,pageArg,receiptArg]=process.argv.slice(2);
assert.ok(folderArg&&pageArg&&receiptArg,'provide export folder, generated page data and receipt');
const folder=path.resolve(folderArg),page=path.resolve(pageArg),root=path.dirname(page);
const read=name=>fs.readFileSync(path.join(folder,name));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const canon=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
let comparisons=0;
const same=(a,b,label)=>{assert.equal(canon(a),canon(b),label);comparisons++;};
const manifest=JSON.parse(read('manifest.json')),db=JSON.parse(read('database.json')),responses=JSON.parse(read('api-responses.json'));
for(const source of manifest.sources)assert.equal(hash(read(source.file)),source.sha256);
assert.equal(hash(read('database.json')),manifest.source_sha256);
const saved={window:{}};vm.runInNewContext(fs.readFileSync(page,'utf8'),saved);const data=saved.window.socai2RecordedData;
const original=JSON.stringify(data),runs=new Map(data.runs.map(r=>[r.sourceRunId,r]));
for(const row of db.runs)same(runs.get(row.id).sourceRecord.run,row,'Run source');
for(const row of db.run_steps)same(runs.get(row.run_id).steps.find(s=>s.payload.source_step.id===row.id).payload.source_step,row,'Step source');
for(const row of db.artifacts){
 if(!row.run_id){same(data.sourceArtifacts.find(a=>a.sourceRecord.id===row.id).sourceRecord,row,'Source snapshot');continue;}
 const run=runs.get(row.run_id),a=run.artifacts.find(a=>a.sourceArtifactId===row.id),body=run.artifactBodies[a.id];
 const {content_json,content_text,...metadata}=row;same(a.sourceRecord,metadata,'Artifact metadata');
 if(content_json!==null)same(body.content,content_json,'Artifact JSON');
 else if(content_text!==null)same(body.content,content_text,'Artifact text');
 assert.equal(a.sha256,row.sha256);
}
const app={innerHTML:''},handlers=new Map(),writes=[];
const s={window:{addEventListener:(n,f)=>handlers.set(n,f),scrollTo(){}},document:{activeElement:null,addEventListener(){},querySelector:q=>q==='#app'?app:null,getElementById(){return null;}},location:{hash:`#/cases/${data.cases[0].id}/case-info`,search:''},localStorage:{getItem:()=>null,setItem:(...args)=>writes.push(args)},structuredClone,URLSearchParams,clearInterval};
vm.createContext(s);
const index=fs.readFileSync(path.join(root,'index.html'),'utf8');
for(const file of [...index.matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)].map(m=>m[1]))vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),s,{filename:file});
function render(route){const oldURL='http://local.invalid/'+s.location.hash;s.location.hash=route;handlers.get('hashchange')({oldURL,newURL:'http://local.invalid/'+route});assert.ok(app.innerHTML.length>0);assert.ok(!/Invalid Date|>undefined<|>null</.test(app.innerHTML),route);return app.innerHTML;}
const rendered=[];
for(const alert of data.alerts)for(const tab of ['overview','timeline','raw','response']){const route=`#/alerts/${alert.id}/${tab}`,html=render(route);assert.ok(html.includes(alert.title));rendered.push(route);}
for(const incident of data.incidents)for(const tab of ['summary','attack','alerts','assets','activities']){const route=`#/incidents/${incident.id}/${tab}`,html=render(route);assert.ok(html.includes(incident.title));rendered.push(route);}
const cas=data.cases[0],baseline=data.runs.find(r=>r.investigationKind==='baseline');
for(const tab of ['case-info','story','overview','alerts','attack','evidence','tasks','activities','comments']){const route=`#/cases/${cas.id}/${tab}`,html=render(route);assert.ok(html.includes(cas.title));rendered.push(route);}
for(const view of ['overview','process','graphs','report','ledger']){const route=`#/cases/${cas.id}/investigations?run=${encodeURIComponent(baseline.id)}&view=${view}`;render(route);rendered.push(route);}
const caseHtml=render(`#/cases/${cas.id}/case-info`),graphHtml=render(`#/cases/${cas.id}/attack`),ledgerHtml=render(`#/cases/${cas.id}/investigations?run=${encodeURIComponent(baseline.id)}&view=ledger`);
assert.ok(caseHtml.includes('调查系统收尾'));assert.ok(caseHtml.includes('0 / 3'));assert.ok(caseHtml.includes('独立证据条目'));
assert.ok(graphHtml.includes('汇总未通过'));assert.ok(ledgerHtml.includes('model_view_not_ready'));
assert.equal(db.case_assessment_members.length,0);assert.equal(data.evidence.length,0);assert.equal(data.cases[0].tasks.length,0);
assert.equal(JSON.stringify(data),original);assert.equal(writes.length,0);
for(const source of manifest.sources)assert.equal(hash(read(source.file)),source.sha256);
const result={batch_id:manifest.batch_id,source_sha256:manifest.source_sha256,page_sha256:hash(fs.readFileSync(page)),source_comparisons:comparisons,rendered_routes:rendered,render_count:rendered.length,api_statuses:responses.map(r=>({path:r.path,status:r.status})),counts:{alerts:db.alerts.length,incidents:db.incidents.length,cases:db.cases.length,runs:db.runs.length,steps:db.run_steps.length,artifacts:db.artifacts.length,raw_objects:db.alert_objects.length,display_objects:data.assets.length,evidence:data.evidence.length,tasks:db.tasks.length,activities:db.activities.length,display_activities:db.activities.length+db.run_steps.length+db.alerts.length},verified:['source hashes unchanged','Run/Step/artifact originals preserved','actual system closing and zero model coverage displayed','graph explicitly incomplete','empty evidence and tasks retained','no UI storage writes'],limitations:['static export, not live API binding','Case detail GET failed with HTTP 500; freshness was not invented','model quality and full Case delivery not passed']};
fs.writeFileSync(receiptArg,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({comparisons,rendered_routes:rendered.length,counts:result.counts,receipt:receiptArg}));
