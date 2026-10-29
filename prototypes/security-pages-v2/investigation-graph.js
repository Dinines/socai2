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
    const nodes=new Map(),edges=[],inputs=new Set(run.alertIds),path=run.graphs?.attack_path,chain=run.graphs?.attack_chain;
    const same=a=>(!run.sourceTenantId||!a.sourceTenantId||a.sourceTenantId===run.sourceTenantId)&&(!run.sourceEnvironment||!a.sourceEnvironment||a.sourceEnvironment===run.sourceEnvironment);
    const inventory=new Map(store.alerts.filter(same).map(a=>[a.id,a]));
    const allowed=n=>!n.properties?.tenant_id||!run.sourceTenantId||n.properties.tenant_id===run.sourceTenantId;
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
    return {runId:run.id,key:[run.sourceEnvironment,run.sourceTenantId,run.id].join(':'),nodes:[...nodes.values()].filter(n=>n.kind!=='case'),edges,inputs:inputNodes.map(n=>n.id),candidates:candidates.map(c=>c.alert_id),seed:cd.seed_alert_id,window:cd.window,caseTech,context:!!context,chainMismatch:!chainAllowed};
  }
  function defaults(mode){return {selected:null,type:null,list:mode==='attack_chain'?'candidates':'inputs',chain:mode==='attack_chain',entity:true,tech:true,hidden:[],grouped:false,expanded:[],layout:'auto',zoom:1,message:''};}
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
    entities.forEach((n,i)=>pos.set(n.id,{x:s.layout==='columns'?50:(entities.length<=2?50:i%2?60:40),y:85+Math.floor(i/(s.layout==='columns'?1:2))*(h-150)/Math.max(1,(s.layout==='columns'?entities.length:Math.ceil(entities.length/2))-1)}));
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
  const states=new Map();let current=null;
  const severityLabel=v=>{const label=({high:'高',critical:'高',medium:'中',low:'低',info:'低',informational:'低'})[String(v).toLowerCase()]||v;return ['高','中','低'].includes(label)?severity(label):'<span>等级未记录</span>';};
  const action=(a,id,text,extra='')=>`<button type="button" data-action="ug-${a}" data-id="${esc(id)}" ${extra}>${text}</button>`;
  function selectedDetail(g,s){
    const n=g.nodes.find(n=>n.id===s.selected),e=g.edges.find(e=>e.id===s.selected),visible=M.visible(g,s);
    const relation=e=>action('edge',e.id,`${esc(g.nodes.find(n=>n.id===e.from)?.code||'')} → ${esc(g.nodes.find(n=>n.id===e.to)?.label||e.to)}`);
    if(s.type==='edge'&&e){const a=g.nodes.find(n=>n.id===e.from),b=g.nodes.find(n=>n.id===e.to);return `<h4>${esc(a.code||a.label)} → ${esc(b.label)}</h4><p>选中这一条关系及两端。关系方向不表示攻击传播。</p><dl>${e.sources.map(p=>`<dt>${esc(p.source)} · ${esc(p.material)}</dt><dd><code>${esc(p.type)}</code>${p.time?' · '+format(p.time):''}</dd>`).join('')}</dl>`;}
    if(!n)return `<h4>${s.message?esc(s.message):'全部关系'}</h4><p>选择告警、实体或技术，查看相关对象与关联依据。</p>`;
    const links=g.edges.filter(e=>e.from===n.id||e.to===n.id),shown=visible.edges.filter(e=>links.includes(e));
    if(n.kind==='alert')return `<div class="ug-detail-title"><h4>${esc(n.code)} · ${esc(n.label)}</h4><span>${n.input?'本次输入':'范围外关联告警'}</span>${ctx.getAlert(n.id)?`<a href="#/alerts/${encodeURIComponent(n.id)}/overview">打开告警详情 ${I('external',13)}</a>`:''}</div><p>${links.length?`${links.filter(e=>e.layer!=='tech').length} 条实体关联 · ${links.filter(e=>e.layer==='tech').length} 条技术映射`:'未保存可绘制的关联关系'}${n.candidate?` · 候选评分 ${esc(n.candidate.score??'—')} · 图距离 ${esc(n.candidate.distance??'—')}`:''}${!links.length&&n.candidate?.distance>1?'；中间连线未保存':''}</p><div class="ug-basis">${links.map(relation).join('')}</div><details><summary>来源与查询范围</summary><p>告警 ID：${esc(n.id)}</p>${n.candidate?`<p>原种子 ${esc(g.seed)} · 窗口 ${esc(g.window||'未记录')} · 时间差 ${esc(n.candidate.dt_seconds??'—')} 秒；候选评分用于关联排序。</p>`:''}<p>选择不改变调查输入、Case 成员或查询种子。</p></details>`;
    const cat=M.catalogue[n.label],related=[...new Set(shown.flatMap(e=>[e.from,e.to]))].map(id=>g.nodes.find(n=>n.id===id)).filter(n=>n.kind==='alert');
    return `<h4>${esc(n.label)}</h4><p>${esc(typeNames[n.kind]||n.kind)} · 当前显示 ${related.length} 条关联告警</p>${n.kind==='tech'?`<p>${cat?esc(cat.tactics.join('、'))+' · '+esc(cat.name):'未载入战术目录映射'}；分类不表示本次调查已确认该战术成立。</p>${cat?`<a href="https://attack.mitre.org/techniques/${cat.url}/" target="_blank" rel="noreferrer">ATT&CK 分类来源 · 2026-10-28核对</a>`:''}`:''}<div class="ug-basis">${related.map(a=>action('node',a.id,esc(a.code+' · '+a.label))).join('')}</div><details><summary>关联依据（${links.length}）</summary><div class="ug-basis">${links.map(relation).join('')}</div></details>`;
  }
  function html(g,s){
    const f=M.focus(g,s),v=M.visible(g,s),d=M.display(g,s),layout=M.positions(g,s),byId=new Map(g.nodes.map(n=>[n.id,n]));
    const rows=(s.list==='candidates'?g.candidates:g.inputs).map(id=>byId.get(id)).filter(Boolean),entityKinds=[...new Set(g.nodes.filter(n=>!['alert','tech'].includes(n.kind)).map(n=>n.kind))];
    const list=rows.map(n=>action('node',n.id,`<span class="ug-row-meta"><time>${format(n.time)}</time><span>${esc(n.code)}</span></span><strong>${esc(n.label.replace(/^Attack context fixture \d+: /,''))}</strong><span class="ug-row-meta">${severityLabel(n.severity)}<span>${n.input?'本次输入':'历史外部候选'}</span></span><span class="ug-row-meta">${n.status==='Unknown'?'<span>状态未记录</span>':status(n.status)}${s.list==='candidates'?`<span>评分 ${esc(n.candidate?.score??'—')} · ${esc(n.candidate?.distance??'—')} 跳</span>`:''}</span>`,`class="ug-alert ${f.related.has(n.id)?'related':''}" aria-pressed="${s.selected===n.id}"`)).join('');
    const nodeHTML=d.nodes.map(n=>{const p=layout.pos.get(n.id),direct=n.members.some(id=>f.direct.has(id)),related=n.members.some(id=>f.related.has(id)),selected=n.members.includes(s.selected),count=n.members.filter(id=>f.direct.has(id)).length;
      return action(n.group?'group':'node',n.group?n.kind:n.id,`${n.kind==='alert'?`<small>${n.input?'输入':'关联'} ${esc(n.code)}</small><span>${esc(n.label.replace(/^Attack context fixture \d+: /,''))}</span>`:n.kind==='tech'?`<strong>${esc(n.label)}</strong><small>${esc(M.catalogue[n.label]?.name||'技术')}</small>`:`<span class="ug-circle">${I(icons[n.kind]||'graph',23)}${n.group?`<b>${n.members.length}</b>`:''}</span><strong>${esc(n.group?n.members.length+' 个'+(typeNames[n.kind]||n.kind):n.label)}</strong>${n.group?`<small>${s.selected?'命中 '+count+' / ':''}${n.members.length} · 点击展开</small>`:''}`}`,`class="ug-node ${n.kind==='alert'?'alert':n.kind==='tech'?'tech':'entity'} ${n.kind==='alert'&&!n.input?'external':''} ${direct?'direct':''} ${s.selected&&!related?'dim':''}" style="left:${p.x}%;top:${p.y}px" title="${esc(n.label)}" aria-label="${esc(n.group?'展开'+typeNames[n.kind]+'分组':n.code?n.code+' '+n.label:n.label)}" aria-pressed="${selected}"`);
    }).join('');
    const lines=d.edges.map(e=>{const a=layout.pos.get(e.drawFrom),b=layout.pos.get(e.drawTo),x=a.x*10,y=b.x*10,curve=`M${x},${a.y} Q${(x+y)/2},${(a.y+b.y)/2+18} ${y},${b.y}`;return `<path class="ug-line ${e.layer} ${f.edgeIds.has(e.id)?'focused':s.selected?'dim':''}" d="${curve}"/><path class="ug-hit" d="${curve}" data-action="ug-edge" data-id="${esc(e.id)}"><title>${esc(e.sources.map(p=>p.type).join(' / '))}</title></path>`;}).join('');
    const tech=g.nodes.filter(n=>n.kind==='tech'),labelTech=n=>{const c=M.catalogue[n.label];return c?(c.tactics.length===1?c.tactics[0]:'多战术映射')+' · '+n.label:n.label;};
    return `<section class="ug-root" data-investigation-graph data-run-id="${esc(g.runId)}"><div class="ug-scope"><span>本次输入 <b>${g.inputs.length}</b> 条 · 链候选 <b>${g.candidates.length}</b> 条</span>${g.seed?`<span>查询种子 ${esc(byId.get(g.seed)?.code||g.seed)} · 窗口 ${esc(g.window||'未记录')}</span>`:''}</div>${tech.length?`<div class="ug-tactics"><span>技术与战术</span>${tech.map(n=>action('node',n.id,esc(labelTech(n)),`aria-pressed="${s.selected===n.id}"`)).join('')}</div>`:''}${g.caseTech.length?'<p class="ug-notice">存在 Case 级技术资料，逐告警归属未核；原记录见下方来源材料。</p>':''}${g.chainMismatch?'<p class="ug-notice">候选材料租户与本次调查不一致，未合入关系图。</p>':''}<div class="ug-body"><aside class="ug-left"><h3>告警与检测</h3><nav aria-label="关系图告警列表">${action('list','inputs','本次输入 '+g.inputs.length,`aria-pressed="${s.list==='inputs'}"`)}${action('list','candidates','链候选 '+g.candidates.length,`aria-pressed="${s.list==='candidates'}"`)}</nav><div class="ug-list">${list||'<p class="ug-empty">本次未返回链候选。</p>'}</div></aside><div class="ug-main"><div class="ug-toolbar"><h3>关系图</h3>${['entity','chain','tech'].map((k,i)=>`<label><input type="checkbox" data-ug-layer="${k}" ${s[k]?'checked':''}>${['实体关系','候选关联','技术映射'][i]}</label>`).join('')}${action('clear','','取消聚焦')}</div><div class="ug-controls"><div class="ug-types">${entityKinds.map(k=>action('type',k,`${I(icons[k]||'graph',14)}${esc(typeNames[k]||k)}`,`aria-pressed="${!s.hidden.includes(k)}"`)).join('')}</div><label>布局<select data-ug-layout aria-label="关系图布局"><option value="auto" ${s.layout==='auto'?'selected':''}>自动布局</option><option value="columns" ${s.layout==='columns'?'selected':''}>分列布局</option></select></label><label><input type="checkbox" data-ug-group ${s.grouped?'checked':''}>同类分组</label></div><div class="ug-canvas"><div class="ug-zoom">${action('zoom','in','＋','aria-label="放大图谱"')}${action('zoom','out','−','aria-label="缩小图谱"')}${action('zoom','reset','重置视角')}</div><div class="ug-scroll"><div class="ug-plane" style="height:${layout.height}px;width:${s.zoom*100}%;min-width:${600*s.zoom}px"><svg class="ug-lines" viewBox="0 0 1000 ${layout.height}" preserveAspectRatio="none" aria-label="本次调查保存的关系图">${lines}</svg>${nodeHTML}</div></div></div><div class="ug-legend"><span><i></i>已记录关系</span><span><i class="chain"></i>候选关联</span><span><i class="tech"></i>技术映射</span><span>显示 ${v.nodes.length} / ${g.nodes.length} 个对象 · ${v.edges.length} 条连线</span></div><div class="ug-detail" aria-live="polite">${selectedDetail(g,s)}</div></div></div></section>`;
  }
  function render(run,context,mode){const g=M.build(run,ctx.store,context);let s=states.get(g.key);if(!s){s=M.defaults(mode);states.set(g.key,s);}M.reconcile(g,s);current={g,s};return html(g,s);}
  function repaint(){if(!current)return;const el=typeof document.querySelector==='function'?document.querySelector('[data-investigation-graph]'):null;if(el){const focused=document.activeElement,token=el.contains(focused)?{action:focused.dataset.action,id:focused.dataset.id,layer:focused.dataset.ugLayer,layout:focused.hasAttribute('data-ug-layout'),group:focused.hasAttribute('data-ug-group')}:null;const scroll=el.querySelector('.ug-scroll'),x=scroll?.scrollLeft||0,y=scroll?.scrollTop||0;el.outerHTML=html(current.g,current.s);const root=document.querySelector('[data-investigation-graph]'),fresh=root.querySelector('.ug-scroll');if(fresh){fresh.scrollLeft=x;fresh.scrollTop=y;}if(token){const target=[...root.querySelectorAll('button,input,select')].find(n=>token.action?n.dataset.action===token.action&&n.dataset.id===token.id:token.layer?n.dataset.ugLayer===token.layer:token.layout?n.hasAttribute('data-ug-layout'):token.group&&n.hasAttribute('data-ug-group'));target?.focus({preventScroll:true});}}else ctx.render();}
  function handle(actionName,id){if(!actionName.startsWith('ug-')||!current)return false;const {g,s}=current,a=actionName.slice(3);s.message='';
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
  return {render,handle,change};
};
