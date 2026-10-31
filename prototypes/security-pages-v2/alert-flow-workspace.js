/* Saved alert-flow additions and explicitly local collections; source ownership stays intact. */
'use strict';
window.alertFlowWorkspace = (() => {
  function merge(store){
    for(const key of ['incidents','cases']){
      const known=new Set(store[key].map(i=>i.id));
      for(const row of window.alertFlowData?.[key]||[])if(!known.has(row.id)){
        store[key].push(structuredClone(row));known.add(row.id);
      }
    }
  }
  function runs(rows){
    const saved=new Map((window.alertFlowData?.runs||[]).map(r=>[r.id,r]));
    return rows.map(r=>saved.has(r.id)?{...r,...saved.get(r.id)}:r);
  }
  function metrics(store){
    const source=window.alertFlowData?.incidents||[],ids=new Set(source.map(i=>i.id));
    const members=new Set(source.flatMap(i=>i.sourceAlertIds));
    const rows=store.alerts.filter(a=>members.has(a.id)&&ids.has(a.incidentId));
    const groups=new Set(rows.map(a=>a.incidentId));
    return {alerts:rows.length,groups:groups.size,reduction:rows.length?Math.round((1-groups.size/rows.length)*100):null};
  }
  function started(run){
    if(run.completion==='not_escalated')return false;
    return ['partial','completed'].includes(run.completion)||(run.steps||[]).some(s=>
      ['recon','forensic','responder','report'].includes(s.kind)||
      (s.kind==='graph_step'&&s.payload?.step_status!=='skipped'&&['enrichment','investigation'].includes(s.payload?.node)));
  }
  function activities(incident,members,runs){
    if(!incident?.recordedIncident)return [];
    const alerts=new Map(members.map(a=>[a.id,a]));
    const rows=members.map(a=>({id:'occurrence:'+a.id,incidentId:incident.id,caseIds:[],
      title:'告警发生',type:'告警',target:a.title,performedBy:a.source||'未记录',trigger:'自动',
      status:'Recorded',time:a.event_time||a.first,alertId:a.id}));
    for(const run of runs){
      const inputs=run.alertIds.filter(id=>alerts.has(id));if(!inputs.length)continue;
      for(const s of run.steps||[])rows.push({id:'event:'+(s.id||run.id+':'+s.seq),incidentId:incident.id,
        caseIds:[],title:s.summary||s.kind,type:s.kind,target:inputs.map(id=>alerts.get(id).title).join('；'),
        performedBy:s.name||'未记录',trigger:'自动',status:'Recorded',time:s.time,runId:run.id,seq:s.seq});
    }
    return rows.sort((a,b)=>Date.parse(b.time)-Date.parse(a.time));
  }
  function relations(store,members){
    const nodes=[],edges=[],seen=new Set();
    for(const a of members){
      nodes.push({id:a.id,kind:'alert',label:a.title});
      for(const id of a.entityIds||[]){
        const entity=store.assets.find(e=>e.id===id);if(!entity)continue;
        if(!seen.has(id)){seen.add(id);nodes.push({id,kind:{device:'host',user:'user'}[entity.type]||'asset',label:entity.name,entityId:id});}
        edges.push({source:a.id,target:id,label:'源告警记录的对象关联'});
      }
    }
    return {nodes,edges};
  }
  function caseActivities(store,c,runs){
    if(!c.localCollection&&!c.recordedCase&&!c.incidentCreated)return [];
    const current=new Set(c.alertIds),ids=new Set([...current,...runs.flatMap(r=>r.alertIds)]);
    const rows=activities({id:c.incidentId,recordedIncident:true},store.alerts.filter(a=>ids.has(a.id)),runs);
    return rows.filter(a=>a.runId||current.has(a.alertId)).map(a=>{
      const run=runs.find(r=>r.id===a.runId),alert=store.alerts.find(x=>x.id===(a.alertId||run?.alertIds[0]));
      return {...a,id:'case:'+c.id+':'+a.id,caseIds:[c.id],incidentId:alert?.incidentId||null};
    });
  }
  function caseStats(runs){return {
    runs:runs.length,started:runs.filter(started).length,partial:runs.filter(r=>r.completion==='partial').length,
    triage:runs.filter(r=>r.completion==='not_escalated').length,
    tools:runs.reduce((n,r)=>n+(r.tools||[]).length,0),artifacts:runs.reduce((n,r)=>n+(r.artifacts||[]).length,0),
    events:runs.reduce((n,r)=>n+(r.steps||[]).length,0),reports:runs.filter(r=>r.report).length
  };}
  return {merge,runs,metrics,started,activities,relations,caseActivities,caseStats};
})();
