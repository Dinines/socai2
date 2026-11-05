"""Read-only source inventory for the current investigation documentation.

Writes documentation only. This is a static write-site catalog, not a runtime
SQL audit log. Unexpanded **values expressions remain explicit in the output.
"""
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/investigation'
ALIASES = {'A': 'alerts', 'I': 'incidents', 'R': 'runs', 'RM': 'run_members', 'S': 'run_steps',
    'steps': 'run_steps', 'F': 'artifacts', 'C': 'cases', 'CA': 'case_alerts', 'CI': 'case_incidents',
    'IA': 'incident_alerts', 'AS': 'alert_assessments', 'D': 'incident_diagnoses',
    'RES': 'results', 'RESM': 'result_members', 'ACT': 'activities', 'TGT': 'activity_targets',
    'T': 'tasks', 'V': 'task_revisions', 'table': 'alerts | incidents (stage kind)',
    'result_table': 'alert_assessments | incident_diagnoses (stage kind)'}


def main():
    models = ast.parse((ROOT / 'services/api/app/models/socai2.py').read_text('utf-8'))
    classes = {c.name: n.value.value for c in models.body if isinstance(c, ast.ClassDef)
        for n in c.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__tablename__' for t in n.targets)}
    files = sorted((ROOT / 'services/api/app/socai2').glob('*.py'))
    files += [ROOT / 'services/fusion/app/services/socai2_sink.py']
    rows, hashes = [], {}

    def add(path, line, owner, operation, table, code, fields=None):
        rows.append({'source': path.relative_to(ROOT).as_posix(), 'line': line, 'function': owner,
            'operation': operation, 'target': table, 'fields': fields or {}, 'expression': code})

    for path in files:
        source = path.read_text('utf-8')
        hashes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        tree = ast.parse(source)
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}

        def owner(node, parents=parents):
            cur = node
            while cur in parents:
                cur = parents[cur]
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    return cur.name
            return '<module>'

        def target(expr, path=path):
            name = ast.unparse(expr)
            if name.endswith('.__table__'):
                cls = name.split('.')[-2]
                return 'socai2.' + classes.get(cls, cls)
            found = ALIASES.get(name, name)
            if path.name == 'human_task_service.py' and name == 'R':
                found = 'results'
            return 'socai2.' + found

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'insert', 'update', 'delete'}:
                if path.name == 'socai2_sink.py':
                    if len(node.args) < 3 or not isinstance(node.args[1], ast.Constant):
                        continue
                    add(path, node.lineno, owner(node), 'INSERT', 'socai2.' + node.args[1].value,
                        ast.unparse(node), {'values': ast.unparse(node.args[2])})
                    continue
                cur = node
                while cur in parents and isinstance(parents[cur], (ast.Call, ast.Attribute)):
                    parent = parents[cur]
                    if isinstance(parent, ast.Call) and isinstance(parent.func, ast.Attribute) and parent.func.attr == 'execute':
                        break
                    cur = parent
                fields = {}
                for value in ast.walk(cur):
                    if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) and value.func.attr == 'values':
                        fields.update({k.arg or '**' + ast.unparse(k.value): ast.unparse(k.value) for k in value.keywords})
                add(path, node.lineno, owner(node), node.func.id.upper(), target(node.args[0]), ast.unparse(cur), fields)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                match = re.match(r'\s*(UPDATE|INSERT INTO|DELETE FROM)\s+(socai2\.\w+)', node.value, re.IGNORECASE)
                if match:
                    add(path, node.lineno, owner(node), match[1].upper(), match[2], node.value.strip())

    migration = ROOT / 'services/api/migrations/125_socai2_baseline_input_freshness.sql'
    text = migration.read_text('utf-8')
    start = text.index('CREATE OR REPLACE FUNCTION socai2.auto_adopt_baseline_result')
    stop = text.index('END $fn$;', start)
    block = text[start:stop]
    hashes[migration.relative_to(ROOT).as_posix()] = hashlib.sha256(migration.read_bytes()).hexdigest()
    for match in re.finditer(r'(?m)^\s*(INSERT INTO|UPDATE)\s+(socai2\.\w+).*?;', block, re.DOTALL):
        line = text[:start + match.start()].count('\n') + 1
        add(migration, line, 'auto_adopt_baseline_result', match[1], match[2], match[0].strip())

    for name in ('deduplicator', 'correlator', 'entity_risk', 'delivery_recovery'):
        path = ROOT / ('services/fusion/app/services/' + name + '.py')
        source = path.read_text('utf-8')
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {
                    'set', 'setex', 'hset', 'zadd', 'expire', 'sadd', 'incr', 'incrbyfloat', 'zremrangebyscore'}:
                add(path, node.lineno, name, 'Redis ' + node.func.attr, 'Redis DB 13', ast.unparse(node))
        hashes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    lake = ROOT / 'services/fusion/app/services/lake_writer.py'
    lake_tree = ast.parse(lake.read_text('utf-8'))
    columns = next(ast.literal_eval(n.value) for n in lake_tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == '_COLUMNS' for t in n.targets))
    hashes[lake.relative_to(ROOT).as_posix()] = hashlib.sha256(lake.read_bytes()).hexdigest()
    for n in ast.walk(lake_tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'execute':
            add(lake, n.lineno, 'flush', 'INSERT', 'ClickHouse socai2_next_validation.raw_events',
                ast.unparse(n), {'columns': list(columns), 'default_id_form': 'event_id omitted when using database default'})

    rows.sort(key=lambda r: (r['source'], r['line']))
    result = {'basis': 'current branch source, not executed SQL logs', 'pg_database': 'socai2_next_20261104',
        'pg_schema': 'socai2', 'count': len(rows), 'source_sha256': hashes, 'writes': rows,
        'limitations': ['dynamic **values kept as source expressions; see linked implementation and field dictionary',
            'one write site may execute zero/many times depending on runtime conditions',
            'DDL and constraint-only triggers are not business row writes']}
    (OUT / 'current-database-write-catalog.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    md = ['# 当前数据库写点明细', '',
        '配合[当前执行账本](current-execution-ledger.md)阅读。以下逐项从当前业务源码与自动采用函数提取；每项有源文件、行号、调用函数、操作、目标、字段及完整表达式。不是某次Run实际执行的SQL日志。', '',
        f'共 {len(rows)} 个写点；字段值和WHERE条件完整保留在[JSON明细](current-database-write-catalog.json)及链接源码中。`**values`等动态字段保留代码表达式，不能当成字段已展开。', '',
        '| 序号 | 函数/源代码 | 操作 | 目标 | 显式字段或参数 |', '|---|---|---|---|---|']
    for i, row in enumerate(rows, 1):
        label = row['source'].rsplit('/', 1)[-1] + ':' + str(row['line']) + ' ' + row['function']
        link = f'[{label}](/E:/aisoc/socai2/{row["source"]}:{row["line"]})'
        keys = ', '.join(row['fields']) or '详见完整表达式/SQL'
        md.append(f'| {i} | {link} | {row["operation"]} | {row["target"].replace("|", "/")} | {keys.replace("|", "/")} |')
    (OUT / 'current-database-write-catalog.md').write_text('\n'.join(md) + '\n', 'utf-8')
    print(json.dumps({'writes': len(rows), 'source_files': len(hashes), 'targets': sorted({r['target'] for r in rows})}))


if __name__ == '__main__':
    main()
