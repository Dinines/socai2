import json
import sys
from pathlib import Path

sys.path.insert(0, 'services/api')
sys.path.insert(0, 'docs/operations')
from app.socai2.human_task_contracts import TaskCreate, TaskEdit
from production_human_probe import HOST, INNER

compile(INNER, 'h-container', 'exec')
compile(HOST, 'h-host', 'exec')
r = Path('docs/operations/evidence/case-current-flow-20261110-01')
cfg = json.loads((r / 'run-config.json').read_text())
c = cfg['cases'][0]
d = json.loads(sorted(r.glob('C01-snapshot-*'))[-1].read_text())['data']
rid = next(x['id'] for x in d['runs'] if x['case_id'] == d['cases'][0]['id'])
result = next(x for x in d['results'] if x['source_run_id'] == rid)
refs = [{'type': 'alert_material', 'id': m['id']} for m in d['alert_materials']]
refs += [{'type': 'artifact', 'id': a['id']} for a in d['artifacts'] if a['run_id'] == rid and a['kind'] == 'tool_response']
base = {'operation_key': c['operation_keys']['human_create'], 'expected_scope_revision': 1,
    'title': '验收过程中的材料完整性核查',
    'description': '由用户委托助手根据本批已保存原始材料及工具回执整理；不是业务人员授权确认、访谈或新采集证据。',
    'state': 'not_started', 'origin_result_id': result['id']}
TaskCreate.model_validate(base)
text = '''用户委托助手完成的材料完整性核查，适用范围为本任务明确列出的三条演练告警及时间窗口。
1. 原始材料分别记录登录、进程启动和出站连接。进程记录的 action=process_start、outcome=success 仅支持进程启动成功，不能据此声称 Get-LocalUser 已执行完成、已枚举出用户或已取得数据。
2. 登录记录与出站连接记录中的 source_ip 来自不同动作和记录上下文。仅数值不同不足以认定同一对象的 IP 发生变化、代理/NAT 已存在或发生横向移动；这些关系仍未核实。
3. 时间邻近、主机或用户名相同只支持记录关联，不能直接证明同一进程/会话、因果链或攻击链。检测标签和历史分诊/诊断均保留来源角色，不能替代本案独立观察。
4. 本轮 threat_intel、ueba、authentication_activity 的实际回执为完成且返回 0 行；assets、history、knowledge 受工具预算限制未执行，graph 未接通。未执行不等于查询为空。authentication_activity 不提供变更工单、白名单或业务审批，不能称为已查询授权系统。
5. 目前没有新增业务人员授权证明、目标 IP 归属、文件传输或受损证据。本核查不确认行为合法或恶意，不授权处置；授权与影响继续待核。'''
complete = {k: v for k, v in base.items() if k != 'origin_result_id'}
complete.update(operation_key=c['operation_keys']['human_complete'], expected_row_version=1,
    state='completed', result_text=text, source_refs=refs, result_scope={
        'kind': 'whole_case', 'alert_ids': c['alert_ids'], 'object_keys': [],
        'window_start': c['window_start'], 'window_end': c['window_end'],
        'limitations': ['材料核查由助手代拟，不是独立业务人员确认或额外现场证据。']})
TaskEdit.model_validate(complete)
for name, value in [('H-create-request.json', base), ('H-complete-request.json', complete)]:
    with (r / name).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
print({'adapter_scripts_compile': True, 'H_contracts_valid': True,
    'source_refs': len(refs), 'semantic_feedback_characters': len(text)})
