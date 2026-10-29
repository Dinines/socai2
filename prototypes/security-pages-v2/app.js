/* Standalone reference UI. All operations stay in browser-local mock state. */
'use strict';
(() => {
  const STORAGE_KEY = 'aisoc-workspace-v2';
  const CURRENT_USER_NAME = 'Alex Wilber';
  const $ = s => document.querySelector(s);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const I = window.icon;
  const typeNames = {device:'设备',user:'用户',ip:'IP 地址',file:'文件',mailbox:'邮箱',app:'应用',cloud:'云资源',robot:'AI 代理'};
  const stateNames = {'New':'新建','In progress':'进行中','Resolved':'已解决','Completed':'已完成','Pending':'等待中','Failed':'失败','Pending approval':'待审批','Remediated':'已处置','Not started':'未开始','No action needed':'无需操作','Rejected':'已拒绝','Not set':'未记录','Recorded':'已记录','Partial':'部分交付'};
  const classificationNames = {'Not set':'未设置','True positive':'真实威胁','Informational':'信息性 / 预期活动','False positive':'误报'};
  const verdictNames = {Malicious:'恶意',Suspicious:'可疑',Clean:'未发现威胁'};
  let store;
  try { const saved = JSON.parse(localStorage.getItem(STORAGE_KEY)); store = saved?.version === 1 && Array.isArray(saved.alerts) && saved.alerts.length ? saved : window.makeDemoData(); }
  catch { store = window.makeDemoData(); }
  const ui = {tables:{},drawer:null,modal:null,drawerTab:'overview',assetType:'device',evidenceType:'all',graph:{selected:'u1',alert:null,zoom:1,grouped:true,layout:'spread',hidden:new Set(),severity:'',status:'',source:'',blast:false,index:99},playing:null,caseCollapsed:false,feedback:null};
  const fixture=window.makeDemoData();
  for(const key of ['incidents','alerts','cases']){const known=new Set(store[key].map(x=>x.id));store[key].push(...fixture[key].filter(x=>!known.has(x.id)));}
  window.mergeReplayedAlerts?.(store);
  window.mergeAiSoc20Data?.(store);window.mergePersistedCaseData?.(store);
  window.alertFlowWorkspace?.merge(store);
  // Update this fixture's old timestamp without replacing user edits or associations.
  const unlinkedSample=store.alerts.find(a=>a.id==='alert-unassigned-case-001');
  if(unlinkedSample?.event_time==='2026-10-24T03:20:00Z'){
    const seed=fixture.alerts.find(a=>a.id===unlinkedSample.id);
    for(const key of ['first','last','event_time'])unlinkedSample[key]=seed[key];
    const material=unlinkedSample.detailMaterial;
    if(material){
      if(material.raw)material.raw.event_time=seed.event_time;
      if(material.explanation)material.explanation.generatedAt=seed.last;
      const offsets={'告警发生':0,'告警被检测到':15,'告警入库':25};
      for(const entry of material.history||[])if(Object.hasOwn(offsets,entry.title))entry.time=new Date(Date.parse(seed.event_time)+offsets[entry.title]*1000).toISOString();
    }
  }
  for(const inc of store.incidents){const seed=fixture.incidents.find(x=>x.id===inc.id);for(const k of ['first','last','updated'])if(!inc[k])inc[k]=seed?.[k];if(inc.classification==='未分类')inc.classification='Not set';if(inc.classification==='真实威胁')inc.classification='True positive';}
  for(const c of store.cases){c.updated ||= c.created;c.tags ||= c.critical?['关键资产']:[];}
  const assetTagFixture={d1:['Web 服务器'],d2:['文件服务器'],d3:['Windows 域控'],c1:['财务存储']};
  function seedAssetTags(){for(const asset of store.assets){asset.tags ||= assetTagFixture[asset.id]||[];if(!store.assetRoleTagsVersion&&['d1','d2','d3'].includes(asset.id)){const roles=['运控','Windows 域控','文件服务器','Web 服务器'];asset.tags=[...new Set([...asset.tags.filter(t=>!roles.includes(t)),...assetTagFixture[asset.id]])];}}store.assetRoleTagsVersion=1;}
  seedAssetTags();
  const tableContexts = new Map();
  const getAlert = id => store.alerts.find(a=>a.id===id);
  const getAsset = id => store.assets.find(a=>a.id===id);
  const currentRoute = () => {
    const [path,search='']=location.hash.replace(/^#\/?/,'').split('?');
    const [page='alerts',id='',tab='']=path.split('/');
    return {page:['alerts','incidents','cases','assets','investigations'].includes(page)?page:'alerts',id,tab,search};
  };
  const currentIncident = () => store.incidents.find(x=>x.id===currentRoute().id) || store.incidents[0];
  const currentCase = () => store.cases.find(x=>x.id===currentRoute().id) || store.cases[0];
  function save(){ try {localStorage.setItem(STORAGE_KEY,JSON.stringify(store));} catch {toast('当前浏览器无法持久保存，操作在本次预览中有效');} }
  function toast(message){const el=$('#toast');el.textContent=message;el.classList.add('visible');clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove('visible'),3200);}
  function navigate(hash){if(location.hash===hash){ui.drawer=null;ui.modal=null;render();}else location.hash=hash;}
  function date(v, brief=false){if(!v)return '未记录';return new Date(v).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',...(brief?{}:{year:'numeric'})}).replace(/\//g,'-');}
  function severity(v){if(!v)return '<span class="muted">—</span>';return `<span class="severity ${v==='高'?'high':v==='中'?'medium':'low'}"><span class="severity-bars"><i></i><i></i><i></i></span>${esc(v)}</span>`;}
  function state(v){return `<span class="state"><i class="dot ${esc(v.replaceAll(' ','-'))}"></i>${esc(stateNames[v]||v)}</span>`;}
  function avatar(v){return `<span class="avatar" aria-hidden="true">${v==='未分配'?'—':esc(v.split(' ').map(x=>x[0]).slice(0,2).join(''))}</span>`;}
  function badge(text,color=''){return `<span class="badge ${color}">${esc(text)}</span>`;}
  function btn(text,action,id='',cls='',icon=''){return `<button type="button" class="button ${cls}" data-action="${action}" data-id="${esc(id)}">${icon?I(icon,15):''}${esc(text)}</button>`;}
  function iconBtn(name,label,action,id='',cls=''){return `<button type="button" class="icon-button ${cls}" aria-label="${esc(label)}" title="${esc(label)}" data-action="${action}" data-id="${esc(id)}">${I(name,17)}</button>`;}
  function empty(title='没有符合条件的结果',subtitle='请调整筛选条件后重试。'){return `<div class="empty">${I('search',30)}<strong>${esc(title)}</strong><p>${esc(subtitle)}</p></div>`;}
  function keyInfo(label,value){return `<div><div class="info-label">${esc(label)}</div><div class="info-value">${value}</div></div>`;}
  function entityChip(a){return a?`<button class="link-button row" data-action="entity" data-id="${a.id}"><span class="entity-icon ${a.type}">${I(a.type,16)}</span><span class="ellipsis">${esc(a.name)}</span></button>`:'—';}
  function alertAssetLink(a){if(a?.inventory===false)return `<span class="row"><span class="entity-icon ${esc(a.type)}">${I(a.type,16)}</span><span class="ellipsis">${esc(a.name)}</span></span>`;return a?`<a class="asset-detail-link row" href="#/assets/${encodeURIComponent(a.id)}"><span class="entity-icon ${esc(a.type)}">${I(a.type,16)}</span><span class="ellipsis">${esc(a.name)}</span></a>`:'—';}
  function assetPage(){const asset=getAsset(currentRoute().id);return `<section class="page"><h1>资产详情${asset?' · '+esc(asset.name):''}</h1></section>`;}
  function incidentAlerts(inc=currentIncident()){return store.alerts.filter(a=>a.incidentId===inc.id);}
  const savedCase = c => !!(c?.localCollection||c?.recordedCase);
  const caseSource = c => c.alertFlowCollection?'AiSOC · 当前流程':c.recordedCase?'AiSOC · 历史联合调查':c.localCollection?'AiSOC · 历史自动调查':'原设计案例';
  const orderedCases = () => store.cases.slice().sort((a,b)=>Number(savedCase(b))-Number(savedCase(a))||(savedCase(a)?Date.parse(b.created)-Date.parse(a.created):0));
  const caseIncidents = c => store.incidents.filter(i=>{
    if(savedCase(c)&&(i.sourceTenantId!==c.sourceTenantId||i.sourceEnvironment!==c.sourceEnvironment))return false;
    return store.alerts.some(a=>{
      if(!c.alertIds.includes(a.id)||a.incidentId!==i.id)return false;
      if(!i.sourceTenantId)return true;
      if(a.sourceTenantId||a.sourceEnvironment)return a.sourceTenantId===i.sourceTenantId&&a.sourceEnvironment===i.sourceEnvironment;
      // Replay alert fields predate source metadata; use the exact saved group projection.
      return (window.alertFlowData?.incidents||[]).some(source=>source.id===i.id&&source.sourceTenantId===i.sourceTenantId&&source.sourceEnvironment===i.sourceEnvironment&&source.sourceAlertIds.includes(a.id));
    });
  });
  function caseAlerts(c=currentCase()){return c.alertIds.map(getAlert).filter(Boolean);}
  function scopeAlerts(){return currentRoute().page==='cases'?caseAlerts():incidentAlerts();}
  function scopeEntities(){const ids=new Set(scopeAlerts().flatMap(a=>a.entityIds));return store.assets.filter(a=>ids.has(a.id));}
  function scopeEvidence(){const ids=new Set(scopeAlerts().map(a=>a.id));return store.evidence.filter(e=>ids.has(e.alertId));}
  function scopeActivities(){
    const r=currentRoute(),local=store.activities.filter(a=>r.page==='cases'?a.caseIds?.includes(currentCase().id):a.incidentId===currentIncident().id);
    const saved=r.page==='incidents'?window.alertFlowWorkspace?.activities(currentIncident(),scopeAlerts(),window.investigationWorkspaceModel.forAlerts(store,scopeAlerts()))||[]:r.page==='cases'?window.alertFlowWorkspace?.caseActivities(store,currentCase(),window.investigationWorkspaceModel.forCase(store,currentCase()))||[]:[];
    return [...local,...saved].sort((a,b)=>Date.parse(b.time)-Date.parse(a.time));
  }
  function logActivity(title,type,target,incidentId,caseIds){store.activities.unshift({id:`act-${Date.now()}-${Math.random().toString(36).slice(2,6)}`,title,type,target,performedBy:'Alex Wilber',trigger:'人工',status:'Completed',time:new Date().toISOString(),incidentId:incidentId||currentIncident().id,caseIds:caseIds||(currentRoute().page==='cases'?[currentCase().id]:[])});}
  function tableState(key){return ui.tables[key] ||= {query:'',severity:'',status:'',source:'',sort:key==='alerts'?'event_time':'',direction:key==='alerts'?-1:1,page:1,size:8,selected:[],columns:null,start:'',end:'',owner:'',tag:'',minPriority:'',priorityBand:'',classification:'',investigation:'',category:'',range:'7'};}
  const alertColumns = [
    {key:'title',label:'告警名称',render:a=>`<button class="cell-link alert-title" title="${esc(a.title)}" data-action="alert" data-id="${a.id}">${esc(a.title)}</button>`},
    {key:'tags',label:'标签',render:a=>a.tags.map(t=>badge(t,t==='关键资产'?'purple':'')).join(' ')||'<span class="muted">—</span>'},
    {key:'severity',label:'严重程度',render:a=>severity(a.severity)},
    {key:'investigation',label:'调查状态',render:a=>state(a.investigation)},
    {key:'status',label:'处理状态',render:a=>state(a.status)},
    {key:'category',label:'类别',render:a=>esc(a.category)},
    {key:'classification',label:'分类',render:a=>esc(classificationNames[a.classification]||a.classification)},
    {key:'source',label:'检测源',render:a=>`<span title="${esc(a.source)}">${esc(a.source.replace('Microsoft ','').replace('Defender for ',''))}</span>`},
    {key:'asset',label:'受影响资产',render:a=>esc(getAsset(a.entityIds[0])?.name)},
    {key:'first',label:'首次活动',render:a=>date(a.first,true)},
    {key:'last',label:'末次活动',render:a=>date(a.last,true)},
    {key:'owner',label:'负责人',render:a=>esc(a.owner)},
  ];
  const alertListLayout=[['title',360],['severity',112],['event_time',140],['assetTags',150],['status',112],['category',150],['source',180],['asset',160],['owner',150]];
  const alertListColumns=alertListLayout.map(([key,width])=>{
    const original=alertColumns.find(c=>c.key===(key==='event_time'?'first':key==='assetTags'?'tags':key));
    const column=key==='event_time'?{key,label:'告警时间',render:a=>date(a.event_time,true)}:key==='assetTags'?{key,label:'资产标签',render:a=>a.assetTags.map(t=>badge(t)).join(' ')||'—'}:original;
    return {...column,...(key==='asset'?{render:a=>{const asset=getAsset(a.entityIds[0]);if(asset?.inventory===false)return esc(asset.name);return asset?`<a class="cell-link" href="#/assets/${encodeURIComponent(asset.id)}" title="${esc(asset.name)}">${esc(asset.name)}</a>`:'—';}}:{}),width,sortable:['severity','event_time'].includes(key)};
  });
  function filteredRows(key,rows){
    const t=tableState(key),q=t.query.trim().toLowerCase();
    const timeField=tableContexts.get(key)?.opts.timeField||'first',tagField=tableContexts.get(key)?.opts.tagField||'tags';
    const bound=v=>Date.parse(/(?:Z|[+-]\d{2}:\d{2})$/.test(v)?v:v+'+08:00');
    let result=rows.filter(row=>(key!=='cases'||!t.dataset||t.dataset==='all'||(t.dataset==='aisoc'?savedCase(row):!savedCase(row)))&&(!q||JSON.stringify(row).toLowerCase().includes(q))&&(!t.severity||row.severity===t.severity)&&(!t.status||row.status===t.status)&&(!t.source||row.source===t.source||row.sources?.includes(t.source))&&(!t.owner||row.owner===t.owner)&&(!t.tag||row[tagField]?.includes(t.tag))&&(!t.minPriority||(Number.isFinite(row.priority)&&row.priority>=Number(t.minPriority)))&&(!t.start||!row[timeField]||Date.parse(row[timeField])>=bound(t.start))&&(!t.end||!row[timeField]||Date.parse(row[timeField])<=bound(t.end)));
    result=result.filter(row=>(!t.priorityBand||(Number.isFinite(row.priority)&&(t.priorityBand==='top'?row.priority>85:t.priorityBand==='medium'?row.priority>=15&&row.priority<=85:row.priority<15)))&&(!t.classification||row.classification===t.classification)&&(!t.investigation||row.investigation===t.investigation)&&(!t.category||row.category===t.category));
    if(t.sort)result=result.slice().sort((a,b)=>{
      if(t.sort==='severity')return (({高:3,中:2,低:1}[a.severity]||0)-({高:3,中:2,低:1}[b.severity]||0))*t.direction;
      return String(a[t.sort]??'').localeCompare(String(b[t.sort]??''),'zh-CN',{numeric:true})*t.direction;
    });
    return result;
  }
  function alertQuickFilters(key){
    const t=tableState(key);
    const group=(field,label,all,values)=>`<div class="quick-filter-group" role="group" aria-label="${label}快捷筛选">${[['',all],...values].map(([value,text])=>`<button type="button" class="quick-filter ${t[field]===value?'selected':''}" aria-pressed="${t[field]===value}" data-action="quick-filter" data-key="${key}" data-field="${field}" data-value="${esc(value)}">${esc(text)}</button>`).join('')}</div>`;
    return `<div class="alert-quick-filters">${group('severity','严重程度','全部级别',['高','中','低'].map(v=>[v,v]))}<span class="quick-filter-divider" aria-hidden="true"></span>${group('status','处理状态','全部状态',['New','In progress','Resolved'].map(v=>[v,stateNames[v]]))}<span class="quick-filter-divider" aria-hidden="true"></span>${group('owner','负责人','全部告警',[[CURRENT_USER_NAME,'分配给我']])}</div>`;
  }
  function table(key,rows,columns,opts={}){
    tableContexts.set(key,{rows,columns,opts});
    const t=tableState(key),validIds=new Set(rows.map(r=>r.id));t.selected=t.selected.filter(id=>validIds.has(id));
    const manageable=!!opts.managementAction||rows.some(r=>getAlert(r.id));
    const all=filteredRows(key,rows),pages=Math.max(1,Math.ceil(all.length/t.size));t.page=Math.min(t.page,pages);
    const slice=all.slice((t.page-1)*t.size,t.page*t.size),shown=t.columns?t.columns.map(k=>columns.find(c=>c.key===k)).filter(Boolean):columns;
    const fixed=key==='alerts';
    const tableWidth=40+shown.reduce((sum,c)=>sum+(c.width||150),0);
    const headers=shown.map(c=>{
      if(!fixed)return `<th><button data-action="sort" data-key="${key}" data-field="${c.key}">${esc(c.label)}${I('down',11)}</button></th>`;
      if(!c.sortable)return `<th scope="col">${esc(c.label)}</th>`;
      const active=t.sort===c.key,ascending=t.direction===1;
      const icon=active?(ascending?'↑':'↓'):'↕';
      const next=active&&!ascending?'升序':active?'降序':'升序';
      return `<th scope="col" aria-sort="${active?(ascending?'ascending':'descending'):'none'}"><button data-action="sort" data-key="${key}" data-field="${c.key}" title="按${esc(c.label)}${next}排列">${esc(c.label)}<span class="sort-indicator ${active?'active':''}" aria-hidden="true">${icon}</span></button></th>`;
    }).join('');
    const selected=rows.filter(r=>t.selected.includes(r.id));
    const chips=[['severity','严重程度',t.severity],['status','状态',stateNames[t.status]],['source','来源',t.source],['start','开始',t.start?.replace('T',' ')],['end','结束',t.end?.replace('T',' ')],['owner','负责人',t.owner],['tag','标签',t.tag],['minPriority','优先级 ≥',t.minPriority]].filter(x=>x[2]);
    return `<div class="table-card" data-table="${key}">
      ${opts.caseQueue?caseQueueToolbar(all.length):`<div class="toolbar">${btn('刷新','refresh',key,'quiet','refresh')}${btn('导出','export',key,'quiet','download')}${opts.copyLink?btn('复制列表链接','copy-queue-link',key,'quiet','link'):''}${opts.dates?btn(t.start?'自定义范围':'最近 7 天','date-filter',key,'quiet','calendar'):''}${selected.length&&manageable?btn(`管理所选 (${selected.length})`,opts.managementAction||'bulk-manage',key,'small','edit'):''}<span class="spacer"></span><span class="table-tools-count">${all.length} ${opts.unit||'项'}</span><label class="search-input">${I('search',15)}<input id="query-${key}" data-query="${key}" type="search" value="${esc(t.query)}" placeholder="${opts.placeholder||'搜索名称或 ID'}" aria-label="${esc(opts.searchLabel||'搜索'+(opts.unit||'记录'))}"></label>${btn('自定义列','columns',key,'quiet','columns')}</div>`}
      ${opts.caseQueue?caseQueueFilters():opts.filter!==false?`<div class="filterbar ${opts.quickFilters?'alert-quick-filterbar':''}" style="padding:10px 15px">${opts.quickFilters?alertQuickFilters(key):''}${chips.filter(x=>!opts.quickFilters||(!['severity','status'].includes(x[0])&&!(x[0]==='owner'&&t.owner===CURRENT_USER_NAME))).map(([field,label,value])=>`<span class="filter-chip">${esc(label)}: <b>${esc(value)}</b><button aria-label="移除${esc(label)}筛选" data-action="remove-filter" data-key="${key}" data-field="${field}">${I('close',12)}</button></span>`).join('')}${btn('添加筛选','filter',key,'quiet small','filter')}${chips.length||t.query?btn('重置全部','clear-filters',key,'quiet small'):''}</div>`:''}
      <div class="table-scroll"><table class="data-table ${fixed?'alert-fixed-table':''}" ${fixed?`style="width:${tableWidth}px;min-width:100%"`:''}>${fixed?`<colgroup><col style="width:40px">${shown.map(c=>`<col style="width:${c.width}px">`).join('')}</colgroup>`:''}<thead><tr><th class="check-cell"><input type="checkbox" aria-label="选择本页全部" data-select-all="${key}" ${slice.length&&slice.every(r=>t.selected.includes(r.id))?'checked':''}></th>${headers}</tr></thead><tbody>${slice.map(row=>`<tr class="${t.selected.includes(row.id)?'selected':''}" ${opts.rowPreview?`data-preview-id="${row.id}" data-preview-type="${opts.rowPreview===true?'incident':opts.rowPreview}" tabindex="0"`:''}><td class="check-cell"><input type="checkbox" data-select-row="${key}" data-id="${row.id}" aria-label="选择 ${esc(row.title||row.name||row.id)}" ${t.selected.includes(row.id)?'checked':''}></td>${shown.map(c=>`<td>${c.render?c.render(row):esc(row[c.key])}</td>`).join('')}</tr>`).join('')}</tbody></table>${!all.length?empty():''}</div>
      <div class="table-footer"><span>${all.length?`${(t.page-1)*t.size+1}–${Math.min(t.page*t.size,all.length)}`:'0'} / ${all.length} 项${selected.length?` · 已选择 ${selected.length} 项`:''}</span><div class="row"><label>每页 <select data-page-size="${key}" aria-label="每页条数">${[8,15,25].map(n=>`<option ${n===t.size?'selected':''}>${n}</option>`).join('')}</select></label>${iconBtn('arrow','上一页','prev-page',key)}<span>${t.page} / ${pages}</span><button class="icon-button" aria-label="下一页" data-action="next-page" data-id="${key}" ${t.page>=pages?'disabled':''}>${I('chevron',15)}</button></div></div></div>`;
  }
  function shell(content){
    const r=currentRoute(),compact=r.page==='cases'&&!!r.id;
    const nav=(title,ico,page,href,count)=>`<a class="nav-item ${r.page===page?'selected':''}" href="${href}" ${r.page===page?'aria-current="page"':''} title="${title}">${I(ico,19)}<span class="nav-label">${title}</span><span class="short-label">${title}</span>${count?`<span class="nav-count">${count}</span>`:''}</a>`;
    const stub=(title,ico)=>`<div class="nav-item dim" title="${title} · 本原型仅展示名称">${I(ico,18)}<span class="nav-label">${title}</span><span class="short-label">${title}</span></div>`;
    return `<header class="topbar"><span class="row"><img class="aisoc-mark" src="./assets/aisoc-mark.svg" alt=""><span class="topbar-title">AiSOC</span></span><div class="top-search" aria-hidden="true">${I('search',15)}<span>搜索安全资源、实体和文档</span></div><div class="topbar-actions"><span class="environment">Contoso</span>${iconBtn('bell','通知（仅展示）','stub')}${iconBtn('help','帮助（仅展示）','stub')}${iconBtn('settings','设置（仅展示）','stub')}<span class="avatar" title="Alex Wilber">AW</span></div></header>
      <div class="layout"><aside class="sidebar ${compact?'compact':''}" aria-label="全局导航">${stub('主页','home')}<div class="side-heading">告警和事件</div>${nav('告警','shield','alerts','#/alerts',store.alerts.filter(a=>a.status!=='Resolved').length)}${nav('事件','graph','incidents','#/incidents',store.incidents.filter(i=>i.status!=='Resolved').length)}<div class="side-heading">案件管理</div>${nav('Cases','briefcase','cases','#/cases',store.cases.filter(c=>c.status!=='Resolved').length)}<div class="side-heading">安全运营</div>${stub('高级搜寻','search')}${stub('资产','device')}${stub('威胁情报','flag')}${stub('Microsoft Sentinel','cloud')}<div class="side-heading">管理</div>${stub('报表','file')}${stub('设置','settings')}<div class="side-bottom">${btn('重置数据','reset','','quiet small','refresh')}<p></p></div></aside><main class="workspace" id="main-content">${content}</main></div>${drawerMarkup()}${modalMarkup()}`;
  }
  function breadcrumbs(items){return `<nav class="breadcrumbs" aria-label="面包屑">${items.map((x,i)=>`${i?I('chevron',10):''}${x.href?`<a href="${x.href}">${esc(x.label)}</a>`:`<span>${esc(x.label)}</span>`}`).join('')}</nav>`;}
  function alertsPage(){
    const r=currentRoute(),a=getAlert(r.id);
    if(a)return fullAlert(a);
    // The legacy fixture's first timestamp serves as mock occurrence time only in this list.
    const rows=store.alerts.map(alert=>({...alert,event_time:alert.event_time??alert.first,assetTags:[...new Set(alert.entityIds.flatMap(id=>getAsset(id)?.tags||[]))]}));
    return `<section class="page">${breadcrumbs([{label:'告警和事件'},{label:'告警'}])}<div class="title-line"><div><h1>告警</h1><p class="page-subtitle">查看、调查和管理来自所有安全产品的告警</p></div><div class="page-top-actions">${btn('管理告警','bulk-manage','alerts','quiet','edit')}</div></div><div class="page-stats">${[['全部告警',store.alerts.length],['高严重程度',store.alerts.filter(a=>a.severity==='高').length],['待处理',store.alerts.filter(a=>a.status==='New').length],['调查进行中',store.alerts.filter(a=>a.investigation==='In progress').length]].map(([label,n])=>`<div class="stat"><div class="stat-number">${n}</div><div class="stat-label">${label}</div></div>`).join('')}</div>${table('alerts',rows,alertListColumns,{dates:true,quickFilters:true,timeField:'event_time',tagField:'assetTags',unit:'条告警',searchLabel:'搜索告警'})}<div class="row muted" style="font-size:10px;margin-top:13px">${I('info',13)}时间显示为 UTC+08:00 · </div></section>`;
  }
  function tabsMarkup(tabs,active,page,id){return `<div class="tabs" role="tablist">${tabs.map(([key,label,n])=>`<a class="tab ${active===key?'selected':''}" role="tab" aria-selected="${active===key}" href="#/${page}/${id}/${key}">${label}${n!==undefined?`<span class="tab-count">(${n})</span>`:''}</a>`).join('')}</div>`;}
  function incidentQueue(){
    const rows=store.incidents.slice().sort((a,b)=>Number(!!b.recordedIncident)-Number(!!a.recordedIncident)).map(inc=>{
      const linked=incidentAlerts(inc),sources=[...new Set(linked.map(a=>a.source))];
      return {...inc,sources,source:sources[0]||'Microsoft Defender XDR',alertCount:linked.length,activeCount:linked.filter(a=>a.status!=='Resolved').length,assetCount:new Set(linked.flatMap(a=>a.entityIds)).size,investigation:linked.length&&linked.every(a=>a.investigation==='Completed')?'Completed':'In progress'};
    });
    const columns=[
      {key:'title',label:'事件名称',render:r=>`<div class="row">${iconBtn('chevron','预览事件 '+r.id,'incident-preview',r.id)}<a href="#/incidents/${r.id}/summary" class="incident-name" title="${esc(r.title)}">${esc(r.title)}</a></div>`},
      {key:'id',label:'事件 ID'},
      {key:'priority',label:'优先级',render:r=>`<button class="priority-pill ${r.priority>=80?'high':''}" data-action="incident-preview" data-id="${r.id}" title="查看优先级评估">${r.priority??'—'} ${I('info',11)}</button>`},
      {key:'tags',label:'标签',render:r=>r.tags.map(t=>badge(t,t==='关键资产'?'purple':'')).join(' ')||'—'},
      {key:'severity',label:'严重程度',render:r=>severity(r.severity)},
      {key:'status',label:'状态',render:r=>state(r.status)},
      {key:'classification',label:'分类',render:r=>esc(classificationNames[r.classification]||r.classification)},
      {key:'owner',label:'负责人',render:r=>`<span class="row">${avatar(r.owner)}${esc(r.owner)}</span>`},
      {key:'activeCount',label:'活跃 / 全部告警',render:r=>`${r.activeCount} / ${r.alertCount}`},
      {key:'assetCount',label:'涉及对象',render:r=>`${r.assetCount} 项对象`},
      {key:'source',label:'服务 / 检测源',render:r=>`<span title="${esc(r.sources.join(', '))}">${esc(r.sources.map(x=>x.replace('Microsoft ','').replace('Defender for ','')).join(', '))}</span>`},
      {key:'updated',label:'最近更新时间',render:r=>date(r.updated||r.last)},
    ];
    const disruption=store.incidents.filter(i=>i.tags.includes('Attack Disruption')).length;
    const actual=window.alertFlowWorkspace?.metrics(store),hasActual=!!actual?.alerts;
    const memberIds=new Set(store.incidents.flatMap(i=>incidentAlerts(i).map(a=>a.id)));
    const reduction=hasActual?actual.reduction:memberIds.size?Math.round((1-store.incidents.length/memberIds.size)*100):null;
    return `<section class="page incident-queue">${breadcrumbs([{label:'告警和事件'},{label:'事件'}])}<div class="title-line"><div><h1>事件</h1><p class="page-subtitle">汇聚告警与关联线索，按优先级开展调查</p></div><div class="page-top-actions">${btn('管理事件','bulk-incidents','incidents','quiet','edit')}</div></div><div class="queue-overview"><article class="queue-metric"><div class="row between"><span>攻击中断</span>${I('shield',17)}</div><b>${hasActual?'—':disruption}</b><small>${hasActual?'尚无可核验的自动中断记录':'个事件已自动中断'}</small></article><article class="queue-metric"><div class="row between"><span>队列压缩</span>${I('graph',17)}</div><b>${reduction==null?'—':reduction+'%'}</b><small>${hasActual?`${actual.alerts} 条流程告警归为 ${actual.groups} 个事件`:`${memberIds.size} 条成员告警 · ${store.incidents.length} 个事件`}</small></article><div class="queue-inline-stats"><span><b>${store.incidents.filter(i=>['New','In progress'].includes(i.status)).length}</b> 活跃事件</span><span><b>${store.incidents.filter(i=>i.owner==='未分配').length}</b> 待分配</span>${hasActual?`<span><b>${store.incidents.filter(i=>i.status==='Not set').length}</b> 状态未记录</span>`:''}</div></div>${table('incidents',rows,columns,{dates:true,copyLink:true,unit:'个事件',searchLabel:'搜索事件',rowPreview:true,managementAction:'bulk-incidents'})}<p class="muted" style="margin-top:12px;font-size:11px">点击事件名称进入事件详情，点击行或箭头预览事件摘要。</p></section>`;
  }
  function incidentHeader(inc){return `<div class="page-header">${breadcrumbs([{label:'告警和事件'},{label:'事件',href:'#/incidents'},{label:inc.id}])}<div class="title-line"><div><h1>ID ${inc.id}: ${esc(inc.title)}</h1></div><div class="page-top-actions">${btn('管理事件','manage-incident',inc.id,'quiet','edit')}${iconBtn('list','切换事件','choose-incident')}</div></div><div class="metadata"><button class="row" data-action="manage-incident" data-id="${inc.id}">${severity(inc.severity)}</button><button data-action="manage-incident" data-id="${inc.id}">${state(inc.status)}</button><button class="row" data-action="manage-incident" data-id="${inc.id}">${avatar(inc.owner)}${esc(inc.owner)}</button><span class="muted">${esc(classificationNames[inc.classification]||inc.classification)}</span><span class="row muted" style="font-size:11px">${I('clock',14)}最近更新：${date(inc.updated||inc.last)}</span>${inc.tags.map(t=>badge(t,t==='关键资产'?'purple':'')).join('')}${store.cases.filter(c=>caseIncidents(c).some(i=>i.id===inc.id)).map(c=>`<a class="button small" href="#/cases/${c.id}/overview">Case · ${esc(c.title)}</a>`).join('')}</div></div>`;}
  function incidentPage(){
    if(!currentRoute().id)return incidentQueue();
    if(!store.incidents.some(i=>i.id===currentRoute().id))return `<section class="page">${empty('未找到该事件','当前数据中没有这个事件，请返回列表选择。')}<a class="button" href="#/incidents">返回事件列表</a></section>`;
    const inc=currentIncident(),tab=currentRoute().tab||'summary',alerts=incidentAlerts(inc),evidence=scopeEvidence();
    const tabs=[['summary','事件概览'],['alerts','成员告警',alerts.length],['triage','基础调查'],['attack','关联关系'],['chain','关联告警链'],['assets','涉及对象',scopeEntities().length],['investigations','关联 AI 调查',window.investigationWorkspaceModel.forAlerts(store,alerts).length],['evidence','证据与处置',inc.recordedIncident?undefined:evidence.length],['activities','处理活动',scopeActivities().length],['similar','相似事件',window.referenceWorkspaces.relatedIncidents(store,alerts,[inc.id]).length]];
    let content=tab==='summary'?investigationView.incidentOverview():tab==='context'?`<div class="section-title"><h2>事件资料概况</h2><a class="button small" href="#/incidents/${inc.id}/summary">返回事件概览</a></div>`+summaryView():tab==='triage'?investigationView.basicInvestigations():tab==='chain'?investigationView.incidentChain():tab==='attack'?(inc.recordedIncident?investigationView.incidentRelations():`<div class="iv-root iv-context-caption"><h2>事件关联关系</h2><p>查看成员告警与对象之间的已有关联，筛选和聚焦不改变事件成员。</p></div>`+attackWorkspace()):tab==='alerts'?table('incident-alerts',alerts,alertColumns,{unit:'条告警',dates:true}):tab==='activities'?activitiesView():tab==='assets'?assetsView():tab==='investigations'?investigationsView():tab==='evidence'?evidenceView():tab==='similar'?similarView():recommendationsView();
    return `${incidentHeader(inc)}${tabsMarkup(tabs,tab==='context'?'summary':tab,'incidents',inc.id)}<section class="content-pane">${content}</section>`;
  }
  function activityColumns(){return [
    {key:'time',label:'活动开始时间',render:a=>date(a.time)},
    {key:'title',label:'标题',render:a=>`<button class="cell-link" data-action="activity" data-id="${a.id}">${esc(a.title)}</button>`},
    {key:'type',label:'类型',render:a=>badge(a.type,a.trigger==='自动'?'green':'blue')},
    {key:'target',label:'目标'},{key:'performedBy',label:'执行者'},{key:'trigger',label:'触发方式'},
    {key:'status',label:'活动状态',render:a=>state(a.status)},
  ];}
  function activitiesView(){return `<div class="section-title"><div><h2>活动</h2><p class="section-subtitle">${currentRoute().page==='cases'&&savedCase(currentCase())?'已有告警与调查的来源记录，以及本地案件操作；历史调查可早于本地整理时间。':'查看事件中的人工与自动操作，以及每一步的执行结果'}</p></div>${badge('人工与自动','blue')}</div>${table('activities',scopeActivities(),activityColumns(),{unit:'条活动',searchLabel:'搜索活动'})}`;}
  function assetsView(){
    const all=scopeEntities(),selected=ui.assetType,rows=selected==='all'?all:all.filter(a=>a.type===selected);
    const columns=[{key:'name',label:'资产名称',render:a=>entityChip(a)},{key:'risk',label:'风险等级',render:a=>a.risk?severity(a.risk):'—'},{key:'domain',label:'域 / 来源',render:a=>esc(a.domain||a.provider||a.department||(a.inventory===false?'—':'Contoso'))},{key:'type',label:'类型',render:a=>esc(typeNames[a.type])},{key:'id',label:'资产 ID',render:a=>a.inventory===false?'未关联库存':`<span class="mono">asset-${esc(a.id)}-20261024</span>`}];
    return `<div class="section-title"><div><h2>资产</h2><p class="section-subtitle">调查范围内的设备、身份与资源</p></div></div><div class="asset-layout"><div class="asset-categories">${[['all','全部资产','grid'],...Object.entries(typeNames).map(([t,n])=>[t,n,t])].map(([type,name,ico])=>`<button class="asset-category ${selected===type?'selected':''}" data-action="asset-type" data-id="${type}">${I(ico,17)}${name}<span class="count">${type==='all'?all.length:all.filter(a=>a.type===type).length}</span></button>`).join('')}</div><div class="asset-content"><h3>${selected==='all'?'全部资产':typeNames[selected]} (${rows.length})</h3>${table('assets-'+selected,rows,columns,{unit:'项资产',filter:false,searchLabel:'搜索资产'})}</div></div>`;
  }
  function evidenceView(){
    if(currentRoute().page==='cases'&&savedCase(currentCase()))return investigationView.flowCaseMaterials();
    if(currentRoute().page==='incidents'&&currentIncident().recordedIncident)return investigationView.incidentMaterials();
    const all=scopeEvidence(),types=[...new Set(all.map(e=>e.type))],rows=ui.evidenceType==='all'?all:all.filter(e=>e.type===ui.evidenceType);
    const columns=[{key:'name',label:'实体 / 证据',render:e=>`<button class="cell-link" data-action="evidence" data-id="${e.id}">${esc(e.name)}</button>`},{key:'type',label:'实体类型'},{key:'verdict',label:'判定',render:e=>badge(verdictNames[e.verdict],e.verdict==='Malicious'?'red':e.verdict==='Suspicious'?'amber':'green')},{key:'remediation',label:'处置状态',render:e=>state(e.remediation)},{key:'origin',label:'检测来源'},{key:'threat',label:'威胁'}];
    return `<div class="section-title"><div><h2>${currentRoute().page==='cases'?'案件证据':'证据与处置'}</h2><p class="section-subtitle">当前成员告警关联的证据及已有处置记录；本次 AI 查询材料在调查详情内查看</p></div>${badge(`${all.filter(e=>e.remediation==='Pending approval').length} 项待审批`,'amber')}${currentRoute().page==='incidents'?`<a class="button small" href="#/incidents/${currentRoute().id}/recommendations">查看已有处置建议</a>`:''}</div><div class="asset-layout"><div class="asset-categories">${['all',...types].map(type=>`<button class="asset-category ${ui.evidenceType===type?'selected':''}" data-action="evidence-type" data-id="${type}">${I(type==='all'?'grid':'file',16)}${type==='all'?'全部证据':esc(type)}<span class="count">${type==='all'?all.length:all.filter(e=>e.type===type).length}</span></button>`).join('')}</div><div class="asset-content">${table('evidence-'+ui.evidenceType,rows,columns,{unit:'条证据',filter:false,searchLabel:'搜索证据'})}</div></div>`;
  }
  function investigationsView(){return currentRoute().page==='cases'&&new URLSearchParams(currentRoute().search).has('run')?investigationView.workbench():investigationView.linkedRuns();}
  function summaryView(){
    const inc=currentRoute().page==='cases'?store.incidents.find(x=>x.id===currentCase().incidentId):currentIncident(),alerts=scopeAlerts(),entities=scopeEntities(),ev=scopeEvidence();
    const tacticCounts=Object.entries(alerts.reduce((m,a)=>(m[a.category]=(m[a.category]||0)+1,m),{}));
    return `<div class="summary-grid"><article class="card summary-card"><div class="card-title"><h3>告警与攻击阶段</h3>${I('info',13)}</div><div class="mini-stat-row"><div><b>${alerts.filter(a=>a.status!=='Resolved').length}/${alerts.length}</b><span class="kpi-note">活跃告警</span></div><div><b>${tacticCounts.length}</b><span class="kpi-note">MITRE ATT&CK 阶段</span></div></div>${tacticCounts.slice(0,5).map(([n,c])=>`<div class="tactic"><div class="row between"><span>${esc(n)}</span><span>${c}/${alerts.length}</span></div><div class="bar-track"><i style="width:${c/Math.max(alerts.length,1)*100}%"></i></div></div>`).join('')}<button class="card-link" data-action="to-tab" data-id="alerts">查看全部告警 ${I('chevron',12)}</button></article><article class="card summary-card"><div class="card-title"><h3>影响范围</h3></div><div class="mini-stat-row"><div><b>${entities.filter(a=>a.type==='device').length}</b><span class="kpi-note">受影响设备</span></div><div><b>${entities.filter(a=>a.type==='user').length}</b><span class="kpi-note">受影响用户</span></div></div>${entities.slice(0,5).map(a=>`<div class="entity-list-item">${entityChip(a)}<span class="spacer"></span>${severity(a.risk)}</div>`).join('')}<button class="card-link" data-action="to-tab" data-id="assets">查看资产 ${I('chevron',12)}</button></article><article class="card summary-card"><div class="card-title"><h3>告警时间线</h3></div>${alerts.slice(0,4).map(a=>`<div class="timeline-item"><span class="timeline-dot" style="background:${a.severity==='高'?'#c42b1c':'#e88b25'}"></span><div><span class="time">${date(a.first,true)} · ${stateNames[a.status]}</span><button data-action="alert" data-id="${a.id}">${esc(a.title)}</button></div></div>`).join('')}<button class="card-link" data-action="to-tab" data-id="alerts">查看告警 ${I('chevron',12)}</button></article><article class="card summary-card"><div class="card-title"><h3>证据</h3>${badge(String(ev.length),'blue')}</div>${[...new Set(ev.map(e=>e.type))].map(type=>`<div class="row between" style="padding:10px 0;border-bottom:1px solid #edf0f3"><span class="muted">${esc(type)}</span><b style="font-weight:500">${ev.filter(e=>e.type===type).length}</b></div>`).join('')}<button class="card-link" data-action="to-tab" data-id="evidence">查看证据 ${I('chevron',12)}</button></article></div><div class="summary-bottom"><article class="card"><div class="card-title"><h3>事件信息</h3></div><p class="muted" style="font-size:12px;line-height:1.9;margin-bottom:20px">${esc(inc.description)}</p><div class="info-grid">${keyInfo('事件 ID',esc(inc.id))}${keyInfo('处理状态',state(inc.status))}${keyInfo('严重程度',severity(inc.severity))}${keyInfo('负责人',esc(inc.owner))}</div></article><article class="card"><div class="card-title"><h3>相关威胁与标签</h3></div><div class="row wrap">${inc.tags.map(t=>badge(t,'blue')).join('')}</div><div class="notice warning" style="margin-bottom:0">${I('info',15)}潜在影响路径与已经发生的活动分别展示。</div><button class="card-link" data-action="to-tab" data-id="attack">查看攻击故事 ${I('chevron',12)}</button></article></div>`;
  }
  function similarView(isCase=false){
    if(isCase)return '<div class="section-title"><h2>相似 Cases</h2></div><div class="card"><p class="muted">仅保留目录入口</p></div>';
    const rows=isCase?store.cases.filter(c=>c.id!==currentCase().id):window.referenceWorkspaces.relatedIncidents(store,incidentAlerts(),[currentIncident().id]);
    const defs=[{key:'title',label:isCase?'Case 名称':'事件名称',render:c=>`<a href="#/${isCase?'cases':'incidents'}/${c.id}/${isCase?'overview':'attack'}">${esc(c.title)}</a>`},{key:'id',label:'ID'},{key:'severity',label:'严重程度',render:c=>severity(c.severity)},{key:'status',label:'状态',render:c=>state(c.status)},{key:'reason',label:'相似原因',render:c=>esc(c.shared.map(id=>getAsset(id)?.name||id).join('、'))}];
    return `<div class="section-title"><div><h2>${isCase?'相似 Cases':'相似事件'}</h2><p class="section-subtitle">通过共享实体发现的关联线索</p></div></div>${table(isCase?'similar-cases':'similar-incidents',rows,defs,{filter:false,unit:'项'})}`;
  }
  function recommendationsView(){if(!scopeEvidence().length)return `<div class="section-title"><h2>建议动作</h2></div><div class="card">${empty('暂无建议动作','此事件尚无关联证据，已有告警可在对应页签查看。')}</div>`;return `<div class="section-title"><div><h2>建议动作</h2><p class="section-subtitle">结合实体和证据核查建议，审批结果会记录在活动中</p></div></div><div class="recommendations">${scopeEvidence().filter(e=>e.verdict!=='Clean').slice(0,3).map((e,i)=>`<article class="recommendation"><div class="row between">${badge(i===0?'遏制':i===1?'修复':'调查','blue')}${state(e.remediation)}</div><h3 style="margin-top:15px">${i===0?'检查并阻止钓鱼入口':i===1?'隔离可疑文件':'复核外联与会话活动'}</h3><p>相关证据被判定为${verdictNames[e.verdict]}。请确认影响范围，并在审核后选择适当的处置动作。</p><div class="entity">${I('link',13)} ${esc(e.name)}</div>${btn('查看证据','evidence',e.id,'small','file')}</article>`).join('')}</div>`;}
  function attackWorkspace(){return workspaceView.attack();}
  function caseQueueRows(){
    return orderedCases().map(c=>{
      const linked=caseAlerts(c),ids=new Set(c.alertIds),inc=store.incidents.find(i=>i.id===c.incidentId);
      const flowRuns=savedCase(c)?window.investigationWorkspaceModel.forCase(store,c):null;
      const changes=[c.updated||c.created,...store.activities.filter(a=>a.caseIds?.includes(c.id)).map(a=>a.time),...store.comments.filter(x=>x.caseId===c.id).map(x=>x.time)];
      return {...c,first:c.created,updated:changes.sort().at(-1),classification:c.classification||inc?.classification||'Not set',determination:c.determination||'未设置',sources:[...new Set(linked.map(a=>a.source))],source:[...new Set(linked.map(a=>a.source))].join(', '),category:linked[0]?.category||'未设置',investigation:flowRuns?(flowRuns.some(r=>r.completion==='partial')?'Partial':flowRuns.some(r=>r.status==='running')?'In progress':flowRuns.some(r=>!r.completion&&window.alertFlowWorkspace.started(r))?'Recorded':flowRuns.some(r=>window.alertFlowWorkspace.started(r))?'Completed':'Not started'):linked.length&&linked.every(a=>a.investigation==='Completed')?'Completed':linked.some(a=>a.investigation==='In progress')?'In progress':'New',alertCount:linked.length,activeCount:linked.filter(a=>a.status!=='Resolved').length,assetCount:new Set(linked.flatMap(a=>a.entityIds)).size,threatCount:new Set(store.evidence.filter(e=>ids.has(e.alertId)&&e.verdict!=='Clean').map(e=>e.threat)).size,due:c.due||'未设置'};
    });
  }
  function caseDateEnd(){const latest=Math.max(Date.parse('2026-10-24T23:59:59+08:00'),...store.cases.map(c=>Date.parse(c.created)).filter(Number.isFinite));return new Date(latest+8*3600000).toISOString().slice(0,10)+'T23:59';}
  function caseQueueToolbar(count){
    const t=tableState('cases');
    return `<div class="toolbar case-queue-toolbar">${btn('创建','stub','','quiet','plus')}${btn('刷新','refresh','cases','quiet','refresh')}<label class="row auto-refresh"><input type="checkbox" role="switch" aria-label="自动刷新案件列表" data-case-auto ${ui.caseAuto?'checked':''}>自动刷新 ${I('info',13)}</label>${btn('导出','export','cases','quiet','download')}<span class="spacer"></span><span class="table-tools-count">${count} 个案件</span><label class="search-input">${I('search',15)}<input id="query-cases" data-query="cases" type="search" value="${esc(t.query)}" placeholder="搜索" aria-label="搜索案件名称或 ID"></label>${btn(t.range==='custom'?'自定义范围':t.range==='1'?'最近24小时':`最近 ${t.range||7} 天`,'date-filter','cases','quiet','calendar')}${btn('自定义列','columns','cases','quiet','columns')}</div>`;
  }
  const caseFilterFields=['dataset','query','severity','status','source','owner','tag','priorityBand','classification','investigation','category','start','end','range'];
  function caseQueueFilters(){
    const t=tableState('cases'),sets=store.caseFilterSets||[];
    const chips=[['priorityBand','优先级',{top:'最高（>85）',medium:'中等（15–85）',low:'低（<15）'}[t.priorityBand]],['severity','严重程度',t.severity],['status','状态',stateNames[t.status]],['owner','负责人',t.owner],['tag','标签',t.tag],['classification','分类',classificationNames[t.classification]],['investigation','调查状态',stateNames[t.investigation]],['category','类别',t.category],['source','检测源',t.source]];
    return `<div class="filterbar case-filterbar"><label class="row">筛选集：<select data-case-filter-set aria-label="选择筛选集"><option value="">无</option>${sets.map(x=>`<option value="${x.id}" ${ui.caseFilterSet===x.id?'selected':''}>${esc(x.name)}</option>`).join('')}<option value="create">创建筛选集…</option></select></label>${btn('保存','save-case-filter-set','','quiet small','save')}${chips.filter(x=>x[2]).map(([field,label,value])=>`<span class="filter-chip">${label}: <b>${esc(value)}</b><button aria-label="移除${label}筛选" data-action="remove-filter" data-key="cases" data-field="${field}">${I('close',12)}</button></span>`).join('')}<span class="spacer"></span>${btn('添加筛选','filter','cases','quiet small','filter')}${btn('重置全部','clear-filters','cases','quiet small','filter')}</div>`;
  }
  function caseQueue(){
    const rows=caseQueueRows(),columns=[
      {key:'title',label:'案件名称',render:c=>`<div class="row">${iconBtn('chevron','预览 Case '+c.id,'case-preview',c.id)}<a class="incident-name" title="${esc(c.title)}" href="#/cases/${c.id}/overview">${esc(c.title)}</a></div><small class="muted">${caseSource(c)}</small>`},
      {key:'id',label:'Case ID'},
      {key:'priority',label:'优先级评分',render:c=>`<button class="priority-pill ${c.priority>85?'high':''}" data-action="case-preview" data-id="${c.id}">${c.priority??'—'} ${c.priority>85?I('info',11):''}</button>`},
      {key:'created',label:'创建时间',render:c=>date(c.created)},
      {key:'owner',label:'负责人',render:c=>`<span class="row">${avatar(c.owner)}${esc(c.owner)}</span>`},
      {key:'severity',label:'严重程度',render:c=>severity(c.severity)},
      {key:'status',label:'状态',render:c=>state(c.status)},
      {key:'classification',label:'分类',render:c=>esc(classificationNames[c.classification]||c.classification)},
      {key:'determination',label:'判定'},
      {key:'tags',label:'标签',render:c=>c.tags.map(t=>badge(t,t==='关键资产'?'purple':'')).join(' ')||'—'},
      {key:'activeCount',label:'活跃 / 全部告警',render:c=>`${c.activeCount} / ${c.alertCount}`},
      {key:'threatCount',label:'关联威胁',render:c=>c.threatCount?`${c.threatCount} 个关联威胁`:'—'},
      {key:'category',label:'类别'},
      {key:'investigation',label:'调查状态',render:c=>state(c.investigation)},
      {key:'source',label:'检测源',render:c=>esc(c.source.replaceAll('Microsoft ',''))||'—'},
      {key:'due',label:'截止时间'},
      {key:'updated',label:'最近更新时间',render:c=>date(c.updated)},
    ];
    const t=tableState('cases');t.columns ||= columns.slice(0,12).map(c=>c.key);
    tableContexts.set('cases',{rows,columns,opts:{timeField:'created'}});
    const shown=filteredRows('cases',rows);
    const multi=Math.round(shown.filter(c=>c.alertCount>1).length/Math.max(1,shown.length)*100),caseRuns=shown.map(c=>window.investigationWorkspaceModel.forCase(store,c)),uniqueRuns=[...new Map(caseRuns.flat().map(r=>[r.id,r])).values()];
    return `<section class="page cases-queue"><div class="title-line"><h1>Cases</h1><div class="page-top-actions"><a class="button primary" href="#/investigations">查看调查运行</a>${btn('案件管理设置','stub','','quiet','settings')}</div></div><nav class="iv-filter-tabs" aria-label="案件数据来源">${[['all','全部案件',rows.length],['aisoc','AiSOC 调查',rows.filter(savedCase).length],['design','原设计案例',rows.filter(c=>!savedCase(c)).length]].map(([key,label,n])=>`<a href="#/cases?data=${key}" data-action="case-data" data-id="${key}" ${((t.dataset||'all')===key)?'aria-current="page"':''}>${label}<b>${n}</b></a>`).join('')}</nav><div class="tabs case-type-tabs"><span class="tab selected">Incident</span><span class="tab disabled" title="本轮范围为 Incident cases">Generic</span></div><div class="case-queue-metrics">${[['有关联调查的案件','可查看已有 AI 调查结果',caseRuns.filter(rs=>rs.some(r=>r.completion!=='not_escalated')).length,'sparkles'],['部分交付的调查','保留已有结果与未完成事项',uniqueRuns.filter(r=>r.completion==='partial').length,'search'],['待跟进任务','案件中尚未完成的任务',shown.flatMap(c=>c.tasks||[]).filter(t=>t.status!=='Completed').length,'check'],['多告警案件','包含多条成员告警',multi+'%','graph']].map(([title,description,value,ico])=>`<article class="case-list-metric"><h3>${title}</h3><p>${description}</p><div class="row"><b>${value}</b><small>当前案件</small><span class="spacer"></span>${I(ico,16)}</div></article>`).join('')}</div>${table('cases',rows,columns,{unit:'个案件',caseQueue:true,rowPreview:'case',dates:true})}</section>`;
  }
  function casePage(){
    if(!currentRoute().id)return caseQueue();
    if(!store.cases.some(c=>c.id===currentRoute().id))return `<section class="page">${empty('未找到该 Case','当前数据中没有这个案件，请返回列表选择。')}<a class="button" href="#/cases">返回 Cases</a></section>`;
    const c=currentCase(),tab=currentRoute().tab||'overview',alerts=caseAlerts(c),entities=scopeEntities(),ev=scopeEvidence();
    const directory=[['overview','AI 调查','search'],['investigations','调查历史','clock',window.investigationWorkspaceModel.forCase(store,c).length],['case-info','案件资料','file'],['alerts','成员告警','shield',alerts.length],['assets','涉及对象','device',entities.length],['attack','案件关系图','graph'],['evidence','案件证据','file',savedCase(c)?undefined:ev.length],['similar','相似 Cases','link'],['tasks','跟进任务','check',(c.tasks||[]).filter(t=>t.status!=='Completed').length],['activities','处理活动','clock',scopeActivities().length],['comments','评论与附件','comment',store.comments.filter(x=>x.caseId===c.id).length+((c.localCollection||c.recordedCase)?0:2)]];
    const selectedTab=tab==='investigations'&&new URLSearchParams(currentRoute().search).has('run')?'overview':tab;
    let content=tab==='overview'?(c.localCollection?investigationView.flowCaseOverview():investigationView.workbench()):tab==='case-info'?caseOverview():tab==='tasks'?workspaceView.tasks():tab==='attack'?(c.alertFlowCollection?investigationView.flowCaseRelations():c.recordedCase?investigationView.persistedCaseRelations():c.localCollection?investigationView.caseRelations():`<div class="iv-root iv-context-caption"><h2>案件关系图</h2><p>当前案件成员的关联资料；某次调查保存的关系分析在 AI 调查内查看。</p></div>`+attackWorkspace()):tab==='alerts'?`<div class="section-title"><h2>成员告警</h2>${btn('移动所选告警','move-case','','small','link')}</div>${table('case-alerts',alerts,alertColumns,{unit:'条告警',dates:true})}`:tab==='assets'?assetsView():tab==='similar'?similarView(true):tab==='investigations'?investigationsView():tab==='evidence'?evidenceView():tab==='activities'?activitiesView():commentsView();
    return `<header class="page-header">${breadcrumbs([{label:'Cases',href:'#/cases'},{label:c.title}])}<div class="title-line"><h1>ID ${c.id}: ${esc(c.title)}</h1><div class="page-top-actions">${iconBtn('refresh','刷新 Case','refresh')}${iconBtn('list','切换 Case','choose-case')}</div></div><div class="metadata"><span class="row"><b class="priority">${c.priority??'—'}</b><span class="muted">优先级评分</span></span><button data-action="manage-case" data-id="${c.id}">${severity(c.severity)}</button><button data-action="manage-case" data-id="${c.id}">${state(c.status)}</button><button class="row" data-action="manage-case" data-id="${c.id}">${avatar(c.owner)}${esc(c.owner)}</button>${c.critical?badge('关键资产','purple'):''}${caseIncidents(c).map(i=>`<a class="button small" href="#/incidents/${i.id}/summary">关联事件 · ${esc(i.title)}</a>`).join('')}</div></header><div class="case-body"><nav class="case-nav" aria-label="Case 内部导航"><div class="case-nav-heading">Case</div>${directory.map(([key,label,ico,count],i)=>`${[0,2,8].includes(i)?`<div class="case-nav-group">${i===0?'AI 调查':i===2?'案件材料':'协作与跟进'}</div>`:''}<a class="case-nav-button ${selectedTab===key?'selected':''}" href="#/cases/${c.id}/${key}" ${selectedTab===key?'aria-current="page"':''}>${I(ico,16)}${label}${count!==undefined?`<span class="count">${count}</span>`:''}</a>`).join('')}</nav><section class="case-content">${c.alertFlowCollection?`<div class="iv-source-notice"><b>本地整理 Case</b><span>汇集已有告警与调查；源系统未创建Case。每次调查保留原输入与结果。</span></div>`:c.localCollection?`<div class="iv-source-notice"><b>AiSOC · 2026-10-24</b><span>演示告警的实际处理结果 · 本地整理 Case，源系统未建 Case。每次调查仍保留原输入范围。</span></div>`:c.recordedCase?`<div class="iv-source-notice"><b>AiSOC · 2026-10-21</b><span>已创建的历史 Case · 三条测试告警的实际联合调查结果。</span></div>`:''}${content}</section></div>`;
  }
  function caseOverview(){
    const c=currentCase(),alerts=caseAlerts(c),entities=scopeEntities();
    if(savedCase(c))return flowCaseInfo(c,alerts,entities);
    return `<div class="case-summary-metrics">${[['关联告警',alerts.length,'alerts'],['受影响资产',entities.length,'assets'],['证据',scopeEvidence().length,'evidence'],['待审批',scopeEvidence().filter(e=>e.remediation==='Pending approval').length,'evidence']].map(([label,n,tab])=>`<button class="card" style="text-align:left" data-action="to-tab" data-id="${tab}"><span class="muted" style="font-size:11px">${label}</span><b>${n}</b></button>`).join('')}</div><div class="case-overview-grid"><div><article class="copilot-card"><div class="copilot-title"><span class="copilot-icon">${I('sparkles',21)}</span>案件资料摘要<span class="spacer"></span>${iconBtn(ui.caseCollapsed?'down':'minus','折叠或展开摘要','case-summary-toggle')}</div>${!ui.caseCollapsed?`<h3>当前案件资料</h3><div class="updated">最近更新：${date(c.updated||c.created)}</div><p>${esc(c.description)}</p><ul><li>当前案件关联 ${alerts.length} 条告警，涉及 ${entities.filter(a=>a.type==='user').length} 个用户与 ${entities.filter(a=>a.type==='device').length} 台设备。</li><li>已有 ${scopeEvidence().length} 项关联证据、${window.investigationWorkspaceModel.forCase(store,c).length} 项调查记录，可从对应材料核对结果。</li><li>${scopeEvidence().filter(e=>e.remediation==='Pending approval').length} 项已有处置记录等待审核，可进入案件证据核对。</li></ul>${btn('查看案件关系图','to-tab','attack','small','graph')}<div class="copilot-footer"><small>根据当前案件成员与资料汇总。</small><div class="row">${iconBtn('check','摘要有帮助','feedback','helpful',ui.feedback==='helpful'?'active':'')}${iconBtn('flag','摘要需改进','feedback','improve',ui.feedback==='improve'?'active':'')}</div></div>`:''}</article><article class="card"><div class="card-title"><h3>关联告警</h3><span class="spacer"></span><button class="link-button" data-action="to-tab" data-id="alerts">查看全部</button></div>${alerts.slice(0,4).map(a=>`<div class="entity-list-item">${I('shield',17)}<button data-action="alert" data-id="${a.id}" style="max-width:100%;flex:1">${esc(a.title)}</button>${severity(a.severity)}</div>`).join('')||empty('暂无关联告警','可在其他视图查看案件信息')}</article></div><aside class="stack"><article class="card"><div class="card-title"><h3>Case 详细信息</h3></div><div class="info-grid">${keyInfo('Case ID',c.id)}${keyInfo('处理状态',state(c.status))}${keyInfo('负责人',esc(c.owner))}${keyInfo('严重程度',severity(c.severity))}${keyInfo(c.localCollection?'本地整理时间':'创建时间',date(c.created))}${keyInfo('截止时间',esc(c.due?.replace('T',' ')||'未设置'))}${keyInfo('结案说明',esc(c.resolutionNote||'—'))}${keyInfo(c.localCollection?'源 Case':'关联事件',c.localCollection?'未创建':c.incidentId?`<a href="#/incidents/${c.incidentId}/summary">${c.incidentId}</a>`:'—')}</div><div style="margin-top:20px">${btn('管理 Case','manage-case',c.id,'small','edit')}</div></article><article class="card"><div class="card-title"><h3>关键实体</h3></div>${entities.slice(0,4).map(a=>`<div class="entity-list-item">${entityChip(a)}</div>`).join('')}<button class="card-link" data-action="to-tab" data-id="assets">查看全部资产 ${I('chevron',12)}</button></article></aside></div>`;
  }
  function flowCaseInfo(c,alerts,entities){
    const stats=window.alertFlowWorkspace.caseStats(window.investigationWorkspaceModel.forCase(store,c));
    return `<div class="case-summary-metrics">${[['当前成员',alerts.length,'alerts'],['涉及对象',entities.length,'assets'],['已保存工件',stats.artifacts,'evidence'],['调查记录',stats.runs,'investigations']].map(([label,n,tab])=>`<button class="card" data-action="to-tab" data-id="${tab}"><span>${label}</span><b>${n}</b></button>`).join('')}</div><div class="case-overview-grid"><div class="stack"><article class="card"><h3>案件资料摘要</h3><p>${esc(c.description)}</p><p>当前 ${alerts.length} 条成员告警，${stats.runs} 次既有运行，其中 ${stats.partial} 次部分交付、${stats.triage} 次仅完成分诊；未记录的交付完整性保持未知。</p><p>${stats.tools} 条工具记录、${stats.artifacts} 份工件及 ${stats.reports} 份报告按各次调查保存。</p><p class="muted">案件判定尚未设置；各次调查的判定、停止原因和建议分别查看。成员变更不会重写历史输入。</p><a class="button primary" href="#/cases/${c.id}/overview">查看 AI 调查</a></article><article class="card"><h3>当前成员告警</h3>${alerts.map(a=>`<div class="entity-list-item"><a href="#/alerts/${a.id}/overview">${esc(a.title)}</a>${severity(a.severity)}<span>${date(a.event_time||a.first)}</span></div>`).join('')||empty('暂无当前成员')}</article></div><aside class="stack"><article class="card"><h3>Case 详细信息</h3><div class="info-grid">${keyInfo(c.localCollection?'本地 Case ID':'Case ID',esc(c.id))}${keyInfo('源 Case',esc(c.sourceCaseId||'未创建'))}${keyInfo(c.localCollection?'本地处理状态':'处理状态',state(c.status))}${keyInfo('负责人',esc(c.owner))}${keyInfo('严重程度',severity(c.severity))}${keyInfo('分类',esc(classificationNames[c.classification]||c.classification))}${keyInfo(c.localCollection?'本地整理时间':'创建时间',date(c.created))}${keyInfo('最近更新',date(c.updated))}${keyInfo('来源采集时间',date(c.sourceCapturedAt))}${keyInfo('关联事件',caseIncidents(c).map(i=>`<a href="#/incidents/${i.id}/summary">${esc(i.title)}</a>`).join('<br>')||'未关联')}${keyInfo('截止时间',esc(c.due?.replace('T',' ')||'未设置'))}${keyInfo('结案说明',esc(c.resolutionNote||'—'))}</div><p class="muted">${c.localCollection?'案件等级依据初始成员最高等级整理':'案件等级沿用源 Case 记录'}；优先级尚未评分。</p>${btn('管理 Case','manage-case',c.id,'small','edit')}</article><article class="card"><h3>涉及对象</h3>${entities.map(entityChip).join('')}</article></aside></div>`;
  }
  function commentsView(){
    const c=currentCase(),comments=store.comments.filter(x=>x.caseId===c.id);
    return `<div class="section-title"><h2>评论与附件</h2>${badge('调查协作','blue')}</div><div class="comments-layout"><article class="card"><div class="card-title"><h3>评论 (${comments.length})</h3></div>${comments.map(x=>`<div class="comment">${avatar(x.author)}<div><span class="author">${esc(x.author)}</span><span class="time">${date(x.time)}</span><p>${esc(x.text)}</p></div></div>`).join('')||'<p class="muted">还没有评论，添加第一条调查备注。</p>'}<form id="comment-form"><label for="new-comment" class="info-label" style="display:block;margin-top:15px">添加调查备注</label><textarea id="new-comment" class="comment-input" name="comment" maxlength="4000" placeholder="记录调查发现、交接信息或待核事项…" required></textarea><div class="row between" style="margin-top:11px"><small class="muted">以 Alex Wilber 身份添加</small><button class="button primary" type="submit">添加评论</button></div></form></article><article class="card"><div class="card-title"><h3>附件 (${(c.localCollection||c.recordedCase)?0:2})</h3></div>${((c.localCollection||c.recordedCase)?[]:[['investigation-notes.txt','调查摘记 · TXT · 1 KB'],['evidence-register.csv','证据索引 · CSV · 2 KB']]).map(([name,label])=>`<div class="attachment"><span class="entity-icon">${I('file',20)}</span><div style="min-width:0"><div class="attachment-name">${name}</div><div class="attachment-info">${label}</div></div><span class="spacer"></span>${iconBtn('download','下载 '+name,'attachment',name)}</div>`).join('')}<p class="muted" style="font-size:11px;line-height:1.8;margin-top:17px">${(c.localCollection||c.recordedCase)?'尚无附件；已有报告可在各次调查的“报告与响应”中查看和下载。':'用于查看和交接调查材料。'}</p></article></div>`;
  }
  function fullAlert(a){return renderAlertDetail(a);}
  function alertInfo(a){return `<article class="card"><div class="card-title"><h3>告警属性</h3>${iconBtn('copy','复制告警 ID','copy',a.id)}</div><div class="info-grid">${keyInfo('严重程度',severity(a.severity))}${keyInfo('状态',state(a.status))}${keyInfo('分类',esc(classificationNames[a.classification]))}${keyInfo('负责人',esc(a.owner))}${keyInfo('首次活动',date(a.first))}${keyInfo('末次活动',date(a.last))}${keyInfo('调查状态',state(a.investigation))}${keyInfo('检测类别',esc(a.category))}</div><div class="detail-summary" style="padding:17px 0 0;margin:0;border:0"><div class="info-label">检测源</div><span class="info-value">${esc(a.source)}</span><div class="info-label" style="margin-top:13px">告警 ID</div><span class="mono">${a.id}</span></div></article>`;}
  function drawerMarkup(){
    const d=ui.drawer;if(!d)return '';
    let title='',subtitle='',body='',footer='',tabs='';
    if(d.type==='incident'){
      const inc=store.incidents.find(x=>x.id===d.id);if(!inc)return '';
      const linked=incidentAlerts(inc),entities=store.assets.filter(a=>linked.some(x=>x.entityIds.includes(a.id)));
      title=inc.title;subtitle='事件摘要 · '+inc.id;
      body=`<div class="row wrap" style="margin-bottom:20px">${severity(inc.severity)}${state(inc.status)}${inc.tags.map(t=>badge(t,t==='关键资产'?'purple':'')).join('')}</div>${inc.recordedIncident?`<div class="card"><h3>优先级评估</h3><p class="muted">尚未评分</p><p class="muted">告警等级按成员最高等级展示。</p></div>`:`<div class="card" style="padding:15px"><div class="row between"><h3>优先级评估</h3><b class="priority">${inc.priority}</b></div><div class="priority-factors">${[['关键资产与影响',inc.critical?90:45],['关联告警严重程度',inc.severity==='高'?85:inc.severity==='中'?60:30],['攻击阶段与关联',Math.min(95,linked.length*12+20)]].map(([n,v])=>`<div class="row"><span>${n}</span><span>${v}</span></div><div class="bar-track"><i style="width:${v}%"></i></div>`).join('')}</div><small class="muted">优先级评估因素。</small></div>`}<p class="inc-preview-description">${esc(inc.description)}</p><div class="info-grid">${keyInfo('事件 ID',inc.id)}${keyInfo('分类',esc(classificationNames[inc.classification]||inc.classification))}${keyInfo('负责人',esc(inc.owner))}${keyInfo('活跃 / 全部告警',`${linked.filter(a=>a.status!=='Resolved').length} / ${linked.length}`)}${keyInfo('首次活动',date(inc.first))}${keyInfo('最近更新',date(inc.updated||inc.last))}</div>${inc.resolutionNote?`<div class="notice clean" style="margin-top:20px"><span><b>解决说明</b><br>${esc(inc.resolutionNote)}</span></div>`:''}<div class="detail-summary" style="padding-top:24px"><h3>受影响资产 (${entities.length})</h3>${entities.slice(0,5).map(a=>`<div class="entity-list-item">${entityChip(a)}</div>`).join('')}</div><div class="detail-summary"><h3>关联告警</h3>${linked.slice(0,4).map(a=>`<div class="entity-list-item"><button data-action="alert" data-id="${a.id}" style="max-width:100%">${esc(a.title)}</button></div>`).join('')}</div>`;
      footer=btn('打开事件页','open-incident',inc.id,'primary','external')+btn('管理事件','manage-incident',inc.id,'','edit');
    }else if(d.type==='case'){
      const c=caseQueueRows().find(x=>x.id===d.id);if(!c)return '';
      title=c.title;subtitle='Case 摘要 · '+c.id;
      body=`<div class="row wrap" style="margin-bottom:20px">${severity(c.severity)}${state(c.status)}${c.tags.map(t=>badge(t,t==='关键资产'?'purple':'')).join('')}</div><div class="card"><div class="row between"><h3>优先级评估</h3><b class="priority">${c.priority??'—'}</b></div><p class="inc-preview-description">${c.priority==null?'尚未评分':c.priority>85?'最高优先级评分':c.priority<15?'低优先级评分':'中等优先级评分'}</p><div class="info-grid">${keyInfo('严重程度',severity(c.severity))}${keyInfo('受影响资产',c.assetCount+' 项')}${keyInfo('关联告警',c.alertCount+' 条')}${keyInfo('攻击类别',esc(c.category))}</div></div><p class="inc-preview-description">${esc(c.description)}</p><div class="info-grid">${keyInfo('Case ID',c.id)}${keyInfo('负责人',esc(c.owner))}${keyInfo(c.localCollection?'本地整理时间':'创建时间',date(c.created))}${keyInfo('最近更新',date(c.updated))}${keyInfo('活跃 / 全部告警',`${c.activeCount} / ${c.alertCount}`)}${keyInfo('调查状态',state(c.investigation))}${keyInfo('分类',esc(classificationNames[c.classification]))}${keyInfo('判定',esc(c.determination))}</div><div class="detail-summary"><h3>关联告警</h3>${caseAlerts(c).slice(0,4).map(a=>`<div class="entity-list-item"><button data-action="alert" data-id="${a.id}">${esc(a.title)}</button></div>`).join('')||'<p>暂无关联告警</p>'}</div>`;
      footer=btn('打开 Case','open-case',c.id,'primary','external')+btn('管理 Case','manage-case',c.id,'','edit');
    }else if(d.type==='alert'){
      const a=getAlert(d.id);if(!a)return '';
      title=a.title;subtitle='告警详情';
      tabs='<div class="tabs"><span class="tab selected">概览</span></div>';
      body=`<div class="row wrap" style="margin-bottom:18px">${severity(a.severity)}${state(a.status)}${badge(a.category,'blue')}</div><div class="detail-summary"><h3>发生了什么</h3><p>${esc(a.description)}</p></div><div class="detail-summary"><h3>告警信息</h3><div class="info-grid alert-preview-info">${keyInfo('告警 ID',esc(a.id))}${keyInfo('告警时间',date(a.event_time||a.first))}${keyInfo('负责人',esc(a.owner))}${keyInfo('检测源',esc(a.source))}${keyInfo('资产标签',[...new Set(a.entityIds.flatMap(id=>getAsset(id)?.tags||[]))].map(t=>badge(t)).join(' ')||'—')}</div></div><div class="detail-summary"><h3>受影响实体</h3>${a.entityIds.slice(0,4).map(id=>`<div style="margin:11px 0">${alertAssetLink(getAsset(id))}</div>`).join('')}</div><div class="detail-summary"><h3>关联事件与 Case</h3><p>${store.incidents.some(i=>i.id===a.incidentId)?`<a href="#/incidents/${a.incidentId}/attack">事件 ${esc(a.incidentId)}</a>`:esc(a.incidentId||'—')}</p>${store.cases.filter(c=>c.alertIds.includes(a.id)).map(c=>`<p><a href="#/cases/${c.id}/overview">Case ${c.id} · ${esc(c.title)}</a></p>`).join('')||'<p>未关联 Case</p>'}</div>`;
      footer=btn('管理告警','manage-alert',a.id,'primary','edit')+btn('打开告警页','full-alert',a.id,'','external');
    }else if(d.type==='entity'){
      const a=getAsset(d.id);if(!a)return '';title=a.name;subtitle=typeNames[a.type]+'详情';
      const related=store.alerts.filter(x=>x.entityIds.includes(a.id));
      body=`<div class="row" style="margin-bottom:22px"><span class="entity-icon ${a.type}" style="width:43px;height:43px">${I(a.type,25)}</span><div>${severity(a.risk)}${a.critical?'<div style="margin-top:5px">'+badge('关键资产','purple')+'</div>':''}</div></div><div class="detail-summary"><h3>基本信息</h3><div class="info-grid">${keyInfo('类型',typeNames[a.type])}${keyInfo('所属组织','Contoso')}${keyInfo('资产 ID','asset-'+a.id+'-20261024')}${keyInfo('风险等级',esc(a.risk))}${Object.entries({domain:'域',os:'操作系统',ip:'IP 地址',displayName:'姓名',department:'部门',role:'角色',location:'位置',provider:'来源',hash:'文件 SHA-256',permissions:'权限'}).filter(([k])=>a[k]).map(([k,n])=>keyInfo(n,esc(a[k]))).join('')}</div>${a.isolated?'<div class="notice clean" style="margin-bottom:0">'+I('check',15)+'已隔离（演示）</div>':''}</div><div class="detail-summary"><h3>关联告警 (${related.length})</h3>${related.slice(0,6).map(x=>`<div class="entity-list-item"><button data-action="alert" data-id="${x.id}" style="max-width:100%">${esc(x.title)}</button></div>`).join('')||'<p>当前没有关联告警。</p>'}</div>`;
      if(a.inventory===false)body=`<div class="detail-summary"><h3>告警中的原始对象</h3><div class="info-grid">${keyInfo('类型',typeNames[a.type])}${keyInfo('名称 / 值',esc(a.name))}${keyInfo('资产库存关系','未关联库存')}</div></div><div class="detail-summary"><h3>关联告警 (${related.length})</h3>${related.map(x=>`<p><a href="#/alerts/${x.id}/overview">${esc(x.title)}</a></p>`).join('')}</div>`;
      footer=a.inventory!==false&&a.type==='device'?btn(a.isolated?'已模拟隔离':'模拟隔离设备','simulate-response',a.id,'primary','shield'):btn('关闭','close-drawer');
    }else if(d.type==='evidence'){
      const e=store.evidence.find(x=>x.id===d.id);if(!e)return '';title=e.name;subtitle='证据详情';
      body=`<div class="row wrap" style="margin-bottom:22px">${badge(e.type,'blue')}${badge(verdictNames[e.verdict],e.verdict==='Malicious'?'red':e.verdict==='Suspicious'?'amber':'green')}${state(e.remediation)}</div><div class="info-grid">${keyInfo('证据 ID',e.id)}${keyInfo('检测来源',esc(e.origin))}${keyInfo('威胁',esc(e.threat))}${keyInfo('关联告警',`<button class="link-button" data-action="alert" data-id="${e.alertId}">${e.alertId}</button>`)}</div><div class="detail-summary" style="padding-top:25px"><h3>受影响实体</h3>${entityChip(getAsset(e.entityId))}</div><div class="detail-summary"><h3>处置说明</h3><p>${e.remediation==='Pending approval'?'建议对相关实体执行处置。请先审阅告警及证据，再批准或拒绝。':'当前处置状态：'+(stateNames[e.remediation]||e.remediation)+'。相关操作记录可在活动页签中查看。'}</p></div>${e.remediation==='Pending approval'?'<div class="notice warning">'+I('info',15)+'请核对证据后审批。</div>':''}`;
      footer=e.remediation==='Pending approval'?btn('批准','approve-evidence',e.id,'primary','check')+btn('拒绝','reject-evidence',e.id,'','close'):btn('关闭','close-drawer');
    }else if(d.type==='activity'){
      const a=store.activities.find(x=>x.id===d.id)||scopeActivities().find(x=>x.id===d.id);if(!a)return '';title=a.title;subtitle='活动详情';body=`<div style="margin-bottom:20px">${state(a.status)}</div><div class="info-grid">${keyInfo('时间',date(a.time))}${keyInfo('执行者',esc(a.performedBy))}${keyInfo('类型',esc(a.type))}${keyInfo('触发方式',esc(a.trigger))}${keyInfo('目标',esc(a.target))}${keyInfo('关联事件',esc(a.incidentId))}</div><div class="notice" style="margin-top:25px">${I('info',15)}${a.status==='Recorded'?'此记录已保存；查询结果与调查完整性请在对应调查中核对。':a.status==='Failed'?'此步骤未完成，已有材料仍保留。':'此记录展示了操作来源、目标和实际处理结果。'}${a.runId?` <a href="${currentRoute().page==='cases'?`#/cases/${encodeURIComponent(currentCase().id)}/investigations?run=${encodeURIComponent(a.runId)}&view=ledger`:`#/investigations/${encodeURIComponent(a.runId)}/ledger`}">查看调查记录</a>`:''}</div>`;footer=btn('关闭','close-drawer');
    }else if(d.type==='investigation'){
      const inv=workspaceView.investigationDetail(d.id);title=inv.title;subtitle='调查详情 · '+d.id;body=inv.body;footer=btn('查看证据与响应','to-tab','evidence','primary','file');
    }else if(d.type==='similar-alerts'){
      const a=getAlert(d.id);title='相似告警';subtitle='按共享实体与检测类别匹配';const similar=store.alerts.filter(x=>x.id!==a.id&&(x.category===a.category||x.entityIds.some(id=>a.entityIds.includes(id))));
      body=similar.map(x=>`<div class="detail-summary"><button class="link-button" data-action="alert" data-id="${x.id}">${esc(x.title)}</button><div class="row" style="margin-top:8px">${severity(x.severity)}${state(x.status)}</div><p style="margin-top:7px">${esc(classificationNames[x.classification])} · ${esc(x.owner)}</p></div>`).join('');footer=btn('关闭','close-drawer');
    }
    return `<div class="overlay-backdrop" data-action="close-drawer"></div><aside class="drawer ${d.type==='investigation'?'wide':''}" role="dialog" aria-modal="true" aria-label="${esc(subtitle)}"><header class="drawer-header"><div style="min-width:0;flex:1"><small>${esc(subtitle)}</small><h2>${esc(title)}</h2></div>${iconBtn('close','关闭详情','close-drawer')}</header>${tabs}<div class="drawer-content">${body}</div><footer class="drawer-footer">${footer}</footer></aside>`;
  }
  function selectField(label,name,values,value,blank=false,preserveUnknown=false){
    if(preserveUnknown&&!blank&&value!=null&&!values.some(v=>(Array.isArray(v)?v[0]:v)===value))values=[[value,stateNames[value]||value],...values];
    return `<div class="form-field"><label for="field-${name}">${esc(label)}</label><select id="field-${name}" name="${name}">${blank?'<option value="">保持不变</option>':''}${values.map(v=>{const item=Array.isArray(v)?v:[v,v];return `<option value="${esc(item[0])}" ${value===item[0]?'selected':''}>${esc(item[1])}</option>`;}).join('')}</select></div>`;
  }
  function modalMarkup(){
    const m=ui.modal;if(!m)return '';let title='',body='',action='',saveLabel='保存';
    if(m.type==='manage-alert'||m.type==='bulk-manage'){
      const bulk=m.type==='bulk-manage',a=getAlert(m.ids[0]);if(!a)return '';
      const listManagement=m.type==='manage-alert'||(bulk&&m.key==='alerts');
      title=bulk?`管理 ${m.ids.length} 条告警`:'管理告警';action='save-alerts';
      body=`<form id="manage-form">${selectField('状态','status',Object.entries(stateNames).filter(([k])=>['New','In progress','Resolved'].includes(k)),bulk?'':a.status,bulk)}${selectField('分配给','owner',store.people,bulk?'':a.owner,bulk)}${listManagement?'':selectField('分类','classification',Object.entries(classificationNames),bulk?'':a.classification,bulk)}<div class="form-field"><label for="field-comment">评论</label><textarea id="field-comment" name="comment" placeholder="${listManagement?'记录处理说明或交接信息':'记录分类理由或交接信息'}" maxlength="4000"></textarea></div></form><p>保存后将在相关页面同步显示。</p>`;
    }else if(m.type==='manage-incident'||m.type==='bulk-incidents'){
      const bulk=m.type==='bulk-incidents',item=store.incidents.find(x=>x.id===(bulk?m.ids[0]:m.id));
      title=bulk?`管理 ${m.ids.length} 个事件`:'管理事件';action='save-incidents';
      body=`<form id="manage-incidents-form">${!bulk?`<div class="form-field"><label for="incident-title">事件名称</label><input id="incident-title" name="title" maxlength="180" value="${esc(item.title)}" required></div>`:''}${selectField('严重程度','severity',['高','中','低'],bulk?'':item.severity,bulk)}${selectField('状态','status',['New','In progress','Resolved'].map(x=>[x,stateNames[x]]),bulk?'':item.status,bulk,true)}${selectField('负责人','owner',store.people,bulk?'':item.owner,bulk,true)}${selectField('分类','classification',Object.entries(classificationNames),bulk?'':item.classification,bulk)}<div class="form-field"><label for="incident-tags">${bulk?'添加标签':'事件标签'}</label><input id="incident-tags" name="tags" value="${bulk?'':esc(item.tags.join(', '))}" placeholder="多个标签用逗号分隔" maxlength="200"></div><div class="form-field"><label for="incident-note">解决说明 / 调查备注</label><textarea id="incident-note" name="note" maxlength="4000" placeholder="解决事件时请填写原因，其余情况下可选"></textarea></div><div id="modal-error" class="form-error"></div></form><p>变更负责人会同步分配关联告警；解决事件会同步解决其活跃告警。</p>`;
    }else if(m.type==='manage-case'){
      const item=store.cases.find(x=>x.id===m.id);title='管理 Case';action='save-scope';
      body=workspaceView.manageBody(item,selectField);
    }else if(m.type==='filter'){
      const ctx=tableContexts.get(m.key),t=tableState(m.key);title='筛选';action='save-filter';saveLabel='应用';
      const severities=[...new Set(ctx.rows.map(x=>x.severity).filter(Boolean))],statuses=[...new Set(ctx.rows.map(x=>x.status).filter(Boolean))],sources=[...new Set(ctx.rows.flatMap(x=>x.sources||[x.source]).filter(Boolean))],owners=[...new Set(ctx.rows.map(x=>x.owner).filter(Boolean))],tags=[...new Set(ctx.rows.flatMap(x=>x[ctx.opts.tagField||'tags']||[]))];
      const field=(label,name,values,val)=>`<div class="form-field"><label for="filter-${name}">${label}</label><select id="filter-${name}" name="${name}"><option value="">全部</option>${values.map(v=>`<option value="${esc(v)}" ${v===val?'selected':''}>${esc(stateNames[v]||v)}</option>`).join('')}</select></div>`;
      body=`<form id="filter-form">${severities.length?field('严重程度','severity',severities,t.severity):''}${statuses.length?field('状态','status',statuses,t.status):''}${sources.length?field('检测来源','source',sources,t.source):''}${owners.length?field('负责人','owner',owners,t.owner):''}${tags.length?field(m.key==='alerts'?'资产标签':'标签','tag',tags,t.tag):''}${m.key==='incidents'?`<div class="form-field"><label for="priority-filter">最低优先级</label><select id="priority-filter" name="minPriority"><option value="">全部</option>${[50,70,90].map(v=>`<option value="${v}" ${String(v)===String(t.minPriority)?'selected':''}>${v} 及以上</option>`).join('')}</select></div>`:''}${m.key==='cases'?selectField('优先级评分','priorityBand',[['','全部'],['top','最高优先级（>85）'],['medium','中等优先级（15–85）'],['low','低优先级（<15）']],t.priorityBand)+selectField('分类','classification',[['','全部'],...Object.entries(classificationNames)],t.classification)+field('调查状态','investigation',[...new Set(ctx.rows.map(x=>x.investigation))],t.investigation)+field('类别','category',[...new Set(ctx.rows.map(x=>x.category))],t.category):''}</form>`;
    }else if(m.type==='columns'){
      const ctx=tableContexts.get(m.key),t=tableState(m.key),order=t.columns?[...t.columns.map(k=>ctx.columns.find(c=>c.key===k)),...ctx.columns.filter(c=>!t.columns.includes(c.key))].filter(Boolean):ctx.columns;title='自定义列';action='save-columns';saveLabel='应用';body=`<p>选择显示字段${m.key==='cases'?'，拖动右侧手柄调整顺序':''}。</p><form id="columns-form">${order.map(c=>`<label class="check-option" ${m.key==='cases'?`draggable="true" data-column="${c.key}"`:''}><input type="checkbox" name="columns" value="${c.key}" ${!t.columns||t.columns.includes(c.key)?'checked':''}>${esc(c.label)}${m.key==='cases'?'<span class="spacer"></span><span class="column-drag-handle" aria-hidden="true">⠿</span>':''}</label>`).join('')}</form><div id="modal-error" class="form-error"></div>`;
    }else if(m.type==='date-filter'){
      const t=tableState(m.key);title=m.key==='cases'?'时间范围':'自定义时间范围';action='save-dates';saveLabel='应用';body=`<form id="date-form">${m.key==='cases'?selectField('时间范围','range',[['1','最近24小时'],['3','最近3天'],['7','最近7天'],['30','最近30天'],['180','最近180天'],['custom','自定义范围']],t.range||'7'):''}<div class="form-field"><label for="date-start">开始时间（UTC+08:00）</label><input id="date-start" type="datetime-local" name="start" value="${esc(t.start||'2026-10-24T00:00')}"></div><div class="form-field"><label for="date-end">结束时间（UTC+08:00）</label><input id="date-end" type="datetime-local" name="end" value="${esc(t.end||(m.key==='cases'?caseDateEnd():'2026-10-24T23:59'))}"></div>${m.key==='cases'?`<p>预置范围截至最新案件日期 ${caseDateEnd().slice(0,10)}；选择自定义后使用上方起止时间。</p>`:''}</form><div id="modal-error" class="form-error"></div>`;
    }else if(m.type==='case-filter-set'){
      title='保存筛选集';action='confirm-case-filter-set';body='<form id="filter-set-form"><div class="form-field"><label for="filter-set-name">筛选集名称</label><input id="filter-set-name" name="name" maxlength="80" required placeholder="例如：最高优先级案件"></div></form><div id="modal-error" class="form-error"></div>';
    }else if(m.type==='move-case'){
      title='移动告警到其他 Case';action='save-move';saveLabel='移动';body=`<p>将选中的 ${m.ids.length} 条告警从 Case ${m.from} 移到目标 Case。告警本身的内容与关联事件保持。</p><form id="move-form">${selectField('目标 Case','caseId',store.cases.filter(c=>c.id!==m.from).map(c=>[c.id,`${c.id} · ${c.title}`]),'')}</form>`;
    }else if(m.type==='reset'){
      title='重置数据数据';action='confirm-reset';saveLabel='重置';body='<p>恢复初始数据，清除本原型在当前浏览器中保存的状态修改、审批和评论。</p>';
    }else if(m.type==='simulate-response'){
      title='模拟隔离设备';action='confirm-response';saveLabel='模拟隔离';body=`<p>将设备 <strong>${esc(getAsset(m.id)?.name)}</strong> 标记为“已隔离（演示）”，并添加一条活动记录。</p><div class="notice">${I('info',16)}只修改本地 Mock 数据，不向设备或服务发送指令。</div>`;
    }else if(m.type==='approve-evidence'||m.type==='reject-evidence'){
      const e=store.evidence.find(x=>x.id===m.id),yes=m.type==='approve-evidence';title=yes?'批准演示动作':'拒绝演示动作';action='confirm-evidence';saveLabel=yes?'批准':'拒绝';body=`<p>证据：<strong>${esc(e.name)}</strong></p><p>确认${yes?'批准':'拒绝'}此模拟响应。结果会反映在证据状态和活动记录中。</p>`;
    }else if(m.type==='choose-incident'||m.type==='choose-case'){
      const cs=m.type==='choose-case',list=cs?orderedCases():store.incidents.slice().sort((a,b)=>Number(!!b.recordedIncident)-Number(!!a.recordedIncident));title=cs?'切换 Case':'切换事件';body=list.map(x=>`<a class="card row" href="#/${cs?'cases':'incidents'}/${x.id}/${cs?'overview':'attack'}" style="margin:8px 0;padding:12px"><span style="flex:1">${esc(x.title)}<small class="muted" style="display:block;margin-top:5px">ID ${x.id}</small></span>${severity(x.severity)}${I('chevron',15)}</a>`).join('');
    }
    return `<div class="modal-backdrop"><section class="modal ${m.key==='cases'&&m.type==='columns'?'side-modal':''}" role="dialog" aria-modal="true" aria-label="${esc(title)}"><header class="modal-header"><h2>${title}</h2>${iconBtn('close','关闭弹窗','close-modal')}</header><div class="modal-content">${body}</div><footer class="modal-footer">${btn(action?'取消':'关闭','close-modal')}${action?btn(saveLabel,action,'','primary'):''}</footer></section></div>`;
  }
  function downloadFile(name,content,mime='text/plain;charset=utf-8'){
    const url=URL.createObjectURL(new Blob([content],{type:mime})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function csvValue(v){let s=Array.isArray(v)?v.join('; '):String(v??'');if(/^[=+\-@]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';}
  function exportTable(key){const ctx=tableContexts.get(key);if(!ctx)return;const selected=tableState(key).columns,cols=selected?selected.map(k=>ctx.columns.find(c=>c.key===k)).filter(Boolean):ctx.columns;const rows=filteredRows(key,ctx.rows);const text='\uFEFF'+[cols.map(c=>csvValue(c.label)).join(','),...rows.map(row=>cols.map(c=>csvValue(c.key==='asset'?getAsset(row.entityIds?.[0])?.name:row[c.key])).join(','))].join('\r\n');downloadFile(`defender-${key}-demo.csv`,text,'text/csv;charset=utf-8');toast(`已导出 ${rows.length} 条记录`);}
  function closeModal(){ui.modal=null;render();}
  function render(){
    const active=document.activeElement,focusId=active?.id,selection=active&&['text','search'].includes(active.type)?[active.selectionStart,active.selectionEnd]:null;
    const scroll=$('.drawer-content')?.scrollTop||0,r=currentRoute();tableContexts.clear();
    workspaceView.resetScope();
    const content=r.page==='assets'?assetPage():r.page==='alerts'?alertsPage():r.page==='incidents'?incidentPage():r.page==='investigations'?`<section class="page">${investigationView.workbench()}</section>`:casePage();
    $('#app').innerHTML=shell(content);
    document.title=`${r.page==='investigations'?'AI 调查':r.page==='assets'?'资产详情':r.page==='alerts'?'告警':r.page==='incidents'?(r.id?'事件调查':'事件'):(r.id?'Case 工作区':'Cases')} · AiSOC`;
    const next=focusId?document.getElementById(focusId):null;
    if(next){next.focus({preventScroll:true});if(selection&&next.setSelectionRange)try{next.setSelectionRange(...selection);}catch{}}
    if($('.drawer-content'))$('.drawer-content').scrollTop=scroll;
    if((ui.modal||ui.drawer)&&!next){const dialog=ui.modal?$('.modal'):$('.drawer');dialog?.querySelector('button, input, select, textarea, a[href]')?.focus({preventScroll:true});}
  }
  function stopPlaying(){if(ui.playing)clearInterval(ui.playing);ui.playing=null;}
  function readQueueLink(){const r=currentRoute();if(!['incidents','cases'].includes(r.page)||r.id||!r.search)return;const p=new URLSearchParams(r.search),t=tableState(r.page);for(const key of ['severity','status','source','owner','tag','minPriority','start','end'])t[key]=p.get(key)||'';t.query=p.get('q')||'';if(r.page==='cases'){t.dataset=['aisoc','design'].includes(p.get('data'))?p.get('data'):'all';if(p.has('data')){t.priorityBand='';t.classification='';t.investigation='';t.category='';t.sort='';t.direction=1;}}t.page=1;}
  function openModal(type,extra={}){ui.modal={type,...extra};render();}
  function showDrawer(type,id){ui.drawer={type,id};ui.drawerTab='overview';render();}
  const workspaceView=window.createReferenceWorkspace({store,ui,esc,I,btn,badge,date,severity,state,empty,getAlert,getAsset,scopeAlerts,currentRoute,currentCase,render,save,toast,logActivity});
  const investigationView=window.createInvestigationWorkspace({store,esc,I,btn,badge,severity,state,currentRoute,currentCase,scopeAlerts,getAlert,getAsset,navigate,render,downloadFile});
  document.addEventListener('click',async event=>{
    const el=event.target.closest('[data-action]');if(!el){const row=event.target.closest('[data-preview-id]');if(row&&!event.target.closest('a,button,input,select'))showDrawer(row.dataset.previewType||'incident',row.dataset.previewId);return;}if(el.disabled)return;
    event.preventDefault();const action=el.dataset.action,id=el.dataset.id,key=el.dataset.key;
    if(investigationView.handle(action,id)||workspaceView.handle(action,id))return;
    switch(action){
      case 'case-data':{const hash='#/cases?data='+id;if(location.hash===hash){readQueueLink();render();}else navigate(hash);break;}
      case 'stub':toast('该入口仅保留名称，本次聚焦告警、事件和 Case');break;
      case 'refresh':render();toast('已刷新记录');break;
      case 'alert':showDrawer('alert',id);break;
      case 'incident-preview':showDrawer('incident',id);break;
      case 'case-preview':showDrawer('case',id);break;
      case 'open-incident':navigate('#/incidents/'+id+'/attack');break;
      case 'open-case':navigate('#/cases/'+id+'/overview');break;
      case 'entity':showDrawer('entity',id);break;
      case 'evidence':showDrawer('evidence',id);break;
      case 'activity':showDrawer('activity',id);break;
      case 'investigation':showDrawer('investigation',id);break;
      case 'similar-alerts':showDrawer('similar-alerts',id);break;
      case 'close-drawer':ui.drawer=null;render();break;
      case 'drawer-tab':ui.drawerTab=id;render();break;
      case 'close-modal':closeModal();break;
      case 'full-alert':navigate('#/alerts/'+id);break;
      case 'alert-evidence':navigate('#/incidents/'+getAlert(id).incidentId+'/evidence');break;
      case 'manage-alert':openModal(action,{ids:[id]});break;
      case 'bulk-manage':{const ctx=tableContexts.get(id||'alerts');const ids=tableState(id||'alerts').selected.filter(aid=>getAlert(aid)&&ctx?.rows.some(row=>row.id===aid));if(!ids.length){toast('请先勾选需要管理的告警');break;}openModal(action,{ids,key:id||'alerts'});break;}
      case 'manage-incident':case 'manage-case':openModal(action,{id});break;
      case 'bulk-incidents':{const ids=tableState('incidents').selected.filter(aid=>tableContexts.get('incidents')?.rows.some(r=>r.id===aid));if(!ids.length){toast('请先勾选需要管理的事件');break;}openModal(action,{ids});break;}
      case 'choose-incident':case 'choose-case':openModal(action);break;
      case 'columns':case 'filter':case 'date-filter':openModal(action,{key:id});break;
      case 'save-alerts':{
        const data=Object.fromEntries(new FormData($('#manage-form'))),ids=ui.modal.ids;
        const listManagement=ui.modal.type==='manage-alert'||(ui.modal.type==='bulk-manage'&&ui.modal.key==='alerts'),fields=listManagement?['status','owner']:['status','owner','classification'];
        for(const aid of ids){const a=getAlert(aid);renderAlertDetail.prepare(a);if(a.detailMaterial){const time=new Date().toISOString();if(data.owner&&data.owner!==a.owner)a.detailMaterial.history.push({time,title:'告警分配',description:`${CURRENT_USER_NAME}：${a.owner} → ${data.owner}`});if(data.status&&data.status!==a.status)a.detailMaterial.history.push({time,title:data.status==='Resolved'?'告警关闭':'告警状态变更',description:`${CURRENT_USER_NAME}：${stateNames[a.status]} → ${stateNames[data.status]}`});}for(const field of fields)if(data[field])a[field]=data[field];if(data.comment.trim())a.comments.push({text:data.comment.trim(),time:new Date().toISOString(),author:'Alex Wilber'});logActivity(listManagement?'更新告警状态、负责人或评论':'更新告警分类、状态或负责人','告警管理',a.title,a.incidentId,store.cases.filter(c=>c.alertIds.includes(aid)).map(c=>c.id));}
        save();ui.modal=null;render();toast(`已保存 ${ids.length} 条告警`);break;
      }
      case 'save-scope':{
        const m=ui.modal,list=m.type==='manage-case'?store.cases:store.incidents,item=list.find(x=>x.id===m.id),data=Object.fromEntries(new FormData($('#manage-form')));if(!data.title?.trim()){$('#modal-error').textContent='请填写名称。';break;}if(data.status==='Resolved'&&item.status!=='Resolved'&&!data.resolutionNote?.trim()){$('#modal-error').textContent='请填写结案说明。';break;}window.referenceWorkspaces.updateCase(store,item,{...data,title:data.title.trim()});logActivity(`更新${m.type==='manage-case'?'Case':'事件'}资料`,'管理',item.title,m.type==='manage-case'?item.incidentId:item.id,m.type==='manage-case'?[item.id]:store.cases.filter(c=>c.incidentId===item.id).map(c=>c.id));save();ui.modal=null;render();toast('修改已保存');break;
      }
      case 'save-incidents':{
        const m=ui.modal,bulk=m.type==='bulk-incidents',ids=bulk?m.ids:[m.id],data=Object.fromEntries(new FormData($('#manage-incidents-form'))),targets=store.incidents.filter(x=>ids.includes(x.id));
        if(!bulk&&!data.title.trim()){$('#modal-error').textContent='请填写事件名称。';break;}
        if(data.status==='Resolved'&&targets.some(x=>x.status!=='Resolved')&&!data.note.trim()){$('#modal-error').textContent='解决事件时请填写解决说明。';break;}
        for(const inc of targets){
          const ownerChanged=!!data.owner&&data.owner!==inc.owner,resolving=data.status==='Resolved'&&inc.status!=='Resolved';
          for(const k of ['severity','status','owner','classification'])if(data[k])inc[k]=data[k];
          if(!bulk)inc.title=data.title.trim();
          const tags=data.tags.split(/[,，]/).map(x=>x.trim()).filter(Boolean);inc.tags=bulk?[...new Set([...inc.tags,...tags])]:tags;
          if(data.note.trim())inc.resolutionNote=data.note.trim();inc.updated=new Date().toISOString();
          for(const a of incidentAlerts(inc)){if(ownerChanged)a.owner=inc.owner;if(resolving)a.status='Resolved';}
          logActivity((resolving?'解决事件':'更新事件资料')+(data.note.trim()?'：'+data.note.trim():''),'事件管理',inc.title,inc.id,store.cases.filter(c=>c.incidentId===inc.id).map(c=>c.id));
        }
        save();ui.modal=null;render();toast(`已保存 ${targets.length} 个事件`);break;
      }
      case 'quick-filter':{const t=tableState(key);if(key==='alerts'&&['severity','status','owner'].includes(el.dataset.field)){t[el.dataset.field]=el.dataset.value;t.page=1;render();}break;}
      case 'save-filter':{const t=tableState(ui.modal.key),data=Object.fromEntries(new FormData($('#filter-form')));for(const field of ['severity','status','source','owner','tag','minPriority','priorityBand','classification','investigation','category'])t[field]=data[field]||'';t.page=1;closeModal();break;}
      case 'save-columns':{const cols=new FormData($('#columns-form')).getAll('columns');if(!cols.length){$('#modal-error').textContent='请至少保留一列。';break;}tableState(ui.modal.key).columns=cols;closeModal();break;}
      case 'save-dates':{const data=Object.fromEntries(new FormData($('#date-form')));if(ui.modal.key==='cases'&&data.range!=='custom'){const end=Date.parse(caseDateEnd()+':59+08:00');data.end=caseDateEnd();data.start=new Date(end-Number(data.range)*86400000+1000+8*3600000).toISOString().slice(0,16);}if(data.start&&data.end&&data.start>data.end){$('#modal-error').textContent='结束时间需要晚于开始时间。';break;}Object.assign(tableState(ui.modal.key),data,{page:1});closeModal();break;}
      case 'clear-filters':{Object.assign(tableState(id),{dataset:'all',query:'',severity:'',status:'',source:'',start:'',end:'',owner:'',tag:'',minPriority:'',priorityBand:'',classification:'',investigation:'',category:'',range:'7',page:1});if(id==='cases')ui.caseFilterSet='';render();break;}
      case 'save-case-filter-set':openModal('case-filter-set');break;
      case 'confirm-case-filter-set':{const name=new FormData($('#filter-set-form')).get('name').trim();if(!name){$('#modal-error').textContent='请填写筛选集名称。';break;}const filters=Object.fromEntries(caseFilterFields.map(k=>[k,tableState('cases')[k]])),sets=store.caseFilterSets||=[],existing=sets.find(x=>x.name===name),item={id:existing?.id||'filters-'+Date.now(),name,filters};store.caseFilterSets=existing?sets.map(x=>x===existing?item:x):[...sets,item];ui.caseFilterSet=item.id;save();closeModal();toast('已保存并应用筛选集');break;}
      case 'remove-filter':tableState(key)[el.dataset.field]='';tableState(key).page=1;render();break;
      case 'sort':{if(key==='alerts'&&!alertListColumns.some(c=>c.key===el.dataset.field&&c.sortable))break;const t=tableState(key);t.direction=t.sort===el.dataset.field?-t.direction:1;t.sort=el.dataset.field;render();break;}
      case 'prev-page':tableState(id).page=Math.max(1,tableState(id).page-1);render();break;
      case 'next-page':tableState(id).page++;render();break;
      case 'export':exportTable(id);break;
      case 'asset-type':ui.assetType=id;render();break;
      case 'evidence-type':ui.evidenceType=id;render();break;
      case 'to-tab':{const r=currentRoute();ui.drawer=null;ui.modal=null;navigate(`#/${r.page}/${r.id||currentIncident().id}/${id}`);break;}
      case 'graph-node':ui.graph.selected=id;render();break;
      case 'graph-alert':{const a=getAlert(id);ui.graph.alert=id;ui.graph.selected=a.entityIds[0];ui.graph.index=99;render();break;}
      case 'graph-type':ui.graph.hidden.has(id)?ui.graph.hidden.delete(id):ui.graph.hidden.add(id);render();break;
      case 'graph-reset':stopPlaying();Object.assign(ui.graph,{severity:'',status:'',source:'',zoom:1,index:99,blast:false,alert:null});ui.graph.hidden.clear();render();break;
      case 'zoom-in':ui.graph.zoom=Math.min(1.7,ui.graph.zoom+.15);render();break;
      case 'zoom-out':ui.graph.zoom=Math.max(.55,ui.graph.zoom-.15);render();break;
      case 'zoom-reset':ui.graph.zoom=1;render();break;
      case 'blast':ui.graph.blast=!ui.graph.blast;render();break;
      case 'play':{
        if(ui.playing){stopPlaying();render();break;}ui.graph.index=0;
        ui.playing=setInterval(()=>{const max=Number($('#playback')?.max||0);if(ui.graph.index>=max){stopPlaying();render();return;}ui.graph.index++;render();},1000);render();break;
      }
      case 'case-summary-toggle':ui.caseCollapsed=!ui.caseCollapsed;render();break;
      case 'feedback':ui.feedback=id;render();toast('已记录对摘要的反馈（演示）');break;
      case 'move-case':{const ids=tableState('case-alerts').selected.filter(aid=>currentCase().alertIds.includes(aid));if(!ids.length){toast('请先勾选要移动的告警');break;}openModal(action,{ids,from:currentCase().id});break;}
      case 'save-move':{const m=ui.modal,target=store.cases.find(c=>c.id===new FormData($('#move-form')).get('caseId')),source=store.cases.find(c=>c.id===m.from);if(!target)break;source.alertIds=source.alertIds.filter(aid=>!m.ids.includes(aid));target.alertIds=[...new Set([...target.alertIds,...m.ids])];logActivity(`移动 ${m.ids.length} 条告警至 Case ${target.id}`,'案件关联',target.title,source.incidentId,[source.id,target.id]);tableState('case-alerts').selected=[];save();ui.modal=null;render();toast(`已移动至 Case ${target.id}`);break;}
      case 'approve-evidence':case 'reject-evidence':openModal(action,{id});break;
      case 'confirm-evidence':{const m=ui.modal,e=store.evidence.find(x=>x.id===m.id),yes=m.type==='approve-evidence',a=getAlert(e.alertId);e.remediation=yes?'Remediated':'Rejected';logActivity((yes?'批准并完成模拟响应：':'拒绝模拟响应：')+e.name,'响应审批',e.name,a.incidentId,store.cases.filter(c=>c.alertIds.includes(a.id)).map(c=>c.id));save();ui.modal=null;render();toast(yes?'已批准并完成演示动作':'已拒绝演示动作');break;}
      case 'simulate-response':if(getAsset(id).isolated){toast('此设备已处于模拟隔离状态');break;}openModal(action,{id});break;
      case 'confirm-response':{const a=getAsset(ui.modal.id);a.isolated=true;const linked=store.alerts.find(x=>x.entityIds.includes(a.id));logActivity('模拟隔离设备','设备响应',a.name,linked?.incidentId,store.cases.filter(c=>caseAlerts(c).some(x=>x.entityIds.includes(a.id))).map(c=>c.id));save();ui.modal=null;render();toast('设备已标记为已隔离（演示）');break;}
      case 'reset':openModal(action);break;
      case 'confirm-reset':stopPlaying();for(const key of Object.keys(store))delete store[key];Object.assign(store,window.makeDemoData());window.mergeReplayedAlerts?.(store);window.mergeAiSoc20Data?.(store);window.mergePersistedCaseData?.(store);window.alertFlowWorkspace?.merge(store);seedAssetTags();save();ui.tables={};ui.modal=null;ui.drawer=null;ui.graph.index=99;render();toast('已恢复初始演示数据');break;
      case 'copy':try{await navigator.clipboard.writeText(id);toast('已复制告警 ID');}catch{toast('告警 ID：'+id);}break;
      case 'copy-queue-link':{const t=tableState('incidents'),p=new URLSearchParams();for(const k of ['severity','status','source','owner','tag','minPriority','start','end'])if(t[k])p.set(k,t[k]);if(t.query)p.set('q',t.query);const url=location.origin+location.pathname+'#/incidents'+(p.size?'?'+p:'');try{await navigator.clipboard.writeText(url);toast('已复制含当前筛选条件的事件列表链接');}catch{toast(url);}break;}
      case 'attachment':{
        if(id.endsWith('.csv')){const rows=scopeEvidence();downloadFile(id,'\uFEFF'+['证据,类型,判定,处置状态',...rows.map(e=>[e.name,e.type,verdictNames[e.verdict],stateNames[e.remediation]].map(csvValue).join(','))].join('\r\n'),'text/csv;charset=utf-8');}
        else downloadFile(id,`Case ${currentCase().id}\n${currentCase().title}\n\n${currentCase().description}\n\n调查备注\n${store.comments.filter(c=>c.caseId===currentCase().id).map(c=>`${c.author}: ${c.text}`).join('\n')}\n\n此文件为前端演示资料。`);toast('已下载演示附件');break;
      }
    }
  });
  document.addEventListener('input',event=>{
    const el=event.target;
    if(el.dataset.query){tableState(el.dataset.query).query=el.value;tableState(el.dataset.query).page=1;render();}
    if(el.hasAttribute('data-playback')){stopPlaying();ui.graph.index=Number(el.value);render();}
  });
  document.addEventListener('change',event=>{
    const el=event.target;
    if(investigationView.change(el))return;
    if(el.hasAttribute('data-ws-scope')){ui.graph.associated=el.value==='associated';ui.graph.alert=null;ui.graph.edge=null;ui.graph.blast=false;ui.graph.index=99;render();return;}
    if(el.dataset.wsTask){workspaceView.changeTask(el.dataset.wsTask,el.value);return;}
    if(el.hasAttribute('data-case-filter-set')){if(el.value==='create'){openModal('case-filter-set');return;}const selected=store.caseFilterSets?.find(s=>s.id===el.value);ui.caseFilterSet=el.value;if(selected)Object.assign(tableState('cases'),selected.filters,{page:1});render();}
    if(el.hasAttribute('data-case-auto')){ui.caseAuto=el.checked;if(ui.caseAutoTimer)clearInterval(ui.caseAutoTimer);ui.caseAutoTimer=ui.caseAuto?setInterval(()=>{if(currentRoute().page==='cases'&&!currentRoute().id&&!ui.modal&&!ui.drawer&&document.activeElement?.tagName!=='INPUT')render();},30000):null;render();}
    if(el.dataset.selectRow){const t=tableState(el.dataset.selectRow);t.selected=el.checked?[...new Set([...t.selected,el.dataset.id])]:t.selected.filter(id=>id!==el.dataset.id);render();}
    if(el.dataset.selectAll){const key=el.dataset.selectAll,t=tableState(key),ctx=tableContexts.get(key),rows=filteredRows(key,ctx.rows).slice((t.page-1)*t.size,t.page*t.size),ids=rows.map(r=>r.id);t.selected=el.checked?[...new Set([...t.selected,...ids])]:t.selected.filter(id=>!ids.includes(id));render();}
    if(el.dataset.pageSize){tableState(el.dataset.pageSize).size=Number(el.value);tableState(el.dataset.pageSize).page=1;render();}
    if(el.dataset.graphFilter){ui.graph[el.dataset.graphFilter]=el.value;ui.graph.index=99;render();}
    if(el.hasAttribute('data-graph-layout')){ui.graph.layout=el.value;render();}
    if(el.hasAttribute('data-graph-grouped')){ui.graph.grouped=el.checked;render();}
  });
  let draggedColumn=null;
  document.addEventListener('dragstart',event=>{const row=event.target.closest('[data-column]');if(row){draggedColumn=row;event.dataTransfer.effectAllowed='move';}});
  document.addEventListener('dragover',event=>{if(draggedColumn&&event.target.closest('[data-column]'))event.preventDefault();});
  document.addEventListener('drop',event=>{const row=event.target.closest('[data-column]');if(draggedColumn&&row&&row!==draggedColumn){event.preventDefault();const before=event.clientY<row.getBoundingClientRect().top+row.offsetHeight/2;row.parentElement.insertBefore(draggedColumn,before?row:row.nextSibling);}draggedColumn=null;});
  document.addEventListener('dragend',()=>{draggedColumn=null;});
  document.addEventListener('submit',event=>{
    event.preventDefault();
    if(event.target.id==='workspace-task-form'){workspaceView.submitTask(event.target);return;}
    if(event.target.id==='comment-form'){
      const text=$('#new-comment').value.trim();if(!text)return;
      const c=currentCase();store.comments.unshift({id:'co-'+Date.now(),caseId:c.id,author:'Alex Wilber',text,time:new Date().toISOString()});logActivity('添加调查评论','评论',c.title,c.incidentId,[c.id]);save();render();toast('已添加评论');
    }
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'){if(ui.modal)closeModal();else if(ui.drawer){ui.drawer=null;render();}return;}
    if(['Enter',' '].includes(event.key)&&event.target.matches('[data-action^="ws-"]')){event.preventDefault();workspaceView.handle(event.target.dataset.action,event.target.dataset.id);}
    if(event.key==='Enter'&&event.target.matches('tr[data-preview-id]')){event.preventDefault();showDrawer(event.target.dataset.previewType||'incident',event.target.dataset.previewId);}
    if(event.key==='Tab'&&(ui.modal||ui.drawer)){
      const dialog=ui.modal?$('.modal'):$('.drawer'),items=[...dialog.querySelectorAll('button:not(:disabled), a[href], input, select, textarea, [tabindex="0"]')].filter(el=>el.getClientRects().length);
      if(!items.length)return;const first=items[0],last=items.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }
  });
  window.addEventListener('hashchange',()=>{stopPlaying();ui.drawer=null;ui.modal=null;ui.graph.index=99;ui.graph.alert=null;ui.graph.blast=false;readQueueLink();render();window.scrollTo({top:0,behavior:'instant'});});
  if(!location.hash)history.replaceState(null,'','#/alerts');
  const renderAlertDetail=window.createAlertDetail({store,esc,date,I,btn,badge,severity,state,entityChip:alertAssetLink,getAsset,save,render,navigate,toast,breadcrumbs,tabsMarkup});
  readQueueLink();render();
})();
