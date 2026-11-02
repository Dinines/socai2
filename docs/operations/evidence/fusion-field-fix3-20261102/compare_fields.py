"""Same synthetic inputs, committed function bodies vs current workspace.

Uses current installed dependencies/models for both; not a deployed baseline.
No services, database writes, models or investigation Runs are invoked.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import types
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/fusion/tests"))
from app.models.alert import FusedAlert, FusionDecision
from app.services import alert_sink, detection_engine, lake_writer, promoter, windowed_detection
from test_field_alignment_preservation import message
from test_windowed_detection import _FakeRedis


def baseline(name):
    relative = f"services/fusion/app/services/{name}.py"
    source = subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", "show", f"b400fd0:{relative}"], cwd=ROOT).decode()
    module = types.ModuleType(f"baseline_{name}")
    module.__file__ = relative
    sys.modules[module.__name__] = module
    exec(compile(source, relative, "exec"), module.__dict__)
    return module


def alert_view(alert):
    return {key: getattr(alert, key) for key in ("event_time", "hostname", "dst_ip", "rule_id", "mitre_tactics", "mitre_techniques")}


def parsed(text):
    try:
        json.loads(text)
        return True
    except ValueError:
        return False


old = {name: baseline(name) for name in ("promoter", "detection_engine", "windowed_detection", "lake_writer", "alert_sink")}
payload = message()
saved = copy.deepcopy(payload)
hit_args = ("local-rule", "Rule", "high", "not-a-tactic", ["T1059"])
old_hit = old["detection_engine"].DetectionHit(*hit_args)
hit = detection_engine.DetectionHit(*hit_args, tactics=["execution"])
before_alerts = [old["promoter"].promote_normalized_event(payload),
                 old["detection_engine"].DetectionEngine(rules=[]).build_alert(payload, old_hit),
                 old["windowed_detection"].WindowedDetectionEngine(_FakeRedis(), rules=(), sequences=()).build_alert(payload, old_hit)]
after_alerts = [promoter.promote_normalized_event(payload),
                detection_engine.DetectionEngine(rules=[]).build_alert(payload, hit),
                windowed_detection.WindowedDetectionEngine(_FakeRedis(), rules=(), sequences=()).build_alert(payload, hit)]
rows = [{"case": origin, "before": alert_view(before), "after": alert_view(after)}
        for origin, before, after in zip(("promotion", "rule", "window"), before_alerts, after_alerts)]
assert before_alerts[1].event_time is None and before_alerts[2].hostname is None
assert all(item.event_time == after_alerts[0].event_time and item.hostname == "observed-host" for item in after_alerts)
assert payload == saved

material = copy.deepcopy(payload)
material["activity"] = {"action": "allow", "outcome": "success"}
material["ocsf_event"]["file"] = {"fingerprints": [{"algorithm": "MD5", "value": "a" * 32}, {"algorithm": "SHA256", "value": "b" * 64}]}
before, after = old["lake_writer"].event_to_row(material), lake_writer.event_to_row(material)
rows.append({"case": "lake_activity_hash_and_raw", "before": {"action": before["action"], "hash_sha256": before["hash_sha256"], "raw_valid_json": parsed(before["raw_payload"])},
             "after": {"action": after["action"], "hash_sha256": after["hash_sha256"], "raw_valid_json": parsed(after["raw_payload"])}})
assert after["action"] == "allow" and after["hash_sha256"] == "b" * 64 and parsed(after["raw_payload"])
assert before["action"] == "" and before["hash_sha256"] == "a" * 32 and not parsed(before["raw_payload"])

material["ocsf_event"]["raw_data"] = json.dumps({"large": "abc" * 100000})
before, after = old["lake_writer"].event_to_row(material), lake_writer.event_to_row(material)
rows.append({"case": "bounded_material", "before": {key: {"valid_json": parsed(before[key]), "bytes": len(before[key].encode())} for key in ("raw_payload", "ocsf_json")},
             "after": {key: {"valid_json": parsed(after[key]), "bytes": len(after[key].encode()), "truncated": json.loads(after[key])["_socai2_storage"]["truncated"]} for key in ("raw_payload", "ocsf_json")}})
assert all(not parsed(before[key]) and parsed(after[key]) for key in ("raw_payload", "ocsf_json"))

fused = FusedAlert(id=UUID(int=800), tenant_id=payload["tenant_id"], alert=after_alerts[0], fusion_decision=FusionDecision.NEW_INCIDENT)
before, after = old["alert_sink"]._insert_args(fused), alert_sink._insert_args(fused)
rows.append({"case": "uncomputed_confidence", "before": {"score": before[11], "label": before[12]},
             "after": {"score": after[11], "label": after[12], "status": json.loads(after[-1])["socai2_fusion"]["confidence_status"]}})
assert before[11] == 50 and after[11] is None
result = {"baseline": "b400fd0 function bodies with current local dependencies", "current": "workspace includes batches 1-3", "synthetic": True,
          "live_services": 0, "cases": rows}
Path(__file__).with_name("before-after.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
print(f"{len(rows)} same-input comparisons passed; no live calls")
