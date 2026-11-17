"""Read actual task links, complete directories and raw content against a snapshot."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urlsplit


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(snapshot, profile, output, transport=urllib.request.urlopen):
    raw = snapshot.read_bytes()
    document = json.loads(raw)
    rows = document.get("rows", document)
    saved = {a["id"]: a for a in rows["artifacts"]}
    all_runs = {r["id"]: r for r in rows["runs"]}
    output.mkdir(exist_ok=False)
    cache, replies, directories, results, details = {}, [], {}, {}, {}

    def get(path):
        assert path.startswith("/api/v1/socai2/") and not urlsplit(path).netloc
        if path in cache:
            return cache[path]
        with transport(
            profile["http_base"] + path, timeout=profile["timeouts"]["http_seconds"]
        ) as response:
            body = json.load(response)
            replies.append(
                {"method": "GET", "path": path, "status": response.status, "body": body}
            )
            (output / "http.json").write_text(
                json.dumps(replies, ensure_ascii=False, indent=2) + "\n"
            )
            assert response.status == 200, (path, response.status)
        cache[path] = body
        return body

    def pages(url):
        items, cursor, seen = [], None, set()
        while True:
            params = {"limit": profile["directory_page_size"]}
            if cursor is not None:
                params["cursor"] = cursor
            body = get(url + "?" + urlencode(params))
            items.extend(body["items"])
            cursor = body["next_cursor"]
            if cursor is None:
                assert len(items) == body["total"] and len(
                    {r["id"] for r in items}
                ) == len(items)
                return items
            assert cursor not in seen
            seen.add(cursor)

    def run(url, subject_type):
        detail = get(url)
        rid = detail["run"]["id"]
        details[rid] = detail
        assert detail["run"]["state"] == all_runs[rid]["state"]
        if rid in directories:
            return detail
        source = detail if subject_type == "case" else get(url + "/trace")
        steps, artifacts = pages(source["steps_url"]), pages(source["artifacts_url"])
        assert {s["id"] for s in steps} == {
            s["id"] for s in rows["run_steps"] if s["run_id"] == rid
        }
        assert {a["id"] for a in artifacts} == {
            a["id"] for a in rows["artifacts"] if a["run_id"] == rid
        }
        for item in artifacts:
            content = get(item["content_url"])
            actual = saved[item["id"]]
            metadata = content.get("artifact", content.get("metadata"))
            assert (
                content["availability"] == "available"
                and metadata["id"] == actual["id"]
            )
            assert (
                content["content_json"] == actual["content_json"]
                and content["content_text"] == actual["content_text"]
            )
            encoded = (
                json.dumps(
                    actual["content_json"],
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
                if actual["content_json"] is not None
                else actual["content_text"].encode()
            )
            assert metadata["sha256"] == actual["sha256"] == digest(encoded)
            assert metadata["size_bytes"] == actual["size_bytes"] == len(encoded)
        directories[rid] = {"steps": len(steps), "artifacts": len(artifacts)}
        return detail

    for task in rows["analysis_tasks"]:
        path = f"/api/v1/socai2/{task['subject_type']}s/{task['subject_id']}/analysis-tasks/{task['id']}"
        current = get(path)
        assert current["task_id"] == task["id"] and current["status"] == task["state"]
        attempts = [a for a in rows["analysis_attempts"] if a["task_id"] == task["id"]]
        assert len(current["attempts"]) == len(attempts)
        for attempt in current["attempts"]:
            stored = next(
                a for a in attempts if a["attempt_no"] == attempt["attempt_no"]
            )
            assert stored["run_id"] == attempt["run_id"]
            run(attempt["run_url"], task["subject_type"])
        for link in current.get("results", []):
            if link["result_type"] != "case_result":
                continue
            result = get(link["url"])["result"]
            stored = next(r for r in rows["results"] if r["id"] == result["id"])
            for key in (
                "source_run_id",
                "conclusion",
                "conclusion_state",
                "validation_state",
                "delivery_state",
                "findings",
                "questions",
            ):
                assert result[key] == stored[key]
            results[result["id"]] = result
    for detail in list(details.values()):
        rid = detail["run"]["id"]
        if all_runs[rid]["case_id"] is None:
            continue
        manifest = saved[all_runs[rid]["input_artifact_id"]]["content_json"]
        references = [
            saved[r["id"]]
            for r in manifest["source_materials"]
            if r["id"] in saved
            and saved[r["id"]]["schema_version"] == "socai2.baseline-context.v1"
        ]
        assert len(references) == 1
        for iid, incident in references[0]["content_json"]["incidents"].items():
            material = incident["analysis_material"]
            if material is None:
                continue
            source_id = material["source_run_id"]
            run(f"/api/v1/socai2/incidents/{iid}/analysis/runs/{source_id}", "incident")
            required = [
                material[k]["id"] for k in ("input", "response", "receipt_source")
            ] + [r["id"] for r in material["originals"]]
            assert all(saved[aid]["run_id"] == source_id for aid in required)
        comp = manifest["comparison_context"]
        assert detail["run"]["comparison_context"] == comp
        if comp["previous_run_id"]:
            assert (
                get(detail["previous_run_url"])["run"]["id"] == comp["previous_run_id"]
            )
        if comp["comparison_result_id"]:
            assert (
                get(detail["comparison_result_url"])["result"]["id"]
                == comp["comparison_result_id"]
            )
    assert set(directories) == set(all_runs)
    report = {
        "status": "passed",
        "source": "actual_case_readback",
        "snapshot_sha256": digest(raw),
        "batch_id": profile["batch_id"],
        "http_gets": len(replies),
        "directories": directories,
        "case_ids": [c["id"] for c in rows["cases"]],
        "result_ids": list(results),
        "terminal_run_ids": [
            r["id"]
            for r in rows["runs"]
            if r["case_id"] is not None and r["state"] in {"completed", "failed"}
        ],
        "saved_readback_complete": True,
        "new_model_calls": 0,
        "quality": "separate; HTTP consistency is not correctness",
    }
    (output / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            read(args.snapshot, json.loads(args.profile.read_text()), args.output)
        )
    )
