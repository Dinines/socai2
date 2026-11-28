"""Download one complete document per explicit class; raw values stay local."""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import ProxyHandler, Request, build_opener

from app.services.lake_ingress import ABSENT, BLOCKED, nested, tagged
from app.services.receipt_json import encoded
from export_opensearch_target_json import file_hash, loads, require, source_document


def pretty(value, level=0):
    """Readable JSON without turning precise decimals into strings or floats."""
    if not isinstance(value, (dict, list)) or not value:
        return encoded(value)
    indent, inner = "  " * level, "  " * (level + 1)
    if isinstance(value, list):
        return "[\n" + ",\n".join(inner + pretty(v, level + 1) for v in value) + "\n" + indent + "]"
    return "{\n" + ",\n".join(inner + encoded(k) + ": " + pretty(v, level + 1)
                               for k, v in value.items()) + "\n" + indent + "}"


def select_one(page, *, index, cls, seen):
    shards = page.get("_shards", {})
    require(page.get("timed_out") is False and shards.get("failed") == 0
            and type(shards.get("total")) is int and shards["total"] > 0
            and shards.get("successful") == shards["total"], "sample_search_incomplete")
    hits = page.get("hits", {}).get("hits")
    require(isinstance(hits, list) and len(hits) == 1, "one_sample_required_for_each_requested_class")
    document, _ = source_document(hits[0], index, [cls], seen)
    return document


def save_json(path, value):
    text = pretty(value) + "\n"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)
    require(tagged(loads(path.read_text())) == tagged(value), "sample_json_readback_mismatch")


def view_value(value):
    if value is ABSENT:
        return "<em>字段不存在</em>"
    if value is BLOCKED:
        return "<em>祖先不是对象，不能按该路径读取</em>"
    return "<pre>" + html.escape(pretty(value)) + "</pre>"


def review_html(profile, documents):
    esc = html.escape
    parts = ["<!doctype html><html lang='zh-CN'><meta charset='utf-8'>",
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\">",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>11类真实JSON样本与工具设计</title>",
        ("<style>body{font:16px/1.6 system-ui;margin:32px auto;max-width:1200px;padding:0 20px;color:#172032}"
        "a{color:#1556ad}article{border-top:2px solid #d7dce5;padding:20px 0}table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #d7dce5;padding:10px;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;"
        "font:13px/1.55 monospace;background:#f3f5f8;padding:12px;max-height:640px;overflow:auto}"
        "summary{cursor:pointer;font-weight:600;padding:8px}small{color:#526176}.note{background:#fff6db;padding:16px}</style>"),
        "<h1>真实JSON样本与取证工具讨论</h1>",
        ("<p class='note'>本页包含实际原始字段值，未脱敏，仅保存在本机。请勿直接上传给Codex/GPT。"
        "每类按Kafka分区、offset升序取一条；单条样本不代表该类全部数据。工具说明基于类别语义，尚非样本业务判定或查询验收。</p>"),
        "<p>每张卡片提供真实JSON、ES来源文档、根字段与partial字段。完整原文不截断；折叠仅影响显示。</p><nav>"]
    for card in profile["classes"]:
        parts.append(f"<a href='#class-{card['class_uid']}'>{card['class_uid']} {esc(card['name'])}</a> · ")
    parts.append("</nav>")
    for card in profile["classes"]:
        cls = card["class_uid"]
        original = documents[cls]["_source"]["ocsf"]
        parts += [f"<article id='class-{cls}'><h2>{cls} · {esc(card['name'])}</h2>",
            f"<p>用户提供的该类条数：{card['user_count']:,}。候选工具：<strong>{esc(card['tool'])}</strong>。</p>",
            f"<p>能回答的问题：{esc(card['question'])}</p><p>查询方向：{esc(card['query'])}</p>",
            f"<p>边界：{esc(card['boundary'])}</p>",
            f"<p><a href='ocsf/class-{cls}.json'>完整OCSF JSON</a> · <a href='documents/class-{cls}.json'>完整ES来源文档</a></p>",
            ("<details open><summary>实际业务字段对照</summary><table><thead><tr><th>路径</th><th>根路径实际值</th>"
            "<th>partial对应路径实际值</th></tr></thead><tbody>")]
        for path in dict.fromkeys([*profile["common_paths"], *card["inspect_paths"]]):
            root = nested(original, tuple(path.split(".")))
            partial = nested(original, ("unmapped", "spirithub", "partial_fields", *path.split(".")))
            parts.append(f"<tr><td>{esc(path)}</td><td>{view_value(root)}</td><td>{view_value(partial)}</td></tr>")
        parts += ["</tbody></table></details><details><summary>展开完整原始JSON</summary>", view_value(original),
            "</details><small>partial列为原文展示，不代表已允许回填。缺失、null、空数组及冲突须按既定规则分别处理。</small></article>"]
    return "\n".join([*parts, "</html>"])


def sample(profile, request=None):
    os.umask(0o077)
    root = Path(profile["output_directory"])
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name in ("responses", "documents", "ocsf"):
        (root / name).mkdir()
    passed = False
    try:
        endpoint = urlparse(profile["base_url"])
        require(endpoint.scheme == "http" and endpoint.hostname == "127.0.0.1" and endpoint.port
                and not endpoint.username, "explicit_loopback_forward_required")
        classes = [v["class_uid"] for v in profile["classes"]]
        require(classes and all(type(v) is int and 0 <= v < 2**32 for v in classes)
                and len(set(classes)) == len(classes), "unique_target_classes_required")
        require(all(type(profile[n]) is int and profile[n] > 0 for n in ("timeout_seconds", "max_response_bytes")), "explicit_read_limits_required")
        if request is None:
            opener = build_opener(ProxyHandler({}))

            def request(body):
                req = Request(profile["base_url"] + "/" + quote(profile["index"], safe="") + "/_search",
                    data=encoded(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with opener.open(req, timeout=profile["timeout_seconds"]) as response:
                    raw = response.read(profile["max_response_bytes"] + 1)
                require(len(raw) <= profile["max_response_bytes"], "sample_response_exceeds_limit")
                return raw

        seen, documents, queries = set(), {}, {}
        for cls in classes:
            query = {"size": 1, "track_total_hits": False, "_source": True,
                "query": {"term": {"ocsf.class_uid": cls}},
                "sort": [{"kafka.partition": {"order": "asc", "unmapped_type": "long"}},
                         {"kafka.offset": {"order": "asc", "unmapped_type": "long"}}]}
            raw = request(query)
            (root / "responses" / f"class-{cls}.json").write_bytes(raw)
            document = select_one(loads(raw), index=profile["index"], cls=cls, seen=seen)
            save_json(root / "documents" / f"class-{cls}.json", document)
            save_json(root / "ocsf" / f"class-{cls}.json", document["_source"]["ocsf"])
            queries[str(cls)], documents[cls] = query, document
        save_json(root / "queries.json", queries)
        page = review_html(profile, documents)
        (root / "index.html").write_text(page)
        require((root / "index.html").read_text() == page, "review_page_readback_mismatch")
        manifest = {"version": "socai2.class-samples.v1", "scope": "one_per_configured_class_not_full_class_coverage",
            "index": profile["index"], "class_uids": classes,
            "files": {str(p.relative_to(root)): file_hash(p) for p in sorted(root.rglob("*")) if p.is_file()}}
        save_json(root / "manifest.json", manifest)
        require(all(file_hash(root / path) == digest for path, digest in manifest["files"].items()), "sample_files_changed")
        passed = True
    except Exception as exc:  # noqa: BLE001 -- avoid printing source bodies or errors containing data.
        save_json(root / "failure.json", {"exception_type": type(exc).__name__})
    status = {"execution": "completed" if passed else "incomplete", "all_requested_classes_sampled": passed,
        "complete_json_saved_and_read_back": passed, "local_actual_value_review_created": passed,
        "raw_data_disclosed_to_codex": False}
    save_json(root / "status.json", status)
    print(json.dumps(status))
    return 0 if passed else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    raise SystemExit(sample(loads(Path(args.profile).read_text())))
