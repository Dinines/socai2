// Presentation of saved delivery records only; never recover an answer on GET.
export const DELIVERY_SCHEMA='socai2.stage-delivery.v1';
export function deliveryRecord(value,run,step) {
  if(value?.schema_version!==DELIVERY_SCHEMA || value.type!=='stage_delivery' ||
     value.run_id!==run.id || value.step_id!==step.id)
    throw new Error('交付回执与所选Run或步骤不一致');
  return value;
}
export function closingRecord(value,run) {
  if(value?.type!=='delivery_report' || value.run_id!==run.id || !value.result)
    throw new Error('收尾报告与所选Run不一致');
  return value;
}
export async function readClosingReport({run,steps,artifacts,readContent}) {
  const closing=steps.filter(s=>s.run_id===run.id && s.kind==='stage' && s.stage_code==='C6');
  if(!closing.length)return null;
  if(closing.length!==1)throw new Error('本轮收尾步骤不唯一');
  const step=closing[0];
  if(!step.output_artifact_id)return null;
  const refFor=id=>{
    const refs=artifacts.filter(a=>a.id===id && a.run_id===run.id && a.step_id===step.id);
    if(refs.length!==1)throw new Error('本轮收尾引用缺失或身份不一致');
    return refs[0];
  };
  const receipt=await readContent(refFor(step.output_artifact_id));
  if(receipt?.type!=='delivery_receipt' || receipt.run_id!==run.id || !receipt.detail_artifact_id)
    throw new Error('收尾回执与所选Run不一致');
  const detail=refFor(receipt.detail_artifact_id);
  if(detail.kind!=='source_snapshot')throw new Error('收尾报告原件类型不一致');
  return closingRecord(await readContent(detail),run);
}
export function localEndLabel(run,task,report) {
  if(run.state!=='unknown')return null;
  const attempt=task?.attempts?.find(a=>a.run_id===run.id);
  const ended=attempt?.local_state==='ended' ||
    (report?.run_id===run.id && report.execution?.local_state==='ended');
  return ended?'本地执行已结束，远端结果未知':'远端结果未知；本地结束情况未确认';
}
export function closingTitle(report, resultReadFailed=false) {
  if(resultReadFailed)return '报告中保留的分析（结果读取失败）';
  return report.result.conclusion_origin==='model'?
    '本轮保留分析（未形成可采用结果）':'本轮收尾（未形成可采用结果）';
}
