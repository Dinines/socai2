"""Read the r300 processing replay on 21, then publish its verified local PG snapshot."""
import argparse
import json
import re
import tempfile
from pathlib import Path
from uuid import UUID

import export_processing_audit_batch as exporter
import update_processing_audit as site
from read_processing_audit_20261106 import (
    check_credentials,
    digest,
    fetch,
    require,
    save,
)

SOURCE = "ie-audit-20261106-a1"
REPLAY = "ie-audit-20261106-r300"
ROOT = site.EVIDENCE / REPLAY
KEYS = {"m01", "s02", "u03"}


def operation_ids(card):
    ops = card["operation_keys"]
    require(set(ops) == {"alerts", "incident", "create", "prepare", "start"}
            and len(ops["alerts"]) == len(card["alert_ids"]), "invalid processing operation list")
    return [*ops["alerts"], ops["incident"], ops["create"], ops["prepare"], ops["start"]]


def plans(root):
    original = site.read(site.EVIDENCE / SOURCE / "plan.json")
    raw = (root / "plan.json").read_bytes()
    check_credentials(raw)
    plan = json.loads(raw)
    require(plan.get("batch") == REPLAY and plan.get("source") == SOURCE, "unexpected replay/source batch")
    # The original source marker is still embedded in every ingested alert material.
    source_plan = dict(plan, batch=SOURCE)
    exporter.valid_plan(source_plan)
    previous = {c["key"]: c for c in original["cases"]}
    require({c["key"] for c in plan["cases"]} == KEYS == set(previous), "expected all three original subjects")
    old_ids = {i for c in previous.values() for i in [c["case_id"], *operation_ids(c)]}
    seen = set(old_ids)
    for card in plan["cases"]:
        old = previous[card["key"]]
        require(card["alert_ids"] == old["alert_ids"] and card["incident_id"] == old["incident_id"],
                "replay upstream subject changed")
        ids = [card["case_id"], *operation_ids(card)]
        require(len(set(ids)) == len(ids) and not seen.intersection(ids)
                and all(str(UUID(i)) == i for i in ids), "reused or invalid replay identity")
        seen.update(ids)
    return plan, source_plan, previous, digest(raw)


def verify_case(card, rows, freshness, *, complete):
    exporter.validate_data(card, rows, SOURCE)
    ops = card["operation_keys"]
    stages = {("alert_basic", alert, operation) for alert, operation in zip(card["alert_ids"], ops["alerts"])}
    stages.add(("incident_diagnosis", card["incident_id"], ops["incident"]))
    actual = []
    baselines = []
    for run in rows["runs"]:
        if run["kind"] == "baseline" and run["case_id"] == card["case_id"]:
            baselines.append(run)
        else:
            actual.append((run["kind"], run.get("alert_id") or run.get("incident_id"), run["operation_key"]))
    require(len(actual) == len(set(actual)) and set(actual) <= stages,
            f'{card["key"]}: found a duplicate or foreign processing attempt on the reused upstream subjects')
    require({r["run_id"] for r in freshness} == {r["id"] for r in baselines}
            and len(freshness) == len(baselines), "freshness/Case Run mismatch")
    if complete:
        completed = {"completed", "failed", "cancelled", "unknown"}
        expected_runs = [r for r in rows["runs"] if r["kind"] != "baseline" or r["operation_key"] == ops["start"]]
        require(rows["cases"] and {i["id"] for i in rows["incidents"]} == {card["incident_id"]}
                and set(actual) == stages and any(r.get("started_at") and r["operation_key"] == ops["start"]
                                                  for r in baselines)
                and all(r["state"] in completed for r in expected_runs), f'{card["key"]}: replay is incomplete')
        for table, pointer, target in (
                ("alerts", "latest_triage_id", "alert_assessments"), ("alerts", "latest_explanation_id", "artifacts"),
                ("incidents", "latest_diagnosis_id", "incident_diagnoses"),
                ("cases", "current_assessment_id", "case_assessments")):
            ids = {r["id"] for r in rows[target]}
            require(all(not s.get(pointer) or s[pointer] in ids for s in rows[table]), f"foreign {pointer}")


def export_readback(root, folder):
    require(not folder.exists() and not folder.is_symlink(), "readback destination must be new")
    plan, source, _, plan_hash = plans(root)
    snapshot, records = fetch(source, build_sql=exporter.sql_for)
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent) as temp:
        staged = Path(temp) / "snapshot"
        staged.mkdir()
        cards = []
        for card in plan["cases"]:
            key = card["key"]
            rows = dict(records[key])
            freshness = rows.pop("input_freshness")
            verify_case(card, rows, freshness, complete=False)
            (staged / key).mkdir()
            save(staged / key / "database.json", rows)
            save(staged / key / "input-freshness.json", freshness)
            cards.append({"case": key, "counts": {k: len(v) for k, v in rows.items()}})
        save(staged / "summary.json", {"batch": REPLAY, "registration_source": SOURCE,
             "publication": "replace_three_case_replay", "plan_sha256": plan_hash, "snapshot": snapshot, "cases": cards})
        save(staged / "files.sha256.json", {p.relative_to(staged).as_posix(): digest(p.read_bytes())
                                           for p in sorted(staged.rglob("*.json"))})
        require(not folder.exists() and not folder.is_symlink(), "readback destination appeared")
        staged.rename(folder)
    return {"readback": str(folder), "cases": len(cards)}


def read_attachment(path):
    raw = path.read_bytes()
    check_credentials(raw)
    return json.loads(raw)


def verify_page_views(card, rows, views):
    aids = set(card["alert_ids"])
    iid, cid = card["incident_id"], card["case_id"]
    runs = {r["id"]: r for r in rows["runs"]}
    subjects = [("incident", iid, "incident_diagnosis", "incident_id")]
    subjects.extend((f"alerts/{aid}", aid, "alert_basic", "alert_id") for aid in aids)
    expected = {"incident/members", "case/run", "case/page-data"}
    for path, subject, kind, foreign_key in subjects:
        expected.update({path, path + "/analysis"})
        require(views[path]["facts"]["id"] == subject, "page view has the wrong subject")
        analysis = views[path + "/analysis"]
        attempts = {r["id"] for r in runs.values() if r["kind"] == kind and r[foreign_key] == subject}
        require(analysis["subject_id"] == subject and analysis["kind"] == kind
                and {e["run"]["id"] for e in analysis["entries"]} == attempts
                and len(analysis["entries"]) == len(attempts), "analysis directory contains a foreign or missing attempt")
        for entry in [*analysis["entries"], *([analysis["current"]] if analysis.get("current") else [])]:
            r = entry["run"]
            require(r["id"] in attempts and r["kind"] == kind, "page analysis points at another subject or Run")
            result = entry.get("result")
            if isinstance(result, dict) and result.get("source_run_id"):
                require(result["source_run_id"] == r["id"], "page result belongs to another Run")
        if kind == "alert_basic":
            expected.add(path + "/material")
            metadata = views[path + "/material"]["metadata"]
            alert = next(a for a in rows["alerts"] if a["id"] == subject)
            require(metadata["alert_id"] == subject and metadata["id"] == alert["latest_material_id"],
                    "page material belongs to another alert or revision")
    require(set(views) == expected and {m["id"] for m in views["incident/members"]["items"]} == aids,
            "unexpected page view or incident members")
    run = views["case/run"]["run"]
    require(run["case_id"] == cid and run["id"] in runs and runs[run["id"]]["kind"] == "baseline"
            and runs[run["id"]]["operation_key"] == card["operation_keys"]["start"], "wrong Case Run in page reads")
    page_data = views["case/page-data"]
    assessment = page_data.get("assessment") or {}
    require(assessment.get("id") == rows["cases"][0].get("current_assessment_id")
            and all(s.get("case_id") == cid for s in assessment.get("sources", []))
            and (page_data.get("evidence") or {}).get("artifact_id") == rows["cases"][0].get("current_evidence_artifact_id"),
            "wrong current Case assessment or evidence in page reads")


def cli_receipts(folder, card, rows):
    if not folder.is_dir():
        return {}
    ops = card["operation_keys"]
    cid = card["case_id"]
    jobs = {"I": ("incident", ops["incident"], card["incident_id"]),
            "create": ("case-create", ops["create"], card["incident_id"]),
            "prepare": ("case-prepare", ops["prepare"], cid), "C": ("case-start", ops["start"], cid)}
    jobs.update({f"A{i}": ("alert", op, aid)
                 for i, (op, aid) in enumerate(zip(ops["alerts"], card["alert_ids"]), 1)})
    received = {}
    runs = {r["operation_key"]: r["id"] for r in rows["runs"] if r.get("operation_key")}
    baseline = runs[ops["start"]]
    for path in sorted(folder.glob("*.json")):
        label, suffix = path.stem.rsplit("-", 1)
        require(label in jobs and suffix in {"input", "output"}, "unexpected case receipt filename")
        command, operation, subject = jobs[label]
        value = read_attachment(path)
        if suffix == "input":
            args = value["job"]
            flag = "--incident-id" if label == "create" else "--subject"
            for name, key in [("--operation-key", operation), (flag, subject)]:
                require(args.count(name) == 1 and args[args.index(name) + 1] == key, "wrong CLI receipt scope")
            require(args[0] == command and ("--card" not in args or args[args.index("--card") + 1] == card["key"])
                    and (label != "C" or args[args.index("--run-id") + 1] == baseline), "wrong CLI intent")
        else:
            require(label + "-input" in received, "CLI response without its replay intent")
            receipt = value["receipt"]
            expected_run = runs.get(operation, baseline)
            checks = {"run_id": expected_run, "pending_run_id": baseline,
                      "requested_run_id": baseline if command == "case-start" else None,
                      "operation_key": operation, "case_id": cid, "command": command, "subject": subject,
                      "batch": REPLAY, "card": card["key"]}
            require(all(receipt[k] == expected for k, expected in checks.items() if k in receipt),
                    "CLI response does not belong to the replay")
            if received[label + "-input"].get("timed") is True and receipt != {"error": "missing_job_receipt"}:
                require({"requested_run_id", "operation_key", "batch", "card", "command", "subject"} <= receipt.keys(),
                        "timed CLI receipt missing its replay identity")
            require(any(k in receipt for k in ("run_id", "pending_run_id", "requested_run_id", "operation_key", "case_id"))
                    or receipt == {"error": "missing_job_receipt"}, "unidentified CLI response")
        received[path.stem] = value
    return received


def archive_old(folder, records, output):
    """The three retired pages remain viewable offline independently of the live registry."""
    archived = folder / "retired-pages"
    if archived.exists():
        saved = site.existing(archived / "index.html")
        require(saved == {r["id"]: r for r in records}, "previous page archive differs")
        for row in records:
            file = archived / row["detail"]
            require(digest(file.read_bytes()) == file.stem, "archived detail checksum mismatch")
        return
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        stage = Path(temp) / "retired-pages"
        (stage / "cases").mkdir(parents=True)
        for row in records:
            require(re.fullmatch(r"cases/[0-9a-f]{64}\.html", row["detail"]), "unexpected historical detail path")
            file = output / row["detail"]
            body = file.read_bytes()
            require(digest(body) == file.stem, "existing detail checksum mismatch")
            (stage / row["detail"]).write_bytes(body)
        (stage / "index.html").write_bytes(site.registry_html({r["id"]: r for r in records}, stage, []))
        stage.rename(archived)


def verified_cases(root, folder):
    plan, _, _, plan_hash = plans(root)
    summary = site.read(folder / "summary.json")
    require(summary.get("publication") == "replace_three_case_replay"
            and summary.get("registration_source") == SOURCE, "expected a registered replay snapshot")
    _, records = exporter.read_local(folder, plan, plan_hash)
    pages_file = root / "page-service-readback.json"
    pages = read_attachment(pages_file) if pages_file.is_file() else None
    if pages is not None:
        require(set(pages) == KEYS, "expected page reads for the three replay subjects")
    for card in plan["cases"]:
        rows = dict(records[card["key"]])
        verify_case(card, rows, rows.pop("input_freshness"), complete=True)
        extras = {"snapshot_at": (summary.get("snapshot") or {}).get("at"),
                  "plan": {"processing_batch": REPLAY, "upstream_material_source": SOURCE,
                  **{k: card[k] for k in ("key", "title", "incident_id", "case_id", "alert_ids", "operation_keys",
                                           "window_start", "window_end") if k in card}},
                  "本轮冻结输入索引（数据库 runs）": [{"run_id": r["id"], "kind": r["kind"],
                                        "input_artifact_id": r.get("input_artifact_id")} for r in rows["runs"]]}
        receipts = cli_receipts(root / "receipts" / card["key"], card, rows)
        if receipts:
            extras["receipts"] = receipts
        if pages is not None:
            verify_page_views(card, rows, pages[card["key"]])
            extras["page_reads"] = pages[card["key"]]
        yield REPLAY, card["key"], card["key"], card.get("title"), rows, extras


def publish(root, folder, output):
    new = [site.prepare(*case) for case in verified_cases(root, folder)]
    original = {c["key"]: c for c in site.read(site.EVIDENCE / SOURCE / "plan.json")["cases"]}
    index = output / "index.html"
    with site.publishing(output):
        require(index.is_file(), "expected the existing audit page to replace")
        registry = site.existing(index)
        require(registry is not None, "expected a current audit registry")
        retired = site.retired_records(index)
        relevant = [r for r in registry.values() if r["batch"] == SOURCE and r["key"] in KEYS]
        if relevant:
            require(len(relevant) == 3 and {r["key"] for r in relevant} == KEYS
                    and all(r["scope_id"] == original[r["key"]]["case_id"] for r in relevant),
                    "original registry differs from the three target cases")
            archive_old(root, relevant, output)
            for r in relevant:
                del registry[r["id"]]
                retired.append({k: r[k] for k in ("id", "batch", "key", "scope_id")})
        else:
            archived = site.existing(root / "retired-pages/index.html")
            require(archived and {r["key"] for r in archived.values()} == KEYS
                    and {r["id"] for r in archived.values()} <= {r["id"] for r in retired},
                    "original cases are absent without a verified retirement")
            archive_old(root, list(archived.values()), output)
        (output / "cases").mkdir(exist_ok=True)
        for row, files in new:
            prior = registry.get(row["id"])
            require(site.preserves_history(prior, row), "replay would discard previously published records")
            site.publish_files(output, files)
            registry[row["id"]] = row
        site.atomic_save(index, site.registry_html(registry, output, retired))
    return {"replaced_cases": len(new), "registry_rows": len(registry), "archive": str(root / "retired-pages")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("export", "publish"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--readback", type=Path, help="new export directory or a previously captured snapshot")
    parser.add_argument("--output", type=Path, default=site.OUTPUT, help="existing local 4177 site (publish only)")
    args = parser.parse_args()
    folder = args.readback or args.root / "readback"
    outcome = (export_readback(args.root, folder) if args.action == "export"
               else publish(args.root, folder, args.output))
    print(json.dumps(outcome, ensure_ascii=False))


if __name__ == "__main__":
    main()
