"""Verify and unpack a processing release on 21. Reads its archive from stdin."""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path("/opt/sting-aisoc-socai2/releases")


def unpack(release, expected_hash, archive):
    if not re.fullmatch(r"processing-[0-9]{8}-r[1-9][0-9]*", release):
        raise ValueError("invalid processing release")
    if len(archive) >= 20_000_000 or hashlib.sha256(archive).hexdigest() != expected_hash:
        raise ValueError("release archive checksum mismatch")
    if ROOT.resolve() != ROOT:
        raise ValueError("unexpected server release root")
    destination = ROOT / release
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        members = tar.getmembers()
        names = [member.name for member in members]
        if (len(members) > 500 or sum(m.size for m in members) > 40_000_000
                or len(set(names)) != len(names) or any(not m.isfile() or m.mode != 0o644 for m in members)):
            raise ValueError("unexpected archive entry")
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or p.as_posix() != name or not name.isascii():
                raise ValueError("invalid package path")
        manifest_bytes = tar.extractfile("manifest.json").read()
        manifest = json.loads(manifest_bytes)
        if manifest["release"] != release or set(names) != set(manifest["files"]) | {"manifest.json"}:
            raise ValueError("manifest content mismatch")
        if destination.exists():
            if (destination.resolve() == destination
                    and (destination / "manifest.json").read_bytes() == manifest_bytes):
                return destination
            raise FileExistsError("release already exists with different contents")
        with tempfile.TemporaryDirectory(dir=ROOT) as scratch:
            stage = Path(scratch) / release
            stage.mkdir(mode=0o750)
            for m in members:
                blob = tar.extractfile(m).read()
                if m.name != "manifest.json" and hashlib.sha256(blob).hexdigest() != manifest["files"][m.name]["sha256"]:
                    raise ValueError("payload checksum mismatch")
                target = stage / m.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(blob)
                target.chmod(0o644)
            stage.rename(destination)
    return destination


if __name__ == "__main__":
    os.umask(0o027)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release")
    parser.add_argument("sha256")
    args = parser.parse_args()
    print(unpack(args.release, args.sha256, sys.stdin.buffer.read(20_000_000)))
