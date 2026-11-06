/* Offline projection of verified socai2 exports. It never executes or invents a Run. */
'use strict';
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root){root.socai2RecordedImport=api;root.mergeSocai2RecordedData=store=>(root.socai2RecordedDataSets||(root.socai2RecordedData?[root.socai2RecordedData]:[])).map(data=>api.merge(store,data));}
})(typeof window==='object'?window:null,()=>{
  const list=v=>Array.isArray(v)?v:[],clone=v=>v===undefined?undefined:JSON.parse(JSON.stringify(v));
  const segment=v=>encodeURIComponent(String(v)).replace(/[!'()*~]/g,c=>'%'+c.charCodeAt(0).toString(16).toUpperCase()).replace(/%/g,'~');
  const states={new:'New',in_progress:'In progress',resolved:'Resolved',unknown:'Unknown'};
  const taskStates={not_started:'New',in_progress:'In progress',completed:'Completed',cancelled:'Cancelled'};
  const severity={critical:'严重',high:'高',medium:'中',low:'低',info:'信息'};
  const tableNames=['alerts','alert_materials','alert_source_refs','alert_objects','alert_assessments','incidents','incident_alerts','incident_diagnoses','cases','case_alerts','case_incidents','results','result_members','tasks','task_revisions','case_assessments','case_assessment_sources','case_assessment_members','runs','run_members','run_steps','artifacts','activities','case_input_freshness'];
  const numeric=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0?v:null;
  // Read the preserved latest material for display; never backfill category or mutate an export.
  function detectionView(alert){
    if(!alert?.recordedImport)return null;
    const material=alert.detailMaterial?.raw?.material,source=alert.sourceRecord;
    const valid=material&&source&&material.id===source.latest_material_id&&material.alert_id===source.id&&material.tenant_id===source.tenant_id;
    const detection=valid&&material.detection&&typeof material.detection==='object'?material.detection:{};
    const value=detection.confidence_value,available=detection.confidence_state==='available'&&numeric(value)!==null&&value<=100;
    return {materialId:valid?material.id:null,sourcePath:'alert_materials.detection',confidenceState:detection.confidence_state??null,score:available?value:null,scoreSource:detection.score_source??null,confidenceLabel:detection.confidence_label??null,confidenceRationale:clone(detection.confidence_rationale)??null,labelsProvided:typeof detection.labels_provided==='boolean'?detection.labels_provided:null,tactics:[...new Set(list(detection.tactics).filter(v=>typeof v==='string'&&v.trim()))],techniques:[...new Set(list(detection.techniques).filter(v=>typeof v==='string'&&v.trim()))]};
  }
  // Presentation only: read saved stage outputs even when a later stage failed.
  // Never repair the model JSON, publish a Result, adopt an assessment or mutate storage.
  function savedOutput(run,step){
    const source=step?.payload?.source_step,artifact=list(run.artifacts).find(a=>a.id===step?.storedOutputArtifactId),record=artifact?.sourceRecord;
    if(!source||source.run_id!==run.sourceRunId||source.tenant_id!==run.sourceTenantId||record?.run_id!==source.run_id||record?.tenant_id!==source.tenant_id||record?.step_id!==source.id||record?.id!==source.output_artifact_id)return null;
    const body=run.artifactBodies?.[artifact.id];
    return body?.mode==='full'&&body.format==='json'?{artifact,content:body.content}:null;
  }
  function responseJson(raw){
    if(!raw||raw.error||raw.status!=='completed')return null;
    const messages=list(raw.output).filter(o=>o.type==='message'&&o.role==='assistant');
    if(messages.some(m=>m.status!=='completed'||list(m.content).some(c=>c.type==='refusal')))return null;
    const text=messages.flatMap(m=>list(m.content).filter(c=>c.type==='output_text'&&typeof c.text==='string').map(c=>c.text)).join('');
    try{const value=JSON.parse(text);return value&&typeof value==='object'&&!Array.isArray(value)?value:null;}catch{return null;}
  }
  const draftLabel='模型原答（格式校验未通过，未采用）';
  function graphContextView(run){
    const context=run.savedGraphContext;if(!context)return null;
    const aliases=new Map(),nodes=list(context.nodes).map(node=>{
      const source=node.sourceRecord,ids=list(source?.alert_ids),alert=ids.length===1?list(run.input?.alerts).find(a=>a.sourceAlertId===ids[0]):null;
      // C5 encodes alert roots as "other". Identify them by the exact frozen
      // alert reference, never by a matching title or a shared object label.
      const isAlert=alert&&source?.type==='other'&&source.object_key===null&&list(source.source_refs).some(ref=>{
        if(ref.type!=='artifact'||ref.source_path!=='$.alerts.'+alert.sourceAlertId+'.alert')return false;
        const a=list(run.artifacts).find(a=>a.sourceArtifactId===ref.id),body=a&&run.artifactBodies?.[a.id];
        return a?.sourceRecord?.run_id===run.sourceRunId&&a.sourceRecord.tenant_id===run.sourceTenantId&&body?.mode==='full'&&body.content?.alerts?.[alert.sourceAlertId]?.alert?.id===alert.sourceAlertId;
      });
      if(!isAlert)return node;
      aliases.set(node.id,alert.id);return {...node,id:alert.id,kind:'alert'};
    });
    return {...context,nodes,edges:list(context.edges).map(edge=>({...edge,source:aliases.get(edge.source)||edge.source,target:aliases.get(edge.target)||edge.target}))};
  }
  function runView(run){
    if(!run?.recordedImport||run.sourceRecord?.run?.id!==run.sourceRunId||run.sourceRecord.run.tenant_id!==run.sourceTenantId)return run;
    const steps=list(run.steps),c3=steps.find(s=>s.sourceKind==='stage'&&s.payload?.stage_code==='C3'&&s.payload?.step_status==='completed'),initial=savedOutput(run,c3);
    const initialAnalysis=initial?.content?.run_id===run.sourceRunId&&initial.content.state==='completed'?initial.content.analysis:null;
    const c5=steps.find(s=>s.sourceKind==='graph'&&s.payload?.stage_code==='C5'&&s.payload?.step_status==='completed'),receipt=savedOutput(run,c5),graph=list(run.artifacts).find(a=>a.id===run.savedGraphArtifactId);
    const graphComplete=!!(receipt?.content?.run_id===run.sourceRunId&&receipt.content.state==='completed'&&receipt.content.graph_artifact_id===graph?.sourceArtifactId&&graph?.kind==='alert_graph'&&graph.schemaVersion==='socai2.baseline-graph.v1'&&graph.sourceRecord?.run_id===run.sourceRunId&&graph.sourceRecord?.tenant_id===run.sourceTenantId&&run.savedGraphContext);
    const model=steps.filter(s=>s.sourceKind==='model'&&s.payload?.stage_code==='C6').sort((a,b)=>b.seq-a.seq)[0],response=savedOutput(run,model);
    const rejected=response?.artifact?.kind==='model_response'&&response.content?.payload?.validation_error==='delivery_shape_invalid'&&model.payload?.error?.code==='delivery_shape_invalid';
    const draft=rejected&&run.sourceResult?.conclusion_origin!=='model'?responseJson(response.content.payload.raw):null;
    const preview=draft&&typeof draft.conclusion?.text==='string'&&draft.conclusion.text.trim()?{label:draftLabel,text:draft.conclusion.text,analysis:draft.analysis||{},impact:draft.impact||{},comparison:draft.comparison||{},closingNote:draft.closing_note||null,sourceArtifactId:response.artifact.id,sourceStepId:model.id,validationError:response.content.payload.validation_error}:null;
    const view={...run,savedGraphContext:graphContextView(run),graphEligible:graphComplete,savedGraphStageCompleted:graphComplete,modelReplyPreview:preview,initialAnalysisPreview:initialAnalysis?{summary:initialAnalysis.summary,sourceArtifactId:initial.artifact.id}:null};
    const delivery=savedOutput(run,steps.filter(s=>s.sourceKind==='stage'&&s.payload?.stage_code==='C6').sort((a,b)=>b.seq-a.seq)[0]);
    const markdown=list(run.artifacts).find(a=>a.sourceArtifactId===delivery?.content?.markdown_artifact_id&&a.kind==='report_markdown'&&a.sourceRecord?.run_id===run.sourceRunId&&a.sourceRecord?.tenant_id===run.sourceTenantId),savedReport=markdown?run.artifactBodies?.[markdown.id]:null;
    if(savedReport?.mode==='full'&&savedReport.format==='text')view.report=savedReport.content;
    view.steps=steps.map(s=>{
      if(s===c3&&typeof initialAnalysis?.summary==='string')return {...s,summary:'已完成初步分析：'+initialAnalysis.summary};
      if(preview&&s.sourceKind==='stage'&&s.payload?.stage_code==='C6')return {...s,summary:draftLabel+'：'+preview.text};
      return s;
    });
    // Rejected responses remain available in execution artifacts and steps.
    // They cannot replace the persisted Result's conclusion, findings or report.
    return view;
  }
  function caseDescription(c){
    // Case information is a persisted business field, not a stage-output fallback.
    return c.description||'';
  }
  function adaptExport(database,manifest,apiResponses=[],pageDataRows=[]){
    if(!database||typeof database!=='object'||Array.isArray(database))throw Error('database_object_required');
    if(['truth','ground_truth','answer_key','expected_answers','audit_truth'].some(k=>Object.hasOwn(database,k)||Object.hasOwn(manifest||{},k)))throw Error('audit_truth_is_not_page_input');
    if(manifest?.schema_version!=='socai2.page-export.v1'||manifest.input_kind!=='synthetic')throw Error('unsupported_page_export_manifest');
    for(const key of ['batch_id','source_environment','exported_at'])if(typeof manifest[key]!=='string'||!manifest[key].trim())throw Error('manifest_field_required:'+key);
    if(!Number.isFinite(Date.parse(manifest.exported_at))||!(/^[a-f0-9]{64}$/i).test(manifest.source_sha256||''))throw Error('invalid_export_provenance');
    for(const key of ['cases','runs','alerts','artifacts','run_steps'])if(!Array.isArray(database[key]))throw Error('export_table_required:'+key);
    if(!Array.isArray(apiResponses))throw Error('api_responses_array_required');
    const warnings=[],tables={},maps={};
    for(const name of tableNames){
      if(database[name]!==undefined&&!Array.isArray(database[name]))throw Error('invalid_export_table:'+name);
      if(database[name]===undefined)warnings.push('table_not_exported:'+name);
      tables[name]=list(database[name]);maps[name]=new Map();
      for(const row of tables[name]){
        if(!row||typeof row!=='object'||typeof row.tenant_id!=='string'||!row.tenant_id)throw Error('tenant_missing:'+name);
        const id=name==='case_input_freshness'?row.case_id:row.id;
        if(typeof id!=='string'||!id)throw Error('identity_missing:'+name);
        const key=row.tenant_id+'\n'+id;if(maps[name].has(key))throw Error('duplicate_source_identity:'+name);
        maps[name].set(key,row);
      }
    }
    const get=(name,tenant,id)=>id?maps[name].get(tenant+'\n'+id):null;
    const rows=(name,tenant,key,value)=>tables[name].filter(r=>r.tenant_id===tenant&&r[key]===value);
    const required=(name,tenant,id)=>{const row=get(name,tenant,id);if(!row)throw Error('missing_scoped_reference:'+name+':'+id);return row;};
    const uid=(tenant,kind,id)=>['socai2',segment(manifest.source_environment),segment(manifest.batch_id),segment(tenant),kind,segment(id)].join('!');
    const scope=row=>({sourceEnvironment:JSON.stringify([manifest.source_environment,manifest.batch_id]),sourceTenantId:row.tenant_id,recordedImport:true,syntheticInput:true});
    const owner=row=>row.owner_id||row.owner_source_value||(row.assignment_state==='unassigned'?'未分配':'未记录');
    const assetTypes={host:'device',user:'user',ip:'ip',file:'file',domain:'domain',url:'url',process:'process'};
    const data={schemaVersion:'socai2.recorded-page.v1',alerts:[],assets:[],incidents:[],cases:[],runs:[],evidence:[],activities:[],sourceArtifacts:[],provenance:{...clone(manifest),warnings}};
    const assetMap=new Map();
    function objectsFor(alert,materialId){return rows('alert_objects',alert.tenant_id,'alert_id',alert.id).filter(x=>x.material_id===materialId);}
    function assetFor(obj){
      const id=uid(obj.tenant_id,'object',JSON.stringify([obj.namespace,obj.object_key]));
      if(!assetMap.has(id))assetMap.set(id,{id,...scope(obj),type:assetTypes[obj.object_type]||obj.object_type||'entity',name:String(obj.normalized_value??obj.raw_value??obj.object_key),tags:[],inventory:false,sourceObjectKey:obj.object_key,sourceRecord:clone(obj)});
      return id;
    }
    for(const alert of tables.alerts){
      const material=get('alert_materials',alert.tenant_id,alert.latest_material_id),objects=objectsFor(alert,alert.latest_material_id),links=rows('incident_alerts',alert.tenant_id,'alert_id',alert.id),assess=get('alert_assessments',alert.tenant_id,alert.latest_triage_id);
      if(material&&material.alert_id!==alert.id)throw Error('alert_material_owner_mismatch');
      if(assess&&assess.alert_id!==alert.id)throw Error('alert_assessment_owner_mismatch');
      const history=[alert.event_time?{time:alert.event_time,title:'告警发生',description:alert.title}:null,alert.ingested_at?{time:alert.ingested_at,title:'告警入库',description:alert.source_namespace||'来源未记录'}:null].filter(Boolean);
      data.alerts.push({id:uid(alert.tenant_id,'alert',alert.id),...scope(alert),sourceAlertId:alert.id,persistedRecord:true,title:alert.title||'未记录标题',description:alert.description||'',severity:severity[alert.severity]||'未记录',sourceSeverity:alert.severity??null,status:states[alert.handling_status]||'Unknown',investigation:'Not set',owner:owner(alert),category:alert.category||'未记录',source:alert.source_namespace||alert.connector_type||'未记录',entityIds:objects.map(assetFor),tags:list(alert.tags),classification:'Not set',event_time:alert.event_time??null,first:alert.event_time??null,last:alert.last_seen_at??null,incidentId:links.length===1?uid(alert.tenant_id,'incident',links[0].incident_id):null,caseId:null,comments:[],disposition:alert.disposition??null,hostNames:objects.filter(x=>x.object_type==='host').map(x=>String(x.normalized_value??x.raw_value)),tactics:[],iocKeys:objects.filter(x=>['ip','domain','url','file'].includes(x.object_type)).map(x=>x.object_key),sourceRecord:clone(alert),detailMaterial:{timelineVersion:2,history,runs:[],raw:{alert:clone(alert),material:clone(material)||null,source_refs:clone(rows('alert_source_refs',alert.tenant_id,'alert_id',alert.id)),source_artifacts:clone(rows('artifacts',alert.tenant_id,'alert_id',alert.id).filter(a=>!a.run_id))},confidence:{score:null,factors:[]},explanation:{summary:null,evidence:[],gaps:[],suggestedActions:[]},responseRecommendations:[]}});
    }
    data.assets=[...assetMap.values()];
    for(const incident of tables.incidents){
      const members=rows('incident_alerts',incident.tenant_id,'incident_id',incident.id).map(x=>required('alerts',incident.tenant_id,x.alert_id));
      const diagnosis=get('incident_diagnoses',incident.tenant_id,incident.latest_diagnosis_id);
      data.incidents.push({id:uid(incident.tenant_id,'incident',incident.id),...scope(incident),recordedIncident:true,sourceIncidentId:incident.id,sourceAlertIds:members.map(x=>uid(x.tenant_id,'alert',x.id)),title:incident.title||'未记录标题',description:incident.description||'',first:incident.created_at??null,last:incident.business_updated_at??null,updated:incident.business_updated_at??null,status:states[incident.handling_status]||'Unknown',owner:owner(incident),severity:severity[incident.severity_override]||'未记录',priority:incident.priority_state==='available'&&incident.priority_value!=null?numeric(Number(incident.priority_value)):null,classification:'Not set',tags:list(incident.tags),sourceRecord:clone(incident),savedDiagnosis:clone(diagnosis)||null});
    }
    function taskView(task,revision){
      if(revision.tenant_id!==task.tenant_id||revision.task_id!==task.id||revision.case_id!==task.case_id)throw Error('task_revision_owner_mismatch');
      const resultScope=clone(revision.result_scope),origin=get('results',task.tenant_id,task.origin_result_id);
      return {id:uid(task.tenant_id,'task',task.id),...scope(task),title:revision.title||'未记录事项',description:revision.description||'',owner:revision.assignee_id||'未分配',due:revision.due_at??null,status:taskStates[revision.state]||'Unknown',result:revision.result_text??null,createdAt:task.created_at??null,updatedAt:revision.changed_at??null,completedAt:revision.completed_at??null,completedBy:revision.completed_by??null,changedBy:revision.changed_by??null,sourceRunId:origin?uid(task.tenant_id,'run',origin.source_run_id):null,referenceContext:{alertIds:list(resultScope?.alert_ids).map(id=>uid(task.tenant_id,'alert',id)),entityIds:[],objectKeys:list(resultScope?.object_keys),windowStart:resultScope?.window_start??null,windowEnd:resultScope?.window_end??null,limitations:list(resultScope?.limitations)},resultScope,materials:[],revisionId:revision.id,revisionNumber:revision.revision,sourceRecord:{task:clone(task),revision:clone(revision)}};
    }
    for(const cas of tables.cases){
      const members=rows('case_alerts',cas.tenant_id,'case_id',cas.id).map(x=>required('alerts',cas.tenant_id,x.alert_id)),linked=rows('case_incidents',cas.tenant_id,'case_id',cas.id);
      linked.forEach(x=>required('incidents',cas.tenant_id,x.incident_id));
      const tasks=rows('tasks',cas.tenant_id,'case_id',cas.id).map(task=>{const current=taskView(task,required('task_revisions',task.tenant_id,task.current_revision_id));current.revisionHistory=rows('task_revisions',task.tenant_id,'task_id',task.id).sort((a,b)=>a.revision-b.revision).map(r=>taskView(task,r));return current;});
      const matchingPageData=list(pageDataRows).filter(p=>p.case_id===cas.id&&p.tenant_id===cas.tenant_id);
      if(matchingPageData.length>1)throw Error('ambiguous_case_page_data');
      const projected=matchingPageData[0],pageData=projected?.page_data||null;
      const sameDeadline=pageData?.due_at===(cas.due_at??null)||(pageData?.due_at&&cas.due_at&&Number.isFinite(Date.parse(cas.due_at))&&Date.parse(pageData.due_at)===Date.parse(cas.due_at));
      if(projected&&(projected.case_row_version!==cas.row_version||projected.current_assessment_id!==cas.current_assessment_id||pageData?.schema_version!=='socai2.case-page-data.v1'||pageData.classification!==(cas.classification??null)||!sameDeadline))throw Error('case_page_data_snapshot_mismatch');
      if(pageData&&pageData.evidence.artifact_id!==(cas.current_evidence_artifact_id??null))throw Error('case_evidence_pointer_mismatch');
      if(cas.current_evidence_artifact_id&&!pageData)throw Error('case_evidence_projection_missing');
      let assessment=null;
      if(cas.current_assessment_id){
        const saved=required('case_assessments',cas.tenant_id,cas.current_assessment_id);if(saved.case_id!==cas.id)throw Error('case_assessment_owner_mismatch');
        const sources=rows('case_assessment_sources',cas.tenant_id,'assessment_id',saved.id),coverage=rows('case_assessment_members',cas.tenant_id,'assessment_id',saved.id);
        const resultSources=sources.filter(x=>x.result_id).map(x=>required('results',cas.tenant_id,x.result_id)),taskSources=sources.filter(x=>x.task_revision_id).map(x=>required('task_revisions',cas.tenant_id,x.task_revision_id)),artifactSources=sources.filter(x=>x.artifact_id).map(x=>required('artifacts',cas.tenant_id,x.artifact_id));if([...resultSources,...taskSources,...artifactSources].some(x=>x.case_id!==cas.id))throw Error('case_assessment_source_mismatch');
        const replies=list(apiResponses).filter(r=>r.method==='GET'&&r.status===200&&r.path==='/api/v1/socai2/cases/'+cas.id&&r.body?.case?.id===cas.id);
        if(replies.length>1)throw Error('ambiguous_case_api_response');
        const detail=replies[0]?.body;
        if(detail&&(detail.case.current_assessment_id!==saved.id||detail.current_assessment?.value?.id!==saved.id))throw Error('case_api_assessment_mismatch');
        // CaseView omits tenant_id: refuse cross-tenant ambiguous UUIDs rather than guessing.
        if(detail&&tables.cases.filter(x=>x.id===cas.id).length!==1)throw Error('ambiguous_case_api_tenant');
        const freshness=detail?.current_assessment?.input_freshness||null;
        assessment={conclusion:saved.conclusion,updatedAt:saved.formed_at??null,author:saved.adopted_by||null,alertIds:coverage.map(x=>uid(cas.tenant_id,'alert',x.alert_id)),sourceRunIds:[...new Set([...resultSources.map(x=>x.source_run_id),...artifactSources.map(x=>x.run_id)].filter(Boolean).map(id=>uid(cas.tenant_id,'run',id)))],taskIds:[...new Set(taskSources.map(x=>uid(cas.tenant_id,'task',x.task_id)))],basis:[],unresolved:[],inputFreshness:freshness?{state:freshness.state,reasons:list(freshness.reasons)}:null,sourceRecord:{assessment:clone(saved),sources:clone(sources),members:clone(coverage),case_api_response:clone(detail)||null}};
      }
      if(pageData&&pageData.determination!==(assessment?.conclusion??null))throw Error('case_determination_mismatch');
      const verdictNames={malicious:'Malicious',suspicious:'Suspicious',clean:'Clean',unknown:'未判定',conflicting:'有冲突'};
      for(const e of list(pageData?.evidence?.entries)){
        const entityIds=list(e.object_keys).map(key=>tables.alert_objects.find(o=>o.tenant_id===cas.tenant_id&&o.material_id===key.material_id&&o.object_key===key.object_key)).filter(Boolean).map(assetFor);
        data.evidence.push({id:uid(cas.tenant_id,'evidence',cas.id+':'+e.evidence_id),...scope(cas),caseId:uid(cas.tenant_id,'case',cas.id),name:e.title,type:e.type,entityId:entityIds[0]||null,entityIds,alertId:uid(cas.tenant_id,'alert',e.alert_ids[0]),alertIds:e.alert_ids.map(a=>uid(cas.tenant_id,'alert',a)),verdict:verdictNames[e.verdict],threat:e.threat?.label||'',remediation:e.remediation?'已有处置回执':'未记录',origin:'已保存证据条目',sourceRecord:clone(e),sourceRefs:clone(e.source_refs),indexArtifactId:pageData.evidence.artifact_id});
      }
      data.cases.push({id:uid(cas.tenant_id,'case',cas.id),...scope(cas),recordedCase:true,sourceCaseId:cas.id,sourceRecord:clone(cas),exportProvenance:clone(manifest),title:cas.title||'未记录标题',description:cas.description||'',alertIds:members.map(x=>uid(x.tenant_id,'alert',x.id)),incidentIds:linked.map(x=>uid(cas.tenant_id,'incident',x.incident_id)),incidentId:linked.length===1?uid(cas.tenant_id,'incident',linked[0].incident_id):null,sourceRunIds:rows('runs',cas.tenant_id,'case_id',cas.id).map(x=>uid(cas.tenant_id,'run',x.id)),created:cas.created_at??null,updated:cas.business_updated_at??null,owner:owner(cas),status:states[cas.handling_status]||'Unknown',severity:severity[cas.severity]||'未记录',sourceSeverity:cas.severity??null,priority:cas.priority_state==='available'&&cas.priority_value!=null?numeric(Number(cas.priority_value)):null,classification:({true_positive:'True positive',informational:'Informational',false_positive:'False positive'})[cas.classification]||'Not set',tags:list(cas.tags),tasks,assessment,determination:assessment?.conclusion??null,pageData:clone(pageData),due:cas.due_at??null,resolutionNote:cas.resolution_note??null,attachments:[]});
    }
    for(const run of tables.runs){
      const tenant=run.tenant_id,runId=uid(tenant,'run',run.id),steps=rows('run_steps',tenant,'run_id',run.id).sort((a,b)=>a.seq-b.seq),arts=rows('artifacts',tenant,'run_id',run.id),members=rows('run_members',tenant,'run_id',run.id);
      const frozen=get('artifacts',tenant,run.input_artifact_id),context=arts.find(a=>a.schema_version==='socai2.baseline-context.v1'&&a.kind==='source_snapshot')?.content_json;
      if(frozen&&frozen.run_id!==run.id)throw Error('frozen_input_run_mismatch');
      if(run.case_id)required('cases',tenant,run.case_id);
      let alertIds=members.map(m=>m.alert_id);
      if(!alertIds.length&&run.alert_id)alertIds=[run.alert_id];
      if(!alertIds.length&&run.kind==='incident_diagnosis')alertIds=list(frozen?.content_json?.members).map(m=>m.alert_id||m.id||m.alert?.id).filter(Boolean);
      alertIds=[...new Set(alertIds)];alertIds.forEach(id=>required('alerts',tenant,id));
      if(run.kind==='incident_diagnosis'&&!alertIds.length)warnings.push('incident_frozen_members_not_exported:'+run.id);
      const runResultRows=rows('results',tenant,'source_run_id',run.id),superseded=new Set(runResultRows.map(r=>r.supersedes_result_id).filter(Boolean)),currentResults=runResultRows.filter(r=>!superseded.has(r.id)&&r.kind==='baseline');
      if(currentResults.length>1)throw Error('ambiguous_current_baseline_result');
      const result=currentResults[0]||null;
      if(result&&(result.case_id!==run.case_id||run.kind!=='baseline'))throw Error('result_run_case_mismatch');
      const triages=rows('alert_assessments',tenant,'source_run_id',run.id).filter(x=>x.kind==='triage'),triage=run.kind==='alert_basic'&&triages.length===1&&triages[0].alert_id===run.alert_id?triages[0]:null;
      const diagnoses=rows('incident_diagnoses',tenant,'source_run_id',run.id),diagnosis=run.kind==='incident_diagnosis'&&diagnoses.length===1&&diagnoses[0].incident_id===run.incident_id?diagnoses[0]:null;
      const modelSteps=steps.filter(s=>s.kind==='model'&&!['planned','skipped'].includes(s.state)),knownSteps=modelSteps.filter(s=>s.usage?.usage_state==='reported'&&numeric(s.usage.total_tokens)!==null);
      const artifacts=arts.map(a=>({id:uid(tenant,'artifact',a.id),kind:a.kind,sha256:a.sha256??null,size_bytes:a.size_bytes??null,event_id:a.step_id?uid(tenant,'step',a.step_id):null,created_at:a.captured_at??null,sourceArtifactId:a.id,schemaVersion:a.schema_version??null,sourceRecord:clone({...a,content_json:undefined,content_text:undefined})}));
      const artifactBodies={};for(const a of arts){const body=a.content_json!=null?{format:'json',content:clone(a.content_json)}:a.content_text!=null?{format:'text',content:a.content_text}:null;artifactBodies[uid(tenant,'artifact',a.id)]=body?{...body,mode:'full'}:{mode:'metadata',note:a.blob_ref?'原件为外部存储，本次未导出正文。':'本次导出没有正文，仅保留目录。'};}
      const stepViews=steps.map(step=>{
        for(const key of ['input_artifact_id','output_artifact_id']){const a=get('artifacts',tenant,step[key]);if(a&&a.run_id!==run.id)throw Error('step_artifact_run_mismatch');}
        return {id:uid(tenant,'step',step.id),seq:step.seq,name:step.name||step.stage_code,kind:step.kind==='stage'?'阶段记录':step.kind==='tool'?'tool_call':step.kind,sourceKind:step.kind,storedOutputArtifactId:step.output_artifact_id?uid(tenant,'artifact',step.output_artifact_id):null,time:step.ended_at||step.started_at||null,summary:step.state==='skipped'?'已跳过':step.state||'状态未记录',payload:{...clone(step),input_artifact_id:step.input_artifact_id?uid(tenant,'artifact',step.input_artifact_id):null,output_artifact_id:step.output_artifact_id?uid(tenant,'artifact',step.output_artifact_id):null,source_step:clone(step),step_status:step.state},adopted:null};
      });
      const tools=steps.filter(s=>s.kind==='tool').map(step=>{const output=get('artifacts',tenant,step.output_artifact_id),input=get('artifacts',tenant,step.input_artifact_id),body=output?.content_json;return {id:uid(tenant,'tool',step.id),name:body?.tool_name||step.actual_args?.tool_name||step.name,time:step.ended_at||step.started_at||null,args:clone(step.actual_args||input?.content_json)||null,result:body!=null?JSON.stringify(body):output?.content_text??null,resultFormat:body!=null||output?.content_text!=null?'saved_result':'metadata',success:step.state==='completed'&&body?['error','unavailable'].includes(body.state)?false:['success','empty'].includes(body.state)?true:null:['failed','timeout'].includes(step.state)?false:null,savedState:body?.state||step.state,sourceRecord:clone(step),sourceArtifactId:step.output_artifact_id||null};});
      const report=get('artifacts',tenant,result?.report_artifact_id);if(report&&report.run_id!==run.id)throw Error('report_artifact_run_mismatch');const graph=arts.find(a=>a.kind==='alert_graph'&&a.schema_version==='socai2.baseline-graph.v1'&&a.content_json);
      let savedGraphContext=null;
      if(graph){const g=graph.content_json,nodeIds=new Map();const nodes=list(g.nodes).map(n=>{const id=n.type==='alert'&&list(n.alert_ids).length===1?uid(tenant,'alert',n.alert_ids[0]):uid(tenant,'graph-node',run.id+':'+n.id);nodeIds.set(n.id,id);return {id,kind:assetTypes[n.type]||n.type,label:n.label,sourceRecord:clone(n)};});const edges=list(g.edges).map(e=>{if(!nodeIds.has(e.from)||!nodeIds.has(e.to))throw Error('graph_edge_missing_node');return {id:uid(tenant,'graph-edge',run.id+':'+e.id),source:nodeIds.get(e.from),target:nodeIds.get(e.to),label:e.relation+(e.strength==='candidate'?'（候选关联）':''),sourceRecord:clone(e)};});savedGraphContext={nodes,edges,source:'本轮 C5 已保存关系投影；关系不证明攻击因果',generatedAt:graph.captured_at,limitations:list(g.limitations)};}
      const sourceResult=result?clone(result):null;
      const conclusion=result?(result.conclusion_origin==='model'?result.conclusion:result.closing_note?'系统交接：'+result.closing_note:null):triage?.rationale||diagnosis?.summary||null;
      const findings=list(result?.findings||diagnosis?.diagnosis?.findings).map(f=>typeof f==='string'?f:{...clone(f),summary:(f.state?({observed:'观察',inferred:'推断',unresolved:'待核',withdrawn:'已撤回'}[f.state]||f.state)+'：':'')+(f.statement||f.text||'')});
      const limitationTexts=[...list(result?.case_impact?.cannot_generalize),...list(result?.questions).filter(q=>q.state!=='answered').map(q=>q.text),...(run.stop_reason?[run.stop_reason]:[])];
      const taskSnapshots=[];for(const entry of Object.values(context?.tasks||{})){const revision=entry.revision;if(!revision)continue;const task=get('tasks',tenant,revision.task_id);if(task)taskSnapshots.push(taskView(task,revision));else warnings.push('frozen_task_identity_missing:'+revision.task_id);}
      const inputAlerts=alertIds.map(id=>{const frozenAlert=context?.alerts?.[id]?.alert||list(frozen?.content_json?.members).find(x=>(x.alert_id||x.id||x.alert?.id)===id)?.alert;return {id:uid(tenant,'alert',id),sourceAlertId:id,...(frozenAlert?{...clone(frozenAlert),id:uid(tenant,'alert',id),sourceAlertId:id}:{title:'冻结字段未单独导出'})};});
      const view={id:runId,...scope(run),sourceRunId:run.id,exportProvenance:clone(manifest),sourceCaseId:run.case_id??null,caseId:run.case_id?uid(tenant,'case',run.case_id):null,title:run.title||'未记录调查标题',recorded:true,fixture:false,investigationKind:run.kind,trigger:run.trigger??null,alertIds:alertIds.map(id=>uid(tenant,'alert',id)),input:{alerts:inputAlerts,source_snapshot:clone(frozen?.content_json)||null,frozen_context:clone(context)||null},input_summary:null,status:run.state,completion:run.delivery_state==='complete'?'completed':run.delivery_state==='partial'?'partial':null,sourceDeliveryState:run.delivery_state,verdict:triage?.verdict??null,confidence:triage?.confidence??null,triage:triage?{verdict:triage.verdict,confidence:triage.confidence,rationale:triage.rationale}:null,outcome:{purpose:run.purpose??result?.purpose??null,conclusion,findings,change:result?.change_summary??null,impact:result?.case_impact?.summary??null,limitations:limitationTexts,basis:[]},findings,started:run.started_at??null,requestedAt:run.requested_at??null,ended:run.ended_at??null,steps:stepViews,tools,graphs:{},savedGraphContext,savedGraphArtifactId:graph?uid(tenant,'artifact',graph.id):null,graphEligible:!!graph,artifacts,artifactBodies,report:report?.content_text??null,stop:run.stop_reason||null,calls:modelSteps.length,tokens:knownSteps.length===modelSteps.length?knownSteps.reduce((n,s)=>n+s.usage.total_tokens,0):null,knownTokens:knownSteps.reduce((n,s)=>n+s.usage.total_tokens,0),unknownTokenCalls:modelSteps.length-knownSteps.length,unpriced:modelSteps.filter(s=>s.usage?.cost_state!=='priced').length,actions:list(result?.recommendations).map(a=>({...clone(a),description:a.action_type,rationale:a.reason,targets:clone(a.targets),target:list(a.targets).map(t=>t.display_name||t.object_key).join('、')||null,requires_approval:a.approval_requirement==='required'?true:a.approval_requirement==='not_required'?false:null,approval_requirement:a.approval_requirement,sourceRecord:clone(a)})),executed:[],referenceSnapshot:context?{capturedAt:context.captured_at??null,tasks:taskSnapshots,runs:[]}:null,sourceRecord:{run:clone(run),results:clone(runResultRows),result_members:result?clone(rows('result_members',tenant,'result_id',result.id)):[],alert_assessments:clone(triages),incident_diagnoses:clone(diagnoses),run_members:clone(members)},sourceResult};
      data.runs.push(view);
    }
    for(const activity of tables.activities)data.activities.push({id:uid(activity.tenant_id,'activity',activity.id),...scope(activity),time:activity.occurred_at??null,title:activity.summary||activity.action||'未记录活动',type:activity.action||'已保存活动',user:activity.actor?.user_id||'未记录',description:activity.summary||'',caseIds:activity.subject_case_id?[uid(activity.tenant_id,'case',activity.subject_case_id)]:[],incidentId:activity.subject_incident_id?uid(activity.tenant_id,'incident',activity.subject_incident_id):null,sourceRecord:clone(activity)});
    data.sourceArtifacts=tables.artifacts.filter(a=>!a.run_id).map(a=>({id:uid(a.tenant_id,'artifact',a.id),...scope(a),sourceArtifactId:a.id,sourceRecord:clone(a)}));
    data.provenance.artifact_counts={total:tables.artifacts.length,run_bound:data.runs.reduce((n,r)=>n+r.artifacts.length,0),without_run:data.sourceArtifacts.length};
    data.provenance.counts=Object.fromEntries(['alerts','assets','incidents','cases','runs','activities'].map(k=>[k,data[k].length]));
    return data;
  }
  function merge(store,data){
    if(data?.schemaVersion!=='socai2.recorded-page.v1')throw Error('unsupported_recorded_page_data');
    const added={};
    for(const key of ['alerts','assets','incidents','cases','evidence','activities']){
      store[key]||=[];const known=new Set(store[key].map(x=>x.id)),fresh=list(data[key]).filter(x=>!known.has(x.id));store[key].push(...clone(fresh));added[key]=fresh.length;
    }
    store.socai2RecordedRuns||=[];const known=new Set(store.socai2RecordedRuns.map(x=>x.id)),fresh=list(data.runs).filter(x=>!known.has(x.id));store.socai2RecordedRuns.push(...clone(fresh));added.runs=fresh.length;
    store.socai2SourceArtifacts||=[];const sourceIds=new Set(store.socai2SourceArtifacts.map(x=>x.id));store.socai2SourceArtifacts.push(...clone(list(data.sourceArtifacts).filter(x=>!sourceIds.has(x.id))));
    store.socai2RecordedProvenance||=[];if(!store.socai2RecordedProvenance.some(x=>x.source_sha256===data.provenance.source_sha256))store.socai2RecordedProvenance.push(clone(data.provenance));
    return added;
  }
  return {adaptExport,merge,detectionView,runView,caseDescription};
});
