-- Current-input checks use the existing immutable C1 snapshot. No new tables.
BEGIN;
CREATE OR REPLACE FUNCTION socai2.task_feedback_signature(v jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,socai2 AS $fn$
 SELECT CASE WHEN v->>'state'='completed' AND nullif(btrim(v->>'result_text'),'') IS NOT NULL THEN
 jsonb_build_object('result_text',v->'result_text','result_scope',v->'result_scope',
   'source_refs',v->'source_refs','completed_at',v->'completed_at','completed_by',v->'completed_by') END
$fn$;

CREATE OR REPLACE FUNCTION socai2.baseline_input_freshness(p_tenant uuid,p_run uuid)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,socai2 AS $fn$
 WITH r AS MATERIALIZED (
   SELECT * FROM socai2.runs WHERE tenant_id=p_tenant AND id=p_run AND kind='baseline'
 ), frozen AS MATERIALIZED (
   SELECT f.content_json AS body FROM socai2.artifacts f JOIN r ON r.id=f.run_id AND r.case_id=f.case_id
   WHERE f.tenant_id=p_tenant AND f.kind='source_snapshot' AND f.material_state='complete'
     AND f.schema_version='socai2.baseline-context.v1'
   ORDER BY f.captured_at,f.id LIMIT 1
 ), incident_ids AS (
   SELECT ci.incident_id FROM socai2.case_incidents ci JOIN r ON ci.case_id=r.case_id WHERE ci.tenant_id=p_tenant
   UNION SELECT ia.incident_id FROM socai2.incident_alerts ia JOIN socai2.case_alerts ca
     ON ca.tenant_id=ia.tenant_id AND ca.alert_id=ia.alert_id JOIN r ON ca.case_id=r.case_id WHERE ca.tenant_id=p_tenant
 ), live_incidents AS (
   SELECT coalesce(jsonb_object_agg(i.id::text,jsonb_build_object('diagnosis_id',i.latest_diagnosis_id,
     'member_ids',(SELECT coalesce(jsonb_agg(ia.alert_id ORDER BY ia.alert_id),'[]'::jsonb)
       FROM socai2.incident_alerts ia WHERE ia.tenant_id=p_tenant AND ia.incident_id=i.id))),'{}'::jsonb) AS value
   FROM socai2.incidents i JOIN incident_ids k ON k.incident_id=i.id WHERE i.tenant_id=p_tenant
 ), old_incidents AS (
   SELECT coalesce(jsonb_object_agg(k,jsonb_build_object('diagnosis_id',v->'incident'->'latest_diagnosis_id',
     'member_ids',v->'member_ids')),'{}'::jsonb) AS value
   FROM frozen, LATERAL jsonb_each(body->'incidents') e(k,v)
 ), live_tasks AS (
   SELECT coalesce(jsonb_object_agg(t.id::text,socai2.task_feedback_signature(to_jsonb(v)))
     FILTER(WHERE socai2.task_feedback_signature(to_jsonb(v)) IS NOT NULL),'{}'::jsonb) AS value
   FROM socai2.tasks t JOIN r ON t.case_id=r.case_id JOIN socai2.task_revisions v
     ON v.tenant_id=t.tenant_id AND v.task_id=t.id AND v.id=t.current_revision_id WHERE t.tenant_id=p_tenant
 ), old_tasks AS (
   SELECT coalesce(jsonb_object_agg(k,socai2.task_feedback_signature(v->'revision'))
     FILTER(WHERE socai2.task_feedback_signature(v->'revision') IS NOT NULL),'{}'::jsonb) AS value
   FROM frozen, LATERAL jsonb_each(body->'tasks') e(k,v)
 ), checks AS (
   SELECT array_remove(ARRAY[
     CASE WHEN NOT EXISTS(SELECT 1 FROM frozen WHERE body->>'schema_version'='socai2.baseline-context.v1')
       THEN 'frozen_context_unavailable' END,
     CASE WHEN EXISTS(SELECT 1 FROM r JOIN socai2.cases c ON c.tenant_id=r.tenant_id AND c.id=r.case_id
         WHERE r.scope_revision IS DISTINCT FROM c.scope_revision)
       OR EXISTS((SELECT ca.alert_id FROM socai2.case_alerts ca JOIN r ON r.case_id=ca.case_id WHERE ca.tenant_id=p_tenant
          EXCEPT SELECT rm.alert_id FROM socai2.run_members rm JOIN r ON r.id=rm.run_id WHERE rm.tenant_id=p_tenant)
         UNION ALL (SELECT rm.alert_id FROM socai2.run_members rm JOIN r ON r.id=rm.run_id WHERE rm.tenant_id=p_tenant
          EXCEPT SELECT ca.alert_id FROM socai2.case_alerts ca JOIN r ON r.case_id=ca.case_id WHERE ca.tenant_id=p_tenant))
       THEN 'scope_changed' END,
     CASE WHEN EXISTS(SELECT 1 FROM socai2.run_members rm JOIN r ON r.id=rm.run_id
       JOIN socai2.alerts a ON a.tenant_id=rm.tenant_id AND a.id=rm.alert_id WHERE rm.tenant_id=p_tenant
       AND (a.latest_material_id IS DISTINCT FROM rm.material_id OR a.latest_triage_id IS DISTINCT FROM rm.triage_id
         OR a.latest_feedback_id IS DISTINCT FROM rm.feedback_id)) THEN 'member_versions_changed' END,
     CASE WHEN (SELECT value FROM live_incidents) IS DISTINCT FROM (SELECT value FROM old_incidents)
       THEN 'incident_context_changed' END,
     CASE WHEN (SELECT value FROM live_tasks) IS DISTINCT FROM (SELECT value FROM old_tasks)
       THEN 'human_feedback_changed' END
   ]::text[],NULL) AS reasons
 ) SELECT jsonb_build_object('state',CASE WHEN NOT EXISTS(SELECT 1 FROM r) OR 'frozen_context_unavailable'=ANY(reasons)
       THEN 'unverified' WHEN cardinality(reasons)>0 THEN 'stale' ELSE 'current' END,
     'reasons',to_jsonb(reasons)) FROM checks
$fn$;

CREATE OR REPLACE FUNCTION socai2.auto_adopt_baseline_result(p_tenant uuid,p_result uuid)
RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE res socai2.results%ROWTYPE; run socai2.runs%ROWTYPE; cas socai2.cases%ROWTYPE;
 cur socai2.case_assessments%ROWTYPE; prior_id uuid; next_id uuid:=gen_random_uuid();
 act_id uuid:=gen_random_uuid(); op_id uuid:=gen_random_uuid(); ts timestamptz:=clock_timestamp();
 next_revision bigint; svc jsonb; freshness jsonb;
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
 freshness:=socai2.baseline_input_freshness(p_tenant,run.id);
 IF freshness->>'state'<>'current' THEN
  RETURN jsonb_build_object('state','stale_input','input_freshness',freshness);
 END IF;
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
COMMIT;
