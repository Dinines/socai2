"""Selected existing PG checks only; no model or production source calls."""
import asyncio
import importlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
config = json.loads((HERE / 'config.json').read_text())
os.environ.update(json.loads((ROOT / config['environment_file']).read_text()))
os.environ.update(config['runtime_overrides'])
os.environ['SOCAI2_INVESTIGATION_POLICY'] = str(ROOT / config['policy'])
sys.path[:0] = [str(ROOT), str(ROOT / 'services/api'), str(ROOT / 'services/api/tests')]


async def main():
    from tools.testdata.incident_integration.run import connect
    records = []
    suffix = '-04' if '--projection-fixed' in sys.argv else '-03' if '--projection' in sys.argv else '-02' if '--followup' in sys.argv else ''
    selected = config['projection_checks'] if suffix in {'-03', '-04'} else config['followup_checks'] if suffix else config['checks']
    assert not (HERE / ('pg-checks' + suffix + '.json')).exists(), 'check_batch_already_recorded'
    def record(name, passed, detail):
        records.append({'name': name, 'passed': passed, 'detail': detail})
        (HERE / ('pg-checks' + suffix + '.json')).write_text(json.dumps(records, ensure_ascii=False, indent=2, default=str) + '\n')
        print(json.dumps({'name': name, 'passed': passed}), flush=True)
    engine = await connect(config)
    try:
        for module, names in selected.items():
            await importlib.import_module(module).run_checks(engine, record, only=set(names))
        assert len(records) == sum(map(len, selected.values())) and all(r['passed'] for r in records)
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
