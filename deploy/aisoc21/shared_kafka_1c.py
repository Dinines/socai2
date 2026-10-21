#!/usr/bin/env python3
"""One bounded shared-Kafka restart and state comparison for host21 batch 1C.

Requires a successful client-before.json. No broker configuration, existing
topic, message, group offset, container image, or volume is changed by this
operator tool. Restart is explicitly authorized in this project session.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

ROOT = Path('/opt/sting-aisoc-socai2')
EVIDENCE = ROOT / 'evidence/1c-20261020'
CONTAINER = 'sting-infra21-kafka-1'
BOOTSTRAP = '192.168.1.21:9092'
OWN_TOPICS = {'socai2.alerts.raw', 'socai2.alerts.fused', 'socai2.alerts.fused.dlq',
              'socai2.verify.1c-20261020'}
OWN_GROUP = 'socai2.verify.1c-20261020.reader'


def run(args, allow_error=False):
    r = subprocess.run(args, capture_output=True, text=True, timeout=90)
    if r.returncode and not allow_error:
        raise RuntimeError((r.stderr or r.stdout)[-2000:])
    return r


def cli(tool, *args, allow_error=False):
    return run(['docker', 'exec', CONTAINER, tool, '--bootstrap-server', BOOTSTRAP,
                *args], allow_error)


def inspect():
    x = json.loads(run(['docker', 'inspect', CONTAINER]).stdout)[0]
    env = dict(s.split('=', 1) for s in x['Config'].get('Env', []) if '=' in s)
    keys = ('KAFKA_LISTENERS', 'KAFKA_ADVERTISED_LISTENERS',
            'KAFKA_LISTENER_SECURITY_PROTOCOL_MAP', 'KAFKA_PROCESS_ROLES',
            'KAFKA_LOG_DIRS', 'KAFKA_NODE_ID', 'KAFKA_CONTROLLER_QUORUM_VOTERS')
    return {'container_id': x['Id'], 'started_at': x['State']['StartedAt'],
            'status': x['State']['Status'], 'image_id': x['Image'],
            'mounts': x['Mounts'], 'selected_env': {k: env[k] for k in keys if k in env}}


def offsets(time_value):
    text = cli('kafka-get-offsets', '--time', str(time_value)).stdout
    result = {}
    for line in text.splitlines():
        topic, partition, offset = line.rsplit(':', 2)
        if not topic.startswith('__') and topic not in OWN_TOPICS:
            result[topic + ':' + partition] = int(offset)
    return result


def snapshot():
    topics = set(cli('kafka-topics', '--list').stdout.splitlines())
    groups = cli('kafka-consumer-groups', '--describe', '--all-groups', '--state').stdout
    parsed_groups = []
    for line in groups.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[-1].isdigit():
            parsed_groups.append({'group': parts[0], 'state': parts[-2], 'members': int(parts[-1])})
    quorum = cli('kafka-metadata-quorum', 'describe', '--status').stdout
    cluster = dict(line.split(':', 1) for line in quorum.splitlines() if ':' in line)
    return {'container': inspect(), 'topic_names': sorted(topics),
            'existing_topic_names': sorted(t for t in topics if t not in OWN_TOPICS and not t.startswith('__')),
            'old_topic_start_offsets': offsets(-2), 'old_topic_end_offsets': offsets(-1),
            'groups': parsed_groups, 'cluster_id': cluster['ClusterId'].strip(),
            'quorum_status': quorum}


def save(name, data):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def restart():
    assert (EVIDENCE / 'client-before.json').exists(), 'Run client before probe first'
    assert not (EVIDENCE / 'restart-before.json').exists(), 'Existing restart evidence retained; do not repeat'
    before = snapshot()
    save('restart-before.json', before)
    assert before['groups'] and all(g['members'] == 0 for g in before['groups']), 'Active shared consumers; inspect impact first'
    started = time.monotonic()
    run(['docker', 'restart', '--time', '30', CONTAINER])
    for attempt in range(20):
        ready = cli('kafka-topics', '--list', allow_error=True)
        if ready.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError('Kafka not ready; preserved restart-before evidence')
    after = snapshot()
    save('restart-after.json', after)
    for key in ('existing_topic_names', 'old_topic_start_offsets', 'old_topic_end_offsets', 'cluster_id'):
        assert before[key] == after[key], key + ' changed'
    for key in ('container_id', 'image_id', 'mounts', 'selected_env'):
        assert before['container'][key] == after['container'][key], 'Unexpected container change: ' + key
    result = {'action': 'docker restart --time 30 sting-infra21-kafka-1',
              'elapsed_until_ready_seconds': round(time.monotonic() - started, 3),
              'cluster_id': after['cluster_id'], 'same_cluster_id': True,
              'same_container_image_mounts_configuration': True,
              'all_shared_groups_inactive_before_restart': True,
              'existing_user_topics_preserved': len(before['existing_topic_names']),
              'old_user_topic_start_and_end_offsets_unchanged': True,
              'before_started_at': before['container']['started_at'],
              'after_started_at': after['container']['started_at'],
              'limitations': ['Single broker/controller, replication factor 1; no high-availability claim',
                              'No TLS or broker authorization added; test traffic only']}
    save('restart-summary.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cleanup():
    assert (EVIDENCE / 'client-after.json').exists(), 'Require successful replay/resume evidence before cleanup'
    topic = 'socai2.verify.1c-20261020'
    groups = cli('kafka-consumer-groups', '--list').stdout.splitlines()
    if OWN_GROUP in groups:
        cli('kafka-consumer-groups', '--delete', '--group', OWN_GROUP)
    cli('kafka-topics', '--delete', '--topic', topic)
    for attempt in range(10):
        topics = set(cli('kafka-topics', '--list').stdout.splitlines())
        if topic not in topics:
            break
        time.sleep(1)
    groups_after = cli('kafka-consumer-groups', '--list').stdout.splitlines()
    assert topic not in topics and OWN_GROUP not in groups_after
    assert OWN_TOPICS - {topic} <= topics
    result = {'only_smoke_topic_deleted': topic, 'only_smoke_group_deleted': OWN_GROUP,
              'project_topics_retained': sorted(OWN_TOPICS - {topic}),
              'old_topics_deleted': False}
    save('cleanup.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('restart', 'cleanup'))
    args = parser.parse_args()
    restart() if args.action == 'restart' else cleanup()
