/* Case-only exploration overlay. Sources and historical Run graphs are immutable. */
'use strict';
window.caseExplorationModel=(()=>{
  const clone=x=>structuredClone(x),supported=n=>!!n&&!['tech','technique','tactic','case'].includes(String(n.kind).toLowerCase())&&!n.group;
  function assetsFor(store,c,eligible){const ids=new Set(store.alerts.filter(a=>eligible(c,a)).flatMap(a=>a.entityIds||[]));return store.assets.filter(a=>ids.has(a.id));}
  function objectFor(n,assets){if(!supported(n)||n.kind==='alert')return null;const exact=assets.find(a=>a.id===n.id);if(exact)return exact;const found=assets.filter(a=>a.name===n.label&&(a.type===n.kind||n.kind==='endpoint'&&['ip','device'].includes(a.type)));return found.length===1?found[0]:null;}
  function candidates(store,c,g,pivot,eligible){
    const assets=assetsFor(store,c,eligible),nodes=pivot?g.nodes.filter(n=>n.id===pivot):g.nodes,keys=new Set();let stamp=Date.parse(g.anchorTime);
    for(const n of nodes){if(!supported(n))continue;if(n.kind==='alert'){const a=store.alerts.find(a=>a.id===n.id&&eligible(c,a));for(const id of a?.entityIds||[])keys.add(id);if(pivot)stamp=Date.parse(a?.event_time||a?.first);}else{const a=objectFor(n,assets);if(a)keys.add(a.id);}}
    if(!Number.isFinite(stamp))return [];
    return store.alerts.filter(a=>eligible(c,a)&&!g.inputs.includes(a.id)&&a.id!==pivot).map(a=>{
      const shared=(a.entityIds||[]).filter(id=>keys.has(id)),dt=Math.abs(Date.parse(a.event_time||a.first)-stamp);
      return {alertId:a.id,title:a.title,time:a.event_time||a.first,shared,dt,score:Math.min(100,shared.length*30+Math.max(0,40-Math.floor(dt/60000))),already:g.nodes.some(n=>n.id===a.id)};
    }).filter(x=>x.shared.length&&Number.isFinite(x.dt)&&x.dt<=86400000).sort((a,b)=>Number(a.already)-Number(b.already)||b.score-a.score||a.dt-b.dt||a.alertId.localeCompare(b.alertId));
  }
  function branch(store,c,g,row,pivot,eligible){
    const a=store.alerts.find(a=>a.id===row.alertId&&eligible(c,a));if(!a)throw Error('当前没有可展开的完整告警记录。');
    const assets=assetsFor(store,c,eligible),nodes=[{id:a.id,kind:'alert',label:a.title,time:a.event_time||a.first,severity:a.severity,status:a.status,input:false}],edges=[];
    for(const id of a.entityIds||[]){const asset=assets.find(x=>x.id===id);if(!asset)continue;const matches=g.nodes.filter(n=>objectFor(n,assets)?.id===id),node=matches.length===1?matches[0]:{id:asset.id,kind:asset.type,label:asset.name};nodes.push(clone(node));edges.push({id:'explore:'+a.id+':'+node.id,from:a.id,to:node.id,layer:'exploration',sources:[{material:'告警对象记录',source:a.id,type:'INVOLVES',time:a.event_time||a.first,direction:'unknown'}]});}
    return {pivot:pivot||null,alertId:a.id,shared:row.shared.slice(),score:row.score,dt:row.dt,nodes,edges};
  }
  function project(base,branches,picked=[],preview=null){const g=clone(base);for(const b of [...branches,...(preview?[preview]:[])]){
    for(const n of b.nodes)if(!g.nodes.some(x=>x.id===n.id))g.nodes.push({...clone(n),explored:true,preview:b===preview});
    for(const e of b.edges)if(!g.edges.some(x=>(x.from===e.from&&x.to===e.to)||(x.to===e.from&&x.from===e.to)))g.edges.push({...clone(e),preview:b===preview});
  }let code=0;for(const n of g.nodes){if(n.kind==='alert'&&!n.input)n.code='E'+(++code);n.picked=picked.includes(n.id);}g.related=g.nodes.filter(n=>n.kind==='alert'&&!n.input).map(n=>n.id);return g;}
  return {supported,objectFor,assetsFor,candidates,branch,project};
})();
window.createCaseExploration=function(ctx){
  const M=window.caseExplorationModel,sessions=new Map(),{esc,store}=ctx;let current=null;
  const button=(a,text,id='',extra='')=>`<button class="button small" data-action="cx-${a}" data-id="${esc(id)}" ${extra}>${text}</button>`;
  const fixed=s=>!!s&&(!!s.savedAt||s.branches.length>0||s.picked.length>0||!!s.preview);
  function begin(c,base,run){
    const freshBase={...structuredClone(base),anchorTime:run.ended||run.started||base.nodes.map(n=>n.time).filter(x=>Number.isFinite(Date.parse(x))).sort().at(-1)||null};
    let s=sessions.get(c.id);if(s&&!fixed(s)){s.base=freshBase;s.baseRunId=run.virtual?null:run.id;if(s.pivot&&!base.nodes.some(n=>n.id===s.pivot))s.pivot=undefined;}if(!s){const saved=c.graphExploration;s=saved?{...structuredClone(saved),preview:null,pivot:undefined,limit:5,dirty:false}:{base:freshBase,baseRunId:run.virtual?null:run.id,branches:[],picked:[],preview:null,pivot:undefined,limit:5,dirty:false};sessions.set(c.id,s);}
    const g=M.project(s.base,s.branches,s.picked,s.preview);g.key='case-exploration:'+c.id+':'+s.base.key;g.explorable=true;current={c,s,g,latestBase:base,run};return g;
  }
  function toolbar(){if(!current)return '';const {s,g,c}=current,selectedAlerts=s.picked.filter(id=>g.nodes.some(n=>n.id===id&&n.kind==='alert')&&!c.alertIds.includes(id));return `<div class="cx-toolbar"><div><strong>探索关联线索</strong><small>展开仅改变画布；确认相关告警后加入本案，更新基础调查范围。</small></div><div class="cx-toolbar-actions">${button('recommend','推荐线索')}${button('undo','撤销展开','',s.branches.length?'':'disabled')}${button('reset','重置探索')}${button('save','保存探索进度')}${button('ask-picked','询问所选对象','',s.picked.length?'':'disabled')}${button('adopt','加入本案 · '+selectedAlerts.length,'',selectedAlerts.length?'':'disabled')}</div><div class="cx-legend"><span><i></i>新增展开</span><span>✓ 已选中</span><span>${s.branches.length} 次展开${s.dirty?' · 未保存':s.savedAt?' · 已保存':''}</span>${s.baseRunId&&s.baseRunId!==current.run.id?'<span>已保留保存时的底图；重置后使用最新调查</span>':''}</div></div>`;}
  const eligible=(c,a)=>ctx.caseActions().eligible(c,a);
  function detail(g,selection,renderDetails){
    if(!current||!g.explorable)return '';
    const {s,c}=current,n=g.nodes.find(n=>n.id===selection.selected),leads=s.panel==='leads';
    const nav=`<nav class="cx-side-tabs" aria-label="案件图侧栏视图">${button('panel','对象详情','details',`aria-pressed="${!leads}"`)}${button('panel','关联线索','leads',`aria-pressed="${leads}"`)}</nav>`;
    if(!leads){
      const actions=n&&M.supported(n)?`<div class="cx-node-actions">${button('ask','询问此对象',n.id,n.preview?'disabled':'')}${button('expand','以此节点扩展',n.id,n.preview?'disabled':'')}${button('pick',s.picked.includes(n.id)?'✓ 已选中':'选择对象',n.id,n.preview?'disabled':'')}</div>`:'';
      const content=n||g.edges.some(e=>e.id===selection.selected)?renderDetails():`<div class="cx-select-guide"><h4>选择一个对象</h4><p>点击图中的告警或实体查看详情，也可以查看推荐线索。</p>${button('recommend','查看推荐线索')}</div>`;
      return nav+`<div class="ug-detail-content cx-object-view" aria-live="polite">${actions}${content}</div>`;
    }
    const rows=M.candidates(store,c,M.project(s.base,s.branches),s.pivot,eligible),pivot=s.pivot?g.nodes.find(n=>n.id===s.pivot)?.label:'当前画布',assets=M.assetsFor(store,c,eligible);
    const anchor=(s.pivot&&store.alerts.find(a=>a.id===s.pivot)?.event_time)||s.base.anchorTime,stamp=Number.isFinite(Date.parse(anchor))?ctx.format(anchor):'未提供';
    const objectName=id=>esc(assets.find(a=>a.id===id)?.name||id);
    const cards=rows.slice(0,s.limit).map(r=>`<article class="cx-candidate ${s.preview?.alertId===r.alertId?'previewing':''}"><a class="cx-candidate-title" href="#/alerts/${encodeURIComponent(r.alertId)}/overview">${esc(r.title)}</a><div class="cx-candidate-meta"><span class="cx-membership">${c.alertIds.includes(r.alertId)?'本案成员':'未加入本案'}</span><span>时间差 ${Math.round(r.dt/60000)} 分钟</span></div><div class="cx-shared"><span>共享对象</span><ul>${r.shared.slice(0,2).map(id=>`<li>${objectName(id)}</li>`).join('')}</ul></div><details class="cx-candidate-basis"><summary>${r.shared.length>2?`还有 ${r.shared.length-2} 个对象 · `:''}查看依据</summary><p>关联分数 ${r.score} · 仅用于排序</p><ul>${r.shared.map(id=>`<li>${objectName(id)}</li>`).join('')}</ul></details><div class="cx-candidate-actions">${r.already?button('focus','已在图中 · 定位',r.alertId):button('preview',s.preview?.alertId===r.alertId?'取消预览':'预览',r.alertId)+button('add','展开到图中',r.alertId,'data-cx-primary')}</div></article>`).join('');
    return nav+`<div class="ug-detail-content cx-leads-view" aria-live="polite"><div class="cx-leads-heading"><h4>${s.pivot?'扩展线索':'推荐线索'} <span>${rows.length}</span></h4><details class="cx-rules"><summary aria-label="查看线索规则">ⓘ</summary><div class="cx-rules-popup"><strong>线索规则</strong><p>查找起点前后24小时内共享对象的告警，按共享对象和时间接近程度排序。</p><p>时间基准（UTC+8）<br>${esc(stamp)}</p><p>关联分数用于排序，不表示恶意概率。展开只改变画布。</p></div></details></div><p class="cx-pivot">${esc(pivot||s.pivot)}<span>相近 24 小时</span></p><section class="cx-candidates" aria-label="候选告警">${cards||'<div class="cx-empty">没有找到其他关联告警。可选择另一个对象继续。</div>'}</section>${rows.length>s.limit?button('more',`查看更多（剩余 ${rows.length-s.limit}）`,'','aria-label="查看更多关联线索"'):''}</div>`;
  }
  function showDetails(){if(current)current.s.panel='details';}
  function handle(action,value){if(!action.startsWith('cx-')||!current||ctx.currentRoute().page!=='cases'||ctx.currentRoute().tab!=='attack')return false;const {c,s,g}=current,a=action.slice(3);
    try{
      if(a==='ask'){const n=g.nodes.find(n=>n.id===value);if(!M.supported(n)||n.preview)return true;const object=M.objectFor(n,M.assetsFor(store,c,eligible));if(n.kind!=='alert'&&!object){ctx.toast('该节点尚无完整对象记录，可先查看关联依据。');return true;}ctx.caseActions().askContext(n.kind==='alert'?{alertIds:[n.id]}:{entityIds:[object.id]});return true;}
      if(a==='panel'&&['details','leads'].includes(value)){s.panel=value;if(value==='leads'&&s.pivot===undefined)s.pivot=null;}
      if(a==='recommend'){s.panel='leads';s.pivot=null;s.limit=5;s.preview=null;}
      if(a==='expand'){const n=g.nodes.find(n=>n.id===value);if(!M.supported(n)||n.preview)return true;s.panel='leads';s.pivot=value;s.limit=5;s.preview=null;}
      if(a==='close'){s.panel='details';s.pivot=undefined;s.preview=null;}
      if(a==='more')s.limit+=5;
      if(a==='add'||a==='preview'){const base=M.project(s.base,s.branches),row=M.candidates(store,c,base,s.pivot,eligible).find(r=>r.alertId===value&&!r.already);if(!row)throw Error('该候选已在画布中或已不在当前范围。');const b=M.branch(store,c,base,row,s.pivot,eligible);if(a==='preview')s.preview=s.preview?.alertId===value?null:b;else{s.branches.push(b);s.preview=null;s.dirty=true;}}
      if(a==='undo'){s.branches.pop();s.preview=null;const visible=M.project(s.base,s.branches);s.picked=s.picked.filter(id=>visible.nodes.some(n=>n.id===id));if(s.pivot&&!visible.nodes.some(n=>n.id===s.pivot))s.pivot=undefined;s.dirty=true;}
      if(a==='reset'){sessions.delete(c.id);delete c.graphExploration;ctx.save();}
      if(a==='pick'){const n=g.nodes.find(n=>n.id===value);if(!M.supported(n)||n.preview)return true;s.picked=s.picked.includes(value)?s.picked.filter(id=>id!==value):[...s.picked,value];s.dirty=true;}
      if(a==='save'){const snapshot=structuredClone({base:s.base,baseRunId:s.baseRunId,branches:s.branches,picked:s.picked,savedAt:new Date().toISOString()});c.graphExploration=snapshot;s.savedAt=snapshot.savedAt;s.dirty=false;ctx.save();ctx.toast('探索已保存，未改变成员或启动调查');}
      if(a==='prepare'||a==='adopt'||a==='ask-picked'){
        const actual=M.project(s.base,s.branches),assets=M.assetsFor(store,c,eligible),nodes=s.picked.map(id=>actual.nodes.find(n=>n.id===id)).filter(Boolean),alertIds=nodes.filter(n=>n.kind==='alert'&&store.alerts.some(a=>a.id===n.id&&eligible(c,a))).map(n=>n.id),entityIds=nodes.map(n=>M.objectFor(n,assets)?.id).filter(Boolean);
        if(!alertIds.length&&!entityIds.length)throw Error('所选节点没有可用于调查的完整记录。');
        if(a==='adopt'){ctx.caseActions().openGraphAdoption(alertIds);return true;}
        if(a==='ask-picked'){ctx.caseActions().askContext({alertIds,entityIds});return true;}
        ctx.caseActions().prepareFromGraph({alertIds,entityIds,sourceRunId:s.baseRunId,graphReference:{baseRunId:s.baseRunId,branches:structuredClone(s.branches),nodeIds:nodes.map(n=>n.id),anchorTime:s.base.anchorTime}});return true;
      }
      if(a==='focus'){s.panel='details';return {focus:value};}
      ctx.render();
    }catch(e){ctx.toast(e.message);}return true;
  }
  const pinnedRunId=c=>{const saved=sessions.get(c.id)||c.graphExploration;return fixed(saved)?(saved.baseRunId||saved.base?.runId):null;};
  return {begin,toolbar,detail,handle,showDetails,pinnedRunId};
};
