/* Shared original workspace chrome and Case frame for demo and service adapters. */
'use strict';
window.caseWorkspaceLayout=(()=>{
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon=(name,size)=>window.icon(name,size);
  function shell({route,counts={},service=false,toolbar='',footer=''},content,overlays=''){
    const compact=route.page==='cases'&&!!route.id;
    const stub=(title,ico)=>`<div class="nav-item dim" aria-disabled="true" title="${esc(title)} · ${service?'暂未开放':'本原型仅展示名称'}">${icon(ico,18)}<span class="nav-label">${esc(title)}</span><span class="short-label">${esc(title)}</span></div>`;
    const nav=(title,ico,page,href,count,id)=>{
      if(service&&!['cases','incidents'].includes(page))return stub(title,ico);
      const selected=route.page===page&&(!id||route.id===id);
      return `<a class="nav-item ${selected?'selected':''}" href="${href}" ${selected?'aria-current="page"':''} title="${title}">${icon(ico,19)}<span class="nav-label">${title}</span><span class="short-label">${title}</span>${count?`<span class="nav-count">${count}</span>`:''}</a>`;
    };
    const platform=!service&&window.platformPreview?.sections;
    const platformGroup=section=>`<div class="side-heading">${esc(section.label)}</div>${section.modules.map(module=>nav(module.label,module.icon,'platform',`#/platform/${module.key}`,null,module.key)).join('')}`;
    const operations=platform?platform.slice(1).map(platformGroup).join(''):`<div class="side-heading">安全运营</div>${stub('高级搜寻','search')}${stub('资产','device')}${stub('威胁情报','flag')}${stub('Microsoft Sentinel','cloud')}<div class="side-heading">管理</div>${stub('报表','file')}${stub('设置','settings')}`;
    return `<header class="topbar"><span class="row"><img class="aisoc-mark" src="./assets/aisoc-mark.svg" alt=""><span class="topbar-title">AiSOC</span></span><div class="top-search" aria-hidden="true">${icon('search',15)}<span>搜索安全资源、实体和文档</span></div><div class="topbar-actions">${toolbar}</div></header><div class="layout ${service?'service-data':''}"><aside class="sidebar ${compact?'compact':''}${platform?' with-platform-preview':''}" aria-label="全局导航">${platform?platformGroup(platform[0]):stub('主页','home')}<div class="side-heading">告警和事件</div>${nav('告警','shield','alerts','#/alerts',counts.alerts)}${nav('事件','graph','incidents','#/incidents',counts.incidents)}<div class="side-heading">案件管理</div>${nav('案件','briefcase','cases','#/cases',counts.cases)}${operations}<div class="side-bottom">${footer}<p></p></div></aside><main class="workspace" id="main-content">${content}</main></div>${overlays}`;
  }
  function caseNavigation(id,selected,directory,disabled=[]){
    return `<nav class="case-nav" aria-label="Case 内部导航"><div class="case-nav-heading">Case</div>${directory.map(([key,label,ico,count],i)=>`${[2,4,7].includes(i)?`<div class="case-nav-group">${i===2?'AI 调查':i===4?'案件材料':'协作与跟进'}</div>`:''}${disabled.includes(key)?`<span class="case-nav-button disabled-label" aria-disabled="true" title="${esc(label)}暂未开放">${icon(ico,16)}${esc(label)}<small class="svc-unavailable">暂未开放</small></span>`:`<a class="case-nav-button ${selected===key?'selected':''}" href="#/cases/${encodeURIComponent(id)}/${key}" ${selected===key?'aria-current="page"':''}>${icon(ico,16)}${esc(label)}${count!==undefined?`<span class="count">${count}</span>`:''}</a>`}`).join('')}</nav>`;
  }
  function caseFrame(header,navigation,content,footer=''){
    return `${header}<div class="case-body">${navigation}<section class="case-content">${content}</section></div>${footer}`;
  }
  return {shell,caseNavigation,caseFrame};
})();
