"""One targeted A/I correction storage check, synthetic replies on isolated PG."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_scope_recovery.real_model import initialize
from tools.testdata.incident_integration.run import connect, save

config, _ = initialize(Path(__file__).with_name('config.json'))
sys.path.insert(0, str(ROOT / 'services/api/tests'))
from test_socai2_incident_boundary_pg import run_checks


async def main():
    results = []
    engine = await connect(config)
    try:
        await run_checks(engine, lambda name, passed, detail: results.append({
            'name': name, 'passed': passed, 'detail': detail}), only={
                'test_boundary_ai_correction_saves_original_and_adopts_valid_answer'})
    finally:
        await engine.dispose()
    save(Path(__file__).with_name(sys.argv[1]), {'real_model_calls': 0, 'checks': results})
    print(results)
    assert results and all(result['passed'] for result in results)


asyncio.run(main())
