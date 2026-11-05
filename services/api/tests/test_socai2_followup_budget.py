"""Old 24k frozen budget remains fixed when queried evidence becomes required."""
import asyncio
import json

from rebuild_socai2_followup_wire_20261105 import DIRECTORY, rebuild


def test_original_budget_is_not_raised_to_fit_new_required_query_evidence():
    before = json.loads((DIRECTORY / "wire-before.json").read_text("utf-8"))
    current = asyncio.run(rebuild())
    assert not before["fits"] and not current["fits"]
    assert current["byte_limit"] == before["byte_limit"] == 17744
    assert current["body"]["max_output_tokens"] == before["body"]["max_output_tokens"] == 3000
    # All formerly mandatory source/value pairs remain. The new endpoint
    # minimum must not be dropped merely to reproduce the old tight fit.
    old_map, new_map = before["prepared"]["source_map"], current["prepared"]["source_map"]
    assert {(json.dumps(s["ref"], sort_keys=True), s["visible_value_sha256"]) for s in old_map.values() if s["required"]} <= {
        (json.dumps(s["ref"], sort_keys=True), s["visible_value_sha256"]) for s in new_map.values()}
    assert {f["value"]["name"] for f in current["visible_fields"] if f["value"].get("record_key", "").startswith("Q")} == {"dest_ip", "dst_port"}
    assert current["after_bytes"] > current["byte_limit"]
    assert {f["value"]["execution_plan_index"] for f in current["visible_fields"]
        if "execution_plan_index" in f["value"]} == {0, 1, 2, 3}
