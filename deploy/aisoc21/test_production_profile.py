"""Profile -> actual command/env; no Docker, network, database or model calls."""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import production_processing as launcher
import pytest
from production_profile import ProfileError, load, runtime_values

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def test_profile_option_cannot_be_overridden_by_abbreviation(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["processor", "--profile", "/frozen/profile.toml", "--prof=/other", "check"])
    monkeypatch.setattr(launcher, "select_profile", lambda _: pytest.fail("must fail before selecting a profile"))
    with pytest.raises(SystemExit) as stopped:
        launcher.main()
    assert stopped.value.code == 2


def profile_file(tmp_path):
    policy = tmp_path / "policy.toml"
    policy.write_bytes((ROOT / "deploy/local-investigation/investigation-policy.toml").read_bytes())
    transport = tmp_path / "transport.env"
    transport.write_text("OPENAI_API_KEY=synthetic-unit-credential\nDATABASE_URL=not-used\nOPENAI_BASE_URL=not-used\n")
    ca = tmp_path / "ca.crt"
    ca.write_text("synthetic certificate fixture")
    private = tmp_path / "private"
    private.mkdir()
    source = (HERE / "production-profile.example.toml").read_text()
    replacements = {"sha256:REPLACE_WITH_VERIFIED_IMAGE_DIGEST": "sha256:" + "b" * 64,
        "/opt/sting-aisoc-socai2/config/investigation-policy.toml": str(policy),
        "/opt/sting-aisoc-socai2/private/processing-handoff/runtime.env": str(transport),
        "/opt/sting-aisoc-socai2/private/processing-production": str(private),
        "/opt/sting-aisoc-socai2/certificates/socai2-ca.crt": str(ca),
        'database = "aisoc"': 'database = "synthetic_configured"',
        'host = "192.168.1.21"': 'host = "configured.example"',
        'port = 5432': 'port = 25439', 'port = 9000': 'port = 29009',
        'processor_role = "socai2_prod_processor"': 'processor_role = "synthetic_processor"',
        'ingress_role = "socai2_prod_ingress"': 'ingress_role = "synthetic_ingress"',
        'network = "socai2_default"': 'network = "configured_network"',
        'memory = "2g"': 'memory = "3g"', 'pids_limit = 128': 'pids_limit = 144'}
    for original, replacement in replacements.items():
        assert original in source
        source = source.replace(original, replacement)
    path = tmp_path / "production.toml"
    path.write_text(source)
    return path


def test_required_profile_has_no_implicit_model_database_or_policy(tmp_path):
    path = profile_file(tmp_path)
    profile = load(path)
    env = runtime_values(profile)
    assert env["CLICKHOUSE_HOST"] == "configured.example" and env["CLICKHOUSE_PORT"] == "29009"
    assert env["SOCAI2_SERVICE_DATABASE_NAME"] == "synthetic_configured"
    assert env["SOCAI2_PROCESSING_DB_ROLE"] == "synthetic_processor"
    assert env["SOCAI2_PROCESSING_DB_PORT"] == "25439"
    assert env["AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS"] == str(profile.policy["model"]["max_prepared_bytes"])
    assert env["SOCAI2_PROCESSING_PROFILE_SHA256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "OPENAI_API_KEY" not in env and "DATABASE_URL" not in env


def test_knowledge_profile_is_explicit_and_mount_matches_runtime(tmp_path):
    path = profile_file(tmp_path)
    data = path.read_text()
    data = data.replace('[runtime]', '[runtime]\nSOCAI2_KNOWLEDGE_PROFILE = "/run/knowledge/profile.json"', 1)
    data += '\n[knowledge]\nprofile_file = "/frozen/knowledge.json"\nprofile_mount = "/run/knowledge/profile.json"\n'
    data += 'key_file = "/private/qdrant-key"\nkey_mount = "/run/knowledge/qdrant-key"\n'
    path.write_text(data)
    selected = load(path)
    assert selected.knowledge.profile_file == "/frozen/knowledge.json"
    assert runtime_values(selected)["SOCAI2_KNOWLEDGE_PROFILE"] == selected.knowledge.profile_mount
    path.write_text(data.replace('profile_mount = "/run/knowledge/profile.json"', 'profile_mount = "/wrong/profile.json"'))
    with pytest.raises(ProfileError, match="processing_knowledge_profile_mismatch"):
        load(path)


@pytest.mark.parametrize("before,after", [
    ('port = 25439', 'port = true'), ('tls_mode = "verify-full"', 'tls_mode = "disable"'),
    ('alias = "aisoc-investigation"', 'alias = "wrong-model"'),
    ('["litellm", "192.168.1.43"]', '["litellm"]'),
    ('processor_role = "synthetic_processor"', 'processor_role = "invalid;role"'),
    ('DATABASE_POOL_SIZE = "2"', 'DATABASE_POOL_SIZE = "2"\nUNDECLARED_SETTING = "value"'),
])
def test_missing_or_inconsistent_profile_fails_before_actions(tmp_path, before, after):
    path = profile_file(tmp_path)
    text = path.read_text()
    assert before in text
    path.write_text(text.replace(before, after))
    with pytest.raises(ProfileError):
        load(path)


def test_installer_and_job_use_same_profile_and_readonly_policy_mount(tmp_path, monkeypatch, capsys):
    profile = launcher.select_profile(profile_file(tmp_path))
    monkeypatch.setattr(launcher, "secure_file", lambda _: None)
    monkeypatch.setattr(launcher, "pg_credential", lambda *_: "f" * 64)
    monkeypatch.setattr(launcher, "lake_credential", lambda: "e" * 64)
    monkeypatch.setattr(launcher, "secret", lambda _: "d" * 64)
    launcher.configure()
    env = dict(line.split("=", 1) for line in (launcher.PRIVATE / "runtime.env").read_text().splitlines())
    dsn = urlsplit(env["DATABASE_URL"])
    assert (dsn.hostname, dsn.port, dsn.path, dsn.username) == ("configured.example", 25439, "/synthetic_configured", "synthetic_processor")
    assert parse_qs(dsn.query) == {"sslmode": ["verify-full"]}
    assert env["OPENAI_BASE_URL"] == profile.model.base_url and env["OPENAI_API_KEY"] == "synthetic-unit-credential"
    commands = []
    def run(args, **kwargs):
        commands.append((args, kwargs))
        return SimpleNamespace(stdout='{"check":"synthetic-only"}\n', returncode=0)
    monkeypatch.setattr(launcher.subprocess, "run", run)
    assert launcher.run(uuid4(), None, ["check"]) == 0
    args, kwargs = commands[0]
    assert args[args.index("--network") + 1] == "configured_network"
    assert "--memory=3g" in args and "--pids-limit=144" in args and profile.image.id in args
    assert f"type=bind,src={profile.paths.policy_file},dst={profile.paths.policy_mount},readonly" in args
    assert kwargs["input"] == "" and "synthetic-unit-credential" not in capsys.readouterr().out
    # A changed policy cannot run against an old generated env file.
    Path(profile.paths.policy_file).write_text(Path(profile.paths.policy_file).read_text() + "\n# changed\n")
    launcher.select_profile(profile.path)
    with pytest.raises(launcher.SetupError, match="reinstall_required"):
        launcher.run(uuid4(), None, ["check"])
    assert len(commands) == 1


def test_configured_image_digest_checked_before_execution(tmp_path, monkeypatch):
    profile = launcher.select_profile(profile_file(tmp_path))
    calls = []
    def call(args, **kwargs):
        calls.append(args)
        return json.dumps([{"Id": profile.image.id, "Config": {"User": profile.image.user}}])
    monkeypatch.setattr(launcher, "call", call)
    launcher.image_check()
    assert calls == [["docker", "image", "inspect", profile.image.tag]]
    monkeypatch.setattr(launcher, "call", lambda *_a, **_k: json.dumps([{"Id": "sha256:" + "a" * 64, "Config": {"User": profile.image.user}}]))
    with pytest.raises(launcher.SetupError, match="configured_image_changed"):
        launcher.image_check()


def test_ingress_uses_configured_identity_and_rejects_mismatched_host(tmp_path, monkeypatch):
    import production_ingress as ingress
    profile = load(profile_file(tmp_path))
    for key, value in runtime_values(profile).items():
        monkeypatch.setenv(key, value)
    dsn = "postgresql+asyncpg://synthetic_ingress:synthetic@configured.example:25439/synthetic_configured?sslmode=verify-full"
    monkeypatch.setenv("DATABASE_URL", dsn)
    assert ingress.database_url() == dsn.replace("postgresql+asyncpg:", "postgresql:")
    monkeypatch.setenv("DATABASE_URL", dsn.replace("configured.example", "wrong.example"))
    with pytest.raises(ingress.IngressError, match="invalid_ingress_database"):
        ingress.database_url()


def test_job_probe_requires_profile_before_transport(monkeypatch):
    import importlib.util
    path = ROOT / "docs/operations/production_case_probe.py"
    spec = importlib.util.spec_from_file_location("synthetic_probe_config_test", path)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    with pytest.raises(ValueError, match="processing_profile_file_required"):
        probe.remote({"transport": {}}, {"mode": "job"})


def test_invalid_policy_rejected_before_any_install_action(tmp_path, monkeypatch):
    import os
    import sys
    path = profile_file(tmp_path)
    policy = tmp_path / "policy.toml"
    policy.write_text(policy.read_text().replace("single_model_timeout_seconds = 300", "single_model_timeout_seconds = -1"))
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid policy reached a Docker or credential action")
    monkeypatch.setattr(launcher, "image_check", forbidden)
    monkeypatch.setattr(launcher, "configure", forbidden)
    monkeypatch.setattr(sys, "argv", ["production_processing.py", "--profile", str(path), "install"])
    prior_umask = os.umask(0o077)
    try:
        with pytest.raises(ProfileError, match="investigation_policy_time_invalid"):
            launcher.main()
    finally:
        os.umask(prior_umask)
