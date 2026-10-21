"""Capture three new authenticated alert/Fusion envelopes without any model."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys

B = '3a-triage-recovery-20261020'
E = Path('/evidence')
ALIASES = ['warm', 'concurrent', 'unknown']

async def main(alias='all'):
    os.umask(0o077)
    assert alias in [*ALIASES, 'all']
    assert not (E / 'inputs.json').exists(), 'Inputs frozen; do not publish again'
    for case in ALIASES if alias == 'all' else [alias]:
        output = E / ('ingress-' + case)
        assert not output.exists(), 'Inspect checkpoint; do not resubmit accepted or unknown inputs'
        output.mkdir(mode=0o700)
        spec = importlib.util.spec_from_file_location('existing_ingress', '/operators/ingress_triage_durability_3a.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.E = output
        module.B = B
        # The original operator requires state.batch==B. Supply a distinct
        # UUID namespace for each input without changing the batch contract.
        original_uuid5 = module.uuid.uuid5
        module.uuid = type('UUIDs', (), {
            'uuid5': staticmethod(lambda namespace, name: original_uuid5(namespace, name + '/' + case)),
            'UUID': staticmethod(__import__('uuid').UUID),
            'NAMESPACE_URL': __import__('uuid').NAMESPACE_URL,
        })
        await module.main()
    if all((E / ('ingress-' + case) / 'normal-fused-envelope.json').exists() for case in ALIASES):
        inputs = {case: json.loads((E / ('ingress-' + case) / 'normal-fused-envelope.json').read_text()) for case in ALIASES}
        assert len({value['alert_row_id'] for value in inputs.values()}) == 3
        p = E / 'inputs.json'
        with p.open('x') as stream: json.dump(inputs, stream, indent=2)
        p.chmod(0o600)
        print(json.dumps({'captured_alerts': 3, 'real_model_calls': 0}))

if __name__ == '__main__':
    asyncio.run(main(*sys.argv[1:]))
