/* Microsoft reference workspaces: explicit local fixtures, never production evidence. */
'use strict';
window.referenceWorkspaces = (() => {
  const alertId = n => `da63896${String(4100+n).padStart(6,'0')}`;
  const relations = [
    ['mail-user','m1','u1','邮箱所属账户',[0,1]],
    ['mail-ip','m1','ip1','邮件检测关联地址',[0]],
    ['user-device','u1','d1','告警关联用户与设备',[3,4,5]],
    ['device-file','d1','f1','设备告警关联文件',[3]],
    ['device-ip','d1','ip1','外联告警关联目标',[6]],
    ['user-app','u1','a1','身份与应用关联',[11]],
    ['app-cloud','a1','c1','告警关联应用与资源',[9,11]],
    ['device-app','d2','a1','设备与应用关联',[9,10]],
    ['other-user-device','u2','d3','告警关联用户与设备',[14,15]],
    ['other-device-ip','d3','ip2','告警关联地址',[15,16]],
  ].map(([id,from,to,label,ids])=>({id,from,to,label,alertIds:ids.map(alertId),kind:'association'}));
  const potentialPaths = [
    {id:'user-finance',source:'u1',target:'c1',alertIds:[alertId(3),alertId(9),alertId(11)],nodes:['u1','a1','c1'],steps:['可访问应用','应用可访问资源'],description:'根据账户与应用访问关系，财务存储是需要核查的潜在目标。路径不代表已发生数据访问或外泄。'},
    {id:'device-finance',source:'d1',target:'c1',alertIds:[alertId(3)],nodes:['d1','u1','a1','c1'],steps:['关联账户','可访问应用','应用可访问资源'],description:'从设备的关联账户出发检查应用及资源访问关系，评估可能影响的目标。'},
  ];
  const investigations = [
    {id:'INV-20261024-001',title:'身份与终端活动调查',alertIds:[0,2,3].map(alertId),completion:'调查已完成',status:'Completed',remediation:'待审批',findings:'已核对异常登录、终端脚本与关联文件；相关处置仍等待审核。',steps:[['收集身份与设备材料','核对登录来源、终端进程和文件。'],['分析关联证据','归纳当前材料中的异常活动。'],['形成调查结果','已有结果可查看；处置审批独立跟踪。']]},
    {id:'INV-20261024-002',title:'异常外联与数据传输调查',alertIds:[6,8].map(alertId),completion:'部分完成',status:'Completed',remediation:'尚未处置',findings:'已查看网络连接，未取得完整传输文件清单；现有材料不足以确认完整传输范围。',steps:[['核对外联记录','保留已有连接信息。'],['确认传输范围','文件清单缺失，范围未确认。'],['保存已有发现','保留结果与缺口，供后续接手。']]},
  ];
  function relatedIncidents(store, alerts, exclude=[]){
    const entities=new Set(alerts.flatMap(a=>a.entityIds)),excluded=new Set(exclude);
    return store.incidents.filter(i=>!excluded.has(i.id)).map(i=>{
      const linked=store.alerts.filter(a=>a.incidentId===i.id&&!a.persistedRecord);
      const shared=[...new Set(linked.flatMap(a=>a.entityIds))].filter(id=>entities.has(id));
      return {...i,shared};
    }).filter(i=>i.shared.length);
  }
  function investigationRecords(alerts){const ids=new Set(alerts.filter(a=>!a.persistedRecord).map(a=>a.id));return investigations.filter(i=>i.alertIds.some(id=>ids.has(id)));}
  function graph(store,members,options={}){
    const excluded=[...new Set(members.map(a=>a.incidentId))];
    const associated=relatedIncidents(store,members,excluded);
    const incidentIds=new Set(associated.map(i=>i.id));
    const all=options.associated?[...members,...store.alerts.filter(a=>!a.persistedRecord&&incidentIds.has(a.incidentId)&&!members.some(m=>m.id===a.id))]:members.slice();
    const alerts=all.filter(a=>(!options.severity||a.severity===options.severity)&&(!options.status||a.status===options.status)&&(!options.source||a.source===options.source)).sort((a,b)=>Date.parse(a.first)-Date.parse(b.first));
    const visible=alerts.slice(0,(options.index??99)+1),ids=new Set(visible.map(a=>a.id)),entityIds=new Set(visible.flatMap(a=>a.entityIds));
    const hidden=options.hidden||new Set();
    let nodes=store.assets.filter(a=>entityIds.has(a.id)&&!hidden.has(a.type)).map(a=>({...a,members:[a.id]}));
    const paths=potentialPaths.filter(p=>p.source===options.selected&&p.alertIds.some(id=>ids.has(id))&&p.nodes.every(id=>!hidden.has(store.assets.find(a=>a.id===id)?.type)));
    const selectedPath=options.blast?(paths.find(p=>p.id===options.path)||paths[0]):null;
    if(selectedPath)for(const id of selectedPath.nodes){if(!nodes.some(a=>a.id===id)){const a=store.assets.find(a=>a.id===id);if(a)nodes.push({...a,members:[id],potential:true});}}
    let edges=[...relations,...(store.designRelations||[])].filter(e=>e.alertIds.some(id=>ids.has(id))&&nodes.some(n=>n.id===e.from)&&nodes.some(n=>n.id===e.to)).map(e=>({...e,alertIds:e.alertIds.filter(id=>ids.has(id))}));
    if(selectedPath)edges=edges.concat(selectedPath.nodes.slice(1).map((id,i)=>({id:`${selectedPath.id}-${i}`,from:selectedPath.nodes[i],to:id,label:selectedPath.steps[i],kind:'potential',alertIds:[],description:selectedPath.description})));
    if(options.grouped&&!options.blast){
      const grouped=new Map();for(const a of nodes){const existing=grouped.get(a.type);if(existing)existing.members.push(a.id);else grouped.set(a.type,{...a,members:[a.id]});}nodes=[...grouped.values()];
      nodes=nodes.map(n=>({...n,id:n.members.length>1?'group-'+n.type:n.id}));
    }
    const represented=new Map(nodes.flatMap(n=>n.members.map(id=>[id,n.id])));
    edges=edges.map(e=>({...e,source:represented.get(e.from),target:represented.get(e.to)}));
    return {alerts,visible,nodes,edges,associated,paths,selectedPath};
  }
  // Saved incident context uses only recorded alert-to-object membership.
  // It deliberately does not consume the illustrative entity relations or paths above.
  function sourceGraph(store,members,options={},incident={}){
    const sameSource=i=>i.recordedIncident&&incident.sourceEnvironment&&incident.sourceTenantId&&i.sourceEnvironment===incident.sourceEnvironment&&i.sourceTenantId===incident.sourceTenantId;
    const sourceMember=(a,i)=>a.incidentId===i.id&&(
      a.sourceEnvironment&&a.sourceTenantId
        ? a.sourceEnvironment===i.sourceEnvironment&&a.sourceTenantId===i.sourceTenantId
        : !a.sourceEnvironment&&!a.sourceTenantId&&(i.sourceAlertIds||[]).includes(a.id));
    const memberIds=new Set(members.map(a=>a.id)),objects=new Set(members.flatMap(a=>a.entityIds||[]));
    const associated=store.incidents.filter(i=>i.id!==incident.id&&sameSource(i)).map(i=>{
      const alerts=store.alerts.filter(a=>sourceMember(a,i));
      return {...i,shared:[...new Set(alerts.flatMap(a=>a.entityIds||[]))].filter(id=>objects.has(id))};
    }).filter(i=>i.shared.length);
    const all=options.associated?[...members,...store.alerts.filter(a=>!memberIds.has(a.id)&&associated.some(i=>sourceMember(a,i)))]:members.slice();
    const time=a=>Number.isFinite(Date.parse(a.event_time))?Date.parse(a.event_time):Infinity;
    const alerts=all.filter(a=>(!options.severity||a.severity===options.severity)&&(!options.status||a.status===options.status)&&(!options.source||a.source===options.source)).sort((a,b)=>time(a)-time(b));
    const visible=alerts.slice(0,(options.index??99)+1),hidden=options.hidden||new Set(),entityIds=new Set(visible.flatMap(a=>a.entityIds||[]));
    let entities=store.assets.filter(a=>entityIds.has(a.id)&&!hidden.has(a.type)).map(a=>({...a,members:[a.id]}));
    if(options.grouped){
      const groups=new Map();for(const a of entities){if(groups.has(a.type))groups.get(a.type).members.push(a.id);else groups.set(a.type,a);}
      entities=[...groups.values()].map(n=>({...n,id:n.members.length>1?'group-'+n.type:n.id}));
    }
    const represented=new Map(entities.flatMap(n=>n.members.map(id=>[id,n.id])));
    const alertNodes=visible.map(a=>({id:'alert:'+a.id,type:'alert',name:a.title,alertId:a.id,members:['alert:'+a.id]}));
    const nodes=[...entities,...alertNodes],edges=visible.flatMap(a=>[...new Set(a.entityIds||[])].filter(id=>represented.has(id)).map(id=>({
      id:JSON.stringify(['source',a.id,id]),from:'alert:'+a.id,to:id,source:'alert:'+a.id,target:represented.get(id),
      label:'源告警记录的对象关联',kind:'association',alertIds:[a.id]
    })));
    return {alerts,visible,nodes,edges,associated,paths:[],selectedPath:null,sourceMode:true};
  }
  function updateCase(store,c,fields){
    for(const k of ['title','severity','status','owner','classification','due','resolutionNote'])if(fields[k]!==undefined)c[k]=fields[k];
    if(fields.tags!==undefined)c.tags=fields.tags.split(/[,，]/).map(s=>s.trim()).filter(Boolean);
    c.updated=new Date().toISOString();
  }
  return {graph,sourceGraph,relatedIncidents,investigationRecords,updateCase};
})();
