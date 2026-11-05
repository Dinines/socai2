/* Loopback-only, in-memory HTTP fixture. Never contacts a real service or model. */
'use strict';
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const ids = Object.fromEntries(['case','target','alert','extra','incident','run','result','task','revision','material','artifact','actor'].map((key,i)=>[key,`00000000-0000-4000-8000-${String(i+1).padStart(12,'0')}`]));
const stamp='2026-11-05T01:00:00Z';
const clone=value=>JSON.parse(JSON.stringify(value));
function fixture() {
  const cas={id:ids.case,title:'模拟验证 · 异常脚本执行',description:'仅用于页面交互验证的内存记录，不代表真实调查结果。',severity:'high',handling_status:'in_progress',assignment_state:'assigned',owner_id:ids.actor,scope_revision:1,business_updated_at:stamp};
  const members=[{alert_id:ids.alert,title:'模拟进程告警',severity:'high',event_time:stamp,latest_material_id:ids.material}];
  const run={id:ids.run,case_id:ids.case,title:'模拟第一轮调查',purpose:'核对脚本执行与授权',kind:'baseline',state:'completed',delivery_state:'partial',requested_at:stamp,started_at:stamp,ended_at:stamp,scope_revision:1};
  const result={id:ids.result,source_run_id:ids.run,case_id:ids.case,title:'模拟第一轮结果',purpose:run.purpose,conclusion:'现有依据不足，需人工确认授权',conclusion_origin:'model',conclusion_state:'available',closing_note:'存在待确认事实',delivery_state:'partial',created_at:stamp,change_summary:'首轮调查，无前次可比较结果',case_impact:{summary:'仅适用于当前一条成员',cannot_generalize:['不能推广到未确认对象']},findings:[{statement:'已观察到进程启动。',state:'observed',support:[],limitations:['不等于脚本执行完成']}],questions:[{text:'是否为授权操作？',state:'unresolved',answer:null}],recommendations:[]};
  const revision={id:ids.revision,task_id:ids.task,revision:1,title:'核对执行授权',description:'向资产负责人确认',assignee_id:null,due_at:null,state:'not_started',result_text:null,result_scope:null,source_refs:[],completed_by:null,completed_at:null,changed_by:ids.actor,changed_at:stamp};
  const task={id:ids.task,case_id:ids.case,current_revision_id:ids.revision,origin_result_id:ids.result,origin_finding_id:null,created_at:stamp,updated_at:stamp,row_version:1,current:revision};
  return {cas,members,runs:[run],results:[result],tasks:[task],revisions:[clone(revision)],freshness:'current',rejectNextTask:false,requests:[],fault:null};
}
function createFixtureServer() {
  const state=fixture(),root=path.resolve(__dirname,'..');
  const server=http.createServer(async(req,res)=>{
    const url=new URL(req.url,'http://127.0.0.1');
    if(!url.pathname.startsWith('/api/v1/socai2')) {
      const file=path.resolve(root,'.'+decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname));
      if(!file.startsWith(root+path.sep)){res.writeHead(403);return res.end();}
      try{const body=fs.readFileSync(file);res.writeHead(200,{'Content-Type':({'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[path.extname(file)]||'application/octet-stream'});return res.end(body);}catch{res.writeHead(404);return res.end();}
    }
    const chunks=[];for await(const chunk of req)chunks.push(chunk);
    let body=null;try{body=chunks.length?JSON.parse(Buffer.concat(chunks).toString()):null;}catch{res.writeHead(400);return res.end('{}');}
    const pathname=url.pathname.slice('/api/v1/socai2'.length),method=req.method;
    // Do not store or print authentication credentials, including synthetic ones.
    state.requests.push({pathname,method,body,query:Object.fromEntries(url.searchParams),hasBearer:req.headers.authorization?.startsWith('Bearer ')});
    const send=(value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(value));};
    if(!req.headers.authorization?.startsWith('Bearer '))return send({detail:'unauthorized'},401);
    if(state.fault)return send({detail:'fixture_unavailable'},state.fault);
    const currentCase=pathname.startsWith('/cases/'+ids.target)?{...state.cas,id:ids.target,title:'模拟目标案件'}:state.cas;
    const baseline_records=state.runs.filter(r=>['running','unknown','pending_update'].includes(r.state)).map(r=>({run:r,start_eligibility:{can_start:r.state==='pending_update'&&!state.runs.some(x=>['running','unknown'].includes(x.state)),reason:state.runs.some(x=>['running','unknown'].includes(x.state))?'baseline_active':'ready'}}));
    if(pathname==='/cases'&&method==='GET')return send({items:[{case:state.cas,member_count:state.members.length,open_task_count:state.tasks.filter(t=>['not_started','in_progress'].includes(t.current.state)).length,baseline_records},{case:{...state.cas,id:ids.target,title:'模拟目标案件'},member_count:0,open_task_count:0,baseline_records:[]}],total:2,next_cursor:null,metrics:{awaiting_assignment:0,in_progress:2,high_severity:2,awaiting_human:1}});
    if(pathname==='/alerts'||pathname==='/incidents')return send({items:[{facts:{id:pathname==='/alerts'?ids.extra:ids.incident,title:pathname==='/alerts'?'模拟新增告警':'模拟关联事件'}}],total:1,next_before_id:null});
    if(pathname==='/cases'&&method==='POST')return send({case_id:ids.case});
    if(pathname.match(/^\/cases\/[^/]+$/))return send({case:currentCase,members:state.members,member_count:state.members.length,members_truncated:false,linked_incidents:[],linked_incident_count:0,linked_incidents_truncated:false,baseline_records,current_assessment:{value:{conclusion:state.results.at(-1).conclusion,formed_at:stamp},members:[{alert_id:ids.alert}],members_truncated:false,sources:[{result_id:state.results.at(-1).id}],sources_truncated:false,covers_current_members:state.members.length===1,uncovered_current_alert_ids:state.members.slice(1).map(m=>m.alert_id),input_freshness:{state:state.freshness,reasons:state.freshness==='stale'?['human_feedback_changed']:[]}}});
    if(pathname.endsWith('/history'))return send({items:state.runs.map(r=>({id:'run:'+r.id,recorded_at:stamp,run:r,result:state.results.find(x=>x.source_run_id===r.id)||null})),next_cursor:null});
    if(pathname.endsWith('/baseline/prepare')){let run=state.runs.find(r=>r.state==='pending_update');if(!run){run={...state.runs[0],id:'00000000-0000-4000-8000-000000000020',title:'模拟下一轮调查',state:'pending_update',delivery_state:'none',started_at:null,ended_at:null,scope_revision:state.cas.scope_revision};state.runs.push(run);}return send({case_id:ids.case,scope_revision:state.cas.scope_revision,pending_run_id:run.id,created:true});}
    if(pathname.includes('/runs/')) {
      const run=state.runs.find(r=>r.id===pathname.split('/')[4]);if(!run)return send({detail:'run_not_found'},404);
      if(pathname.endsWith('/start')){run.state='completed';run.delivery_state='partial';run.started_at=stamp;run.ended_at=stamp;state.results.push({...state.results[0],id:'00000000-0000-4000-8000-000000000021',source_run_id:run.id,title:'模拟下一轮结果',change_summary:'本轮读取了明确保存的人工结果'});state.freshness='current';}
      if(pathname.includes('/artifacts/'))return send({artifact:{id:ids.artifact,kind:'source_snapshot'},content_json:{simulation:true,task_revisions:state.revisions.map(x=>x.id)},content_text:null,availability:'available'});
      if(pathname.includes('/materials/'))return send({id:ids.material,alert_id:ids.alert,version:1,ocsf:{activity_name:'Process Start'},simulation:true});
      return send({run,execution_summary:state.executionSummary??null,result_ids:state.results.filter(x=>x.source_run_id===run.id).map(x=>x.id),result_count:1,results_truncated:false,start_eligibility:{can_start:run.state==='pending_update',reason:run.state==='pending_update'?'ready':'not_pending'},current_member_count:state.members.length,input_member_count:1,members:[{alert_id:ids.alert,material_id:ids.material,read_state:'read',analysis_state:'needs_review'}],members_truncated:false,read_counts:{read:1},analysis_counts:{needs_review:1},steps:[{stage_code:'C1',name:'冻结输入',state:'completed'},{stage_code:'C6',name:'形成交付',state:'completed'}],steps_truncated:false,tool_calls:0,usage:{model_calls:1,known_total_tokens:2400,unknown_token_calls:0,total_tokens:2400},artifacts:[{id:ids.artifact,kind:'source_snapshot',captured_at:stamp}],artifacts_truncated:false});
    }
    if(pathname.includes('/results/')){const result=state.results.find(x=>x.id===pathname.split('/')[4]);return send({result,run:state.runs.find(x=>x.id===result.source_run_id),members:[{alert_id:ids.alert,conclusion_covered:true}],member_count:1,members_truncated:false,delivery:null});}
    if(pathname.endsWith('/tasks')&&method==='GET')return send({items:state.tasks,total:state.tasks.length,next_offset:null});
    if(pathname.endsWith('/revisions'))return send({items:state.revisions,total:state.revisions.length,next_offset:null});
    if(pathname.includes('/tasks/')&&method==='GET')return send(state.tasks.find(x=>x.id===pathname.split('/')[4]));
    if(pathname.includes('/tasks')&&['POST','PUT'].includes(method)) {
      if(state.rejectNextTask){state.rejectNextTask=false;return send({detail:'row_version_conflict'},409);}
      const task=method==='PUT'?state.tasks.find(x=>x.id===pathname.split('/')[4]):{id:ids.task,case_id:ids.case,row_version:0,origin_result_id:body.origin_result_id};
      if(method==='PUT'&&task.row_version!==body.expected_row_version)return send({detail:'row_version_conflict'},409);
      const current={...task.current,...body,id:'00000000-0000-4000-8000-'+String(30+state.revisions.length).padStart(12,'0'),task_id:task.id,revision:task.row_version+1,changed_by:ids.actor,changed_at:stamp,completed_by:body.state==='completed'?ids.actor:null,completed_at:body.state==='completed'?stamp:null};
      task.current=current;task.row_version++;task.current_revision_id=current.id;state.revisions.push(clone(current));if(method==='POST')state.tasks.push(task);state.freshness='stale';return send({task,created:method==='POST'});
    }
    if(pathname.endsWith('/associations')){state.members.push({alert_id:ids.extra,title:'模拟新增告警',severity:'medium',event_time:stamp});state.cas.scope_revision++;return send({case_id:ids.case,scope_revision:state.cas.scope_revision});}
    if(pathname.endsWith('/members/move')){state.members=state.members.filter(x=>!body.alert_ids.includes(x.alert_id));state.cas.scope_revision++;return send({source_case_id:ids.case,target_case_id:body.target_case_id});}
    return send({detail:'fixture_route_not_found'},404);
  });
  return {server,state,ids};
}
if(require.main===module){const {server}=createFixtureServer();const port=Number(process.argv[2]||4196);server.listen(port,'127.0.0.1',()=>process.stdout.write(`Simulation only: http://127.0.0.1:${port}/?data=service#/cases (use any synthetic credential)\n`));}
module.exports={createFixtureServer,ids};
