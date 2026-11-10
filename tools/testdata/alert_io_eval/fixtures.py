"""Frozen recorded inputs plus six new instances of labelled synthetic templates."""
import copy
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from app.socai2 import alert_basic_contract as contract


def uid(batch, value):
    return str(uuid5(NAMESPACE_URL, batch + ":" + value))


def packets(root, config):
    raw = (root / config["snapshot"]).read_bytes()
    database = json.loads(raw)
    artifacts = {a["id"]: a for a in database["artifacts"]}
    actual = []
    for run in sorted((r for r in database["runs"] if r["kind"] == "alert_basic"), key=lambda r: r["started_at"]):
        request = next(a for a in database["artifacts"] if a["run_id"] == run["id"] and a["kind"] == "model_request")
        data = json.loads(request["content_json"]["body"]["messages"][1]["content"])
        actual.append({"id": f"A{len(actual)+1}", "kind": "recorded", "source_run_id": run["id"],
                       "source": artifacts[run["input_artifact_id"]]["content_json"],
                       "body": request["content_json"]["body"], "source_map": request["content_json"]["source_map"], "data": data,
                       "queries": [(a["id"], a["content_json"]) for a in database["artifacts"]
                                   if a["run_id"] == run["id"] and a["kind"] == "tool_response"]})
    assert len(actual) == 3
    corpus_path = root / config["corpus"]
    corpus = {x["id"]: x for x in json.loads(corpus_path.read_text())["decisions"]}
    answer_key, synthetic = [], []
    for index, origin in enumerate(config["corpus_cases"], 1):
        specimen = corpus[origin]
        sample = f"S{index}"
        source = copy.deepcopy(actual[0]["source"])
        member = source["members"][0]
        alert, material = member["alert"], member["material"]
        aid, mid, iid = (uid(config["batch"], sample + ":" + v) for v in ("alert", "material", "input"))
        event_time = f"2026-11-08T03:{index:02}:00+00:00"
        # Allocate fresh fixture identities/times. Do not copy labels, decisive_evidence,
        # author reasoning or expected dispositions into the model's packet.
        evidence = copy.deepcopy(specimen["evidence"])
        text = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
        event = {"time": event_time, "activity": {"action": "vendor_record"}, "raw_data": text}
        raw_event = {"event_id": uid(config["batch"], sample + ":event"), "schema_version": "v1", "ocsf_event": event,
                     "original_vendor": specimen["vendor"]}
        alert.update(id=aid, title=specimen["title"], description=None, original_vendor=specimen["vendor"],
                     event_time=event_time, event_time_source="source", severity=specimen["severity"],
                     source_alert_id=uid(config["batch"], sample + ":source"), latest_material_id=mid,
                     ingested_at=event_time, source_namespace="source:alert-io-evaluation")
        for key in ("latest_feedback_id", "latest_triage_id", "latest_explanation_id"):
            if key in alert:
                alert[key] = None
        material.update(id=mid, alert_id=aid, received_at=event_time, raw_text=text, ocsf_json=event,
                        raw_json={"raw_event": raw_event}, material_state="complete",
                        detection={"rule_id": specimen["rule_id"], "rule_name": specimen["title"],
                                   "confidence_state": "not_computed", "confidence_value": None,
                                   "tactics": [], "techniques": []},
                        enrichment={}, source_scope={"kind": "explicit_sources", "complete": True, "truncated": False})
        retained = {k: material[k] for k in ("raw_text", "raw_json", "ocsf_json", "detection", "enrichment", "source_scope")}
        retained_bytes = json.dumps(retained, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        material["sha256"] = hashlib.sha256(retained_bytes).hexdigest()
        material["retention"] = {"truncated": False, "original_size_bytes": len(retained_bytes),
                                 "retained_size_bytes": len(retained_bytes), "reason": None, "omitted_paths": []}
        member.update(objects=[], feedback=None, triage=None)
        queries = []
        for name in ("assets", "history", "threat_intel"):
            payload = {"tool_name": name, "state": "skipped", "reason": "synthetic_fixture_no_external_query",
                       "rows": None, "returned_rows": None, "truncated": False,
                       "limitations": ["synthetic_fixture_no_real_query"],
                       "actual_args": {"scope": {"alert_ids": [aid], "object_keys": [], "window_start": None, "window_end": event_time}}}
            queries.append((uid(config["batch"], sample + ":" + name), payload))
        messages, mapping, data = contract.build(source, iid, queries, execution_time=event_time)
        body = {"model": config["transport"]["expected_model"], "messages": messages,
                "max_tokens": config["output_tokens"], "temperature": config["temperature"],
                "response_format": contract.constrained_response_format(mapping)}
        assert origin not in json.dumps(body) and "expected_disposition" not in json.dumps(body)
        synthetic.append({"id": sample, "kind": "synthetic", "source": source, "queries": queries,
                          "body": body, "source_map": mapping, "data": data})
        answer_key.append({"sample": sample, "template": origin, "expected": specimen["expected_disposition"],
                           "direction": "malicious" if specimen["expected_disposition"] == "true_positive" else "non_malicious",
                           "provenance": "pre-existing hand-authored synthetic label; not production truth",
                           "decisive_evidence": specimen.get("decisive_evidence"), "family": specimen["family"]})
    return actual + synthetic, answer_key, {
        "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "synthetic_note": "New fixture IDs/timestamps, existing corpus evidence content; not claimed unseen in model training or previous unrelated evaluations."}
