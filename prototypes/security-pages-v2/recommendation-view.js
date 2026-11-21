/* Read-only presentation of saved recommendations. Never infers approval or execution. */
'use strict';
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.socai2Recommendations=api;
})(typeof window==='object'?window:globalThis,()=>{
  const list=v=>Array.isArray(v)?v:[];
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const present=v=>typeof v==='string'&&v.trim().length>0;
  function model(value){
    const x=value&&typeof value==='object'?value:{};
    const native=Object.hasOwn(x,'reason')||Object.hasOwn(x,'approval_requirement');
    const body=typeof value==='string'?value:native?x.reason:x.description;
    const approval=native?x.approval_requirement:x.requires_approval===true?'required':x.requires_approval===false?'not_required':'unknown';
    return {body:present(body)?body:null,actionType:x.action_type??null,
      targets:Array.isArray(x.targets)?x.targets.map(t=>({name:t?.display_name??null,key:t?.object_key??null})):present(x.target)?[{name:x.target,key:null}]:[],
      approval:['required','not_required'].includes(approval)?approval:'unknown',
      rationale:!native&&present(x.rationale)&&x.rationale!==body?x.rationale:null,
      sources:list(x.source_refs),limitations:list(x.limitations)};
  }
  function content(value,index=0){
    const m=model(value),approvals={required:'需要审批',not_required:'无需审批',unknown:'审批要求未知'};
    const targets=m.targets.map(t=>`<li>${esc(t.name||t.key||'未记录目标名称')}${t.key&&t.key!==t.name?` <span class="recommendation-key">${esc(t.key)}</span>`:''}</li>`).join('');
    const sources=m.sources.map(s=>`<li><span>${esc(s.type||'未记录类型')} · ${esc(s.id||'未记录标识')}</span>${s.role?`<div>来源角色：${esc(s.role)}</div>`:''}${s.source_path?`<div>字段路径：${esc(s.source_path)}</div>`:''}${list(s.row_keys).length?`<div>记录键：${list(s.row_keys).map(esc).join('、')}</div>`:''}</li>`).join('');
    return `<div class="recommendation-heading"><strong>建议 ${index+1}</strong>${m.actionType?`<span>动作类别：${esc(m.actionType)}</span>`:''}</div><p class="recommendation-body">${esc(m.body??'未记录建议正文')}</p><div class="recommendation-targets"><strong>目标</strong>${targets?`<ul>${targets}</ul>`:'<p>未记录目标</p>'}</div><p class="recommendation-approval" data-approval="${m.approval}">${approvals[m.approval]}</p><details class="recommendation-basis"><summary>建议依据与限制</summary>${m.rationale?`<p class="recommendation-body">${esc(m.rationale)}</p>`:''}<h4>来源引用</h4>${sources?`<ul>${sources}</ul>`:'<p>未记录来源引用</p>'}<h4>限制</h4>${m.limitations.length?`<ul>${m.limitations.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p>未记录限制</p>'}</details>`;
  }
  function render(values){
    const rows=list(values);
    return `<section class="saved-recommendations" aria-label="已保存建议"><p class="recommendation-note">建议及审批要求不代表已审批或已执行。</p>${rows.length?rows.map((x,i)=>`<article class="saved-recommendation" data-recommendation-index="${i}">${content(x,i)}</article>`).join(''):`<p class="recommendation-empty">${values==null?'本结果未提供建议字段。':'本结果未保存建议。'}</p>`}</section>`;
  }
  function checkResult(detail,{caseId,resultId,runId}){
    const x=detail?.result,r=detail?.run;
    if(!x||x.id!==resultId||x.case_id!==caseId||!x.source_run_id||(runId&&x.source_run_id!==runId)||!r||r.id!==x.source_run_id||r.case_id!==caseId)
      throw Error('建议来源结果与所选主体或轮次不一致。');
    return x;
  }
  function resultSources(assessment){
    const ids=new Set();
    return list(assessment?.sources).filter(x=>x.result_id&&!ids.has(x.result_id)&&ids.add(x.result_id));
  }
  return {model,content,render,checkResult,resultSources};
});
