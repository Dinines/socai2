const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
function setup(){
 const sandbox={window:{},document:{addEventListener(){}},location:{hash:''},structuredClone};
 vm.createContext(sandbox);
 vm.runInContext(fs.readFileSync(path.join(root,'data.js'),'utf8'),sandbox);
 const old=sandbox.window.makeDemoData();
 vm.runInContext(fs.readFileSync(path.join(root,'replayed-alerts.js'),'utf8'),sandbox);
 const store=sandbox.window.makeDemoData();
 vm.runInContext(fs.readFileSync(path.join(root,'alert-detail.js'),'utf8'),sandbox);
 const esc=v=>String(v??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
 const render=sandbox.window.createAlertDetail({store,esc,date:v=>v,I:()=>'',btn:t=>t,badge:esc,severity:esc,state:esc,entityChip:e=>esc(e?.name),getAsset:id=>store.assets.find(a=>a.id===id),save(){},render(){},navigate(){},toast(){},breadcrumbs:()=>'',tabsMarkup:()=>''});
 return {sandbox,store,old,render};
}
test('six actual records are additive and merging preserves fixture/local changes',()=>{
 const {sandbox,store,old}=setup();
 assert.equal(store.alerts.length,58);assert.equal(store.incidents.length,old.incidents.length);assert.equal(store.cases.length,old.cases.length);
 for(const key of ['alerts','assets','incidents','cases'])for(const a of old[key])assert.deepEqual(store[key].find(x=>x.id===a.id),a);
 store.alerts[0].title='local edit';sandbox.window.mergeReplayedAlerts(store);
 assert.equal(store.alerts.length,58);assert.equal(store.alerts[0].title,'local edit');
});
test('actual detail tabs render recorded fields without fabricated evidence or cases',()=>{
 const {sandbox,store,render}=setup();
 const actual=store.alerts.filter(a=>a.persistedRecord);
 assert.equal(actual.filter(a=>a.status==='In progress').length,5);assert.equal(actual.filter(a=>a.status==='Resolved').length,1);
 for(const a of actual){
  assert.ok(a.incidentId);assert.equal(a.caseId,null);assert.equal(a.owner,'未分配');
  const before=JSON.stringify(a.detailMaterial.history);
  for(const tab of ['overview','timeline','raw','response']){
   sandbox.location.hash=`#/alerts/${a.id}/${tab}`;
   const html=render(a);
   assert.ok(html.includes(a.title));assert.ok(html.includes(a.incidentId));assert.ok(!html.includes('尚未关联事件'));
   if(tab==='overview'){
    assert.ok(html.includes('建议动作'));assert.ok(html.includes('stingAISOC Production'));
    assert.ok(!html.includes('待核实事项'));assert.ok(!html.includes('Contoso'));
   }
   if(tab==='response')assert.ok(html.includes(a.status==='Resolved'?'未升级调查':'部分完成'));
  }
  assert.equal(JSON.stringify(a.detailMaterial.history),before);
 }
 const first=actual.find(a=>a.id==='4c71eec2-77da-5b81-b68a-72801d55ea24');
 assert.equal(first.detailMaterial.risk,85);assert.equal(first.detailMaterial.confidence.score,80);
 assert.ok(first.detailMaterial.runs[0].tools.some(t=>t.result.includes('LakeQueryError')));
});
