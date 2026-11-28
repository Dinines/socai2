"""Synthetic 3c inputs shared by direct unit and native-driver database checks."""

import json
from copy import deepcopy


def event(**overrides):
    body = {
        "metadata": {"uid": "opaque/record:0", "version": "1.9.0"},
        "class_uid": 4001, "category_uid": 4, "activity_id": 1, "type_uid": 400101,
        "severity_id": 1, "time": 1000, "is_alert": False,
        "device": {"hostname": "sensor.example", "name": "display label", "ip": "192.0.2.1"},
        "src_endpoint": {"hostname": "source.example", "ip": "198.51.100.1", "port": 0},
        "dst_endpoint": {"hostname": "destination.example", "ip": "2001:db8::2", "port": 443},
        "connection_info": {"protocol_name": "TCP"},
        "actor": {"user": {"name": "actor-user"}, "process": {"name": "actor-process"}},
        "file": {"path": "/tmp/sample", "fingerprints": [{"algorithm_id": 3, "value": "a" * 64}]},
        "attacks": [{"technique": {"uid": "T1003"}, "tactic": {"uid": "TA0006"}}],
        "raw_data": False,
    }
    body.update(deepcopy(overrides))
    return body


def encoded(body):
    return json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")


def database_cases():
    normal = event()
    large = event(metadata={"uid": "opaque/large", "version": "1.9.0"},
                  raw_data="原始正文\x00\n" * 14000, extension={"unknown": "完整扩展" * 30000},
                  _socai2_storage={"upstream_field": "must stay unchanged"})
    partial = event(class_uid=0, category_uid=0, activity_id=0, type_uid=0, is_alert=None,
                    unmapped={"spirithub": {"mapping_status": "partial", "partial_fields": {
                        "class_uid": 4001, "is_alert": True, "device": {"hostname": "partial-device.example"}}}})
    partial.pop("device")
    missing = event(metadata={"uid": "opaque/no-time", "version": "1.9.0"})
    missing.pop("time")
    no_id = event(metadata={"version": "1.9.0"})
    precision = encoded(event(raw_data="PRECISE", counter=9007199254740993)).replace(
        b'"PRECISE"', b'{"long":9007199254740993,"decimal":123456789012345678901234567890.010,"flag":false,"null":null}')
    return [
        ("normal", encoded(normal)), ("large", encoded(large)), ("partial", encoded(partial)),
        ("missing_time", encoded(missing)), ("missing_id", encoded(no_id)), ("precision", precision),
        ("auth", encoded(event(class_uid=3002, user={"name": "target-user"}))),
        ("process", encoded(event(class_uid=1007, process={"name": "target-process"}))),
        ("unknown_class", encoded(event(class_uid=65001))),
        ("class_zero", encoded(event(class_uid=0))),
        ("negative_ms", encoded(event(time=-1))),
        ("decimal_time", encoded(event(time=1000.0))),
        ("decimal_class", encoded(event(class_uid=4001.0))),
        ("minimum_time", encoded(event(time=-2208988800000))),
        ("maximum_time", encoded(event(time=10413791999999))),
        ("outside_time", encoded(event(time=10413792000000))),
        ("non_object", b'[false,0,null]'), ("duplicate_key", b'{"x":1,"x":2}'),
        ("invalid_utf8", b'\xff\x00\xfe'), ("tombstone", None), ("empty", b''),
    ]
