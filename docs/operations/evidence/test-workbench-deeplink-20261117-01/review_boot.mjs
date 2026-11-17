// Executes the actual viewer start/navigation/read/render functions in a minimal
// in-memory DOM. Saved HTTP bodies are replayed; list pagination is controlled.
// This is a direct navigation probe, not a browser layout or real HTTP claim.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../../..');
const evidence=path.dirname(fileURLToPath(import.meta.url));
const base=path.join(root,'docs/operations/evidence/acceptance-fullflow-21-20261117-01');
const owner=path.join(root,'docs/operations/evidence/workbench-deeplink-20261117-01');
const web=path.join(root,'services/investigation_test/web');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const hash=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const clone=o=>JSON.parse(JSON.stringify(o));
const report=read(path.join(owner,'report-01/report.json'));
const caseSubject=report.subjects.find(s=>s.kind==='case');
const casePath='/api/v1/socai2/cases/'+caseSubject.id;
const caps=read(path.join(owner,'http/capabilities.json'));
const caseDetail=read(path.join(owner,'http/case-detail.json'));
const responses=new Map();
function key(value){const u=new URL(value,'http://replay.invalid');u.searchParams.delete('limit');u.searchParams.sort();return u.pathname+u.search;}
const receipts=[];
for(const part of ['part1','part2'])for(const file of fs.readdirSync(path.join(base,'results/prepared/runs',part,'http'))){
  if(!file.endsWith('.json'))continue;
  const row=read(path.join(base,'results/prepared/runs',part,'http',file));
  if(row.request.method==='GET'&&row.response?.status===200)receipts.push(row);
}
receipts.sort((a,b)=>a.ended_at.localeCompare(b.ended_at));
for(const row of receipts)responses.set(key(row.request.path),row.response.body);
for(const row of read(path.join(root,'docs/operations/evidence/workbench-test-source-20261117-01/live-traces.json')).reads)
  responses.set(key(row.path),row.body);
const moduleNames=['viewer_state.mjs','execution_flow.mjs','frozen_sources.mjs','test_sources.mjs','viewer_links.mjs'];
const modules=Object.fromEntries(await Promise.all(moduleNames.map(async name=>[name,await import(pathToFileURL(path.join(web,name)))])));
const source=fs.readFileSync(path.join(web,'viewer.js'),'utf8');
const executable=source.replace(/^import \{([^}]+)\} from '\.\/([^']+)';$/gm,(_,names,name)=>`const {${names}}=modules[${JSON.stringify(name)}];`)
  .replace('start().catch(showError);','globalThis.bootPromise=start().catch(showError);');
const sourceFiles=['viewer.js',...moduleNames];
const before=Object.fromEntries(sourceFiles.map(f=>[f,hash(path.join(web,f))]));

class Element{
  constructor(tag='div'){this.tagName=tag;this.children=[];this.dataset={};this.hidden=false;this.attrs={};this._text='';this.className='';this.listeners={};this.classList={add:()=>{},toggle:()=>{}};}
  set textContent(v){this._text=String(v);this.children=[];}
  get textContent(){return this._text+this.children.map(c=>typeof c==='string'?c:c.textContent).join('');}
  append(...children){for(const c of children){this.children.push(c);if(typeof c==='object')c.parent=this;}}
  replaceChildren(...children){this.children=[];this._text='';this.append(...children);}
  setAttribute(k,v){this.attrs[k]=v;}
  addEventListener(k,v){this.listeners[k]=v;}
  querySelector(){return null;}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);}
  scrollIntoView(){}
}
const drain=async()=>{for(let i=0;i<20;i++)await new Promise(resolve=>setImmediate(resolve));};
async function boot(search,{missingCase=false}={}){
  const elements=new Map(),listeners={},requests=[];
  const doc={hidden:false,getElementById:id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},
    createElement:tag=>new Element(tag),createDocumentFragment:()=>new Element('fragment'),querySelectorAll:()=>[],addEventListener:(k,v)=>listeners[k]=v};
  globalThis.document=doc;
  const location={origin:'http://replay.invalid',pathname:'/viewer/',search};
  const window={history:{replaceState:(_a,_b,uri)=>{const u=new URL(uri,location.origin);location.pathname=u.pathname;location.search=u.search;}}};
  const fetcher=async(input,options={})=>{
    assert.equal(options.method??'GET','GET');const u=new URL(input,location.origin);requests.push(u.pathname+u.search);
    let body,status=200;
    if(u.pathname==='/viewer/config.json')body={viewer_version:'review',request_timeout_seconds:15,poll_interval_seconds:30,page_size:100,test_source_prefixes:['telemetry-channel-02']};
    else if(u.pathname==='/test-api/v1/capabilities')body=caps;
    else if(u.pathname==='/test-api/v1/batches')body={items:[],total:0,next_cursor:null};
    else if(u.pathname==='/api/v1/socai2/cases')body={items:[],next_cursor:null}; // deliberately outside first page
    else if(u.pathname===casePath){status=missingCase?404:200;body=missingCase?{detail:'controlled missing subject'}:caseDetail;}
    else if(u.pathname==='/api/v1/socai2/analysis-runs'){
      assert.equal(u.searchParams.get('subject_id'),caseSubject.id);
      const second=u.searchParams.has('cursor'),r=caseSubject.rounds[second?0:1];
      body={items:[{subject_type:'case',subject_id:caseSubject.id,run_id:r.run_id,task_id:r.task_ids[0],state:r.state,
        started_at:r.started_at,detail_url:`${casePath}/runs/${r.run_id}`}],next_cursor:second?null:'controlled-page-2'};
    }else if(u.pathname===casePath+'/analysis-tasks'){
      body={items:caseSubject.rounds.map(r=>responses.get(key(`${casePath}/analysis-tasks/${r.task_ids[0]}`))),next_cursor:null};
    }else if(responses.has(key(u)))body=responses.get(key(u));
    else throw new Error('Missing offline fixture: '+u.pathname+u.search);
    return {ok:status===200,status,url:u.href,json:async()=>clone(body),text:async()=>JSON.stringify(body)};
  };
  // Imported ReadScope resolves its default fetch in Node's outer module realm.
  // Bind both realms to the replay transport before starting the real page.
  globalThis.fetch=fetcher;
  const context=vm.createContext({modules,document:doc,window,location,fetch:fetcher,URL,URLSearchParams,AbortController,DOMException,
    setTimeout,clearTimeout,Blob,console});
  vm.runInContext(executable,context,{filename:'viewer.js'});await context.bootPromise;await drain();
  const state=()=>JSON.parse(vm.runInContext(`JSON.stringify({selectedRun:selected?.mapping?.run_id??null,requestedRun,reportTarget,detailObserved,
    source:roundSources.get('case:${caseSubject.id}')?.get(selected?.mapping?.run_id)??null})`,context));
  return {state,elements,requests,doc,listeners,location,context};
}
const checks=[];
async function check(name,fn){try{checks.push({name,status:'passed',details:await fn()});}catch(error){checks.push({name,status:'failed',error:error.stack});}}
for(const [i,round] of caseSubject.rounds.entries())await check(`actual_boot_round_${i+1}_outside_first_page`,async()=>{
  const b=await boot(new URL(round.viewer_url).search);
  assert.equal(b.state().selectedRun,round.run_id);
  assert.ok(b.state().detailObserved,b.elements.get('read-status')?.textContent);
  assert.match(b.elements.get('inspection-body').textContent,new RegExp(`本轮输入 ${i+1} 条告警`));
  assert.equal(b.state().source.matched,i+1);
  assert.ok(b.requests.some(p=>p.includes('cursor=controlled-page-2')));
  await b.elements.get('refresh-selection').onclick();await drain();assert.equal(b.state().selectedRun,round.run_id);assert.ok(b.state().detailObserved);
  b.doc.hidden=true;b.listeners.visibilitychange();b.doc.hidden=false;b.listeners.visibilitychange();await drain();assert.equal(b.state().selectedRun,round.run_id);
  const again=await boot(b.location.search);assert.equal(again.state().selectedRun,round.run_id);assert.ok(again.state().detailObserved);
  return {run_id:round.run_id,frozen_members:i+1,source_matched:i+1,refresh_reload_visibility:'passed',request_count:b.requests.length};
});
await check('invalid_or_foreign_targets_never_open_latest',async()=>{
  const first=new URL(caseSubject.rounds[0].viewer_url),incident=report.subjects.find(s=>s.kind==='incident');
  const variants=[];
  for(const run of ['00000000-0000-0000-0000-000000000099',incident.rounds[0].run_id]){
    const u=new URL(first);u.searchParams.set('run_id',run);variants.push(u.search);
  }
  const wrong=new URL(first);wrong.searchParams.set('environment','wrong');variants.push(wrong.search,'?subject_type=case');
  for(const search of variants){const b=await boot(search);assert.equal(b.state().selectedRun,null);assert.equal(b.requests.filter(p=>p.includes('/runs/')).length,0);assert.match(b.elements.get('tab-content').textContent,/未改选|环境|无效/);}
  return {controlled_negative_variants:variants.length};
});
await check('missing_subject_does_not_open_run',async()=>{
  const b=await boot(new URL(caseSubject.rounds[0].viewer_url).search,{missingCase:true});assert.equal(b.state().selectedRun,null);
  assert.match(b.elements.get('tab-content').textContent,/指定主体.*未读到/);return {run_requests:b.requests.filter(p=>p.includes('/runs/')).length};
});
await check('explicit_round_change_updates_target_and_refresh',async()=>{
  const b=await boot(new URL(caseSubject.rounds[0].viewer_url).search);
  const walk=e=>[e,...(e.children??[]).filter(x=>typeof x==='object').flatMap(walk)];
  const select=walk(b.elements.get('inspection-body')).find(e=>e.tagName==='select');assert.ok(select);
  select.value=caseSubject.rounds[1].run_id;select.onchange();await drain();assert.equal(b.state().selectedRun,caseSubject.rounds[1].run_id);assert.ok(b.state().detailObserved);
  assert.equal(new URLSearchParams(b.location.search).get('run_id'),caseSubject.rounds[1].run_id);
  await b.elements.get('refresh-selection').onclick();await drain();assert.equal(b.state().selectedRun,caseSubject.rounds[1].run_id);
  return {run_id:b.state().selectedRun};
});
const after=Object.fromEntries(sourceFiles.map(f=>[f,hash(path.join(web,f))]));
const result={status:checks.every(c=>c.status==='passed')&&JSON.stringify(before)===JSON.stringify(after)?'passed':'needs_review',checks,
  evidence_kind:'actual_viewer_functions_with_minimal_memory_DOM_and_saved_HTTP_replay',
  controlled_inputs:['empty first Case list','two-page directory derived from saved actual rounds','missing/foreign target and missing subject','legacy prefix explicitly enabled only in memory'],
  source_before:before,source_after:after,network_calls:0,business_writes:0,model_calls:0,
  not_verified:['real browser layout','new deployed 21 page','model content quality']};
const target=path.join(evidence,process.argv[2]??'boot-review-01.json');fs.writeFileSync(target,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:result.status,checks:checks.map(c=>[c.name,c.status,c.error?.split('\n')[0]])}));
