"""为标准Swagger补充已审计的HTTP字段语义；只处理静态文件。"""
from pathlib import Path
import re
import json

GROUPS = {'告警': ('alerts', 22), '事件': ('incidents', 15), '调查': ('investigation', 88)}
AUDIT_REL = Path('deliverables/investigation-validation-20261106/http-handoff-audit')
SOURCES = [
    'docs/investigation/socai2-page-data-handoff-20261106.md',
    'docs/design/socai2-data-contract-current.json',
    'docs/design/socai2-independent-api-v2.openapi.json',
    'docs/design/socai2-json-contracts-20261103.schema.json',
]

RESULTS = {
1:'创建Case并保存所选告警/事件关系，返回案件ID、范围版本和待启动Run ID；创建本身不执行调查。',
2:'按指定条件和顺序返回案件列表、筛选总数total和next_cursor；metrics保留租户整体指标。',
3:'返回指定案件的资料、当前成员、关联事件、已采用判断和调查记录引用。',
4:'保存分类和截止时间，返回案件ID、行版本、是否变更及当前证据目录ID；资料正文需随后GET E03/E05读取。传null会清空对应值。',
5:'返回案件分类、期限、已采用判断摘要和当前证据目录。',
6:'保存并发布提交的证据目录版本，返回当前目录工件ID；此操作不生成新证据。',
7:'用提交的完整告警集合替换当前成员范围，返回新的范围版本及待启动调查引用。',
8:'将所选告警或事件关联到案件，返回实际新增成员、事件关系和范围版本。',
9:'将所选告警从源案件移至目标案件，返回两案变更回执；历史调查范围保持不变。',
10:'返回该案件的基础调查Run及已保存AI结果历史和下一页游标；人工任务修订历史通过E42/E43读取。',
11:'为当前案件范围准备或复用待启动Run，返回Run ID及是否本次新建；随后需显式启动。',
12:'返回指定Run的执行状态、冻结成员、步骤、工件、结果引用、用量和启动资格。',
13:'执行指定pending Run并等待本次执行返回，返回Run状态和已有结果引用；异常或执行未知时先读取同一Run。',
14:'返回指定正式结果、对应Run、冻结成员及交付信息；结论、发现、待核问题和建议分别返回。',
15:'返回指定Case Run工件的元数据、正文和可用状态；完整性校验失败返回409。',
16:'返回案件非Run来源工件的元数据、正文和可用状态；不适用于Run工件。',
17:'返回与案件、成员或显式关联事件匹配的处理活动、目标和分页信息。',
18:'返回该Run冻结的指定告警材料版本原始行，不替换为当前最新材料。',
19:'当前返回501，不执行问答、不调用模型，也不保存消息。',
20:'当前返回501，不保存回答，也不产生正式调查结果。',
21:'当前返回501，不变更案件当前采用判断。',
22:'返回告警当前分诊及历史执行目录；失败尝试和当前有效分诊分别保留。',
23:'返回事件当前诊断及历史执行目录，保留交付、成员覆盖和待核内容。',
24:'返回指定告警分诊Run及其分诊结果、有效性和输入是否变化。',
25:'返回指定事件诊断Run及其诊断结果、交付状态和待核内容。',
26:'按条件和顺序返回告警列表；filtered_total为筛选总数，next_cursor用于下一页，total/overall_stats保持租户整体统计。',
27:'按条件和顺序返回事件列表；filtered_total为筛选总数，next_cursor用于下一页，total/overall_stats保持租户整体统计。',
28:'返回告警事实、当前材料摘要、分诊、已存人工反馈及后续读取地址。',
29:'返回事件事实、成员和对象汇总及后续读取地址；诊断和成员明细使用对应读取接口。',
30:'返回所选分区的记录、总数和下一页偏移；资产分区返回对象与真实库存资产的匹配记录及资产标签。',
31:'返回指定告警材料版本的原始JSON、标准化记录、富化内容及原始文本，并说明正文可用性。',
32:'返回指定告警/事件Run的原始执行记录、步骤、工件目录、用量及截断标志。',
33:'返回告警/事件Run工件的元数据、正文及可用状态；内容完整性异常时正文为空并返回对应availability。',
34:'返回告警非Run来源工件的元数据、正文及可用状态。',
35:'返回事件非Run来源工件的元数据、正文及可用状态。',
36:'发起告警分诊并返回Run结果；21新独立正式入口已挂载并启用，调用会执行当前模型流程。',
37:'发起事件诊断并返回Run结果；21新独立正式入口已挂载并启用，调用会执行当前模型流程。',
38:'保存用户创建的人工任务及首个修订，返回任务ID、当前版本和创建结果。',
39:'返回案件人工任务的当前版本列表、总数和下一页偏移。',
40:'完整更新任务字段，实际变更时保存新的不可变修订并返回当前版本；无变化不新建修订，幂等重试沿用原回执。完成任务必须提供结果正文及有效适用范围。',
41:'返回指定任务的当前修订和行版本，供读取或后续完整更新使用。',
42:'返回任务的历史修订列表及下一页偏移，保留各次确认时的事实和范围。',
43:'返回指定不可变修订的事项、人工结果、范围、引用及完成信息。',
44:'返回当前Case、未完人工任务数量、running/unknown阻塞Run、结案/重开资格及是否需要待办确认。',
45:'只保存显式提交的管理字段，实际变化才增加行版本；返回保存后的完整Case及changed，不执行调查。',
46:'核对当前运行和人工待办后，将Case标为resolved，保存解决人/时间/理由；返回Case快照，任务与Run保持。',
47:'将已解决Case恢复in_progress，记录重开时间并清空当前结案字段；返回Case快照，历史活动保留，不自动调查。',

48:'单条人工判定，reason必填，追加反馈并保留模型分诊；误报/正常关闭，已关闭改真实威胁/需跟进恢复处理中。E28读feedback及facts，E30读活动，不自动改父事件/Case结论或启动模型。',
49:'仅用户明确选中的items，共用feedback判定和理由；逐项版本校验，整批成功或拒绝，默认配置最多100项。不会自动按相似度选中或批量改判。',
50:'PATCH省略保持，owner_id=null取消分配、tags=[]清空；仅分配不改状态，人工关闭须reason且保留原判定。返回保存时facts及activity_id，最新摘要沿E28读取。',
51:'items带每条ID和expected_row_version，共用changes；批量整体事务，未选告警不改。设置负责人不自动关闭或重开。返回按ID排序的逐项快照和changed_count。',
52:'分配未解决事件默认进入处理中；已解决仅改负责人不重开。显式resolved须resolution_note；severity_override非null须理由，null恢复自动等级且清空覆盖元数据；不改成员告警等级。',
53:'对明确选中事件应用共用changes；每项都验证版本、状态和理由，整批成功或拒绝。负责人/严重度/状态遵守单条规则，不修改其他事件或Case。',
54: '返回告警筛选命中的全部记录CSV；已选列按给定顺序，超限明确失败。不会修改记录。',
55: '返回事件筛选命中的全部记录CSV；已选列按给定顺序，超限明确失败。不会修改记录。',
56: '返回调查筛选命中的全部记录CSV；已选列按给定顺序，超限明确失败。不会修改记录。',
57:'返回同一告警范围的6个数量/比例字段、三个筛选条件和观察时间。例6条告警中4条归为2事件、2条未归并，compression_rate=0.5；处理中只数这些事件的实际in_progress状态。',
}


def blocks(text):
    return {name: body.strip() for name, body in re.findall(
        r'^## ([^\n]+)\n(.*?)(?=^## |\Z)', text, re.M | re.S)}


def rows(body):
    for line in body.splitlines():
        if not line.startswith('|') or re.fullmatch(r'[| :\-]+', line):
            continue
        yield [s.strip().replace(r'\|', '|') for s in re.split(r'(?<!\\)\|', line.strip('|'))]


def links(root, source, text, self_url=None):
    """可点击文档必须随包发布；源码引用保留文件/行号，不伪造在线链接。"""
    mapping = {(root / p).resolve(): '/handoff/sources/' + Path(p).name.replace('.md', '.html') for p in SOURCES}
    for name in ['README', 'interfaces', 'response-fields', 'dynamic-fields']:
        mapping[(root / AUDIT_REL / (name + '.md')).resolve()] = '/handoff/audit/' + ('guide' if name == 'README' else name) + '.html'
    base = root / 'deliverables/investigation-validation-20261106/http-handoff'
    for name in ['README', 'endpoints', 'schemas', 'features']:
        mapping[(base / (name + '.md')).resolve()] = '/handoff/' + ('guide' if name == 'README' else name) + '.html'
    mapping[(root / AUDIT_REL / 'coverage.json').resolve()] = '/handoff/audit/coverage.json'

    def replace(m):
        label, url = m.groups()
        if url == '/' or url.startswith(('http:', 'https:', '/handoff/', '/#/')):
            return m.group(0)
        if url.startswith('#'):
            return f'[{label}]({self_url or ""}{url})'
        path, sep, fragment = url.partition('#')
        target = (source.parent / path).resolve()
        if target in mapping:
            return f'[{label}]({mapping[target]}' + (sep + fragment if sep else '') + ')'
        # 相对静态文件如examples.json由生成器自身输出。
        if target.is_relative_to(base) and target.suffix in ['.json', '.html']:
            return f'[{label}](/handoff/{target.relative_to(base)})'
        try:
            location = str(target.relative_to(root))
        except ValueError:
            location = path
        return f'{label}（来源：`{location}' + (sep + fragment if sep else '') + '`）'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace, text)


def enrich_contract(root, doc, features, endpoints, version):
    audit = root / AUDIT_REL
    sc = doc['components']['schemas']
    fixed = blocks((audit / 'response-fields.md').read_text())
    count = 0
    for name, body in fixed.items():
        for row in rows(body):
            if len(row) != 6 or row[0] == '输出字段':
                continue
            field, _, required, nullable, meaning, origin = row
            if name not in sc or field not in sc[name].get('properties', {}):
                raise ValueError(f'审计字段无法映射：{name}.{field}')
            sc[name]['properties'][field]['description'] = links(
                root, audit / 'response-fields.md',
                f'{meaning}\n\nOpenAPI required：{required}；{nullable}。来源：{origin}',
                '/handoff/audit/response-fields.html')
            sc[name]['properties'][field]['x-audit-url'] = '/handoff/audit/response-fields.html#' + name.lower()
            count += 1
    if count != 542:
        raise ValueError(f'固定字段审计数量发生变化：{count}')
    dynamic = blocks((audit / 'dynamic-fields.md').read_text())
    if sum('落点：' in body for body in dynamic.values()) != 28:
        raise ValueError('动态字段审计数量发生变化')
    groups = {g: [f for f in features if f['group'] == g] for g in GROUPS}
    if {g: len(fs) for g, fs in groups.items()} != {g: n for g, (_, n) in GROUPS.items()}:
        raise ValueError('三类功能数量不匹配')
    doc['info']['version'] = version
    doc['info']['title'] = '调查服务 HTTP API'
    doc['info']['description'] = (
        '后端HTTP接口，按告警、事件、调查分类。展开接口查看用途、输入参数、输出字段、示例、操作结果和错误。'
        '\n\n状态标明接口逻辑是否实现；E19–E21为未实现预留接口，返回501。'
        '本机18024为grouping-summary-20261113-r1-local，21正式18024为grouping-summary-20261113-r1；两端均已挂载57操作，本机使用v12_upgrade_dev，21使用aisoc。'
        '原43操作经本机原路由/真实隔离库检查；执行模型和外部查询用测试替身。新增4个Case管理操作经本机TCP及21正式HTTP完成修改、结案、重开及SQL读回；原Case/H流程证据保留；未调用真实模型，模型质量仍未通过。'
        '新增六个告警/事件管理操作复用现有字段，单条和批量均支持，测试不调用模型。'
        '示例为合成数据，实际执行和结论状态以响应字段为准。'
        '\n\n[HTTP接入说明](/handoff/guide.html) · [下载OpenAPI](/handoff/openapi.json)')
    doc['tags'] = [
        {'name':'告警','description':'告警列表、详情、材料、分诊及关联记录。'},
        {'name':'事件','description':'事件列表、详情、诊断、成员及关联记录。'},
        {'name':'调查','description':'Case、成员范围、调查执行、结果、工件及人工任务。'},
    ]
    all_ops = {o['operationId']: o for methods in doc['paths'].values() for o in methods.values() if isinstance(o, dict) and 'operationId' in o}
    for e in endpoints:
        eid = e['id']; number = int(eid[1:]); op = all_ops[eid]
        if number in [48,49,50,51,54]:
            tags = ['告警']
        elif number in [52,53,55,57]:
            tags = ['事件']
        elif number <= 21 or number >= 38:
            tags = ['调查']
        elif number in [30,32,33]:
            tags = ['告警','事件']
        elif number in [23,25,27,29,35,37]:
            tags = ['事件']
        else:
            tags = ['告警']
        status = '未实现' if number in [19,20,21] else '已实现'
        op['tags'] = tags; e['tags'] = tags; e['tag'] = '、'.join(tags)
        op['summary'] = f'{eid} [{status}] {e["title"]}'
        op['x-implementation-status'] = status; e['status'] = status
        op.pop('x-feature-details',None)
        inputs=[]
        for loc, label in [('path','路径'),('query','查询')]:
            names=[p['name'] for p in e['params'] if p['in']==loc]
            if names:inputs.append(label+'参数：'+', '.join('`'+n+'`' for n in names))
        if e['body']:
            schema=e['body']['schema'];model=schema.get('$ref','').rsplit('/',1)[-1]
            inputs.append('JSON请求体：`'+model+'`，字段和必填要求见Request body')
        else:inputs.append('无请求体')
        response=e['response'].get('schema',{}).get('$ref','').rsplit('/',1)[-1]
        if 54<=number<=56:response='text/csv；字段名表头，完整CSV，错误仍为JSON'
        desc = (f'**实现状态：** {status}\n\n**用途：** {e["title"]}。'
                + '\n\n**输入：** '+'；'.join(inputs)+'。'
                + f'\n\n**输出：** HTTP {e["example"]["response_status"]}，`{response}`；完整字段和示例见Responses。'
                + '\n\n**结果：** '+RESULTS[number]+'\n\n**规则与限制：** '+e['note'])
        verification = ('本机新8告警/4事件/6关系，13次真实TCP与独立SQL计算一致；覆盖已归并/未归并、跨来源、日期及未知时间、空事件和422；查询前后数据保持。两端正式发布另有读回回执。' if number==57 else '本机62次真实TCP及PG核对：55条告警超过旧单页范围，三类104个公开列与列表逐值一致，行上限413，查询前后数据不变；发布读回见本批回执。' if 54<=number<=56 else '已确认返回501，功能未实现。' if number in [19,20,21] else
            '本机真实PostgreSQL和TCP完成三类列表117次请求：筛选、九种排序双向分页、旧游标兼容及查询前后行不变；21发布读回见本批回执。' if number in [2,26,27] else
            '本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。' if 48 <= number <= 53 else
            '本机及21正式HTTP完成管理读取/局部更新、结案与重开，SQL读回一致；任务/Run保持，版本冲突和未完任务确认已验证。' if number >= 44 else
            '本机原路由及真实隔离库的执行、保存和读取通过；模型/外部查询为替身，真实模型效果未据此验收。' if number in [13,36,37] else
            '本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。' if number in [1,3,12,38,40,41,42,43,44,45,46,47] else
            '本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。')
        desc += '\n\n**验证结果（列表更新于2026-11-13；其他沿既有验收）：** '+verification
        desc += '\n\n**部署情况：** '+'本机18024为grouping-summary-20261113-r1-local，21正式18024为grouping-summary-20261113-r1；两端均已挂载57操作，本机使用v12_upgrade_dev，21使用aisoc。'
        response_notes = ''
        if number==57:
            for model in ('GroupingSummary','GroupingQuery'):
                response_notes+='\n\n### '+model+'\n\n| 字段 | 含义 |\n| --- | --- |\n'
                for field,prop in sc[model]['properties'].items():
                    response_notes+='| `'+field+'` | '+prop.get('description', '固定合同版本socai2.incident-grouping.v1').replace('\n',' ')+' |\n'
        relevant = []
        for name, body in dynamic.items():
            match = re.search(r'^落点：([^\n]+)', body, re.M)
            if (match and eid in re.findall(r'E\d{2}', match[1])) or (name == 'activity-target' and eid in ['E17', 'E30']):
                relevant.append(name)
                body = re.sub(r'<a id="[^"]+"></a>', '', body)
                response_notes += '\n### 输出字段：' + name + '\n\n' + links(root, audit / 'dynamic-fields.md', body) + '\n'
        if eid in ['E15', 'E16', 'E18', 'E31', 'E33', 'E34', 'E35']:
            for name in ['版本化正文需要继续沿原件合同读取', '原件可用性与错误不能统一处理']:
                response_notes += '\n### ' + name + '\n\n' + links(root, audit / 'dynamic-fields.md', dynamic[name])
        maincode=str(e['example']['response_status'])
        op['responses'][maincode]['description'] = RESULTS[number] + response_notes
        if 54<=number<=56:
            kind={54:'alerts',55:'incidents',56:'cases'}[number]
            columns=json.loads((root/'deploy/api-docs/list-export-columns.json').read_text())[kind]
            model={54:'AlertFacts',55:'IncidentFacts',56:'CaseView'}[number]
            derived={'owner_name':'本租户人员目录中的负责人显示名；未解析为null。','member_count':'当前案件告警成员数。','open_task_count':'当前案件未完成人工任务数。','derived.member_count':'事件当前告警成员数。','derived.first_activity_at':'成员真实event_time最小值；全部缺失为null。','derived.last_activity_at':'成员真实event_time最大值；全部缺失为null。','derived.severity_auto':'成员已知等级最大值；全部未知为null。','derived.severity_effective':'人工覆盖优先，否则使用成员最大等级。','derived.severity_source':'manual_override/member_max；无已知等级为null。'}
            table='\n\n**可选输出列（按columns传入顺序）：**\n\n| 列名 | 默认列 | 含义 |\n| --- | --- | --- |\n'
            for col in columns['allowed']:
                desc_field=derived.get(col) or sc[model]['properties'][col.split('.',1)[1]].get('description',col)
                table+='| `'+col+'` | '+('是' if col in columns['defaults'] else '否')+' | '+desc_field.split('\n\n')[0].replace('|','\\|').replace('\n',' ')+' |\n'
            desc+=table
            op['responses'][maincode]['description']+=table
            op['x-csv-columns']=columns
        op['description'] = desc
        op['x-dynamic-sections'] = relevant
        e['description'] = desc
        # 框架422是ValidationError[]；业务422还可能是字符串，分别保留，不混入501固定DTO。
        op['responses']['422']['content']['application/json']['schema'] = {'anyOf': [
            {'$ref': '#/components/schemas/HTTPValidationError'},
            {'$ref': '#/components/schemas/ServiceError'}]}

    # 给原本宽松的动态Schema附加审计字段，不改变JSON类型/必填项或源合同。
    schema_sections = {
        'CaseDetail': {'members': 'case-members', 'linked_incidents': 'case-linked-incidents', 'current_assessment': 'current-assessment'},
        'RunDetail': {'members': 'run-members', 'steps': 'run-steps', 'artifacts': 'artifact-metadata', 'usage': 'usage-total'},
        'TraceView': {'run': 'run-row', 'steps': 'run-steps', 'artifacts': 'artifact-metadata', 'usage': 'usage-total'},
        'ResultDetail': {'members': 'result-members', 'delivery': 'delivery'},
        'SubjectView': {'material': 'alert-material-meta', 'triage': 'alert-triage-feedback', 'feedback': 'alert-triage-feedback'},
        'SubjectPage': {'overall_stats': 'overall-stats'},
        'ArtifactContent': {'artifact': 'artifact-metadata'},
    }
    for model, fields in schema_sections.items():
        for field, section in fields.items():
            p = sc[model]['properties'][field]
            p['description'] = p.get('description', '') + '\n\n' + links(root, audit / 'dynamic-fields.md', dynamic[section])
            p['x-audit-url'] = '/handoff/audit/dynamic-fields.html#' + section
    sc['ContentView']['properties']['metadata']['description'] += '\n\nE31为材料元数据；E33/E34/E35为工件元数据。详见各操作动态字段，不能套用Case的artifact包装。'


def publish_pages(root, out, doc, features, endpoints, version, render, head, intro, schema_table, typ, dump):
    """同一源生成标准Swagger、接入说明及审计补充。"""
    audit = root / AUDIT_REL
    (out / 'audit').mkdir(exist_ok=True)
    (out / 'sources').mkdir(exist_ok=True)
    nav = '<nav><a href="/">Swagger HTTP接口</a><a href="/handoff/openapi.json">下载OpenAPI</a><a href="/handoff/guide.html">接入说明</a></nav>'
    for name in ['README', 'interfaces', 'response-fields', 'dynamic-fields']:
        source = audit / (name + '.md'); text = source.read_text()
        # 保留审计原件的历史结论；线上附上当前发布注记。
        notice = f'<p class="badge">本页保留既有JSON接口字段审计原文（原文的47/53操作和当前仅指原审计时点）。{version}总计57操作；新增CSV接口及104个可选列见<a href="/handoff/endpoints.html#e54">E54–E56</a>。E57新增归并统计和12个固定字段，见<a href="/handoff/endpoints.html#e57">E57</a>。旧审计不替代新接口验收。</p>'
        (out / 'audit' / source.name).write_text('> 既有JSON接口字段审计原文；原文47/53操作仅指原审计时点。本批当前57操作，CSV接口/104列见[E54–E56](../endpoints.md#e54)；新增统计/12字段见[E57](../endpoints.md#e57)。\n\n'+text)
        (out / 'audit' / (('guide' if name == 'README' else name) + '.html')).write_text(
            head + nav + notice + render(links(root, source, text)) + '</main></html>')
    (out / 'audit/coverage.json').write_bytes((audit / 'coverage.json').read_bytes())
    for path in SOURCES:
        source = root / path
        if source.suffix == '.md':
            (out / 'sources' / source.name).write_bytes(source.read_bytes())
            (out / 'sources' / (source.stem + '.html')).write_text(head + nav + render(links(root, source, source.read_text())) + '</main></html>')
        else:
            (out / 'sources' / source.name).write_bytes(source.read_bytes())
    # 接入指南沿用既有人工内容；暂存目录生成也从仓库源读取。
    guide = root / 'deliverables/investigation-validation-20261106/http-handoff/README.md'
    (out / 'README.md').write_bytes(guide.read_bytes())
    (out / 'guide.html').write_text(head + nav + render(links(root, guide, guide.read_text())) + '</main></html>')
    (out / 'swagger-config.json').write_text(dump({'url': '/handoff/openapi.json', 'filter': True, 'validatorUrl': None,
        'docExpansion': 'none', 'deepLinking': True, 'displayOperationId': True, 'persistAuthorization': False, 'tryItOutEnabled': False}))

    redirect = '<!doctype html><html lang="zh-CN"><meta charset="UTF-8"><meta http-equiv="refresh" content="0;url=/"><title>Swagger HTTP API</title><p><a href="/">打开Swagger HTTP接口文档</a></p></html>'
    for filename in ['index.html','features.html']:
        (out / filename).write_text(redirect)
