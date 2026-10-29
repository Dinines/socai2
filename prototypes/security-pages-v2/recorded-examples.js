/* Append historical records without replacing browser-local edits or source identities. */
'use strict';
window.mergeAiSoc20Data = function(store){
  const data=window.aisoc20RecordedData;
  if(!data)return;
  for(const key of ['alerts','assets','cases']){
    const known=new Set(store[key].map(x=>x.id));
    store[key].push(...structuredClone(data[key].filter(x=>!known.has(x.id))));
  }
  // Record original Run references once; later member edits must not erase history.
  for(const source of data.cases){
    const c=store.cases.find(x=>x.id===source.id);
    const members=data.alerts.filter(a=>source.alertIds.includes(a.id));
    const tenants=[...new Set(members.map(a=>a.sourceTenantId).filter(Boolean))];
    if(tenants.length!==1)continue;
    c.sourceTenantId ??= tenants[0];
    c.sourceRunIds ??= data.runs.filter(r=>r.sourceEnvironment===source.sourceEnvironment&&r.sourceTenantId===tenants[0]&&r.alertIds.some(id=>source.alertIds.includes(id))).map(r=>r.id);
  }
  // Only saved incident identities become groups; unlinked alerts stay unlinked.
  const groups=new Map();
  for(const a of data.alerts)if(a.incidentId){
    const key=JSON.stringify([a.sourceEnvironment,a.sourceTenantId,a.incidentId]);
    if(!groups.has(key))groups.set(key,[]);groups.get(key).push(a);
  }
  for(const members of groups.values()){
    const first=members[0];if(store.incidents.some(i=>i.id===first.incidentId))continue;
    const sourceCase=data.cases.find(c=>c.alertIds.includes(first.id));
    const times=members.flatMap(a=>[a.event_time||a.first,a.last]).filter(Boolean).sort();
    store.incidents.push({id:first.incidentId,title:(sourceCase?.title||first.title).replace('（本地整理）',''),
      recordedIncident:true,sourceEnvironment:first.sourceEnvironment,sourceTenantId:first.sourceTenantId,
      sourceAlertIds:members.map(a=>a.id),first:times[0],last:times.at(-1),updated:times.at(-1),
      severity:members.some(a=>a.severity==='高')?'高':members.some(a=>a.severity==='中')?'中':'低',
      status:'Not set',owner:'未记录',classification:'Not set',priority:null,tags:[],
      description:'按保存告警的事件标识汇集成员与已有处理结果。事件管理信息未记录。'});
  }
};
window.mergePersistedCaseData = function(store){
  const data=window.persistedCaseData;
  if(!data)return;
  for(const key of ['alerts','assets','cases']){
    const known=new Set(store[key].map(x=>x.id));
    store[key].push(...structuredClone(data[key].filter(x=>!known.has(x.id))));
  }
};
