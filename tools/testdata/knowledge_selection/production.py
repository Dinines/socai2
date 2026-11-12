"""One post-release method-document write/read and bounded C2 selection readback."""
import argparse
import copy
import json
from pathlib import Path

from tools.testdata.case_knowledge.production import HTTP, PROBE, remote
from tools.testdata.historical_knowledge.production import save

ROOT = Path(__file__).resolve().parents[3]


def main(path, phase):
    config = json.loads(path.read_text())
    output = (ROOT / config["output"]).parent / "method"
    if phase == "import":
        private_path = ROOT / config["credential_file"]
        assert not private_path.stat().st_mode & 0o077
        private = json.loads(private_path.read_text())
        assert private["user_id"] == config["actor_id"] and private["tenant_id"] == config["tenant_id"]
        docs = json.loads((ROOT / config["corpus"]).read_text())
        save(output / "intent.json", {"release": config["release"], "documents": docs, "attempts": 1, "analysis_model_calls": 0})
        program = HTTP.replace("two public source documents", "one source-preserving method document")
        result = remote(config, program, {"config": config, "documents": docs, "api_key": private["api_key"]})
        save(output / "http.json", result)
        assert result["summary"]["state"] == "passed"
        print(json.dumps(result["summary"]))
    else:
        imported = json.loads((output / "http.json").read_text())["summary"]
        snapshot = json.loads((ROOT / config["local_snapshot"]).read_text())
        body = next(a["content_json"] for a in snapshot["artifacts"]
                    if a["kind"] == "tool_response" and (a["content_json"] or {}).get("tool_name") == "knowledge")
        args = copy.deepcopy(body["actual_args"])
        args["parameters"]["selectors"] = [k for k in args["parameters"]["selectors"]
            if k["purpose"] != "historical_case_reference" and k.get("facets", {}).get("ocsf.process.name")]
        save(output / "retrieval-intent.json", {"args": args, "scope": "read-only C2 probe; no Case or model call"})
        result = remote(config, PROBE, {"tenant_id": config["tenant_id"], "args": args,
            "document_ids": imported["document_ids"]}, container=True)
        save(output / "retrieval.json", result)
        print(json.dumps({"state": result["state"], "rows": len(result["rows"]), "analysis_model_calls": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("import", "probe"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    main(args.config, args.phase)
