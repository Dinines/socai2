// Report navigation uses saved identities, never a supplied API URL or a round number.
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const KEYS=['subject_type','subject_id','run_id','environment'];

export function parseRunLink(search) {
  const query=new URLSearchParams(search);
  if(!query.size)return null;
  if(KEYS.some(key=>query.getAll(key).length!==1 || !query.get(key)) || [...query.keys()].some(key=>!KEYS.includes(key)))
    throw new Error('报告链接必须包含唯一的主体类型、主体ID、Run和环境');
  const mapping=Object.fromEntries(KEYS.slice(0,3).map(key=>[key,query.get(key)]));
  if(!['case','incident','alert'].includes(mapping.subject_type) || !UUID.test(mapping.subject_id) || !UUID.test(mapping.run_id))
    throw new Error('报告链接的主体类型或UUID无效');
  return {mapping,environment:query.get('environment')};
}

export function checkLinkEnvironment(target,capabilities) {
  if(target.environment!==capabilities.investigation_http?.environment_label)
    throw new Error('报告目标环境与当前工作台不一致，未读取指定执行');
}

export function chooseRun(history,runId) {
  if(!runId)return history[0]??null;
  const found=history.find(item=>item.run.id===runId);
  if(!found)throw new Error(`指定Run ${runId} 不在此主体的执行目录中；未改选最新轮次`);
  return found;
}

export function linkedSubject(target,subjects) {
  const mapping={subject_type:target.mapping.subject_type,subject_id:target.mapping.subject_id};
  return subjects.get(`${mapping.subject_type}:${mapping.subject_id}`)??{mapping,title:({case:'Case',incident:'事件',alert:'告警'})[mapping.subject_type]};
}

export function runLinkSearch(mapping,environment) {
  // Only the stable subject/Run keys belong in a browser link.
  const clean='?'+new URLSearchParams({subject_type:mapping.subject_type,subject_id:mapping.subject_id,run_id:mapping.run_id,environment});
  parseRunLink(clean);
  return clean;
}

export function checkRunIdentity(mapping,detail,directory) {
  if(detail.run?.id!==mapping.run_id || directory.run?.id!==mapping.run_id ||
     directory.run?.[`${mapping.subject_type}_id`]!==mapping.subject_id)
    throw new Error('读取的Run身份或主体归属与指定目标不一致；未显示其他执行');
}
