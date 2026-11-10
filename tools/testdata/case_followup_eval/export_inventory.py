"""Export actual visible messages, schemas and replies for human review only."""
import argparse
import hashlib
import json
from pathlib import Path

from .audit import ROOT, digest, read, sha


def checked(artifact):
    assert artifact["content_json"] is not None
    assert digest(artifact["content_json"]) == artifact["sha256"]
    return artifact["content_json"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("inventory-config.json"))
    args = parser.parse_args()
    config = read(args.config)
    output = ROOT / config["output"]
    if output.exists():
        raise ValueError("inventory_already_exists")
    fingerprints = {str(p.relative_to(ROOT)): sha(p) for p in [args.config.resolve(), Path(__file__).resolve()]}
    exchanges = []
    for item in config["snapshots"]:
        path = ROOT / item["path"]
        fingerprints[item["path"]] = sha(path)
        data = read(path)
        artifacts = {a["id"]: a for a in data["artifacts"]}
        steps = {s["id"]: s for s in data["run_steps"]}
        for spec in item["requests"]:
            request = artifacts[spec["id"]]
            step = steps[request["step_id"]]
            response = artifacts[step["output_artifact_id"]]
            assert request["run_id"] == response["run_id"] == step["run_id"]
            assert request["tenant_id"] == response["tenant_id"]
            req, res = checked(request), checked(response)
            req, res = req.get("payload", req), res.get("payload", res)
            exchanges.append({**spec, "body": req["body"], "raw": res["raw"],
                "request_source": item["path"], "response_source": item["path"],
                "response_artifact_id": response["id"], "run_id": step["run_id"], "stage": step["stage_code"],
                "step_state": step["state"], "step_error": step.get("error")})
    for spec in config["standalone"]:
        for key in ("request", "result"):
            fingerprints[spec[key]] = sha(ROOT / spec[key])
        result = read(ROOT / spec["result"])
        exchanges.append({**spec, "body": read(ROOT / spec["request"]), "raw": result["raw"],
            "request_source": spec["request"], "response_source": spec["result"], "stage": "C3",
            "http_status": result["http_status"], "run_id": None})
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for exchange in exchanges:
        folder = output / exchange["key"]
        folder.mkdir()
        body = exchange["body"]
        # Only the visible answer; do not export provider reasoning fields.
        choice = exchange["raw"]["choices"][0]
        answer = choice["message"]["content"]
        assert isinstance(answer, str)
        input_text = "\n\n".join(f"消息 {i} · {m['role']}\n\n{m['content']}" for i, m in enumerate(body["messages"], 1))
        files = {"input.txt": input_text, "output-original.txt": answer,
                 "request.json": json.dumps(body, ensure_ascii=False, indent=2),
                 "output-schema.json": json.dumps(body["response_format"]["json_schema"]["schema"], ensure_ascii=False, indent=2)}
        for name, value in files.items():
            (folder / name).write_bytes(value.encode())
        assert (folder / "output-original.txt").read_bytes() == answer.encode()
        assert read(folder / "request.json") == body
        records.append({k: v for k, v in exchange.items() if k not in {"body", "raw"}} | {
            "finish_reason": choice["finish_reason"], "usage": exchange["raw"].get("usage"),
            "visible_answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
            "files": {name: sha(folder / name) for name in files}})
    assert all(sha(ROOT / name) == value for name, value in fingerprints.items())
    (output / "manifest.json").write_text(json.dumps({"batch": config["batch"],
        "mode": "read_only_export_of_saved_visible_model_io", "new_model_calls": 0, "database_connections": 0,
        "source_sha256": fingerprints, "records": records,
        "limitations": ["historical_exchanges_not_new_online_probe", "separate_batches_not_controlled_ab",
            "C3_standalone_generation_not_business_run", "raw_answers_include_known_failures",
            "no_provider_reasoning_exported", "no_optional_C3_reanalysis_sample_in_this_inventory"]}, ensure_ascii=False, indent=2) + "\n")
    lines = ["# 模型实际输入输出原件", "", "从保存原件逐值提取；0 新模型调用、0 数据库连接。失败和截断按原样保留。", "",
             "| 环节 | 版本/结果说明 | 完整输入 | 原始输出 | 要求的输出结构 |",
             "| --- | --- | --- | --- | --- |"]
    for row in records:
        key = row["key"]
        lines.append(f"| {row['title']} | {row['note']} | [输入]({key}/input.txt) | [原答]({key}/output-original.txt) | [Schema]({key}/output-schema.json) |")
    lines += ["", "每个目录同时保存 `request.json`，可核对消息、Schema 和实际调用参数；输入文本中的消息边界由本导出器标注，消息正文不改写。", "",
        "C3.reanalysis 是可选入口，本目录没有该环节的新样例；职责和合同见[完整清单](../../../investigation/model-input-output-current-20261109.md)。", ""]
    (output / "README.md").write_text("\n".join(lines))
    print(json.dumps({"output": str(output.relative_to(ROOT)), "saved_exchanges": len(records), "new_model_calls": 0}))


if __name__ == "__main__":
    main()
