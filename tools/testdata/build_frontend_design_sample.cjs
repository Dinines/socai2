/* Offline, illustrative UI fixtures only. Never reads or writes business services. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../../prototypes/security-pages-v2');
const context={window:{},structuredClone};vm.createContext(context);
for(const file of ['data.js','workspace-model.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),context);
const store=context.window.makeDemoData(),source=context.window.referenceWorkspaces.investigationRecords(store.alerts);
const sampleQueries=[
 [
  ['identity_signins',{user:'hcook@contoso.com',start:'2026-10-24T00:30:00Z',end:'2026-10-24T01:10:00Z'},
   {records:[{time:'2026-10-24T00:51:00Z',user:'hcook@contoso.com',source_ip:'203.0.113.50',result:'success',device:'cont-adrianbrad'}],coverage:'所选账户及时间窗内登录记录。'}],
  ['process_activity',{hostname:'cont-adrianbrad',start:'2026-10-24T00:50:00Z',end:'2026-10-24T01:10:00Z'},
   {records:[{time:'2026-10-24T00:58:00Z',hostname:'cont-adrianbrad',user:'hcook@contoso.com',process:'powershell.exe',parent:'WINWORD.EXE',command_line:'powershell.exe -NoProfile -EncodedCommand '+Buffer.from("Write-Output 'review'",'utf16le').toString('base64')}],coverage:'该终端的进程启动记录；命令行不证明脚本全部行为。'}],
  ['file_metadata',{hostname:'cont-adrianbrad',filename:'invoice_2026.pdf.exe'},
   {records:[{filename:'invoice_2026.pdf.exe',sha256:store.assets.find(a=>a.id==='f1').hash,signature:'unsigned',detection:'Trojan:Win32/Example'}],coverage:'文件检测与元数据；未据此推断文件外传。'}]
 ],
 [
  ['network_connections',{hostname:'cont-adrianbrad',start:'2026-10-24T01:00:00Z',end:'2026-10-24T01:32:00Z'},
   {records:[{time:'2026-10-24T01:16:00Z',hostname:'cont-adrianbrad',remote_ip:'203.0.113.50',remote_port:443,protocol:'TLS',bytes_sent:20480}],coverage:'连接及流量元数据，不包含传输内容。'}],
  ['transfer_inventory',{hostname:'cont-adrianbrad',destination:'203.0.113.50'},
   {status:'unavailable',reason:'未取得文件级传输清单；不能根据连接字节数认定具体文件外泄。'}]
 ]
];
const runs=source.map((base,index)=>{
 const partial=index===1,alerts=base.alertIds.map(id=>store.alerts.find(a=>a.id===id));
 const start=Date.parse(index===0?'2026-10-24T01:12:00Z':'2026-10-24T01:32:00Z');
 const stamp=n=>new Date(start+n*60000).toISOString();
 const tools=sampleQueries[index].map(([name,args,result],i)=>({id:`${base.id}-query-${i+1}`,name,args,time:stamp(i+1),success:result.status!=='unavailable',resultFormat:'saved_result',result:JSON.stringify(result,null,2)}));
 const findings=partial?[
  '终端与 203.0.113.50:443 存在 TLS 连接，已取得连接时间和发送字节数。',
  '没有文件级传输清单，不能确认传输对象或完整范围。',
  '本次保留部分结果，等待补充资料后复核。'
 ]:[
  '同一账户的登录、终端脚本启动和文件检测记录在所选时间窗内出现。',
  '进程记录显示 WINWORD.EXE 启动 powershell.exe；文件元数据包含未签名可执行文件。',
  '共享账户与设备构成关联线索，图中关系不单独证明攻击因果。',
  '已完成本次输入范围的材料核对，处置建议等待审批。'
 ];
 const actions=partial?[{description:'补充文件传输清单并复核范围',target:'cont-adrianbrad',requires_approval:false,rationale:'连接元数据不足以确定文件内容。'}]:[
  {description:'复核并撤销可疑账户会话',target:'hcook@contoso.com',requires_approval:true,rationale:'登录记录与所选异常活动存在关联。'},
  {description:'审核终端隔离及可疑文件处置',target:'cont-adrianbrad',requires_approval:true,rationale:'进程与文件检测需结合业务影响审批。'}
 ];
 const report=`# ${base.title}\n\n## 范围\nCase 17420；输入告警 ${base.alertIds.join('、')}。仅覆盖本次输入及查询窗口。\n\n## 结论\n${findings.join('\n\n')}\n\n## 查询与依据\n${tools.map(t=>`- ${t.name}：${t.success?'已取得记录':'资料不可用'}；引用 ${t.id}`).join('\n')}\n\n## 完整性\n${partial?'部分交付。未取得完整传输文件清单，等待补充后继续调查。':'本次输入范围内的调查材料已齐备。调查结束不代表案件关闭或处置完成。'}\n\n## 后续处理\n${actions.map(a=>'- '+a.description+(a.requires_approval?'（待审批）':'')).join('\n')}\n\n## 执行记录\n未执行隔离、封禁或会话撤销。\n`;
 const phaseNames=['侦察分析','取证分析','响应分析','报告整理'],phaseKinds=['recon','forensic','responder','report'];
 const steps=tools.map((t,i)=>({id:`${base.id}-event-query-${i+1}`,seq:i+1,kind:'tool_call',name:'调查工具',time:t.time,summary:`${t.name}：${t.success?'已取得记录':'资料不可用'}`,payload:{tool_id:t.id,name:t.name,arguments:t.args,result:JSON.parse(t.result)}}));
 for(let i=0;i<4;i++)steps.push({id:`${base.id}-event-stage-${i+1}`,seq:steps.length+1,kind:phaseKinds[i],name:phaseNames[i],time:stamp(tools.length+i+1),summary:i===0?'核对输入、账户与设备范围':i===1?findings[0]:i===2?'形成建议，执行与审批独立跟踪':'保存本次结果及材料引用',adopted:{summary:i===1?findings.join('；'):i===2?actions.map(a=>a.description).join('；'):i===3?'报告引用本次查询及范围限制。':'范围限定为本次输入，不自动扩大到所有 Case 成员。',evidence_ids:tools.map(t=>t.id)}});
 const entityIds=[...new Set(alerts.flatMap(a=>a.entityIds))];
 const entities=entityIds.map(id=>store.assets.find(a=>a.id===id));
 const nodes=[...alerts.map(a=>({id:a.id,label:'Alert',properties:{title:a.title,source_alert_id:a.id}})),...entities.map(e=>({id:e.id,label:{device:'Host',user:'User',ip:'IOC'}[e.type]||'Entity',properties:{name:e.name}}))];
 const edges=alerts.flatMap(a=>a.entityIds.map(id=>({source:a.id,target:id,type:'OBSERVED_WITH'})));
 const graphs={
  attack_chain:{status:'success',source:'design_fixture',queried_at:stamp(4),data:{case_id:'17420',seed_alert_id:base.alertIds[0],window:'40m',chain:alerts.slice(1).map(a=>({alert_id:a.id,title:a.title,event_time:a.first,severity:a.severity,shared_entities:a.entityIds.filter(id=>alerts[0].entityIds.includes(id)).map(id=>({kind:'Entity',value:store.assets.find(e=>e.id===id).name})),distance:1}))}},
  attack_path:{status:'success',source:'design_fixture',queried_at:stamp(4),data:{nodes,edges}},
  alert_graph:{status:'success',source:'design_fixture',queried_at:stamp(4),data:{neighbors:{neighbor_count:entities.length,neighbors:entities.map(e=>({label:e.type,properties:{name:e.name},rel_type:'OBSERVED_WITH'}))},blast_radius:{total_affected:entities.length,hops:1}}}
 };
 const artifacts=[],artifactBodies={};
 function artifact(kind,content,format,eventId){const id=`${base.id}-artifact-${artifacts.length+1}`,raw=format==='json'?JSON.stringify(content):content;artifacts.push({id,kind,event_id:eventId,size_bytes:Buffer.byteLength(raw),sha256:crypto.createHash('sha256').update(raw).digest('hex'),created_at:stamp(tools.length+4)});artifactBodies[id]={mode:'full',format,content};}
 tools.forEach((t,i)=>artifact('tool_result',JSON.parse(t.result),'json',steps[i].id));
 artifact('relationship_graph',graphs,'json',steps.at(-3).id);
 artifact('report_md',report,'markdown',steps.at(-1).id);
 return {...base,recorded:false,fixture:true,sourceEnvironment:'design',sourceTenantId:'design',sourceCaseId:'17420',status:'completed',completion:partial?'partial':'completed',verdict:partial?'needs_review':'reviewed',started:stamp(0),ended:stamp(tools.length+4),input:{case_id:'17420',alerts:structuredClone(alerts)},findings,steps,tools,graphs,artifacts,artifactBodies,actions,executed:[],report,stop:partial?'未取得完整传输文件清单，需继续核查传输范围。':null,depth:{iterations:tools.length,distinct_pivots:tools.length,truncated:false,pivots:tools.map(t=>t.name),unavailable_data:partial?['文件级传输清单']:[],coverage_notes:['限定于输入告警的账户、设备及绝对时间窗口。'],strategy_id:'design-material-review'}};
});
const code=`/* Design-only material. No actual queries, model calls or executed responses. */\n'use strict';\nwindow.designInvestigationRuns = ${JSON.stringify(runs,null,2)};\nwindow.mergeDesignWorkspace = function(store){\n  const c=store.cases.find(c=>c.id==='17420'&&!c.localCollection&&!c.recordedCase);\n  if(c&&c.tasks===undefined)c.tasks=[\n    {id:'design-task-review',title:'审核账户会话与终端处置建议',owner:'Alex Wilber',due:'2026-10-25T12:00',status:'In progress'},\n    {id:'design-task-transfer',title:'补充文件级传输清单',owner:'Megan Bowen',due:'2026-10-26T18:00',status:'New'}\n  ];\n};\n`;
fs.writeFileSync(path.join(root,'design-investigation-data.js'),code);
console.log(JSON.stringify({runs:runs.length,tools:runs.reduce((n,r)=>n+r.tools.length,0),artifacts:runs.reduce((n,r)=>n+r.artifacts.length,0),reports:runs.length}));
