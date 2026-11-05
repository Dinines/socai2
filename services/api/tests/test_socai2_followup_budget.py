"""Real failed synthetic C6 input rebuilt locally; no model or DB calls."""
import asyncio
import json

from rebuild_socai2_followup_wire_20261105 import DIRECTORY, rebuild


def test_required_plan_and_facts_fit_original_budget_after_prompt_consolidation():
    before = json.loads((DIRECTORY / "wire-before.json").read_text("utf-8"))
    current = asyncio.run(rebuild())
    assert not before["fits"] and current["fits"]
    assert current["byte_limit"] == before["byte_limit"] == 17744
    assert current["body"]["text"] == before["body"]["text"]
    assert current["body"]["max_output_tokens"] == before["body"]["max_output_tokens"] == 3000
    assert current["visible_fields"] == before["visible_fields"]
    assert current["prepared"]["source_map"] == before["prepared"]["source_map"]
    old_data = json.loads(before["body"]["input"][1]["content"])
    new_data = json.loads(current["body"]["input"][1]["content"])
    # More optional entries fit the shorter system message before final wire
    # trimming, so only the reason counts for their omission may differ.
    assert {k: v for k, v in old_data.items() if k != "omission_counts"} == {
        k: v for k, v in new_data.items() if k != "omission_counts"}
    assert {f["value"]["execution_plan_index"] for f in current["visible_fields"]
        if "execution_plan_index" in f["value"]} == {0, 1, 2, 3}
