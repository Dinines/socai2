"""Prepare an immutable 1.2 processing image context from an explicit build profile.

Historical r1-r3 packages retain their own frozen builder and isolated launcher.
This entry prepares code only; it never creates a database or changes a service.
"""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy/aisoc21"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def source_bytes(path):
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError("Expected a regular source file: " + str(path))
    return path.read_bytes()


def load_profile(path):
    path = Path(path).resolve(strict=True)
    raw = source_bytes(path)
    data = tomllib.loads(raw.decode())
    if (set(data) != {"version", "release", "output_dir", "policy_file", "image"}
            or data["version"] != "socai2.processing-build.v1.2"
            or not re.fullmatch(r"processing-[0-9]{8}-r[1-9][0-9]*", data["release"])):
        raise ValueError("Invalid processing build profile")
    image = data["image"]
    if (set(image) != {"base_tag", "base_id", "tag", "user", "platform", "build_timeout_seconds", "buildkit"}
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", image["base_id"])
            or not re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", image["user"])
            or image["platform"] not in {"linux/amd64", "linux/arm64"}
            or type(image["build_timeout_seconds"]) is not int or image["build_timeout_seconds"] <= 0
            or image["buildkit"] is not False):
        raise ValueError("Invalid build image identity")
    for name in ("base_tag", "tag"):
        if not isinstance(image[name], str) or not re.fullmatch(r"[a-z0-9][a-z0-9._/:@-]*", image[name]):
            raise ValueError("Invalid image tag")
    if image["tag"] == image["base_tag"]:
        raise ValueError("Candidate must not replace its base image tag")
    for name in ("output_dir", "policy_file"):
        value = Path(data[name])
        data[name] = str((path.parent / value).resolve() if not value.is_absolute() else value.resolve())
    spec = importlib.util.spec_from_file_location("socai2_build_policy", ROOT / "services/api/app/socai2/runtime_policy.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    validated = module.load_policy(data["policy_file"])
    policy = source_bytes(Path(data["policy_file"]))
    if validated.sha256 != sha256(policy):
        raise ValueError("Policy changed during candidate preparation")
    return data, sha256(raw), policy


def payloads(policy):
    files = {}
    for source, prefix in (("services/api/app", "app"), ("services/fusion/app", "smoke-fusion/app")):
        folder = ROOT / source
        for path in sorted(folder.rglob("*")):
            if path.suffix not in {".py", ".json"}:
                continue
            relative = path.relative_to(folder)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
                raise ValueError("Unexpected hidden source")
            files[f"{prefix}/{relative.as_posix()}"] = source_bytes(path)
        if f"{prefix}/__init__.py" not in files:
            raise ValueError("Missing application package")
    for name in ("processing_job.py", "production_ingress.py", "build_processing_image.py"):
        files[name] = source_bytes(DEPLOY / name)
    files["Dockerfile"] = source_bytes(DEPLOY / "processing.Dockerfile")
    files["investigation-policy.toml"] = policy
    return files


def build(profile_path):
    profile, profile_hash, policy = load_profile(profile_path)
    output = Path(profile["output_dir"])
    directory = output / profile["release"]
    files = payloads(policy)
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    manifest = {
        "format": "socai2.processing-release.v1.2", "release": profile["release"],
        "source_branch": git("symbolic-ref", "--short", "HEAD"), "source_commit": git("rev-parse", "--verify", "HEAD"),
        "source_basis": "working tree; per-file SHA-256 includes local changes",
        "build_profile_sha256": profile_hash, "policy_sha256": sha256(policy), "image": profile["image"],
        "files": {name: {"sha256": sha256(body), "bytes": len(body), "mode": "0644"}
                  for name, body in sorted(files.items())},
    }
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        stage = Path(temporary) / profile["release"]
        stage.mkdir()
        archive = stage / "release.tar.gz"
        with archive.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz, \
                tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar:
            for name, body in sorted(files.items()):
                member = tarfile.TarInfo(name)
                member.size, member.mode, member.mtime = len(body), 0o644, 0
                tar.addfile(member, io.BytesIO(body))
        (stage / "manifest.json").write_bytes(files["manifest.json"])
        sums = (f"{sha256(archive.read_bytes())}  release.tar.gz\n"
                f"{sha256(files['manifest.json'])}  manifest.json\n")
        (stage / "SHA256SUMS").write_text(sums)
        if directory.exists():
            names = {"release.tar.gz", "manifest.json", "SHA256SUMS"}
            if {p.name for p in directory.iterdir()} == names and all(
                    source_bytes(directory / name) == (stage / name).read_bytes() for name in names):
                return directory
            raise FileExistsError("Release already contains different content: " + str(directory))
        stage.rename(directory)
    return directory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    print(build(parser.parse_args().profile))
