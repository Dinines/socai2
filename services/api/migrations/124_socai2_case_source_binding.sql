-- Incremental change: keep migration 123 and frozen Run inputs unchanged.
BEGIN;
ALTER TABLE socai2.cases ADD COLUMN IF NOT EXISTS source_namespace text;
COMMENT ON COLUMN socai2.cases.source_namespace IS
 'Fixed data identity namespace; not a vendor, connector, or inferred source environment. NULL means unverified legacy scope.';

-- Only unambiguous recorded relationships qualify. Include removed members,
-- even when their pending Run was refreshed before it ever started.
WITH recorded AS (
 SELECT ca.tenant_id,ca.case_id,a.source_namespace FROM socai2.case_alerts ca
 JOIN socai2.alerts a ON a.tenant_id=ca.tenant_id AND a.id=ca.alert_id
 UNION ALL
 SELECT rm.tenant_id,rm.case_id,a.source_namespace FROM socai2.run_members rm
 JOIN socai2.alerts a ON a.tenant_id=rm.tenant_id AND a.id=rm.alert_id WHERE rm.case_id IS NOT NULL
 UNION ALL
 SELECT ci.tenant_id,ci.case_id,i.source_namespace FROM socai2.case_incidents ci
 JOIN socai2.incidents i ON i.tenant_id=ci.tenant_id AND i.id=ci.incident_id
 UNION ALL
 SELECT act.tenant_id,act.subject_case_id,a.source_namespace FROM socai2.activities act
 JOIN socai2.activity_targets t ON t.tenant_id=act.tenant_id AND t.activity_id=act.id
 JOIN socai2.alerts a ON a.tenant_id=t.tenant_id AND a.id=t.alert_id
 WHERE act.action='case_members_changed' AND act.subject_case_id IS NOT NULL
), unambiguous AS (
 SELECT tenant_id,case_id,min(source_namespace) AS namespace FROM recorded
 GROUP BY tenant_id,case_id HAVING count(DISTINCT source_namespace)=1
 AND bool_and(source_namespace IS NOT NULL AND btrim(source_namespace)<>'')
)
UPDATE socai2.cases c SET source_namespace=u.namespace FROM unambiguous u
WHERE c.tenant_id=u.tenant_id AND c.id=u.case_id AND c.source_namespace IS NULL;

CREATE OR REPLACE FUNCTION socai2.keep_case_source_binding() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN
 IF NEW.source_namespace IS NOT NULL AND btrim(NEW.source_namespace)='' THEN
   RAISE EXCEPTION 'case source namespace must not be blank' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND OLD.source_namespace IS NOT NULL
    AND NEW.source_namespace IS DISTINCT FROM OLD.source_namespace THEN
   RAISE EXCEPTION 'case source namespace is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS cases_keep_source_binding ON socai2.cases;
CREATE TRIGGER cases_keep_source_binding BEFORE INSERT OR UPDATE OF source_namespace
ON socai2.cases FOR EACH ROW EXECUTE FUNCTION socai2.keep_case_source_binding();
COMMIT;
