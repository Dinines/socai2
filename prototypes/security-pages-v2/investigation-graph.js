/* Run-scoped, read-only graph projection. Never infer a missing path from a report. */
'use strict';
window.investigationGraphModel = (() => {
  const kinds={Alert:'alert',Case:'case',Host:'device',User:'user',Identity:'user',Endpoint:'endpoint',IOC:'ip',Technique:'tech',host:'device',technique:'tech',asset:'ip'};
  const catalogue={
    'T1059.001':{name:'PowerShell',tactics:['执行'],url:'T1059/001'},
    'T1071.001':{name:'Web 协议',tactics:['命令与控制'],url:'T1071/001'},
    'T1078':{name:'有效账户',tactics:['初始访问','持久化','权限提升','隐匿'],url:'T1078'}
  };
  const kind=n=>kinds[n.kind||n.label||n.type]||n.kind||n.type||'entity';
  const value=n=>{const p=n.properties||{};return p.hostname||p.username||p.indicator_value||p.technique_id||p.title||p.name||p.value||n.name||(n.kind?n.label:null)||n.id;};
  function build(run,store,context){
    const nodes=new Map(),edges=[],inputs=new Set(run.alertIds),path=run.graphs?.attack_path,chain=run.graphs?.attack_chain,neighborhood=run.graphs?.alert_graph;
    const same=a=>window.investigationWorkspaceModel?.sameScope?window.investigationWorkspaceModel.sameScope(a,run):(a.sourceTenantId||'')===(run.sourceTenantId||'')&&(a.sourceEnvironment||'')===(run.sourceEnvironment||'');
    const inventory=new Map(store.alerts.filter(same).map(a=>[a.id,a]));
    const inTenant=n=>!n.properties?.tenant_id||!run.sourceTenantId||n.properties.tenant_id===run.sourceTenantId;
    const sourceNodes=[...(path?.data?.nodes||[]),...(context?.nodes||[]),neighborhood?.data?.neighbors?.source,...(neighborhood?.data?.neighbors?.neighbors||[]).map(n=>n.node||n.neighbor||n)].filter(Boolean);
    const conflictedIds=new Set(sourceNodes.filter(n=>!inTenant(n)).flatMap(n=>[n.id,n.properties?.source_alert_id]).filter(Boolean));
    const allowed=n=>inTenant(n)&&!conflictedIds.has(n.id)&&!conflictedIds.has(n.properties?.source_alert_id);
    const add=(id,k,label,extra={})=>{if(!nodes.has(id))nodes.set(id,{id,kind:k,label:String(label||id),...extra});return nodes.get(id);};
    const addAlert=(id,record={})=>{const a=inventory.get(id)||{},n=add(id,'alert',record.title||a.title||id,{input:inputs.has(id),time:record.event_time||a.event_time||a.first,severity:record.severity||a.severity,status:a.status||'Unknown'});if(record.title)n.label=record.title;if(record.event_time)n.time=record.event_time;return n;};
    [...inputs].forEach(id=>addAlert(id));
    const addEdge=(a,b,type,layer,source)=>{
      if(!nodes.has(a)||!nodes.has(b)||nodes.get(a).kind==='case'||nodes.get(b).kind==='case')return;
      let edge=edges.find(e=>e.from===a&&e.to===b);
      if(!edge){edge={id:'relation-'+edges.length,from:a,to:b,layer,sources:[]};edges.push(edge);}
      if(layer!=='chain')edge.layer=layer;
      if(!edge.sources.some(s=>s.material===source.material&&s.type===type))edge.sources.push({...source,type});
    };
    const fallback=path?.fallback||path?.source==='postgres_fallback'||path?.data?.source==='postgres_fallback';
    const caseTech=[];
    if(path?.status==='success'){
      const local=new Map();
      for(const n of path.data?.nodes||[]){if(!allowed(n))continue;const k=kind(n),id=k==='alert'?(n.properties?.source_alert_id||n.id):n.id;local.set(n.id,id);if(k==='alert')addAlert(id,n.properties||{});else add(id,k,value(n),{origin:'path'});}
      for(const e of path.data?.edges||[]){const a=local.get(e.source),b=local.get(e.target),type=e.type||e.label||'关系';
        if(fallback&&type==='MAPS_TO'){if(nodes.has(b)&&!caseTech.includes(b))caseTech.push(b);continue;}
        addEdge(a,b,type,type==='MAPS_TO'?'tech':'entity',{material:'attack_path',source:path.source||'已保存路径',time:path.queried_at});}
      if(fallback)for(const id of caseTech)nodes.delete(id);
    }
    // Context is explicitly supplied by the caller and never written back into Run.graphs.
    if(context&&!path?.data?.nodes?.length){
      for(const n of context.nodes||[]){if(!allowed(n))continue;const k=kind(n);if(k==='alert')addAlert(n.id,{title:n.label});else add(n.id,k,value(n),{origin:'context'});}
      for(const e of context.edges||[])addEdge(e.source,e.target,e.label||e.type||'关联',e.label==='MAPS_TO'?'tech':'entity',{material:'context',source:context.source||'告警关联资料',time:context.generatedAt});
    }
    // The saved neighborhood records direct relationships; reachability alone supplies no drawable edges.
    if(neighborhood?.status==='success'){
      const adjacent=neighborhood.data?.neighbors,anchor=adjacent?.source;
      if(anchor&&allowed(anchor)){
        const register=n=>{if(!n||!allowed(n))return null;const k=kind(n),id=k==='alert'?(n.properties?.source_alert_id||n.id):n.id;if(!id)return null;if(k==='alert')addAlert(id,n.properties||{});else add(id,k,value(n),{origin:'alert_graph'});return id;};
        const anchorId=register(anchor);
        for(const item of adjacent.neighbors||[]){const type=item.rel_type||item.relationship_type||item.type;if(!type)continue;const target=register(item.node||item.neighbor||item);
          if(anchorId&&target&&type)addEdge(anchorId,target,type,type==='MAPS_TO'?'tech':'entity',{material:'alert_graph',source:neighborhood.source||'已保存邻居',time:neighborhood.queried_at,direction:'unknown'});
        }
      }
    }
    const cd=chain?.data||{},chainAllowed=!cd.tenant_id||!run.sourceTenantId||cd.tenant_id===run.sourceTenantId;
    const candidates=chainAllowed&&['success','empty'].includes(chain?.status)?(cd.chain||[]):[];
    for(const c of candidates)Object.assign(addAlert(c.alert_id,c),{candidate:c});
    if(chainAllowed&&['success','empty'].includes(chain?.status)){
      const aliases=new Map();
      for(const n of cd.entity_graph?.nodes||[]){
        if(kind(n)==='alert'){const id=String(n.id).replace(/^alert:/,'');addAlert(id,{title:n.label,event_time:n.event_time,severity:n.severity});aliases.set(n.id,id);continue;}
        const k=kind(n),v=value(n),matches=[...nodes.values()].filter(x=>x.label===v&&(k==='user'?x.kind==='user':k==='endpoint'?['device','ip','endpoint'].includes(x.kind):x.kind===k));
        const id=matches.length===1?matches[0].id:'pg:'+n.id;aliases.set(n.id,id);add(id,k,v,{origin:'chain'});
      }
      for(const e of cd.entity_graph?.edges||[])addEdge(aliases.get(e.source),aliases.get(e.target),e.kind||e.type||'TOUCHES',inputs.has(aliases.get(e.source))?'entity':'chain',{material:'attack_chain',source:chain.source||'postgres',time:chain.queried_at});
    }
    const inputNodes=[...inputs].map(id=>nodes.get(id)).filter(Boolean).sort((a,b)=>(Date.parse(a.time)||0)-(Date.parse(b.time)||0));
    const others=[...nodes.values()].filter(n=>n.kind==='alert'&&!inputs.has(n.id));
    inputNodes.forEach((n,i)=>n.code='A'+(i+1));others.forEach((n,i)=>n.code='E'+(i+1));
    const related=others.slice().sort((a,b)=>(b.candidate?.score??-1)-(a.candidate?.score??-1)).map(n=>n.id);
    const relatedState=!chainAllowed?'scope_mismatch':!chain?'missing':chain.status;
    return {runId:run.id,key:[run.sourceEnvironment,run.sourceTenantId,run.id].join(':'),nodes:[...nodes.values()].filter(n=>n.kind!=='case'),edges,inputs:inputNodes.map(n=>n.id),candidates:candidates.map(c=>c.alert_id),related,relatedState,seed:cd.seed_alert_id,window:cd.window,caseTech,context:!!context,chainMismatch:!chainAllowed};
  }
  function defaults(mode){return {selected:null,type:null,list:mode==='attack_chain'?'candidates':'inputs',chain:mode==='attack_chain'||mode==='all',entity:true,tech:true,hidden:[],grouped:false,expanded:[],layout:'auto',zoom:1,message:''};}
  function visible(g,s){const nodes=g.nodes.filter(n=>n.kind==='alert'?(n.input||s.chain):n.kind==='tech'?s.tech:(s.entity&&!s.hidden.includes(n.kind)));const ids=new Set(nodes.map(n=>n.id));return {nodes,edges:g.edges.filter(e=>ids.has(e.from)&&ids.has(e.to)&&(e.layer==='chain'?s.chain:e.layer==='tech'?s.tech:s.entity))};}
  function focus(g,s){const v=visible(g,s),direct=new Set(),related=new Set(),edgeIds=new Set();
    if(s.type==='edge'){const e=v.edges.find(e=>e.id===s.selected);if(e){direct.add(e.from);direct.add(e.to);edgeIds.add(e.id);}}
    else if(v.nodes.some(n=>n.id===s.selected)){direct.add(s.selected);for(const e of v.edges)if(e.from===s.selected||e.to===s.selected){direct.add(e.from);direct.add(e.to);edgeIds.add(e.id);}}
    direct.forEach(id=>related.add(id));
    if(s.type==='alert')for(const e of v.edges)if(e.layer!=='tech'&&direct.has(e.to))related.add(e.from);
    return {direct,related,edgeIds};
  }
  function ensureVisible(g,s,id){const n=g.nodes.find(n=>n.id===id);if(!n)return;if(n.kind==='alert'&&!n.input)s.chain=true;else if(n.kind==='tech')s.tech=true;else if(n.kind!=='alert'){s.entity=true;s.hidden=s.hidden.filter(k=>k!==n.kind);}}
  function select(g,s,id,type){s.message='';if(s.selected===id&&s.type===type){s.selected=null;s.type=null;return;}s.selected=id;s.type=type;if(type==='edge'){const e=g.edges.find(e=>e.id===id);if(e){ensureVisible(g,s,e.from);ensureVisible(g,s,e.to);if(e.layer==='chain')s.chain=true;}}else ensureVisible(g,s,id);}
  function reconcile(g,s){const v=visible(g,s);if(s.selected&&!(s.type==='edge'?v.edges:v.nodes).some(x=>x.id===s.selected)){s.selected=null;s.type=null;s.message='所选对象已隐藏，聚焦已清除。';}}
  function display(g,s){const v=visible(g,s),all=g.nodes.filter(n=>n.kind!=='alert'&&n.kind!=='tech'),map=new Map(v.nodes.map(n=>[n.id,n.id])),nodes=[];
    for(const n of v.nodes){const peers=all.filter(x=>x.kind===n.kind);if(s.grouped&&n.kind!=='alert'&&n.kind!=='tech'&&peers.length>1&&!s.expanded.includes(n.kind)){
      const id='group:'+n.kind;map.set(n.id,id);if(!nodes.some(x=>x.id===id))nodes.push({id,kind:n.kind,label:peers.length+' 个'+n.kind,members:peers.map(x=>x.id),group:true});
    }else nodes.push({...n,members:[n.id]});}
    return {nodes,edges:v.edges.map(e=>({...e,drawFrom:map.get(e.from),drawTo:map.get(e.to)}))};
  }
  function positions(g,s){
    const pos=new Map(),inputs=g.inputs.map(id=>g.nodes.find(n=>n.id===id)),external=g.nodes.filter(n=>n.kind==='alert'&&!n.input),entities=g.nodes.filter(n=>!['alert','tech'].includes(n.kind)),techs=g.nodes.filter(n=>n.kind==='tech').sort((a,b)=>{const index=n=>Math.min(...g.edges.filter(e=>e.to===n.id).map(e=>g.inputs.indexOf(e.from)).filter(i=>i>=0),999);return index(a)-index(b);});
    const h=Math.max(510,Math.max(inputs.length,techs.length,Math.ceil(entities.length/2))*145+80),height=h+(external.length?Math.ceil(external.length/3)*105:0);
    inputs.forEach((n,i)=>pos.set(n.id,{x:13,y:65+i*(h-120)/Math.max(1,inputs.length-1)}));
    techs.forEach((n,i)=>pos.set(n.id,{x:86,y:65+i*(h-120)/Math.max(1,techs.length-1)}));
    entities.forEach((n,i)=>pos.set(n.id,{x:50,y:85+i*(h-150)/Math.max(1,entities.length-1)}));
    // The reference graph uses a central entity and a spacious surrounding network.
    // Use all saved nodes, not the filtered/selected view, so focus never moves them.
    if(s.layout==='auto'){
      const degree=n=>g.edges.filter(e=>e.from===n.id||e.to===n.id).length;
      const center=[...entities].sort((a,b)=>degree(b)-degree(a))[0];
      const ring=[...inputs,...entities.filter(n=>n!==center),...techs];
      if(center)pos.set(center.id,{x:50,y:h/2});
      ring.forEach((n,i)=>{
        if(ring.length>10){pos.set(n.id,{x:14+(i%4)*24,y:75+Math.floor(i/4)*135});return;}
        const angle=-Math.PI/2+i*2*Math.PI/Math.max(1,ring.length);
        pos.set(n.id,{x:50+35*Math.cos(angle),y:h/2+(h/2-76)*Math.sin(angle)});
      });
      // Large saved graphs use a grid with a separate slot for the central entity.
      if(center&&ring.length>10)pos.set(center.id,{x:14+(ring.length%4)*24,y:75+Math.floor(ring.length/4)*135});
    }
    external.forEach((n,i)=>pos.set(n.id,{x:[14,50,85][i%3],y:h+48+Math.floor(i/3)*105}));
    for(const k of new Set(entities.map(n=>n.kind))){const ns=entities.filter(n=>n.kind===k),ps=ns.map(n=>pos.get(n.id));pos.set('group:'+k,{x:ps.reduce((v,p)=>v+p.x,0)/ps.length,y:ps.reduce((v,p)=>v+p.y,0)/ps.length});}
    return {pos,height};
  }
  return {build,defaults,visible,focus,select,reconcile,display,positions,catalogue};
})();

window.createUnifiedInvestigationGraph = function(ctx){
  const {esc,I,severity,state:status,format}=ctx,M=window.investigationGraphModel;
  const typeNames={device:'设备',user:'账户',ip:'IP / IOC',endpoint:'端点',entity:'实体',email:'邮箱',file:'文件',app:'应用',cloud:'云资源',tech:'ATT&CK 技术'};
  const icons={device:'device',user:'user',ip:'ip',endpoint:'device',entity:'graph',email:'mail',file:'file',app:'app',cloud:'cloud'};
  const states=new Map(),explorer=window.createCaseExploration?.(ctx);let current=null;
  const severityLabel=v=>{const label=({high:'高',critical:'高',medium:'中',low:'低',info:'低',informational:'低'})[String(v).toLowerCase()]||v;return ['高','中','低'].includes(label)?severity(label):'<span>等级未记录</span>';};
  const action=(a,id,text,extra='')=>`<button type="button" data-action="ug-${a}" data-id="${esc(id)}" ${extra}>${text}</button>`;
  const caseForView=()=>ctx.currentRoute?.().page==='cases'?ctx.currentCase?.():null;
  const memberLabel=n=>{const c=caseForView();return c?(c.alertIds.includes(n.id)?'本案成员':'未加入本案'):'';};
  const relatedStatus=g=>({missing:'未保存关联查询结果',unavailable:'关联查询不可用',error:'关联查询失败',scope_mismatch:'关联资料范围不匹配',not_linked:'未保存关联查询结果'})[g.relatedState]||'未发现其他关联告警';
  function membershipDetail(n,g){
    const c=caseForView();if(!c)return '';
    const a=ctx.getAlert(n.id),other=ctx.store.cases.filter(x=>x.id!==c.id&&x.alertIds.includes(n.id)),member=c.alertIds.includes(n.id);
    const canAdd=!member&&a&&ctx.caseActions?.().eligible(c,a);
    return `<div class="ug-case-membership"><strong>${member?'已在本案中':'未加入本案'}</strong>${other.length?`<p>同时关联 ${other.map(x=>`<a href="#/cases/${encodeURIComponent(x.id)}/case-info">${esc(x.title)}</a>`).join('、')}</p>`:''}${canAdd?`<button class="button primary small" data-action="cw-add-related" data-id="${esc(JSON.stringify([g.virtual?null:g.runId,n.id]))}">加入本案</button><small>确认后加入案件，历史调查输入保持不变。</small>`:!member?'<small>当前没有可加入本案的完整告警记录。</small>':''}</div>`;
  }
  function selectedDetail(g,s){
    const n=g.nodes.find(n=>n.id===s.selected),e=g.edges.find(e=>e.id===s.selected),visible=M.visible(g,s);
    const connector=e=>e.sources.every(p=>p.direction==='unknown')?'—':'→';
    const relation=e=>action('edge',e.id,`${esc(g.nodes.find(n=>n.id===e.from)?.code||'')} ${connector(e)} ${esc(g.nodes.find(n=>n.id===e.to)?.label||e.to)}`);
    if(s.type==='edge'&&e){const a=g.nodes.find(n=>n.id===e.from),b=g.nodes.find(n=>n.id===e.to);return `<h4>${esc(a.code||a.label)} ${connector(e)} ${esc(b.label)}</h4><p>选中这一条关系及两端。关系方向不表示攻击传播。</p><dl>${e.sources.map(p=>`<dt>${esc(p.source)} · ${esc(p.material)}</dt><dd><code>${esc(p.type)}</code>${p.time?' · '+format(p.time):''}${p.direction==='unknown'?' · 原记录未提供方向':''}</dd>`).join('')}</dl>`;}
    if(!n)return `<h4>${s.message?esc(s.message):'全部关系'}</h4><p>选择告警、实体或技术，查看相关对象与关联依据。</p>`;
    const links=g.edges.filter(e=>e.from===n.id||e.to===n.id),shown=visible.edges.filter(e=>links.includes(e));
    if(n.kind==='alert')return `<div class="ug-detail-title"><h4>${esc(n.code)} · ${esc(n.label)}</h4><span>${n.input?'本次输入':'非本次输入'}</span>${ctx.getAlert(n.id)?`<a href="#/alerts/${encodeURIComponent(n.id)}/overview">打开告警详情 ${I('external',13)}</a>`:''}</div>${membershipDetail(n,g)}<div class="ug-related-basis"><h4>关联依据</h4>${n.candidate?.shared_entities?.length?`<p>共享对象：${n.candidate.shared_entities.map(x=>esc(x.value)).join('、')}</p>`:''}${n.candidate?`<p>关联排序分数 ${esc(n.candidate.score??'未提供')} · 关联层数 ${esc(n.candidate.distance??'未提供')}</p><p>与种子时间差 ${n.candidate.dt_seconds==null?'未提供':esc(n.candidate.dt_seconds)+' 秒'}</p>`:''}<p>${links.length?`${links.filter(e=>e.layer!=='tech').length} 条实体关联 · ${links.filter(e=>e.layer==='tech').length} 条技术映射`:'未保存可绘制的关联关系'}${!links.length&&n.candidate?.distance>1?'；中间连线未保存':''}</p></div><div class="ug-basis">${links.map(relation).join('')}</div><details><summary>来源与查询范围</summary><p>告警 ID：${esc(n.id)}</p>${n.candidate?`<p>原种子 ${esc(g.seed)} · 窗口 ${esc(g.window||'未记录')}；分数用于关联排序，不表示恶意概率。</p>`:''}<p>选择不改变调查输入、Case 成员或查询种子。</p></details>`;
    const cat=M.catalogue[n.label],related=[...new Set(shown.flatMap(e=>[e.from,e.to]))].map(id=>g.nodes.find(n=>n.id===id)).filter(n=>n.kind==='alert');
    return `<h4>${esc(n.label)}</h4><p>${esc(typeNames[n.kind]||n.kind)} · 当前显示 ${related.length} 条关联告警</p>${n.kind==='tech'?`<p>${cat?esc(cat.tactics.join('、'))+' · '+esc(cat.name):'未载入战术目录映射'}；分类不表示本次调查已确认该战术成立。</p>${cat?`<a href="https://attack.mitre.org/techniques/${cat.url}/" target="_blank" rel="noreferrer">ATT&CK 分类来源 · 2026-10-28核对</a>`:''}`:''}<div class="ug-basis">${related.map(a=>action('node',a.id,esc(a.code+' · '+a.label))).join('')}</div><details><summary>关联依据（${links.length}）</summary><div class="ug-basis">${links.map(relation).join('')}</div></details>`;
  }
  function html(g,s){
    const f=M.focus(g,s),v=M.visible(g,s),d=M.display(g,s),layout=M.positions(g,s),byId=new Map(g.nodes.map(n=>[n.id,n]));
    const rows=(s.list==='candidates'?g.related:g.inputs).map(id=>byId.get(id)).filter(Boolean),entityKinds=[...new Set(g.nodes.filter(n=>!['alert','tech'].includes(n.kind)).map(n=>n.kind))];
    const list=rows.map(n=>action('node',n.id,`<span class="ug-row-meta"><time>${format(n.time)}</time><span>${esc(n.code)}</span></span><strong>${esc(n.label.replace(/^Attack context fixture \d+: /,''))}</strong><span class="ug-row-meta">${severityLabel(n.severity)}<span>${memberLabel(n)|| (n.input?'本次输入':'关联告警')}</span></span><span class="ug-row-meta">${n.status==='Unknown'?'<span>状态未记录</span>':status(n.status)}${s.list==='candidates'&&n.candidate?`<span>关联分数 ${esc(n.candidate.score??'—')} · ${esc(n.candidate.distance??'—')} 层</span>`:''}</span>`,`class="ug-alert ${f.related.has(n.id)?'related':''}" aria-pressed="${s.selected===n.id}"`)).join('');
    const nodeHTML=d.nodes.map(n=>{const p=layout.pos.get(n.id),direct=n.members.some(id=>f.direct.has(id)),related=n.members.some(id=>f.related.has(id)),selected=n.members.includes(s.selected),count=n.members.filter(id=>f.direct.has(id)).length;
      const label=n.group?n.members.length+' 个'+(typeNames[n.kind]||n.kind):n.kind==='alert'?n.code:n.label;
      const caption=n.kind==='alert'?n.label.replace(/^Attack context fixture \d+: /,''):n.kind==='tech'?(M.catalogue[n.label]?.name||'ATT&CK 技术'):'';
      const glyph=n.kind==='alert'?'shield':n.kind==='tech'?'tag':icons[n.kind]||'graph';
      return action(n.group?'group':'node',n.group?n.kind:n.id,`<span class="ug-circle">${I(glyph,22)}${n.picked?'<b class="cx-pick-mark">✓</b>':''}${n.group?`<b>${n.members.length}</b>`:''}</span><strong>${esc(label)}</strong>${n.kind==='alert'&&!n.input&&memberLabel(n)?`<small>${esc(memberLabel(n))}</small>`:''}${caption?`<span class="ug-node-caption">${esc(caption)}</span>`:''}${n.group?`<small>${s.selected?'命中 '+count+' / ':''}${n.members.length} · 点击展开</small>`:''}`,`class="ug-node ${n.explored?'cx-expanded':''} ${n.preview?'cx-preview':''} ${n.picked?'cx-picked':''} ${n.kind==='alert'?'alert':n.kind==='tech'?'tech':'entity'} ${n.kind==='alert'&&!n.input?'external':''} ${direct?'direct':''} ${selected?'selected':''} ${s.selected&&!related?'dim':''}" style="left:${p.x}%;top:${p.y}px" title="${esc(n.label)}" aria-label="${esc(n.group?'展开'+typeNames[n.kind]+'分组':n.code?n.code+' '+n.label:n.label)}" aria-pressed="${selected}"`);
    }).join('');
    const lines=d.edges.map(e=>{const a=layout.pos.get(e.drawFrom),b=layout.pos.get(e.drawTo),x=a.x*10,y=b.x*10,curve=`M${x},${a.y} Q${(x+y)/2},${(a.y+b.y)/2+18} ${y},${b.y}`;return `<path class="ug-line ${e.layer} ${f.edgeIds.has(e.id)?'focused':s.selected?'dim':''}" d="${curve}"/><path class="ug-hit" d="${curve}" data-action="ug-edge" data-id="${esc(e.id)}"><title>${esc(e.sources.map(p=>p.type).join(' / '))}</title></path>`;}).join('');
    const tech=g.nodes.filter(n=>n.kind==='tech'),labelTech=n=>{const c=M.catalogue[n.label];return c?(c.tactics.length===1?c.tactics[0]:'多战术映射')+' · '+n.label:n.label;};
    return `<section class="ug-root ${g.explorable?'cx-root':''}" data-investigation-graph data-run-id="${esc(g.runId)}">${g.explorable?explorer.toolbar():''}<div class="ug-scope"><span>本次输入 <b>${g.inputs.length}</b> 条</span>${g.seed?`<span>查询种子 ${esc(byId.get(g.seed)?.code||g.seed)} · 窗口 ${esc(g.window||'未记录')}</span>`:''}</div>${tech.length?`<div class="ug-tactics"><span>技术与战术</span>${tech.map(n=>action('node',n.id,esc(labelTech(n)),`aria-pressed="${s.selected===n.id}"`)).join('')}</div>`:''}${g.caseTech.length?`<p class="ug-notice">存在 Case 级技术资料，逐告警归属未核；${g.explorable?'原记录可在本次调查中查看':'原记录见下方来源材料'}。</p>`:''}${g.chainMismatch?'<p class="ug-notice">候选材料租户与本次调查不一致，未合入关系图。</p>':''}<div class="ug-body"><aside class="ug-left"><h3>告警与检测</h3><nav aria-label="关系图告警列表">${action('list','inputs','本次输入 '+g.inputs.length,`aria-pressed="${s.list==='inputs'}"`)}${action('list','candidates','关联告警'+(g.related.length?' '+g.related.length:''),`aria-pressed="${s.list==='candidates'}"`)}</nav><div class="ug-list">${list||`<p class="ug-empty">${s.list==='candidates'?(g.explorable?'当前画布没有其他关联告警，可查看推荐线索或从对象扩展。':relatedStatus(g)):'未记录输入告警'}</p>`}</div></aside><div class="ug-main"><div class="ug-toolbar"><h3>关系图</h3><label><select data-ug-layout aria-label="关系图布局"><option value="auto" ${s.layout==='auto'?'selected':''}>自动布局</option><option value="columns" ${s.layout==='columns'?'selected':''}>分列布局</option></select></label><label><input type="checkbox" data-ug-group ${s.grouped?'checked':''}>同类分组</label></div><div class="ug-controls"><div class="ug-types">${entityKinds.map(k=>action('type',k,`${I(icons[k]||'graph',12)}${esc(typeNames[k]||k)}`,`aria-pressed="${!s.hidden.includes(k)}"`)).join('')}</div></div><div class="ug-layers">${['entity','chain','tech'].map((k,i)=>`<label><input type="checkbox" data-ug-layer="${k}" ${s[k]?'checked':''}>${['实体关系',g.explorable?'关联告警':'候选关联','技术映射'][i]}</label>`).join('')}${action('clear','','取消聚焦')}</div><div class="ug-canvas"><div class="ug-zoom">${action('zoom','in','＋','aria-label="放大图谱"')}${action('zoom','out','−','aria-label="缩小图谱"')}${action('zoom','reset','重置视角')}</div><div class="ug-scroll"><div class="ug-plane" style="height:${layout.height}px;width:${s.zoom*100}%;min-width:${600*s.zoom}px"><svg class="ug-lines" viewBox="0 0 1000 ${layout.height}" preserveAspectRatio="none" aria-label="本次调查保存的关系图">${lines}</svg>${nodeHTML}</div></div></div><div class="ug-legend"><span><i></i>已记录关系</span><span><i class="${g.explorable?'exploration':'chain'}"></i>${g.explorable?'探索关系':'候选关联'}</span><span><i class="tech"></i>技术映射</span><span>显示 ${v.nodes.length} / ${g.nodes.length} 个对象 · ${v.edges.length} 条连线</span></div></div><aside class="ug-detail" aria-label="图谱对象详情">${g.explorable?explorer.detail(g,s,()=>selectedDetail(g,s)):`<div class="ug-detail-heading">对象与关联详情</div><div class="ug-detail-content" aria-live="polite">${selectedDetail(g,s)}</div>`}</aside></div></section>`;
  }
  function render(run,context,mode,options={}){
    const explore=!!(options.caseSnapshot&&explorer&&caseForView()),source=explore?{...run,graphs:{...run.graphs,attack_chain:null}}:run;
    let g=M.build(source,ctx.store,context);g.virtual=!!run.virtual;if(explore)g=explorer.begin(caseForView(),g,run);
    let s=states.get(g.key);if(!s){s={...M.defaults(mode),mode};states.set(g.key,s);}else if(s.mode!==mode){const preset=M.defaults(mode);Object.assign(s,{mode,list:preset.list,chain:preset.chain,entity:true,tech:true,selected:null,type:null});}M.reconcile(g,s);current={g,s};return html(g,s);
  }
  function repaint(){if(!current)return;const el=typeof document.querySelector==='function'?document.querySelector('[data-investigation-graph]'):null;if(el){const focused=document.activeElement,token=el.contains(focused)?{action:focused.dataset.action,id:focused.dataset.id,layer:focused.dataset.ugLayer,layout:focused.hasAttribute('data-ug-layout'),group:focused.hasAttribute('data-ug-group')}:null;const scroll=el.querySelector('.ug-scroll'),x=scroll?.scrollLeft||0,y=scroll?.scrollTop||0;el.outerHTML=html(current.g,current.s);const root=document.querySelector('[data-investigation-graph]'),fresh=root.querySelector('.ug-scroll');if(fresh){fresh.scrollLeft=x;fresh.scrollTop=y;}if(token){const target=[...root.querySelectorAll('button,input,select')].find(n=>token.action?n.dataset.action===token.action&&n.dataset.id===token.id:token.layer?n.dataset.ugLayer===token.layer:token.layout?n.hasAttribute('data-ug-layout'):token.group&&n.hasAttribute('data-ug-group'));target?.focus({preventScroll:true});}}else ctx.render();}
  function handle(actionName,id){if(current?.g.explorable&&actionName.startsWith('cx-')){const result=explorer.handle(actionName,id);if(result?.focus){M.select(current.g,current.s,result.focus,'alert');repaint();}return !!result;}if(!actionName.startsWith('ug-')||!current)return false;const {g,s}=current,a=actionName.slice(3);s.message='';
    if(g.explorable&&(a==='node'||a==='edge'))explorer.showDetails();
    if(a==='node'){const n=g.nodes.find(n=>n.id===id);if(n)M.select(g,s,id,n.kind==='alert'?'alert':n.kind==='tech'?'tech':'entity');}
    if(a==='edge')M.select(g,s,id,'edge');
    if(a==='clear'){s.selected=null;s.type=null;}
    if(a==='list'){s.list=id;if(id==='candidates')s.chain=true;}
    if(a==='type'){s.hidden=s.hidden.includes(id)?s.hidden.filter(k=>k!==id):[...s.hidden,id];M.reconcile(g,s);}
    if(a==='group')s.expanded=[...new Set([...s.expanded,id])];
    if(a==='zoom')s.zoom=id==='reset'?1:Math.max(.7,Math.min(1.8,s.zoom+(id==='in'?.15:-.15)));
    repaint();return true;
  }
  function change(el){if(!current)return false;const {g,s}=current;
    if(el.hasAttribute('data-ug-layer')){s[el.dataset.ugLayer]=el.checked;M.reconcile(g,s);}
    else if(el.hasAttribute('data-ug-layout'))s.layout=el.value;
    else if(el.hasAttribute('data-ug-group')){s.grouped=el.checked;s.expanded=[];}
    else return false;repaint();return true;
  }
  return {render,handle,change,pinnedRunId:c=>explorer?.pinnedRunId(c)};
};
