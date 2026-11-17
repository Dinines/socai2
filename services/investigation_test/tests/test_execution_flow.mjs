import test from 'node:test';
import assert from 'node:assert/strict';
import {executionTree, originalChoices, stepReferences, requestBody, matchingExchange, matchingAttempt, domainLabel, stepReason} from '../web/execution_flow.mjs';

test('flow preserves actual order, child links, orphan steps and retries in this Run only',()=>{
  const steps=[{id:'child',run_id:'r',seq:3,parent_step_id:'parent',retry_of_step_id:'earlier'},
    {id:'foreign',run_id:'other',seq:1},{id:'parent',run_id:'r',seq:2},
    {id:'orphan',run_id:'r',seq:4,parent_step_id:'unavailable'}];
  const tree=executionTree(steps,'r');
  assert.deepEqual(tree.map(x=>x.step.id),['parent','orphan']);
  assert.equal(tree[0].children[0].step.id,'child');
  assert.equal(tree[0].children[0].step.retry_of_step_id,'earlier');
});
test('original reply cannot be replaced by the parsed or merged model output',()=>{
  assert.equal(originalChoices({payload:{answer:'derived'},choices:[{message:{content:'also derived'}}]}),null);
  const choices=[{finish_reason:'length',message:{content:'unfinished original'}}];
  assert.equal(originalChoices({raw:{choices}}),choices);
  assert.equal(originalChoices({payload:{raw:{choices}}}),choices);
});
test('cross-Run artifact references keep their actual identity and returned URL',()=>{
  const ref={role:'input',run_id:'source',subject_id:'incident',artifact_id:'a',content_url:'/returned-source'};
  assert.equal(stepReferences({run_id:'case',artifact_refs:[ref]},[],'input')[0],ref);
  assert.deepEqual(stepReferences({run_id:'case',input_artifact_id:'a'},[{id:'a',run_id:'other',content_url:'/wrong'}],'input'),[]);
});
test('prompt view reads the saved request envelope without discarding zero or false',()=>{
  const body={messages:[{role:'user',content:'original'}],temperature:0,stream:false};
  assert.equal(requestBody({payload:{body}}),body);
  assert.equal(requestBody({payload:{body}}).stream,false);
});
test('changing round cannot reuse another task HTTP receipt or attempt',()=>{
  const first={subject_type:'case',subject_id:'c',run_id:'r1',task_id:'t1',response:{status:201}};
  assert.equal(matchingExchange([first],{subject_type:'case',subject_id:'c'},'r1','t1'),first);
  assert.equal(matchingExchange([first],{subject_type:'case',subject_id:'c'},'r2','t2'),null);
  assert.equal(matchingExchange([first],{subject_type:'case',subject_id:'other'},'r1','t1'),null);
  assert.equal(matchingAttempt({attempts:[{run_id:'r1',attempt_no:1}]},'r2'),null);
});
test('domain labels keep actual applicability and skipped reasons remain distinct',()=>{
  assert.equal(domainLabel({domain:'identity',applicability:'undetermined'}),'身份 · 适用性待定');
  assert.equal(domainLabel({domain:'phishing',applicability:'not_applicable'}),'钓鱼 · 不适用');
  assert.equal(domainLabel({domain:'new-domain',applicability:'new-state'}),'new-domain · new-state');
  assert.equal(stepReason({error:{code:'source_not_connected'}}),'数据源未接入');
  assert.equal(stepReason({error:{code:'tool_budget_reserved_for_evidence'}}),'工具额度预留给证据补查');
});
