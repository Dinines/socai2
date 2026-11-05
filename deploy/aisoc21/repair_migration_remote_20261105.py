"""Backup/apply only candidate migration 125 in the independent next database.

No bootstrap, data rewrite or automatic rollback. Review rollback.sql separately
before using it: it restores pre-migration function definitions, not Run data.
"""
import argparse
import hashlib
import json
from pathlib import Path

from repair_acceptance_remote_20261105 import bootstrap, core_gate, save

HERE = Path(__file__).resolve().parent
SIGNATURES = ["socai2.auto_adopt_baseline_result(uuid,uuid)",
    "socai2.baseline_input_freshness(uuid,uuid)", "socai2.task_feedback_signature(jsonb)"]


def snapshot(service):
    values = ",".join("(" + service.literal(signature) + ")" for signature in SIGNATURES)
    return json.loads(service.pg(service.DATABASE, "BEGIN READ ONLY; SELECT json_build_object("
        "'database',current_database(),'functions',(SELECT json_agg(json_build_object('signature',signature,"
        "'definition',CASE WHEN to_regprocedure(signature) IS NULL THEN NULL ELSE pg_get_functiondef(to_regprocedure(signature)) END)) "
        "FROM (VALUES " + values + ") functions(signature)),"
        "'table_count',(SELECT count(*) FROM information_schema.tables WHERE table_schema='socai2' AND table_type='BASE TABLE'),"
        "'column_count',(SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2')); COMMIT;"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["backup", "apply"])
    args = parser.parse_args()
    plan, release, service = bootstrap()
    sql_file = release / "migrations/125_socai2_baseline_input_freshness.sql"
    digest = hashlib.sha256(sql_file.read_bytes()).hexdigest()
    assert digest == plan["candidate_files"]["migrations/125_socai2_baseline_input_freshness.sql"]
    if args.phase == "backup":
        before = snapshot(service)
        assert before["database"] == "socai2_next_20261104" and (before["table_count"], before["column_count"]) == (29, 459)
        save("migration-125-before", {**before, "migration_sha256": digest})
        statements = ["BEGIN;"]
        # Restore the publication function first, removing its new dependencies.
        for row in before["functions"]:
            if row["definition"]:
                statements.append(row["definition"].rstrip(";\n") + ";")
        for row in before["functions"]:
            if row["definition"] is None:
                statements.append("DROP FUNCTION IF EXISTS " + row["signature"] + ";")
        statements.append("COMMIT;")
        rollback = HERE / "migration-125-rollback.sql"
        with rollback.open("x") as stream:
            stream.write("\n".join(statements) + "\n")
        rollback.chmod(0o600)
        print(json.dumps({"backed_up": True, "functions": len(before["functions"]), "database": before["database"],
            "rollback_requires_separate_review": True, "database_mutations": 0}))
        return
    core_gate(plan)
    before = json.loads((HERE / "migration-125-before.json").read_text())
    assert before["migration_sha256"] == digest
    current = snapshot(service)
    assert all(current[key] == before[key] for key in current), "database functions changed since backup"
    assert (HERE / "migration-125-rollback.sql").is_file()
    save("migration-125-apply-intent", {"database": service.DATABASE, "migration_sha256": digest,
        "scope": "three functions only, no existing Run or business row rewrite"})
    service.pg(service.DATABASE, sql_file.read_text())
    after = snapshot(service)
    assert (after["table_count"], after["column_count"]) == (29, 459)
    assert all(row["definition"] for row in after["functions"])
    save("migration-125-after", after)
    print(json.dumps({"applied": True, "database": service.DATABASE, "tables": 29, "columns": 459}))


if __name__ == "__main__":
    main()
