"""Install or verify the approved investigation schema alongside 21's existing public schema."""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Hash of the approved standalone installer with line endings normalized.
BASELINE_SHA = "0a7dabf334c198af7fafd530223e47aa8014f9fb58c7a1cb584c029f681a828e"
ROLES = ("socai2_prod_reader", "socai2_prod_processor", "socai2_prod_ingress")

PROTECTED = """
WITH guarded AS (
 SELECT c.* FROM pg_class c WHERE c.relnamespace='public'::regnamespace
 AND c.relkind IN ('r','p','v','m') AND (c.relname LIKE '%alert%' OR c.relname LIKE '%incident%')
), definitions AS (
 SELECT g.relname AS name,jsonb_build_array(
   g.oid,g.relkind,g.relowner,g.relacl,g.relrowsecurity,g.relforcerowsecurity,g.reloptions,
   (SELECT jsonb_agg(to_jsonb(a) ORDER BY a.attnum) FROM pg_attribute a
    WHERE a.attrelid=g.oid AND a.attnum>0),
   (SELECT jsonb_agg(pg_get_expr(d.adbin,d.adrelid) ORDER BY d.adnum) FROM pg_attrdef d WHERE d.adrelid=g.oid),
   (SELECT jsonb_agg(pg_get_constraintdef(c.oid) ORDER BY c.conname) FROM pg_constraint c WHERE c.conrelid=g.oid),
   (SELECT jsonb_agg(pg_get_indexdef(i.indexrelid) ORDER BY i.indexrelid) FROM pg_index i WHERE i.indrelid=g.oid),
   (SELECT jsonb_agg(to_jsonb(p) ORDER BY p.polname) FROM pg_policy p WHERE p.polrelid=g.oid),
   (SELECT jsonb_agg(jsonb_build_array(t.tgenabled,pg_get_triggerdef(t.oid)) ORDER BY t.tgname)
    FROM pg_trigger t WHERE t.tgrelid=g.oid)
 ) AS definition FROM guarded g
)
SELECT encode(sha256(convert_to(jsonb_object_agg(name,definition)::text,'UTF8')),'hex') AS protected_hash
FROM definitions
"""

PREFLIGHT = r"""
\set ON_ERROR_STOP on
\encoding UTF8
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='45s';
SET LOCAL search_path=pg_catalog;
SELECT pg_advisory_xact_lock(hashtext('socai2'),hashtext('schema-initialization'));
DO $check$ BEGIN
 IF current_database()<>'aisoc' OR current_setting('server_version_num')::int/10000<>16
    OR current_setting('server_encoding')<>'UTF8' OR to_regclass('public.alerts') IS NULL
    OR to_regprocedure('public.current_tenant_id()') IS NULL
    OR NOT EXISTS(SELECT FROM pg_database WHERE datname='aisoc' AND pg_get_userbyid(datdba)='aisoc')
 THEN RAISE EXCEPTION 'Expected the 21 aisoc production PG16 dependencies'; END IF;
 IF to_regnamespace('socai2') IS NULL AND (
   EXISTS(SELECT FROM public.aisoc_schema_migrations WHERE name LIKE '%\_socai2\_%')
   OR to_regnamespace('socai2_ops') IS NOT NULL
   OR EXISTS(SELECT FROM pg_roles WHERE rolname IN ('socai2_prod_reader','socai2_prod_processor','socai2_prod_ingress'))
 ) THEN RAISE EXCEPTION 'Refusing to adopt a partial installation or a pre-existing role'; END IF;
END $check$;
SELECT to_regnamespace('socai2') IS NULL AS fresh_install \gset
"""


def installation():
    text = (HERE / "init_socai2_v1.sql").read_text(encoding="utf-8")
    if hashlib.sha256(text.encode()).hexdigest() != BASELINE_SHA:
        raise ValueError("Approved V1 installer hash mismatch")
    # public dependencies already exist. Only the four signed migration bodies
    # and their ledger/catalog checks run on the shared database.
    start = text.index("-- schema/123_")
    boundary = text.index("\\endif\nSET LOCAL search_path = pg_catalog;", start)
    verify = text.index("\\if :verified", boundary)
    return text[start:boundary], text[boundary + len("\\endif\n"):verify]


def build_sql(mode):
    migrations, verify = installation()
    grants = (HERE / "aisoc21_processing_access.sql").read_text(encoding="utf-8")
    pieces = [PREFLIGHT, PROTECTED + r" \gset before_", r"\echo protected_before :before_protected_hash"]
    if mode == "inspect":
        return "\n".join([*pieces, r"\echo fresh :fresh_install", "ROLLBACK;"])
    if mode == "verify":
        pieces.extend([r"\if :fresh_install", "DO $$ BEGIN RAISE EXCEPTION 'V1 not installed'; END $$;", r"\endif"])
    else:
        pieces.extend([r"\if :fresh_install", "SET LOCAL ROLE aisoc;", migrations,
                       "RESET ROLE;"])
        for role in ROLES:
            pieces.extend([(f"CREATE ROLE {role} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE"
                            " NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 12;"),
                           f"COMMENT ON ROLE {role} IS 'socai2:production:v1';"])
        pieces.extend(["ALTER ROLE socai2_prod_reader IN DATABASE aisoc SET default_transaction_read_only=on;",
                       "SET LOCAL ROLE aisoc;", grants, "RESET ROLE;", r"\endif"])
    pieces.extend([verify, r"\if :verified", r"\echo verified_socai2_v1 29_tables_462_columns",
                   r"\else", "DO $$ BEGIN RAISE EXCEPTION 'Frozen V1 catalog mismatch'; END $$;", r"\endif",
                   (HERE / "verify_aisoc21_processing_access.sql").read_text(encoding="utf-8"),
                   PROTECTED + r" \gset after_", r"\echo protected_after :after_protected_hash",
                   r"SELECT :'before_protected_hash' = :'after_protected_hash' AS protected_same \gset",
                   r"\if :protected_same", "COMMIT;" if mode == "apply" else "ROLLBACK;", r"\else",
                   "DO $$ BEGIN RAISE EXCEPTION 'Existing alert catalog changed'; END $$;", r"\endif"])
    return "\n".join(pieces)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inspect", "rehearse", "apply", "verify"))
    parser.add_argument("--print-sql", action="store_true", help="emit SQL locally without connecting")
    args = parser.parse_args()
    body = build_sql(args.mode) + "\n"
    if args.print_sql:
        sys.stdout.buffer.write(body.encode("utf-8"))
        return 0
    cmd = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=8",
           "sting-infra21", "docker exec -i spirithub-postgres-1 psql -XwAtq -v ON_ERROR_STOP=1 -U spirithub -d aisoc"]
    return subprocess.run(cmd, input=body.encode("utf-8"), check=False, timeout=150).returncode


if __name__ == "__main__":
    raise SystemExit(main())
