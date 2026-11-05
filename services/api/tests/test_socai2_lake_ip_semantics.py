"""CH IPv6 storage encoding must not fabricate evidence conflicts."""
import pytest
from app.socai2.baseline_evidence_tools import row_projection


@pytest.mark.parametrize(("source", "stored"), [
    ("198.51.100.30", "::ffff:198.51.100.30"),
    ("198.51.100.30", "::ffff:c633:641e"),
    ("2001:db8::1", "2001:0db8:0000:0000:0000:0000:0000:0001"),
])
def test_equivalent_ip_encodings_keep_original_without_conflict(source, stored):
    raw = {"class_uid": 4001, "src_endpoint": {"ip": source}, "dst_endpoint": {"ip": source}}
    row = {"ocsf_json": raw, "source_ip": stored, "dest_ip": stored}
    projected = row_projection(row)
    fields = [f for f in projected["fields"] if f["name"] in {"source_ip", "dest_ip"}]
    assert len(fields) == 2 and all(not f["conflict"] for f in fields)
    assert all(f["value"] == source and f["source_path"].startswith("$.ocsf_json.") for f in fields)
    assert row["dest_ip"] == stored and raw["dst_endpoint"]["ip"] == source


@pytest.mark.parametrize("stored", ["::ffff:198.51.100.31", "::198.51.100.30", "2001:db8::1"])
def test_different_addresses_keep_both_values_and_conflict(stored):
    row = {"ocsf_json": {"class_uid": 4001, "dst_endpoint": {"ip": "198.51.100.30"}}, "dest_ip": stored}
    fields = [f for f in row_projection(row)["fields"] if f["name"] == "dest_ip"]
    assert [f["value"] for f in fields] == ["198.51.100.30", stored]
    assert all(f["conflict"] for f in fields)
    assert fields[1]["source_path"] == "$.dest_ip"
