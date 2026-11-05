"""Deterministic C5 graph from frozen source labels and typed C4 observations.

Graph connectivity is a presentation of sources, not independent corroboration.
Processes, sessions and endpoints are record-scoped; no PID/name/time join.
"""
import copy
from collections import Counter
from uuid import UUID

from .baseline_context import MAX_CONTEXT_BYTES, reference
from .baseline_model_view import MAX_FIELD_BYTES, blocked
from .baseline_store import StoreError, digest, encoded

SCHEMA = "socai2.baseline-graph.v1"
MAX_NODES, MAX_EDGES = 200, 400
LIMITATIONS = ["derived_view_not_independent_evidence", "connectivity_does_not_prove_causality_or_impact",
    "record_scoped_process_endpoint_and_session_identity", "external_topology_not_queried",
    "no_attack_path_or_transitive_impact_inferred", "analysis_prose_not_converted_to_edges"]
OBJECT_TYPES = {"host", "user", "ip", "domain", "url", "file", "hash", "process", "email",
    "application", "cloud_resource", "technique", "other"}


def identity(*parts):
    return digest([str(p) if isinstance(p, UUID) else p for p in parts])


def usable(value):
    return value is not None and not blocked(value) and len(encoded(value)) <= MAX_FIELD_BYTES


def node(key, kind, label, aids, refs, object_key=None):
    return {"id": key, "type": kind, "label": str(label), "object_key": object_key,
        "alert_ids": aids, "source_refs": refs}


def edge(start, end, relation, refs, *, strength="candidate", limitations=()):
    return {"id": identity(start, end, relation), "from": start, "to": end, "relation": relation,
        "strength": strength, "source_refs": refs, "limitations": list(limitations)}


class Projection:
    def __init__(self):
        self.nodes, self.edges, self.records = {}, {}, []
        self.omissions = Counter()

    def graph(self):
        return {"schema_version": SCHEMA, "nodes": list(self.nodes.values()), "edges": list(self.edges.values()),
            "layout": None, "expanded_node_ids": [], "selected_node_ids": [], "limitations": LIMITATIONS}

    def add(self, nodes, edges, record, *, mandatory=False):
        before = self.nodes, self.edges, self.records
        self.nodes, self.edges, self.records = copy.deepcopy(before)
        for n in nodes:
            if n["id"] in self.nodes:
                old = self.nodes[n["id"]]
                old["alert_ids"] = sorted(set(old["alert_ids"] + n["alert_ids"]))
                old["source_refs"] += [r for r in n["source_refs"] if r not in old["source_refs"]]
            else:
                self.nodes[n["id"]] = n
        self.edges.update({e["id"]: e for e in edges})
        self.records.append(record)
        if (len(self.nodes) > MAX_NODES or len(self.edges) > MAX_EDGES
                or len(encoded(self.graph())) > MAX_CONTEXT_BYTES - 8192
                or len(encoded(self.records)) > MAX_CONTEXT_BYTES - 16384):
            self.nodes, self.edges, self.records = before
            if mandatory:
                raise StoreError("graph_member_anchors_exceed_retention_limit", 422)
            self.omissions["whole_relation_bundle_exceeds_graph_limit"] += 1
            return False
        return True

    def observation(self, key, semantics, artifact_id, path, aids, related, time_basis):
        # A conflicting field cannot be silently selected to establish an edge.
        values = {}
        for i, field in enumerate(semantics.get("fields", [])):
            if field.get("conflict") or not usable(field["value"]):
                self.omissions["conflicting_or_guarded_field_not_used"] += 1
                continue
            values.setdefault(field["name"], []).append({**field,
                "ref": reference("artifact", artifact_id, "observation", path + f".fields.{i}")})

        def one(name):
            fields = values.get(name, [])
            return fields[0] if len(fields) == 1 else None

        def fields(*names):
            return [v for name in names if (v := one(name))]

        def make(suffix, kind, entries):
            return node(identity(key, suffix), kind, entries[0]["value"], aids, [v["ref"] for v in entries])

        def retain(nodes, edges, entries, kind):
            self.add(nodes, edges, {"kind": kind, "record_key": key, "node_ids": [n["id"] for n in nodes],
                "edge_ids": [e["id"] for e in edges], "related_alert_ids": related,
                "membership_basis": "frozen_material" if aids else "query_binding_only",
                "time_basis": time_basis, "fields": entries, "source_state": semantics["state"],
                "limitations": semantics.get("limitations", [])})

        # Only nested OCSF parent fields establish a reported parent relation.
        for prefix, pid, uid, parent_pid, parent_uid, attrs in [
                ("process", "process_pid", "process_uid", "parent_pid", "parent_uid",
                 ("process_name", "process_path", "process_command_line", "parent_name", "parent_path")),
                ("actor.process", "actor_process_pid", None, "actor_process_parent_pid", None,
                 ("actor_process_name", "actor_process_command_line"))]:
            child = fields(*[x for x in (uid, pid) if x])
            parent = fields(*[x for x in (parent_uid, parent_pid) if x])
            if child:
                child_node = make(prefix, "process", child)
                nodes, edges = [child_node], []
                if parent:
                    parent_node = make(prefix + ".parent", "process", parent)
                    nodes.append(parent_node)
                    edges.append(edge(parent_node["id"], child_node["id"], "reported_parent_process",
                        [v["ref"] for v in child + parent], strength="observed",
                        limitations=["source_reported_parent_not_execution_or_malicious_causality"]))
                retain(nodes, edges, child + parent + fields(*attrs), "process")

        # Endpoint pairs must come from one structured record; do not synthesize
        # a pair by mixing lake fallback columns and nested OCSF fields.
        source = fields("source_ip", "src_hostname")
        target = fields("dest_ip", "dst_hostname")
        event = one("event_kind")
        source = [f for f in source if ".src_endpoint." in f["source_path"]]
        target = [f for f in target if ".dst_endpoint." in f["source_path"]]
        if source and target and event and event["value"] in {"network_activity", "authentication_activity"}:
            src = make("source_endpoint", "ip" if source[0]["name"] == "source_ip" else "host", source)
            dst = make("destination_endpoint", "ip" if target[0]["name"] == "dest_ip" else "host", target)
            attrs = fields("src_port", "dst_port", "protocol", "action", "outcome")
            entries = source + target + [event] + attrs
            retain([src, dst], [edge(src["id"], dst["id"], "reported_" + event["value"],
                [v["ref"] for v in entries], strength="observed", limitations=[
                    "activity_not_proof_of_success_authorization_or_impact",
                    "no_process_to_connection_link_inferred"])], entries, "endpoints")
        elif source or target:
            self.omissions["endpoint_pair_or_event_kind_not_sufficient"] += 1

        # Never combine alternate session paths into a purported global session.
        for name in ("process_session_uid", "process_session_uid_alt", "actor_session_uid",
                "actor_session_uid_alt", "session_id", "session_key"):
            entry = one(name)
            if entry:
                retain([make(name, "other", [entry])], [], [entry], "record_session")


def build(context, context_id, bases):
    p = Projection()
    coverage = {aid: {"anchor_retained": True, "material_state": "unavailable"} for aid in context.alerts}
    # Every member gets an anchor before optional objects and observations.
    for aid, member in sorted(context.alerts.items()):
        title = member.alert.get("title")
        if not usable(title):
            title = "Alert " + aid
            p.omissions["member_title_unavailable_or_guarded"] += 1
        key = identity("alert", aid)
        ref = reference("artifact", context_id, "source_label", f"$.alerts.{aid}.alert")
        p.add([node(key, "other", title, [aid], [ref])], [], {"kind": "member_anchor", "alert_id": aid,
            "node_ids": [key], "edge_ids": [], "event_time": member.alert.get("event_time"),
            "time_basis": "frozen_alert_event_time", "event_time_source": member.alert.get("event_time_source")}, mandatory=True)
    for aid, member in sorted(context.alerts.items()):
        for obj in sorted(member.objects, key=lambda o: str(o["id"])):
            kind, value = obj["object_type"], obj.get("normalized_value")
            if not usable(obj) or not value or kind not in OBJECT_TYPES:
                p.omissions["source_object_guarded_missing_or_unsupported"] += 1
                continue
            # Namespaced exact keys are necessary but not sufficient for process
            # or hash identity; keep these objects local to their source record.
            local = obj["id"] if kind in {"process", "hash", "other"} or not obj.get("namespace") else None
            key = identity("source_object", kind, obj.get("namespace"), obj["object_key"], value, local)
            ref = reference("artifact", context_id, "source_label", f"$.alerts.{aid}.objects")
            n = node(key, kind, value, [aid], [ref], obj["object_key"])
            e = edge(identity("alert", aid), key, "source_reports_object", [ref],
                limitations=["source_label_not_behavior_or_cross_alert_causality"])
            p.add([n], [e], {"kind": "source_object", "alert_id": aid, "object_id": obj["id"],
                "namespace": obj.get("namespace"), "source_path": obj.get("source_path"),
                "node_ids": [key], "edge_ids": [e["id"]]})
    queries = []
    catalog = next(r["content_json"]["catalog"]["bindings"] for r in bases if r["content_json"]["type"] == "materials")
    for row in bases:
        payload, fid = row["content_json"], row["id"]
        if payload["type"] == "materials":
            for aid, data in sorted(payload["members"].items()):
                coverage[aid]["material_state"] = data["state"]
                p.observation(identity(fid, aid), data, fid, f"$.members.{aid}", [aid], [aid],
                    {"value": context.alerts[aid].alert.get("event_time"), "origin": "frozen_alert_event_time",
                        "source_kind": context.alerts[aid].alert.get("event_time_source")})
        elif payload["type"] == "query_projection":
            binding = catalog[payload["binding_id"]]
            queries.append({k: payload[k] for k in ("binding_id", "question_id", "state", "reason", "receipt_id",
                "observed_rows_in_bounded_fetch", "truncated")})
            queries[-1]["omission_count"] = len(payload["omissions"])
            queries[-1]["projection_id"] = str(fid)
            queries[-1].update(tool_name=binding["tool_name"], hostname=binding["hostname"],
                related_alert_ids=payload["alert_ids"], scope=binding["scope"])
            if payload.get("source_role", "observation") != "observation":
                p.omissions["current_snapshot_not_activity"] += len(payload["rows"])
                continue
            for i, data in enumerate(payload["rows"]):
                times = [f for f in data["semantics"]["fields"] if f["name"] == "event_time"]
                events = [f for f in data["semantics"]["fields"] if f["name"] == "event_id"]
                p.observation(identity(fid, i), data["semantics"], fid, f"$.rows.{i}.semantics", [], payload["alert_ids"],
                    {"value": times[0]["value"] if times else None, "origin": "query_row_event_time",
                        "event_id": events[0]["value"] if events else None})
    graph = p.graph()
    return graph, {"records": p.records, "coverage": coverage, "queries": queries,
        "omissions": dict(p.omissions), "limits": {"nodes": MAX_NODES, "edges": MAX_EDGES,
            "artifact_bytes": MAX_CONTEXT_BYTES}, "limitations": LIMITATIONS + [
            "query_binding_does_not_prove_alert_membership", "empty_query_does_not_disprove_relationship",
            "missing_or_omitted_edge_does_not_disprove_relationship"]}


def citation_roles(payload):
    # Graphs remain a derived analytical view even when their underlying fields
    # report an observed relation. Cite those fields for the actual observation.
    return {f"$.{key}.{i}": "prior_analysis" for key in ("nodes", "edges")
        for i in range(len(payload.get(key, [])))}
