"""Read frozen local packages only; never start a service or model request."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[4]
BATCH = Path(__file__).resolve().parent
FREEZE = BATCH / "source-freeze-01.json"
PROFILE = ROOT / "deploy/aisoc21/acceptance-release-20261117-01/http-profile.json"
ACCEPTED = ROOT / "docs/operations/evidence/acceptance-append-20261117-02/source-freeze-02.json"
C1_SCOPE = ROOT / "docs/operations/evidence/acceptance-case-continuation-20261117-01/core-fix-scope.json"
R4 = ROOT / "deploy/aisoc21/streaming-release-20261116-04/contract/openapi.json"
R4_PROFILE = ROOT / "deploy/aisoc21/streaming-release-20261116-04/http-profile.json"
OUTPUT = BATCH / "http-package-review-02.json"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


IMPORT_PROBE = r'''
import json, socket, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
attempts = []
def forbidden(*args, **kwargs):
    attempts.append("blocked")
    raise RuntimeError("network_not_allowed_in_package_review")
socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
socket.create_connection = forbidden
sys.path.insert(0, str(root))
from investigation_http.main import app
document = app.openapi()
origins = {}
for name, module in list(sys.modules.items()):
    if name in {"app", "investigation_http"} or name.startswith(("app.", "investigation_http.")):
        value = getattr(module, "__file__", None)
        if value:
            path = Path(value).resolve()
            assert path.is_relative_to(root), (name, str(path))
            origins[name] = str(path.relative_to(root))
assert not attempts
print(json.dumps({"document": document, "module_origins": origins,
                  "network_attempts": len(attempts), "lifespan_started": False}))
'''


def main():
    if OUTPUT.exists():
        raise SystemExit("Review output already exists; do not overwrite an ended review.")
    freeze = read_json(FREEZE)
    profile = read_json(PROFILE)
    http = ROOT / freeze["http"]["directory"]
    processing = ROOT / freeze["processing"]["directory"]
    archive = processing / "release.tar.gz"
    viewer_manifest = ROOT / freeze["viewer_and_acceptance"]["directory"] / "package-manifest.json"
    tracked = [FREEZE, PROFILE, ACCEPTED, C1_SCOPE, R4, R4_PROFILE, viewer_manifest,
               http / "manifest.json", processing / "manifest.json", archive]
    tracked += [ROOT / name for name in freeze["config_files"]]
    before = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in tracked}
    report = {
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "status": "running", "scope": "frozen_local_http_contract_and_shared_runtime_sources",
        "source_freeze": str(FREEZE.relative_to(ROOT)),
        "source_freeze_sha256": before[str(FREEZE.relative_to(ROOT))],
        "review_script_sha256": sha(Path(__file__).read_bytes()),
        "review_driver_initial_failure": "http-package-review-driver-failure-01.json",
        "prior_review": "http-package-review-01.json",
        "prior_review_correction": "HTTP-only package extras include five Markdown files and three unchanged query SQL resources; the initial reviewer assumed all eight were Markdown.",
        "checks": [], "new_http_requests": 0, "new_database_requests": 0,
        "new_model_calls": 0, "service_changes": False, "package_changes": False,
        "limitations": [
            "Package import uses local Python dependencies, not a new Docker runtime.",
            "No 21 TCP, database, model, browser or deployment verification in this review.",
            "Accepted 3c2 source identity does not newly execute or re-accept its business flow.",
            "D5a abnormal PostgreSQL persistence acceptance remains incomplete; D5 is not closed.",
            "4b report deep links and automatic purple-source mapping remain unimplemented.",
        ],
    }

    def check(name, **details):
        report["checks"].append({"name": name, "status": "passed", **details})

    try:
        hm = read_json(http / "manifest.json")
        pm = read_json(processing / "manifest.json")
        assert sha((http / "manifest.json").read_bytes()) == freeze["http"]["manifest_sha256"]
        assert sha((processing / "manifest.json").read_bytes()) == freeze["processing"]["manifest_sha256"]
        assert sha(archive.read_bytes()) == freeze["processing"]["archive_sha256"]
        assert sha(viewer_manifest.read_bytes()) == freeze["viewer_and_acceptance"]["manifest_sha256"]
        for name, digest in freeze["config_files"].items():
            assert sha((ROOT / name).read_bytes()) == digest, name
        assert len(hm["files"]) == freeze["http"]["files"] == 733
        assert len(pm["files"]) == freeze["processing"]["files"] == 742
        check("freeze_manifest_archive_and_configuration_identity", configuration_files=len(freeze["config_files"]))

        http_bytes = {}
        for name, digest in hm["files"].items():
            path = http / name
            assert path.resolve().is_relative_to(http.resolve()) and not path.is_symlink(), name
            http_bytes[name] = path.read_bytes()
            assert sha(http_bytes[name]) == digest, name
        actual = {str(p.relative_to(http)) for p in http.rglob("*") if p.is_file()}
        assert actual == set(hm["files"]) | {"manifest.json"}
        assert read_json(http / "profile.json") == profile
        assert len(profile["patches"]) == len(profile["expected_source_hashes"]) == freeze["http"]["sources"] == 730
        for source, target in profile["patches"].items():
            assert hm["files"][target] == profile["expected_source_hashes"][source], source
        for source, target in profile["complete_packages"].items():
            included = {path for path in hm["files"] if path.startswith(target + "/")}
            mapped = {dest for src, dest in profile["patches"].items() if src.startswith(source + "/")}
            assert included == mapped, target
        check("complete_http_package_manifest_and_source_mapping", files=733, source_files=730,
              generated_files=sorted(set(hm["files"]) - set(profile["patches"].values())))

        processing_bytes = {}
        with tarfile.open(archive) as package:
            members = package.getmembers()
            assert len({m.name for m in members}) == len(members)
            assert all(m.isfile() and not m.name.startswith("/") and ".." not in Path(m.name).parts for m in members)
            assert {m.name for m in members} == set(pm["files"]) | {"manifest.json"}
            for member in members:
                body = package.extractfile(member).read()
                if member.name == "manifest.json":
                    assert body == (processing / "manifest.json").read_bytes()
                    continue
                expected = pm["files"][member.name]
                assert sha(body) == expected["sha256"] and len(body) == expected["bytes"], member.name
                processing_bytes[member.name] = body
        check("processing_archive_manifest_and_actual_payload", files=len(processing_bytes), extraction_performed=False)

        core = sorted(name for name in processing_bytes if name.startswith("app/"))
        for name in core:
            assert name in http_bytes and processing_bytes[name] == http_bytes[name], name
        assert len(core) == freeze["shared_core_files"] == 670
        http_only_app = sorted(name for name in http_bytes if name.startswith("app/") and name not in processing_bytes)
        query_resources = {"app/socai2/alert_host_query.sql", "app/socai2/alert_review_query.sql", "app/socai2/exploration_query.sql"}
        assert {name for name in http_only_app if Path(name).suffix != ".md"} == query_resources, http_only_app
        r4_sources = read_json(R4_PROFILE)["expected_source_hashes"]
        for name in query_resources:
            assert sha(http_bytes[name]) == r4_sources["services/api/" + name], name
        check("all_shared_app_runtime_sources_equal", common_files=len(core),
              http_only_documentation=[name for name in http_only_app if Path(name).suffix == ".md"],
              http_only_query_sql_unchanged_from_r4=sorted(query_resources),
              file_sha256={name: sha(http_bytes[name]) for name in core})

        accepted = read_json(ACCEPTED)["files"]
        matched = {}
        for source, expected in accepted.items():
            if source.startswith("services/api/"):
                target = source.removeprefix("services/api/")
                assert target in http_bytes and sha(http_bytes[target]) == expected, source
                if target.startswith("app/"):
                    assert target in processing_bytes and sha(processing_bytes[target]) == expected, source
                matched[source] = expected
            elif source.startswith("services/fusion/"):
                target = "smoke-fusion/" + source.removeprefix("services/fusion/")
                assert target in processing_bytes and sha(processing_bytes[target]) == expected, source
                matched[source] = expected
        assert len(matched) == freeze["accepted_3c2_api_fusion_files_matched"] == 286
        check("accepted_3c2_actual_source_freeze_matches", baseline=str(ACCEPTED.relative_to(ROOT)),
              matched_files=len(matched), api_files=sum(name.startswith("services/api/") for name in matched),
              fusion_files=sum(name.startswith("services/fusion/") for name in matched), file_sha256=matched)

        c1 = read_json(C1_SCOPE)
        c1_name = c1["source"].removeprefix("services/api/")
        assert sha(http_bytes[c1_name]) == sha(processing_bytes[c1_name]) == c1["sha256"]
        deep = "app/socai2/case_deep_delivery.py"
        assert deep in http_bytes and http_bytes[deep] == processing_bytes[deep]
        check("validated_c1_and_current_deep_file_in_both_packages", c1_source=c1["source"],
              c1_sha256=c1["sha256"], deep_source=deep, deep_sha256=sha(http_bytes[deep]),
              D5a_abnormal_acceptance="incomplete_not_claimed")

        child_env = dict(os.environ, SOCAI2_HTTP_RELEASE=profile["release"], PYTHONDONTWRITEBYTECODE="1")
        child = subprocess.run([sys.executable, "-I", "-B", "-c", IMPORT_PROBE, str(http)],
                               cwd="/private/tmp", env=child_env, capture_output=True, text=True, timeout=45)
        assert child.returncode == 0, ("offline_package_import_failed", child.stderr[-2000:])
        probe = json.loads(child.stdout)
        actual = probe["document"]
        packed = json.loads(http_bytes[profile["expected_openapi_file"]])
        r4 = read_json(R4)
        normalized = lambda d: {k: v for k, v in d.items() if k not in {"info", "servers"}}
        assert normalized(actual) == normalized(packed) == normalized(r4)
        assert actual["info"]["version"] == packed["info"]["version"] == profile["release"]
        verbs = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
        operations = [(path, method) for path, item in actual["paths"].items() for method in item if method in verbs]
        schemas = actual["components"]["schemas"]
        assert len(operations) == profile["expected_operations"] == 80
        assert len(schemas) == 181 and schemas == r4["components"]["schemas"]
        assert not actual.get("security") and not actual["components"].get("securitySchemes")
        assert not any(actual["paths"][path][method].get("security") for path, method in operations)
        assert not probe["network_attempts"] and not probe["lifespan_started"]
        check("actual_frozen_package_import_and_public_openapi", operations=80, schemas=181, paths=len(actual["paths"]),
              public_contract_equal_to_r4_except_info_servers=True, release=profile["release"],
              normalized_contract_sha256=sha(encoded(normalized(actual))),
              all_schema_sha256=sha(encoded(schemas)), authentication_required=False,
              imported_module_origins=probe["module_origins"], network_attempts=0, lifespan_started=False,
              interpreter=sys.executable)
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = {"type": type(exc).__name__, "detail": str(exc)}
    finally:
        after = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in tracked}
        immutable_files = all(sha((http / name).read_bytes()) == digest for name, digest in read_json(http / "manifest.json")["files"].items())
        report["review_inputs_before"] = before
        report["review_inputs_after"] = after
        report["frozen_inputs_unchanged"] = before == after and immutable_files
        if not report["frozen_inputs_unchanged"]:
            report["status"] = "failed"
        with OUTPUT.open("x") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]),
                      "frozen_inputs_unchanged": report["frozen_inputs_unchanged"],
                      "report": str(OUTPUT.relative_to(ROOT))}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
