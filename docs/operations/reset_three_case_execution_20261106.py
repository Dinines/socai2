"""Emit psql for the single approved IE audit reset. Does not connect to any service.

preflight checks fixed archived rows in a read-only snapshot. rehearse exercises the
exact apply transaction and rolls it back. Stop old workers before apply and replay.
Send the emitted ASCII bytes to psql -X -v ON_ERROR_STOP=1 on the verified host.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from uuid import UUID

BASE = Path(__file__).resolve().parent / "evidence/ie-audit-20261106-a1/readback"
BATCH = "ie-audit-20261106-a1"
TENANT = "6aff0ef7-c670-5a84-a2ee-83d73e25b964"
ACTOR = "0fa5e92d-8c36-5a4b-8bd4-8120b15356bd"
SNAPSHOTS = {
    "m01": "42448fcf8bdc76b10b30af585a39e6810b9aec0756c7326b3a2433607ee9f53a",
    "s02": "56f7fd5b8b2f428075571d90229590376fd82dfa3ff4d08e6d5eb2a0b16566fd",
    "u03": "d7a078eaf1786f2b8b04f402aea84a3c8e0c13c434db141e6b736798be5a8a00",
}
KEEP = {"alerts": 4, "alert_materials": 4, "alert_source_refs": 3, "alert_objects": 9,
        "incidents": 3, "incident_alerts": 4}
DELETE = {"alert_assessments": 3, "incident_diagnoses": 3, "cases": 3, "case_alerts": 4,
          "case_incidents": 3, "case_assessments": 3, "case_assessment_sources": 3, "runs": 10,
          "run_members": 4, "run_steps": 62, "artifacts": 126, "activities": 18, "activity_targets": 31}
EMPTY = {"case_assessment_members", "results", "result_members", "tasks", "task_revisions",
         "conversations", "messages", "graph_explorations", "comments", "response_links"}
TABLES = sorted(KEEP.keys() | DELETE.keys() | EMPTY)
GUARDS = {"alert_assessments": "history_immutable", "case_assessments": "history_immutable",
          "case_assessment_sources": "history_immutable", "artifacts": "history_immutable",
          "activities": "history_immutable", "activity_targets": "history_immutable",
          "incident_diagnoses": "terminal_immutable", "run_steps": "terminal_immutable",
          "runs": "run_guard", "run_members": "member_guard"}


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def load_scope():
    rows = {name: {} for name in TABLES}
    for case, checksum in SNAPSHOTS.items():
        raw = (BASE / case / "database.json").read_bytes()
        require(hashlib.sha256(raw).hexdigest() == checksum, f"changed archive: {case}")
        snapshot = json.loads(raw)
        require(set(snapshot) == set(TABLES), "unexpected snapshot schema")
        for table, records in snapshot.items():
            for row in records:
                identity = row["id"]
                require(str(UUID(identity)) == identity and row["tenant_id"] == TENANT, "unexpected identity")
                require(identity not in rows[table], "overlapping case scopes")
                rows[table][identity] = row
    for table, count in {**KEEP, **DELETE}.items():
        require(len(rows[table]) == count + (4 if table == "artifacts" else 0), f"unexpected {table} count")
    require(not any(rows[t] for t in EMPTY), "human, external or result data present")
    require(Counter(r["kind"] for r in rows["runs"].values()) ==
            {"alert_basic": 4, "incident_diagnosis": 3, "baseline": 3}, "unexpected execution kinds")
    require(all(r["requested_by"] == ACTOR for r in rows["runs"].values()), "unexpected run initiator")
    require(all(r["raw_json"]["source"] == BATCH for r in rows["alert_materials"].values()), "unexpected source")
    allowed_actions = {"baseline_prepared", "case_members_changed", "case_created", "baseline_started",
                       "case_associated", "baseline_system_closing_saved"}
    for r in rows["activities"].values():
        actor = r["actor"]
        require(r["action"] in allowed_actions and r["subject_case_id"] in rows["cases"], "unexpected activity")
        if r["action"] == "baseline_system_closing_saved":
            require(actor["type"] == "service" and actor["service_name"] == "socai2.baseline-closing",
                    "unexpected closing service")
        else:
            require(actor["type"] == "user" and actor["user_id"] == ACTOR, "unexpected actor")
    targets = {table: sorted(rows[table]) for table in DELETE}
    sources = [r for r in rows["artifacts"].values() if r["run_id"] is None]
    require(len(sources) == 4 and {r["alert_id"] for r in sources} == set(rows["alerts"]) and
            all(r["kind"] == "source_snapshot" and r["schema_version"] == "fusion.first-result.v1" for r in sources),
            "unexpected ingestion artifacts")
    targets["artifacts"] = sorted(i for i, r in rows["artifacts"].items() if r["run_id"] in rows["runs"])
    require(len(targets["artifacts"]) == DELETE["artifacts"], "unexpected execution artifacts")
    return rows, targets


def uuids(ids):
    return "ARRAY[" + ",".join("'" + str(UUID(i)) + "'" for i in ids) + "]::uuid[]"


def selected(ids):
    return f"tenant_id='{TENANT}'::uuid AND id=ANY({uuids(ids)})"


def sql_for(mode):
    require(mode in {"preflight", "rehearse", "apply"}, "unexpected mode")
    rows, targets = load_scope()
    # ASCII JSON avoids shell transport encoding differences. Exact JSONB equality also checks mutable values.
    expected = json.dumps(rows, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    require("$frozen$" not in expected and "$audit$" not in expected, "SQL delimiter collision")
    preflight = mode == "preflight"
    lock = "" if preflight else "LOCK TABLE " + ", ".join("socai2." + t for t in TABLES) + " IN ACCESS EXCLUSIVE MODE;"
    sql = [r"\set ON_ERROR_STOP on", "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;" if preflight else "BEGIN;",
           "SET LOCAL search_path=pg_catalog; SET LOCAL TIME ZONE 'UTC'; SET LOCAL DateStyle='ISO, MDY';",
           "SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='120s';",
           f"SET LOCAL app.current_tenant_id='{TENANT}';",
           """DO $identity$ BEGIN
  IF current_database()<>'socai2_processing_handoff' OR current_user<>'spirithub'
     OR current_setting('server_version_num')::int / 10000 <> 16
     OR current_setting('session_replication_role')<>'origin'
     OR NOT EXISTS (SELECT FROM pg_roles WHERE rolname=current_user AND (rolsuper OR rolbypassrls)) THEN
    RAISE EXCEPTION 'wrong database, server or maintenance identity';
  END IF;
END $identity$;""", lock]
    check = """DO $audit$
DECLARE original jsonb := $frozen$__SNAPSHOT__$frozen$::jsonb;
    scoped_ids text[]; tbl text; expected_rows jsonb; offender uuid; mismatch int;
BEGIN
  IF public.current_tenant_id() IS DISTINCT FROM '__TENANT__'::uuid
     OR EXISTS (SELECT FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()
          AND usename='socai2_processing_job')
     OR EXISTS (SELECT FROM pg_prepared_xacts WHERE database=current_database()) THEN
    RAISE EXCEPTION 'unexpected tenant or live processing session/prepared transaction';
  END IF;
  IF (SELECT array_agg(relname::text ORDER BY relname::text COLLATE "C") FROM pg_class
       WHERE relnamespace='socai2'::regnamespace AND relkind IN ('r','p')) IS DISTINCT FROM
     (SELECT array_agg(k ORDER BY k COLLATE "C") FROM jsonb_object_keys(original) k)
     OR EXISTS (SELECT FROM pg_class WHERE relnamespace='socai2'::regnamespace AND relkind IN ('r','p')
         AND (NOT relrowsecurity OR NOT relforcerowsecurity OR relkind<>'r'))
     OR EXISTS (SELECT FROM pg_constraint c JOIN pg_class parent ON parent.oid=c.confrelid
         JOIN pg_class child ON child.oid=c.conrelid WHERE c.contype='f'
         AND parent.relnamespace='socai2'::regnamespace AND child.relnamespace<>parent.relnamespace)
     OR EXISTS (SELECT FROM pg_trigger g JOIN pg_class t ON t.oid=g.tgrelid
         WHERE t.relnamespace='socai2'::regnamespace AND (g.tgenabled NOT IN ('O','A')
          OR (NOT g.tgisinternal AND (g.tgname, g.tgfoid) NOT IN (
           ('identity_immutable','socai2.guard_identity()'::regprocedure),
           ('history_immutable','socai2.reject_history_mutation()'::regprocedure),
           ('terminal_immutable','socai2.guard_terminal_record()'::regprocedure),
           ('run_guard','socai2.guard_run()'::regprocedure),
           ('member_guard','socai2.guard_run_member()'::regprocedure),
           ('member_creation_scope','socai2.check_new_member_transaction()'::regprocedure),
           ('case_membership_lock','socai2.lock_case_membership()'::regprocedure),
           ('publication_scope','socai2.check_publication_scope()'::regprocedure),
           ('cases_keep_source_binding','socai2.keep_case_source_binding()'::regprocedure),
           ('cases_evidence_pointer','socai2.check_case_evidence_pointer()'::regprocedure)))))
     OR EXISTS (SELECT FROM pg_rewrite w JOIN pg_class t ON t.oid=w.ev_class
         WHERE t.relnamespace='socai2'::regnamespace AND t.relkind IN ('r','p'))
     OR EXISTS (SELECT FROM pg_constraint c JOIN pg_class t ON t.oid=c.confrelid
         WHERE c.contype='f' AND t.relnamespace='socai2'::regnamespace
         AND (NOT c.convalidated OR c.confdeltype NOT IN ('r','a'))) THEN
    RAISE EXCEPTION 'unexpected schema, protected relation, trigger, rule or referential action';
  END IF;
  SELECT array_agg(DISTINCT i) INTO scoped_ids FROM jsonb_each(original) e,
      LATERAL jsonb_object_keys(e.value) i;
  FOR tbl,expected_rows IN SELECT key,value FROM jsonb_each(original) LOOP
    EXECUTE format('SELECT count(*) FROM jsonb_each($1) e LEFT JOIN socai2.%I r
       ON r.id=e.key::uuid WHERE to_jsonb(r) IS DISTINCT FROM e.value',tbl)
       INTO mismatch USING expected_rows;
    IF mismatch<>0 THEN RAISE EXCEPTION 'frozen subject changed in %: % missing or unequal rows',tbl,mismatch; END IF;
    -- Out-of-scope relations can bind to an ID via FK columns OR JSON evidence and receipts.
    -- Check all tenants with the named maintenance login; every mutation still includes the fixed tenant.
    EXECUTE format('SELECT r.id FROM socai2.%I r WHERE NOT ($1 ? r.id::text)
        AND EXISTS (SELECT FROM regexp_matches(to_jsonb(r)::text,
        ''[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'',
        ''g'') AS hit(piece) WHERE lower(piece[1])=ANY($2)) LIMIT 1',tbl)
       INTO offender USING expected_rows,scoped_ids;
    IF offender IS NOT NULL THEN RAISE EXCEPTION 'external scope reference: % %',tbl,offender; END IF;
  END LOOP;
END $audit$;"""
    sql.append(check.replace("__TENANT__", TENANT).replace("__SNAPSHOT__", expected))
    for table, guard in GUARDS.items():
        sql.append(f"""DO $guard$ BEGIN IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid='socai2.{table}'::regclass
            AND tgname='{guard}' AND NOT tgisinternal AND tgenabled='O') THEN
            RAISE EXCEPTION 'missing expected guard on {table}'; END IF; END $guard$;""")
    summary = {"delete": DELETE, "preserve": {**KEEP, "fusion.first-result.v1": 4}}
    sql.append(f"SELECT '{json.dumps(summary, sort_keys=True)}'::jsonb AS verified_scope;")
    if preflight:
        return "\n".join(sql + ["ROLLBACK;"])
    for table, guard in GUARDS.items():
        sql.append(f"ALTER TABLE socai2.{table} DISABLE TRIGGER {guard};")
    for table, fields in (("alerts", ("latest_triage_id", "latest_explanation_id")),
                          ("incidents", ("latest_diagnosis_id",))):
        sql.append(f"UPDATE socai2.{table} SET " + ", ".join(f"{f}=NULL" for f in fields) +
                   f", row_version=row_version+1, business_updated_at=transaction_timestamp() WHERE {selected(rows[table])} AND (" +
                   " OR ".join(f"{f} IS NOT NULL" for f in fields) + ");")
    # case_membership_lock must see its live parent. Other cyclic FK references (runs <-> artifacts,
    # steps <-> artifacts, cases <-> assessments) are removed as a single PostgreSQL statement;
    # ON DELETE RESTRICT triggers still run with the final statement state.
    sql.append("DELETE FROM socai2.case_alerts WHERE " + selected(targets["case_alerts"]) + ";")
    batches = [f"deleted_{t} AS (DELETE FROM socai2.{t} WHERE {selected(ids)} RETURNING id)"
               for t, ids in targets.items() if t != "case_alerts"]
    sql.append("WITH " + ",\n".join(batches) + "\nSELECT " +
               ", ".join(f"(SELECT count(*) FROM deleted_{t}) AS {t}" for t in targets if t != "case_alerts") + ";")
    sql.append("SET CONSTRAINTS ALL IMMEDIATE;")
    for table, guard in GUARDS.items():
        sql.append(f"ALTER TABLE socai2.{table} ENABLE TRIGGER {guard};")
    # Compare retained rows field by field; only the declared pointer/clock/version transition is permitted.
    for table in (*KEEP, "artifacts"):
        originals = [r for i, r in rows[table].items() if i not in targets.get(table, ())]
        fields = {"alerts": ["latest_triage_id", "latest_explanation_id"], "incidents": ["latest_diagnosis_id"]}.get(table, [])
        for row in originals:
            new = row.copy()
            changed = any(new[f] is not None for f in fields)
            if changed:
                new.update(dict.fromkeys(fields))
                new["row_version"] += 1
                del new["business_updated_at"]
            data = json.dumps(new, ensure_ascii=True, separators=(",", ":"))
            projection = "to_jsonb(t)-'business_updated_at'" if changed else "to_jsonb(t)"
            clock = " AND business_updated_at=transaction_timestamp()" if changed else ""
            require("$frozen$" not in data and "$proof$" not in data, "SQL delimiter collision")
            sql.append(f"""DO $proof$ BEGIN IF NOT EXISTS (SELECT FROM socai2.{table} t WHERE {selected([row['id']])}
                 AND {projection}=$frozen${data}$frozen$::jsonb{clock}) THEN
                 RAISE EXCEPTION 'preservation mismatch: {table} {row['id']}'; END IF; END $proof$;""")
    for table, ids in targets.items():
        sql.append(f"""DO $gone$ BEGIN IF EXISTS (SELECT FROM socai2.{table} WHERE {selected(ids)}) THEN
            RAISE EXCEPTION 'unremoved rows in {table}'; END IF; END $gone$;""")
    sql.append("ROLLBACK;" if mode == "rehearse" else "COMMIT;")
    return "\n".join(sql)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "rehearse", "apply"))
    parser.add_argument("--confirm-batch", help="required for emitting the committing SQL")
    parser.add_argument("--output", type=Path, help="write a new ASCII psql file instead of stdout")
    args = parser.parse_args()
    if args.mode == "apply" and args.confirm_batch != BATCH:
        parser.error("apply requires --confirm-batch " + BATCH)
    body = sql_for(args.mode) + "\n"
    if args.output is None:
        sys.stdout.buffer.write(body.encode("ascii"))
    else:
        with args.output.open("x", encoding="ascii", newline="\n") as out:
            out.write(body)


if __name__ == "__main__":
    main()
