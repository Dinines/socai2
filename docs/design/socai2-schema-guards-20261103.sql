-- Included by the generated migration inside its transaction.
CREATE OR REPLACE FUNCTION socai2.guard_identity() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id THEN
  RAISE EXCEPTION 'socai2 identity is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $fn$;

CREATE OR REPLACE FUNCTION socai2.reject_history_mutation() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
BEGIN
 RAISE EXCEPTION 'socai2 history is append-only: %',TG_TABLE_NAME USING ERRCODE='23514';
END $fn$;

CREATE OR REPLACE FUNCTION socai2.guard_terminal_record() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
BEGIN
 IF TG_OP='DELETE' OR OLD.state IN ('completed','failed','timeout','cancelled','skipped') THEN
  RAISE EXCEPTION 'socai2 terminal record is immutable' USING ERRCODE='23514';
 END IF;
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id THEN
  RAISE EXCEPTION 'socai2 identity is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $fn$;

CREATE OR REPLACE FUNCTION socai2.guard_run() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE current_scope bigint;
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'run history cannot be deleted' USING ERRCODE='23514';
 END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.kind='baseline' AND NEW.state<>'pending_update' THEN
   RAISE EXCEPTION 'baseline must be created pending, then claimed atomically' USING ERRCODE='23514';
  END IF;
 ELSE
  IF ROW(NEW.id,NEW.tenant_id,NEW.kind,NEW.case_id,NEW.alert_id,NEW.incident_id)
     IS DISTINCT FROM ROW(OLD.id,OLD.tenant_id,OLD.kind,OLD.case_id,OLD.alert_id,OLD.incident_id) THEN
   RAISE EXCEPTION 'run identity and parent are immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.state IN ('completed','failed','cancelled') THEN
   RAISE EXCEPTION 'terminal run is immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.state='pending_update' AND NEW.state NOT IN ('pending_update','running','cancelled')
     OR OLD.state='running' AND NEW.state NOT IN ('running','unknown','completed','failed','cancelled')
     OR OLD.state='unknown' AND NEW.state NOT IN ('unknown','completed','failed','cancelled') THEN
   RAISE EXCEPTION 'invalid run state transition' USING ERRCODE='23514';
  END IF;
  IF OLD.state<>'pending_update' AND
     (to_jsonb(NEW)-ARRAY['state','ended_at','stop_reason','stop_detail','delivery_state','row_version'])
      IS DISTINCT FROM
     (to_jsonb(OLD)-ARRAY['state','ended_at','stop_reason','stop_detail','delivery_state','row_version']) THEN
   RAISE EXCEPTION 'claimed run input is frozen' USING ERRCODE='23514';
  END IF;
 END IF;
 IF NEW.kind='baseline' AND NEW.state='running' AND TG_OP='UPDATE' AND OLD.state='pending_update' THEN
  -- API acquires Case then Run before this UPDATE; this lock also protects direct SQL writers.
  SELECT scope_revision INTO current_scope FROM socai2.cases
   WHERE tenant_id=NEW.tenant_id AND id=NEW.case_id FOR UPDATE;
  IF NOT FOUND OR current_scope<>NEW.scope_revision THEN
   RAISE EXCEPTION 'case scope changed before claim' USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM socai2.run_members WHERE tenant_id=NEW.tenant_id AND run_id=NEW.id) THEN
   RAISE EXCEPTION 'cannot claim empty baseline' USING ERRCODE='23514';
  END IF;
  IF EXISTS(
   (SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id
    EXCEPT SELECT alert_id FROM socai2.run_members WHERE tenant_id=NEW.tenant_id AND run_id=NEW.id)
   UNION ALL
   (SELECT alert_id FROM socai2.run_members WHERE tenant_id=NEW.tenant_id AND run_id=NEW.id
    EXCEPT SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id)
  ) THEN RAISE EXCEPTION 'baseline must cover complete current case' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $fn$;

CREATE OR REPLACE FUNCTION socai2.lock_case_membership() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE cid uuid; tid uuid;
BEGIN
 IF TG_OP='UPDATE' AND ROW(NEW.case_id,NEW.alert_id) IS DISTINCT FROM ROW(OLD.case_id,OLD.alert_id) THEN
  RAISE EXCEPTION 'change membership using delete+insert under sorted Case locks' USING ERRCODE='23514';
 END IF;
 IF TG_OP='DELETE' THEN cid:=OLD.case_id;tid:=OLD.tenant_id;
 ELSE cid:=NEW.case_id;tid:=NEW.tenant_id; END IF;
 PERFORM 1 FROM socai2.cases WHERE tenant_id=tid AND id=cid FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'case not found in tenant' USING ERRCODE='23503'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $fn$;

CREATE OR REPLACE FUNCTION socai2.guard_run_member() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE parent_state text; rid uuid; tid uuid;
BEGIN
 IF TG_OP='DELETE' THEN rid:=OLD.run_id;tid:=OLD.tenant_id; ELSE rid:=NEW.run_id;tid:=NEW.tenant_id; END IF;
 SELECT state INTO parent_state FROM socai2.runs WHERE tenant_id=tid AND id=rid FOR UPDATE;
 IF NOT FOUND THEN
  -- Preallocated AI Run identity: children, parent and input publish in one transaction.
  -- The deferred FK and member_creation_scope trigger prevent a different transaction
  -- from appending members to a concurrently-created, already-frozen Run.
  IF TG_OP='INSERT' THEN RETURN NEW; END IF;
  RAISE EXCEPTION 'run not found' USING ERRCODE='23503';
 END IF;
 IF TG_OP='UPDATE' AND ROW(NEW.run_id,NEW.case_id,NEW.alert_id,NEW.id,NEW.tenant_id)
   IS DISTINCT FROM ROW(OLD.run_id,OLD.case_id,OLD.alert_id,OLD.id,OLD.tenant_id) THEN
  RAISE EXCEPTION 'member identity cannot be reassigned' USING ERRCODE='23514';
 END IF;
 IF parent_state<>'pending_update' THEN
  IF TG_OP<>'UPDATE' THEN RAISE EXCEPTION 'claimed member set is frozen' USING ERRCODE='23514'; END IF;
  IF parent_state NOT IN ('running','unknown') OR
    (to_jsonb(NEW)-ARRAY['read_state','analysis_state','omission_reason'])
     IS DISTINCT FROM
    (to_jsonb(OLD)-ARRAY['read_state','analysis_state','omission_reason']) THEN
   RAISE EXCEPTION 'claimed member source is frozen' USING ERRCODE='23514';
  END IF;
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $fn$;

CREATE OR REPLACE FUNCTION socai2.check_new_member_transaction() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE st text; parent_xid text; member_xid text;
BEGIN
 SELECT state,xmin::text INTO st,parent_xid FROM socai2.runs WHERE tenant_id=NEW.tenant_id AND id=NEW.run_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'member Run missing at commit' USING ERRCODE='23503'; END IF;
 SELECT xmin::text INTO member_xid FROM socai2.run_members WHERE tenant_id=NEW.tenant_id AND id=NEW.id;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF st<>'pending_update' AND parent_xid IS DISTINCT FROM member_xid THEN
  RAISE EXCEPTION 'new members of a frozen Run must publish with its creation/claim transaction' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $fn$;

-- Cross-parent equality and result kind cannot be expressed by a nullable FK alone.
-- Deferral permits the artifact / Run / message insert order inside one publication transaction.
CREATE OR REPLACE FUNCTION socai2.check_publication_scope() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE r socai2.runs%ROWTYPE; a socai2.artifacts%ROWTYPE; m socai2.messages%ROWTYPE;
BEGIN
 IF TG_TABLE_NAME='artifacts' THEN
  IF NEW.run_id IS NOT NULL THEN
  SELECT * INTO r FROM socai2.runs WHERE tenant_id=NEW.tenant_id AND id=NEW.run_id;
  IF NOT FOUND OR ROW(NEW.alert_id,NEW.incident_id,NEW.case_id)
       IS DISTINCT FROM ROW(r.alert_id,r.incident_id,r.case_id) THEN
   RAISE EXCEPTION 'artifact parent differs from Run' USING ERRCODE='23514';
  END IF;
  END IF;
 ELSIF TG_TABLE_NAME='results' THEN
  SELECT * INTO r FROM socai2.runs WHERE tenant_id=NEW.tenant_id AND id=NEW.source_run_id;
  IF NOT FOUND OR r.case_id IS DISTINCT FROM NEW.case_id OR r.state NOT IN ('completed','failed','cancelled') OR
     (NEW.kind='baseline' AND r.kind<>'baseline') OR (NEW.kind='ai_saved' AND r.kind<>'ai_question') THEN
   RAISE EXCEPTION 'result has invalid source Run' USING ERRCODE='23514';
  END IF;
  IF NEW.input_artifact_id IS DISTINCT FROM r.input_artifact_id THEN
   RAISE EXCEPTION 'result must preserve actual Run input' USING ERRCODE='23514';
  END IF;
  IF NEW.kind='ai_saved' THEN
   SELECT * INTO m FROM socai2.messages WHERE tenant_id=NEW.tenant_id AND id=NEW.source_answer_id;
   IF NOT FOUND OR m.role<>'assistant' OR m.state<>'completed' OR m.source_run_id IS DISTINCT FROM NEW.source_run_id
      OR m.input_artifact_id IS DISTINCT FROM NEW.input_artifact_id THEN
    RAISE EXCEPTION 'saved answer must reference its actual completed message' USING ERRCODE='23514';
   END IF;
  END IF;
  FOR a IN SELECT * FROM socai2.artifacts WHERE tenant_id=NEW.tenant_id AND id IN (NEW.graph_artifact_id,NEW.report_artifact_id) LOOP
   IF a.run_id IS DISTINCT FROM NEW.source_run_id THEN
    RAISE EXCEPTION 'result graph/report must belong to source Run' USING ERRCODE='23514';
   END IF;
  END LOOP;
 ELSIF TG_TABLE_NAME='messages' THEN
  IF NEW.source_run_id IS NOT NULL THEN
  SELECT * INTO r FROM socai2.runs WHERE tenant_id=NEW.tenant_id AND id=NEW.source_run_id;
  IF NOT FOUND OR r.kind<>'ai_question' OR r.case_id IS DISTINCT FROM NEW.case_id THEN
   RAISE EXCEPTION 'message must reference a same-Case AI Run' USING ERRCODE='23514';
  END IF;
  END IF;
 END IF;
 RETURN NULL;
END $fn$;

-- Optional explicit publication step for the new backend; no old writer calls this automatically.
-- AI results are deliberately ineligible. Manual AI adoption remains a separate authorized action.
CREATE OR REPLACE FUNCTION socai2.auto_adopt_baseline_result(p_tenant uuid,p_result uuid)
RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE res socai2.results%ROWTYPE; run socai2.runs%ROWTYPE; cas socai2.cases%ROWTYPE;
 cur socai2.case_assessments%ROWTYPE; prior_id uuid; next_id uuid:=gen_random_uuid();
 act_id uuid:=gen_random_uuid(); op_id uuid:=gen_random_uuid(); ts timestamptz:=clock_timestamp();
 next_revision bigint; svc jsonb;
BEGIN
 IF p_tenant IS DISTINCT FROM public.current_tenant_id() OR p_tenant IS NULL THEN
  RAISE EXCEPTION 'explicit tenant context required' USING ERRCODE='42501';
 END IF;
 SELECT * INTO res FROM socai2.results WHERE tenant_id=p_tenant AND id=p_result;
 IF NOT FOUND THEN RAISE EXCEPTION 'result not found' USING ERRCODE='23503'; END IF;
 SELECT * INTO cas FROM socai2.cases WHERE tenant_id=p_tenant AND id=res.case_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'case not found' USING ERRCODE='23503'; END IF;
 SELECT a.id INTO prior_id FROM socai2.case_assessments a
  JOIN socai2.case_assessment_sources s ON s.tenant_id=a.tenant_id AND s.assessment_id=a.id
  WHERE a.tenant_id=p_tenant AND a.case_id=cas.id AND s.result_id=res.id
    AND a.operation_key='baseline-auto:'||res.id::text LIMIT 1;
 IF FOUND THEN RETURN jsonb_build_object('state','already_adopted','assessment_id',prior_id); END IF;
 SELECT * INTO run FROM socai2.runs WHERE tenant_id=p_tenant AND id=res.source_run_id;
 IF NOT FOUND OR res.kind<>'baseline' OR run.kind<>'baseline' OR run.state<>'completed'
    OR res.validation_state<>'accepted' OR res.conclusion_origin<>'model'
    OR res.conclusion_state='unavailable' OR nullif(btrim(res.conclusion),'') IS NULL THEN
  RETURN jsonb_build_object('state','not_eligible');
 END IF;
 IF run.case_id IS DISTINCT FROM cas.id OR run.scope_revision IS DISTINCT FROM cas.scope_revision THEN
  RETURN jsonb_build_object('state','stale_scope');
 END IF;
 IF EXISTS(
  (SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=p_tenant AND case_id=cas.id
   EXCEPT SELECT alert_id FROM socai2.run_members WHERE tenant_id=p_tenant AND run_id=run.id)
  UNION ALL
  (SELECT alert_id FROM socai2.run_members WHERE tenant_id=p_tenant AND run_id=run.id
   EXCEPT SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=p_tenant AND case_id=cas.id)
 ) THEN RETURN jsonb_build_object('state','stale_scope'); END IF;
 SELECT * INTO cur FROM socai2.case_assessments WHERE tenant_id=p_tenant AND id=cas.current_assessment_id;
 IF FOUND AND cur.adopted_at>=run.started_at THEN RETURN jsonb_build_object('state','newer_assessment'); END IF;
 IF NOT EXISTS(SELECT 1 FROM socai2.result_members WHERE tenant_id=p_tenant AND result_id=res.id
   AND conclusion_covered AND assessment_state IN ('analyzed','unresolved')) THEN
  RETURN jsonb_build_object('state','no_conclusion_coverage');
 END IF;
 -- Every promised member must have a delivery record, including explicit unresolved limitations.
 IF EXISTS(SELECT alert_id FROM socai2.run_members WHERE tenant_id=p_tenant AND run_id=run.id
  EXCEPT SELECT alert_id FROM socai2.result_members WHERE tenant_id=p_tenant AND result_id=res.id) THEN
  RETURN jsonb_build_object('state','missing_member_delivery');
 END IF;
 SELECT coalesce(max(revision),0)+1 INTO next_revision FROM socai2.case_assessments WHERE tenant_id=p_tenant AND case_id=cas.id;
 svc:=jsonb_build_object('type','service','user_id',NULL,'name_snapshot','基础调查结果自动采用',
  'service_name','socai2.baseline-publication','service_version','v1');
 INSERT INTO socai2.case_assessments(id,tenant_id,case_id,revision,conclusion,origin,validity,scope_revision,formed_at,adopted_at,actor,operation_key)
 VALUES(next_id,p_tenant,cas.id,next_revision,res.conclusion,'model','accepted',run.scope_revision,res.created_at,ts,svc,'baseline-auto:'||res.id::text);
 INSERT INTO socai2.case_assessment_sources(id,tenant_id,case_id,assessment_id,result_id)
 VALUES(gen_random_uuid(),p_tenant,cas.id,next_id,res.id);
 INSERT INTO socai2.case_assessment_members(id,tenant_id,case_id,assessment_id,alert_id,coverage_note)
 SELECT gen_random_uuid(),p_tenant,cas.id,next_id,alert_id,limitations FROM socai2.result_members
 WHERE tenant_id=p_tenant AND result_id=res.id AND conclusion_covered;
 UPDATE socai2.cases SET current_assessment_id=next_id,row_version=row_version+1,business_updated_at=ts
 WHERE tenant_id=p_tenant AND id=cas.id;
 INSERT INTO socai2.activities(id,tenant_id,operation_id,actor,action,subject_case_id,occurred_at,summary,detail)
 VALUES(act_id,p_tenant,op_id,svc,'case.assessment_adopted',cas.id,ts,'有效基础调查结果自动更新案件判断',
  jsonb_build_object('schema_version','activity.v1','reason',NULL,'request_key','baseline-auto:'||res.id::text,
   'source','baseline_publication','expected_version',cas.row_version,'actual_version',cas.row_version+1,'notes',jsonb_build_array()));
 INSERT INTO socai2.activity_targets(id,tenant_id,activity_id,case_id,before_value,after_value,result_state)
 VALUES(gen_random_uuid(),p_tenant,act_id,cas.id,jsonb_build_object('current_assessment_id',cas.current_assessment_id),
  jsonb_build_object('current_assessment_id',next_id),'succeeded');
 INSERT INTO socai2.activity_targets(id,tenant_id,activity_id,result_id,before_value,after_value,result_state)
 VALUES(gen_random_uuid(),p_tenant,act_id,res.id,NULL,jsonb_build_object('adopted_assessment_id',next_id),'succeeded');
 RETURN jsonb_build_object('state','adopted','assessment_id',next_id);
END $fn$;

DO $triggers$
DECLARE n text;
BEGIN
 FOR n IN SELECT tablename FROM pg_tables WHERE schemaname='socai2' LOOP
  EXECUTE format('DROP TRIGGER IF EXISTS identity_immutable ON socai2.%I',n);
  EXECUTE format('CREATE TRIGGER identity_immutable BEFORE UPDATE ON socai2.%I FOR EACH ROW EXECUTE FUNCTION socai2.guard_identity()',n);
 END LOOP;
 FOREACH n IN ARRAY ARRAY['alert_materials','alert_source_refs','alert_objects','alert_assessments',
  'case_assessments','case_assessment_sources','case_assessment_members','artifacts','results','result_members',
  'task_revisions','activities','activity_targets','response_links'] LOOP
  EXECUTE format('DROP TRIGGER IF EXISTS history_immutable ON socai2.%I',n);
  EXECUTE format('CREATE TRIGGER history_immutable BEFORE UPDATE OR DELETE ON socai2.%I FOR EACH ROW EXECUTE FUNCTION socai2.reject_history_mutation()',n);
 END LOOP;
 FOREACH n IN ARRAY ARRAY['run_steps','incident_diagnoses','messages'] LOOP
  EXECUTE format('DROP TRIGGER IF EXISTS terminal_immutable ON socai2.%I',n);
  EXECUTE format('CREATE TRIGGER terminal_immutable BEFORE UPDATE OR DELETE ON socai2.%I FOR EACH ROW EXECUTE FUNCTION socai2.guard_terminal_record()',n);
 END LOOP;
END $triggers$;
DROP TRIGGER IF EXISTS run_guard ON socai2.runs;
CREATE TRIGGER run_guard BEFORE INSERT OR UPDATE OR DELETE ON socai2.runs FOR EACH ROW EXECUTE FUNCTION socai2.guard_run();
DROP TRIGGER IF EXISTS member_guard ON socai2.run_members;
CREATE TRIGGER member_guard BEFORE INSERT OR UPDATE OR DELETE ON socai2.run_members FOR EACH ROW EXECUTE FUNCTION socai2.guard_run_member();
DROP TRIGGER IF EXISTS member_creation_scope ON socai2.run_members;
CREATE CONSTRAINT TRIGGER member_creation_scope AFTER INSERT ON socai2.run_members DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION socai2.check_new_member_transaction();
DROP TRIGGER IF EXISTS case_membership_lock ON socai2.case_alerts;
CREATE TRIGGER case_membership_lock BEFORE INSERT OR UPDATE OR DELETE ON socai2.case_alerts FOR EACH ROW EXECUTE FUNCTION socai2.lock_case_membership();
DO $publication$
DECLARE n text;
BEGIN
 FOREACH n IN ARRAY ARRAY['artifacts','results','messages'] LOOP
  EXECUTE format('DROP TRIGGER IF EXISTS publication_scope ON socai2.%I',n);
  EXECUTE format('CREATE CONSTRAINT TRIGGER publication_scope AFTER INSERT OR UPDATE ON socai2.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION socai2.check_publication_scope()',n);
 END LOOP;
END $publication$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA socai2 FROM PUBLIC;
DO $functions$
BEGIN
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN
  GRANT EXECUTE ON FUNCTION socai2.auto_adopt_baseline_result(uuid,uuid) TO aisoc_app;
 END IF;
END $functions$;
