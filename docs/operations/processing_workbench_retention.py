"""Retire rendered files replaced in the live workbench, preserving shared links."""
import re
import shutil
from pathlib import Path


def generated_paths(record):
    if not record:
        return set()
    html = [record.get("detail"), *(subject["detail"] for subject in record.get("subjects", []))]
    paths = {Path(p) for p in html if p and re.fullmatch(r"(?:cases|subjects)/[0-9a-f]{64}\.html", p)}
    index = (record.get("logs") or {}).get("index")
    if index and re.fullmatch(r"logs/[0-9a-f]{64}/index\.html", index):
        paths.add(Path(index).parent)
    return paths


def prune_publication(site_dir, previous_record, current_records):
    """Called after the index switch; only remove paths owned by the superseded record."""
    obsolete = generated_paths(previous_record)
    if not obsolete:
        return
    for record in current_records:
        obsolete.difference_update(generated_paths(record))
    root = Path(site_dir).resolve()
    for name in obsolete:
        path = root / name
        if path.resolve() != path or not path.exists():
            continue
        if name.parts[0] == "logs":
            shutil.rmtree(path)
        else:
            path.unlink()
