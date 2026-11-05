'use strict';
window.makeDemoData = function makeDemoData() {
  const people = ['Alex Wilber', 'Megan Bowen', 'Patti Fernandez', '未分配'];
  const assets = [
    {id:'d1',type:'device',name:'cont-adrianbrad',domain:'CONTOSO',os:'Windows 11',risk:'高',ip:'10.0.161.135',critical:true},
    {id:'d2',type:'device',name:'fin-ws-023',domain:'CONTOSO',os:'Windows 10',risk:'高',ip:'172.16.45.29'},
    {id:'d3',type:'device',name:'srv-ad-01',domain:'CONTOSO',os:'Windows Server 2022',risk:'中',ip:'172.16.45.42',critical:true},
    {id:'u1',type:'user',name:'hcook@contoso.com',displayName:'Holly Cook',department:'Finance',risk:'高',role:'财务分析员'},
    {id:'u2',type:'user',name:'meganb@contoso.com',displayName:'Megan Bowen',department:'Operations',risk:'中',role:'业务运营'},
    {id:'u3',type:'user',name:'pattif@contoso.com',displayName:'Patti Fernandez',department:'IT',risk:'低',role:'系统管理员'},
    {id:'ip1',type:'ip',name:'203.0.113.50',risk:'高',location:'Madrid, Spain',provider:'Example hosting'},
    {id:'ip2',type:'ip',name:'198.51.100.98',risk:'中',location:'Amsterdam, Netherlands',provider:'Example cloud'},
    {id:'f1',type:'file',name:'invoice_2026.pdf.exe',risk:'高',hash:'b604e516f760ed4b3bf2cc96a21d3c746d6f8a808c5713fb4d142c01d487ed0a'},
    {id:'m1',type:'mailbox',name:'hcook@contoso.com',risk:'高',domain:'contoso.com',kind:'用户邮箱'},
    {id:'a1',type:'app',name:'Contoso Document Sync',risk:'中',publisher:'Contoso',permissions:'Files.ReadWrite.All'},
    {id:'c1',type:'cloud',name:'finance-storage-prod',risk:'中',provider:'Microsoft Azure',region:'East Asia'},
    {id:'ai1',type:'robot',name:'Contoso Finance Assistant',risk:'低',publisher:'Contoso',permissions:'只读财务知识库'},
  ];
  const names = [
    'Authentication request from AiTM-related phishing page',
    '用户访问了随后被隔离的邮件链接',
    'Unfamiliar sign-in properties',
    '检测到可疑的 PowerShell 命令行',
    'Sensitive credential memory read',
    'Possible misuse of DCSync attack',
    '异常外部 IP 的出站连接',
    '可疑的文件打包与归档行为',
    '向未知云应用上传敏感文件',
    'Identity Created',
    'Device Info Alert evidence',
    '新增具有高权限的 OAuth 应用',
    '异常登录后的邮箱转发规则',
    'Malicious URL detected in Proxy logs',
    'Compromised account conducting hands-on-keyboard activity',
    '可疑的远程服务执行',
    'Atypical travel',
    'Suspicious access to LSASS service',
    'ADFS private key extraction attempt',
    '来自未受管理设备的高风险登录',
    'DLP policy: Financial data matched for sharing',
    '可疑的计划任务创建',
    '用户报告了一封钓鱼邮件',
    '授权安全演练中的凭据访问行为',
  ];
  const sources = ['Microsoft Defender for Office 365','Microsoft Entra ID Protection','Microsoft Defender for Endpoint','Microsoft Sentinel','Microsoft Defender for Identity'];
  const sourceByAlert = [0,0,1,2,2,4,3,2,3,1,2,1,0,3,2,2,1,2,4,1,0,2,0,3];
  const categoryByAlert = ['初始访问','初始访问','初始访问','执行','凭据访问','凭据访问','命令与控制','收集','数据外泄','持久化','发现','持久化','收集','命令与控制','横向移动','横向移动','初始访问','凭据访问','凭据访问','初始访问','数据外泄','持久化','初始访问','凭据访问'];
  const alerts = names.map((title,i) => {
    const n = i < 14 ? '262144' : i < 20 ? '337075' : '2152';
    const stamp = new Date(Date.UTC(2026,9,24,0,40+i*6)).toISOString();
    return {id:`da63896${String(4100+i).padStart(6,'0')}`,title,severity:i%7===6?'低':i%4===2?'中':'高',status:i>19?'Resolved':i%4===0?'In progress':'New',classification:i>19?(i===23?'Informational':'True positive'):'Not set',owner:i%4===2?people[0]:i>19?people[2]:'未分配',source:sources[sourceByAlert[i]],category:categoryByAlert[i],tags:i===0?['AiTM attack','Credential Phish']:i===23?['安全演练']:i%5===0?['关键资产']:[],investigation:i>19?'Completed':i%5===2?'Pending':i%3===0?'In progress':'New',first:stamp,last:new Date(Date.parse(stamp)+180000).toISOString(),incidentId:n,entityIds:i<3?['u1','m1','ip1']:i<9?['d1','u1','ip1','f1']:i<14?['d2','u1','a1','c1']:['d3','u2','ip2'],description:`${title}。安全检测发现与当前事件相关的活动，请结合实体上下文、事件时间线和关联证据进一步评估。`,comments:[]};
  });
  const incidents = [
    {id:'262144',title:'涉及初始访问与数据外泄的多阶段事件',severity:'高',status:'In progress',owner:'Alex Wilber',priority:81,classification:'未分类',tags:['Credential Phish','AiTM attack','关键资产'],description:'攻击者通过 AiTM 钓鱼页面获取用户会话，随后在终端执行可疑脚本，尝试访问凭据并向外部地址传输文件。',entityIds:['d1','d2','d3','u1','u2','ip1','ip2','f1','m1','a1','c1'],critical:true},
    {id:'337075',title:'涉及单个用户的初始访问事件',severity:'中',status:'New',owner:'未分配',priority:54,classification:'未分类',tags:['Initial access'],description:'同一账号出现来自多个地址的异常登录，需要进一步核对是否为授权行为。',entityIds:['d3','u2','ip2']},
    {id:'2152',title:'通过 AiTM 钓鱼发起的攻击',severity:'高',status:'Resolved',owner:'Patti Fernandez',priority:72,classification:'真实威胁',tags:['Attack Disruption','AiTM'],description:'钓鱼邮件及相关会话已完成模拟处置，保留证据供复核。',entityIds:['d3','u2','ip2','m1']},
  ];
  const cases = [
    {id:'17420',title:'Identity Created involving one user1',severity:'高',status:'New',owner:'未分配',priority:35,description:'汇集身份创建、异常登录与终端活动的调查材料，确认用户账号与设备是否受到影响。',alertIds:[alerts[9],alerts[10],...alerts.slice(0,9)].map(a=>a.id),incidentId:'262144',critical:true,created:'2026-10-24T01:10:00Z'},
    {id:'17421',title:'异常账号活动与远程访问复核',severity:'中',status:'In progress',owner:'Megan Bowen',priority:48,description:'核对异常账号活动及远程访问的范围。',alertIds:alerts.slice(14,20).map(a=>a.id),incidentId:'337075',created:'2026-10-24T02:00:00Z'},
  ];
  const extraIncidents = [
    ['248940','多个终端上的持久化与凭据访问活动','高','In progress','Megan Bowen',93,['关键资产','Credential Access']],
    ['249923','涉及身份与数据外泄的多阶段事件','高','New','未分配',89,['Identity']],
    ['249938','单个终端上的可疑远程执行','中','New','未分配',64,['Endpoint']],
    ['249941','检测到 Vigor 恶意软件','高','In progress','Patti Fernandez',92,['关键资产']],
    ['247223','多个资源上的横向移动活动','高','New','Alex Wilber',86,['Lateral movement']],
    ['246613','涉及持久化与命令控制的多阶段事件','中','Resolved','Megan Bowen',58,['Attack Disruption']],
    ['242240','身份风险与邮箱转发规则异常','中','New','未分配',61,['Identity']],
    ['239225','多个设备上的安全策略规避活动','高','In progress','Patti Fernandez',78,['Endpoint']],
    ['248891','云存储中的异常共享与访问','低','Resolved','Alex Wilber',32,['Cloud']],
  ];
  extraIncidents.forEach(([id,title,severity,status,owner,priority,tags],k)=>{
    const newAlerts=Array.from({length:3},(_,j)=>{
      const base=alerts[(k*2+j)%20],first=new Date(Date.UTC(2026,9,24-Math.floor(k/3),1+k%3,j*8));
      return {...base,id:`demo-alert-${id}-${j+1}`,incidentId:id,status,owner,classification:status==='Resolved'?'True positive':'Not set',investigation:status==='Resolved'?'Completed':'New',severity,comments:[],first:first.toISOString(),last:new Date(+first+180000).toISOString()};
    });
    alerts.push(...newAlerts);
    incidents.push({id,title,severity,status,owner,priority,tags,classification:status==='Resolved'?'True positive':'Not set',description:`${title}。已关联${newAlerts.length}条告警，可从攻击故事、资产和活动记录核对上下文。`,entityIds:[...new Set(newAlerts.flatMap(a=>a.entityIds))],critical:tags.includes('关键资产')});
  });
  incidents.forEach(inc=>{
    const linked=alerts.filter(a=>a.incidentId===inc.id).sort((a,b)=>Date.parse(a.first)-Date.parse(b.first));
    inc.first=linked[0]?.first||'2026-10-24T00:00:00Z';inc.last=linked.at(-1)?.last||inc.first;inc.updated=inc.last;
    if(inc.classification==='未分类')inc.classification='Not set';
    if(inc.classification==='真实威胁')inc.classification='True positive';
  });
  incidents.filter(inc=>!cases.some(c=>c.incidentId===inc.id)).forEach((inc,i)=>{
    cases.push({id:String(17422+i),title:inc.title+'调查',severity:inc.severity,status:inc.status,owner:inc.owner,priority:inc.priority,description:inc.description,alertIds:alerts.filter(a=>a.incidentId===inc.id).map(a=>a.id),incidentId:inc.id,critical:!!inc.critical,created:inc.first,updated:inc.updated,tags:inc.tags.slice()});
  });
  cases.forEach(c=>{c.updated ||= c.created;c.tags ||= c.critical?['关键资产']:[];});
  const evidence = [
    {id:'ev1',name:'AiTM-related phishing page',type:'URL',entityId:'ip1',alertId:alerts[0].id,verdict:'Malicious',remediation:'Pending approval',origin:'邮件检测',threat:'Credential phishing'},
    {id:'ev2',name:'invoice_2026.pdf.exe',type:'文件',entityId:'f1',alertId:alerts[3].id,verdict:'Malicious',remediation:'Pending approval',origin:'终端检测',threat:'Trojan:Win32/Example'},
    {id:'ev3',name:'203.0.113.50',type:'IP 地址',entityId:'ip1',alertId:alerts[6].id,verdict:'Suspicious',remediation:'Not started',origin:'网络连接',threat:'异常外联'},
    {id:'ev4',name:'powershell.exe -EncodedCommand …',type:'进程',entityId:'d1',alertId:alerts[3].id,verdict:'Suspicious',remediation:'Remediated',origin:'终端检测',threat:'可疑脚本'},
    {id:'ev5',name:'hcook@contoso.com',type:'云登录会话',entityId:'u1',alertId:alerts[2].id,verdict:'Suspicious',remediation:'Pending approval',origin:'身份检测',threat:'会话令牌滥用'},
    {id:'ev6',name:'Quarterly finance report',type:'邮件',entityId:'m1',alertId:alerts[1].id,verdict:'Malicious',remediation:'Remediated',origin:'邮件检测',threat:'钓鱼邮件'},
    {id:'ev7',name:'Contoso Document Sync',type:'云应用',entityId:'a1',alertId:alerts[8].id,verdict:'Suspicious',remediation:'Not started',origin:'云应用检测',threat:'异常数据访问'},
    {id:'ev8',name:'finance-storage-prod',type:'云资源',entityId:'c1',alertId:alerts[8].id,verdict:'Clean',remediation:'No action needed',origin:'云资源检测',threat:'未发现威胁'},
  ];
  const activities = [
    ['已将关联告警添加至事件','告警关联','Microsoft Defender XDR','Completed','自动'],
    ['已完成初始分诊与优先级评估','分诊','Microsoft Defender XDR','Completed','自动'],
    ['已发现关联的异常身份活动','关联分析','Microsoft Sentinel','Completed','自动'],
    ['分析员更新了事件负责人','人员分派','Alex Wilber','Completed','人工'],
    ['自动调查收集终端与网络证据','调查','Automated investigation','Completed','自动'],
    ['文件隔离操作等待审批','响应','Microsoft Defender for Endpoint','Pending','自动'],
    ['补充数据外泄的调查备注','分析备注','Alex Wilber','Completed','人工'],
    ['外部连接查询未完成','调查','Automated investigation','Failed','自动'],
  ].map((x,i)=>({id:`act${i}`,title:x[0],type:x[1],performedBy:x[2],status:x[3],trigger:x[4],target:i===5?'invoice_2026.pdf.exe':'cont-adrianbrad',time:new Date(Date.UTC(2026,9,24,1,10+i*8)).toISOString(),incidentId:'262144',caseIds:['17420']}));
  alerts.push({id:'alert-unassigned-case-001',title:'Web 服务器出现异常外联',description:'Web 服务器 cont-adrianbrad 向外部地址 203.0.113.50 发起异常连接，需要核对进程、访问用途及授权记录。',severity:'高',status:'New',classification:'Not set',owner:'未分配',source:'Microsoft Defender for Endpoint',category:'命令与控制',tags:[],investigation:'New',first:'2026-10-24T11:59:57Z',last:'2026-10-24T12:00:22Z',event_time:'2026-10-24T11:59:57Z',incidentId:'262144',entityIds:['d1','ip1'],comments:[]});
  return {version:1,people,assets,alerts,incidents,cases,evidence,activities,comments:[{id:'co1',caseId:'17420',author:'Alex Wilber',text:'已核对异常登录与终端活动的时间关联，请继续确认外联目标和文件传输范围。',time:'2026-10-24T02:15:00Z'}]};
};
