/* Fixed, offline UI examples. Never queries a service or invokes a model. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const output=path.resolve(__dirname,'../../prototypes/security-pages-v2/page-showcase-data.js');
const provenance={fixture:true,recorded:false,fixtureSet:'incident-alert-20261031',sourceEnvironment:'design-showcase',sourceTenantId:'showcase-contoso'};
const data={version:1,...provenance,incidents:[],alerts:[],assets:[],cases:[],evidence:[],activities:[],comments:[],relations:[],runs:[]};
const hash=value=>crypto.createHash('sha256').update(value).digest('hex');
function asset(id,type,name,fields={}){const row={...provenance,id:'showcase-'+id,type,name,tags:[],inventory:true,...fields};data.assets.push(row);return row.id;}
const ids={
 finance:asset('finance','device','FIN-LAPTOP-07',{domain:'CONTOSO',os:'Windows 11',risk:'高',ip:'10.20.10.7',tags:['财务终端','关键资产'],critical:true}),
 analyst:asset('analyst','user','lin.chen@contoso.com',{department:'财务部',role:'财务分析员',risk:'高'}),
 mailbox:asset('mailbox','mailbox','lin.chen@contoso.com',{domain:'contoso.com',kind:'用户邮箱',risk:'中'}),
 external:asset('external','ip','203.0.113.77',{location:'文档示例地址',provider:'外部连接目标',risk:'高'}),
 attachment:asset('attachment','file','quarterly-review.exe',{hash:hash('showcase quarterly review sample'),risk:'高'}),
 app:asset('app','device','APP-SRV-02',{domain:'CONTOSO',os:'Windows Server 2022',risk:'高',ip:'10.20.20.2',tags:['应用服务器']}),
 share:asset('share','device','FILE-SRV-03',{domain:'CONTOSO',os:'Windows Server 2022',risk:'中',ip:'10.20.20.3',tags:['文件服务器']}),
 jump:asset('jump','device','OPS-JUMP-01',{domain:'CONTOSO',os:'Windows Server 2022',risk:'中',ip:'10.20.20.1',tags:['运维跳板机']}),
 service:asset('service','user','svc.reports@contoso.com',{department:'数据平台',role:'报表服务账号',risk:'高'}),
 archive:asset('archive','file','finance-export.zip',{hash:hash('showcase finance export sample'),risk:'中'}),
 upload:asset('upload','ip','198.51.100.42',{location:'文档示例地址',provider:'外部上传目标',risk:'中'}),
 cloud:asset('cloud','cloud','finance-reports-store',{provider:'Microsoft Azure',region:'East Asia',risk:'中',tags:['财务存储']}),
 cloudapp:asset('cloudapp','app','Report Transfer Client',{publisher:'Contoso',permissions:'Files.ReadWrite.All',risk:'中'}),
 backup:asset('backup','device','BACKUP-SRV-01',{domain:'CONTOSO',os:'Windows Server 2022',risk:'低',ip:'10.20.30.1',tags:['备份服务器']}),
 operator:asset('operator','user','backup.ops@contoso.com',{department:'基础设施',role:'备份操作员',risk:'低'}),
 repository:asset('repository','cloud','approved-backup-store',{provider:'Microsoft Azure',region:'East Asia',risk:'低',tags:['备份存储']}),
 automation:asset('automation','robot','Backup Validation Assistant',{publisher:'Contoso',permissions:'只读备份任务',risk:'低'}),
 internal:asset('internal','ip','192.0.2.25',{location:'文档示例地址',provider:'批准的备份目标',risk:'低'})
};
const scenarios=[
 {id:'showcase-incident-01',title:'财务终端钓鱼附件与脚本外联',base:'2026-10-31T01:10:00Z',status:'In progress',owner:'Alex Wilber',severity:'高',priority:92,caseId:'showcase-case-01',completion:'completed',disposition:'true_positive',
  description:'财务用户打开邮件附件后，同一终端先后出现脚本启动、凭据进程读取和外部连接告警。告警共享终端与账号，文件哈希贯穿附件和执行记录；事件用于呈现这些关联事实，联合研判及处置由关联 Case 承接。',
  reason:'关联依据：同一终端 FIN-LAPTOP-07、同一账号 lin.chen@contoso.com，12分钟窗口内连续出现邮件、进程与网络记录；附件和进程记录包含同一文件哈希。',
  rows:[
   ['可疑邮件附件在财务终端被打开','初始访问','T1566.001','邮件安全网关','高',[ids.finance,ids.analyst,ids.mailbox,ids.attachment], '邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。'],
   ['文档进程启动隐藏脚本解释器','执行','T1059.001','终端检测与响应','高',[ids.finance,ids.analyst,ids.attachment], '父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。'],
   ['同一终端出现凭据进程读取','凭据访问','T1003.001','终端检测与响应','高',[ids.finance,ids.analyst], '终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。'],
   ['脚本执行后连接外部 HTTPS 地址','命令与控制','T1071.001','网络流量检测','中',[ids.finance,ids.analyst,ids.external], 'FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。']
  ]},
 {id:'showcase-incident-02',title:'服务账号跨主机访问与归档上传',base:'2026-10-31T03:00:00Z',status:'New',owner:'未分配',severity:'高',priority:78,caseId:null,completion:'partial',disposition:'escalate',
  description:'报表服务账号先后访问跳板机、应用服务器与文件服务器，随后生成归档并向外部地址传输数据。现有记录可串联账号、主机和归档对象，但没有取得完整文件传输清单，尚不能确认外传内容或完整范围。',
  reason:'关联依据：svc.reports@contoso.com 在12分钟窗口中访问三台主机；文件服务器归档日志与上传进程记录共享 finance-export.zip 的哈希。',
  rows:[
   ['服务账号从跳板机访问应用服务器','横向移动','T1021.002','身份与目录检测','中',[ids.service,ids.jump,ids.app], '服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。'],
   ['应用服务器读取文件服务器共享目录','收集','T1039','文件访问审计','高',[ids.service,ids.app,ids.share,ids.cloud], '应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。'],
   ['服务账号生成财务文件归档','收集','T1560.001','文件访问审计','中',[ids.service,ids.share,ids.archive], '文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。'],
   ['归档进程向外部目标上传字节','数据外传','T1567.002','网络流量检测','高',[ids.service,ids.share,ids.archive,ids.upload,ids.cloudapp], '上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。']
  ]},
 {id:'showcase-incident-03',title:'已核实的授权备份与维护活动',base:'2026-10-29T02:00:00Z',status:'Resolved',owner:'Patti Fernandez',severity:'低',priority:24,caseId:'showcase-case-03',completion:'not_escalated',disposition:'benign',
  description:'备份服务器上的脚本、文件归档与存储上传告警对应批准的维护工单 CHG-2026-1031。分析员核对操作账号、目标存储和维护窗口后，确认属于预期备份行为并手动解决事件。',
  reason:'关联依据：三条告警共享 BACKUP-SRV-01、backup.ops@contoso.com 和维护工单 CHG-2026-1031，均位于批准的备份时间窗内。',
  rows:[
   ['备份服务器在维护窗口运行脚本','执行','T1059.001','终端检测与响应','低',[ids.backup,ids.operator,ids.automation], '脚本路径和签名与批准的备份任务一致，执行账号为 backup.ops@contoso.com。'],
   ['备份任务批量归档业务文件','收集','T1560.001','文件访问审计','低',[ids.backup,ids.operator,ids.repository], '归档目录和文件集合匹配维护工单，未发现超出备份范围的访问。'],
   ['归档上传至批准的备份存储','数据外传','T1567.002','网络流量检测','低',[ids.backup,ids.operator,ids.repository,ids.internal], '目标存储及访问凭据属于批准的备份任务，传输清单与备份清单一致。']
  ]}
];
for(const [si,sc] of scenarios.entries()){
 const stamp=minutes=>new Date(Date.parse(sc.base)+minutes*60000).toISOString();
 const alerts=sc.rows.map(([title,category,technique,source,severity,entities,description],i)=>{
  const id=`showcase-alert-0${si+1}-${i+1}`,time=stamp(i*4),known=sc.status==='Resolved';
  const a={...provenance,id,title,description,severity,source,category,entityIds:entities,incidentId:sc.id,caseId:sc.caseId,status:known?'Resolved':i===0&&sc.status==='In progress'?'In progress':'New',owner:sc.owner,classification:known?'Informational':i===0&&si===0?'True positive':'Not set',disposition:i===0?sc.disposition:null,tags:known?['授权维护']:['重点核查'],event_time:time,first:time,last:stamp(i*4+1),hostNames:entities.map(id=>data.assets.find(e=>e.id===id)).filter(e=>e.type==='device').map(e=>e.name),tactics:[category],iocKeys:entities.map(id=>data.assets.find(e=>e.id===id)).filter(e=>['ip','file'].includes(e.type)).map(e=>e.type+':'+(e.hash||e.name)),investigation:i===0?'Completed':'Not started',comments:[]};
  const raw={id,tenant_id:'showcase-contoso',source,source_ref:`SEC-20261031-${si+1}${i+1}`,event_time:time,title,description,severity,status:a.status,incident_id:sc.id,case_id:sc.caseId,mitre_tactics:[category],mitre_techniques:[technique],rule_id:`RULE-${si+1}${i+1}`,entities:entities.map(id=>{const e=data.assets.find(e=>e.id===id);return {id:e.id,type:e.type,name:e.name,...(e.hash?{sha256:e.hash}:{})};}),raw_event:{event_id:`evt-${si+1}-${i+1}`,hostname:a.hostNames[0],username:data.assets.find(e=>entities.includes(e.id)&&e.type==='user')?.name,observation:description,approval_reference:known?'CHG-2026-1031':null}};
  a.detailMaterial={timelineVersion:2,tenantName:'Contoso',techniques:[technique],raw,confidence:{score:known?88:93-i*3},risk:known?96:si===0?96-i*4:72-i*3,
   explanation:{generatedAt:stamp(i*4+1),summary:description+(known?' 已核对维护工单、账号和操作范围，当前判断为预期行为。':' 请结合事件中的共享对象和时间线核查授权与影响。'),evidence:[`源记录 ${raw.source_ref}`,`规则 ${raw.rule_id}`,`对象 ${entities.map(id=>data.assets.find(e=>e.id===id).name).join('、')}`],gaps:known?[]:si===1?['文件传输清单不完整，需补查范围']:['处置建议尚待人工审批'],suggestedActions:[{title:known?'保留工单与备份清单供复核':'核对授权、进程和目标记录',rationale:known?'后续同类告警可按相同范围复核。':'检测命中需要结合上下文研判。'}]},
   history:[{time,title:'告警发生',description},{time:stamp(i*4+0.25),title:'告警被检测到',description:`${source} · ${raw.rule_id}`},{time:stamp(i*4+0.5),title:'告警入库',description:`源记录 ${raw.source_ref}`},{time:stamp(i*4+1),title:'告警关联到事件',description:sc.title}],runs:[],responseRecommendations:[]};
  if(sc.owner!=='未分配')a.detailMaterial.history.push({time:stamp(16),title:'告警分配',description:`负责人：${sc.owner}`});
  if(known){a.feedbackReason='已核对 CHG-2026-1031、执行账号及备份清单，符合批准的维护范围。';a.detailMaterial.history.push({time:stamp(32),title:'人工复核并关闭告警',description:a.feedbackReason});a.disposition='benign';a.last=stamp(32);}
  data.alerts.push(a);return a;
 });
 const inc={...provenance,id:sc.id,title:sc.title,description:sc.description,correlationReason:sc.reason,status:sc.status,owner:sc.owner,severity:sc.severity,priority:sc.priority,classification:sc.status==='Resolved'?'Informational':'Not set',tags:sc.status==='Resolved'?['授权维护']:['联合核查'],first:sc.base,last:alerts.at(-1).event_time,updated:stamp(35),entityIds:[...new Set(alerts.flatMap(a=>a.entityIds))],critical:si===0};
 if(sc.status==='Resolved')inc.resolutionNote='已人工核对维护工单、执行身份、时间窗和传输清单，属于预期备份活动。';
 data.incidents.push(inc);
 if(sc.caseId)data.cases.push({...provenance,id:sc.caseId,title:sc.title+'调查',description:sc.description,status:sc.status,owner:sc.owner,severity:sc.severity,priority:sc.priority,classification:inc.classification,tags:inc.tags.slice(),incidentId:sc.id,alertIds:alerts.map(a=>a.id),created:stamp(16),updated:stamp(35),tasks:[]});
 for(const a of alerts){
  const first=a.entityIds[0];
  for(const to of a.entityIds.slice(1))data.relations.push({id:`${a.id}:${to}`,from:first,to,label:`${a.category}记录关联`,alertIds:[a.id],kind:'association',description:a.description});
  const e=a.entityIds.map(id=>data.assets.find(x=>x.id===id)).find(x=>['file','ip'].includes(x.type))||data.assets.find(x=>x.id===first);
  data.evidence.push({...provenance,id:'evidence-'+a.id,alertId:a.id,entityId:e.id,name:e.name,type:({file:'文件',ip:'IP 地址',device:'进程',user:'云登录会话'})[e.type]||'对象记录',origin:a.source,verdict:si===2?'Clean':'Suspicious',remediation:si===2?'No action needed':si===0?'Pending approval':'Not started',threat:si===2?'授权备份':a.category});
 }
 // One saved automation example per scenario; other alerts explicitly have no Run.
 const a=alerts[0],rid=`showcase-run-0${si+1}`,partial=sc.completion==='partial',triageOnly=sc.completion==='not_escalated';
 // Freeze the ingested record before triage; current manual feedback is not model input.
 const input={...structuredClone(a.detailMaterial.raw),status:'New',last:stamp(1)};
 const queryHosts=[...new Set(alerts.flatMap(row=>row.hostNames))],queryUser=data.assets.find(e=>a.entityIds.includes(e.id)&&e.type==='user').name;
 const toolRows=triageOnly?[]:[
  {id:rid+'-query-1',name:'asset_activity',args:{hostnames:queryHosts,username:queryUser,start:sc.base,end:stamp(16)},resultFormat:'saved_result',time:stamp(17),success:true,result:JSON.stringify({records:alerts.map(row=>({alert_id:row.id,time:row.event_time,hostnames:row.hostNames,username:queryUser,description:row.description})),scope:{hostnames:queryHosts,username:queryUser,start:sc.base,end:stamp(16)}},null,2)},
  {id:rid+'-query-2',name:partial?'transfer_inventory':'process_and_file_context',args:{alert_id:a.id,start:sc.base,end:stamp(16)},resultFormat:'saved_result',time:stamp(18),success:!partial,result:JSON.stringify(partial?{status:'unavailable',reason:'未取得完整文件传输清单'}:{status:'success',parent_process:'WINWORD.EXE',process:'powershell.exe',sha256:hash('showcase quarterly review sample'),host:'FIN-LAPTOP-07'},null,2)}
 ];
 const findings=triageOnly?['维护工单、账号、执行窗口与备份目标匹配，判为预期活动。']:partial?['已确认同一服务账号跨主机访问和归档操作。','缺少完整传输清单，不能确认外传内容及范围。']:['邮件附件、进程与网络记录可通过同一终端、账号及文件哈希相互核对。','输入范围的材料已齐备，处置尚待审批。'];
 const actions=triageOnly?[]:[{description:partial?'补查文件传输清单并核对授权':'核对业务影响后隔离财务终端',target:a.hostNames[0],requires_approval:!partial,rationale:partial?'连接记录不足以确认具体传输对象。':'相关终端记录已齐备，隔离需确认业务影响。'}];
 const steps=[{id:rid+'-triage',seq:1,kind:'triage_verdict',name:'自动分诊',time:stamp(16),summary:triageOnly?'符合批准的维护任务，未升级调查':'进入自动调查核查材料',payload:{verdict:triageOnly?'benign_true_positive':partial?'needs_review':'true_positive',confidence:a.detailMaterial.risk/100,auto_closed:false}}];
 toolRows.forEach(t=>steps.push({id:t.id+'-event',seq:steps.length+1,kind:'tool_call',name:'调查工具',time:t.time,summary:t.name+(t.success?'：已取得记录':'：资料不可用'),payload:{tool:t.name,args:t.args,result:JSON.parse(t.result)}}));
 if(!triageOnly)for(const [i,kind] of ['recon','forensic','responder','report'].entries())steps.push({id:rid+'-'+kind,seq:steps.length+1,kind,name:['侦察分析','取证分析','响应分析','报告整理'][i],time:stamp(19+i),summary:i===1?findings.join('；'):i===2?'形成建议，未执行响应':'保存输入范围内的材料与引用',adopted:{summary:i===1?findings.join('；'):'按当前输入及可用证据交付',evidence_ids:toolRows.map(t=>t.id)}});
 const report=triageOnly?null:`# ${sc.title}\n\n## 输入范围\n告警 ${a.id}；关联事件 ${sc.id}。其余成员记录仅作查询上下文。\n\n## 调查发现\n${findings.join('\n\n')}\n\n## 查询依据\n${toolRows.map(t=>`- ${t.id}：${t.name}，${t.success?'已取得记录':'资料不可用'}`).join('\n')}\n\n## 完整性\n${partial?'部分交付，缺少文件传输清单。':'本次输入范围的材料完整，事件仍处理中。'}\n\n## 建议与执行\n${actions.map(x=>x.description).join('\n')}\n未执行真实响应。\n`;
 const artifacts=[],artifactBodies={};
 for(const [i,t] of toolRows.entries()){const content=JSON.parse(t.result),text=JSON.stringify(content),id=rid+'-artifact-'+(i+1);artifacts.push({id,kind:'tool_result',event_id:t.id+'-event',sha256:hash(text),size_bytes:Buffer.byteLength(text),created_at:t.time});artifactBodies[id]={mode:'full',format:'json',content};}
 if(report){const id=rid+'-report';artifacts.push({id,kind:'report_md',event_id:rid+'-report',sha256:hash(report),size_bytes:Buffer.byteLength(report),created_at:stamp(22)});artifactBodies[id]={mode:'full',format:'markdown',content:report};}
 const run={...provenance,id:rid,title:sc.title+'自动处理',alertIds:[a.id],sourceCaseId:null,status:'completed',completion:sc.completion,verdict:steps[0].payload.verdict,triage:steps[0].payload,started:stamp(16),ended:stamp(22),input,findings,steps,tools:toolRows,graphs:{},artifacts,artifactBodies,actions,executed:[],report,stop:partial?'文件传输清单不可用，保留部分结果供人工接手。':triageOnly?'分诊判断为预期维护活动，未升级调查。':''};
 data.runs.push(run);
 a.detailMaterial.runs=[{id:rid,time:run.started,status:'Completed',completion:run.completion,stop:run.stop,findings,actions:actions.map(x=>x.description),calls:null,tokens:null,report,steps:steps.map(s=>({name:s.name,agent:s.name,status:s.kind==='tool_call'&&s.payload.result?.status==='unavailable'?'Failed':'Completed',input:s.payload?.args||{alert_id:a.id},output:s.adopted||s.payload})),tools:toolRows.map(t=>({...t,status:t.success?'已返回完整记录':'资料不可用'}))}];
 a.detailMaterial.responseRecommendations=actions.map(x=>({action:x.description,target:x.target,reason:x.rationale,approval:x.requires_approval?'待审核':'无需审批',execution:'未执行'}));
 a.detailMaterial.history.push({time:stamp(16),title:'自动分诊完成',description:steps[0].summary});
 if(!triageOnly)a.detailMaterial.history.push({time:stamp(22),title:'调查结果交付',description:partial?'部分交付：文件传输清单不可用':'本次材料已齐备，处置仍待人工审批'});
 const events=[['成员告警关联至事件','告警关联','系统','自动','Completed',13],['事件分诊与优先级评估','分诊','系统','自动','Completed',14],['自动处理结果已保存','调查','自动处理','自动',partial?'Partial':'Completed',22]];
 if(sc.owner!=='未分配')events.push(['分配事件负责人','人员分派',sc.owner,'人工','Completed',16]);
 if(partial)events.push(['文件传输清单查询不可用','调查','自动处理','自动','Failed',18]);
 if(si===0)events.push(['终端隔离建议等待审批','响应',sc.owner,'人工','Pending approval',23]);
 if(si===2)events.push(['核对维护工单并手动解决事件','事件管理',sc.owner,'人工','Completed',35]);
 events.forEach(([title,type,performedBy,trigger,status,n],i)=>data.activities.push({...provenance,id:`showcase-activity-${si+1}-${i+1}`,title,type,performedBy,trigger,status,target:sc.title,time:stamp(n),incidentId:sc.id,caseIds:sc.caseId?[sc.caseId]:[]}));
 if(sc.caseId)data.comments.push({...provenance,id:'comment-'+sc.caseId,caseId:sc.caseId,author:sc.owner,text:sc.description,time:stamp(25)});
}
const code=`/* Offline demonstration records. Never mixed into saved AiSOC objects. */\n'use strict';\nwindow.pageShowcaseData = ${JSON.stringify(data,null,2)};\nwindow.mergePageShowcases = function(store){\n  const data=window.pageShowcaseData;\n  for(const key of ['assets','alerts','incidents','cases','evidence','activities','comments']){\n    store[key] ||= [];\n    const known=new Set(store[key].map(row=>row.id));\n    for(const row of data[key])if(!known.has(row.id)){store[key].push(structuredClone(row));known.add(row.id);}\n  }\n  store.designRelations ||= [];\n  const known=new Set(store.designRelations.map(row=>row.id));\n  for(const row of data.relations)if(!known.has(row.id)){store.designRelations.push(structuredClone(row));known.add(row.id);}\n};\n`;
fs.writeFileSync(output,code);
console.log(JSON.stringify(Object.fromEntries(['incidents','alerts','assets','cases','evidence','activities','runs'].map(k=>[k,data[k].length]))));
