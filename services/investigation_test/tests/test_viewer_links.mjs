import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseRunLink,checkLinkEnvironment,chooseRun,runLinkSearch,checkRunIdentity,linkedSubject} from '../web/viewer_links.mjs';

const report=JSON.parse(readFileSync(new URL('../../../docs/operations/evidence/workbench-deeplink-20261117-01/report-01/report.json',import.meta.url)));
const caps={investigation_http:{environment_label:report.workbench.workbench_environment_label}};
const caseSubject=report.subjects.find(s=>s.kind==='case');
const first=parseRunLink(new URL(caseSubject.rounds[0].viewer_url).search);

test('six saved report links choose the exact subject and Run, including both Case rounds',()=>{
  let count=0;
  for(const subject of report.subjects)for(const run of subject.rounds){
    const target=parseRunLink(new URL(run.viewer_url).search);
    checkLinkEnvironment(target,caps);
    const history=subject.rounds.toReversed().map(r=>({run:{id:r.run_id}}));
    assert.equal(chooseRun(history,target.mapping.run_id).run.id,run.run_id);
    assert.equal(target.mapping.subject_id,subject.id);
    assert.deepEqual(parseRunLink(runLinkSearch({...target.mapping,task_id:'not-a-link-field'},target.environment)),target);
    count++;
  }
  assert.equal(count,6);
});
test('missing Run and foreign subject Run do not fall back to the latest round',()=>{
  const history=caseSubject.rounds.toReversed().map(r=>({run:{id:r.run_id}}));
  assert.throws(()=>chooseRun(history,'00000000-0000-0000-0000-000000000099'),/未改选最新/);
  const incident=report.subjects.find(s=>s.kind==='incident');
  assert.throws(()=>chooseRun(history,incident.rounds[0].run_id),/未改选最新/);
  assert.equal(chooseRun(history,null).run.id,caseSubject.rounds[1].run_id);
});
test('direct target resolution works outside the first subject list page',()=>{
  const group=linkedSubject(first,new Map());
  assert.deepEqual(group.mapping,{subject_type:'case',subject_id:caseSubject.id});
  assert.equal(group.subject,undefined);
});
test('invalid links and mismatched environments have no default target',()=>{
  assert.equal(parseRunLink(''),null);
  const search=new URL(caseSubject.rounds[0].viewer_url).search;
  for(const broken of ['?subject_type=case',search+'&run_id='+first.mapping.run_id,search.replace('subject_type=case','subject_type=other'),search.replace(first.mapping.subject_id,'not-uuid')])
    assert.throws(()=>parseRunLink(broken));
  assert.throws(()=>checkLinkEnvironment({...first,environment:'wrong'},caps),/环境/);
});
test('returned Run and parent identities must match before displaying data',()=>{
  const run={id:first.mapping.run_id,case_id:first.mapping.subject_id};
  checkRunIdentity(first.mapping,{run},{run});
  assert.throws(()=>checkRunIdentity(first.mapping,{run:{...run,id:caseSubject.rounds[1].run_id}},{run}),/身份/);
  assert.throws(()=>checkRunIdentity(first.mapping,{run},{run:{...run,case_id:'other'}}),/归属/);
});
