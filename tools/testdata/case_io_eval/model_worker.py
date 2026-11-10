"""Bounded internal gateway calls; no business writes or hidden-reasoning logs."""
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request


def visible_response(raw, hidden_fields):
    removed = []

    def walk(value, path):
        if isinstance(value, dict):
            output = {}
            for key, item in value.items():
                if key in hidden_fields and item is not None:
                    serialized = json.dumps(item, ensure_ascii=False, sort_keys=True).encode()
                    removed.append({"path": [*path, key], "sha256": hashlib.sha256(serialized).hexdigest(), "bytes": len(serialized)})
                    output[key] = None
                else:
                    output[key] = walk(item, [*path, key])
            return output
        if isinstance(value, list):
            return [walk(item, [*path, i]) for i, item in enumerate(value)]
        return value

    result = dict(raw)
    result["choices"] = []
    for i, choice in enumerate(raw.get("choices", [])):
        copy = dict(choice)
        if isinstance(choice.get("message"), dict):
            copy["message"] = walk(choice["message"], ["choices", i, "message"])
        result["choices"].append(copy)
    return result, removed


def main():
    task = json.load(sys.stdin)
    config = task["transport"]
    env_path = pathlib.Path(config["runtime_env_file"])
    env_bytes = env_path.read_bytes()
    env = dict(line.split("=", 1) for line in env_bytes.decode().splitlines() if "=" in line and not line.startswith("#"))
    key = env[config["key_variable"]]
    assert env[config["model_variable"]] == config["expected_model"]
    base = config["gateway_base_url"].rstrip("/")

    def request(path, body=None):
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        req = urllib.request.Request(path, data=data, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=task["timeout_seconds"]) as response:
            payload = response.read()
            return response.status, json.loads(payload), hashlib.sha256(payload).hexdigest()

    if task["phase"] == "preflight":
        status, models, _ = request(base + "/models")
        assert config["expected_model"] in [m["id"] for m in models["data"]]
        _, info, _ = request(base.removesuffix("/v1") + "/model/info")
        route = next(r for r in info["data"] if r["model_name"] == config["expected_model"])["litellm_params"]
        result = {"state": "ready", "http_status": status, "model": config["expected_model"],
                  "upstream_model": route.get("model"), "upstream_base": route.get("api_base"),
                  "runtime_sha256": hashlib.sha256(env_bytes).hexdigest(), "generation_calls": 0}
    elif task["phase"] == "call":
        assert re.fullmatch(r"[A-Za-z0-9_-]+", task["cell"])
        assert task["body"]["model"] == config["expected_model"]
        folder = pathlib.Path(config["remote_evidence_dir"])
        folder.mkdir(parents=True, exist_ok=True)
        intent = folder / (task["cell"] + "-intent.json")
        output = folder / (task["cell"] + "-result.json")
        if intent.exists():
            result = json.loads(output.read_text()) if output.exists() else {"state": "unknown_existing_intent_no_redispatch"}
        else:
            with intent.open("x") as stream:
                json.dump({"body_sha256": hashlib.sha256(json.dumps(task["body"], sort_keys=True, ensure_ascii=False).encode()).hexdigest(), "attempt": 1}, stream)
            started = time.monotonic()
            try:
                status, raw, response_hash = request(base + "/chat/completions", task["body"])
                visible, removed = visible_response(raw, task["hidden_message_fields"])
                result = {"state": "response_received", "http_status": status, "raw": visible,
                          "provider_response_sha256": response_hash, "hidden_message_fields_omitted": removed}
            except urllib.error.HTTPError as exc:
                result = {"state": "http_rejection" if 400 <= exc.code < 500 and exc.code not in (408, 429) else "unknown_no_retry",
                          "http_status": exc.code, "error_body": exc.read(6000).decode(errors="replace").replace(key, "[REDACTED]")}
            except (OSError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                result = {"state": "unknown_no_retry", "error_type": type(exc).__name__}
            result["http_seconds"] = round(time.monotonic() - started, 6)
            safe = json.dumps(result, ensure_ascii=False)
            assert key not in safe
            with output.open("x") as stream:
                stream.write(safe)
    else:
        raise ValueError("unsupported_phase")
    safe = json.dumps(result, ensure_ascii=False)
    assert key not in safe
    print(safe, flush=True)


if __name__ == "__main__":
    main()
