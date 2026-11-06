"""Check branch attribution and links from the case flow to the preserved records."""
import unittest
from html.parser import HTMLParser

from processing_audit_detail import render_case_detail


class Nodes(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.ids = set()
        self.nodes = {}
        self.active = None
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.add(values["id"])
        if "flow-node" in values.get("class", "").split():
            self.active = values

    def handle_endtag(self, tag):
        if tag in {"a", "span"}:
            self.active = None

    def handle_data(self, data):
        if self.active is not None:
            self.nodes[data] = self.active


class ProcessingFlowTest(unittest.TestCase):
    def render(self, routes):
        run = {"id": "r", "kind": "baseline", "state": "completed", "delivery_state": "partial"}
        steps = [
            {"id": "graph", "run_id": "r", "stage_code": "C5", "kind": "graph", "name": "g", "seq": 1, "state": "completed"},
            {"id": "route", "run_id": "r", "stage_code": "C4.routing", "kind": "stage", "name": "followup_dispatch",
             "seq": 2, "state": "completed", "output_artifact_id": "dispatch"},
        ]
        artifact = {"id": "dispatch", "run_id": "r", "step_id": "route", "kind": "source_snapshot",
                    "content_json": {"type": "followup_dispatch", "routes": routes}}
        return render_case_detail(key="t", title="测试", batch="b", data={
            "runs": [run], "run_steps": steps, "artifacts": [artifact],
        }, extras={"inputs": [{"original_marker": 77}], "page_reads": {"original_page_read": 88}})

    def test_constructed_map_is_independent_of_the_graph_followup(self):
        view = self.render([{"mode": "human", "state": "handoff"}])
        parsed = Nodes(view)
        self.assertIn("is-success", parsed.nodes["C5 构建关系图 · 已完成"]["class"])
        self.assertNotIn("href", parsed.nodes["构图 · 无此分派"])
        self.assertIn("is-unknown", parsed.nodes["人工确认 · 待人工确认"]["class"])
        for label in ["直接查询 · 无此分派", "问题深查 · 无此分派"]:
            self.assertIn("is-idle", parsed.nodes[label]["class"])
        for node in parsed.nodes.values():
            if "href" in node:
                self.assertIn(node["href"][1:], parsed.ids)

    def test_skipped_and_completed_attempts_remain_separate_and_keep_originals(self):
        view = self.render([{"mode": "deep", "state": "completed", "followup_index": 0},
                            {"mode": "deep", "state": "skipped", "followup_index": 1}])
        nodes = Nodes(view).nodes
        branches = [v for k, v in nodes.items() if k.startswith("问题深查 ·")]
        self.assertEqual(len(branches), 2)
        self.assertEqual({n["class"] for n in branches}, {"flow-node is-success", "flow-node is-idle"})
        self.assertIn("original_marker", view)
        self.assertIn("original_page_read", view)
        self.assertIn("执行记录（数据库 runs）", view)
        self.assertIn("步骤记录（数据库 run_steps）", view)
