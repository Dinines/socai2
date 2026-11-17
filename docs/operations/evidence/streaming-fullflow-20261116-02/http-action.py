"""Run one explicit current HTTP operation; save intent before any POST."""

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


def execute(folder, phase, request, transport=urllib.request.urlopen):
    profile = json.loads((folder / "profile.json").read_text())
    method, path = request["method"], request["path"]
    assert re.fullmatch(r"[a-zA-Z0-9_-]+", phase)
    assert (
        method in {"GET", "POST"}
        and path.startswith("/api/v1/socai2/")
        and ".." not in path
    )
    out = folder / "out"
    destination = out / ("http-" + phase + ".json")
    assert not destination.exists()
    if method == "POST":
        assert path == "/api/v1/socai2/cases" or re.fullmatch(
            r"/api/v1/socai2/(?:cases/[0-9a-f-]+/investigations|incidents/[0-9a-f-]+/diagnose)",
            path,
        )
        UUID(request["body"]["operation_key"])
        if path != "/api/v1/socai2/cases":
            assert request["body"]["mode"] == "check"
        with (out / ("intent-" + phase + ".json")).open("x") as stream:
            json.dump(
                {"state": "started_outcome_unknown", "request": request},
                stream,
                ensure_ascii=False,
                indent=2,
            )
    record = {"request": request, "observed_at": datetime.now(timezone.utc).isoformat()}
    body = (
        None
        if method == "GET"
        else json.dumps(request["body"], ensure_ascii=False).encode()
    )
    wire = urllib.request.Request(
        profile["http_base"] + path,
        method=method,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with transport(wire, timeout=profile["timeouts"]["http_seconds"]) as response:
            record["response"] = {
                "status": response.status,
                "body": json.load(response),
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            content = json.loads(raw)
        except ValueError:
            content = raw
        record["response"] = {"status": exc.code, "body": content}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        record.update(outcome="unknown", error_type=type(exc).__name__)
    with destination.open("x") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    return record


if __name__ == "__main__":
    value = execute(Path(sys.argv[1]), sys.argv[2], json.load(sys.stdin))
    print(json.dumps(value, ensure_ascii=False))
