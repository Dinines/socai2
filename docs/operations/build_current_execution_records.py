"""Index existing synthetic execution exports without changing their contents."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'docs/operations/evidence/socai2-kafka-chain-20261105/k2/20261105T001341-export/database-20261105T001344.json'
OUT = ROOT / 'docs/investigation/current-execution-records.md'


def cell(value):
    return str(value if value is not None else '—').replace('|', '\\|').replace('\n', ' ')


def main():
    data = json.loads(SOURCE.read_text('utf-8'))
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    cases = {r['id']: r for r in data['cases']}
    alerts = {r['id']: r for r in data['alerts']}
    incidents = {r['id']: r for r in data['incidents']}
    artifacts = {r['id']: r for r in data['artifacts']}
    runs = sorted(data['runs'], key=lambda r: (r['requested_at'], r['id']))
    source_link = '/E:/aisoc/socai2/' + SOURCE.relative_to(ROOT).as_posix()
    md = ['# 调查执行记录逐Run索引', '',
        ('配合[当前执行账本](current-execution-ledger.md)阅读。本页仅整理已保存的真实合成样本记录，'
        '取数时点2026-11-05 00:13:44 UTC（北京时间08:13:44），本次没有重新读取线上状态。'
        '这是实际执行到达情况，不是当前全部代码和分支已成功验收的声明。'), '',
        f'[数据库取回原件]({source_link})；SHA256 `{before}`。原件未修改。', '',
        (f'{len(runs)}条Run、{len(data["run_steps"])}条Step、{len(data["artifacts"])}份工件（包含无Run的Fusion首份材料）。'
        f'保存了{len(data["results"])}份Case结果，采用判断{len(data["case_assessments"])}份。'), '',
        ('下表的输入/输出ID是原件`artifacts[]`的id，内容在content_json/content_text；'
        '按ID搜索即可看到实际请求、原答、查询或报告。model_request保存派发用的协议正文；其存在不证明远端执行成功，凭据不在工件里。'
        'Step的主输出之外还可能有多份工件，因此逐Run也列出全部工件目录。'), '',
        ('关联行数是这份数据库快照中的记录数，不等于本次执行的INSERT/UPDATE次数；'
        '没有事务前后快照的写入不伪称已还原。完整写入规则见[逐表写点](current-database-write-catalog.md)。'), '',
        '| 序号 | Run | 对象/类型 | 状态 | 停止原因 |', '|---|---|---|---|---|']
    titles = {}
    for i, run in enumerate(runs, 1):
        parent = cases.get(run['case_id']) or alerts.get(run['alert_id']) or incidents.get(run['incident_id']) or {}
        titles[run['id']] = parent.get('title', '未记录标题')
        md.append(f'| {i} | [{run["id"]}](#run-{i}) | {cell(titles[run["id"]])} / {run["kind"]} | {run["state"]} | {cell(run["stop_reason"])} |')
    for i, run in enumerate(runs, 1):
        rid = run['id']
        steps = sorted((s for s in data['run_steps'] if s['run_id'] == rid), key=lambda s: s['seq'])
        arts = sorted((a for a in data['artifacts'] if a['run_id'] == rid), key=lambda a: (a['captured_at'], a['id']))
        publications = [r for r in data['results'] if r['source_run_id'] == rid]
        counts = {table: sum(r.get(key) == rid for r in data[table]) for table, key in [
            ('run_members', 'run_id'), ('alert_assessments', 'source_run_id'),
            ('incident_diagnoses', 'source_run_id'), ('result_members', 'run_id')]}
        md += ['', f'<a id="run-{i}"></a>', f'## {i}. {titles[rid]} · {run["kind"]}', '',
            f'Run：`{rid}`；对象：`{run["case_id"] or run["alert_id"] or run["incident_id"]}`。', '',
            (f'状态：`{run["state"]}`；停止：`{run["stop_reason"]}`；交付：`{run["delivery_state"]}`。'
            f'请求 `{run["requested_at"]}`，开始 `{run["started_at"]}`，结束 `{run["ended_at"]}`。'), '',
            (f'冻结输入：`{run["input_artifact_id"]}`；范围版本：`{run["scope_revision"]}`。'
            f'关联行数：{json.dumps(counts, ensure_ascii=False)}。'), '',
            '| seq | 阶段/类型/名称 | 状态 | 输入工件 | 输出工件 | 行数/错误 |', '|---|---|---|---|---|---|']
        for step in steps:
            md.append('| ' + ' | '.join(cell(x) for x in [step['seq'],
                f'{step["stage_code"]} / {step["kind"]} / {step["name"]}', step['state'],
                step['input_artifact_id'], step['output_artifact_id'],
                json.dumps({'rows': step['returned_rows'], 'error': step['error']}, ensure_ascii=False)]) + ' |')
            for key in ('input_artifact_id', 'output_artifact_id'):
                if step[key]:
                    assert step[key] in artifacts and artifacts[step[key]]['run_id'] == rid, (rid, step[key])
        if not steps:
            md += ['', '该Run尚无Step，不能按完成处理。']
        md += ['', '| 全部工件ID | 类型 / Schema | Step ID |', '|---|---|---|']
        for artifact in arts:
            md.append('| ' + ' | '.join(cell(x) for x in [artifact['id'],
                artifact['kind'] + ' / ' + artifact['schema_version'], artifact['step_id']]) + ' |')
        md += ['', '本轮Case结果：']
        if not publications:
            md += ['', '没有Case results记录。A/I的输出分别查上述alert_assessments/incident_diagnoses。']
        for result in publications:
            md += ['', (f'- `{result["id"]}`：conclusion={cell(result["conclusion"])}；'
                f'origin={result["conclusion_origin"]}；validation={result["validation_state"]}；'
                f'delivery={result["delivery_state"]}；report_artifact_id=`{result["report_artifact_id"]}`。')]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before
    OUT.write_text('\n'.join(md) + '\n', 'utf-8')
    print(json.dumps({'runs': len(runs), 'steps': len(data['run_steps']), 'artifacts': len(data['artifacts']),
        'results': len(data['results']), 'adopted_assessments': len(data['case_assessments']), 'source_sha256': before}))


if __name__ == '__main__':
    main()
