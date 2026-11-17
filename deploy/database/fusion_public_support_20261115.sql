-- Native socai2 Fusion support only. Original migrations remain unchanged.
-- 102 contributes its sessions definition/policy, not public.alerts alterations.
-- Upstream default-role grants are omitted; only the configured roles are touched.
-- This bootstrap does not mark the full platform migrations as installed.
\set ON_ERROR_STOP on
BEGIN;
SELECT current_database()=:'expected_database'
 AND to_regclass('socai2.alerts') IS NOT NULL
 AND to_regclass('public.tenants') IS NOT NULL
 AND EXISTS(SELECT FROM pg_roles WHERE rolname=:'analysis_ingress_role'
   AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb)) AS fusion_ready \gset
\if :fusion_ready
SELECT set_config('lock_timeout', :'analysis_ingress_lock_timeout', true);
SELECT set_config('statement_timeout', :'analysis_ingress_statement_timeout', true);
SET LOCAL ROLE :"function_owner";
SET LOCAL search_path=public;
-- Source: services/api/migrations/053_dead_letters.sql
-- SHA256: 27ae740a64c4e56edbb54fb18b45d244391ea52f82d1d4a138c000192812c87c
-- Dead letters, made visible.
--
-- The fusion consumer routes poison events to a dead-letter queue and has
-- done since the DLQ landed. Nothing ever read it back: `LoggingDLQ` writes
-- a log line, `KafkaDLQ` writes to a topic with no consumer, and
-- `InMemoryDLQ` forgets on restart. So an operator could not answer "what
-- did we drop, and why" — which is the one question a dead-letter queue
-- exists to answer.
--
-- Dropped events are rare by construction (a poison message is a bug, not
-- traffic), so this table stays small and a plain B-tree index is enough.
-- It is deliberately not partitioned: partitioning a table that should have
-- tens of rows a week optimises for a failure mode that would itself be the
-- incident.

CREATE TABLE IF NOT EXISTS aisoc_dead_letters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Nullable because a message can be rejected *before* its tenant is
    -- known — a malformed envelope has no tenant, and recording a guess
    -- would put another tenant's name on someone else's bad data.
    tenant_id       UUID REFERENCES tenants(id) ON DELETE CASCADE,

    topic           TEXT        NOT NULL,
    reason          TEXT        NOT NULL,
    schema_version  TEXT        NOT NULL DEFAULT 'unknown',

    -- An excerpt, never the whole payload. The payload is what was rejected,
    -- so it is untrusted by definition and may be large or hostile; storing
    -- all of it turns this table into an unbounded sink for exactly the
    -- content the pipeline refused.
    payload_excerpt TEXT        NOT NULL DEFAULT '',
    source_event_id TEXT,

    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Triage state. A dead letter nobody acknowledged is different from one
    -- someone looked at and decided was expected.
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by TEXT
);

-- The query an operator actually runs: recent drops for my tenant, newest
-- first.
CREATE INDEX IF NOT EXISTS idx_dead_letters_tenant_time
    ON aisoc_dead_letters (tenant_id, occurred_at DESC);

-- And the aggregate that turns a list into a finding: which reason is
-- responsible for most of them.
CREATE INDEX IF NOT EXISTS idx_dead_letters_reason
    ON aisoc_dead_letters (reason, occurred_at DESC);

COMMENT ON TABLE aisoc_dead_letters IS
    'Events the pipeline refused, with the reason. Written by services/fusion; '
    'read by GET /api/v1/health/dead-letters. Subject to the tenant retention '
    'policy like any other tenant-scoped data.';

-- Source: services/api/migrations/102_sessions.sql
-- SHA256: 96ff853504761f3e980f85ae154fd7a5b72dad0527c9754cca6d31eeea8244c5
-- Depth plan 2.4: sessions per principal.
--
-- Why this table is in Postgres and not only in the graph: ADR-0010
-- (docs/decisions/0010-entity-and-session-context-in-core.md). Neo4j measured
-- 696.8 MiB resident for 20,000 sessions, which is 42.2% of what the CORE
-- profile has left at the moment it is triaging an alert; the same rows here
-- cost +10.9 MiB in a container CORE already runs. The graph still gets the
-- Session nodes when it is enabled, written from the same ingest-side
-- projection, so `full` keeps one traversable graph and CORE keeps the
-- context on the alert.
--
-- What a row is
-- -------------
-- One session as a *vendor* understands it, or as close as the vendor lets us
-- get. `services/ingest/internal/activity/session.go` reads the key per event
-- and labels how strong it is; this table is the stateful half — start, end,
-- event count, and the walk up an assumed-role chain.
--
-- `key_kind` is stored rather than flattened away because the four kinds are
-- not interchangeable. Okta's externalSessionId is a durable session; Entra's
-- correlationId groups one sign-in flow and nothing the resulting session went
-- on to do; a derived key is principal + address + client with an idle gap. A
-- surface that renders all four as "session" is lying with a precise number,
-- so the column is NOT NULL and constrained to the producer's closed set.
--
-- `id` is deterministic — uuidv5 over (tenant, source, key) — so the lake row,
-- the graph node and this row agree on one identifier without any of the three
-- coordinating, and a Kafka replay upserts the same row instead of minting a
-- second session for events that already have one.

CREATE TABLE IF NOT EXISTS sessions (
    id                     uuid PRIMARY KEY,
    tenant_id              uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- As the vendor spells it, never a hash: an analyst pastes this into the
    -- vendor's own console, and a value that exists nowhere else cannot be
    -- looked up anywhere.
    session_key            text NOT NULL,
    key_kind               text NOT NULL,
    -- The vendor field the key was read from, so a reviewer can check the
    -- derivation against the vendor's documentation without reading Go.
    key_source             text NOT NULL DEFAULT '',
    source                 text NOT NULL,

    principal              text,
    -- The person behind the session. On a chained session this is resolved by
    -- walking `parent_session_id`, because the second hop's own events name
    -- only the role. NULL is the honest answer when nothing named a person;
    -- the role name is never read as one.
    originating_human      text,
    originating_human_source text,

    first_seen_at          timestamptz NOT NULL,
    last_seen_at           timestamptz NOT NULL,
    -- Set when the session is known to have ended: a vendor logout event, or
    -- the idle gap closing a derived session. NULL means still open *or*
    -- unknown, which are the same thing from here and are not claimed apart.
    ended_at               timestamptz,
    ended_reason           text,

    event_count            bigint NOT NULL DEFAULT 0,
    -- The strongest actor kind seen on the session's events, from the 2.2
    -- projection. A session that is sometimes a human and sometimes a token
    -- is the interesting case, so this is the maximum rather than the first.
    actor_kinds            jsonb NOT NULL DEFAULT '[]'::jsonb,
    highest_severity       text,
    source_ips             jsonb NOT NULL DEFAULT '[]'::jsonb,

    -- The assumed-role chain. ON DELETE SET NULL rather than CASCADE: losing
    -- the parent must not delete the child's events, it must only make the
    -- chain unresolvable, which is what actually happened.
    parent_session_id      uuid REFERENCES sessions(id) ON DELETE SET NULL,
    -- How the parent edge was established, so a chain built from a
    -- caller-chosen roleSessionName is distinguishable from one built from
    -- AWS's own sourceIdentity.
    parent_link_source     text,

    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT sessions_key_kind_check CHECK (
        key_kind IN ('vendor_session', 'vendor_credential', 'vendor_flow', 'derived')
    )
);

-- The upsert's conflict target. A key is only unique within its source: an
-- Okta session id and a GitHub token hash have no shared namespace, and two
-- tenants may legitimately observe the same vendor identifier.
CREATE UNIQUE INDEX IF NOT EXISTS sessions_tenant_source_key_idx
    ON sessions (tenant_id, source, session_key);

-- "What else did this person do" — the question the chain exists to answer.
CREATE INDEX IF NOT EXISTS sessions_tenant_human_idx
    ON sessions (tenant_id, originating_human, last_seen_at DESC)
    WHERE originating_human IS NOT NULL;

-- "What else did this principal do", and the idle sweep's scan.
CREATE INDEX IF NOT EXISTS sessions_tenant_principal_idx
    ON sessions (tenant_id, principal, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS sessions_open_idx
    ON sessions (tenant_id, last_seen_at)
    WHERE ended_at IS NULL;

CREATE INDEX IF NOT EXISTS sessions_parent_idx
    ON sessions (parent_session_id)
    WHERE parent_session_id IS NOT NULL;

COMMENT ON TABLE sessions IS
    'One session per principal, keyed by the strongest identifier the source offers. key_kind carries '
    'how strong that is and is never flattened away: a vendor session, the credential that is the '
    'session, one sign-in flow, or a derived principal+address+client grouping closed on an idle gap.';

COMMENT ON COLUMN sessions.parent_session_id IS
    'The session that issued this one, from an STS AssumeRole response. The edge exists only on the '
    'issuing call, so it is unrecoverable once that record ages out of the lake.';

-- Written out rather than looped with `format()`: the loop was shorter and it
-- made the policy invisible to `grep` and to
-- `scripts/check_tenant_query_predicates.py`, which reads migrations to learn
-- which tables carry one. A control a tool cannot see is a control nobody can
-- audit.
DO $$
BEGIN
    EXECUTE 'ALTER TABLE sessions ENABLE ROW LEVEL SECURITY';
    EXECUTE 'ALTER TABLE sessions FORCE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS tenant_isolation ON sessions';
    EXECUTE
        'CREATE POLICY tenant_isolation ON sessions '
        'USING (tenant_id = current_tenant_id() OR current_tenant_id() IS NULL) '
        'WITH CHECK (tenant_id = current_tenant_id())';

END
$$;

-- Source: services/api/migrations/110_ai_assets.sql
-- SHA256: dacc369e7ff0c0bda7add66f5b311b308d559296d58a095cce5e51a42c1703d5
-- 110: the AI estate a tenant actually runs, as opposed to the one it registered.
--
-- Depth plan 6.1.
--
-- `aisoc_mcp_servers` (069) is a *declaration*: the MCP servers an operator
-- chose to trust. This table is an *observation*: every AI app, coding agent,
-- MCP server, IDE extension, provider key and OAuth grant AiSOC has seen,
-- whether or not anybody declared it. The two have to be separate, because
-- the interesting row is the one in this table and not in that one — the
-- coding agent nobody registered, running on a laptop, holding a key.
--
-- Why one table with a `kind` rather than six tables
-- --------------------------------------------------
-- Every question an analyst asks of this data is asked across the kinds, not
-- within one: what does this person run, what runs on this device, what has
-- appeared since Friday. Six tables would make each of those a six-way union
-- and would let the columns drift apart. The kinds differ in what identifies
-- them, which is `external_id`, and in what they carry, which is `attributes`.
--
-- Why `first_seen_at` and `last_seen_at` are columns and not derived
-- ------------------------------------------------------------------
-- Derived from the lake they would be a scan over every AI event ever
-- archived, per row, per page load. They are also the two fields the page is
-- sorted and filtered by. The recorder maintains them with `LEAST`/`GREATEST`
-- on conflict so a late-arriving event cannot move `first_seen_at` forward.
--
-- Why the person, the device and the permissions are nullable
-- -----------------------------------------------------------
-- Because the source often does not know. A gateway log names the agent and
-- the model and nothing about the laptop; an osquery row names the device and
-- the process and nothing about the provider account. Writing an empty string
-- or a placeholder would make "we did not learn this" indistinguishable from
-- "there is nobody", and the console renders the two differently: an unlinked
-- asset is a finding, not a blank cell.
--
-- `effective_permissions` holds what Phase 2.5's resolver returned for the
-- linked principal at the time of the last sighting, as a snapshot rather
-- than a join. A join would re-resolve on every read and would silently
-- change history; a snapshot answers "what could this agent reach when we
-- last saw it", which is the question an incident asks.
--
-- Why `risk_score` is stored rather than computed in the query
-- ------------------------------------------------------------
-- It is computed by one function (`app/services/ai_inventory.py::score_risk`)
-- on write, so the console, the API and any future detection all read the
-- same number. Two surfaces computing a risk two ways is how `mttr_hours` and
-- `cases_closed_7d` came to disagree about the same rows.

CREATE TABLE IF NOT EXISTS aisoc_ai_assets (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id             UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- The six kinds the plan names. Constrained in the database because a
    -- seventh value arriving from a new discovery source should fail loudly
    -- at the write rather than appear as an unfilterable row in the console.
    kind                  TEXT        NOT NULL CHECK (kind IN (
                                          'ai_app',
                                          'coding_agent',
                                          'mcp_server',
                                          'ide_extension',
                                          'provider_key',
                                          'oauth_grant'
                                      )),

    -- Stable within (tenant, kind): the agent id from runtime telemetry, the
    -- process name plus device from endpoint discovery, the key id from a
    -- provider's audit log, the client id of an OAuth grant.
    external_id           TEXT        NOT NULL,
    display_name          TEXT,
    vendor                TEXT,

    -- Which discovery path produced this row. Carried because the three see
    -- different things and an analyst needs to know which one is talking:
    -- `ai_runtime` knows the model and the tools and not the device,
    -- `endpoint` knows the device and the binary and not the model,
    -- `provider_audit` knows the account and the key and neither.
    discovery_source      TEXT        NOT NULL CHECK (discovery_source IN (
                                          'ai_runtime',
                                          'endpoint',
                                          'provider_audit',
                                          'oauth_audit',
                                          'declared'
                                      )),

    -- Links. NULL means "not learned", never "none" — see the header.
    principal             TEXT,
    device                TEXT,
    effective_permissions JSONB,

    -- Everything kind-specific: model, provider, tool names, extension
    -- version, scopes granted. Indexed as a whole rather than per key,
    -- because the shape differs per kind by design.
    attributes            JSONB       NOT NULL DEFAULT '{}'::jsonb,

    risk_score            INTEGER     NOT NULL DEFAULT 0 CHECK (risk_score BETWEEN 0 AND 100),
    -- Why the row scored what it scored, so the console can show it and a
    -- reviewer can disagree with a reason rather than with a number.
    risk_reasons          JSONB       NOT NULL DEFAULT '[]'::jsonb,

    -- An operator's judgement, independent of the score. `sanctioned` is the
    -- allowlist the shadow-AI detection reads; it defaults to NULL, meaning
    -- nobody has decided, which is different from "reviewed and refused".
    sanctioned            BOOLEAN,

    first_seen_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    observation_count     BIGINT      NOT NULL DEFAULT 1,

    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- The upsert key. A device is part of identity for the kinds where the
    -- same binary on two laptops is two assets (a coding agent, an IDE
    -- extension) and NULL for the kinds where it is one (a provider key).
    --
    -- NULLS NOT DISTINCT is load-bearing and is the whole reason this is a
    -- named constraint. Under the default, NULL never equals NULL, so every
    -- sighting of a provider key — which has no device — would insert a new
    -- row rather than update the one before it, and the inventory would grow
    -- one row per event while `first_seen_at` reset on each. The same
    -- mistake was made in 074 and is spelled the same way here. PostgreSQL
    -- 15 or later; the tree pins 16.
    CONSTRAINT aisoc_ai_assets_identity
        UNIQUE NULLS NOT DISTINCT (tenant_id, kind, external_id, device)
);

COMMENT ON TABLE aisoc_ai_assets IS
    'Observed AI estate: apps, coding agents, MCP servers, IDE extensions, '
    'provider keys and OAuth grants, with the person and device behind each. '
    'Written by the fusion recorder from AI runtime, endpoint and provider '
    'audit telemetry. Distinct from aisoc_mcp_servers, which is what an '
    'operator declared rather than what is running.';
COMMENT ON COLUMN aisoc_ai_assets.principal IS
    'The person the asset acted for, when a source said so. NULL means not '
    'learned, never "nobody" — the console renders an unlinked asset as a '
    'finding rather than a blank cell.';
COMMENT ON COLUMN aisoc_ai_assets.effective_permissions IS
    'Snapshot of what the Phase 2.5 resolver returned for the linked '
    'principal at the last sighting. A snapshot and not a join, so history '
    'does not change under a later permission edit.';
COMMENT ON COLUMN aisoc_ai_assets.sanctioned IS
    'Operator judgement. NULL means undecided, which is not the same as '
    'reviewed-and-refused; the shadow-AI detection reads TRUE as an allowlist.';

CREATE INDEX IF NOT EXISTS idx_ai_assets_tenant_last_seen
    ON aisoc_ai_assets (tenant_id, last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_assets_tenant_kind
    ON aisoc_ai_assets (tenant_id, kind);
CREATE INDEX IF NOT EXISTS idx_ai_assets_tenant_principal
    ON aisoc_ai_assets (tenant_id, principal);

-- Row-level security. The `OR current_tenant_id() IS NULL` arm is what lets
-- the cross-tenant workers (retention purge, tenant deletion) reach this
-- table; dropping it makes those silently see nothing. FORCE so the table
-- owner, which is the role that runs migrations, does not walk past it.
ALTER TABLE aisoc_ai_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE aisoc_ai_assets FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS aisoc_ai_assets_tenant ON aisoc_ai_assets;
CREATE POLICY aisoc_ai_assets_tenant ON aisoc_ai_assets
    USING (tenant_id = current_tenant_id() OR current_tenant_id() IS NULL);


RESET ROLE;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.sessions,public.aisoc_dead_letters,public.aisoc_ai_assets TO :"analysis_ingress_role";
GRANT SELECT ON public.sessions,public.aisoc_dead_letters,public.aisoc_ai_assets TO :"reader_role";
GRANT SELECT ON public.connectors TO :"reader_role";
COMMIT;
\else
ROLLBACK;
DO $failure$ BEGIN RAISE EXCEPTION 'fusion_support_target_invalid'; END $failure$;
\endif
