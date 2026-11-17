"""C3 selection over the shared strict lexical reader; no repaired JSON."""
from .baseline_analysis_contract import AnalysisRejected
from .closed_json_units import read_units as selected_units
from .runtime_policy import C3_SECTIONS as SECTIONS


def read_units(content):
    value = selected_units(content, fields=(("summary",),),
        arrays=tuple((name,) for name in SECTIONS if name != "summary"))
    value["closed_sections"] = [name.removeprefix("$.") for name in value["closed_sections"]]
    for key in ("retained", "value_spans"):
        value[key] = {name.removeprefix("$."): item for name, item in value[key].items()}
    return value


def read_sections(content):
    """Section-only inspection of the same reader for existing stored C3 fixtures."""
    value = read_units(content)
    if value["invalid_units"] or not value["retained"]:
        raise AnalysisRejected(value["reasons"][0] if value["reasons"] else "c3_completion_no_reliable_sections")
    missing = [key for key in SECTIONS if key not in value["retained"]]
    return {"retained": value["retained"], "missing": missing, "value_spans": value["value_spans"],
            "outer_closed": value["parse_state"] == "complete_json", "closing_delimiter_only": not missing and value["truncated"]}
