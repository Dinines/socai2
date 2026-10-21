"""Include four independent audit reads before the remaining C01 probes.

All previous limits/checkpoints stay immutable. The extra reads were observed
while physical deliveries still totaled 16, below the then-current limit20.
"""
from pathlib import Path
import hashlib
import json
import os

R = Path('/opt/sting-aisoc-socai2')
E = R / 'evidence/c01-fusion-delivery-20261020'


def main():
    os.umask(0o077)
    prior = E / 'limits-amended.json'
    old = json.loads(prior.read_text())
    assert old['test_deliveries'] == 20
    audit_path = E / 'independent-main-readback.json'
    audit = json.loads(audit_path.read_text())
    assert audit['new_physical_deliveries'] == 4
    assert not (E / 'boundaries/gap-seed-started.json').exists() and not (E / 'http').exists()
    main_count = len(list((E / 'probe').glob('event-delivery-*.json')))
    boundary_count = len(list((E / 'boundaries').glob('event-delivery-*.json')))
    assert main_count == 10 and boundary_count == 2
    total = main_count + boundary_count + audit['new_physical_deliveries']
    assert total == 16 and total <= old['test_deliveries']
    revised = dict(old)
    revised['test_deliveries'] = 24
    revised['previous_limits_sha256'] = hashlib.sha256(prior.read_bytes()).hexdigest()
    revised['reason'] = 'The four independent audit broker reads and the resident Fusion raw delivery during HTTP were absent from initial probe accounting. Include them explicitly before remaining gap/DLQ/HTTP deliveries; no replay or extra model calls.'
    revised['physical_deliveries_before_amendment'] = total
    revised['independent_readback_sha256'] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
    revised['expected'] = dict(old['expected'], worker_deliveries_and_output_reads=23, independent_audit_output_reads=4,
                               resident_http_raw_delivery=1, http_fused_capture=1)
    with (E / 'limits-amended2.json').open('x') as output:
        json.dump(revised, output, indent=2)
        output.write('\n')
    (E / 'limits-amended2.json').chmod(0o600)
    print(json.dumps({'independent_audit_reads_included': 4, 'physical_deliveries_so_far': total,
                      'delivery_limit': 24, 'original_limit_exceeded_before_amendment': False}))


if __name__ == '__main__':
    main()
