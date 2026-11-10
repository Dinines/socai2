"""Run through the configured internal gateway; no database or business writes."""
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request


def main():
    x = json.load(sys.stdin)
    cfg = x["transport"]
    env = dict(line.split("=", 1) for line in pathlib.Path(cfg["runtime_env_file"]).read_text().splitlines()
               if "=" in line and not line.startswith("#"))
    key = env[cfg["key_variable"]]
    assert env[cfg["model_variable"]] == cfg["expected_model"]
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    base = cfg["gateway_base_url"].rstrip("/")

    def request(url, body=None, auth=True, timeout=30):
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        req = urllib.request.Request(url, data=data, headers=headers if auth else {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.load(response)

    if x["phase"] == "preflight":
        status, model_list = request(base + "/models")
        assert cfg["expected_model"] in [m["id"] for m in model_list["data"]]
        _, info = request(base.removesuffix("/v1") + "/model/info")
        route = next(r for r in info["data"] if r["model_name"] == cfg["expected_model"])
        params = route["litellm_params"]
        result = {"state": "ready", "http_status": status, "model": cfg["expected_model"],
                  "upstream_model": params.get("model"), "upstream_base": params.get("api_base"),
                  "runtime_sha256": hashlib.sha256(pathlib.Path(cfg["runtime_env_file"]).read_bytes()).hexdigest(),
                  "model_calls": 0}
    elif x["phase"] == "call":
        assert re.fullmatch(r"[A-Z0-9a-z_-]+", x["cell"])
        directory = pathlib.Path(cfg["remote_evidence_dir"])
        directory.mkdir(parents=True, exist_ok=True)
        intent, output = (directory / (x["cell"] + suffix) for suffix in ("-intent.json", "-result.json"))
        if intent.exists():
            result = json.loads(output.read_text()) if output.exists() else {"state": "unknown_existing_intent_no_redispatch"}
        else:
            assert x["body"]["model"] == cfg["expected_model"]
            with intent.open("x") as stream:
                json.dump({"body_sha256": hashlib.sha256(json.dumps(x["body"], sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                           "attempt": 1}, stream)
            start = time.monotonic()
            try:
                status, raw = request(base + "/chat/completions", x["body"], timeout=x["timeout_seconds"])
                result = {"state": "response_received", "http_status": status, "raw": raw}
            except urllib.error.HTTPError as exc:
                result = {"state": "http_rejection" if 400 <= exc.code < 500 and exc.code not in (408, 429) else "unknown_no_retry",
                          "http_status": exc.code, "error_body": exc.read(6000).decode("utf-8", errors="replace").replace(key, "[REDACTED]")}
            except Exception as exc:
                result = {"state": "unknown_no_retry", "error_type": type(exc).__name__}
            result["http_seconds"] = round(time.monotonic() - start, 6)
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
