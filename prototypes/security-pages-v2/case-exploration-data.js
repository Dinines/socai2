/* Independent, append-only demonstration; never enriches recorded AiSOC Runs. */
'use strict';
window.caseExplorationData=(()=>{
  const meta={fixture:true,recorded:false,fixtureSet:'case-exploration-20261102',sourceEnvironment:'design-exploration',sourceTenantId:'exploration-contoso'};
  const time=m=>new Date(Date.UTC(2026,10,2,1,m)).toISOString();
  const assets=[['fin','device','FIN-WS-12'],['user','user','mei.lin@contoso.com'],['jump','device','JUMP-02'],['svc','user','svc.report@contoso.com'],['file','file','quarterly-report.zip'],['ip','ip','203.0.113.82'],['share','device','FILE-SRV-03'],['backup','device','BACKUP-02'],['isolated','file','access-review.csv']].map(([id,type,name])=>({...meta,id:'explore-'+id,type,name,risk:'中',tags:[],domain:'CONTOSO',inventory:true}));
  const definitions=[
    ['Office 启动脚本解释器',1,0,['fin','user'],'执行','T1059.001'],
    ['财务终端连接外部地址',1,3,['fin','ip'],'命令与控制','T1071.001'],
    ['财务账号登录跳板机',2,6,['user','jump'],'横向移动','T1078'],
    ['跳板机使用服务账号访问共享',2,9,['jump','svc','share'],'横向移动','T1078'],
    ['财务终端创建计划任务',1,12,['fin','user'],'持久化','T1053.005'],
    ['财务账号读取敏感目录',2,15,['user','share'],'收集','T1005'],
    ['财务终端生成报表归档',1,18,['fin','file'],'收集','T1560.001'],
    ['财务账号发起外部上传',2,21,['user','ip','file'],'数据渗出','T1041'],
    ['财务账号调用服务账号执行脚本',3,24,['user','svc','share','isolated'],'执行','T1059.001'],
    ['文件服务器向备份主机传输归档',3,27,['share','backup','file'],'横向移动','T1021.002']
  ];
  const alerts=definitions.map(([title,event,m,objects,category,technique],i)=>{
    const id='explore-alert-'+String(i+1).padStart(2,'0'),entityIds=objects.map(x=>'explore-'+x),hostNames=assets.filter(a=>entityIds.includes(a.id)&&a.type==='device').map(a=>a.name);
    const raw={id,title,event_time:time(m),tenant_id:meta.sourceTenantId,entities:assets.filter(a=>entityIds.includes(a.id)).map(a=>({id:a.id,type:a.type,name:a.name})),observation:title};
    return {...meta,id,title,description:title+'；需要结合关联告警、授权记录与时间范围继续核实。',severity:'高',status:'New',owner:'未分配',classification:'Not set',disposition:'needs_review',source:'终端与身份安全',category,entityIds,hostNames,incidentId:'explore-incident-'+event,event_time:time(m),first:time(m),last:time(m),updated:time(m),tags:[],tactics:[category],iocKeys:[],investigation:i<3?'Completed':'Not started',comments:[],detailMaterial:{timelineVersion:2,tenantName:'Contoso',techniques:[technique],raw,explanation:'告警记录了'+title+'。该条记录本身不能确定活动是否经过授权。',timeline:[]}};
  });
  const incidents=[['财务终端脚本执行与外联',1],['跨主机账号活动',2],['服务账号文件访问与备份传输',3]].map(([title,n])=>{
    const rows=alerts.filter(a=>a.incidentId==='explore-incident-'+n);return {...meta,id:'explore-incident-'+n,title,description:title+'，关联告警共享主机或账号。',correlationReason:'成员告警共享具体对象，并发生在同一时间窗口。',severity:'高',status:'In progress',owner:'Alex Wilber',classification:'Not set',priority:null,tags:[],first:rows[0].first,last:rows.at(-1).last,updated:time(35),entityIds:[...new Set(rows.flatMap(a=>a.entityIds))]};
  });
  function graph(ids){const rows=alerts.filter(a=>ids.includes(a.id)),entityIds=[...new Set(rows.flatMap(a=>a.entityIds))],techs=[...new Set(rows.flatMap(a=>a.detailMaterial.techniques))];return {attack_path:{status:'success',source:'演示关系快照',queried_at:time(35),data:{nodes:[...rows.map(a=>({id:a.id,label:'Alert',properties:{source_alert_id:a.id,title:a.title,event_time:a.first}})),...assets.filter(a=>entityIds.includes(a.id)).map(a=>({id:a.id,kind:a.type,name:a.name})),...techs.map(t=>({id:'explore-tech-'+t,label:'Technique',properties:{technique_id:t}}))],edges:rows.flatMap(a=>[...a.entityIds.map(id=>({source:a.id,target:id,type:'INVOLVES'})),...a.detailMaterial.techniques.map(t=>({source:a.id,target:'explore-tech-'+t,type:'MAPS_TO'}))])}},alert_graph:{status:'success',source:'演示直接邻居',queried_at:time(35),data:{neighbors:{source:{id:rows[0].id,label:'Alert',properties:{title:rows[0].title}},neighbors:assets.filter(a=>rows[0].entityIds.includes(a.id)).map(a=>({rel_type:'INVOLVES',node:{id:a.id,kind:a.type,name:a.name}}))}}},attack_chain:{status:'empty',source:'演示候选资料',data:{chain:[],window:'24h'}}};}
  function run(id,caseId,ids,active=false){return {...meta,simulation:true,investigationKind:'baseline',trigger:active?'members_changed':'case_created',id,caseId,sourceCaseId:caseId,title:active?'基础调查更新 · 文件传输范围':'基础调查 · 首次分析',alertIds:ids.slice(),status:active?'running':'completed',completion:active?null:'completed',verdict:active?null:'needs_review',started:time(active?42:30),ended:active?null:time(35),phase:active?1:3,input:{alerts:structuredClone(alerts.filter(a=>ids.includes(a.id)))},findings:active?[]:[caseId==='explore-case-01'?'终端脚本、账号登录和连接记录共享财务终端或账号，授权和影响仍需人工核实。':'两条告警共享文件服务器 FILE-SRV-03，服务账号授权与备份传输范围待核实。'],steps:[{seq:1,kind:'阶段记录',name:active?'查询范围（模拟）':'整理关系',summary:active?'演示正在核查选定范围，尚无结果。':'保存告警与对象的直接关系。',time:time(active?42:35)}],tools:[],graphs:graph(ids),artifacts:[],actions:[],executed:[],report:null,stop:null};}
  const cases=[['explore-case-01','财务终端与跨主机活动核查',[0,1,2],['explore-incident-1','explore-incident-2']],['explore-case-02','服务账号文件传输核查',[8,9],['explore-incident-3']]].map(([id,title,indexes,incidentIds])=>({...meta,id,title,description:'核对账号授权、关联活动与潜在影响范围。可从案件关系图核查新线索，将相关告警加入本案。',simulation:true,incidentCreated:true,status:'In progress',owner:'Alex Wilber',classification:'Not set',determination:'待核实',severity:'高',priority:null,tags:[],category:'多告警联合调查',source:'终端与身份安全',created:time(28),updated:time(45),alertIds:indexes.map(i=>alerts[i].id),incidentIds,investigation:'In progress',tasks:[],investigationDrafts:[],retainedRunIds:[]}));
  const runs=[run('explore-run-01',cases[0].id,cases[0].alertIds),run('explore-run-02',cases[1].id,cases[1].alertIds),run('explore-run-03',cases[1].id,cases[1].alertIds,true)];
  cases[1].investigationDrafts=[{id:'explore-draft-next',objective:'补充核对服务账号的授权与备份范围',alertIds:cases[1].alertIds.slice(),entityIds:['explore-svc'],materials:[],sourceRunId:'explore-run-02',status:'draft',createdAt:time(44),updatedAt:time(44)},{id:'explore-draft-cancelled',objective:'单独核查重复传输告警',alertIds:[alerts[9].id],entityIds:[],materials:[],status:'cancelled',createdAt:time(37),updatedAt:time(40),cancelledAt:time(40)}];
  return {...meta,assets,alerts,incidents,cases,runs};
})();
window.mergeCaseExplorationData=function(store){const d=window.caseExplorationData;for(const key of ['assets','alerts','incidents','cases','caseDemoRuns']){store[key]||=[];const ids=new Set(store[key].map(x=>x.id));for(const row of d[key==='caseDemoRuns'?'runs':key])if(!ids.has(row.id)){store[key].push(structuredClone(row));ids.add(row.id);}}};
