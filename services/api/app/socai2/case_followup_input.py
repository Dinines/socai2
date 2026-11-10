"""Frozen business sources and explicit prior dependencies for Deep/C6."""
import copy
from collections import Counter

from .baseline_context import reference
from .baseline_evidence import SCHEMA as EVIDENCE_SCHEMA
from .baseline_evidence import citation_roles
from .baseline_final_evidence import query_candidates
from .baseline_model_view import blocked, draft_limit
from .baseline_store import StoreError, digest, encoded
from .case_input_hierarchy import project, render, render_tools
from .case_model_boundary import selected_profile
from .case_source_scope import describe, frozen_query_scope
from .case_source_scope import metadata as scope_metadata
from .model_input_view import source_prefix

SCHEMA = "socai2.case-followup-input.v1"
REFERENCES = {"evidence_ids", "source_ids", "support_ids", "counter_ids"}


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
    def __init__(self, context, base, artifacts, extra):
        self.artifacts, self.context = artifacts, context
        self.rows, self.by_ref, self.dependencies, self.omissions = [], {}, [], copy.deepcopy(base["omissions"])
        self.prefix = source_prefix([context.model_dump(mode="json"), base, artifacts, extra])
        self.boundary = copy.deepcopy(base["case_boundary"])
        self.base_ids = {}
        self.base_records = {encoded(r["ref"]): r for r in base["input_ledger"]["records"]}

    def add(self, ref, value, owners, block, *, original=None, **extra):
        ref, owners = copy.deepcopy(ref), list(map(str, owners))
        key = encoded(ref)
        if key in self.by_ref:
            row = self.by_ref[key]
            if row["alert_ids"] != owners or digest(row["value"]) != digest(value):
                raise StoreError("followup_source_projection_conflict", 422)
            return row["id"]
        if blocked(value if original is None else original):
            self.omissions.append({"ref": ref, "reason": "input_guard", "value_sha256": digest(value)})
            return None
        sid = self.prefix + "S" + str(len(self.rows) + 1)
        row = {"id": sid, "ref": ref, "alert_ids": owners, "value": copy.deepcopy(value),
               "block": block, **extra}
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
                for rec in value.get("recommendations", []):
                    if "source_refs" in rec:
                        resolved = [current(s) for s in rec["source_refs"]]
                        rec["source_refs"] = [s for s in resolved if s]
                        if None in resolved:
                            rec["unavailable_prior_reference_count"] = rec.get("unavailable_prior_reference_count", 0) + resolved.count(None)


def query_records(registry, material, projections, *, final):
    facts = []
    for row in projections:
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
        sid = registry.add(source["ref"], item["entry"]["value"], source["alert_ids"], "query",
                           membership_basis="query_binding_only", record_key=source["record_key"])
        required_missing |= bool(final and item.get("required") and sid is None)
    for row in facts:
        row["visible_fields"] = sum(r["block"] == "query" and r["ref"]["id"] == row["artifact_id"] for r in registry.rows)
        if row["visible_fields"] < row["projected_fields"]:
            row["limitations"] = [*row["limitations"], "部分查询返回字段被输入检查排除，不能视作已读全部返回内容。"]
        else:
            row["view_state"] = "all_projected_fields"
    registry.omissions.extend(missing)
    return facts, required_missing


def build(stage, context, base, artifacts, *, previous=None, prior_id=None, question_id=None,
          material=None, projections=(), options=(), binding_map=None, extra=None, lead=(), graphs=()):
    profile = selected_profile(context)
    cfg, policy = profile.config, profile.config["followup"]
    if base["case_boundary"]["profile"] != profile.identity:
        raise StoreError("case_input_profile_changed", 422)
    reg = Sources(context, base, artifacts, [previous, extra, lead, graphs])
    boundary, ledger = reg.boundary, base["input_ledger"]
    required_missing = False
    prior_visible = None
    # Prior result comparisons may include members no longer in this Case.
    external = sorted({str(a) for row in lead for a in row["source"]["alert_ids"]} - set(boundary["member_aliases"]))
    for aid in external:
        boundary["member_aliases"][aid] = "X" + str(len([v for v in boundary["member_aliases"].values() if v.startswith("X")]) + 1)
    question = next((q for q in context.questions if q.id == question_id), None) if stage == "Deep" else None
    if stage == "Deep" and question is None:
        raise StoreError("question_outside_frozen_scope", 422)
    allowed = set(map(str, question.scope.alert_ids)) if question else set(context.alerts)
    # Retain cross-member/common/unknown-scope and all human material. The
    # current frozen questions usually cover the whole Case; no pretend filter.
    for row in ledger["records"]:
        if row["alert_ids"] and not allowed.intersection(row["alert_ids"]) and row["ref"]["role"] != "human_statement":
            reg.omissions.append({"ref": row["ref"], "reason": "outside_frozen_question_scope"})
            continue
        sid = reg.add(row["ref"], row["value"], row["alert_ids"], "base",
                      original=row.get("original_value"), business_block=row["block"], **scope_metadata(row))
        reg.base_ids[row["id"]] = sid
    queries, query_missing = query_records(reg, material, projections, final=stage == "C6") if projections else ([], False)
    if previous and previous.get("analysis"):
        if previous.get("validation") != "structure_scope_sources_checked":
            raise StoreError("unaccepted_prior_analysis", 422)
        analysis = copy.deepcopy(previous["analysis"])
        for followup in analysis["followups"]:
            for key in policy["prior_followup_omit"]:
                if key in followup:
                    reg.omissions.append({"reason": "prior_binding_is_not_current_tool_choice", "field": key,
                                          "value_sha256": digest(followup.pop(key))})
        if question:
            analysis = {"question": next(q for q in analysis["questions"] if q["id"] == question_id),
                        "followups": [f for f in analysis["followups"] if f["question_id"] == question_id]}
        value = reg.rebind(analysis, previous["source_map"], str(prior_id))
        prior_visible = reg.add(reference("artifact", prior_id, "prior_analysis", "$.analysis"), value,
                                sorted(context.alerts), "C3", original=analysis)
    for row in lead:
        value = copy.deepcopy(row["entry"]["value"])
        if "execution_plan_index" in value:
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
        visible = reg.add(row["source"]["ref"], value, row["source"]["alert_ids"],
                          "plan" if "execution_plan_index" in value else "comparison", original=row["original"])
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
    omissions = [r for r in reg.omissions if r["reason"] != "outside_frozen_question_scope" or encoded(r["ref"]) not in reg.by_ref]
    metadata = copy.deepcopy(extra or {})
    comparison = metadata.get("comparison")
    visible_comparison = None
    if comparison:
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
        blocks += ["[要复核的问题]", *[q.id + "：" + q.text for q in context.questions]]
    blocks += ["[对象短号]", *[alias + "=" + key for key, alias in boundary["object_aliases"].items()]]
    if ledger.get("presented_program_facts"):
        blocks += ["[必要程序事实]", render(ledger["presented_program_facts"], cfg)]
    if queries:
        blocks += ["[实际补查回执｜查询完成不代表问题解决]", *[
            render(identities({k: v for k, v in row.items() if k not in policy["query_omit"]}, boundary), cfg) for row in queries]]
    execution = metadata.get("followup_execution")
    if execution:
        visible = {"routes": [{k: v for k, v in row.items() if k not in policy["execution_omit"]} for row in execution["routes"]]}
        blocks += ["[原计划执行情况｜按 execution_plan_index 对应]", render(visible, cfg)]
    if visible_comparison:
        blocks += ["[本次比较条件]", render(visible_comparison, cfg)]
    if metadata.get("graph_state") in {"not_built", "stale"}:
        blocks.append("[图谱限制] " + metadata["graph_state"] + "；未提供可用的当前派生图，不表示没有关联。")
    if prior_visible is None:
        blocks.append("没有可用的C3判断；需根据现有材料独立分析，不能假装已承接初步结论。")
    last = None
    for row in reg.rows:
        members = "、".join(boundary["member_aliases"].get(a, "案件外成员") for a in row["alert_ids"]) or "共同背景/范围不明"
        heading = row["block"], members, row["ref"]["role"], row.get("membership_basis")
        if heading != last:
            blocks.append(f"[{policy['labels'][row['block']]}｜原范围={members}｜{row['ref']['role']}"
                          + ("｜仅查询绑定，非逐行归属" if row.get("membership_basis") == "query_binding_only" else "") + "]")
            last = heading
        path = row["ref"]["source_path"] or ""
        caption = path.removeprefix("$.ocsf_json.").removeprefix("$.raw_json.") if row.get("business_block") == "material" else ""
        provenance = describe(row, lambda aid: boundary["member_aliases"].get(aid, "案件外成员"))
        blocks.append("[" + row["id"] + "] " + (provenance + " " if provenance else "")
                      + (caption + "=" if caption else "") + render(row["value"], cfg))
    if omissions:
        blocks.append("[材料限制] " + render(dict(Counter(r["reason"] for r in omissions)), cfg)
                      + "；省略或不可见不表示不存在，不能视作已读全文。")
    messages = [{"role": "system", "content": policy[stage] + "\n" + policy["common"]
                + ("\n" + cfg["citation_instruction"] if stage == "C6" else "")},
                {"role": "user", "content": "\n".join(blocks)}]
    presentation = None
    if stage == "Deep":
        from .baseline_tool_catalog import data
        presentation = render_tools(identities(data(options), boundary), cfg)
        messages.append({"role": "user", "content": presentation["text"]})
    sources = {r["id"]: {"ref": r["ref"], "alert_ids": r["alert_ids"], "visible_value_sha256": digest(r["value"]),
                            **scope_metadata(r), **{k: r[k] for k in ("record_key",) if k in r}} for r in reg.rows}
    coverage = copy.deepcopy(base["coverage"])
    for aid, row in coverage.items():
        row["included"] = sum(aid in r["alert_ids"] for r in reg.rows)
    why = "case_followup_input_exceeds_prepared_limit" if len(encoded(messages)) > draft_limit() else None
    if any(blocked(m["content"]) for m in messages):
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
                              "query_facts": queries, "program_metadata": metadata},
        "binding_map": binding_map or {}, "tool_presentation": presentation,
        "source_states": base.get("source_state_ledger", []), "program_facts": ledger.get("program_facts"),
        "bytes": len(encoded(messages))}
