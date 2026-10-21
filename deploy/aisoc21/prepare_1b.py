#!/usr/bin/env python3
"""Import only 1B's fixed SQL/init inputs and prepare the credential-output patch."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REVISION = "34ca18c57dd4175539e5c6dd3d04a72dc057306b"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(source: Path, output: Path) -> None:
    revision = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != REVISION:
        raise SystemExit("Reference revision changed; review before importing.")
    mapping = json.loads((ROOT / "docs/handoff/migration-source-map.json").read_text())
    group = mapping["postgres_batch"]
    entries = group["initdb_files"] + group["ordered_sql_files"]
    license_entry = next(e for e in mapping["other_direct_inputs"] if e["source_path"] == "LICENSE")
    entries = entries + [license_entry]
    for entry in entries:
        relative = entry["source_path"]
        original = source / relative
        target = ROOT / relative
        data = original.read_bytes()
        if sha(data) != entry["sha256"]:
            raise SystemExit(f"Reference hash mismatch: {relative}")
        if target.exists() and target.read_bytes() != data:
            raise SystemExit(f"Existing destination differs; retained without overwrite: {relative}")
    records = []
    for entry in entries:
        relative = entry["source_path"]
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source / relative).read_bytes())
        target.chmod(0o755 if entry["git_mode"] == "100755" else 0o644)
        records.append({**entry, "destination": relative})
    output.mkdir(parents=True, exist_ok=True)
    for entry in group["initdb_files"]:
        relative = entry["source_path"]
        data = (ROOT / relative).read_text()
        if relative.endswith("20_runtime_role_password.sh"):
            before = 'psql -v ON_ERROR_STOP=1 \\\n'
            if data.count(before) != 1:
                raise SystemExit("Unexpected upstream psql invocation; review the patch.")
            data = data.replace(before, 'psql --no-psqlrc --quiet --output=/dev/null -v ON_ERROR_STOP=1 \\\n')
            before = '     --set=app_password="${PASSWORD}" <<\'SQL\'\n'
            if data.count(before) != 1:
                raise SystemExit("Unexpected upstream password argument; review the patch.")
            data = data.replace(before, "     <<'SQL'\n\\getenv app_password AISOC_APP_DB_PASSWORD\n")
        target = output / Path(relative).name
        target.write_text(data)
        target.chmod(0o755)
    patch = {
        "source": "infra/postgres/initdb/20_runtime_role_password.sh",
        "source_sha256": sha((ROOT / "infra/postgres/initdb/20_runtime_role_password.sh").read_bytes()),
        "generated_sha256": sha((output / "20_runtime_role_password.sh").read_bytes()),
        "changes": [
            "Disable psqlrc and suppress SQL result output, including set_config's secret return value",
            "Use psql getenv so the password is not passed in psql command arguments",
        ],
        "original_modified": False,
        "activation": "Executed only for credential protection probes in the new shared-service database; not used as a shared-instance initdb hook",
    }
    (ROOT / "deploy/aisoc21/postgres-init-patch.json").write_text(
        json.dumps(patch, indent=2) + "\n"
    )
    manifest = {
        "date": "2026-10-20", "batch": "1B", "revision": REVISION,
        "reference_directory": str(source), "files": records,
        "sql_files": len(group["ordered_sql_files"]),
        "initdb_files": len(group["initdb_files"]),
        "scope": "Only PostgreSQL initialization inputs and license; application service source not imported",
        "deployment_patch": "deploy/aisoc21/postgres-init-patch.json",
    }
    (ROOT / "docs/handoff/1b-import-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"imported_files": len(records), "sql_files": manifest["sql_files"],
                      "original_init_scripts_preserved": True, "generated_initdb": str(output)}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
