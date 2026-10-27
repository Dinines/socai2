"""Package the existing static UI and recorded data; never contacts a backend.

Run from the repository with Python 3 + markdown and Node on PATH.
Recipients only need the generated directory, not this build tool.
"""
from pathlib import Path
import hashlib
import html
import json
import re
import shutil
import subprocess
from urllib.parse import unquote, urlsplit
from html.parser import HTMLParser
import markdown

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables/aisoc-frontend-handoff'
SOURCE = ROOT / 'prototypes/security-pages'
EVIDENCE = ROOT / '.local/verification/alert-reset-replay-20261025/replay'
FILES = ('index.html', 'styles.css', 'icons.js', 'app.js', 'alert-detail.js',
         'data.js', 'replayed-alerts.js', 'serve.py', 'package.json',
         'assets/aisoc-mark.svg', 'tests/replayed-alerts.test.cjs',
         'workspace-model.js', 'workspace-view.js', 'workspace.css', 'tests/workspaces.test.cjs')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def render_doc(path, destination=None):
    title = path.read_text(encoding='utf-8').splitlines()[0].lstrip('# ')
    body = markdown.markdown(path.read_text(encoding='utf-8'), extensions=['tables', 'fenced_code', 'toc'])
    (destination or path.with_suffix('.html')).write_text(
        '<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{html.escape(title)}</title><style>'
        'body{font:16px/1.75 system-ui,-apple-system,"Segoe UI",sans-serif;color:#242424;'
        'max-width:1120px;margin:40px auto;padding:0 24px 64px;background:#fff}'
        'h1{font-size:30px}h2{margin-top:38px;border-bottom:1px solid #e1e5eb;padding-bottom:8px}'
        'a{color:#0078d4;text-decoration:none}a:hover{text-decoration:underline}'
        'table{border-collapse:collapse;width:100%;font-size:14px;display:block;overflow:auto}'
        'th,td{padding:12px;border:1px solid #e1e5eb;text-align:left;vertical-align:top}'
        'th{background:#f3f6fa}pre{background:#f3f6fa;padding:16px;overflow:auto}'
        'code{font-size:.9em;overflow-wrap:anywhere}blockquote{border-left:4px solid #0078d4;'
        'margin:20px 0;padding:4px 18px;background:#eff6fc}'
        '@media(max-width:700px){body{margin-top:20px;padding:0 16px 32px}h1{font-size:25px}}'
        '</style></head><body><main>' + body + '</main></body></html>', encoding='utf-8')


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.links += [attrs[k] for k in ('href', 'src') if k in attrs]
        if 'id' in attrs:
            self.ids.add(attrs['id'])


def verify_links():
    parsed = {}
    for path in OUT.rglob('*.html'):
        parser = Links()
        parser.feed(path.read_text(encoding='utf-8'))
        parsed[path.resolve()] = parser
    count = 0
    for path, parser in parsed.items():
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(OUT.resolve()) or not target.is_file():
                raise ValueError(f'Invalid local link: {path.name}: {link}')
            if url.fragment and not url.fragment.startswith('/') and target.suffix == '.html':
                if unquote(url.fragment) not in parsed[target].ids:
                    raise ValueError(f'Missing anchor: {link}')
            count += 1
    return count


def main():
    origins = {}
    for name in FILES:
        dest = OUT / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / name, dest)
        origins[name] = {'source': (SOURCE / name).relative_to(ROOT).as_posix(),
                         'source_sha256': digest(SOURCE / name)}
    # The exact same factories used by the UI, without executing the app or touching localStorage.
    script = """
const fs=require('node:fs'),vm=require('node:vm');
const ctx={window:{},structuredClone}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync('data.js','utf8'),ctx);
const reference=ctx.window.makeDemoData();
vm.runInContext(fs.readFileSync('replayed-alerts.js','utf8'),ctx);
const replay=ctx.window.mergeReplayedAlerts({alerts:[],assets:[]});
process.stdout.write(JSON.stringify({reference,replay}));
"""
    exported = json.loads(subprocess.check_output(['node', '-e', script], cwd=OUT, text=True))
    reference, replay = exported['reference'], exported['replay']
    assert len(reference['alerts']) == 52 and len(replay['alerts']) == 6
    assert len(reference['cases']) == 12 and len(reference['incidents']) == 12
    dump(OUT / 'data/reference-data.json', reference)
    dump(OUT / 'data/replayed-alerts.json', replay)
    ids = {a['id'] for a in replay['alerts']}
    snapshot = json.loads((EVIDENCE / 'observed-final.json').read_text())
    # No entire snapshot, prompts, configuration or credentials enter the handoff folder.
    fields = ('id', 'tenant_id', 'title', 'description', 'severity', 'status', 'event_time',
              'created_at', 'updated_at', 'resolved_at', 'assigned_at', 'assigned_to_id', 'case_id',
              'confidence', 'ai_score', 'disposition', 'category', 'mitre_tactics', 'mitre_techniques',
              'affected_hosts', 'affected_users', 'entities', 'iocs', 'raw_event', 'source_event_ids',
              'connector_id', 'connector_type', 'is_synthetic')
    samples = []
    for alert in snapshot['alerts']:
        if alert['id'] not in ids:
            continue
        fusion = alert['enrichment_data']['socai2_fusion']
        samples.append({**{key: alert.get(key) for key in fields}, 'enrichment_data': {
            'socai2_fusion': {'identity': {k: fusion['identity'].get(k) for k in ('source', 'source_alert_id')},
                              'incident_id': fusion['incident_id']}}})
    assert {a['id'] for a in samples} == ids
    dump(OUT / 'data/alert-database-sample.json', {
        'captured_at': snapshot['captured_at'], 'database': 'aisoc', 'table': 'public.alerts',
        'note': 'Selected columns only; enrichment_data retains only identity source and incident ID.',
        'alerts': samples})
    explanations = []
    for filename in ('explain-1.json', 'explain-2.json', 'explain-rest.jsonl'):
        for line in (EVIDENCE / filename).read_text().splitlines():
            data = json.loads(line)
            if data['alert_id'] in ids:
                explanations.append({k: data[k] for k in ('alert_id', 'status', 'response')})
    assert len(explanations) == 6 and {e['alert_id'] for e in explanations} == ids
    dump(OUT / 'data/explain-responses.json', explanations)
    shutil.copyfile(EVIDENCE / 'comparison.json', OUT / 'data/replay-comparison.json')

    # Keep the previous query as an explicitly dated historical reference; current query uses all six IDs.
    old_sql = (ROOT / 'docs/design/alert-ui-snapshot-queries.sql').read_text()
    (OUT / 'docs/alert-ui-snapshot-queries.sql').write_text(
        '-- HISTORICAL 2026-10-24 IDs; use ../data/alert-read-queries.sql for 2026-10-25 examples.\n' + old_sql)
    sql = re.sub(r'AND a.id IN \(.*?\)', 'AND a.id IN (' + ',\n               '.join(
        f"'{a['id']}'::uuid" for a in replay['alerts']) + ')', old_sql, count=1, flags=re.S)
    sql = sql.replace('92070605-0aa0-5e8f-8f0f-4a44222a0146', '4c71eec2-77da-5b81-b68a-72801d55ea24')
    sql = sql.replace('a.category, a.confidence', 'a.category, a.mitre_tactics, a.mitre_techniques, a.confidence')
    (OUT / 'data/alert-read-queries.sql').write_text('-- Updated sample IDs only; not executed during packaging.\n' + sql)

    source_doc = ROOT / 'docs/design/alert-ui-data-contract.md'
    replacements = {'../../prototypes/security-pages/alert-detail.js': '../alert-detail.js',
                    '../../prototypes/security-pages/app.js': '../app.js',
                    'alert-ui-snapshot-queries.sql': 'alert-ui-snapshot-queries.sql'}
    def link(match):
        label, target = match.groups()
        if target in replacements:
            return f'[{label}]({replacements[target]})'
        if target.startswith(('http:', 'https:', '#')):
            return match.group(0)
        file, _, fragment = target.partition('#')
        resolved = (source_doc.parent / file).resolve().relative_to(ROOT)
        return f'{label}（仓库参考路径：`{resolved.as_posix()}{"#" + fragment if fragment else ""}`）'
    doc = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, source_doc.read_text())
    banner = ('# 告警 UI 字段对照：完整讨论参考\n\n'
              '> 便携参考副本。当前确认口径请先读 [当前字段对照](data-mapping.html)。'
              '本文件包含先前讨论和不同日期的结果；旧 ID / 库存、只讨论不改页面的阶段说明不代表当前交付状态。'
              '包外源码链接已转换为仓库路径文字。\n\n[返回交接导航](../guide.html)\n\n')
    (OUT / 'docs/alert-ui-data-contract.md').write_text(banner + doc, encoding='utf-8')
    origins['docs/alert-ui-data-contract.md'] = {'source': source_doc.relative_to(ROOT).as_posix(),
                                               'source_sha256': digest(source_doc), 'adaptation': 'portable links and dated banner'}
    source_doc = ROOT / 'docs/design/microsoft-incident-case-analysis.md'
    doc = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, source_doc.read_text())
    (OUT / 'docs/microsoft-incident-case-analysis.md').write_text(doc, encoding='utf-8')
    origins['docs/microsoft-incident-case-analysis.md'] = {'source': source_doc.relative_to(ROOT).as_posix(), 'source_sha256': digest(source_doc), 'adaptation': 'portable reference paths'}
    render_doc(OUT / 'README.md', OUT / 'guide.html')
    for path in sorted((OUT / 'docs').glob('*.md')) + sorted((OUT / 'data').glob('*.md')):
        render_doc(path)
    for name in FILES:
        assert digest(OUT / name) == digest(SOURCE / name), name
    links = verify_links()
    manifest = {'packaged_date': '2026-10-25', 'source_branch': 'codex/security-pages-replica',
                'entry': 'index.html', 'counts': {'reference_alerts': 52, 'replayed_alerts': 6,
                                               'incidents': 12, 'cases': 12},
                'local_html_links_checked': links, 'files': []}
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.name != 'MANIFEST.json':
            rel = path.relative_to(OUT).as_posix()
            manifest['files'].append({'path': rel, 'bytes': path.stat().st_size,
                                      'sha256': digest(path), **origins.get(rel, {})})
    dump(OUT / 'MANIFEST.json', manifest)
    print(json.dumps({'directory': str(OUT), 'files': len(manifest['files']) + 1,
                      'html_links_checked': links}, ensure_ascii=False))


if __name__ == '__main__':
    main()
