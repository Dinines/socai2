"""Display-only links from saved identities; no execution or network access."""
from __future__ import annotations

from typing import Literal
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from uuid import UUID

from acceptance_contract import Control, Text
from acceptance_materials import MaterialError, control, read_json
from pydantic import field_validator


class ReportConfig(Control):
    schema_version: Literal["socai2.acceptance-report-config.v1"]
    source_environment_label: Text
    workbench_environment_label: Text
    workbench_url: Text

    @field_validator("workbench_url")
    @classmethod
    def page_address(cls, value):
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or "?" in value or "#" in value
                or any(c.isspace() or c in '<>"\\' for c in value)):
            raise ValueError("use an HTTP(S) page URL without credentials, query or fragment")
        _ = parsed.port
        return value


def load_report_config(path):
    return control(ReportConfig, read_json(path), "report configuration") if path else None


def add_workbench_links(report, config):
    report["workbench"] = {"configured": config is not None}
    if config is None:
        return
    if config.source_environment_label != report["environment"]["label"]:
        raise MaterialError("report configuration does not match the saved session environment")
    report["workbench"].update(config.model_dump())
    for subject in report["subjects"]:
        if subject["kind"] not in {"case", "incident", "alert"} or str(UUID(subject["id"])) != subject["id"]:
            raise MaterialError("cannot link an invalid saved subject identity")
        for run in subject["rounds"]:
            if str(UUID(run["run_id"])) != run["run_id"]:
                raise MaterialError("cannot link an invalid saved Run identity")
            query = urlencode({"subject_type": subject["kind"], "subject_id": subject["id"],
                               "run_id": run["run_id"], "environment": config.workbench_environment_label})
            address = urlsplit(config.workbench_url)
            run["viewer_url"] = urlunsplit((address.scheme, address.netloc, quote(address.path, safe="/%"), query, ""))
