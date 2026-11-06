"""Build the offline processing job and its isolated smoke test from allowlisted sources."""
import argparse
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from prepare_next_service import support_schema

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy/aisoc21"
OUTPUT = ROOT / ".local/processing-release"
DATABASE = "socai2_processing_handoff"
JOB_ROLE = "socai2_processing_job"
DEFAULT_RELEASE = "processing-20261106-r3"
MIGRATIONS = (
    "123_socai2_page_data_model.sql",
    "124_socai2_case_source_binding.sql",
    "125_socai2_baseline_input_freshness.sql",
    "126_socai2_case_page_data.sql",
)


def git(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", *arguments],
        cwd=ROOT, text=True,
    ).strip()


def processing_grants() -> bytes:
    sys.path.insert(0, str(ROOT / "deploy/local-investigation"))
    try:
        from schema import API_ROLE, FUSION_ROLE, grants_schema
        from schema import DATABASE as local_database
    finally:
        sys.path.pop(0)

    lines = []
    for statement in grants_schema().splitlines():
        if FUSION_ROLE in statement:
            if not re.fullmatch(r"GRANT [^;]+ TO " + re.escape(FUSION_ROLE) + ";", statement):
                raise ValueError("Unexpected Fusion privilege in the grant template")
            continue
        lines.append(statement.replace(API_ROLE, JOB_ROLE).replace(local_database, DATABASE))
    if f"GRANT CONNECT ON DATABASE {DATABASE} TO {JOB_ROLE};" not in lines:
        raise ValueError("Missing database grant for the processing job")
    return ("\n".join(lines) + "\n").encode()


def source_bytes(path: Path) -> bytes:
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError(f"Expected a regular source file inside the workspace: {path}")
    return path.read_bytes()


def payloads() -> dict[str, bytes]:
    files = {}
    for source, prefix, suffixes in (
        ("services/api/app/socai2", "app/socai2", {".py", ".json"}),
        ("services/fusion/app", "smoke-fusion/app", {".py"}),
    ):
        folder = ROOT / source
        for path in sorted(folder.rglob("*")):
            if path.suffix not in suffixes:
                continue
            relative = path.relative_to(folder)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
                raise ValueError(f"Unexpected hidden or cached source: {relative}")
            files[f"{prefix}/{relative.as_posix()}"] = source_bytes(path)
        if f"{prefix}/__init__.py" not in files:
            raise ValueError(f"Missing Python package in {source}")

    # Migration 126 adds Case ORM fields that are absent from the pinned n15 base.
    files["app/models/socai2.py"] = source_bytes(ROOT / "services/api/app/models/socai2.py")
    for name in ("processing_job.py", "processing_smoke.py", "processing_host.py"):
        files[name] = source_bytes(DEPLOY / name)
    files["Dockerfile"] = source_bytes(DEPLOY / "processing.Dockerfile")
    for name in MIGRATIONS:
        files["schema/" + name] = source_bytes(ROOT / "services/api/migrations" / name)
    # SQLAlchemy builds DDL from model metadata. Give its lazy engine a local inert URL.
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://127.0.0.1:1/metadata"
    files["schema/support.sql"] = support_schema()
    files["schema/grants.sql"] = processing_grants()
    return files


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(release: str) -> Path:
    if not re.fullmatch(r"processing-[0-9]{8}-r[1-9][0-9]*", release):
        raise ValueError("Expected a release tag like processing-20261106-r1")
    directory = OUTPUT / release
    if directory.resolve() != directory:
        raise ValueError("Release output must stay in the repository's .local/processing-release")
    files = payloads()
    manifest = {
        "release": release,
        "source_branch": git("symbolic-ref", "--short", "HEAD"),
        "source_commit": git("rev-parse", "--verify", "HEAD"),
        "source_basis": "working tree; per-file SHA-256 includes local changes",
        "database": DATABASE,
        "job_role": JOB_ROLE,
        "files": {name: {"sha256": sha256(body), "bytes": len(body), "mode": "0644"}
                  for name, body in sorted(files.items())},
    }
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUTPUT) as temporary:
        stage = Path(temporary) / release
        stage.mkdir()
        archive = stage / "release.tar.gz"
        with (
            archive.open("wb") as raw,
            gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz,
            tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar,
        ):
            for name, body in sorted(files.items()):
                member = tarfile.TarInfo(name)
                member.size, member.mode, member.mtime = len(body), 0o644, 0
                tar.addfile(member, io.BytesIO(body))
        (stage / "manifest.json").write_bytes(files["manifest.json"])
        sums = (f"{sha256(archive.read_bytes())}  release.tar.gz\n"
                f"{sha256(files['manifest.json'])}  manifest.json\n")
        (stage / "SHA256SUMS").write_bytes(sums.encode("ascii"))
        if directory.exists():
            names = {"release.tar.gz", "manifest.json", "SHA256SUMS"}
            if {p.name for p in directory.iterdir()} == names and all(
                source_bytes(directory / name) == (stage / name).read_bytes() for name in names
            ):
                return directory
            raise FileExistsError(f"Release tag already contains different content: {directory}")
        stage.rename(directory)
    return directory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", default=DEFAULT_RELEASE)
    print(build(parser.parse_args().release))
