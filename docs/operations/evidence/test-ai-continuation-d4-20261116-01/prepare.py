"""Independent A/I prefix fixtures from frozen complete real responses.

Only stdlib decodes the complete mother; no product parser or service is called.
The catalog includes nested values so later stage-specific grouping can select
real spans without redefining the oracle from the receiver's own results.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def catalog(text):
    """Locate complete JSON values, including object/array children, in the mother."""
    decoder, found = json.JSONDecoder(), []

    def skip(pos):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        return pos

    def walk(path, start):
        value, end = decoder.raw_decode(text, start)
        kind = "object" if isinstance(value, dict) else "array" if isinstance(value, list) else (
            "string" if isinstance(value, str) else "literal")
        # Numbers/null/booleans need a visible delimiter. A partial token cannot
        # be admitted just because the complete mother tells us how it ends.
        following = skip(end)
        closure = following + 1 if kind == "literal" else end
        if kind == "literal":
            assert text[following] in ",]}"
        found.append({"path": path, "kind": kind, "value": value, "value_span": [start, end],
                      "value_sha256": sha(text[start:end]), "closure_offset": closure})
        if isinstance(value, dict):
            pos = skip(start + 1)
            for key, expected in value.items():
                name, pos = decoder.raw_decode(text, pos)
                assert name == key
                pos = skip(pos)
                assert text[pos] == ":"
                pos = skip(pos + 1)
                assert decoder.raw_decode(text, pos)[0] == expected
                pos = skip(walk(path + "." + key, pos))
                if text[pos] == ",":
                    pos = skip(pos + 1)
        elif isinstance(value, list):
            pos = skip(start + 1)
            for index, expected in enumerate(value):
                assert decoder.raw_decode(text, pos)[0] == expected
                pos = skip(walk(path + f"[{index}]", pos))
                if text[pos] == ",":
                    pos = skip(pos + 1)
        return end

    assert isinstance(json.loads(text), dict)
    walk("$", skip(0))
    return found


def candidates(stage, spans):
    if stage == "A":
        fields = {"$.verdict", "$.confidence", "$.rationale", "$.evidence_ids"}
        arrays = ("$.recommendations[",)
    else:
        fields = {"$.diagnosis.summary", "$.diagnosis.conclusion", "$.diagnosis.limitations", "$.diagnosis.source_ids"}
        arrays = ("$.members[", "$.findings[", "$.open_questions[")
    return [s for s in spans if s["path"] in fields or (
        s["path"].startswith(arrays) and s["path"].endswith("]") and s["path"].count("[") == 1
        and s["kind"] == "object")]


def prepare(out):
    cfg = json.loads((HERE / "fixture-config.json").read_text())
    source = ROOT / cfg["source_snapshot"]
    assert sha(source.read_bytes()) == cfg["source_snapshot_sha256"]
    rows = json.loads(source.read_text())["rows"]
    artifacts = {a["id"]: a for a in rows["artifacts"]}
    out.mkdir(exist_ok=False)
    manifests = {}
    for stage, run_id in cfg["runs"].items():
        folder = out / stage
        folder.mkdir()
        run = next(r for r in rows["runs"] if r["id"] == run_id)
        models = [s for s in rows["run_steps"] if s["run_id"] == run_id and s["kind"] == "model"]
        assert len(models) == 1 and models[0]["state"] == "completed"
        model = models[0]
        request, response = (artifacts[model[k]] for k in ("input_artifact_id", "output_artifact_id"))
        raw = response["content_json"]["raw"]
        originals = [a for a in artifacts.values() if a["run_id"] == run_id and a["kind"] == "source_snapshot"
                     and (a["content_json"] or {}).get("raw") == raw]
        assert len(originals) == 1
        original = originals[0]
        assert original["content_json"]["request_artifact_id"] == request["id"]
        assert raw["choices"][0]["finish_reason"] == "stop"
        text = raw["choices"][0]["message"]["content"]
        spans = catalog(text)
        by_path = {s["path"]: s for s in spans}
        selected = candidates(stage, spans)
        points = [("empty", 0, "stop"), ("complete-stop", len(text), "stop"),
                  ("complete-length", len(text), "length"),
                  ("root-close-missing", len(text.rstrip()) - 1, "length")]
        if stage == "A":
            points += [("verdict-only", by_path["$.verdict"]["value_span"][1], "length"),
                       ("rationale-closed", by_path["$.rationale"]["value_span"][1], "length"),
                       ("recommendation-1-closed-2-partial", sum(by_path["$.recommendations[1]"]["value_span"]) // 2, "length")]
        else:
            points += [("member-1-closed-2-partial", sum(by_path["$.members[1]"]["value_span"]) // 2, "length"),
                       ("finding-closed-question-partial", sum(by_path["$.open_questions[0]"]["value_span"]) // 2, "length"),
                       ("diagnosis-summary-closed-conclusion-partial", sum(by_path["$.diagnosis.conclusion"]["value_span"]) // 2, "length")]
        used = {cut for _, cut, _ in points}
        random_points = random.Random(cfg["seed"]).sample([i for i in range(1, len(text)) if i not in used],
                                                        cfg["random_points_per_stage"])
        points += [(f"random-{i}", cut, "length") for i, cut in enumerate(random_points, 1)]
        (folder / "mother.txt").write_text(text)
        save(folder / "value-catalog.json", spans)
        save(folder / "frozen-source.json", {"run": run, "model_step": model,
            "input_snapshot": artifacts[run["input_artifact_id"]], "request": request,
            "response": response, "original": original, "historical_only": True})
        variants = []
        for name, cut, finish in points:
            fragment = text[:cut]
            closed = [s for s in selected if s["closure_offset"] <= cut]
            missing = [s["path"] for s in selected if s["closure_offset"] > cut]
            (folder / (name + ".txt")).write_text(fragment)
            expected = {"stage": stage, "name": name, "cut_offset": cut, "offset_unit": "Unicode_code_point",
                "fragment_sha256": sha(fragment), "finish_reason": finish,
                "complete_candidate_units": closed, "incomplete_or_unseen_paths": missing,
                "source": "complete real mother and original value spans; no product recovery parser",
                "business_admission": "stage11_design_section_11_1_frozen_real_mother_only",
                "forbidden": ["invent missing original values", "enlarge declared or actual analyzed scope",
                              "treat scalar verdict without dependencies as usable triage",
                              "turn incomplete suggestions into actions"]}
            paths = {s["path"] for s in closed}
            core = ({"$.verdict", "$.confidence", "$.rationale", "$.evidence_ids"} if stage == "A" else
                    {"$.diagnosis.summary", "$.diagnosis.conclusion", "$.diagnosis.limitations", "$.diagnosis.source_ids"})
            members = [] if stage == "A" else [s["value"]["alert_ref"] for s in closed
                if s["path"].startswith("$.members[")]
            all_members = [] if stage == "A" else [m["alert_ref"] for m in json.loads(text)["members"]]
            expected.update(expected_usable_result=core <= paths and set(members) == set(all_members),
                expected_original_member_aliases=members, frozen_member_aliases=all_members,
                expected_dispatch_paths=[],
                expected_quality="not_checked",
                expected_delivery="none" if not closed else "complete" if not missing else "partial")
            if stage == "I" and name == "member-1-closed-2-partial":
                assert [s["path"] for s in closed] == ["$.members[0]"]
                expected["must_not_claim_analyzed_aliases"] = [m["alert_ref"] for m in json.loads(text)["members"][1:]]
            if stage == "A" and name == "verdict-only":
                expected["usable_triage"] = False
            if not fragment:
                expected.update(delivery="none", usable_conclusion=False)
            save(folder / (name + ".expected.json"), expected)
            variants.append({k: expected[k] for k in ("name", "cut_offset", "finish_reason", "fragment_sha256")})
        manifest = {"stage": stage, "status": "prepared_not_product_tested", "source_snapshot": cfg["source_snapshot"],
            "source_snapshot_sha256": cfg["source_snapshot_sha256"], "run_id": run_id,
            "request_artifact_id": request["id"], "response_artifact_id": response["id"],
            "original_artifact_id": original["id"], "original_content_path": "$.raw.choices[0].message.content",
            "mother_sha256": sha(text), "mother_characters": len(text), "catalog_values": len(spans),
            "candidate_units": len(selected), "seed": cfg["seed"], "random_points": random_points,
            "historical_output_tokens": request["content_json"]["body"]["max_tokens"],
            "current_config_hashes": {p: sha((ROOT / p).read_bytes()) for p in [cfg["current_policy"], *cfg["current_profiles"]]},
            "variants": variants, "model_calls": 0, "database_calls": 0, "product_parser_calls": 0}
        save(folder / "manifest.json", manifest)
        manifests[stage] = manifest
    assert sha(source.read_bytes()) == cfg["source_snapshot_sha256"]
    save(out / "manifest.json", {"status": "prepared_not_product_tested", "stages": manifests,
                                "source_unchanged": True, "model_calls": 0, "database_calls": 0})
    print(json.dumps({s: {k: v[k] for k in ("mother_characters", "candidate_units", "random_points")}
                      for s, v in manifests.items()}))


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--output", type=Path, required=True)
    prepare(cli.parse_args().output)
