"""This batch only: real Docker mounts, offline CLI and host-side readback.

No business execution callback or service lifecycle operations are used.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(path):
    root = Path(path)
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob('*')) if p.is_file()}


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def verify(config_path):
    cfg = read(config_path)
    out = Path(cfg['output'])
    out.mkdir(exist_ok=False)
    (out/'commands').mkdir()
    (out/'environments').mkdir()
    commands, results = [], {}
    preserved = {name: tree(path) for name, path in cfg['preserve'].items()}
    save(out/'sources-before.json', preserved)

    def call(label, args, expected=0, stdin=None):
        result = subprocess.run(args, input=stdin, capture_output=True, text=True,
                                timeout=cfg['command_timeout_seconds'])
        value = {'command': args, 'input_commands': stdin, 'expected_exit': expected,
                 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        save(out/'commands'/(label+'.json'), value)
        commands.append({'label': label, 'exit_code': result.returncode})
        assert result.returncode == expected, f'{label}: unexpected exit; inspect saved command'
        return result.stdout

    def environment(name, materials, private_config, output):
        roots = [Path(p).resolve() for p in (materials, private_config, output)]
        for a in roots:
            for b in roots:
                assert a == b or not a.is_relative_to(b), 'mount roots must not overlap'
        assert len(set(roots)) == 3
        assert all(p.is_dir() for p in roots)
        env = dict(cfg['environment'])
        env.update(ACCEPTANCE_MATERIALS_DIR=str(roots[0]), ACCEPTANCE_CONFIG_DIR=str(roots[1]),
                   ACCEPTANCE_RESULTS_DIR=str(roots[2]))
        target = out/'environments'/(name+'.env')
        with target.open('x') as stream:
            stream.write(''.join(f'{key}={value}\n' for key, value in env.items()))
        prefix = ['docker', 'compose', '--env-file', str(target), '-f', cfg['compose']]
        resolved = json.loads(call(name+'-config', [*prefix, 'config', '--format', 'json']))
        service = resolved['services']['acceptance']
        assert service['network_mode'] == 'none' and service['read_only']
        assert service['pull_policy'] == 'never' and not service.get('ports')
        mounts = service['volumes']
        assert len(mounts) == 3 and [m.get('read_only', False) for m in mounts] == [True, True, False]
        assert all(m['bind']['create_host_path'] is False for m in mounts)
        assert service['user'] == cfg['environment']['ACCEPTANCE_USER']
        return prefix

    def run(prefix, label, *args, expected=0, stdin=None):
        return call(label, [*prefix, 'run', '--rm', '-T', 'acceptance', *args], expected, stdin)

    def report_readback(folder):
        manifest = read(folder/'manifest.json')
        assert manifest['readback'] == 'passed'
        for item in manifest['files']:
            assert digest(folder/item['path']) == item['sha256']
        return read(folder/'report.json')

    def console_readback(folder, state, reason):
        end = read(folder/'end.json')
        assert end['observed_execution_state'] == state and end['reason'] == reason
        assert end['execution_attempts'] == 0 and not end['permanently_closed']
        assert not end['remote_cancellation_requested'] and not list(folder.glob('*-intent.json'))
        if end['report']:
            report_readback(folder/Path(end['report']).parent)
        return end

    try:
        for name, material in cfg['materials'].items():
            area = out/name
            area.mkdir()
            private_config, conversion, execution = (area/n for n in ('config', 'conversion', 'execution'))
            for path in (private_config, conversion, execution):
                path.mkdir()
            profile = read(cfg['profile_example'])
            profile['profile_id'] = 'docker-'+name
            profile['environment_label'] = '本批仅离线文件处理，未检查业务连接'
            save(private_config/'profile.json', profile)
            selected = read(cfg['execution_example'])
            selected['execution_id'] = 'acceptance-docker-'+name+'-20261117-01'
            save(private_config/'execution.json', selected)
            config_hashes = tree(private_config)
            first = environment(name+'-convert', material['source'], private_config, conversion)
            if name == 'streaming':
                help_text = run(first, 'default-help')
                assert all(command in help_text for command in cfg['commands'])
                assert not list(conversion.iterdir())
            run(first, name+'-convert', 'convert', '--source', '/materials', '--recipe', material['recipe'],
                '--profile', '/run/acceptance-config/profile.json', '--output', '/results/converted')
            converted = conversion/'converted'
            hashes = tree(converted)
            plan = read(converted/'plan.json')
            old = read(Path(material['reference'])/'plan.json')
            for key in ('material_sha256', 'scenario', 'scenario_sha256', 'parts'):
                assert plan[key] == old[key], f'{name}: converted facts or plan differ'
            for relative, expected in plan['material_sha256'].items():
                assert digest(converted/relative) == expected
            assert not any(plan[k] for k in ('business_connections', 'kafka_sends', 'model_calls'))
            second = environment(name+'-execution', converted, private_config, execution)
            run(second, name+'-inspect', 'inspect', '--materials', '/materials', '--profile',
                '/run/acceptance-config/profile.json', '--report', '/results/inspection.json')
            run(second, name+'-prepare', 'prepare', '--materials', '/materials', '--profile',
                '/run/acceptance-config/profile.json', '--execution', '/run/acceptance-config/execution.json',
                '--output', '/results/prepared')
            prepared = execution/'prepared'
            prepared_hashes = tree(prepared)
            session = read(prepared/'session.json')
            assert session['source_directory'] == '/materials' and session['profile'] == profile
            assert session['execution'] == selected and len(session['identities']) == material['records']
            assert not (prepared/'runs').exists()
            run(second, name+'-status', 'status', '--prepared', '/results/prepared', '--report', '/results/status.json')
            status = read(execution/'status.json')
            assert status['state'] == 'ready' and status['next_part'] == 'part1'
            assert not any(status['this_command'].values())
            run(second, name+'-console1', 'session', '--prepared', '/results/prepared', '--output',
                '/results/console1', stdin='view\nquit\n')
            console_readback(execution/'console1', 'ready', 'quit')
            # Each run --rm is a different container; this observes the same persisted execution.
            run(second, name+'-console2', 'session', '--prepared', '/results/prepared', '--output',
                '/results/console2', stdin='')
            console_readback(execution/'console2', 'ready', 'eof')
            run(second, name+'-report', 'report', '--prepared', '/results/prepared', '--output', '/results/report')
            report = report_readback(execution/'report')
            assert report['execution_id'] == selected['execution_id'] and report['state'] == 'ready'
            assert all(value == 0 for value in report['counts'].values())
            assert not report['all_parts_completed'] and not (prepared/'runs').exists()
            if name == 'streaming':
                run(second, 'reject-status-inside-prepared', 'status', '--prepared', '/results/prepared',
                    '--report', '/results/prepared/rejected.json', expected=2)
                run(second, 'reject-report-inside-materials', 'report', '--prepared', '/results/prepared',
                    '--output', '/materials/rejected', expected=2)
                run(second, 'reject-existing-report', 'report', '--prepared', '/results/prepared',
                    '--output', '/results/report', expected=2)
                run(second, 'reject-missing-profile', 'inspect', '--materials', '/materials', '--profile',
                    '/run/acceptance-config/absent.json', '--report', '/results/rejected.json', expected=2)
                assert not (execution/'rejected.json').exists() and not (prepared/'rejected.json').exists()
                name_in_docker = cfg['probe_container']
                probe = '''import errno,json,os
from pathlib import Path
errors={}
for name in ("/materials/.docker-ro-probe", "/run/acceptance-config/.docker-ro-probe"):
    try: Path(name).write_text("unexpected writable mount")
    except OSError as exc: errors[name]=exc.errno
assert len(errors)==2 and all(value in (errno.EROFS,errno.EACCES) for value in errors.values())
assert os.getuid()!=0
Path("/results/nonroot-write.json").write_text(json.dumps({"uid":os.getuid(),"gid":os.getgid(),"readonly_errors":errors}))
print(json.dumps({"uid":os.getuid(),"gid":os.getgid(),"readonly_errors":errors}))'''
                try:
                    call('readonly-probe', [*second, 'run', '--name', name_in_docker, '-T', '--entrypoint',
                                           'python', 'acceptance', '-c', probe])
                    item = json.loads(call('mount-inspect', ['docker', 'inspect', name_in_docker]))[0]
                    safe = {'mounts': item['Mounts'], 'network': item['HostConfig']['NetworkMode'],
                            'root_readonly': item['HostConfig']['ReadonlyRootfs'], 'user': item['Config']['User'],
                            'image_reference': item['Config']['Image'], 'image': item['Image']}
                    assert safe['network'] == 'none' and safe['root_readonly']
                    assert {m['Destination']: m['RW'] for m in safe['mounts']} == {
                        '/materials': False, '/run/acceptance-config': False, '/results': True}
                    save(out/'actual-mounts.json', safe)
                finally:
                    call('remove-own-probe', ['docker', 'rm', name_in_docker])
                assert read(execution/'nonroot-write.json')['uid'] == int(cfg['environment']['ACCEPTANCE_USER'].split(':')[0])
            assert tree(private_config) == config_hashes and tree(converted) == hashes
            assert tree(prepared) == prepared_hashes
            save(area/'preserved.json', {'config': config_hashes, 'converted': hashes, 'prepared': prepared_hashes})
            results[name] = {'status': 'passed', 'prepared_records': len(session['identities']),
                             'execution_id': selected['execution_id'], 'state': status['state'],
                             'runs_created': False, 'connection_files_present': False}
            print(name, 'conversion, preparation, persistent re-open passed', flush=True)

        for name, legacy in cfg['legacy'].items():
            area = out/name
            area.mkdir()
            private_config, output = area/'config', area/'output'
            private_config.mkdir()
            output.mkdir()
            prefix = environment(name, legacy['prepared'], private_config, output)
            code, state = legacy['exit_code'], legacy['state']
            run(prefix, name+'-status', 'status', '--prepared', '/materials', '--report',
                '/results/status.json', expected=code)
            run(prefix, name+'-report', 'report', '--prepared', '/materials', '--output',
                '/results/report', expected=code)
            report = report_readback(output/'report')
            previous = read(Path(legacy['reference'])/'report.json')
            assert {k: v for k, v in report.items() if k != 'observed_at'} == {
                k: v for k, v in previous.items() if k != 'observed_at'}
            for path in (output/'report/models').rglob('*'):
                if path.is_file():
                    assert digest(path) == digest(Path(legacy['reference'])/path.relative_to(output/'report'))
            for action, part in (('run', 'part1'), ('append', 'part2')):
                run(prefix, name+'-'+action+'-refused', action, '--prepared', '/materials', '--part', part, expected=2)
            run(prefix, name+'-console1', 'session', '--prepared', '/materials', '--output',
                '/results/console1', expected=code, stdin='run part1\nappend part2\nview\nfinish\n')
            console_readback(output/'console1', state, 'finish')
            run(prefix, name+'-console2', 'session', '--prepared', '/materials', '--output',
                '/results/console2', expected=code, stdin='')
            console_readback(output/'console2', state, 'eof')
            assert not list(private_config.iterdir())
            results[name] = {'status': 'passed', 'state': report['state'], 'counts': report['counts'],
                             'request_count': report['models']['request_count'], 'usage': report['models']['usage'],
                             'quality_issues': report['quality']['issue_count'],
                             'quality_by_stage': report['quality']['issues_by_stage'],
                             'step_issues': len(report['step_issues']), 'exact_report_equality_except_observed_at': True}
            print(name, 'original reports, refusal gates, persistent re-open passed', flush=True)

        after = {name: tree(path) for name, path in cfg['preserve'].items()}
        assert after == preserved
        save(out/'sources-after.json', after)
        containers = call('own-containers-after', ['docker', 'ps', '-a', '--filter',
                          'label=com.docker.compose.project='+cfg['environment']['ACCEPTANCE_PROJECT'], '--format', '{{.ID}}'])
        assert not containers.strip()
        save(out/'validation.json', {'status': 'passed', 'config_sha256': digest(config_path), 'results': results,
             'commands': commands, 'preserved_files': {k: len(v) for k, v in preserved.items()},
             'new_business_executions': 0, 'new_model_calls': 0, 'new_kafka_sends': 0,
             'network': 'none', 'unverified': ['target services connectivity', 'task4 real flow', '21 native execution']})
    except BaseException as exc:
        save(out/'failed.json', {'status': 'failed', 'exception_type': type(exc).__name__,
                                'message': str(exc), 'commands': commands, 'completed_results': results})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    verify(parser.parse_args().config)
