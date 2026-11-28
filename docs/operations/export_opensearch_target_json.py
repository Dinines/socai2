"""Export one explicit OpenSearch index and target classes to private JSON files."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import ssl
from collections import Counter
from contextlib import ExitStack
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from app.services.receipt_json import encoded


def loads(value):
    def unique(pairs):
        result = {}
        for key, child in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = child
        return result
    return json.loads(value, parse_float=Decimal, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_json")))


def require(ok, code):
    if not ok:
        raise ValueError(code)


def file_hash(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""):
            result.update(chunk)
    return result.hexdigest()


def json_array(ndjson, output):
    expected = hashlib.sha256()
    with ndjson.open("rb") as source, output.open("xb") as dest:
        def write(value):
            dest.write(value)
            expected.update(value)
        write(b"[\n")
        first = True
        for line in source:
            require(line.endswith(b"\n"), "incomplete_ndjson_line")
            if not first:
                write(b",\n")
            write(line[:-1])
            first = False
        write(b"\n]\n")
    require(file_hash(output) == expected.hexdigest(), "array_readback_mismatch")


def page_hits(page, expected_total=None):
    require(page.get("timed_out") is False, "search_timed_out_or_missing_status")
    shards = page.get("_shards", {})
    require(shards.get("failed") == 0 and shards.get("successful") == shards.get("total"), "incomplete_search_shards")
    total = page["hits"]["total"]
    require(total["relation"] == "eq" and type(total["value"]) is int, "inexact_search_total")
    if expected_total is not None:
        require(total["value"] == expected_total, "scroll_total_changed")
    hits = page["hits"]["hits"]
    require(isinstance(hits, list), "invalid_search_hits")
    return total["value"], hits


def source_document(hit, index, targets, seen):
    require(hit.get("_index") == index and isinstance(hit.get("_id"), str), "unexpected_document_identity")
    require(hit["_id"] not in seen, "duplicate_document_in_snapshot")
    source = hit.get("_source")
    require(isinstance(source, dict) and isinstance(source.get("ocsf"), dict), "complete_ocsf_source_required")
    cls = source["ocsf"].get("class_uid")
    require(type(cls) is int and cls in targets, "document_outside_target_classes")
    seen.add(hit["_id"])
    return {"_index": index, "_id": hit["_id"], "_source": source}, cls


def verify(root):
    manifest = loads((root/"manifest.json").read_text())
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    require(actual - {"manifest.json", "status.json"} == set(manifest["files"]), "export_file_set_mismatch")
    for name, expected in manifest["files"].items():
        path = root/name
        require(path.resolve().is_relative_to(root.resolve()) and path.is_file(), "invalid_export_file")
        require(file_hash(path) == expected["sha256"] and path.stat().st_size == expected["bytes"], "export_file_mismatch")
    counts, seen = Counter(), set()
    with (root/"documents.ndjson").open() as documents, (root/"ocsf.ndjson").open() as originals:
        for document_line, original_line in zip(documents, originals, strict=True):
            document, cls = source_document(loads(document_line), manifest["index"], manifest["target_class_uids"], seen)
            require(loads(original_line) == document["_source"]["ocsf"], "ocsf_readback_mismatch")
            counts[str(cls)] += 1
    require(len(seen) == manifest["snapshot_total"], "export_count_mismatch")
    require({str(cls): counts[str(cls)] for cls in manifest["target_class_uids"]} == manifest["counts_by_class"], "class_count_mismatch")
    for cls in manifest["target_class_uids"]:
        count = 0
        with (root/f"by-class/class-{cls}.ndjson").open() as handle:
            for line in handle:
                require(loads(line).get("class_uid") == cls, "class_split_mismatch")
                count += 1
        require(count == counts[str(cls)], "class_split_count_mismatch")
    return True


def export(config):
    root = Path(config["output_directory"])
    os.umask(0o077)
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    (root/"pages").mkdir()
    (root/"by-class").mkdir()
    (root/"json").mkdir()
    index, targets = config["index"], config["target_class_uids"]
    require(re.fullmatch(r"[a-z0-9][a-z0-9_.-]+", index) is not None, "explicit_index_required")
    require(bool(targets) and all(type(v) is int and 0 <= v < 2**32 for v in targets) and len(set(targets)) == len(targets), "invalid_target_classes")
    endpoint = urlparse(config["base_url"])
    require(endpoint.scheme in {"http", "https"} and endpoint.hostname and endpoint.port and not endpoint.username, "explicit_endpoint_required")
    require(config["authentication"] == "none", "unsupported_export_authentication")
    for name in ("page_size", "request_timeout_seconds", "max_response_bytes", "max_export_bytes", "max_records", "max_pages"):
        require(type(config[name]) is int and config[name] > 0, "explicit_export_limits_required")
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()))
    used_bytes = 0

    def request(method, path, body=None):
        nonlocal used_bytes
        req = Request(config["base_url"].rstrip("/")+path,
                      data=encoded(body).encode() if body is not None else None,
                      headers={"Content-Type": "application/json"}, method=method)
        with opener.open(req, timeout=config["request_timeout_seconds"]) as response:
            raw = response.read(config["max_response_bytes"]+1)
        require(len(raw) <= config["max_response_bytes"], "search_response_exceeds_limit")
        used_bytes += len(raw)
        require(used_bytes <= config["max_export_bytes"], "export_exceeds_limit")
        return raw, loads(raw)

    scroll_ids, seen, counts = set(), set(), Counter()
    completed, released, failure = False, True, None
    try:
        _, mapping = request("GET", "/"+quote(index, safe="")+"/_mapping")
        properties = mapping[index]["mappings"]["properties"]
        cls_field = properties["ocsf"]["properties"]["class_uid"]
        require(cls_field.get("type") in {"long", "integer", "short", "byte"} and cls_field.get("index", True), "indexed_class_contract_required")
        (root/"query.json").write_text(encoded({"terms": {"ocsf.class_uid": targets}})+"\n")
        raw, page = request("POST", "/"+quote(index, safe="")+"/_search?"+urlencode({"scroll": config["scroll_keepalive"]}),
                            {"size": config["page_size"], "sort": ["_doc"], "track_total_hits": True,
                             "_source": True, "query": {"terms": {"ocsf.class_uid": targets}}})
        total = None
        with ExitStack() as stack:
            documents = stack.enter_context((root/"documents.ndjson").open("x"))
            originals = stack.enter_context((root/"ocsf.ndjson").open("x"))
            classes = {cls: stack.enter_context((root/f"by-class/class-{cls}.ndjson").open("x")) for cls in targets}
            for number in range(config["max_pages"]):
                if page.get("_scroll_id"):
                    scroll_ids.add(page["_scroll_id"])
                total, hits = page_hits(page, total)
                require(total <= config["max_records"], "snapshot_exceeds_record_limit")
                with gzip.open(root/f"pages/page-{number:06}.json.gz", "wb") as handle:
                    handle.write(raw)
                if not hits:
                    require(len(seen) == total, "incomplete_scroll_snapshot")
                    completed = True
                    break
                for hit in hits:
                    document, cls = source_document(hit, index, targets, seen)
                    document_text, original_text = encoded(document), encoded(document["_source"]["ocsf"])
                    require(loads(document_text) == document and loads(original_text) == document["_source"]["ocsf"], "exact_json_roundtrip_failed")
                    documents.write(document_text+"\n")
                    originals.write(original_text+"\n")
                    classes[cls].write(original_text+"\n")
                    counts[str(cls)] += 1
                require(len(seen) <= total, "scroll_exceeds_declared_total")
                require(isinstance(page.get("_scroll_id"), str), "scroll_context_missing")
                raw, page = request("POST", "/_search/scroll", {"scroll": config["scroll_keepalive"], "scroll_id": page["_scroll_id"]})
                if page.get("_scroll_id"):
                    scroll_ids.add(page["_scroll_id"])
            require(completed, "scroll_page_limit_reached")
        for cls in targets:
            json_array(root/f"by-class/class-{cls}.ndjson", root/f"json/class-{cls}.json")
        manifest = {"schema_version": "socai2.es-target-json-export.v1", "index": index,
                    "target_class_uids": targets, "snapshot_total": total,
                    "counts_by_class": {str(cls): counts[str(cls)] for cls in targets},
                    "files": {str(p.relative_to(root)): {"sha256": file_hash(p), "bytes": p.stat().st_size}
                              for p in sorted(root.rglob("*")) if p.is_file()}}
        (root/"manifest.json").write_text(encoded(manifest)+"\n")
        verify(root)
    except Exception as exc:  # noqa: BLE001 -- source data and error details never reach stdout.
        completed = False
        failure = type(exc).__name__
        (root/"failure.json").write_text(encoded({"exception_type": failure})+"\n")
    finally:
        if scroll_ids:
            try:
                _, result = request("DELETE", "/_search/scroll", {"scroll_id": sorted(scroll_ids)})
                released = result.get("succeeded") is True
            except Exception:  # noqa: BLE001
                released = False
    status = {"execution": "completed" if completed else "incomplete", "validation": "passed" if completed else "not_passed",
              "search_context_released": released, "private_manifest_saved": (root/"manifest.json").exists()}
    (root/"status.json").write_text(encoded(status)+"\n")
    print(encoded(status))
    return 0 if completed and released else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--profile")
    mode.add_argument("--verify-only")
    args = parser.parse_args()
    if args.verify_only:
        verify(Path(args.verify_only))
        print('{"execution":"completed","validation":"passed"}')
        return 0
    return export(loads(Path(args.profile).read_text()))


if __name__ == "__main__":
    raise SystemExit(main())
