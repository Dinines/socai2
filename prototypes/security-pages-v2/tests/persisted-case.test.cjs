const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
function load(){
 const s={window:{addEventListener(){}},document:{addEventListener(){}},location:{hash:'#/cases'},localStorage:{getItem:()=>null},structuredClone,URLSearchParams,clearInterval};vm.createContext(s);
 for(const file of ['icons','data','replayed-alerts','alert-detail','workspace-model','workspace-view','investigation-data','alert-flow-workspace','aisoc20-data','persisted-case-data','recorded-examples','investigation-graph','investigation-workspace'])vm.runInContext(fs.readFileSync(path.join(root,file+'.js'),'utf8'),s);
 const code=fs.readFileSync(path.join(root,'app.js'),'utf8').replace('readQueueLink();render();\n})();','window.api={store,ui,casePage,fullAlert,investigationView,filteredRows,caseQueueRows,tableState};\n})();');
 vm.runInContext(code,s);return {...s.window.api,s,data:s.window.persistedCaseData};
}
test('actual Case retains its identity and one joint Run without changing the earlier no-Case sources',()=>{
 const x=load(),d=x.data,c=d.cases[0],r=d.runs[0];assert.equal(x.store.alerts.length,67);assert.equal(x.store.cases.length,16);assert.equal(x.s.window.investigationWorkspaceModel.runs(x.store).length,15);
 assert.equal(c.id,'82b1246f-9f34-463c-8c2d-27d2b075c741');assert.equal(r.id,'e998308a-a353-4647-99f6-10f94ced0ecf');assert.equal(r.sourceCaseId,c.id);assert.notEqual(r.agentRunId,r.id);
 assert.deepEqual([...r.alertIds].sort(),[...c.alertIds].sort());assert.equal(c.status,'New');assert.equal(r.status,'completed');assert.equal(r.completion,null);assert.equal(r.verdict,null);
 for(const a of d.alerts){assert.equal(a.caseId,c.id);assert.equal(a.status,'Unknown');assert.equal(a.detailMaterial.runs.length,0);assert.equal(a.detailMaterial.confidence.score,null);}
 for(const a of x.s.window.aisoc20RecordedData.alerts)assert.equal(a.caseId,null);
 const saved=x.store.cases.find(row=>row.id===c.id);saved.title='本地编辑';saved.alertIds.pop();const before=JSON.stringify(x.store);x.s.window.mergePersistedCaseData(x.store);assert.equal(JSON.stringify(x.store),before);
});
test('saved graph scope, stage adoption and report preserve the historical receipt',()=>{
 const x=load(),r=x.data.runs[0],g=r.graphs;
 assert.equal(g.attack_chain.data.chain.length,5);assert.equal(g.attack_chain.data.chain.filter(a=>r.alertIds.includes(a.alert_id)).length,2);
 assert.equal(g.attack_path.data.nodes.length,11);assert.equal(g.attack_path.data.edges.length,15);assert.equal(g.alert_graph.data.blast_radius.total_affected,16);
 assert.equal(r.steps.length,29);assert.equal(r.tools.length,7);assert.equal(r.tools.filter(t=>t.success===false).length,1);assert.equal(r.calls,4);assert.equal(r.tokens,18388);
 assert.equal(r.steps.filter(s=>s.adopted).length,3);assert.equal(r.steps.find(s=>s.kind==='forensic').adopted.timeline.length,3);assert.equal(r.steps.find(s=>s.kind==='responder').adopted.dry_run,true);assert.equal(r.actions.length,3);assert.equal(r.executed.length,0);
 assert.equal(crypto.createHash('sha256').update(r.report).digest('hex'),r.artifacts.find(a=>a.kind==='report_md').sha256);
 const blocked=new Set(['messages','prompt','prompt_block','response','reasoning_content','api_key','authorization','password','access_token']);
 function inspect(v){if(!v||typeof v!=='object')return;for(const [k,value]of Object.entries(v)){assert.ok(!blocked.has(k.toLowerCase()),k);inspect(value);}}inspect(x.data);
});
test('all Case and alert detail views render with truthful missing values and no mutation',()=>{
 const x=load(),r=x.data.runs[0],c=x.data.cases[0],before=JSON.stringify(x.store);
 for(const view of ['overview','process','tools','graphs','ledger','report']){
  x.s.location.hash=`#/cases/${c.id}/investigations?run=${r.id}&view=${view}`;const html=x.casePage();assert.ok(!/Invalid Date|undefined|>null</.test(html),view);assert.ok(html.includes('已创建的历史 Case'));assert.ok(html.includes('完整性未记录'));
  if(view==='overview'){assert.ok(html.includes('取证分析置信度 10%'));assert.ok(html.includes('8 小时差异'));assert.ok(html.includes('判定未记录'));}
  if(view==='process')for(const text of ['侦察分析','取证分析','响应分析','报告整理','查看阶段采用结果','dry_run'])assert.ok(html.includes(text));
  if(view==='tools'){assert.ok(html.includes('查询失败'));assert.ok(!html.includes('最多200字符'));}
 }
 for(const tab of ['overview','case-info','alerts','assets','attack','evidence','tasks','activities','comments','similar','investigations']){
  x.s.location.hash=`#/cases/${c.id}/${tab}`;const html=x.casePage();assert.ok(!/Invalid Date|undefined|>null</.test(html),tab);assert.ok(!html.includes('源系统未建 Case'));if(tab==='comments'){assert.ok(html.includes('附件 (0)'));assert.ok(!html.includes('investigation-notes.txt'));}
 }
 for(const a of x.data.alerts)for(const tab of ['overview','timeline','raw','response']){
  x.s.location.hash=`#/alerts/${a.id}/${tab}`;const html=x.fullAlert(x.store.alerts.find(row=>row.id===a.id));assert.ok(!/Invalid Date|undefined|>null</.test(html),tab);if(tab==='response'){assert.ok(html.includes('查看 Case 联合调查'));assert.ok(!html.includes('自动处理过程'));}
 }
 assert.equal(JSON.stringify(x.store),before);
});
test('graph filters preserve external candidates and frozen Run path when current membership changes',()=>{
 const x=load(),r=x.data.runs[0],c=x.store.cases.find(row=>row.id===r.sourceCaseId);
 for(const kind of ['all','attack_chain','attack_path','alert_graph']){
  x.s.location.hash=`#/cases/${c.id}/investigations?run=${r.id}&view=graphs&graph=${kind}`;const html=x.casePage();assert.ok(!html.includes('本次未保存此类材料'));
  if(['all','attack_chain'].includes(kind)){assert.equal((html.match(/历史外部候选/g)||[]).length,3);assert.ok(html.includes('候选评分'));assert.ok(html.includes('图距离'));}
  if(['all','attack_path'].includes(kind)){assert.ok(html.includes('11 个对象 · 15 条已记录关系'));assert.ok(html.includes('本次 Case 联合调查保存的路径图'));}
  if(['all','alert_graph'].includes(kind)){assert.ok(html.includes('图可达实体'));assert.ok(html.includes('<strong>16</strong>'));}
 }
 c.alertIds.splice(0);assert.equal(x.s.window.investigationWorkspaceModel.forCase(x.store,c).length,1);x.s.location.hash=`#/cases/${c.id}/attack`;const html=x.casePage();assert.ok(html.includes('当时的 3 条输入'));assert.ok(html.includes('11 个对象'));assert.equal(r.alertIds.length,3);
 x.s.location.hash=`#/cases/${c.id}/overview`;assert.ok(x.casePage().includes('取证分析置信度 10%'));
 x.s.location.hash=`#/cases/${c.id}/investigations`;assert.ok(x.casePage().includes('打开调查'));
});
