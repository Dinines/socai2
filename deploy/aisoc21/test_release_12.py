"""Deployment checks reject lost settings and changed prepared payloads."""
import importlib.util
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import tomllib
import yaml

spec = importlib.util.spec_from_file_location("release_12", Path(__file__).with_name("release_12.py"))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def test_gateway_timeout_is_in_release_and_new_install_configuration():
    root = Path(__file__).resolve().parents[2]
    cfg = json.loads((root / "deploy/aisoc21/release-v1.2.json").read_text())
    gateway = cfg["projects"]["gateway"]["services"]["litellm"]
    compose = yaml.safe_load((root / "deploy/aisoc21/compose.gateway.yml").read_text())
    policy = tomllib.loads((root / "deploy/local-investigation/investigation-policy.toml").read_text())
    expected = str(policy["single_model_timeout_seconds"])
    assert gateway["override"]["environment"]["AISOC_LITELLM_REQUEST_TIMEOUT"] == expected
    assert compose["services"]["litellm"]["environment"]["AISOC_LITELLM_REQUEST_TIMEOUT"] == expected
    assert "deploy/aisoc21/litellm.config.yaml" in cfg["files"]


def test_processing_policy_mount_and_runtime_validation_are_explicit():
    root = Path(__file__).resolve().parents[2]
    cfg = json.loads((root / "deploy/aisoc21/release-v1.2.json").read_text())
    profile = tomllib.loads((root / "deploy/aisoc21/production-v1.2.toml").read_text())
    api = cfg["projects"]["main"]["services"]["api"]
    assert profile["paths"]["policy_file"] + ":" + profile["paths"]["policy_mount"] + ":ro" in api["override"]["volumes"]
    assert api['use_processing_environment'] is True
    assert set(cfg['processing_policy_check']['profiles']) == {'alert_io', 'incident_io', 'case_io'}


def test_processing_environment_supersedes_rendered_old_environment(tmp_path):
    env = tmp_path / 'processing.env'
    env.write_text('POLICY_SHA=new\nMODEL_KEY=private-test-value\n')
    cfg = {'processing': {'api_model_env': str(env), 'api_model_keys': ['POLICY_SHA', 'MODEL_KEY']}}
    change = {'use_processing_environment': True, 'allowed_env_changes': ['POLICY_SHA', 'MODEL_KEY'],
              'override': {'environment': {'MODE': 'production'}}}
    overlay = r.processing_environment_overlay(change, cfg)
    assert {'POLICY_SHA': 'old', **overlay['environment']} == {
        'POLICY_SHA': 'new', 'MODEL_KEY': 'private-test-value', 'MODE': 'production'}
    r.write(tmp_path / 'overlay.json', overlay, private=True)
    assert (tmp_path / 'overlay.json').stat().st_mode & 0o777 == 0o600
    change['override']['environment']['POLICY_SHA'] = 'old'
    with pytest.raises(ValueError, match='override_conflict'):
        r.processing_environment_overlay(change, cfg)


def test_api_reader_release_check_is_readonly_and_fails_closed(tmp_path):
    cfg = {'api_reader_check': {'profile': '/explicit/profile.toml'}}
    with patch.object(r, 'command', return_value='verified_socai2_v1_2_reader') as command:
        assert r.verify_api_reader(tmp_path, cfg)['writes'] == 0
        assert command.call_args.args[0][-3:] == ['verify', '--profile', '/explicit/profile.toml']
    with patch.object(r, 'command', return_value=''), pytest.raises(ValueError, match='api_reader_permissions_not_ready'):
        r.verify_api_reader(tmp_path, cfg)


def test_case_database_mapping_does_not_replace_general_api_database():
    processing = {"api_model_keys": ["OPENAI_MODEL", "SOCAI2_CASE_DATABASE_URL"],
        "api_environment_sources": {"SOCAI2_CASE_DATABASE_URL": "DATABASE_URL"}}
    values = {"OPENAI_MODEL": "model", "DATABASE_URL": "private-processor-dsn", "UNSELECTED_SECRET": "omit"}
    selected = r.select_api_environment(values, processing)
    assert selected == {"OPENAI_MODEL": "model", "SOCAI2_CASE_DATABASE_URL": "private-processor-dsn"}
    assert {"DATABASE_URL": "original-reader-dsn", **selected}["DATABASE_URL"] == "original-reader-dsn"
    with pytest.raises(ValueError, match="api_environment_source_invalid"):
        r.select_api_environment({}, processing)


def test_case_http_release_check_requires_actual_writer_identity():
    cfg = {"case_http_check": {"container": "api", "database": "selected", "role": "writer"}}
    with patch.object(r, "command", return_value=json.dumps({"enabled": True, "database": "selected", "role": "writer"})):
        assert r.verify_case_http(cfg) == {"enabled": True, "database": "selected", "role": "writer", "writes": 0}
    with patch.object(r, "command", return_value=json.dumps({"enabled": True, "database": "selected", "role": "reader"})), \
            pytest.raises(ValueError, match="case_http_database_identity_mismatch"):
        r.verify_case_http(cfg)


def test_runtime_policy_check_rejects_old_boundary_even_with_healthy_container(tmp_path):
    policy = tmp_path / 'policy.toml'
    policy.write_text('candidate')
    profile = tmp_path / 'profile.toml'
    profile.write_text('[paths]\npolicy_file="' + str(policy) + '"\npolicy_mount="/policy"\n')
    cfg = {'processing': {'profile': str(profile)},
           'processing_policy_check': {'container': 'api', 'profiles': {'alert_io': 'a', 'incident_io': 'i', 'case_io': 'c'}, 'read_flags': {'read': True}}}
    result = {'path': '/policy', 'sha256': r.digest(policy.read_bytes()),
              'configured_sha256': r.digest(policy.read_bytes()), 'profiles': {'alert_io': None, 'incident_io': None}, 'read_flags': {'read': True}}
    with patch.object(r, 'command', return_value=json.dumps(result)), \
            pytest.raises(ValueError, match='runtime_processing_policy_mismatch'):
        r.verify_processing_policy(cfg)
    result['profiles'] = cfg['processing_policy_check']['profiles']
    with patch.object(r, 'command', return_value=json.dumps(result)):
        assert r.verify_processing_policy(cfg) == result
    result['profiles'] = {**result['profiles'], 'case_io': None}
    with patch.object(r, 'command', return_value=json.dumps(result)) as command, \
            pytest.raises(ValueError, match='runtime_processing_policy_mismatch'):
        r.verify_processing_policy(cfg)
    assert json.loads(command.call_args.args[0][-1]) == ['alert_io', 'incident_io', 'case_io']
    result['profiles'] = cfg['processing_policy_check']['profiles']
    result['read_flags']['read'] = False
    with patch.object(r, 'command', return_value=json.dumps(result)), \
            pytest.raises(ValueError, match='runtime_processing_policy_mismatch'):
        r.verify_processing_policy(cfg)
    del cfg['processing_policy_check']['read_flags']
    with patch.object(r, 'command', return_value=json.dumps(result)):
        assert r.verify_processing_policy(cfg) == result


def fixture():
    image = {"Config": {"Env": ["BASE=kept"], "Cmd": ["serve"],
                        "User": "10001:10001", "WorkingDir": "/app"}}
    service = {"image": "sha256:old", "command": None, "environment": {"MODE": "production"}, "read_only": True,
               "cap_drop": ["ALL"], "security_opt": ["no-new-privileges:true"], "mem_limit": 1024,
               "restart": "unless-stopped", "networks": {"default": None},
               "volumes": [{"type": "bind", "source": "/data", "target": "/data", "read_only": True}],
               "ports": [{"target": 8000, "published": "18000", "host_ip": "127.0.0.1", "protocol": "tcp"}]}
    current = {"Id": "container-before", "Image": "sha256:old", "Config": {**image["Config"], "Env": ["BASE=kept", "MODE=production"]},
               "Mounts": [{"Type": "bind", "Source": "/data", "Destination": "/data", "RW": False}],
               "NetworkSettings": {"Networks": {"socai2_default": {}}},
               "HostConfig": {"PortBindings": {"8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "18000"}]},
                   "ReadonlyRootfs": True, "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges:true"],
                   "Memory": 1024, "RestartPolicy": {"Name": "unless-stopped"}}}
    return image, {"services": {"api": service}, "networks": {"default": {"name": "socai2_default"}}}, current


@pytest.mark.parametrize("change", ["none", "environment", "port", "mount", "command", "network"])
def test_runtime_definition_matches_or_rejects_changes(change):
    image, rendered, current = fixture()
    if change == "environment":
        current["Config"]["Env"].append("MISSING_FROM_COMPOSE=must_preserve")
    elif change == "port":
        current["HostConfig"]["PortBindings"]["8000/tcp"][0]["HostIp"] = "0.0.0.0"
    elif change == "mount":
        current["Mounts"][0]["RW"] = True
    elif change == "command":
        current["Config"]["Cmd"] = ["different"]
    elif change == "network":
        current["NetworkSettings"]["Networks"] = {"other": {}}
    with patch.object(r, "command", return_value=json.dumps([image])):
        if change == "none":
            r.runtime_matches({}, rendered, "api", current)
        else:
            with pytest.raises(ValueError, match="runtime_"):
                r.runtime_matches({}, rendered, "api", current)


def test_rollout_rejects_modified_prepared_compose(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    target = state / "main-after.json"
    target.write_text("changed payload")
    r.write(state / "prepared.json", {"manifest_sha256": "release", "hashes": {str(target): "oldhash"}})
    with patch.object(r, "verify_files", return_value=({"state_dir": str(state)}, {}, "release")), \
            patch.object(r, "command") as command:
        with pytest.raises(ValueError, match="prepared_release_drift"):
            r.rollout(tmp_path, "main", "api")
        command.assert_not_called()


@pytest.mark.parametrize("args", [["--profile", "/other"], ["--profile=/other"],
    ["--profile", "/right", "--profile", "/other"], []])
def test_current_entry_binds_profile_once(tmp_path, monkeypatch, args):
    stub = SimpleNamespace(main=lambda: list(sys.argv[1:]), SetupError=ValueError, ProfileError=ValueError)
    monkeypatch.setitem(sys.modules, "production_processing", stub)
    loaded = runpy.run_path(str(Path(__file__).with_name("production_entry.py")))
    entry = loaded["entry"]
    entry.__globals__["__file__"] = str(tmp_path / "deploy/aisoc21/production_entry.py")
    (tmp_path / "release.json").write_text(json.dumps({"processing": {"profile": "/frozen/profile.toml"}}))
    monkeypatch.setattr(sys, "argv", ["entry", *args, "check"])
    if args:
        with pytest.raises(ValueError, match="cannot_be_overridden"):
            entry()
    else:
        assert entry() == ["--profile", "/frozen/profile.toml", "check"]


def test_rollout_rechecks_running_configuration_before_mutation(tmp_path):
    image, rendered, current = fixture()
    current["Config"]["Env"].append("DRIFT=changed_after_prepare")
    project = {"services": {"api": {"container": "api"}}}
    cfg = {"state_dir": str(tmp_path), "projects": {"main": project}}
    r.write(tmp_path / "prepared.json", {"manifest_sha256": "release", "hashes": {}})
    r.write(tmp_path / "targets.json", {"api": {"before_id": "container-before", "before_image": "sha256:old", "target_image": "sha256:new"}})
    r.write(tmp_path / "main-before.json", rendered)
    with patch.object(r, "verify_files", return_value=(cfg, {}, "release")), \
            patch.object(r, "inspect", return_value=current), \
            patch.object(r, "command", return_value=json.dumps([image])) as command:
        with pytest.raises(ValueError, match="runtime_environment_drift"):
            r.rollout(tmp_path, "main", "api")
        assert all(call.args[0][:3] == ["docker", "image", "inspect"] for call in command.call_args_list)


def test_configuration_only_rollout_can_verify_already_recreated_container(tmp_path):
    image, rendered, current = fixture()
    current["Id"] = "container-after"
    rendered["services"]["api"]["environment"]["MODE"] = "updated"
    current["Config"]["Env"] = ["BASE=kept", "MODE=updated"]
    project = {"name": "test", "directory": str(tmp_path), "services": {"api": {"container": "api"}}}
    cfg = {"state_dir": str(tmp_path), "deploy_timeout_seconds": 10, "projects": {"main": project}}
    r.write(tmp_path / "prepared.json", {"manifest_sha256": "release", "hashes": {}})
    r.write(tmp_path / "targets.json", {"api": {"before_id": "container-before",
        "before_image": "sha256:old", "target_image": "sha256:old"}})
    r.write(tmp_path / "main-after.json", rendered)
    with patch.object(r, "verify_files", return_value=(cfg, {}, "release")), \
            patch.object(r, "inspect", return_value=current), \
            patch.object(r, "command", return_value=json.dumps([image])) as command:
        assert r.rollout(tmp_path, "main", "api")["target_image"] == "sha256:old"
        assert any(call.args[0][-1] == "api" for call in command.call_args_list)
