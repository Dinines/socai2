"""Read a frozen Kafka range without a group or commits; keep reports private."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import ssl
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

MISSING = object()


def at_path(value, path):
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return MISSING
        value = value[key]
    return value


def kind(value):
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def numeric_bucket(value):
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    # Do not collapse boolean values or strings into valid OCSF integer IDs.
    return str(value) if type(value) is int and value >= 0 else "invalid"


def alert_bucket(value):
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if type(value) is bool:
        return "true" if value else "false"
    return "invalid"


def reject_constant(_value):
    raise ValueError("non_finite_json")


class Profile:
    """Counts only; no event text, entity values, keys or record samples."""

    def __init__(self, field_paths):
        self.field_paths = field_paths
        self.records = 0
        self.message_kinds = Counter()
        self.classes = {}

    def add(self, raw):
        self.records += 1
        if raw is None:
            self.message_kinds["tombstone"] += 1
            return
        try:
            value = json.loads(raw, parse_constant=reject_constant)
        except (ValueError, UnicodeError, RecursionError):
            self.message_kinds["invalid_json"] += 1
            return
        if not isinstance(value, dict):
            self.message_kinds["non_object"] += 1
            return
        if "ocsf_event" in value:
            if not isinstance(value["ocsf_event"], dict):
                self.message_kinds["invalid_envelope"] += 1
                return
            event = value["ocsf_event"]
            self.message_kinds["envelope"] += 1
        else:
            event = value
            self.message_kinds["bare_object"] += 1
        key = numeric_bucket(event.get("class_uid", MISSING))
        row = self.classes.setdefault(key, {
            "records": 0, "category_uid": Counter(), "activity_id": Counter(),
            "type_uid": Counter(), "is_alert": Counter(),
            "original_class_uid": Counter(), "partial_fields": Counter(),
            "fields": {path: Counter() for path in self.field_paths},
        })
        row["records"] += 1
        for name in ("category_uid", "activity_id", "type_uid"):
            row[name][numeric_bucket(event.get(name, MISSING))] += 1
        row["is_alert"][alert_bucket(event.get("is_alert", MISSING))] += 1
        row["original_class_uid"][numeric_bucket(
            at_path(event, "unmapped.spirithub.classification.class_uid"))] += 1
        row["partial_fields"][kind(at_path(event, "unmapped.spirithub.partial_fields"))] += 1
        for path in self.field_paths:
            value = at_path(event, path)
            bucket = kind(value)
            if isinstance(value, (str, list, dict)) and len(value) == 0:
                bucket += "_empty"
            row["fields"][path][bucket] += 1

    def report(self):
        return {"records": self.records, "message_kinds": self.message_kinds,
                "classes": self.classes}


def client_options(config):
    kafka = config["kafka"]
    protocol = kafka["security_protocol"]
    if protocol not in {"PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"}:
        raise ValueError("invalid_security_protocol")
    options = {
        "bootstrap_servers": kafka["bootstrap_servers"],
        "client_id": kafka["client_id"], "security_protocol": protocol,
        "group_id": None, "enable_auto_commit": False, "auto_offset_reset": "none",
        "isolation_level": kafka["isolation_level"],
        "request_timeout_ms": config["scan"]["request_timeout_ms"],
        "fetch_max_bytes": config["scan"]["fetch_max_bytes"],
        "max_partition_fetch_bytes": config["scan"]["max_partition_fetch_bytes"],
    }
    if "SSL" in protocol:
        tls = kafka["tls"]
        context = ssl.create_default_context(cafile=tls["ca_file"])
        if tls.get("cert_file"):
            context.load_cert_chain(tls["cert_file"], tls["key_file"])
        options["ssl_context"] = context
    if protocol.startswith("SASL"):
        credentials = json.loads(Path(kafka["credentials_file"]).read_text())
        options.update(sasl_mechanism=kafka["sasl_mechanism"],
                       sasl_plain_username=credentials["username"],
                       sasl_plain_password=credentials["password"])
    return options


def available_partitions(rows, topics):
    return {row["topic"]: [p["partition"] for p in row["partitions"]]
            for row in rows if row["topic"] in topics and row["error_code"] == 0
            and all(p["error_code"] == 0 for p in row["partitions"])}


async def scan_topic(consumer, topic, entry, config, partition_type, partitions):
    if not partitions:
        raise ValueError("topic_has_no_partitions")
    tps = [partition_type(topic, p) for p in sorted(partitions)]
    starts = await consumer.beginning_offsets(tps)
    ends = await consumer.end_offsets(tps)
    consumer.assign(tps)
    for tp in tps:
        consumer.seek(tp, starts[tp])
    entry["partitions"] = {
        str(tp.partition): {"start_offset": starts[tp], "end_offset_exclusive": ends[tp],
                            "next_offset": starts[tp], "records": 0}
        for tp in tps
    }
    profile = Profile(config["field_paths"])
    # Keep the live object attached so a timeout still saves the partial counts.
    entry["profile"] = profile.report()
    pending = {tp for tp in tps if starts[tp] < ends[tp]}
    while pending:
        batches = await consumer.getmany(
            *sorted(pending, key=lambda tp: tp.partition),
            timeout_ms=config["scan"]["poll_timeout_ms"],
            max_records=config["scan"]["max_records_per_poll"],
        )
        for tp, records in batches.items():
            if tp not in pending:
                continue
            part = entry["partitions"][str(tp.partition)]
            for record in records:
                if starts[tp] <= record.offset < ends[tp]:
                    profile.add(record.value)
                    part["records"] += 1
                    part["next_offset"] = record.offset + 1
            entry["profile"] = profile.report()
        for tp in list(pending):
            # Offsets can have gaps: message count must not equal offset span.
            position = min(await consumer.position(tp), ends[tp])
            entry["partitions"][str(tp.partition)]["next_offset"] = position
            if position >= ends[tp]:
                pending.remove(tp)
    entry["status"] = "complete"


async def inventory(config, consumer, partition_type, read_metadata):
    report = {"schema_version": "socai2.ocsf-type-inventory.v1",
              "profile": config["profile"], "started_at": now(),
              "scope": "retained_records_in_frozen_offset_ranges",
              "group_id": None, "offset_commits": False,
              "topics": {}, "status": "incomplete"}
    try:
        await consumer.start()
        # topics() does not fill the consumer's partition cache. Describe all
        # metadata explicitly; requesting no specific name cannot create a topic.
        metadata = await read_metadata()
        for topic in config["topics"]:
            entry = {"status": "incomplete", "partitions": {}}
            report["topics"][topic] = entry
            try:
                if topic not in metadata:
                    raise ValueError("configured_topic_missing")
                await asyncio.wait_for(
                    scan_topic(consumer, topic, entry, config, partition_type,
                               metadata[topic]),
                    timeout=config["scan"]["max_duration_seconds_per_topic"],
                )
            except Exception as exc:  # noqa: BLE001 - save failure type without private values
                entry["error_type"] = type(exc).__name__
        report["status"] = ("complete" if all(
            entry["status"] == "complete" for entry in report["topics"].values()
        ) else "incomplete")
    except Exception as exc:  # noqa: BLE001 - save failure type without private values
        report["error_type"] = type(exc).__name__
    finally:
        try:
            await consumer.stop()
        except Exception as exc:  # noqa: BLE001 - save failure type without private values
            report["close_error_type"] = type(exc).__name__
            report["status"] = "incomplete"
    report["finished_at"] = now()
    return report


def now():
    return datetime.now(timezone.utc).isoformat()


def write_report(path, report):
    # Exclusive create preserves completed batches; no raw data goes to stdout.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    config = json.loads(args.config.read_text())
    if (not config["profile"] or not config["topics"]
            or len(set(config["topics"])) != len(config["topics"])
            or len(set(config["field_paths"])) != len(config["field_paths"])
            or any(type(v) is not int or v <= 0 for v in config["scan"].values())):
        raise ValueError("invalid_profile")
    output = Path(config["report_path"])
    if output.exists():
        raise FileExistsError("report_already_exists")
    from aiokafka import AIOKafkaConsumer, TopicPartition
    from aiokafka.admin import AIOKafkaAdminClient

    async def run():
        options = client_options(config)
        consumer = AIOKafkaConsumer(**options)

        async def read_metadata():
            names = {"bootstrap_servers", "client_id", "security_protocol", "ssl_context",
                     "sasl_mechanism", "sasl_plain_username", "sasl_plain_password",
                     "request_timeout_ms"}
            admin = AIOKafkaAdminClient(**{k: v for k, v in options.items() if k in names})
            try:
                await admin.start()
                rows = await admin.describe_topics()
                return available_partitions(rows, config["topics"])
            finally:
                await admin.close()

        return await inventory(config, consumer, TopicPartition, read_metadata)

    report = asyncio.run(run())
    write_report(output, report)
    # Verify saved bytes in the controlled environment without printing them.
    if json.loads(output.read_text()) != report:
        raise ValueError("report_readback_mismatch")
    return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # noqa: BLE001 - do not print broker exception values
        # Never stringify a broker exception: it may carry private values.
        print("inventory_failed:" + type(error).__name__)
        raise SystemExit(2)
