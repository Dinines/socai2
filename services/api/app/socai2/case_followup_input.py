"""Frozen business sources and explicit prior dependencies for Deep/C6."""
import copy
from collections import Counter

from . import case_followup_selection as selection
from . import knowledge_model_input as knowledge
from .baseline_context import reference
from .baseline_evidence import SCHEMA as EVIDENCE_SCHEMA
from .baseline_evidence import citation_roles
from .baseline_final_evidence import query_candidates
from .baseline_model_view import blocked, blocked_message, draft_limit
from .baseline_store import StoreError, digest, encoded
from .case_c3_input_selection import describe as business_provenance
from .case_c3_input_selection import semantic as material_semantic
from .case_input_hierarchy import project, render, render_tools, shared_fields
from .case_input_text import field_hint, project_context
from .case_model_boundary import selected_profile
from .case_program_output import enabled, observation_literals
from .case_source_scope import describe, frozen_query_scope
from .case_source_scope import metadata as query_metadata
from .knowledge_content import project_content
from .model_input_view import source_prefix
from .program_facts import query_result_text

SCHEMA = "socai2.case-followup-input.v1"
REFERENCES = {"evidence_ids", "source_ids", "support_ids", "counter_ids"}


def scope_metadata(row):
    return {**query_metadata(row), **({"original_scope": copy.deepcopy(row["original_scope"])}
                                   if "original_scope" in row else {})}


def execution_receipt(payload):
    """Project recorded execution fields without upgrading them to observations."""
    if payload.get("type") == "query_projection":
        return {k: payload[k] for k in ("state", "question_id", "observed_rows_in_bounded_fetch", "truncated", "reason") if k in payload}
    if payload.get("type") == "materials":
        return {"members": {aid: {k: row[k] for k in
            ("state", "material_state", "material_id", "limitations", "omissions") if k in row}
            for aid, row in payload["members"].items()}}
    return None


def path_value(value, path):
    if not isinstance(path, str) or not path.startswith("$."):
        raise ValueError("unsupported_source_path")
    for key in path[2:].split("."):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def identities(value, boundary):
    """Only use on known scope/analysis structures, never arbitrary raw data."""
    def member(aid):
        key = str(aid)
        if key not in boundary["member_aliases"]:
            boundary["member_aliases"][key] = "X" + str(1 + sum(v.startswith("X") for v in boundary["member_aliases"].values()))
        return boundary["member_aliases"][key]

    def obj(key):
        if key not in boundary["object_aliases"]:
            boundary["object_aliases"][key] = "H" + str(1 + sum(v.startswith("H") for v in boundary["object_aliases"].values()))
        return boundary["object_aliases"][key]

    if isinstance(value, list):
        return [identities(v, boundary) for v in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, child in value.items():
        if key in {"alert_ids", "related_alert_ids", "added_alert_ids", "removed_alert_ids", "shared_alert_ids"}:
            result[key] = [member(a) for a in child]
        elif key == "alert_id":
            result[key] = member(child)
        elif key == "object_keys":
            result[key] = [obj(a) for a in child]
        else:
            result[key] = identities(child, boundary)
    return result


class Sources:
    def __init__(self, context, base, artifacts, extra, records=None, field_selection=False):
        self.artifacts, self.context = artifacts, context
        self.field_selection = field_selection
        self.rows, self.by_ref, self.dependencies, self.omissions = [], {}, [], copy.deepcopy(base["omissions"])
        self.prefix = source_prefix([context.model_dump(mode="json"), base, artifacts, extra])
        self.boundary = copy.deepcopy(base["case_boundary"])
        self.base_ids = {}
        self.query_numbers = {}
        records = base["input_ledger"]["records"] if records is None else records
        self.base_records = {encoded(r["ref"]): r for r in records}
        for row in records:
            for origin in row.get("knowledge", {}).get("origins", []):
                self.base_records[encoded(origin["ref"])] = row

    def query_record_key(self, ref):
        number = self.query_numbers.setdefault(str(ref["id"]), len(self.query_numbers) + 1)
        return f"Q{number}R{ref['source_path'].split('.')[2]}"

    def add(self, ref, value, owners, block, *, original=None, **extra):
        ref, owners = copy.deepcopy(ref), list(map(str, owners))
        config = selected_profile(self.context).config
        value = project_context(ref, value, config, self.omissions)
        if value == {} and ref.get("source_path") in config["context_projection"]:
            return None
        if blocked(value if original is None else original):
            self.omissions.append({"ref": ref, "reason": "input_guard", "value_sha256": digest(value)})
            return None
        if extra.get("knowledge", {}).get("part") == "card":
            value = project_content(value, config, self.omissions, ref)
        artifact = self.artifacts.get(str(ref["id"]), {})
        if (self.field_selection and (block == "query" or artifact.get("schema_version") == EVIDENCE_SCHEMA)
                and isinstance(value, dict) and {"name", "value"} <= set(value)):
            value = project(value, "query_field", config["followup_input_selection"], self.omissions, ref)
        key = encoded(ref)
        if key in self.by_ref:
            row = self.by_ref[key]
            if row["alert_ids"] != owners or digest(row["value"]) != digest(value):
                raise StoreError("followup_source_projection_conflict", 422)
            return row["id"]
        sid = self.prefix + "S" + str(len(self.rows) + 1)
        row = {"id": sid, "ref": ref, "alert_ids": owners, "value": copy.deepcopy(value),
               "block": block, **extra}
        if extra.get("record_alert_ids"):
            identities({"alert_ids": extra["record_alert_ids"]}, self.boundary)
        self.rows.append(row)
        self.by_ref[key] = row
        return sid

    def resolve(self, source):
        ref = source["ref"]
        row = self.by_ref.get(encoded(ref))
        if row:
            return row["id"]
        original = self.base_records.get(encoded(ref))
        if original:
            if original.get("knowledge"):
                # A cited historical judgment needs its whole card and conditions;
                # restore roles separately, all from this Run's frozen rows.
                for item in self.base_records.values():
                    if item.get("knowledge", {}).get("identity") == original["knowledge"]["identity"]:
                        self.add(item["ref"], item["value"], item["alert_ids"], "dependency",
                                 original=item.get("original_value"), **scope_metadata(item))
                return self.by_ref[encoded(original["ref"])]["id"]
            return self.add(ref, original["value"], original["alert_ids"], "dependency",
                            original=original.get("original_value"), **scope_metadata(original))
        # Exact references to frozen C4 projections remain valid dependencies.
        # Do not fetch latest data or material hidden by the business guard.
        artifact = self.artifacts.get(str(ref["id"]))
        if not artifact or ref["type"] != "artifact":
            return None
        payload, path = artifact["content_json"], ref["source_path"]
        if artifact.get("schema_version") == "socai2.baseline-context.v1":
            if payload.get("citation_roles", {}).get(path) != ref["role"]:
                return None
            value = path_value(payload, path)
            query_identity = frozen_query_scope(payload, path, self.context.alerts)
            if query_identity is not None:
                return self.add(ref, value, query_identity["alert_ids"], "dependency",
                                **scope_metadata(query_identity))
            cfg = selected_profile(self.context).config
            parent = next((rule for rule in cfg["followup"]["parent_dependencies"] if path.endswith(rule["suffix"])), None)
            if parent:
                children = [r for r in self.base_records.values() if (
                    parent["source_kind"] == "context_children" and r["ref"]["id"] == ref["id"]
                    and (r["ref"]["source_path"] or "").startswith(path + ".")) or (
                    parent["source_kind"] == "material_fields" and r["ref"]["type"] == "alert_material"
                    and r["ref"]["id"] == value["id"])]
                ids = [self.resolve({"ref": r["ref"], "alert_ids": r["alert_ids"]}) for r in children]
                if not any(ids):
                    return None
                projected = {"description": parent["label"], "source_ids": [s for s in ids if s],
                             **{k: value[k] for k in parent["keep"] if k in value}}
                if None in ids:
                    projected["unavailable_prior_reference_count"] = ids.count(None)
                return self.add(ref, projected, source["alert_ids"], "dependency", original=value)
            # Compatibility with valid earlier parent-level A/I references.
            # Use the same configured backend-field selection as the base view.
            from .case_input_text import select
            kind = "triage" if path.endswith(".triage") else "incident" if path.endswith(".diagnosis") else None
            projected = select(value, cfg["rules"][kind], self.omissions, path) if kind else value
            return self.add(ref, projected, source["alert_ids"], "dependency", original=value)
        if artifact.get("schema_version") != EVIDENCE_SCHEMA:
            return None
        if path is None and ref["role"] == "execution_receipt":
            value = execution_receipt(payload)
            if value is not None:
                owners = payload["alert_ids"] if payload["type"] == "query_projection" else sorted(payload["members"])
                return self.add(ref, value, owners, "query_receipt")
        if citation_roles(payload).get(path) != ref["role"]:
            return None
        value = path_value(payload, path)
        if payload.get("type") == "materials":
            owners = [path.split(".")[2]]
            basis = "frozen_material"
            member = payload["members"][owners[0]]
            raw_ref = reference("alert_material", member["material_id"], ref["role"], value["source_path"])
            raw = self.base_records.get(encoded(raw_ref))
            # Only exact, unchanged scalars share a source number. Mapped enums,
            # conflicts and other derived values retain their own provenance.
            if (value.get("transform") == "identity" and not value.get("conflict") and raw
                    and raw["alert_ids"] == owners and digest(raw.get("original_value")) == digest(value["value"])
                    and digest(raw["value"]) == digest(value["value"]) and not blocked(value)):
                return self.resolve({"ref": raw_ref, "alert_ids": owners})
        elif payload.get("type") == "query_projection":
            owners, basis = payload["alert_ids"], "query_binding_only"
            record_key = self.query_record_key(ref)
            return self.add(ref, {"record_key": record_key, **value}, owners, "dependency",
                            membership_basis=basis, record_key=record_key)
        else:
            return None
        return self.add(ref, value, owners, "dependency", membership_basis=basis)

    def rebind(self, value, mapping, owner):
        missing = []

        def walk(item, path):
            if isinstance(item, list):
                return [walk(v, [*path, i]) for i, v in enumerate(item)]
            if not isinstance(item, dict):
                return item  # free text and historical inline IDs are immutable
            result = {}
            for key, child in item.items():
                if key in REFERENCES:
                    current = []
                    for old in child:
                        source = mapping.get(old)
                        sid = self.resolve(source) if source else None
                        receipt = {"owner": owner, "path": [*path, key], "old_id": old,
                                   "original_source": source, "visible_id": sid}
                        self.dependencies.append(receipt)
                        if sid:
                            if sid not in current:
                                current.append(sid)
                        else:
                            missing.append(receipt)
                    result[key] = current
                else:
                    result[key] = walk(child, [*path, key])
            return result

        result = walk(value, [])
        if missing:
            result["unavailable_prior_reference_count"] = len(missing)
            result["reference_limitation"] = "部分旧依据当前不可见，不能仅沿用原判断。"
        return identities(result, self.boundary)

    def rebind_base(self, base):
        """Rebind projected A/I references, including dependencies restored late."""
        def current(sid):
            if not self.base_ids.get(sid) and sid in base["source_map"]:
                self.base_ids[sid] = self.resolve(base["source_map"][sid])
            return self.base_ids.get(sid)

        # resolve() may append a previously filtered record. Visit appended
        # records too; never recurse through free text or arbitrary raw fields.
        for row in self.rows:
            original = self.base_records.get(encoded(row["ref"]))
            if not original:
                continue
            value = row["value"]
            if original["block"] in {"finding", "question"}:
                for key, refs in value.get("visible_prior_references", {}).items():
                    resolved = [current(s) for s in refs]
                    value["visible_prior_references"][key] = [s for s in resolved if s]
                    if None in resolved:
                        counts = value.setdefault("unavailable_prior_reference_counts", {})
                        counts[key] = counts.get(key, 0) + resolved.count(None)
            if original["block"] == "triage":
                if "source_refs" in value:
                    resolved = [current(s) for s in value["source_refs"]]
                    value["source_refs"] = [s for s in resolved if s]
                    if None in resolved:
                        value["unavailable_prior_reference_count"] = value.get("unavailable_prior_reference_count", 0) + resolved.count(None)
                for rec in value.get("recommendations", []):
                    if "source_refs" in rec:
                        resolved = [current(s) for s in rec["source_refs"]]
                        rec["source_refs"] = [s for s in resolved if s]
                        if None in resolved:
                            rec["unavailable_prior_reference_count"] = rec.get("unavailable_prior_reference_count", 0) + resolved.count(None)
            if original["block"] == "incident" and original.get("prior_reference_resolution"):
                prior = original["prior_reference_resolution"]
                resolved = [current(s) for s in prior["visible"]]
                row["prior_reference_resolution"] = {"visible": [s for s in resolved if s],
                    "unavailable_count": len(prior["not_visible"]) + resolved.count(None)}


def query_records(registry, material, projections, *, final, excluded_fields=(), required_refs=()):
    facts = []
    required_refs = {encoded(ref) for ref in required_refs}
    for row in projections:
        registry.query_numbers.setdefault(str(row["id"]), len(registry.query_numbers) + 1)
        payload = row["content_json"]
        binding = material["catalog"]["bindings"][payload["binding_id"]]
        facts.append({"artifact_id": str(row["id"]), "state": payload["state"], "reason": payload["reason"],
            "tool_name": binding["tool_name"], "hostname": binding["hostname"], "question_id": payload["question_id"],
            "related_alert_ids": payload["alert_ids"], "window_start": binding["scope"]["window_start"],
            "window_end": binding["scope"]["window_end"],
            "observed_rows_in_bounded_fetch": payload["observed_rows_in_bounded_fetch"],
            "truncated": payload["truncated"], "limitations": payload["limitations"]})
    candidates, missing = query_candidates(facts, projections)
    required_missing = bool(missing) if final else False
    for item in candidates:
        source = item["source"]
        value = item["entry"]["value"]
        if (value["name"] in excluded_fields and not item.get("required")
                and encoded(source["ref"]) not in required_refs):
            registry.omissions.append({"ref": source["ref"], "reason": "query_identity_kept_in_backend",
                                       "value_sha256": digest(value)})
            continue
        record_key = registry.query_record_key(source["ref"])
        sid = registry.add(source["ref"], {**value, "record_key": record_key}, source["alert_ids"], "query",
                           membership_basis="query_binding_only", record_key=record_key)
        required_missing |= bool(final and item.get("required") and sid is None)
    for row in facts:
        payload = next(p["content_json"] for p in projections if str(p["id"]) == row["artifact_id"])
        row["receipt_source_id"] = registry.add(reference("artifact", row["artifact_id"], "execution_receipt"),
            execution_receipt(payload), row["related_alert_ids"], "query_receipt")
        row["visible_fields"] = sum(r["block"] == "query" and r["ref"]["id"] == row["artifact_id"] for r in registry.rows)
        if row["visible_fields"] < row["projected_fields"]:
            row["limitations"] = [*row["limitations"], "部分查询返回字段未进入模型输入，不能视作已读全部返回内容。"]
        else:
            row["view_state"] = "all_projected_fields"
    registry.omissions.extend(missing)
    return facts, required_missing


def build(stage, context, base, artifacts, *, previous=None, prior_id=None, question_id=None,
          material=None, projections=(), options=(), binding_map=None, extra=None, lead=(), graphs=(), _excluded_knowledge=()):
    profile = selected_profile(context)
    cfg, policy = profile.config, profile.config["followup"]
    if base["case_boundary"]["profile"] != profile.identity:
        raise StoreError("case_input_profile_changed", 422)
    if previous and previous.get("analysis") and previous.get("validation") != "structure_scope_sources_checked":
        raise StoreError("unaccepted_prior_analysis", 422)
    task_selection = stage in cfg.get("followup_input_selection", {}).get("stages", [])
    question = next((q for q in context.questions if q.id == question_id), None) if stage == "Deep" else None
    if stage == "Deep" and question is None:
        raise StoreError("question_outside_frozen_scope", 422)
    selected_analysis, selection_omissions = None, []
    selected_records = base["input_ledger"]["records"]
    required = []
    if task_selection:
        cfg = copy.deepcopy(cfg)
        cfg["presentation"]["labels"].update(cfg["c3_input_selection"]["labels"])
        cfg["presentation"]["labels"].update(cfg["followup_input_selection"]["labels"])
        if previous and previous.get("analysis"):
            selected_analysis = selection.prior(previous["analysis"], question, lead, prior_id, cfg,
                selection_omissions, program_owned=enabled(base["case_boundary"]))
            required.extend(selection.references(selected_analysis, previous["source_map"]))
        if stage == "C6":
            for artifact in artifacts.values():
                payload = artifact.get("content_json") or {}
                if payload.get("type") == "deep_summary" and payload.get("answer"):
                    required.extend(selection.references(payload["answer"], payload["source_map"]))
            for row in lead:
                plan = artifacts.get(str(row["source"]["ref"]["id"]), {}).get("content_json", {})
                required.extend(selection.references(row["original"], plan.get("source_map", {})))
        selected_records = selection.records(base, context, cfg, profile.business, required, selection_omissions)
    reg = Sources(context, base, artifacts, [previous, extra, lead, graphs], records=selected_records,
                  field_selection=task_selection)
    reg.omissions.extend(selection_omissions)
    boundary, ledger = reg.boundary, base["input_ledger"]
    required_missing = False
    prior_visible = None
    # Prior result comparisons may include members no longer in this Case.
    external = sorted({str(a) for row in lead for a in row["source"]["alert_ids"]} - set(boundary["member_aliases"]))
    for aid in external:
        boundary["member_aliases"][aid] = "X" + str(len([v for v in boundary["member_aliases"].values() if v.startswith("X")]) + 1)
    allowed = set(map(str, question.scope.alert_ids)) if question else set(context.alerts)
    # Retain cross-member/common/unknown-scope and all human material. The
    # current frozen questions usually cover the whole Case; no pretend filter.
    for row in selected_records:
        if row.get("knowledge"):
            continue  # Restore prior dependencies first, then select optional knowledge.
        owners = row["alert_ids"] or row.get("query_alert_ids", [])
        if owners and not allowed.intersection(owners) and (task_selection or row["ref"]["role"] != "human_statement"):
            reg.omissions.append({"ref": row["ref"], "reason": "outside_frozen_question_scope"})
            continue
        sid = reg.add(row["ref"], row["value"], row["alert_ids"], "base",
                      original=row.get("original_value"), business_block=row["block"], **scope_metadata(row))
        reg.base_ids[row["id"]] = sid
    if task_selection and question:
        projections = [r for r in projections if not r["content_json"].get("alert_ids")
                       or allowed.intersection(map(str, r["content_json"]["alert_ids"]))]
        options = [r for r in options if not r.get("alert_ids") or allowed.intersection(map(str, r["alert_ids"]))]
        binding_map = {k: v for k, v in (binding_map or {}).items() if any(o["binding_id"] == k for o in options)}
    queries, query_missing = query_records(reg, material, projections, final=stage == "C6",
        excluded_fields=cfg["followup_input_selection"].get("query_backend_fields", ()) if task_selection else (),
        required_refs=required) if projections else ([], False)
    material_source = None
    if stage == "C6" and enabled(boundary) and material is not None:
        material_artifact = next((aid for aid, row in artifacts.items() if row.get("content_json") == material), None)
        if material_artifact:
            material_source = reg.add(reference("artifact", material_artifact, "execution_receipt"),
                execution_receipt(material), sorted(material["members"]), "query_receipt")
    if previous and previous.get("analysis"):
        analysis = copy.deepcopy(selected_analysis if selected_analysis is not None else previous["analysis"])
        for followup in analysis.get("followups", []):
            for key in policy["prior_followup_omit"]:
                if key in followup:
                    reg.omissions.append({"reason": "prior_binding_is_not_current_tool_choice", "field": key,
                                          "value_sha256": digest(followup.pop(key))})
        if question and not task_selection:
            analysis = {"question": next(q for q in analysis["questions"] if q["id"] == question_id),
                        "followups": [f for f in analysis["followups"] if f["question_id"] == question_id]}
        value = reg.rebind(analysis, previous["source_map"], str(prior_id))
        prior_visible = reg.add(reference("artifact", prior_id, "prior_analysis", "$.analysis"), value,
                                sorted(context.alerts), "C3", original=previous["analysis"])
    for row in lead:
        value = copy.deepcopy(row["entry"]["value"])
        is_plan = "execution_plan_index" in value
        if is_plan:
            plan = artifacts[str(row["source"]["ref"]["id"])]["content_json"]
            if plan.get("validation") != "structure_scope_sources_checked":
                raise StoreError("unaccepted_prior_plan", 422)
            original = copy.deepcopy(row["original"])
            for key in policy["prior_followup_omit"]:
                original.pop(key, None)
            value["followup"] = reg.rebind(original, plan["source_map"], row["source"]["ref"])
        else:
            value = {k: v for k, v in value.items() if k not in policy["comparison_source_omit"]}
            value = identities(value, boundary)
        if task_selection and is_plan:
            value = project(value, "plan", cfg["followup_input_selection"], reg.omissions, row["source"]["ref"])
        visible = reg.add(row["source"]["ref"], value, row["source"]["alert_ids"],
                          "plan" if is_plan else "comparison", original=row["original"])
        required_missing |= bool(row.get("required") and visible is None)
    if stage == "C6":
        for aid, row in artifacts.items():
            payload = row.get("content_json") or {}
            if payload.get("type") != "deep_summary" or not payload.get("answer"):
                continue
            q = next((q for q in context.questions if q.id == payload["question_id"]), None)
            if q is None:
                raise StoreError("question_outside_frozen_scope", 422)
            value = reg.rebind(payload["answer"], payload["source_map"], aid)
            reg.add(reference("artifact", aid, "prior_analysis", "$.answer"),
                    {"question_id": q.id, **value}, q.scope.alert_ids, "Deep", original=payload["answer"])
        for row in graphs:
            reg.add(row["source"]["ref"], row["entry"]["value"], row["source"]["alert_ids"], "graph", original=row["original"],
                    membership_basis=row["source"].get("membership_basis", "source_label"))
    reg.rebind_base(base)
    dependencies = {r["knowledge"]["identity"] for r in reg.rows if r.get("knowledge")}
    knowledge_scope = allowed
    if stage == "C6":
        answered = {q["id"] for q in ((previous or {}).get("analysis") or {}).get("questions", [])
                    if q["state"] in {"answered", "not_applicable"}}
        answered.update(row["content_json"]["question_id"] for row in artifacts.values()
                        if row.get("content_json", {}).get("type") == "deep_summary"
                        and (row["content_json"].get("answer") or {}).get("state") == "supported")
        knowledge_scope = {str(a) for q in context.questions if q.id not in answered and q.id != "coverage"
                           for a in q.scope.alert_ids}
    elif question.id == "coverage":
        knowledge_scope = set()
    selected, knowledge_omissions = knowledge.choose([r for r in selected_records if r.get("knowledge")],
        stage, knowledge_scope, cfg["knowledge_selection"], dependencies=dependencies, excluded=_excluded_knowledge)
    reg.omissions.extend(knowledge_omissions)
    for row in selected:
        if row["knowledge"]["identity"] in dependencies:
            continue
        reg.add(row["ref"], row["value"], row["alert_ids"], "base", original=row.get("original_value"),
                business_block=row["block"], **scope_metadata(row))
    omissions = [r for r in reg.omissions if r["reason"] != "outside_frozen_question_scope" or encoded(r["ref"]) not in reg.by_ref]
    metadata = copy.deepcopy(extra or {})
    comparison = metadata.get("comparison")
    visible_comparison = None
    if comparison and not (task_selection and comparison.get("state") == "initial" and comparison.get("result_id") is None):
        visible_comparison = identities({k: v for k, v in comparison.items() if k not in policy["comparison_omit"]}, boundary)
        if visible_comparison.get("prior_scope"):
            visible_comparison["prior_scope"] = project(visible_comparison["prior_scope"], "scope", cfg, omissions, "prior_scope")
        else:
            visible_comparison.pop("prior_scope", None)
    scope = project(identities((question.scope if question else context.scope).model_dump(mode="json"), boundary),
                    "scope", cfg, omissions, "scope")
    blocks = ["[本次任务]", question.text if question else "根据本轮实际材料作出最终案件判断。",
              "调查范围：" + render(scope, cfg)]
    if question:
        blocks.append("依据要求：" + "；".join(question.evidence_requirements))
    else:
        blocks += ["[要复核的业务问题]", *[q.id + "：" + q.text for q in context.questions
                                        if not enabled(boundary) or q.id != "coverage"]]
    for q in ([question] if question else context.questions):
        if q.id in cfg["question_instructions"]:
            blocks.append("[" + q.id + " 的回答边界] " + cfg["question_instructions"][q.id])
    blocks += ["[对象短号]", *[alias + "=" + key for key, alias in boundary["object_aliases"].items()]]
    if ledger.get("presented_program_facts") and not (task_selection and question):
        blocks += ["[必要程序事实]", render(ledger["presented_program_facts"], cfg)]
    query_names = {row["artifact_id"]: row["tool_name"] for row in queries}
    tool_labels = {**profile.business["render"]["query_names"], **cfg["c3_input_selection"]["query_names"]}
    execution = metadata.get("followup_execution")
    if execution and not task_selection:
        visible = {"routes": [{k: v for k, v in row.items() if k not in policy["execution_omit"]} for row in execution["routes"]]}
        blocks += ["[原计划执行情况｜按 execution_plan_index 对应]", render(visible, cfg)]
    if visible_comparison:
        blocks += ["[本次比较条件]", render(visible_comparison, cfg)]
    if metadata.get("graph_state") in {"not_built", "stale"}:
        blocks.append(cfg["followup_input_selection"]["graph_unavailable_text"] if task_selection else
                      "[图谱限制] " + metadata["graph_state"] + "；未提供可用的当前派生图，不表示没有关联。")
    if prior_visible is None:
        blocks.append("没有可用的C3判断；需根据现有材料独立分析，不能假装已承接初步结论。")
    presentation = []
    shared, shared_omits = shared_fields(
        [(r["id"], r["value"]) for r in reg.rows if r["block"] == "graph"],
        cfg["presentation"]["receipt_shared_fields"], presentation)
    if shared:
        blocks.append("[共同限制｜仅适用于所列来源]")
        blocks += [",".join(item["applies_to"]) + "：" + render({item["field"]: item["value"]}, cfg) for item in shared]
    groups, seen = [], {}
    for row in reg.rows:
        key = (row["ref"]["id"], tuple(row["query_record_identity"]), row["block"], row["ref"]["role"],
               tuple(row["alert_ids"]), digest(scope_metadata(row)), digest(row["value"])) if row.get("query_record_identity") else None
        if task_selection and row.get("query_record_identity"):
            key = ("history", tuple(row["query_record_identity"]), row["ref"]["role"], tuple(row["alert_ids"]),
                   tuple(row.get("record_alert_ids", [])), row.get("membership_basis"), digest(row["value"]))
        path = row["ref"]["source_path"] or ""
        semantic = next((path[len(root):] for root in profile.business["render"]["event_roots"] if path.startswith(root)), None)
        if task_selection:
            semantic = material_semantic(reg.base_records.get(encoded(row["ref"]), row), profile.business["render"], cfg)
        if row["ref"]["type"] == "alert_material" and semantic:
            key = ("material", row["ref"]["id"], row["ref"]["role"], tuple(row["alert_ids"]), semantic, digest(row["value"]))
        if task_selection and row.get("record_key") and not row["value"].get("conflict"):
            key = ("query_field", row["ref"]["id"], row["ref"]["role"], tuple(row["alert_ids"]),
                   digest(scope_metadata(row)), digest({k: v for k, v in row["value"].items() if k != "record_key"}))
        if key is not None and key in seen:
            seen[key]["ids"].append(row["id"])
            seen[key]["rows"].append(row)
            continue
        group = {"row": row, "ids": [row["id"]], "rows": [row]}
        groups.append(group)
        if key is not None:
            seen[key] = group
    last = None
    for group in groups:
        row = group["row"]
        members = "、".join(boundary["member_aliases"].get(a, "案件外成员") for a in row["alert_ids"]) or "共同背景/范围不明"
        block = ("case_record" if row["ref"]["type"] == "artifact" and row["ref"]["source_path"] == "$.case"
                 else "query_receipt" if row["ref"]["role"] == "execution_receipt" else row["block"])
        heading = block, members, row["ref"]["role"], row.get("membership_basis")
        if heading != last:
            blocks.append(f"[{policy['labels'][block]}｜原范围={members}｜{row['ref']['role']}"
                          + ("｜仅查询绑定，非逐行归属" if row.get("membership_basis") == "query_binding_only" else "") + "]")
            last = heading
        path = row["ref"]["source_path"] or ""
        caption = path.removeprefix("$.ocsf_json.").removeprefix("$.raw_json.") if row.get("business_block") == "material" else ""
        provenance = ("" if row["ref"]["role"] == "execution_receipt"
                      else (business_provenance if task_selection else describe)(row, lambda aid: boundary["member_aliases"].get(aid, "案件外成员")))
        meaning = field_hint(row["ref"], cfg)
        shown = ({k: v for k, v in row["value"].items() if k not in shared_omits.get(row["id"], set())}
                 if isinstance(row["value"], dict) else row["value"])
        citations = "[" + ",".join(group["ids"]) + "]"
        if task_selection and row.get("record_key"):
            citations = "、".join(f"[{r['id']}] {r['record_key']}" for r in group["rows"])
            provenance = ""  # The section heading already states query binding, not row membership.
            caption = shown["name"]
            shown = {k: v for k, v in shown.items() if k not in {"record_key", "name"}}
            if set(shown) == {"value"}:
                shown = shown["value"]
        if row["ref"]["role"] == "execution_receipt":
            if "members" in row["value"]:
                shown = "；".join(boundary["member_aliases"].get(aid, "案件外成员") + "：材料"
                    + {"available": "可用", "unavailable": "不可用"}.get(member.get("state"), "状态未知")
                    for aid, member in row["value"]["members"].items())
            else:
                shown = query_result_text(row["value"], tool_labels,
                                          tool_name=query_names.get(row["ref"]["id"]))
        blocks.append(citations + " " + (provenance + " " if provenance else "")
                      + (caption + "=" if caption else "") + render(shown, cfg)
                      + ("（字段含义：" + meaning + "）" if meaning else ""))
        if row.get("prior_reference_resolution"):
            resolution = row["prior_reference_resolution"]
            if resolution["visible"]:
                blocks[-1] += "；依据=" + render(resolution["visible"], cfg)
            if resolution["unavailable_count"]:
                blocks[-1] += f"；{resolution['unavailable_count']}条原依据当前不可见"
    # Keep the original receipts and source IDs; this is a direct field projection,
    # not a model summary or a reconstruction from prior analysis prose.
    background = [{"source_id": row["id"], **{k: row["value"][k] for k in
        ("tool_name", "state", "outcome", "returned_rows", "truncated") if k in row["value"]}}
        for row in reg.rows if row.get("business_block") == "background_query"
        and row["ref"]["role"] == "execution_receipt" and isinstance(row["value"], dict)]
    # The result was displayed with its source above. Keep this complete
    # background ledger for program-owned coverage, without displaying it again.
    if task_selection:
        if any(r["reason"] == "input_guard" for r in omissions):
            blocks.append(cfg["followup_input_selection"]["unavailable_text"])
    elif omissions:
        blocks.append("[材料限制] " + render(dict(Counter(r["reason"] for r in omissions)), cfg)
                      + "；省略或不可见不表示不存在，不能视作已读全文。")
    if enabled(boundary):
        boundary["observation_literals"] = observation_literals(reg.rows, boundary["member_aliases"])
        if stage == "C6":
            states = [{"tool_name": row["tool_name"], "state": row["state"], "outcome": row.get("outcome"),
                       "returned_rows": row.get("returned_rows"), "truncated": row.get("truncated"),
                       "source_ids": [row["source_id"]]} for row in background]
            states += [{"tool_name": row["tool_name"], "state": row["state"],
                        "observed_rows_in_bounded_fetch": row["observed_rows_in_bounded_fetch"],
                        "truncated": row["truncated"], "source_ids": [row["receipt_source_id"]] if row["receipt_source_id"] else []}
                       for row in queries]
            reads = (execution_receipt(material) or {}).get("members", {}) if material else {}
            boundary["coverage_facts"] = {"visible_members": sum(row["included"] > 0 for row in base["coverage"].values()),
                "total_members": len(context.alerts), "omission_count": len(omissions), "queries": states,
                "material_reads": {boundary["member_aliases"][aid]: copy.deepcopy(reads.get(aid, {"state": "unrecorded"}))
                                   for aid in context.alerts},
                "material_source_ids": [material_source] if material_source else [],
                "execution_states": dict(Counter(row["state"] for row in (execution or {}).get("routes", [])))}
    messages = [{"role": "system", "content": policy[stage] + "\n" + policy["common"]
                + ("\n" + cfg["program_output"]["instruction"] if stage == "C6" else "")
                + ("\n" + cfg["citation_instruction"] if stage == "C6" else "")},
                {"role": "user", "content": "\n".join(blocks)}]
    presentation = None
    if stage == "Deep":
        from .baseline_tool_catalog import data
        catalog = identities(data(options), boundary)
        presentation = render_tools(selection.available_tools(catalog) if task_selection else catalog, cfg)
        if task_selection and not options:
            presentation["text"] = cfg["followup_input_selection"]["no_tools_text"]
        messages.append({"role": "user", "content": presentation["text"]})
    sources = {r["id"]: {"ref": r["ref"], "alert_ids": r["alert_ids"], "visible_value_sha256": digest(r["value"]),
                            **scope_metadata(r), **{k: r[k] for k in ("record_key",) if k in r}} for r in reg.rows}
    coverage = copy.deepcopy(base["coverage"])
    for aid, row in coverage.items():
        row["included"] = sum(aid in r["alert_ids"] for r in reg.rows)
    why = "case_followup_input_exceeds_prepared_limit" if len(encoded(messages)) > draft_limit() else None
    optional = [r["knowledge"]["identity"] for r in reg.rows if r.get("knowledge")
                and r["knowledge"]["identity"] not in dependencies]
    if why and optional:
        return build(stage, context, base, artifacts, previous=previous, prior_id=prior_id, question_id=question_id,
            material=material, projections=projections, options=options, binding_map=binding_map, extra=extra,
            lead=lead, graphs=graphs, _excluded_knowledge=(*_excluded_knowledge, optional[-1]))
    if any(blocked_message(m["content"]) for m in messages):
        why = "case_followup_input_guard"
    if not base["ready"]:
        why = base["reason"]
    if required_missing:
        why = "required_followup_input_unavailable"
    if query_missing:
        why = "required_query_evidence_unavailable"
    return {"schema_version": SCHEMA, "ready": why is None, "reason": why, "messages": messages if why is None else [],
        "source_map": sources, "coverage": coverage, "omissions": omissions,
        "case_boundary": {**boundary, "stage": stage, "question_id": question_id},
        "followup_boundary": {"version": policy["version"], "records": reg.rows, "dependencies": reg.dependencies,
                              "query_facts": queries, "background_status": background, "program_metadata": metadata,
                              "presentation": {"groups": [g["ids"] for g in groups], "shared_fields": shared, "ledger": presentation}},
        "binding_map": binding_map or {}, "tool_presentation": presentation,
        "source_states": base.get("source_state_ledger", []), "program_facts": ledger.get("program_facts"),
        "bytes": len(encoded(messages))}
