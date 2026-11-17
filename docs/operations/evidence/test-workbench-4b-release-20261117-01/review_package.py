"""Independent local package/configuration review; never contacts or deploys 21."""
import hashlib
import io
import json
import sys
import tarfile
import tomllib
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OWNER = ROOT / "docs/operations/evidence/workbench-4b-release-20261117-01"
PACK = ROOT / ".local/investigation-test-release/test-service-0.6.1-20261117-4b01"
BASE = ROOT / "docs/operations/evidence/acceptance-fullflow-21-20261117-01"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value):
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items() if k not in {"observed_at", "workbench", "viewer_url"}}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


manifest = read(PACK / "package-manifest.json")
receipt = read(OWNER / "package-build.json")
plan = read(OUT / "release-check-plan-01.json")
release_path = ROOT / "deploy/investigation-test/releases/workbench-4b-20261117-01/release.json"
report_config_path = ROOT / "deploy/investigation-test/releases/workbench-4b-20261117-01/report.json"
release, config = read(release_path), read(report_config_path)
files = set(manifest["files"]) | {"package-manifest.json"}
checks = []

assert {str(p.relative_to(PACK)) for p in PACK.rglob("*") if p.is_file()} == files
assert all(sha(PACK / f) == v["sha256"] and (PACK / f).stat().st_size == v["size"] for f, v in manifest["files"].items())
assert sha(PACK / "package-manifest.json") == receipt["manifest_sha256"]
assert sha(Path(receipt["archive"])) == receipt["archive_sha256"]
with tarfile.open(receipt["archive"]) as archive:
    members = archive.getmembers()
    assert len(members) == len(files)
    for member in members:
        assert member.isfile() and member.name.startswith(manifest["release"] + "/")
        name = member.name[len(manifest["release"]) + 1:]
        assert name in files
        assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == sha(PACK / name)
checks.append({"id": "PKG1", "status": "passed", "detail": "119文件及manifest与压缩包逐项字节一致", "archive_sha256": receipt["archive_sha256"], "manifest_sha256": receipt["manifest_sha256"]})

assert all(sha(PACK / f) == h == sha(ROOT / f) for f, h in plan["reviewed_source_sha256"].items())
checks.append({"id": "PKG2", "status": "passed", "reviewed_files": 15,
               "current_source_differences": [f for f, h in manifest["source_files"].items() if sha(ROOT / f) != h],
               "detail": "15份已审4b文件精确保持，完整包来源冻结在manifest"})
assert manifest["service_version"] == manifest["viewer_version"] == release["version"] == "0.6.1"
assert tomllib.loads((PACK / "services/investigation_test/pyproject.toml").read_text())["project"]["version"] == "0.6.1"
assert '__version__ = "0.6.1"' in (PACK / "services/investigation_test/__init__.py").read_text()
image = read(PACK / "deploy/investigation-test/acceptance-image.json")
assert manifest["image"]["tag"] == release["viewer_image"] and image["tag"] == release["acceptance_image"]
assert manifest["image"]["platform"] == image["platform"] == release["platform"] == "linux/amd64"
assert read(PACK / "deploy/investigation-test/viewer.example.json")["test_source_prefixes"] == ["lyc"]
assert read(PACK / "tools/testdata/material-source.json")["connector_type"] == "lyc-telemetry-01"
assert release["test_source_prefixes"] == ["lyc", "telemetry-channel-02"]
assert config["workbench_environment_label"] == release["environment_label"] == "acceptance-release-20261117-01"
assert config["workbench_url"] == release["local_entry"] + "/viewer/"
checks.append({"id": "PKG3", "status": "passed", "detail": "版本/tag/profile一致；新默认lyc，发布显式兼容旧来源；报告指向4177"})

preflight = json.loads(read(OWNER / "preflight-02.json")["stdout"])
assert preflight["old"]["id"] == release["old_id"] and preflight["old"]["running"]
assert preflight["old"]["ports"]["14178/tcp"] == [{"HostIp": release["bind_host"], "HostPort": str(release["bind_port"])}]
assert len(preflight["ledger_sha256"]) == 8 and set(preflight["core"]) == set(release["core_containers"])
assert all(c["running"] for c in preflight["core"].values())
checks.append({"id": "PKG4", "status": "passed", "detail": "已存切换前回执固定r7、4核心容器和8账本文件；尚不判断发布后保持",
               "core_before": {k: {x: v[x] for x in ["id", "image", "started_at", "restart_count"]} for k, v in preflight["core"].items()},
               "ledger_sha256_before": preflight["ledger_sha256"]})
proof = json.loads(read(OWNER / "base-identity-01.json")["stdout"])
base_observed = json.loads(read(OWNER / "base-image-review-01.json")["stdout"])
assert proof["reference"] == image["base_ref"] and proof["expected_platform_blob"]["sha256"] == image["base_id"]
assert proof["platform"] == image["platform"]
base_image = next(b for b in base_observed["bases"] if b["kind"] == "acceptance")
assert image["base_ref"] in base_image["repo_digests"] and proof["docker_image_id"] == base_image["image_id"]
assert base_image["architecture"] == "amd64" and base_image["os"] == "linux"
checks.append({"id": "PKG5", "status": "passed_evidence_review", "base_ref": image["base_ref"],
               "docker_image_id": proof["docker_image_id"], "platform_manifest_sha256": image["base_id"],
               "detail": "核固定ref、观测RepoDigests、平台manifest身份及prove-base.py对原始tar字节的哈希过程；索引ID与平台ID保持区别",
               "limit": "平台blob仅存解析后的JSON，未在本机获得原始字节复算；不把重新序列化JSON的哈希当原件哈希"})

originals = read(BASE / "results-copy.json")["sha256"]
assert all(sha(BASE / f) == h for f, h in originals.items())
sys.path.insert(0, str(PACK / "tools/testdata"))
import acceptance
import acceptance_report_links

assert Path(acceptance.__file__).resolve().is_relative_to(PACK)
assert Path(acceptance_report_links.__file__).resolve().is_relative_to(PACK)
prepared = BASE / "results/prepared"
secret_paths = set(read(prepared / "session.json")["profile"]["connection_files"].values())
attempts = {"network": 0, "connection_config": 0}
original_open = Path.open


def block_socket(*args, **kwargs):
    attempts["network"] += 1
    raise AssertionError("offline report attempted network")


def guarded_open(path, *args, **kwargs):
    if str(path) in secret_paths:
        attempts["connection_config"] += 1
        raise AssertionError("offline report opened connection config")
    return original_open(path, *args, **kwargs)


output = OUT / "package-report-01"
with patch("socket.socket", side_effect=block_socket), patch("socket.create_connection", side_effect=block_socket), patch.object(Path, "open", guarded_open), redirect_stdout(io.StringIO()):
    assert acceptance.main(["report", "--prepared", str(prepared), "--output", str(output),
                            "--report-config", str(PACK / report_config_path.relative_to(ROOT))]) == 0
new, old = read(output / "report.json"), read(BASE / "results/report-01/report.json")
assert normalize(new) == normalize(old)
links = []
for subject in new["subjects"]:
    for run in subject["rounds"]:
        parsed = urlsplit(run["viewer_url"])
        assert parsed.scheme + "://" + parsed.netloc + parsed.path == config["workbench_url"]
        assert parse_qs(parsed.query) == {"subject_type": [subject["kind"]], "subject_id": [subject["id"]], "run_id": [run["run_id"]], "environment": [config["workbench_environment_label"]]}
        links.append(run["viewer_url"])
assert len(links) == len(set(links)) == 6
exports = [p for p in (output / "models").rglob("*") if p.is_file()]
assert len(exports) == 24 and all(p.read_bytes() == (BASE / "results/report-01" / p.relative_to(output)).read_bytes() for p in exports)
assert all(sha(output / f["path"]) == f["sha256"] for f in read(output / "manifest.json")["files"])
assert all(sha(BASE / f) == h for f, h in originals.items()) and not any(attempts.values())
assert {str(p.relative_to(PACK)) for p in PACK.rglob("*") if p.is_file()} == files
assert all(sha(PACK / f) == v["sha256"] for f, v in manifest["files"].items())
checks.append({"id": "PKG6", "status": "passed", "detail": "从发布包导入CLI离线生成6个准确4177链接，24导出/1036母本/包字节保持",
               "import_origin": str(Path(acceptance.__file__).relative_to(ROOT)), "guard_attempts": attempts, "report": "package-report-01/report.json"})
refs = [OWNER / n for n in ["package-build.json", "preflight-01.json", "preflight-02.json", "base-image-review-01.json", "base-identity-01.json", "prove-base.py", "build-images-01.json", "package-check-01.log"]]
refs += [PACK / "package-manifest.json", release_path, report_config_path, Path(__file__)]
result = {"status": "passed_package_and_configuration_only", "observed_at": datetime.now(timezone.utc).isoformat(), "checks": checks, "open_findings": [],
          "evidence": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in refs],
          "preserved_failures": ["preflight-01旧Swagger名称配置错误，02按实际部署修正；不表示服务曾修改", "build-images-01直接比较索引/平台ID失败，base-identity-01保留分层身份依据", "本独立初始内联驱动误假定解析后JSON重序列化哈希等于原始OCI字节，断言失败；此假设已移除，未执行产品报告阶段或产生验收结论"],
          "reviewer_actions": {"product_changes": 0, "remote_reads": 0, "deployments": 0, "business_writes": 0, "ingress": 0, "model_calls": 0},
          "not_verified": ["新构建镜像实际运行与模块/配置", "21 r8切换及实际4177", "发布后核心/账本/目标记录保持", "发布后真实报告/浏览器轮次与来源", "新lyc投放、模型质量、D5/D6和整个change"]}
target = OUT / "independent-package-review-01.json"
with target.open("x") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps({"path": str(target), "sha256": sha(target), "status": result["status"], "checks": len(checks)}, ensure_ascii=False))
