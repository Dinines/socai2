#!/usr/bin/env python3
"""Copy or verify the fixed AiSOC dependency snapshot; never install or deploy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "deploy/aisoc21/dependencies/source"
MANIFEST = ROOT / "docs/handoff/dependency-manifest.json"
REVISION = "34ca18c57dd4175539e5c6dd3d04a72dc057306b"
DEFAULT_SOURCE = Path("/Users/lychee/Documents/project/SOCAI/opensource/AiSOC")
ROOT_FILES = {
    "LICENSE", "VERSION", ".dockerignore", ".gitattributes", "docker-compose.yml",
    "package.json", "pnpm-workspace.yaml", "pnpm-lock.yaml", "turbo.json",
    "tsconfig.base.json", "ruff.toml", "infra/litellm/config.yaml",
    "scripts/service_requirements.py", "scripts/gate_toolkit.py",
}
DEPENDENCY_NAMES = {
    "pyproject.toml", "poetry.lock", "package.json", "package-lock.json",
    "go.mod", "go.sum", "Dockerfile",
}


def run(*args: str, **kwargs) -> str:
    return subprocess.check_output(args, text=True, **kwargs).strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected(path: str) -> bool:
    p = Path(path)
    return path in ROOT_FILES or (
        p.parts[0] in {"services", "apps", "packages"}
        and p.name in DEPENDENCY_NAMES
    )


def copy(source: Path) -> None:
    if run("git", "-C", str(source), "rev-parse", "HEAD") != REVISION:
        raise SystemExit("Reference HEAD differs from the fixed revision; review before copying.")
    tree = run("git", "-C", str(source), "ls-tree", "-r", REVISION)
    pending = []
    for row in tree.splitlines():
        metadata, relative = row.split("\t", 1)
        if not selected(relative):
            continue
        mode, kind, blob = metadata.split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise SystemExit(f"Unsupported dependency entry: {relative}")
        src = source / relative
        if run("git", "hash-object", "--no-filters", str(src)) != blob:
            raise SystemExit(f"Reference file differs from fixed Git object: {relative}")
        dst = DEST / relative
        if dst.exists() and src.read_bytes() != dst.read_bytes():
            raise SystemExit(f"Destination changed; review before replacement: {relative}")
        pending.append((relative, src, dst, mode, blob))
    if not pending:
        raise SystemExit("No dependency files selected.")
    entries = []
    for relative, src, dst, mode, blob in pending:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        dst.chmod(0o755 if mode == "100755" else 0o644)
        entries.append({
            "source_path": relative, "destination": dst.relative_to(ROOT).as_posix(),
            "git_blob": blob, "git_mode": mode, "sha256": digest(dst),
        })
    data = {
        "schema_version": 1, "date": "2026-10-20", "revision": REVISION,
        "reference_directory": str(source), "upstream": "https://github.com/beenuar/AiSOC",
        "scope": "Dependency declarations, locks and build recipes only; application source deferred",
        "installed": False, "built": False, "deployed": False,
        "files": len(entries), "entries": entries,
    }
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def check(source: Path | None) -> None:
    data = json.loads(MANIFEST.read_text())
    errors = []
    for entry in data["entries"]:
        path = ROOT / entry["destination"]
        if not path.is_file() or digest(path) != entry["sha256"]:
            errors.append(f"Content mismatch: {entry['destination']}")
            continue
        if bool(path.stat().st_mode & 0o111) != (entry["git_mode"] == "100755"):
            errors.append(f"Executable mode mismatch: {entry['destination']}")
        if source and (source / entry["source_path"]).read_bytes() != path.read_bytes():
            errors.append(f"Reference mismatch: {entry['source_path']}")
        if run("git", "hash-object", "--no-filters", str(path)) != entry["git_blob"]:
            errors.append(f"Fixed Git object mismatch: {entry['source_path']}")
        if path.suffix == ".json":
            json.loads(path.read_text())
        elif path.suffix == ".toml" or path.name == "poetry.lock":
            tomllib.loads(path.read_text())
    inputs = "\n".join(e["destination"] for e in data["entries"]) + "\n"
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"], cwd=ROOT,
        input=inputs, text=True, capture_output=True,
    )
    if ignored.returncode not in {0, 1}:
        errors.append(ignored.stderr)
    if ignored.stdout:
        errors.append("Dependency files are Git ignored: " + ignored.stdout)
    if errors:
        raise SystemExit("\n".join(errors))
    print(json.dumps({"files_verified": len(data["entries"]), "revision": REVISION,
                      "reference_compared": bool(source), "installed": False}))


def export() -> None:
    helper = DEST / "scripts/service_requirements.py"
    output = DEST.parent / "requirements"
    output.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "AISOC_REPO_ROOT": str(DEST), "PYTHONDONTWRITEBYTECODE": "1"}
    services = sorted(p.parent.name for p in (DEST / "services").glob("*/poetry.lock"))
    summary = []
    for service in services:
        counts = {}
        for group in ("main", "all"):
            text = run(sys.executable, str(helper), service, "--locked", "--only", group, env=env)
            if not text:
                raise SystemExit(f"Empty resolved dependency set: {service}/{group}")
            (output / f"{service}.{group}.txt").write_text(text + "\n")
            counts[group] = len(text.splitlines())
        summary.append({"service": service, "locked_requirements": counts})
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"python_services_exported": len(summary), "installed": False}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--copy", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--export", action="store_true")
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.copy:
        copy(args.source or DEFAULT_SOURCE)
        check(args.source or DEFAULT_SOURCE)
    elif args.check:
        check(args.source)
    else:
        check(None)
        export()


if __name__ == "__main__":
    main()
