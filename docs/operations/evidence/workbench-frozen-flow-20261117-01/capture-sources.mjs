// Read-only live verification of the same saved 02 identities used by the page.
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {loadCaseSources,readSourceExecution,checkArtifact} from '../../../../services/investigation_test/web/frozen_sources.mjs';
import {originalChoices} from '../../../../services/investigation_test/web/execution_flow.mjs';
const [profileFile,output]=process.argv.slice(2);
const profile=JSON.parse(await readFile(profileFile,'utf8'));
const config=JSON.parse(await readFile(profile.upstream_file,'utf8'));
const old=JSON.parse(await readFile(new URL('../streaming-fullflow-20261116-02/final-http-01.json',import.meta.url),'utf8')).value.http;
await mkdir(output,{recursive:false});
const responses=[],cache=new Map();
async function readBody(path) {
  if(cache.has(path))return cache.get(path);
  const response=await fetch(config.base_url+path,{signal:AbortSignal.timeout(config.read_timeout_seconds*1000)});
  const raw=await response.text(),name=`${String(responses.length+1).padStart(3,'0')}.json`;
  await writeFile(`${output}/${name}`,raw);
  responses.push({path,status:response.status,file:name,sha256:createHash('sha256').update(raw).digest('hex')});
  if(!response.ok)throw new Error(`${path}: ${response.status}`);
  const result={data:JSON.parse(raw),raw};cache.set(path,result);return result;
}
async function readPages(path,identity) {
  const items=[],seen=new Set();let cursor=null;
  do {
    const url=new URL(path,config.base_url);url.searchParams.set('limit',String(profile.viewer.page_size));
    if(cursor)url.searchParams.set('cursor',cursor);
    const {data}=await readBody(url.pathname+url.search);
    if(identity && ['run_id','subject_type','subject_id'].some(k=>identity[k]!==data[k]))throw new Error('directory identity mismatch');
    items.push(...data.items);cursor=data.next_cursor;
    if(cursor&&seen.has(cursor))throw new Error('repeated cursor');seen.add(cursor);
  }while(cursor);
  return items;
}
const casePaths=[...new Set(old.filter(r=>/^\/api\/v1\/socai2\/cases\/[^/]+\/runs\/[^/]+$/.test(r.path)).map(r=>r.path))];
const cases=[],sources=new Map(),originals=[];
for(const path of casePaths) {
  const {data}=await readBody(path),artifacts=await readPages(data.artifacts_url,{subject_type:'case',subject_id:data.run.case_id,run_id:data.run.id});
  const frozen=await loadCaseSources({run:data.run,artifacts,previousUrl:data.previous_run_url,readBody,readPages});
  if(frozen.issues.length)throw new Error(frozen.issues.join('; '));
  cases.push({run_id:data.run.id,case_id:data.run.case_id,manifest_id:frozen.current.manifestRef.id,c1_id:frozen.current.ref.id,
    sources:frozen.entries.map(e=>({kind:e.kind,id:e.id,run_id:e.runId,relation:e.relation,coverage:e.coverage}))});
  for(const entry of frozen.entries)if(!sources.has(entry.runId)) {
    const source=await readSourceExecution(entry,readBody,readPages);
    if(source.issues.length)throw new Error(source.issues.join('; '));
    sources.set(entry.runId,{kind:entry.kind,id:entry.id,run_id:source.run.id,steps:source.steps.length,artifacts:source.artifacts.length});
    for(const ref of source.artifacts.filter(a=>a.kind==='source_snapshot')) {
      const body=(await readBody(ref.content_url)).data,content=checkArtifact(ref,body),choices=originalChoices(content);
      if(choices)originals.push({run_id:source.run.id,artifact_id:ref.id,content_url:ref.content_url,
        choices:choices.map(c=>({finish_reason:c.finish_reason,sha256:createHash('sha256').update(c.message?.content??'').digest('hex')}))});
    }
  }
  if(data.run.id==='30c0c38c-ee33-4073-bd94-566a73017fed') {
    const steps=await readPages(data.steps_url),c6=steps.find(s=>s.stage_code==='C6'&&s.kind==='model');
    for(const ref of artifacts.filter(a=>a.step_id===c6?.id&&a.kind==='source_snapshot')) {
      const choices=originalChoices(checkArtifact(ref,(await readBody(ref.content_url)).data));
      if(choices)originals.push({run_id:data.run.id,artifact_id:ref.id,content_url:ref.content_url,
        choices:choices.map(c=>({finish_reason:c.finish_reason,sha256:createHash('sha256').update(c.message?.content??'').digest('hex')}))});
    }
  }
}
const report={state:'passed',observed_at:new Date().toISOString(),environment:config.environment_label,cases,
  sources:[...sources.values()],originals,responses,http_get_count:responses.length,business_writes:0,model_calls:0,
  boundary:'Read-only existing 02 identities. No new execution or database-wide audit.'};
await writeFile(`${output}/index.json`,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({state:report.state,cases:cases.length,sources:sources.size,originals:originals.length,http_get_count:responses.length}));
