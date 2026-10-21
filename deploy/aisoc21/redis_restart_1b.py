#!/usr/bin/env python3
"""Persist existing ACLs and verify one authorized host21 Redis restart.

Run only after shared_1b provision/verification. The shared Compose changes by
one Redis command argument; other services and the existing volume are retained.
Private backups include ACL password hashes and must never be published.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from shared_1b import SharedBatch, REDIS_CONTAINER


def main():
    batch = SharedBatch(Path('/opt/sting-aisoc-socai2'))
    compose = Path('/opt/sting-aisoc-infra/compose.yml')
    backup = batch.private / 'redis-restart-before'
    backup.mkdir(mode=0o700)
    original = compose.read_bytes()
    (backup / 'compose.yml').write_bytes(original)
    (backup / 'compose.yml').chmod(0o600)
    before = batch.inspect(REDIS_CONTAINER)
    acl = batch.redis('ACL', 'LIST').stdout
    users = sorted(line.split()[1] for line in acl.splitlines())
    (backup / 'users.acl').write_text(acl)
    (backup / 'users.acl').chmod(0o600)
    old_aclfile = batch.redis('CONFIG', 'GET', 'aclfile').stdout.splitlines()[1:]
    if any(old_aclfile):
        raise RuntimeError('An ACL file already exists; inspect before changing configuration')
    target = b'exec redis-server --appendonly yes --requirepass "$$REDIS_PASSWORD"'
    replacement = target + b' --aclfile /data/socai2-users.acl'
    if original.count(target) != 1:
        raise RuntimeError('Unexpected shared Redis command; no configuration changed')
    # Save every existing user including default, without exposing password hashes.
    batch.run(['docker', 'exec', '-i', REDIS_CONTAINER, 'sh', '-c',
               'umask 077; test ! -e /data/socai2-users.acl && cat > /data/socai2-users.acl && '
               'chown redis:redis /data/socai2-users.acl'], acl)
    key = 'socai2:1b:restart-20261020'
    marker = 'socai2-1b-restart-persistence'
    if batch.redis('EXISTS', key, app=True, database=8).stdout.strip() != '0':
        raise RuntimeError('Restart test key already exists')
    batch.redis(app=True, database=8, content=f'SET {key} {marker} EX 3600\nWAITAOF 1 0 5000\n')
    client_count = len(batch.redis('CLIENT', 'LIST').stdout.splitlines())
    compose.write_bytes(original.replace(target, replacement))
    command = ['docker', 'compose', '--project-directory', str(compose.parent),
               '-f', str(compose)]
    validation = batch.run(command + ['config', '--quiet'], allow_error=True)
    if validation.returncode:
        compose.write_bytes(original)
        raise RuntimeError('Compose validation failed; original restored')
    started = time.monotonic()
    batch.run(command + ['up', '-d', '--no-deps', '--pull', 'never', 'redis'])
    for attempt in range(30):
        result = batch.redis('PING', allow_error=True)
        if result.stdout.strip() == 'PONG':
            break
        time.sleep(1)
    else:
        raise RuntimeError('Redis did not become ready; private Compose backup retained')
    after = batch.inspect(REDIS_CONTAINER)
    identity = batch.redis('ACL', 'WHOAMI', app=True).stdout.strip()
    value = batch.redis('GET', key, app=True, database=8).stdout.strip()
    restored_acl = batch.redis('ACL', 'LIST').stdout
    restored_users = sorted(line.split()[1] for line in restored_acl.splitlines())
    if identity != 'socai2' or value != marker or users != restored_users:
        raise RuntimeError('Restart account/data preservation check failed; evidence retained')
    if sorted(acl.splitlines()) != sorted(restored_acl.splitlines()):
        raise RuntimeError('An existing ACL changed during restart')
    if before['Mounts'] != after['Mounts'] or before['Image'] != after['Image']:
        raise RuntimeError('Redis image or volume changed unexpectedly')
    batch.redis('DEL', key, app=True, database=8)
    result = {
        'service': REDIS_CONTAINER, 'operation': 'compose up --no-deps --pull never redis',
        'configuration_change': 'add --aclfile /data/socai2-users.acl; retain requirepass and AOF',
        'before_container_id': before['Id'], 'after_container_id': after['Id'],
        'before_started_at': before['State']['StartedAt'], 'after_started_at': after['State']['StartedAt'],
        'elapsed_until_ready_seconds': round(time.monotonic()-started, 3),
        'pre_restart_clients_including_probe': client_count,
        'image_id': after['Image'], 'image_and_mounts_unchanged': True,
        'acl_users_before': users, 'acl_users_after': restored_users,
        'all_acl_rules_and_password_hashes_unchanged': True,
        'default_admin_ping': 'PONG', 'project_identity_after_restart': identity,
        'input': {'redis_db': 8, 'key': key, 'value': marker}, 'actual_value_after_restart': value,
        'only_test_key_deleted': batch.redis('EXISTS', key, app=True, database=8).stdout.strip() == '0',
        'compose_before_sha256': hashlib.sha256(original).hexdigest(),
        'compose_after_sha256': hashlib.sha256(compose.read_bytes()).hexdigest(),
        'private_backup': str(backup), 'postgres_restarted': False,
        'limitation': 'Redis restart passed; other application recovery is checked by container state only, not business probes',
    }
    batch.save('redis-restart.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Avoid printing subprocess commands, Redis ACL hashes, or credentials.
        print(json.dumps({'success': False, 'error_type': type(exc).__name__,
                          'action': 'inspect private host21 state before retrying'}))
        sys.exit(1)
