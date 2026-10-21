"""Clarify all broker-attempt accounting before any C01 probe publication."""
from pathlib import Path
import hashlib
import json
import os

R = Path('/opt/sting-aisoc-socai2')
E = R / 'evidence/c01-fusion-delivery-20261020'


def main():
    os.umask(0o077)
    assert not (E / 'probe').exists() and not (E / 'boundaries').exists() and not (E / 'http').exists()
    previous = E / 'limits.json'
    old = json.loads(previous.read_text())
    assert old['broker_test_publishes'] == 12 and old['test_deliveries'] == 20
    revised = {k: v for k, v in old.items() if k != 'broker_test_publishes'}
    revised.update(broker_send_attempts_including_failed=20, raw_send_attempts=10, fused_send_attempts=10)
    revised['previous_limits_sha256'] = hashlib.sha256(previous.read_bytes()).hexdigest()
    revised['reason'] = 'Count raw input, fused output and failed SDK attempts separately and together; clarify before any real probe publication.'
    revised['expected'] = {'raw': 9, 'fused_acked': 7, 'fused_failed_sdk': 1, 'all_send_attempts': 17,
                           'worker_deliveries_and_output_reads': 18, 'new_alert_rows': 5, 'new_topics': 10, 'new_groups': 5}
    plan = R / 'source/docs/operations/c01-fusion-delivery-plan.md'
    revised['scope_addendum_sha256'] = hashlib.sha256(plan.read_bytes()).hexdigest()
    with (E / 'limits-amended.json').open('x') as output:
        json.dump(revised, output, indent=2)
        output.write('\n')
    (E / 'limits-amended.json').chmod(0o600)
    (E / 'scope-addendum.md').write_bytes(plan.read_bytes())
    (E / 'scope-addendum.md').chmod(0o600)
    print(json.dumps({'limits_clarified_before_real_probe': True, 'all_send_attempts_limit': 20,
                      'deliveries_and_output_reads_limit': 20, 'previous_limits_preserved': True}))


if __name__ == '__main__':
    main()
