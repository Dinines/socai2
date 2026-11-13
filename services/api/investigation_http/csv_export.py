"""CSV representation of existing public list fields; no SQL or workflow calls."""
import csv
import io
import json
from datetime import UTC, datetime

from fastapi import HTTPException, Response

from investigation_http.contracts import AlertFacts, CaseView, IncidentFacts

MODELS = {"alerts": ("facts", AlertFacts), "incidents": ("facts", IncidentFacts), "cases": ("case", CaseView)}
DERIVED = ("member_count", "first_activity_at", "last_activity_at", "severity_auto", "severity_effective", "severity_source")
ALLOWED = {kind: tuple(prefix + "." + name for name in model.model_fields)
    + (("member_count", "open_task_count") if kind == "cases" else ("owner_name",))
    + (tuple("derived." + name for name in DERIVED) if kind == "incidents" else ())
    for kind, (prefix, model) in MODELS.items()}
DEFAULTS = {
    "alerts": ("facts.id", "facts.title", "facts.severity", "facts.event_time", "facts.handling_status",
        "facts.category", "facts.original_vendor", "facts.connector_type", "facts.source_namespace",
        "facts.owner_id", "owner_name", "facts.assignment_state", "facts.tags", "facts.business_updated_at"),
    "incidents": ("facts.id", "facts.title", "derived.severity_effective", "derived.severity_source",
        "derived.member_count", "derived.first_activity_at", "derived.last_activity_at", "facts.handling_status",
        "facts.owner_id", "owner_name", "facts.assignment_state", "facts.tags", "facts.created_at", "facts.business_updated_at"),
    "cases": ("case.id", "case.title", "case.handling_status", "case.severity", "case.owner_id", "case.assignment_state",
        "case.classification", "case.due_at", "member_count", "open_task_count", "case.tags", "case.created_at", "case.business_updated_at"),
}


def columns_for(kind, raw):
    fields = tuple(x.strip() for x in raw.split(",")) if raw is not None else DEFAULTS[kind]
    if not fields or len(set(fields)) != len(fields) or any(x not in ALLOWED[kind] for x in fields):
        raise HTTPException(422, "export_columns_invalid")
    return fields


def validate_parameters(request, kind):
    if {"limit", "cursor", "before_id", "offset"} & request.query_params.keys():
        raise HTTPException(422, "export_pagination_not_supported")
    allowed = {"columns", "q", "severity", "handling_status", "owner_id", "assignment_state",
        "time_from", "time_to", "sort_by", "sort_order"}
    if kind == "cases":
        allowed |= {"metric", "classification"}
    if set(request.query_params) - allowed:
        raise HTTPException(422, "export_query_parameter_not_supported")


def cell(value):
    if value is None:
        return "\\N"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, dict, bool)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    value = str(value)
    if value.startswith("\\"):
        value = "\\" + value
    if value.startswith(("'", "\t", "\r", "\n")) or value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        value = "'" + value
    return value


def response(kind, fields, result):
    data = bytearray(b"\xef\xbb\xbf")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")

    def append(values):
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow(values)
        encoded = buffer.getvalue().encode("utf-8")
        if len(data) + len(encoded) > result.max_bytes:
            raise HTTPException(413, "export_size_limit_exceeded")
        data.extend(encoded)

    append(fields)
    for row in result.rows:
        values = []
        for path in fields:
            value = row
            for part in path.split("."):
                value = value[part]
            values.append(cell(value))
        append(values)
    stamp = result.observed_at.astimezone(UTC)
    return Response(bytes(data), media_type="text/csv", headers={
        "Content-Disposition": f'attachment; filename="{kind}-{stamp:%Y%m%dT%H%M%SZ}.csv"',
        "X-Export-Count": str(len(result.rows)),
        "X-Export-Observed-At": stamp.isoformat(),
        "X-Export-Schema": "socai2.list-export.v1",
    })
