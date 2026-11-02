"""Offline baseline/current comparison using synthetic received events only."""
import asyncio
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/fusion"))
from app.core.config import settings
from app.models.alert import RawAlert
from app.services.detection_engine import DetectionEngine, DetectionHit
from app.services.promoter import promote_normalized_event
from app.services.windowed_detection import WindowedDetectionEngine
from app.workers.consumer import FusionWorker


def baseline(name, path):
    source = subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", "show", f"b400fd0:{path}"], cwd=ROOT)
    module = ModuleType(name)
    module.__file__ = str(ROOT / path)
    sys.modules[name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


old_model = baseline("baseline_model", "services/fusion/app/models/alert.py")
old_promoter = baseline("baseline_promoter", "services/fusion/app/services/promoter.py")
old_detection = baseline("baseline_detection", "services/fusion/app/services/detection_engine.py")
old_window = baseline("baseline_window", "services/fusion/app/services/windowed_detection.py")
old_worker = baseline("baseline_worker", "services/fusion/app/workers/consumer.py")
tenant = UUID(int=301)


def event(identity):
    return {"event_id": identity, "tenant_id": str(tenant), "connector_id": str(UUID(int=401)),
            "ocsf_event": {"class_uid": 2001, "severity_id": 5, "message": "same finding",
                           "device": {"name": "shared"}, "metadata": {"product": {"name": "fixture"}}}}


hit = DetectionHit(rule_id="rule-1", name="same title", severity="high", category="execution", mitre=[])
builders = [
    ("promotion", old_promoter.promote_normalized_event, promote_normalized_event),
    ("rule", lambda e: old_detection.DetectionEngine(rules=[]).build_alert(e, hit),
     lambda e: DetectionEngine(rules=[]).build_alert(e, hit)),
    ("window", lambda e: old_window.WindowedDetectionEngine(None, rules=[]).build_alert(e, hit),
     lambda e: WindowedDetectionEngine(None, rules=[]).build_alert(e, hit)),
]
comparisons = []
for origin, before, after in builders:
    old_ids = [str(old_model.RawAlert.model_validate(before(event(i)).model_dump()).deterministic_id()) for i in ("event-1", "event-2")]
    new_ids = [str(after(event(i)).deterministic_id()) for i in ("event-1", "event-2")]
    replay_id = str(after(event("event-1")).deterministic_id())
    assert old_ids[0] == old_ids[1] and new_ids[0] != new_ids[1] and replay_id == new_ids[0]
    comparisons.append({"origin": origin, "baseline_ids": old_ids, "fixed_ids": new_ids, "replay_id": replay_id})

base = {"tenant_id": tenant, "source": "fixture", "title": "same"}
keys = []
for name, left, right in (("host_vs_user", {"hostname": "shared"}, {"username": "shared"}),
                           ("missing_objects", {"title": "a"}, {"title": "b"})):
    old_keys = [old_model.RawAlert(**(base | fields)).correlation_key() for fields in (left, right)]
    new_keys = [RawAlert(**(base | fields)).correlation_key() for fields in (left, right)]
    assert old_keys[0] == old_keys[1] and new_keys[0] != new_keys[1]
    keys.append({"scenario": name, "baseline_keys": old_keys, "fixed_keys": new_keys})

unchanged = {}
for version in ("legacy-v1", "source-v1"):
    payload = base | {"identity_version": version, "source_alert_id": UUID(int=311) if version == "source-v1" else None}
    old_id, new_id = old_model.RawAlert(**payload).deterministic_id(), RawAlert(**payload).deterministic_id()
    assert old_id == new_id
    unchanged[version] = str(new_id)


async def promotion_disabled(worker_type):
    worker = worker_type(SimpleNamespace())
    worker._lake = SimpleNamespace(write_event=AsyncMock(return_value=True))
    worker._detector = SimpleNamespace(evaluate_async=AsyncMock(return_value=[hit]), build_alert=lambda *args: object())
    worker._windowed = SimpleNamespace(evaluate=AsyncMock(return_value=[hit]), build_alert=lambda *args: object())
    worker.process_alert = AsyncMock()
    await worker._process_message(event("event-1"), topic=settings.kafka_topic_raw_events)
    return {"alert_calls": worker.process_alert.await_count, "lake_calls": worker._lake.write_event.await_count}


enabled = settings.event_promotion_enabled
try:
    settings.event_promotion_enabled = False
    switches = {"baseline": asyncio.run(promotion_disabled(old_worker.FusionWorker)), "fixed": asyncio.run(promotion_disabled(FusionWorker))}
finally:
    settings.event_promotion_enabled = enabled
assert switches == {"baseline": {"alert_calls": 3, "lake_calls": 1}, "fixed": {"alert_calls": 2, "lake_calls": 1}}

schema = ROOT / "services/api/app/schemas/fusion_alert.py"
spec = importlib.util.spec_from_file_location("api_mirror", schema)
mirror = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mirror
spec.loader.exec_module(mirror)
generated = promote_normalized_event(event("event-1"))
assert mirror.RawAlert.model_validate(generated.model_dump()).deterministic_id() == generated.deterministic_id()
assert schema.read_bytes() == (ROOT / "services/fusion/app/models/alert.py").read_bytes()

result = {"scope": "synthetic local builders/worker; no PG/Redis/Kafka/lake/model connections",
          "baseline": "b400fd0", "identities": comparisons, "correlation": keys,
          "unchanged_identity_contracts": unchanged, "promotion_disabled": switches, "api_schema_matches": True}
Path(__file__).with_name("before-after.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"identity_paths": len(comparisons), "correlation_cases": len(keys), "promotion_disabled": switches, "api_schema_matches": True}))
