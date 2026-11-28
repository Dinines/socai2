/* Read saved Result fields without rewriting analysis or expanding its scope. */
'use strict';
(function(root,factory){
  const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;root.socai2Assessment=api;
})(typeof window==='object'?window:globalThis,()=>{
  const list=v=>Array.isArray(v)?v:[];
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const text=v=>`<p class="assessment-text">${esc(v??'未保存正文')}</p>`;
  const state=v=>esc(({observed:'观察',inferred:'推断',unresolved:'待核',withdrawn:'已撤回',open:'待回答',answered:'已回答',not_attempted:'未尝试'})[v]||v||'未记录状态');
  function values(rows,missing='未提供此字段',empty='未记录条目'){
    return !Array.isArray(rows)?text(missing):rows.length?`<ul>${rows.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:text(empty);
  }
  function refs(rows,title){
    return `<section class="assessment-references"><h5>${esc(title)}</h5>${!Array.isArray(rows)?text('未提供引用字段'):rows.length?`<ul>${rows.map(x=>`<li data-reference-role="${esc(x.role)}"><span>${esc(x.type)} · ${esc(x.id)}</span><div>来源角色：${esc(x.role??'未记录')}</div>${x.source_path!=null?`<div>字段路径：${esc(x.source_path)}</div>`:''}${list(x.row_keys).length?`<div>记录键：${list(x.row_keys).map(esc).join('、')}</div>`:''}</li>`).join('')}</ul>`:text('未保存引用')}</section>`;
  }
  function scope(value){
    if(!value||typeof value!=='object')return text('未提供原适用范围，不能按当前成员推断。');
    return `<details class="assessment-scope"><summary>原始适用范围</summary><p>范围类型：${esc(({whole_case:'当轮全案范围',selected_alerts:'指定告警',explicit_objects:'指定对象'})[value.kind]||value.kind||'未记录')}</p><h5>原告警范围</h5>${values(value.alert_ids,'未提供告警范围','未指定告警')}<h5>原对象范围</h5>${values(value.object_keys,'未提供对象范围','未指定对象键')}<p>时间窗：<span data-scope-start>${esc(value.window_start===null?'未限定':value.window_start??'未提供')}</span> — <span data-scope-end>${esc(value.window_end===null?'未限定':value.window_end??'未提供')}</span></p><h5>范围限制</h5>${values(value.limitations,'未提供范围限制','未记录范围限制')}</details>`;
  }
  function finding(x){
    return `<article class="assessment-item" data-finding-state="${esc(x.state)}"><h5>发现 · ${state(x.state)}</h5>${text(x.statement)}${scope(x.scope)}<details class="assessment-evidence"><summary>支持、反证与限制</summary>${refs(x.support,'支持引用')}${refs(x.counterevidence,'反证引用')}<h5>发现限制</h5>${values(x.limitations,'未提供发现限制','未记录发现限制')}</details></article>`;
  }
  function question(x){
    return `<article class="assessment-item" data-question-state="${esc(x.state)}"><h5>问题 · ${state(x.state)}</h5>${text(x.text)}${x.answer!=null?`<h5>保存的回答</h5>${text(x.answer)}`:x.state==='answered'?text('状态为已回答，但未保存回答正文。'):''}${scope(x.scope)}<details class="assessment-evidence"><summary>证据需求、引用与限制</summary><h5>证据需求</h5>${values(x.evidence_requirements,'未提供证据需求','未记录证据需求')}${refs(x.evidence_refs,'问题依据')}<h5>问题限制</h5>${values(x.limitations,'未提供问题限制','未记录问题限制')}</details></article>`;
  }
  function model(result){
    return {findings:list(result?.findings).filter(x=>x.state!=='unresolved'),pendingFindings:list(result?.findings).filter(x=>x.state==='unresolved'),
      questions:list(result?.questions).filter(x=>x.state!=='answered'),answered:list(result?.questions).filter(x=>x.state==='answered'),
      findingsAvailable:Array.isArray(result?.findings),questionsAvailable:Array.isArray(result?.questions),impact:result?.case_impact??null};
  }
  function render(result){
    const m=model(result),pending=[...m.pendingFindings.map(finding),...m.questions.map(question)].join('');
    const impact=m.impact?`<section class="assessment-impact"><h4>影响与适用边界</h4>${text(m.impact.summary)}<h5>已支持的变化</h5>${values(m.impact.supported_changes,'未提供变化字段','未记录已支持的变化')}<h5>不可推广的范围</h5>${values(m.impact.cannot_generalize,'未提供不可推广范围','未记录不可推广范围')}${scope(m.impact.affected_scope)}<h5>后续事项</h5>${values(m.impact.next_steps,'未提供后续事项','未记录后续事项')}</section>`:text('未提供案件影响字段。');
    return `<section class="saved-assessment" aria-label="结果依据与未决项"><h4>已保存发现与依据</h4><p class="assessment-note">状态和引用角色按原记录展示；推断、待核或已撤回不表示已证实。</p>${m.findings.map(finding).join('')||text(m.findingsAvailable?m.pendingFindings.length?'待核发现见下方未解决事项。':'结果未保存发现。':'结果未提供发现字段。')}<section class="assessment-unresolved"><h4>未解决事项</h4>${pending||text(m.findingsAvailable&&m.questionsAvailable?'结果未保存未解决事项。':'发现或问题字段未完整提供，不能据此判定没有未解决事项。')}${pending&&(!m.findingsAvailable||!m.questionsAvailable)?text('发现或问题字段未完整提供。'):''}</section>${m.answered.length?`<details class="assessment-answered"><summary>已回答问题（${m.answered.length}）</summary>${m.answered.map(question).join('')}</details>`:''}${impact}</section>`;
  }
  function coverage(members,truncated=false){
    return `<details class="assessment-adopted-scope"><summary>采用时覆盖的告警</summary>${values(Array.isArray(members)?members.map(x=>typeof x==='string'?x:x.alert_id):members,'未提供采用范围','未记录覆盖成员')}<p class="assessment-note">原采用范围保留，当前成员覆盖另行计算。</p>${truncated?text('采用覆盖目录已截断，以上仅为已读取部分。'):''}</details>`;
  }
  const sourceKey=x=>x.task_revision_id?'task_revision:'+x.task_revision_id:x.artifact_id?'artifact:'+x.artifact_id:'unknown';
  function sourcePath(caseId,source){
    if(source.case_id&&source.case_id!==caseId)throw Error('采用来源不属于所选Case。');
    if([source.result_id,source.task_revision_id,source.artifact_id].filter(Boolean).length!==1)throw Error('采用来源类型不明确。');
    const base='/cases/'+encodeURIComponent(caseId),enc=encodeURIComponent;
    if(source.task_revision_id){
      if(!source.task_id)throw Error('来源未提供任务ID，无法读取指定人工版本。');
      return `${base}/tasks/${enc(source.task_id)}/revisions/${enc(source.task_revision_id)}`;
    }
    if(source.artifact_id){
      if(source.run_id===undefined)throw Error('来源未提供工件所属轮次，无法确定正文入口。');
      if(source.run_id!==null&&(typeof source.run_id!=='string'||!source.run_id))throw Error('工件所属轮次无效。');
      return `${base}${source.run_id?'/runs/'+enc(source.run_id):''}/artifacts/${enc(source.artifact_id)}`;
    }
    throw Error('此读取入口不适用于结果来源。');
  }
  function checkSource(data,{caseId,source}){
    sourcePath(caseId,source);
    if(source.task_revision_id){
      if(data?.id!==source.task_revision_id||data.task_id!==source.task_id||data.case_id!==caseId)throw Error('人工版本与采用来源不一致。');
    }else if(data?.artifact?.id!==source.artifact_id||data.artifact.case_id!==caseId||data.artifact.run_id!==source.run_id||typeof data.availability!=='string')throw Error('工件与采用来源或所属轮次不一致。');
    return data;
  }
  function sourceBody(source,data){
    if(source.task_revision_id){
      const status=({not_started:'未开始',in_progress:'进行中',completed:'已完成',cancelled:'已取消'})[data.state]||data.state||'未提供';
      return `<div class="assessment-human-source"><h5>${esc(data.title??'未提供标题')}</h5><p>保存版本：${esc(data.revision??'未提供')} · 状态：${esc(status)}</p><p class="assessment-note">来源角色：人工陈述；正文和范围属于此保存版本。</p><h5>事项说明</h5>${text(data.description??'未保存说明')}<h5>保存的人工反馈</h5>${text(data.result_text===undefined?'未提供反馈字段':data.result_text===null?'未保存反馈正文':data.result_text===''?'已保存空反馈正文':data.result_text)}${scope(data.result_scope)}${refs(data.source_refs,'人工版本的来源引用')}<details><summary>版本记录</summary><p>任务：${esc(data.task_id)} · 版本：${esc(data.id)}</p><p>负责人：${esc(data.assignee_id??'未指定')} · 截止：${esc(data.due_at??'未设置')}</p><p>完成时间：${esc(data.completed_at??'未记录')} · 完成人：${esc(data.completed_by??'未记录')}</p><p>保存时间：${esc(data.changed_at??'未提供')} · 保存人：${esc(data.changed_by??'未提供')}</p></details></div>`;
    }
    const meta=data.artifact,readable=data.availability==='available'||data.availability==='exported_content'||data.availability.startsWith('retained_');
    const json=data.content_json!==null&&data.content_json!==undefined,plain=data.content_text!==null&&data.content_text!==undefined;
    const body=readable?(json?`<pre class="assessment-artifact-body">${esc(JSON.stringify(data.content_json,null,2))}</pre>`:'')+(plain?data.content_text===''?text('已保存空文本正文。'):`<pre class="assessment-artifact-body">${esc(data.content_text)}</pre>`:'')||text('响应未提供工件正文，不能视为已读取空内容。'):text(({external_content_not_loaded:'原件为外部存储，本次未加载正文。',content_exceeds_read_limit_or_size_unknown:'正文大小未知或受到读取限制，本次未读取。',unavailable:'工件正文不可用。'})[data.availability]||'未识别的正文可用状态，本次未展示正文。');
    return `<div class="assessment-artifact-source"><p>工件类型：${esc(meta.kind??'未提供')} · 正文状态：${esc(data.availability)}</p><p>所属轮次：${esc(meta.run_id??'Case级工件')}</p><p class="assessment-note">以下是该工件保存的原始正文；其类型不因被引用而变为Result。</p>${body}<details><summary>工件元数据</summary><pre class="assessment-artifact-body">${esc(JSON.stringify(meta,null,2))}</pre></details></div>`;
  }
  function otherSources(sources,contents=[]){
    const rows=list(sources).filter(x=>!x.result_id);
    return rows.length?`<section class="assessment-other-sources"><h4>人工版本与工件来源</h4>${rows.map(x=>{
      const loaded=list(contents).find(c=>sourceKey(c.source)===sourceKey(x));
      return `<article class="assessment-source" data-source-kind="${x.task_revision_id?'task_revision':x.artifact_id?'artifact':'unknown'}" data-source-id="${esc(x.task_revision_id||x.artifact_id||'')}"><p>${x.task_revision_id?'人工版本 · '+esc(x.task_revision_id):x.artifact_id?'工件 · '+esc(x.artifact_id):'未识别的来源类型'}</p>${x.source_note!=null?text(x.source_note):''}${loaded?.error?`<p role="alert">来源读取失败：${esc(loaded.error)}</p>`:loaded?.data?sourceBody(x,loaded.data):text('尚未读取此来源正文，不能据此认定没有依据或未决项。')}</article>`;
    }).join('')}</section>`:'';
  }
  const verdictLabels=new Map([['malicious','恶意'],['benign','正常'],['false_positive','误报'],['needs_review','待复核']]);
  const verdictLabel=value=>verdictLabels.get(value)??'未记录';
  function verdict(value){
    return `<p class="assessment-note">模型判定 <strong data-business-verdict>${verdictLabel(value)}</strong></p>`;
  }
  return {model,render,scope,coverage,otherSources,sourcePath,checkSource,sourceKey,verdict,verdictLabel};
});
