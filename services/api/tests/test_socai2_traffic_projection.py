"""Counter visibility and source semantics, independent of real model outputs."""
import pytest
from app.socai2.baseline_evidence_tools import row_projection
from app.socai2.baseline_semantics import project


def test_traffic_direction_zero_and_exact_source_paths_survive_tool_projection():
    traffic = {"bytes": 1200, "bytes_in": 0, "bytes_out": 1200,
        "packets": 3, "packets_in": 0, "packets_out": 3}
    view = row_projection({"ocsf_json": {"class_uid": 4001, "traffic": traffic}})
    actual = {f["name"]: (f["value"], f["source_path"]) for f in view["fields"]}
    for name, value in traffic.items():
        assert actual["network_" + name] == (value, "$.ocsf_json.traffic." + name)
    assert any("destination_to_source" in text for text in view["limitations"])
    assert not any("network_" in f["name"] for f in project({"class_uid": 1007})["fields"])
    assert not any("traffic" in o["source_path"] for o in project({"class_uid": 1007})["omissions"])


@pytest.mark.parametrize("bad", [-1, True, 1.5, "100", 2**63])
def test_invalid_counters_are_omitted_not_coerced(bad):
    view = project({"class_uid": 4001, "traffic": {"bytes_out": bad}})
    assert not any(f["name"] == "network_bytes_out" for f in view["fields"])
    assert any(o["source_path"].endswith("traffic.bytes_out") for o in view["omissions"])
