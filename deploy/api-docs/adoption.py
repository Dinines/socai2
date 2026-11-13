"""Field meanings and synthetic examples for the existing adoption DTOs."""
FIELDS = {
    'ResultAdoptionRequest': {
        'operation_key': '一次逻辑采用的UUID；相同操作者和完整请求重试沿用，改变意图使用新key。',
        'expected_review_token': '先GET E63取得的64位小写十六进制review_token，原样提交；不自行计算。预览中的判断、成员、任务或Run等变化时409。',
        'reason': '采用理由；去掉两端空白后1–4000字符，记录实际操作者及理由。',
        'acknowledge_pending_work': '默认false；预览requires_pending_work_acknowledgement=true时，用户明确知道任务/Run仍未完成后才传true。不会结束这些工作。',
    },
    'ResultAdoptionReceipt': {
        'case_id':'本案UUID。', 'result_id':'本次选择的原Result UUID，不创建或改写Result。',
        'assessment_id':'这次采用追加的判断UUID。', 'previous_assessment_id':'采用前当前判断UUID；此前无判断为null。',
        'assessment_revision':'这次追加的判断版本序号。', 'case_row_version':'采用提交后的Case行版本；重试返回原回执，最新版本和指针另读E03。',
    },
    'ResultAdoptionPreview': {
        'case_id':'本案UUID。', 'case_row_version':'预览时Case行版本。', 'scope_revision':'预览时案件成员范围版本。',
        'handling_status':'案件处理状态；resolved必须先显式重开才能采用。',
        'review_token':'本次预览摘要，提交E21的expected_review_token原样使用；不是权限凭据。',
        'current_assessment':'当前采用判断及原来源；null表示尚无判断。',
        'candidate':'指定Result的完整既存内容，含conclusion、questions、limitations所在的原结构；不重新生成。',
        'source_run':'候选来源Run的原执行状态和范围，不能用HTTP成功代替执行成功。',
        'current_alert_ids':'当前案件实际成员告警UUID集合。',
        'members':'候选覆盖明细；每项alert_id、assessment_state、conclusion_covered、assessment、limitations，见接口内动态字段表。',
        'uncovered_alert_ids':'当前成员中未被候选有效覆盖的告警UUID；非空不能作为全案判断。',
        'outside_alert_ids':'候选交付成员中不属于当前案件的告警UUID；非空不能采用。',
        'input_freshness':'候选依据新鲜度；state=current/stale/unverified及reasons原因数组，current才可采用。',
        'unfinished_tasks':'当前未完人工任务：task_id、revision_id、title、state；状态not_started或in_progress。',
        'unfinished_runs':'当前未完调查：run_id、kind、state、row_version；状态pending_update/running/unknown。',
        'requires_pending_work_acknowledgement':'是否存在上述未完工作；true时E21必须明确传acknowledge_pending_work=true。',
        'can_adopt':'当前资格是否满足；未完工作不会直接使此值false，但仍要求明确知晓。',
        'refusal_reasons':'不符合资格的原因列表，空列表表示资格允许；具体含义见接口错误说明。',
    },
    'AdoptedAssessment': {
        'id':'判断版本UUID。', 'case_id':'所属案件UUID。', 'revision':'本案判断版本序号，按倒序读取。',
        'scope_revision':'判断形成时的案件范围版本，不等于目前范围。', 'conclusion':'当时采用的结论原文。',
        'origin':'结论内容来源；人工选择模型结果仍为model，不冒充人工生成。',
        'validity':'当时结果校验状态；accepted不等于模型结论准确或当前依据仍新鲜。',
        'formed_at':'来源结果形成时间。', 'adopted_at':'本版本实际采用时间。',
        'adopted_by':'人工采用的用户UUID；服务自动采用通常为null。',
        'actor':'采用者快照：type、user_id、service_name、name_snapshot、service_version；见接口字段表。',
        'reason':'本次人工采用理由；旧自动采用可能为null。',
        'sources':'来源引用，每项result_id/task_revision_id/artifact_id；未使用的引用为null。',
        'members':'当时覆盖的告警，含alert_id和coverage_note限制说明；不是当前成员快照。',
        'results':'来源Result完整原内容，含未解决问题与限制；判断历史本身不重新检查新鲜度，当前状态读取E03。',
    },
    'AssessmentHistory': {
        'items':'按revision倒序的判断版本及原来源。', 'total':'本案全部判断版本数，不受分页影响。',
        'next_offset':'下一页偏移；null结束。每次请求读取当前快照，跨页不冻结。',
    },
}

DYNAMIC = {
    'ResultAdoptionPreview.members[]': 'alert_id：告警UUID；assessment_state：成员分析状态；conclusion_covered：是否计入结论覆盖；assessment：成员结论，可空；limitations：该成员限制，可空。只有有效覆盖且analyzed/unresolved计入全案覆盖。',
    'ResultAdoptionPreview.input_freshness': 'state：current/stale/unverified；reasons：变化或无法验证的原因数组。stale和unverified均不能人工提升为当前全案判断。',
    'ResultAdoptionPreview.unfinished_tasks[]': 'task_id：任务UUID；revision_id：当前修订UUID；title：任务标题原文；state：not_started/in_progress。',
    'ResultAdoptionPreview.unfinished_runs[]': 'run_id：调查UUID；kind：调查类型；state：pending_update/running/unknown；row_version：当前Run行版本。',
    'AdoptedAssessment.actor': 'type：user/service；user_id：人工用户UUID或null；service_name：服务身份或null；name_snapshot：记录时姓名/登录名；service_version：服务版本或null。',
    'AdoptedAssessment.sources[]': 'result_id：来源Result UUID；task_revision_id：来源人工任务修订UUID；artifact_id：来源工件UUID。未使用项为null；本次人工采用只引用指定Result。',
    'AdoptedAssessment.members[]': 'alert_id：采用时覆盖的告警UUID；coverage_note：原覆盖限制说明，可空。',
}


def describe(schemas):
    for name, fields in FIELDS.items():
        assert set(fields) == set(schemas[name]['properties']), name
        for field, meaning in fields.items():
            schemas[name]['properties'][field]['description'] = meaning


def examples(ex, ids, date):
    import copy
    result = copy.deepcopy(ex['ResultView'])
    run = copy.deepcopy(ex['RunView'])
    result.update(id=ids['result'], case_id=ids['case'], kind='baseline', source_run_id=ids['run'], conclusion='仍需核实维护授权；保留待核问题及限制。', conclusion_state='uncertain', conclusion_origin='model', validation_state='accepted', delivery_state='partial')
    run.update(id=ids['run'], case_id=ids['case'], state='completed', scope_revision=1, scope_kind='whole_case', delivery_state='partial', started_at=date, ended_at=date)
    scope = dict(kind='whole_case',alert_ids=[ids['alert']],object_keys=[],window_start=None,window_end=None,limitations=[])
    result['questions'] = [dict(id='authorization',text='这次操作是否经过维护授权？',scope=scope,evidence_requirements=['维护负责人确认'],state='unresolved',answer=None,evidence_refs=[],limitations=['尚未取得授权记录。'])]
    ex['ResultAdoptionRequest'] = dict(operation_key=ids['operation'], expected_review_token='a'*64, reason='保留本轮待复核结论，人工核实任务继续跟进。', acknowledge_pending_work=True)
    ex['ResultAdoptionReceipt'] = dict(case_id=ids['case'], result_id=ids['result'], assessment_id=ids['revision'], previous_assessment_id=None, assessment_revision=1, case_row_version=2)
    assessment = dict(id=ids['revision'], case_id=ids['case'], revision=1, scope_revision=1, conclusion=result['conclusion'], origin='model', validity='accepted', formed_at=date, adopted_at=date, adopted_by=ids['user'], actor=dict(type='user',user_id=ids['user'],service_name=None,name_snapshot='analyst@example.invalid',service_version=None), reason=ex['ResultAdoptionRequest']['reason'], sources=[dict(result_id=ids['result'],task_revision_id=None,artifact_id=None)], members=[dict(alert_id=ids['alert'],coverage_note='维护授权未核实。')], results=[result])
    ex['AdoptedAssessment'] = assessment
    ex['AssessmentHistory'] = dict(items=[assessment],total=1,next_offset=None)
    ex['ResultAdoptionPreview'] = dict(case_id=ids['case'],case_row_version=1,scope_revision=1,handling_status='new',review_token='a'*64,current_assessment=None,candidate=result,source_run=run,current_alert_ids=[ids['alert']],members=[dict(alert_id=ids['alert'],assessment_state='unresolved',conclusion_covered=True,assessment=None,limitations='维护授权未核实。')],uncovered_alert_ids=[],outside_alert_ids=[],input_freshness=dict(state='current',reasons=[]),unfinished_tasks=[dict(task_id=ids['task'],revision_id=ids['revision'],title='核实维护授权',state='not_started')],unfinished_runs=[],requires_pending_work_acknowledgement=True,can_adopt=True,refusal_reasons=[])


def field_notes():
    text = '\n\n### 嵌套动态字段\n\n| 位置 | 每个字段的含义 |\n| --- | --- |\n' + ''.join(f'| `{key}` | {value} |\n' for key,value in DYNAMIC.items())
    text += '\n\n### 采用拒绝原因\n\n| 原因 | 含义与处理 |\n| --- | --- |\n'
    reasons = {
        'case_reopen_required':'案件已解决；需要先重开，采用本身不重开。',
        'result_not_whole_case_baseline':'不是全案基础调查结果；局部探索和助手答案不能覆盖全案。',
        'result_run_not_completed':'来源调查未正常完成，不能手动提升为完成结果。',
        'result_conclusion_not_eligible':'候选未accepted、非model结论、unavailable或正文为空。',
        'result_scope_not_current':'范围版本或冻结成员与当前案件不一致。',
        'result_member_coverage_incomplete':'成员缺失、存在案外成员或部分成员没有有效分析覆盖。',
        'result_input_not_current':'材料、人工反馈等依据已变化或无法核验；先查变化，按业务需要显式发起新调查。',
        'result_adoption_preview_changed':'预览后状态改变；重新预览并由用户核对，不能自动把新摘要换进去提交。',
        'result_adoption_pending_work_confirmation_required':'仍有未完人工任务或Run；先向用户展示并取得明确知晓。',
        'operation_key_conflict':'相同key被用于不同目标、操作者或请求；新意图使用新key。',
    }
    return text + ''.join(f'| `{key}` | {value} |\n' for key,value in reasons.items())
