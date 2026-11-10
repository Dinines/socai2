"""Candidate packaging preserves current code and refuses mutable release identities."""
import json
import tarfile
from pathlib import Path

import prepare_processing_release as release
import pytest
from build_processing_image import verify_release

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def configured(tmp_path):
    profile = tmp_path / "build.toml"
    text = (HERE / "processing-build.example.toml").read_text()
    text = text.replace('../../.local/processing-release', str(tmp_path / "output"))
    text = text.replace('../local-investigation/investigation-policy.toml',
        str(ROOT / "deploy/local-investigation/investigation-policy.toml"))
    profile.write_text(text)
    return profile


def test_candidate_contains_current_tls_readers_policy_and_ingress(tmp_path):
    profile = configured(tmp_path)
    directory = release.build(profile)
    assert release.build(profile) == directory
    manifest = json.loads((directory / "manifest.json").read_text())
    unpacked = tmp_path / "extracted" / manifest["release"]
    unpacked.mkdir(parents=True)
    with tarfile.open(directory / "release.tar.gz") as archive:
        archive.extractall(unpacked, filter="data")
    verify_release(unpacked)
    for name in ("db/database.py", "socai2/runtime_policy.py", "socai2/stage_answer_review.py",
                 "socai2/contracts.schema.json", "api/v1/endpoints/socai2_pages.py", "models/socai2.py"):
        assert (unpacked / "app" / name).read_bytes() == (ROOT / "services/api/app" / name).read_bytes()
    assert (unpacked / "production_ingress.py").read_bytes() == (HERE / "production_ingress.py").read_bytes()
    assert not any(name.startswith("schema/") or "private" in Path(name).parts for name in manifest["files"])
    original = (directory / "release.tar.gz").read_bytes()
    profile.write_text(profile.read_text().replace('build_timeout_seconds = 300', 'build_timeout_seconds = 301'))
    with pytest.raises(FileExistsError):
        release.build(profile)
    assert (directory / "release.tar.gz").read_bytes() == original
    extra = unpacked / "app/socai2/unlisted.py"
    extra.write_text("raise AssertionError('unlisted module')")
    with pytest.raises(ValueError, match="unexpected files"):
        verify_release(unpacked)
    extra.unlink()
    (unpacked / "app/db/database.py").write_text("altered")
    with pytest.raises(ValueError, match="source mismatch"):
        verify_release(unpacked)


def test_optional_incident_profile_is_validated_and_packaged_from_same_source(tmp_path):
    profile = configured(tmp_path)
    profile.write_text(profile.read_text().replace("investigation-policy.toml", "investigation-policy-incident-v1.toml"))
    directory = release.build(profile)
    manifest = json.loads((directory / "manifest.json").read_text())
    with tarfile.open(directory / "release.tar.gz") as archive:
        files = {member.name: archive.extractfile(member).read()
                 for member in archive.getmembers() if member.isfile()}
    for name in ("incident-input-v1.json", "incident_model_boundary.py", "incident_input_text.py",
                 "incident_output_adapter.py", "incident_delivery.py"):
        assert "app/socai2/" + name in manifest["files"]
        assert files["app/socai2/" + name] == (ROOT / "services/api/app/socai2" / name).read_bytes()
    assert files["investigation-policy.toml"] == (ROOT / "deploy/local-investigation/investigation-policy-incident-v1.toml").read_bytes()


def test_combined_alert_incident_profile_contains_both_boundaries(tmp_path):
    profile = configured(tmp_path)
    profile.write_text(profile.read_text().replace('investigation-policy.toml', 'investigation-policy-ai-v1.toml'))
    directory = release.build(profile)
    with tarfile.open(directory / 'release.tar.gz') as archive:
        for name in ('alert-input-v1.json', 'alert_model_boundary.py', 'alert_input_text.py', 'alert_output_adapter.py',
                     'incident-input-v1.json', 'incident_model_boundary.py', 'incident_delivery.py'):
            assert archive.extractfile('app/socai2/' + name).read() == (ROOT / 'services/api/app/socai2' / name).read_bytes()
        assert archive.extractfile('investigation-policy.toml').read() == (ROOT / 'deploy/local-investigation/investigation-policy-ai-v1.toml').read_bytes()


def test_case_profile_packages_frozen_query_and_input_output_modules(tmp_path):
    profile = configured(tmp_path)
    profile.write_text(profile.read_text().replace('investigation-policy.toml', 'investigation-policy-case-v1.toml'))
    directory = release.build(profile)
    with tarfile.open(directory / 'release.tar.gz') as archive:
        for name in ('case-input-v1.json', 'case_model_boundary.py', 'case_input_text.py',
                     'case_input_hierarchy.py', 'case_query_snapshot.py', 'case_output_adapter.py',
                     'case_followup_input.py', 'case_followup_loader.py', 'case_followup_output.py',
                     'baseline_context.schema.json', 'incident-input-v1.json', 'alert-input-v1.json'):
            assert archive.extractfile('app/socai2/' + name).read() == (ROOT / 'services/api/app/socai2' / name).read_bytes()
        assert archive.extractfile('investigation-policy.toml').read() == (ROOT / 'deploy/local-investigation/investigation-policy-case-v1.toml').read_bytes()


@pytest.mark.parametrize("before,after", [
    ('platform = "linux/amd64"', 'platform = "unknown"'),
    ('build_timeout_seconds = 300', 'build_timeout_seconds = -1'),
    ('buildkit = false', 'buildkit = true'),
    ('sha256:c78b01862896f966cf8f6901ad21baa941f35ebe6ec83a5894d17c97575a5795', 'mutable-tag'),
])
def test_invalid_build_identity_refused_before_freezing(tmp_path, before, after):
    profile = configured(tmp_path)
    profile.write_text(profile.read_text().replace(before, after))
    with pytest.raises(ValueError):
        release.build(profile)
    assert not (tmp_path / "output").exists()
