"""从冻结 OpenAPI 与人工注释生成静态交接包；不连接服务或数据库。"""
from pathlib import Path
import copy, json, re, html, hashlib, ast, argparse
from catalog import OPERATIONS, FEATURE_MAP
from publish import enrich_contract, publish_pages
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'deliverables/investigation-validation-20261106'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=SOURCE/'http-handoff')
OUT=parser.parse_args().output.resolve()
VERSION='2026-11-13.docs10'
BASE=ROOT/'docs/design/socai2-independent-api-v2.openapi.json'
DOC=json.loads(BASE.read_text())
DOC['paths']={k:v for k,v in DOC['paths'].items() if k.startswith('/api/v1/socai2')}
SC=DOC['components']['schemas']
ID={k:f'00000000-0000-4000-8000-{i:012d}' for i,k in enumerate(['case','alert','incident','run','result','task','revision','material','artifact','user','operation','message','conversation','target'],1)}
DATE='2026-11-12T08:00:00Z'
def uid(field):
 for k in ID:
  if k in field:return ID[k]
 return ID['artifact']
DESC={
'operation_key':'客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。',
'expected_scope_revision':'读 Case 详情获得的当前范围版本；不匹配返回409。',
'expected_row_version':'读当前 Case/Task 获得的行版本；不匹配返回409。',
'expected_source_scope_revision':'源 Case 当前范围版本。','expected_target_scope_revision':'目标 Case 当前范围版本。',
'expected_current_artifact_id':'当前证据目录工件 ID；首次为null。必须显式传入，和实际旧版本比较。',
'case_id':'Case UUID；来自真实回执/列表，不是页面展示编号。','alert_id':'告警 UUID。','incident_id':'事件 UUID。','run_id':'该父主体下的执行 UUID。','result_id':'同案已保存正式结果 UUID。','task_id':'本案人工任务 UUID。','revision_id':'指定不可变任务修订 UUID。','material_id':'材料版本 UUID；历史读取使用冻结版本。','artifact_id':'工件 UUID，必须保持父主体/Run 归属。',
'identity':'subject 对应的告警或事件 UUID。','subject':'alerts 或 incidents，不能传 cases。','section':'记录分区；members仅事件、incidents仅告警。见分区表。',
'limit':'本次最多返回条数；不是总量。默认值及上限见字段约束。','offset':'分页偏移，沿 next_offset 继续。','cursor':'使用服务上一页 next_cursor；改变筛选条件后清空。','before_id':'仅无新增筛选/排序的旧调用沿next_before_id翻页；不与cursor混用。','before_run_id':'沿上页 next_before_run_id 翻页。',
'next_cursor':'下一页游标；null表示结束。','next_offset':'下一页偏移；null表示结束。','next_before_id':'下一页主体游标；null表示结束。','next_before_run_id':'下一页运行游标；null表示结束。',
'time_from':'带时区的起点，包含；告警按event_time，事件至少一条成员event_time命中，Case按business_updated_at。','time_to':'带时区的终点，不包含；两端同时传时必须晚于time_from。','sort_by':'服务排序字段，可选值见本接口枚举；记录排序字段缺值时置后，同值按UUID排序；非法sort_by返回422。','sort_order':'asc升序或desc降序，默认desc。','filtered_total':'全部筛选条件命中数，不受分页影响；total和overall_stats仍为租户整体。',
'q':'标题字面包含或精确UUID搜索；%和_按普通字符处理。','metric':'Case整体指标快捷过滤条件。','classification':'案件分类true_positive/informational/false_positive；null未设置；队列可用not_set过滤未设置。',
'due_at':'带时区的截止时间；null清空。','source':'本次资料变更来源 manual 或 import。','source_note':'资料修改原因/来源说明，非空。','source_refs':'来源引用；任务写入为type/id，读取为已冻结EvidenceRef，不能把读取对象原样回写。',
'alert_ids':'真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。','incident_ids':'显式关联事件UUID集合，服务展开成员。','target_case_id':'移动目标Case；不得等于路径源Case。',
'window_start':'窗口起点，带时区；和window_end同时提供或同时为空。','window_end':'窗口终点，带时区且不早于起点。',
'comparison_result_id':'同案比较结果ID；null表示未指定。','title':'显示标题；写入必须非空，长度约束见Schema。','description':'补充说明，可空；不是程序生成结论。','tags':'标签列表，不替代资产标签。',
'severity':'严重度枚举；null为未知，不强行补默认等级。','handling_status':'主体业务处理状态，与Run执行状态分开。','owner_id':'负责人用户UUID；人员目录由业务后端负责。','assignee_id':'人工任务负责人UUID，需真实存在于本租户；null未分配。','assignment_state':'分配状态，unresolved不等于unassigned。',
'question':'用户明确发送的问题文本；当前Q接口未实现。','conversation_id':'可选会话UUID；当前无正式对话读写。','conclusion':'本环节结论正文；null可能未交付/拒收，不补造。','origin_result_id':'创建任务时关联的同案正式结果UUID。','origin_finding_id':'该结果中的发现ID；必须同时传origin_result_id。',
'result_text':'人工确认结果正文；任务completed时必填非空。','result_scope':'人工结果适用范围；completed时必填，不得扩大到Case外。','object_keys':'对象键；explicit_objects需非空且属于所选告警当前对象。','limitations':'本次结果或阅读的限制，原样保留。',
'state':'本对象状态；含义依模型枚举，不与交付/业务判定合并。','row_version':'并发修改版本；后续写入的expected_row_version取此值。','scope_revision':'Case成员范围版本，历史Run保持冻结值。','revision':'材料或任务修订序号。','current_revision_id':'任务当前不可变修订ID。','current':'当前有效读取对象；可能为空，不能用最近失败尝试替代。',
'changed':'本次写入是否实际改变业务内容；幂等重读不表示重新执行。','created':'是否本次新建pending记录；false可能复用已有待启动项。','pending_run_id':'准备好的待启动Run；需要用户显式调用start。',
'current_assessment':'当前采用判断及来源/覆盖；null表示未形成，不能自行采用最近结果。','assessment':'已采用判断的页面投影。','evidence':'已发布证据目录及可用状态。','index':'证据目录版本正文，不是自动生成证据的命令。','supersedes_artifact_id':'被替换的证据目录工件；首次为null。',
'availability':'正文是否可用；200仅代表读取请求成功。available/retained_*/大小限制/外部正文未载入分开展示。','material_state':'complete/truncated/summary_only/unavailable，保持原材料状态。','content_json':'保存的结构化正文；格式由工件schema_version和实际类型决定。','content_text':'保存的文本正文，可空；不得自动重生成。','metadata':'A/I工件/材料元数据。','artifact':'Case工件元数据，和A/I的metadata字段不同。',
'questions':'未解决问题，作为该轮调查结论的一部分；无独立负责人/关闭/跨轮合并流程。','recommendations':'建议；不表示批准或执行。','findings':'该轮发现及来源范围；不能跨成员扩大或缩小。','closing_note':'系统收尾说明，与模型业务结论区分。','validation_state':'程序校验状态，不代表结论准确率。','delivery_state':'交付完整性 none/partial/complete/unknown，与执行状态分开。',
'confidence':'AI分诊置信度0..1，不是恶意概率；详情的confidence_percent已乘100。','usage':'调用数、token、费用；未知值保留null/unknown计数。','total':'当前集合总数；records/assets为对象资产匹配边数。','metrics':'Case租户整体指标，不随分页或筛选total变化。','overall_stats':'主体整体统计；按原口径和observed_at展示。','observed_at':'本次读取观察时间。','start_eligibility':'是否可启动及原因，依据最新Run与Case范围。','can_start':'服务给出的启动资格，不由前端从状态猜测。','reason':'服务返回原因；不代表adopt已有reason请求参数。',
'raw_text':'保留的原始文本。','raw_json':'保留的原始JSON。','ocsf_json':'标准化事件正文。','enrichment':'已有富化内容。','detection':'实际检测信息及分数/ATT&CK标签。','source_scope':'原材料来源范围合同。','retention':'保留/截断说明。','sha256':'原件内容摘要；不等于业务结论验证。',
}
for name,s in SC.items():
 if name in ['GroupingQuery','GroupingSummary']:continue
 for field,p in s.get('properties',{}).items():
  if field in DESC:p['description']=DESC[field]
  elif field.endswith('_truncated'):p['description']='集合是否被读取上限截断；true时不能声称全量。'
  elif field.endswith('_at'):p['description']='服务记录的带时区时间；null表示未记录/不可得。'
  elif field.endswith('_by'):p['description']='服务保存的操作者用户UUID；null表示未记录。'
  elif field.endswith('_id'):p['description']='原合同中的关联UUID；从对应父主体真实响应获取，不使用名称代替。'

# 补充旧导出中没有形状的冻结材料响应：只记录实际行结构，不改变服务。
props={}
for k in ['id','tenant_id','alert_id']:props[k]={'type':'string','format':'uuid'}
props.update(revision={'type':'integer','minimum':1},received_at={'type':'string','format':'date-time'})
for k in ['source_version','raw_text','sha256']:props[k]={'type':['string','null']}
for k in ['raw_json','ocsf_json','enrichment']:props[k]={'type':['object','null'],'additionalProperties':True}
for k in ['detection','source_scope','retention']:props[k]={'type':'object','additionalProperties':True}
props['material_state']={'type':'string','enum':['complete','truncated','summary_only','unavailable']}
for k,p in props.items():p['description']=DESC.get(k,k)
SC['FrozenAlertMaterial']={'type':'object','properties':props,'required':list(props),'description':'Run冻结材料的原始行；不包装ContentView。嵌套业务JSON见json-contracts.json。'}

# 读取分区中动态记录的字段：从本仓库模型提取用于文档，不导入/运行ORM。
modeltree=ast.parse((ROOT/'services/api/app/models/socai2.py').read_text())
private={'tenant_id','source_identity_key','operation_key','request_hash','source_operation_id','operation_id','blob_ref'}
def row_schema(class_name):
 c=next(x for x in modeltree.body if isinstance(x,ast.ClassDef) and x.name==class_name)
 p={}
 for n in c.body:
  if not isinstance(n,ast.AnnAssign) or not isinstance(n.target,ast.Name):continue
  k=n.target.id
  if k in private:continue
  typ=ast.unparse(n.annotation)
  sql=ast.unparse(n.value)
  t='object' if 'JSONB' in sql else 'array' if 'ARRAY' in sql else 'integer' if 'int' in typ else 'number' if 'Decimal' in typ or 'float' in typ else 'boolean' if 'bool' in typ else 'string'
  f={'type':t,'description':DESC.get(k,k)}
  if '| None' in typ:f['type']=[t,'null']
  if t=='array':f['items']={'type':'string'}
  if 'UUID' in typ:f['format']='uuid'
  if 'datetime' in typ:f['format']='date-time'
  p[k]=f
 # JSONB列可为数组；枚举和JSON类型来自实际CheckConstraint，不能一律写object。
 for call in ast.walk(c):
  if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Name) or call.func.id!='CheckConstraint' or not call.args or not isinstance(call.args[0],ast.Constant):continue
  check=call.args[0].value
  for field,jtype in re.findall(r'''jsonb_typeof\("([^"]+)"\) = '([^']+)' ''',check+' '):
   if field in p:
    nullable=isinstance(p[field]['type'],list)
    p[field]['type']=[jtype,'null'] if nullable else jtype
    if jtype=='array':p[field]['items']={}
  for field,values in re.findall(r'"([^"]+)" IN \(([^)]+)\)',check):
   if field in p:p[field]['enum']=re.findall(r"'([^']+)'",values)+([None] if isinstance(p[field]['type'],list) else [])
 return {'type':'object','properties':p,'required':list(p),'description':'实际读取行字段；嵌套JSON保持其原合同，非新增写入DTO。'}
for name,cl in [('RecordAlert','Alerts'),('RecordIncident','Incidents'),('RecordObject','AlertObjects'),('RecordSource','AlertSourceRefs'),('RecordComment','Comments'),('RecordResponse','ResponseLinks'),('RecordActivity','Activities'),('RecordActivityTarget','ActivityTargets')]:
 SC[name]=row_schema(cl)
for name in ['RecordAlertMember','RecordIncidentLink']:
 SC[name]=copy.deepcopy(SC['RecordAlert' if name=='RecordAlertMember' else 'RecordIncident'])
 SC[name]['properties'].update(linked_at={'type':'string','format':'date-time'},membership_source={'type':'string'},correlation_basis={'type':'object'},basis_version={'type':'string'})
 SC[name]['required']=list(SC[name]['properties'])
SC['RecordActivity']['properties'].update(matching_targets={'type':'array','items':{'$ref':'#/components/schemas/RecordActivityTarget'}},targets_truncated={'type':'boolean'})
SC['RecordActivity']['required']+=['matching_targets','targets_truncated']
SC['RecordSourceArtifact']=row_schema('Artifacts')
for field in ['content_json','content_text']:
 SC['RecordSourceArtifact']['properties'].pop(field,None)
 SC['RecordSourceArtifact']['required']=[k for k in SC['RecordSourceArtifact']['required'] if k!=field]
SC['RecordSourceArtifact']['properties']['content_url']={'type':'string','description':'读取该非Run来源工件正文的相对URL。'}
SC['RecordSourceArtifact']['required'].append('content_url')
SC['RecordCaseLink']={'type':'object','properties':{'id':{'type':'string','format':'uuid'},'title':{'type':'string'},'handling_status':{'$ref':'#/components/schemas/WorkStatus'},'scope_revision':{'type':'integer'},'via_member_alert':{'type':'boolean'},'explicit_incident_link':{'type':'boolean'}}}
SC['RecordAssetMatch']={'type':'object','properties':{k:{'type':'string'} for k in ['object_id','alert_id','material_id','object_key','namespace','asset_id','name','fqdn','asset_type','criticality','os','os_version']}}
for k in ['tags','ip_addresses']:SC['RecordAssetMatch']['properties'][k]={'type':'array','items':{'type':'string'}}
SC['RecordAssetMatch']['properties']['match_basis']={'type':'string','enum':['exact_ip','exact_name_casefold','exact_fqdn_casefold']}
# 宽松类型保留库存空值；不是将这些字段升级为新的冻结合同。
for k in ['name','fqdn','asset_type','criticality','os','os_version']:
 SC['RecordAssetMatch']['properties'][k]['type']=['string','null']
SECTIONS={
'members':('RecordAlertMember','仅incidents；告警事实+linked_at/membership_source/correlation_basis/basis_version。'),
'incidents':('RecordIncidentLink','仅alerts；事件事实+关联依据。'),
'objects':('RecordObject','当前成员材料对象；共现边不是因果图。'),
'sources':('RecordSource','当前材料来源引用；保留命名空间、版本和source_path。'),
'source_artifacts':('RecordSourceArtifact','非Run来源工件元数据及content_url，不代表调查运行。'),
'assets':('RecordAssetMatch','仅匹配成功的对象–库存资产边；total不是去重资产数。'),
'cases':('RecordCaseLink','共享告警关系和显式事件关系分别标记。'),
'comments':('RecordComment','A/I现有评论只读；没有Case评论写入服务。'),
'activities':('RecordActivity','只匹配实际主体/目标；matching_targets最多200，检查targets_truncated。'),
'related_alerts':('RecordAlert','同类型、同命名空间、同对象键的其他告警，排除当前成员，可跨Case。'),
'responses':('RecordResponse','现有响应关联；ID本身不证明审批/执行成功。'),
}
DOC['info'].update(title='调查服务 HTTP 交接 · 125 项功能',version='2026-11-12.docs1',description='57 个现有 HTTP 操作，125 项功能逐项映射。\n\n[打开功能清单、调用流程与边界](/handoff/index.html) · [下载完整示例](/handoff/examples.json) · [原JSON业务合同](/handoff/json-contracts.json)\n\n示例均为合成合同示例，不是线上数据或执行证据。可用指现有HTTP能力，不代表产品页面或模型质量验收通过。3个AI预留操作返回501；21独立正式服务手动A/I执行已启用，真实模型质量另行验收。后端通过HTTP对接，无需连接调查数据库或照搬旧AiSOC表。当前服务需Authorization: Bearer <已有有效凭据>。')
DOC['servers']=[
 {'url':'http://192.168.1.21:18024','description':'21正式独立服务；数据库aisoc，内网HTTP对接使用此入口。'},
 {'url':'http://127.0.0.1:28024','description':'本机SSH转发到21正式服务；需已开启relay.json对应转发。'},
 {'url':'http://127.0.0.1:18024','description':'本机独立测试服务；数据库v12_upgrade_dev，记录ID与21不通用。'},
]
SC['ServiceError']={'type':'object','required':['detail'],'properties':{'detail':{'oneOf':[{'type':'string'},{'type':'object','additionalProperties':True},{'type':'array','items':{'type':'object','additionalProperties':True}}]}},'description':'实际错误有字符串、结构化对象或字段校验数组三种detail；不要假定都是code对象。'}
DOC['tags']=[{'name':n} for n in ['Case与范围','调查运行与结果','页面读取','A/I分析','人工任务','未实现AI预留']]

def sample(s, field='', model='', depth=0):
 if depth>12:return None
 if '$ref' in s:
  nm=s['$ref'].rsplit('/',1)[-1]
  if nm in EX:return copy.deepcopy(EX[nm])
  return sample(SC[nm],field,nm,depth+1)
 if 'default' in s:return copy.deepcopy(s['default'])
 if 'const' in s:return s['const']
 if 'anyOf' in s or 'oneOf' in s:
  opts=s.get('anyOf',s.get('oneOf'))
  if any(x.get('type')=='null' for x in opts):return None
  return sample(opts[0],field,model,depth+1)
 if 'enum' in s:return s['enum'][0]
 t=s.get('type','object')
 if isinstance(t,list):
  if 'null' in t:return None
  t=t[0]
 if t=='null':return None
 if t=='object':return {k:sample(v,k,model,depth+1) for k,v in s.get('properties',{}).items()}
 if t=='array':return [sample(s.get('items',{}),field,model,depth+1) for _ in range(s.get('minItems',0))]
 if t=='boolean':return False
 if t in ['integer','number']:return max(0,s.get('minimum',0),1 if field in ['row_version','scope_revision','revision'] else 0)
 if s.get('format')=='uuid':return ID.get(model.replace('View','').lower(),uid(field)) if field=='id' else uid(field)
 if s.get('format')=='date-time':return DATE
 if field in ['title']:return '合成示例：核查异常登录'
 if field=='source_namespace':return 'example'
 if field in ['purpose','closing_note']:return '仅说明合同结构，无真实执行或业务判断。'
 return '示例'
EX={}
def base(n):return sample(SC[n],model=n)
EX['AIUnavailable']={'detail':{'code':'case_ai_not_implemented','status':'not_implemented','message':'AI问答功能暂未实现；本次请求未执行、保存或采用任何结果。'}}
EX['CaseCreate']={'operation_key':ID['operation'],'title':'核查异常登录','description':None,'severity':None,'tags':[],'alert_ids':[ID['alert']],'incident_ids':[]}
EX['AssociationRequest']={'operation_key':ID['operation'],'expected_scope_revision':1,'alert_ids':[ID['alert']],'incident_ids':[]}
EX['MemberChange']={'operation_key':ID['operation'],'expected_scope_revision':1,'alert_ids':[ID['alert']]}
EX['MoveMembers']={'operation_key':ID['operation'],'target_case_id':ID['target'],'expected_source_scope_revision':1,'expected_target_scope_revision':1,'alert_ids':[ID['alert']]}
EX['CaseDataUpdate']={'operation_key':ID['operation'],'expected_row_version':1,'classification':'informational','due_at':None,'source':'manual','source_note':'业务负责人确认该案用于跟踪已知活动'}
EX['PrepareBaseline']={'operation_key':ID['operation'],'expected_scope_revision':1}
EX['Start']={'operation_key':ID['operation'],'expected_scope_revision':1,'window_start':None,'window_end':None,'comparison_result_id':None}
EX['ExecuteStage']={'operation_key':ID['operation']}
EX['AskCaseAI']={'operation_key':ID['operation'],'question':'这些告警有哪些共同依据？','conversation_id':None}
EX['SaveCaseAIAnswer']={'operation_key':ID['operation'],'title':'待保存的回答','conclusion':'用户确认保存的正文（接口当前501）'}
EX['AdoptCaseAIResult']={'operation_key':ID['operation'],'expected_scope_revision':1}
EX['EvidenceIndex']={'schema_version':'socai2.case-evidence.v1','scope_revision':1,'alert_ids':[ID['alert']],'supersedes_artifact_id':None,'availability_state':'unavailable','limitations':['尚未整理可发布的证据目录'],'entries':[]}
EX['EvidencePublish']={'operation_key':ID['operation'],'expected_row_version':1,'expected_current_artifact_id':None,'index':EX['EvidenceIndex']}
EX['Scope']={'kind':'selected_alerts','alert_ids':[ID['alert']],'object_keys':[],'window_start':None,'window_end':None,'limitations':['仅覆盖人工核实的该条告警']}
EX['TaskCreate']={'title':'核实登录是否为本人操作','description':'联系对应负责人核实','assignee_id':None,'due_at':None,'state':'not_started','result_text':None,'result_scope':None,'source_refs':[],'operation_key':ID['operation'],'expected_scope_revision':1,'origin_result_id':None,'origin_finding_id':None}
EX['TaskEdit']={k:v for k,v in EX['TaskCreate'].items() if k not in ['origin_result_id','origin_finding_id']}
EX['TaskEdit'].update(expected_row_version=1,state='completed',result_text='人工已联系负责人；其确认该次登录为本人操作。',result_scope=EX['Scope'])
EX['AssociationReceipt']={'case_id':ID['case'],'scope_revision':1,'pending_run_id':ID['run'],'changed':True,'added_alert_ids':[ID['alert']],'linked_incident_ids':[]}
EX['MutationReceipt']={k:v for k,v in EX['AssociationReceipt'].items() if k not in ['added_alert_ids','linked_incident_ids']}
EX['BaselinePreparation']={'case_id':ID['case'],'scope_revision':1,'pending_run_id':ID['run'],'created':True}
EX['CaseDataReceipt']={'case_id':ID['case'],'row_version':2,'changed':True,'current_evidence_artifact_id':None}
EX['MoveReceipt']={'source':{**EX['MutationReceipt'],'scope_revision':2},'target':{**EX['MutationReceipt'],'case_id':ID['target'],'scope_revision':2,'pending_run_id':None},'moved_alert_ids':[ID['alert']],'added_to_target_alert_ids':[ID['alert']]}
EX['CaseView']=base('CaseView');EX['CaseView'].update(id=ID['case'],scope_revision=1,row_version=1,priority_state='not_provided')
EX['RunView']=base('RunView');EX['RunView'].update(id=ID['run'],case_id=ID['case'],kind='baseline',trigger='manual',scope_revision=1,state='pending_update',delivery_state='none')
EX['StartAvailability']={'can_start':False,'reason':'empty_scope'}
EX['RunDetail']=base('RunDetail');EX['RunDetail']['usage']={'model_calls':0,'known_total_tokens':0,'unknown_token_calls':0,'total_tokens':0,'costs_by_currency_and_price_version':[],'unpriced_model_calls':0}
EX['EvidenceView']=base('EvidenceView');EX['EvidenceView'].update(state='not_recorded',index=None)
EX['TaskRevisionView']=base('TaskRevisionView');EX['TaskRevisionView'].update(id=ID['revision'],case_id=ID['case'],task_id=ID['task'],title=EX['TaskCreate']['title'],description=EX['TaskCreate']['description'],state='not_started',changed_by=ID['user'])
EX['TaskView']=base('TaskView');EX['TaskView'].update(id=ID['task'],case_id=ID['case'],current_revision_id=ID['revision'],current=EX['TaskRevisionView'])
EX['TaskMutation']={'task':EX['TaskView'],'changed':True}
EX['StageEntry']=base('StageEntry');EX['StageEntry'].update(freshness='unavailable',is_current_pointer=False,valid_for_current_input=False)
EX['StageEntry']['run'].update(id=ID['run'],kind='alert_basic',state='pending_update',delivery_state='none')
EX['StagePage']=base('StagePage');EX['StagePage'].update(subject_id=ID['alert'],kind='alert_basic',current=None,current_pointer_id=None,current_unavailable_reason=None)
EX['SubjectView']=base('SubjectView');EX['SubjectView'].update(kind='alerts',analysis_url='/api/v1/socai2/alerts/'+ID['alert']+'/analysis',section_urls={s:'/api/v1/socai2/alerts/'+ID['alert']+'/records/'+s for s in SECTIONS if s!='members'})
EX['SubjectView']['facts'].update(id=ID['alert'],source_namespace='example',event_time_source='unknown')
EX['SubjectPage']=base('SubjectPage');EX['SubjectPage'].update(kind='alerts',total=0,filtered_total=0,next_cursor=None,next_before_id=None,overall_stats={k:0 for k in ['total','new','in_progress','unknown','high_severity','investigating']})
EX['ArtifactContent']=base('ArtifactContent');EX['ArtifactContent'].update(availability='available',content_json=None,content_text='合成示例报告：未形成可采用结论。')
EX['ContentView']=base('ContentView');EX['ContentView'].update(availability='available',content_json=None,content_text='合成示例原文')
EX['ResultView']=base('ResultView');EX['ResultView'].update(id=ID['result'],case_id=ID['case'],source_run_id=ID['run'],conclusion=None,conclusion_state='unavailable',conclusion_origin='system',validation_state='system_only',delivery_state='partial')
EX['ResultDetail']=base('ResultDetail');EX['ResultDetail']['run'].update(state='failed',started_at=DATE,ended_at=DATE,stop_reason='example_no_conclusion',delivery_state='partial',input_artifact_id=ID['artifact'],scope_kind='whole_case')
EX['ResultDetail']['result']['case_impact']['affected_scope']['limitations']=['该轮未形成可采用结论']
EX['ResultDetail']['members']=[{'id':ID['revision'],'case_id':ID['case'],'result_id':ID['result'],'run_id':ID['run'],'alert_id':ID['alert'],'assessment_state':'not_analyzed','conclusion_covered':False,'assessment':None,'limitations':'该轮未形成可采用结论','evidence_refs':[]}]
EX['ResultDetail']['member_count']=1
EX['FrozenAlertMaterial']=base('FrozenAlertMaterial');EX['FrozenAlertMaterial'].update(id=ID['material'],tenant_id=ID['user'],alert_id=ID['alert'],revision=1,material_state='unavailable',raw_text=None,raw_json=None,ocsf_json=None,enrichment=None,detection={},source_scope={},retention={})

EX['CaseManagementUpdate']={'operation_key':ID['operation'],'expected_row_version':1,'title':'需要人工跟进的调查','description':'核对相关告警','owner_id':None,'severity':'high','tags':['人工跟进'],'handling_status':'in_progress'}
EX['CaseCloseRequest']={'operation_key':ID['operation'],'expected_row_version':1,'acknowledge_open_tasks':True,'reason':'当前调查结案，未完人工任务另行跟进。'}
EX['CaseLifecycleRequest']={'operation_key':ID['operation'],'expected_row_version':1,'reason':'收到需要继续处理的信息，人工重开。'}
EX['CaseManagementView']={'case':base('CaseView'),'open_task_count':1,'blocking_runs':[],'can_close':True,'can_reopen':False,'requires_open_task_confirmation':True}
EX['CaseManagementView']['case'].update(id=ID['case'],handling_status='in_progress',owner_id=None,assignment_state='unassigned',row_version=1)
EX['CaseManagementReceipt']={'case':copy.deepcopy(EX['CaseManagementView']['case']),'changed':True}
EX['CaseManagementReceipt']['case']['row_version']=2

EX['AlertFeedback']={'operation_key':ID['operation'],'expected_row_version':1,'disposition':'false_positive','reason':'人工核实为已知检测误报'}
EX['AlertFeedbackBatch']={'operation_key':ID['operation'],'items':[{'id':ID['alert'],'expected_row_version':1}],'feedback':{'disposition':'false_positive','reason':'逐条核实所选告警属于本次误报'}}
EX['AlertManagementUpdate']={'operation_key':ID['operation'],'expected_row_version':1,'owner_id':ID['user'],'tags':['人工跟进']}
EX['IncidentManagementUpdate']={'operation_key':ID['operation'],'expected_row_version':1,'severity_override':'high','severity_override_reason':'人工核对影响范围后调整'}
EX['AlertManagementBatch']={'operation_key':ID['operation'],'items':[{'id':ID['alert'],'expected_row_version':1}],'changes':{'owner_id':ID['user'],'tags':['人工跟进']}}
EX['IncidentManagementBatch']={'operation_key':ID['operation'],'items':[{'id':ID['incident'],'expected_row_version':1}],'changes':{'handling_status':'resolved','resolution_note':'人工完成事件核实'}}
EX['SubjectMutationReceipt']={'kind':'alerts','facts':base('AlertFacts'),'changed':True,'feedback_id':None,'activity_id':ID['operation']}
EX['SubjectMutationReceipt']['facts'].update(id=ID['alert'],row_version=2,handling_status='in_progress',owner_id=ID['user'],assignment_state='assigned',assigned_at=DATE)
EX['SubjectBatchReceipt']={'operation_key':ID['operation'],'items':[EX['SubjectMutationReceipt']],'changed_count':1}

# 清晰区分代码标识、输入、输出与错误；示例不执行。
features=[]
lookup={}
for l in FEATURE_MAP.strip().splitlines():
 a=l.split('|',3);lookup[a[0]]=(a[1],[int(x) for x in a[2].split(',') if x],a[3])
page='';group=''
for l in (SOURCE/'frontend-feature-list.md').read_text().splitlines():
 if l.startswith('## '):
  for name in ['告警','事件','调查']:
   if name+'功能' in l:group=name
 if l.startswith('### '):page=l[4:]
 if not l.startswith('| F'):continue
 cells=[x.strip() for x in l.strip('|').split('|')]
 fid,title=cells[0].split(' ',1)
 status,ops,notes=lookup[fid]
 features.append(dict(id=fid,group=group,page=page,title=title,purpose=cells[1],result=cells[2],implementation_status=cells[3],backend_status=cells[4],http_status=status,operations=[f'E{x:02}' for x in ops],notes=notes))
if len(features)!=125 or set(lookup)!={f['id'] for f in features}:raise RuntimeError('功能清单与注释不一致，停止生成')
common='所有UUID用真实返回身份；时间带时区。已有身份以 Authorization: Bearer <token> 传入，JSON写请求使用Content-Type: application/json。401/403沿既有登录/身份处理，不增加权限设计。额外body字段会422。'
endpoints=[]; examples={}; i=0
for path,methods in DOC['paths'].items():
 for method,op in methods.items():
  if method not in ['get','post','put','patch','delete']:continue
  i+=1;eid=f'E{i:02}';title,status,note,errs=OPERATIONS[i]
  op['operationId']=eid
  tag='未实现AI预留' if i in [19,20,21] else '人工任务' if i>=38 else 'A/I分析' if i in [22,23,24,25,32,33,36,37] else '页面读取' if 26<=i<=35 else '调查运行与结果' if 10<=i<=18 else 'Case与范围'
  op['tags']=[tag];op['summary']=f'{eid} [{status}] {title}'
  mapped=[f['id'] for f in features if eid in f['operations']]
  op['x-feature-ids']=mapped;op['x-implementation-status']=status
  op['description']=note+'\n\n'+common+'\n\n功能对应：'+('、'.join(mapped) if mapped else '支撑操作，参见相邻功能调用流程')+'。\n\n所有示例都是独立合成场景，不能把不同操作示例的版本号串作真实执行。'
  params=[]; pv={}
  for p in op.get('parameters',[]):
   p['description']=DESC.get(p['name'],p.get('description',p['name']))
   if 54<=i<=56 and p['name']=='columns':p['description']='逗号分隔的公开字段路径，按给定顺序输出；省略使用默认列；空列、重复或未知列返回422。全部可选列及默认列见Responses。'
   if 54<=i<=56 and p['name']=='severity':p['description']='按已知等级精确筛选；省略不筛选。当前没有单独筛选未知等级的参数，不传null字符串。'
   if 54<=i<=56 and p['name']=='sort_by':p['description']+=' 默认'+{54:'ingested_at',55:'created_at',56:'business_updated_at'}[i]+'。'
   if i==57 and p['name']=='source_namespace':p['description']='告警来源命名空间精确匹配，区分大小写；省略为全部来源；空白拒绝422。'
   if i==57 and p['name'] in ['time_from','time_to']:p['description']='告警真实event_time的带时区范围：起点包含、终点不含；允许单边；范围内不包含未知时间。省略时间条件则包含未知时间。'
   v=sample(p['schema'],p['name'])
   if p['name']=='section':v='objects'
   if p['name']=='subject':v='alerts'
   if v is not None:p['example']=v
   if p['required'] or 'default' in p['schema']:pv[p['name']]=v
   params.append(p)
  if i in [2,26,27]:
   pv.update(q='需要核实',sort_by='severity',sort_order='desc',time_from='2026-11-10T00:00:00Z',time_to='2026-11-11T00:00:00Z')
  body=op.get('requestBody',{}).get('content',{}).get('application/json')
  req=sample(body['schema']) if body else None
  if body:body['examples']={'contract':{'summary':'合成请求示例；UUID与版本必须换成真实值','value':req}}
  if i==18:op['responses']['200']['content']['application/json']['schema']={'$ref':'#/components/schemas/FrozenAlertMaterial'}
  if i in [19,20,21]:op['responses'].pop('200',None)
  maincode='501' if i in [19,20,21] else '200'
  resp=op['responses'][maincode].setdefault('content',{}).setdefault('text/csv' if 54<=i<=56 else 'application/json',{})
  out=sample(resp.get('schema',{}))
  if 48 <= i <= 53:
   one=copy.deepcopy(EX['SubjectMutationReceipt'])
   if i in [48,49]:
    one['feedback_id']=ID['result'];one['facts'].update(latest_feedback_id=ID['result'],disposition='false_positive',handling_status='completed',closed_at=DATE,closed_by=ID['user'])
   if i in [52,53]:
    one['kind']='incidents';one['facts']=base('IncidentFacts');one['facts'].update(id=ID['incident'],row_version=2,handling_status='in_progress',severity_override='high',severity_override_reason='人工核对影响范围后调整',severity_override_by=ID['user'],severity_override_at=DATE)
   if i in [50,51]:one['facts']['tags']=['人工跟进']
   if i==53:one['facts'].update(handling_status='resolved',resolution_note='人工完成事件核实',resolved_at=DATE,resolved_by=ID['user'])
   out={'operation_key':ID['operation'],'items':[one],'changed_count':1} if i in [49,51,53] else one
  if 54<=i<=56:
   kind={54:'alerts',55:'incidents',56:'cases'}[i]
   cols=json.loads((ROOT/'deploy/api-docs/list-export-columns.json').read_text())[kind]['defaults']
   out=','.join(cols)+'\r\n'
   pv={'q':'合成示例无记录','columns':','.join(cols),'sort_by':'severity','sort_order':'desc'}
  if i==57:
   out.update(scope={'source_namespace':'example','time_from':None,'time_to':None},alert_count=6,grouped_alert_count=4,ungrouped_alert_count=2,incident_count=2,in_progress_incident_count=1,compression_rate=0.5)
   pv={'source_namespace':'example'}
  if i in [23,25,37]:
   if 'kind' in out:out['kind']='incident_diagnosis'
   if 'subject_id' in out:out['subject_id']=ID['incident']
   if 'run' in out:out['run']['kind']='incident_diagnosis'
  if i==27:out['kind']='incidents';out['overall_stats']={k:0 for k in ['total','new','in_progress','unknown','active','unassigned','grouped_alert_count','new_alerts_24h','high_severity']}
  if i==29:
   out['kind']='incidents';out['facts']=base('IncidentFacts');out['facts']['id']=ID['incident'];out['analysis_url']='/api/v1/socai2/incidents/'+ID['incident']+'/analysis';out['section_urls']={s:'/api/v1/socai2/incidents/'+ID['incident']+'/records/'+s for s in SECTIONS if s!='incidents'}
  if i==6:out['current_evidence_artifact_id']=ID['artifact']
  if i==13:
   out['run'].update(state='failed',started_at=DATE,ended_at=DATE,stop_reason='example_unavailable',stop_detail='合成失败示例，不表示真实执行',delivery_state='none');out['start_eligibility']={'can_start':False,'reason':'not_pending'}
  if i in [36,37]:out['run'].update(state='failed',started_at=DATE,ended_at=DATE,stop_reason='example_unavailable')
  if i==40:
   out['task']['row_version']=2;out['task']['current'].update(state='completed',result_text=EX['TaskEdit']['result_text'],result_scope=EX['Scope'],completed_at=DATE,completed_by=ID['user'],revision=2)
  if i==45:out['case'].update(title=EX['CaseManagementUpdate']['title'],description=EX['CaseManagementUpdate']['description'],severity='high',severity_source='manual',tags=['人工跟进'])
  if i==46:out['case'].update(handling_status='resolved',resolved_at=DATE,resolved_by=ID['user'],resolution_note=EX['CaseCloseRequest']['reason'])
  if i==47:out['case'].update(handling_status='in_progress',resolved_at=None,resolved_by=None,resolution_note=None,reopened_at=DATE)
  if i==31:out.update(content_json={'raw_json':{'example':True},'ocsf_json':None,'enrichment':None},content_text='合成原始材料示例',metadata={'id':ID['material'],'alert_id':ID['alert'],'revision':1,'material_state':'complete'})
  if i in [15,16,33,34,35]:
   out['artifact' if i in [15,16] else 'metadata']={'id':ID['artifact'],'run_id':ID['run'] if i in [15,33] else None,'material_state':'complete'}
  resp['examples']={'contract':{'summary':'合成响应示例；独立场景，非线上执行证据','value':out}}
  if i==30:
   op['description']+='\n\n分区项类型：\n'+''.join(f'- `{s}` → `{nm}`：{nt}\n' for s,(nm,nt) in SECTIONS.items())+'- `source_artifacts` → 工件元数据和content_url，仅非Run来源工件。\n'
   op['x-section-schemas']={s:{'$ref':'#/components/schemas/'+nm} for s,(nm,_) in SECTIONS.items()}
   for s,(nm,_) in SECTIONS.items():
    val=sample({'$ref':'#/components/schemas/'+nm})
    resp['examples'][s]={'summary':f'{s}分区的空集合示例；非空字段见对应Record Schema','value':{'items':[],'total':0,'next_offset':None,'observed_at':DATE,'limitations':[]}}
  errorlist=[]
  defaults={'401':[('not_authenticated',{'detail':'Not authenticated'},'缺少有效已有凭据')],'403':[('identity',{'detail':('subject_user_actor_required' if 48<=i<=53 else 'case_user_actor_required') if i<22 or i>=38 else 'Permission denied: alerts:read'},'现有身份/访问条件不符')],'422':[('validation',{'detail':[{'type':'uuid_parsing','loc':['path','case_id' if i<=21 or i>=38 else 'identity'],'msg':'Input should be a valid UUID','input':'not-a-uuid'}]},'UUID、枚举、长度、额外字段或跨字段约束不符')],'503':[]}
  # 校验错误示例必须引用该操作实际存在的入参，列表不能虚构path.identity。
  error_param=next((p for p in params if p['in']=='path' and p['schema'].get('format')=='uuid'),None)
  if error_param:
   error_item={'type':'uuid_parsing','loc':['path',error_param['name']],'msg':'Input should be a valid UUID','input':'not-a-uuid'}
  elif body:
   error_item={'type':'uuid_parsing','loc':['body','operation_key'],'msg':'Input should be a valid UUID','input':'not-a-uuid'}
  else:
   error_item={'type':'int_parsing','loc':['query','limit'],'msg':'Input should be a valid integer','input':'not-an-integer'}
  defaults['422'][0][1]['detail']=[error_item]
  if 54<=i<=56:
   defaults['422'][0][1]['detail']='export_columns_invalid'
   defaults['403']=[('permission_denied',{'detail':'Permission denied: '+('cases:read' if i==56 else 'alerts:read')},'现有读取条件不符')]
  if i==57:
   defaults['422'][0][1]['detail']=[{'type':'value_error','loc':[],'msg':'Value error, time_from_must_precede_time_to'}]
   defaults['403']=[('permission_denied',{'detail':'Permission denied: alerts:read'},'现有读取条件不符')]
  if i==2:
   defaults['403']=[('permission_denied',{'detail':'Permission denied: cases:read'},'缺少Case读取能力')]
  flag='socai2_page_read_not_enabled' if i in [54,55,57] else 'socai2_subject_write_not_enabled' if 48<=i<=53 else 'socai2_case_api_not_enabled' if i<=21 or i>=38 else 'socai2_analysis_read_not_enabled' if i in [22,23,24,25] else 'socai2_stage_execution_not_enabled' if i in [36,37] else 'socai2_page_read_not_enabled'
  defaults['503'].append(('feature_disabled',{'detail':flag},'服务对应功能开关关闭'))
  if i in [2,26,27]:
   defaults['422'].append(('invalid_time_window',{'detail':[{'type':'value_error','loc':[],'msg':'Value error, time_from_must_precede_time_to'}]},'起点不早于终点；无时区、非法排序或枚举同样422'))
  if i in [26,27]:
   defaults['422'].append(('mixed_pagination',{'detail':[{'type':'value_error','loc':[],'msg':'Value error, before_id_cannot_combine_with_cursor_filters_or_sort'}]},'before_id不能与cursor、新筛选或排序混用'))
  for e in errs.split():
   code,http=e.rsplit(':',1)
   val=EX['AIUnavailable'] if http=='501' else {'detail':code}
   defaults.setdefault(http,[]).append((code,val,'业务约束/对象状态，见操作说明'))
  if i==13:defaults['503'].append(('read_run',{'detail':{'code':'baseline_execution_unavailable_read_run','run_id':ID['run'],'read_path':f"/api/v1/socai2/cases/{ID['case']}/runs/{ID['run']}"}},'执行异常或结果未知；先GET读取，禁止盲目重派'))
  if i in [36,37]:defaults['503'].append(('read_run',{'detail':{'code':'stage_execution_unavailable_read_run','run_id':ID['run']}},'先读该主体下指定Run；此错误没有read_path'))
  for http,els in defaults.items():
   err=op['responses'].setdefault(http,{})
   err['description']='；'.join(f'{key}：{why}' for key,_,why in els)
   err['content']={'application/json':{'schema':{'$ref':'#/components/schemas/AIUnavailable' if http=='501' else '#/components/schemas/ServiceError'},'examples':{key:{'summary':why,'value':value} for key,value,why in els}}}
   errorlist.extend((http,k,why,val) for k,val,why in els)
  examples[eid]={'method':method.upper(),'path':path,'parameters':pv,'request_body':req,'response_status':int(maincode),'response_body':out,'errors':{k:{'status':int(h),'body':v} for h,k,_,v in errorlist},'notice':'合成合同示例，不连接API或数据库；各示例为独立场景。'}
  endpoints.append(dict(id=eid,title=title,status=status,path=path,method=method.upper(),tag=tag,note=note,params=params,body=body,response=resp,example=examples[eid],errors=errorlist,features=mapped))

enrich_contract(ROOT,DOC,features,endpoints,VERSION)
# 仅保留本调查路径及文档扩展可达的Schema；移除原登录模块的无关Schema。
used=set()
def refs(o):
 if isinstance(o,dict):
  r=o.get('$ref','')
  if r.startswith('#/components/schemas/'):
   k=r.rsplit('/',1)[-1]
   if k not in used:used.add(k);refs(SC[k])
  for k,v in o.items():
   if k!='$ref':refs(v)
 elif isinstance(o,list):
  for v in o:refs(v)
refs(DOC['paths'])
DOC['components']['schemas']={k:v for k,v in SC.items() if k in used}
SC=DOC['components']['schemas']

def dump(o):return json.dumps(o,ensure_ascii=False,indent=2)+'\n'
def typ(s):
 if '$ref' in s:return '['+s['$ref'].rsplit('/',1)[-1]+'](schemas.md#'+s['$ref'].rsplit('/',1)[-1].lower()+')'
 if 'anyOf' in s or 'oneOf' in s:return ' / '.join(typ(v) for v in s.get('anyOf',s.get('oneOf')))
 t=s.get('type','object');r='/'.join(t) if isinstance(t,list) else t
 if r=='array':r+=' <'+typ(s.get('items',{}))+'>'
 if 'format'in s:r+=' ('+s['format']+')'
 if 'enum'in s:r+=' '+', '.join(map(str,s['enum']))
 if 'const'in s:r+=' = '+str(s['const'])
 for k in ['minimum','maximum','minLength','maxLength','minItems','maxItems','pattern']:
  if k in s:r+=f'; {k}={s[k]}'
 return r

def mdtable(headers,rows):
 def clean(x):return str(x).replace('|','\\|').replace('\n','<br>')
 return '\n| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(clean(c) for c in r)+' |\n' for r in rows)+'\n'

def schema_table(s):
 if '$ref'in s:return schema_table(SC[s['$ref'].rsplit('/',1)[-1]])
 return mdtable(['字段','OpenAPI required','类型与约束','默认值','含义'],[[k,'是' if k in s.get('required',[]) else '否',typ(v),json.dumps(v['default'],ensure_ascii=False) if 'default'in v else '无（可空不等于可省略）',v.get('description',v.get('title',k)).split('\n\n')[0]+(' [完整语义]('+v['x-audit-url']+')' if 'x-audit-url' in v else '')] for k,v in s.get('properties',{}).items()])
epmd='# 调查HTTP接口目录（57项）\n\n[共同约定与调用流程](README.md) · [嵌套Schema](schemas.md) · [合成示例JSON](examples.json)\n\n参数来自现有OpenAPI，附加业务校验来自现有实现。以下错误列出调用方直接处理的典型分支；未枚举的5xx仍按未知处理，不伪造成功。示例独立，不可将示例UUID当真实数据发送。\n'
for e in endpoints:
 epmd+=f"\n<a id=\"{e['id'].lower()}\"></a>\n\n## {e['id']} {e['title']}\n\n`{e['method']} {e['path']}`\n\n状态：**{e['status']}**。分类：{e['tag']}。\n\n{e['description']}\n"
 if int(e['id'][1:])<54:epmd+=f'\n[本接口用途及完整输出字段审计](audit/interfaces.html#{e["id"].lower()}) · [动态投影与差异](audit/dynamic-fields.html)\n'
 epmd+=mdtable(['位置','参数','必传','类型/限制','默认值','说明'],[[p['in'],p['name'],p['required'],typ(p['schema']),json.dumps(p['schema'].get('default'),ensure_ascii=False),p['description']] for p in e['params']]) if e['params'] else '\n无路径/查询参数。\n'
 epmd+='\n请求体：\n'+schema_table(e['body']['schema']) if e['body'] else '\n无请求体。\n'
 epmd+='\n响应类型：'+typ(e['response'].get('schema',{}))+'。字段完整展开见Schema或Swagger Models。\n'
 epmd+='\n输入示例（参数与JSON体）：\n\n```json\n'+dump({'parameters':e['example']['parameters'],'body':e['example']['request_body']})+'```\n'
 epmd+=f"\n输出示例（HTTP {e['example']['response_status']}）：\n\n"+("```csv\n"+e["example"]["response_body"]+"```\n" if 54<=int(e["id"][1:])<=56 else "```json\n"+dump(e["example"]["response_body"])+"```\n")
 epmd+=mdtable(['HTTP','错误/形状','处理'],[[h,k,why+('；保留用户输入→读最新版本→确认差异后重新提交。' if h=='409' else '；参数修正前不重试。' if h=='422' else '')] for h,k,why,v in e['errors']])
 epmd+='完整错误JSON示例见 `examples.json` 的 `'+e['id']+'.errors`，Swagger同操作 Responses 可直接展开。\n'
schmd='# HTTP字段与嵌套类型\n\n按实际JSON类型保留required、可空、枚举和限制。请求额外字段禁止；服务输出可空字段不能擅自补0/空串。动态正文见[原JSON合同](json-contracts.json)，不要将任意工件统一套成一种业务结论。\n'
for k,v in SC.items():
 schmd+=f'\n<a id="{k.lower()}"></a>\n\n## {k}\n\n'+v.get('description','')+'\n'
 schmd+=schema_table(v) if v.get('properties') else '\n'+typ(v)+'\n'
OUT.mkdir(parents=True,exist_ok=True)
for name,obj in [('openapi.json',DOC),('examples.json',examples)]: (OUT/name).write_text(dump(obj))
for name,txt in [('endpoints.md',epmd),('schemas.md',schmd)]: (OUT/name).write_text(txt.rstrip()+"\n")
(OUT/'json-contracts.json').write_bytes((ROOT/'docs/design/socai2-json-contracts-20261103.schema.json').read_bytes())
(OUT/'manifest.json').write_text(dump({'version':VERSION,'features':len(features),'feature_groups':{g:sum(f['group']==g for f in features) for g in ['告警','事件','调查']},'operations':len(endpoints),'schemas':len(SC),'fixed_output_fields':554,'dynamic_structures':28,'source_openapi':str(BASE.relative_to(ROOT)),'source_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'audit_sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE/'http-handoff-audit').iterdir() if p.is_file()},'examples':'synthetic_not_execution_evidence','business_api_called':False}))
# 自包含静态功能页；无CDN，无线上校验或业务API调用。
styles='body{margin:0;background:#f6f8fb;color:#182337;font:15px/1.7 system-ui,sans-serif}main{max-width:1150px;margin:auto;padding:36px 28px}a{color:#1a58ad}header{background:#112a46;color:white;padding:28px;border-radius:16px}header a{color:#bce2ff}nav{display:flex;gap:18px;flex-wrap:wrap;margin:16px 0}.toolbar{position:sticky;top:0;background:#f6f8fb;padding:12px 0;display:flex;gap:12px}input{padding:12px;width:100%;font:inherit;border:1px solid #b5c6da;border-radius:8px}article{background:white;border:1px solid #dae2ec;border-radius:10px;padding:20px;margin:18px 0}h2{margin:0 0 8px}p{margin:8px 0}.meta{color:#53667c}.badge{background:#e6edf6;padding:3px 10px;border-radius:14px;font-size:13px}code{background:#eef2f6;padding:2px 4px}details{margin:10px 0}pre{overflow:auto;background:#17263b;color:#e7f0fa;padding:15px;border-radius:8px;line-height:1.5}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #dce3ed;padding:7px;text-align:left}h1{font-size:28px}section{padding:15px 0}'
def esc(x):return html.escape(str(x))
head='<html lang="zh-CN"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>调查服务 HTTP 对接</title><style>'+styles+'</style><main>'
intro='<header><h1>调查服务 HTTP API</h1><p>告警 · 事件 · 调查</p><nav><a href="/">Swagger接口</a><a href="openapi.json">下载OpenAPI</a><a href="endpoints.html">参数与输入输出</a><a href="schemas.html">字段字典</a><a href="guide.html">接入说明</a></nav></header>'
# Markdown呈现只处理本生成器用到的基础语法；所有内容先转义，JSON展示不执行。
def render_md(md):
 lines=md.splitlines();out=[];code=[];fence=False;table=[]
 def inline(s):
  s=esc(s);s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',lambda m:'<a href="'+m[2].replace('README.md','guide.html').replace('.md','.html')+'">'+m[1]+'</a>',s)
  s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s);s=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',s);return s.replace('&lt;br&gt;','<br>').replace('\\|','|')
 def flush():
  if not table:return
  out.append('<table>')
  for i,l in enumerate(table):
   if re.fullmatch(r'[| :\-]+',l):continue
   tag='th' if i==0 else 'td';out.append('<tr>'+''.join(f'<{tag}>{inline(c.strip())}</{tag}>' for c in re.split(r'(?<!\\)\|',l.strip('|')) )+'</tr>')
  out.append('</table>');table.clear()
 for l in lines:
  if l.startswith('```'):
   flush()
   if fence:out.append('<pre>'+esc('\n'.join(code))+'</pre>');code=[]
   fence=not fence;continue
  if fence:code.append(l);continue
  if l.startswith('|'):table.append(l);continue
  flush()
  if l.startswith('<a id='):out.append(l);continue
  if l.startswith('#'):
   n=len(l)-len(l.lstrip('#'));title=l[n:].strip();anchor=re.sub(r'[^\w\s-]','',title.lower()).replace(' ','-');out.append(f'<h{n} id="{esc(anchor)}">'+inline(title)+f'</h{n}>')
  elif l.startswith('- '):out.append('<p>• '+inline(l[2:])+'</p>')
  elif l.strip():out.append('<p>'+inline(l)+'</p>')
 flush();return '\n'.join(out)
for fname,title in [('endpoints','接口参数与示例'),('schemas','字段字典')]:
 (OUT/(fname+'.html')).write_text(head+intro+render_md((OUT/(fname+'.md')).read_text())+'</main></html>')
if (OUT/'README.md').exists():(OUT/'guide.html').write_text(head+intro+render_md((OUT/'README.md').read_text())+'</main></html>')
publish_pages(ROOT,OUT,DOC,features,endpoints,VERSION,render_md,head,intro,schema_table,typ,dump)
print(f'后端Swagger生成：{len(endpoints)} 操作，{len(SC)} 类型；未连接业务服务。')
