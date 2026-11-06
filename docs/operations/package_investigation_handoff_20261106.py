"""Package synthetic test records and handoff contracts locally; never upload or run them."""
import hashlib
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.local/local-investigation/handoff-20261106'
EVIDENCE = ROOT / 'docs/operations/evidence/additional-tests-20261106'


def main():
    index = json.loads((EVIDENCE / 'test-index.json').read_text())
    candidates = set()
    for batch in index['batches']:
        candidates.update((ROOT / batch['plan']).parent.rglob('*.json'))
    candidates.update((ROOT / '.local/local-investigation/page-data-20261106T013645Z').rglob('*.json'))
    plan = json.loads((ROOT / '.local/local-investigation/validation/local-eval-20261106-01/plan.json').read_text())
    candidates.update(ROOT / p for p in plan['source_sha256'])
    candidates.update(p for p in (ROOT / 'prototypes/security-pages-v2').iterdir() if p.suffix in ('.js', '.css', '.html'))
    candidates.update(p for p in (ROOT / 'prototypes/security-pages-v2/assets').rglob('*') if p.is_file())
    candidates.update(p for p in EVIDENCE.iterdir() if p.is_file() and p.name not in ('package-receipt.json', 'closeout.json'))
    names = [
        'docs/investigation/investigation-test-handoff-20261106.md',
        'docs/investigation/socai2-page-data-handoff-20261106.md',
        'docs/investigation/socai2-page-data-readback-20261106.sql',
        'docs/investigation/socai2-page-reader-20261104.md',
        'docs/investigation/current-execution-readback.sql',
        'docs/design/socai2-data-contract-20261103.json',
        'docs/design/socai2-field-dictionary-20261103.md',
        'docs/design/socai2-independent-api-v2.openapi.json',
        'docs/design/socai2-json-contracts-20261103.schema.json',
        'docs/design/alert-incident-case-product-requirements.md',
        'docs/operations/audit_investigation_tests_20261106.py',
        'docs/operations/audit_investigation_reads_20261106.py',
        'docs/operations/index_investigation_tests_20261106.py',
        'docs/operations/verify_investigation_pages_20261106.cjs',
        'docs/operations/package_investigation_handoff_20261106.py',
        'docs/operations/evidence/page-data-20261106/summary.json',
        'docs/operations/evidence/investigation-repair-20261105/local-comparison-summary.json',
        'docs/operations/evidence/investigation-repair-20261105/local-c6-business-fields-summary.json',
        'openspec/changes/complete-socai2-investigation-chain/additional-validation-20261106.md',
        'openspec/changes/complete-socai2-investigation-chain/additional-validation-review-20261106.md',
        'openspec/changes/complete-socai2-investigation-chain/tasks.md',
        'openspec/changes/complete-socai2-investigation-chain/design.md',
        'openspec/changes/complete-socai2-investigation-chain/acceptance-plan-20261104.md',
    ]
    candidates.update(ROOT / p for p in names)
    # Compare bytes against known credentials only in memory; never print them.
    secrets = set()
    env = ROOT / '.local/local-investigation/private/runtime.env'
    for line in env.read_text().splitlines():
        if '=' not in line or line.startswith('#'):
            continue
        key, value = line.split('=', 1)
        value = value.strip().strip('\"\'')
        if re.search(r'(password|secret|token|api_key)', key, re.IGNORECASE) and len(value) > 8:
            secrets.add(value.encode())
        if '://' in value:
            password = urlsplit(value).password
            if password and len(password) > 8:
                secrets.add(password.encode())
    token_file = ROOT / 'dsapi.txt'
    if token_file.exists():
        token = token_file.read_bytes().strip()
        if len(token) > 20:
            secrets.add(token)
    files = {}
    for path in sorted(candidates):
        assert path.is_file() and not path.is_symlink(), str(path.relative_to(ROOT))
        name = path.relative_to(ROOT).as_posix()
        assert '/private/' not in name and not name.endswith('.env')
        raw = path.read_bytes()
        assert not any(secret in raw for secret in secrets), 'credential match in ' + name
        files[name] = raw
    files['START_HERE.md'] = '''# 调查数据与测试交接包

先读 `docs/investigation/investigation-test-handoff-20261106.md`：三案结果、全部本机测试索引、F01—F28功能/字段/页面对应及下一轮部署模型方案。

- `.local/local-investigation/validation/`：13个本机合成模型批次，原计划、入湖、请求/响应、所有导出版本及GET原件。`expected.json`仅为评估答案，不可送模型或并入页面。隐藏目录请通过路径打开。
- `.local/local-investigation/page-data-20261106T013645Z/`：4个无模型数据合同样例及其读回；不要混成真实模型结论。
- `docs/operations/evidence/additional-tests-20261106/`：逐值回查、语义审阅、首次校验器问题和最终验证。模型语义质量未通过。
- `docs/design/`与已固定候选源码：表/字段/JSON/OpenAPI；没有运行凭据。代码仅作交接和复现参考，本包不会自动启动/派发/部署。
- `prototypes/security-pages-v2/index.html`：原页面模板及数据；也可用已有4174服务查看。完整源数据在database.json，页面无需将所有审计字段同时铺开。

旧21环境m/k/r测试通过主报告中的原仓库索引查阅，本包不宣称包含全部远端原件，也不是完整Git仓库或部署包。除本包主交接和附带合同外，历史文档中的相对链接可能需要回原仓库打开。

`PACKAGE_MANIFEST.json`列出每个交付文件的SHA256和字节数。包内13批按各批快照保留；后续回查/legacy补记并不回写历史失败导出。部署模型测试留下一轮，不使用本轮剩余次数自动重试。
'''.encode()
    manifest = {'schema': 'socai2.investigation-handoff-package.v1', 'input_kind': 'synthetic',
        'local_model_batches': 13, 'data_contract_cases': 4, 'known_credentials_found': 0,
        'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in files.items()}}
    files['PACKAGE_MANIFEST.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / 'socai2-investigation-tests-20261106.zip'
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name, expected in manifest['files'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected['sha256']
        html = archive.read('prototypes/security-pages-v2/index.html').decode()
        for link in re.findall(r'(?:src|href)="\./([^"]+)"', html):
            assert 'prototypes/security-pages-v2/' + link.split('?')[0] in archive.namelist()
    receipt = {'archive': str(target.relative_to(ROOT)), 'bytes': target.stat().st_size,
        'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'files': len(files),
        'crc_passed': True, 'all_file_sha256_passed': True, 'page_local_assets_present': True, 'known_credentials_found': 0,
        'scope': '13 local model batches, all their saved exports, 4 contract cases, original pages, frozen candidate and listed contracts/reviews',
        'is_deployment_package': False, 'uploaded': False}
    (EVIDENCE / 'package-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
