-- S5: confirmed enqueue timestamps and visible preparation. No historical backfill.
-- Caller supplies expected database, transaction and timeouts; V1/128 stay unchanged.
DO $preflight$
BEGIN
  IF current_database() IS DISTINCT FROM current_setting('socai2.migration.expected_database', true)
     OR to_regclass('public.aisoc_schema_migrations') IS NULL THEN
    RAISE EXCEPTION 'analysis_times_migration_target_mismatch';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext('socai2'), hashtext('schema-initialization'));
  IF NOT EXISTS (SELECT FROM public.aisoc_schema_migrations WHERE name='128_socai2_analysis_lifecycle.sql') THEN
    RAISE EXCEPTION 'analysis_times_migration_baseline_missing';
  END IF;
END $preflight$;

ALTER TABLE socai2.analysis_tasks ADD COLUMN IF NOT EXISTS first_enqueued_at timestamptz;
ALTER TABLE socai2.analysis_tasks ADD COLUMN IF NOT EXISTS next_attempt_enqueued_at timestamptz;
ALTER TABLE socai2.analysis_attempts ADD COLUMN IF NOT EXISTS enqueued_at timestamptz;

CREATE OR REPLACE FUNCTION socai2.guard_analysis_task() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,socai2 AS $body$
DECLARE root socai2.analysis_tasks;
BEGIN
  IF TG_OP='UPDATE' THEN
    IF (to_jsonb(NEW)-ARRAY['state','reason_code','error_detail','merged_into_task_id','retry_count',
        'next_retry_at','started_at','ended_at','observed_input_digest','last_enqueued_at',
        'first_enqueued_at','next_attempt_enqueued_at']) IS DISTINCT FROM
       (to_jsonb(OLD)-ARRAY['state','reason_code','error_detail','merged_into_task_id','retry_count',
        'next_retry_at','started_at','ended_at','observed_input_digest','last_enqueued_at',
        'first_enqueued_at','next_attempt_enqueued_at'])
       OR (OLD.state IN ('completed','failed','skipped','merged') AND NEW IS DISTINCT FROM OLD)
       OR (OLD.first_enqueued_at IS NOT NULL AND NEW.first_enqueued_at IS DISTINCT FROM OLD.first_enqueued_at)
       OR (OLD.next_attempt_enqueued_at IS NOT NULL AND NEW.next_attempt_enqueued_at IS NOT NULL
           AND NEW.next_attempt_enqueued_at IS DISTINCT FROM OLD.next_attempt_enqueued_at)
       OR NEW.retry_count<OLD.retry_count
       OR (OLD.started_at IS NOT NULL AND NEW.started_at IS DISTINCT FROM OLD.started_at) THEN
      RAISE EXCEPTION 'analysis_task_history_immutable' USING ERRCODE='23514';
    END IF;
  END IF;
  IF NEW.submitted_by IS NOT NULL AND NOT EXISTS (SELECT FROM public.users
      WHERE id=NEW.submitted_by AND tenant_id=NEW.tenant_id) THEN
    RAISE EXCEPTION 'analysis_actor_not_in_tenant' USING ERRCODE='23503';
  END IF;
  IF NEW.kind='knowledge_sync' AND NOT EXISTS (SELECT FROM socai2.alert_assessments a
      JOIN socai2.runs r ON (r.tenant_id,r.id)=(a.tenant_id,a.source_run_id)
      WHERE a.tenant_id=NEW.tenant_id AND a.id=NEW.source_result_id AND r.id=NEW.source_run_id
      AND a.alert_id=NEW.subject_id AND r.kind='alert_basic') THEN
    RAISE EXCEPTION 'analysis_knowledge_source_invalid' USING ERRCODE='23503';
  END IF;
  IF NEW.merged_into_task_id IS NOT NULL THEN
    SELECT * INTO root FROM socai2.analysis_tasks
      WHERE tenant_id=NEW.tenant_id AND id=NEW.merged_into_task_id FOR UPDATE;
    IF root.id IS NULL OR root.merged_into_task_id IS NOT NULL OR root.state NOT IN ('accepted','waiting')
       OR (NEW.subject_type,NEW.subject_id,NEW.kind) IS DISTINCT FROM (root.subject_type,root.subject_id,root.kind)
       OR NEW.intent NOT IN ('initial','check') OR root.intent NOT IN ('initial','check')
       OR EXISTS (SELECT FROM socai2.analysis_tasks WHERE tenant_id=NEW.tenant_id AND merged_into_task_id=NEW.id) THEN
      RAISE EXCEPTION 'analysis_merge_target_invalid' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END $body$;

CREATE OR REPLACE FUNCTION socai2.guard_analysis_attempt() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,socai2 AS $body$
DECLARE task socai2.analysis_tasks; run socai2.runs; prior socai2.runs; expected_kind text; preparation_skip boolean;
BEGIN
  IF TG_OP='UPDATE' AND (
      (OLD.local_state<>'running' AND NEW IS DISTINCT FROM OLD)
      OR (NEW.tenant_id,NEW.id,NEW.task_id,NEW.attempt_no,NEW.started_at,NEW.enqueued_at,NEW.subject_type,NEW.subject_id,NEW.kind,NEW.source_run_id)
         IS DISTINCT FROM (OLD.tenant_id,OLD.id,OLD.task_id,OLD.attempt_no,OLD.started_at,OLD.enqueued_at,OLD.subject_type,OLD.subject_id,OLD.kind,OLD.source_run_id)
      OR (OLD.run_id IS NOT NULL AND NEW.run_id IS DISTINCT FROM OLD.run_id)
      OR (OLD.input_artifact_id IS NOT NULL AND (NEW.input_artifact_id,NEW.input_digest,NEW.previous_run_id,
          NEW.comparison_result_id,NEW.policy_artifact_id) IS DISTINCT FROM (OLD.input_artifact_id,OLD.input_digest,
          OLD.previous_run_id,OLD.comparison_result_id,OLD.policy_artifact_id))) THEN
    RAISE EXCEPTION 'analysis_attempt_history_immutable' USING ERRCODE='23514';
  END IF;
  SELECT * INTO task FROM socai2.analysis_tasks WHERE tenant_id=NEW.tenant_id AND id=NEW.task_id;
  -- Only a finished preparation check can be completed without an analysis Run.
  -- It cannot enter the normal-completion pointer or refresh the auto window.
  preparation_skip := task.state='skipped' AND task.intent IN ('initial','check')
      AND task.reason_code IN ('no_changes','automatic_attempts_stopped')
      AND NEW.run_id IS NULL AND NEW.input_artifact_id IS NULL AND NEW.input_digest IS NULL
      AND NEW.previous_run_id IS NULL AND NEW.comparison_result_id IS NULL AND NEW.policy_artifact_id IS NULL
      AND NEW.local_state='ended' AND NEW.outcome='completed' AND NEW.local_ended_at=task.ended_at
      AND NEW.failed_at IS NULL AND NEW.error_code IS NULL AND NEW.error_stage IS NULL
      AND NEW.error_detail IS NULL AND NOT NEW.retryable;
  IF (task.state<>'running' AND NOT COALESCE(preparation_skip,false))
     OR NEW.source_run_id IS DISTINCT FROM task.source_run_id THEN
    RAISE EXCEPTION 'analysis_attempt_task_not_running' USING ERRCODE='23514';
  END IF;
  IF NEW.run_id IS NOT NULL THEN
    SELECT * INTO run FROM socai2.runs WHERE tenant_id=NEW.tenant_id AND id=NEW.run_id;
    expected_kind := CASE NEW.kind WHEN 'alert_triage' THEN 'alert_basic'
        WHEN 'incident_diagnosis' THEN 'incident_diagnosis'
        WHEN 'case_investigation' THEN CASE WHEN task.intent='targeted' THEN 'targeted' ELSE 'baseline' END END;
    IF run.id IS NULL OR COALESCE(run.alert_id,run.incident_id,run.case_id)<>NEW.subject_id
       OR run.kind IS DISTINCT FROM expected_kind
       OR run.started_at IS NULL OR run.started_at<NEW.started_at
       OR NEW.input_artifact_id IS DISTINCT FROM run.input_artifact_id
       OR NEW.comparison_result_id IS DISTINCT FROM run.comparison_result_id
       OR (NEW.outcome='completed' AND run.state<>'completed')
       OR (NEW.local_state<>'running' AND run.state IN ('running','pending_update')) THEN
      RAISE EXCEPTION 'analysis_attempt_run_invalid' USING ERRCODE='23514';
    END IF;
  END IF;
  IF NEW.outcome='completed' AND NEW.kind<>'knowledge_sync' AND NEW.run_id IS NULL
     AND NOT COALESCE(preparation_skip,false) THEN
    RAISE EXCEPTION 'analysis_completed_run_missing' USING ERRCODE='23514';
  END IF;
  IF NEW.input_artifact_id IS NOT NULL AND NOT EXISTS (SELECT FROM socai2.artifacts
      WHERE tenant_id=NEW.tenant_id AND id=NEW.input_artifact_id
        AND COALESCE(alert_id,incident_id,case_id)=NEW.subject_id) THEN
    RAISE EXCEPTION 'analysis_input_scope_invalid' USING ERRCODE='23503';
  END IF;
  IF NEW.policy_artifact_id IS NOT NULL AND NOT EXISTS (SELECT FROM socai2.artifacts
      WHERE tenant_id=NEW.tenant_id AND id=NEW.policy_artifact_id
      AND COALESCE(alert_id,incident_id,case_id)=NEW.subject_id) THEN
    RAISE EXCEPTION 'analysis_policy_scope_invalid' USING ERRCODE='23503';
  END IF;
  IF NEW.previous_run_id IS NOT NULL THEN
    SELECT * INTO prior FROM socai2.runs WHERE tenant_id=NEW.tenant_id AND id=NEW.previous_run_id;
    IF NEW.subject_type<>'case' OR prior.case_id IS DISTINCT FROM NEW.subject_id OR prior.kind<>'baseline'
       OR prior.id=NEW.run_id OR prior.state IN ('running','pending_update') THEN
      RAISE EXCEPTION 'analysis_previous_run_invalid' USING ERRCODE='23514';
    END IF;
  END IF;
  IF NEW.comparison_result_id IS NOT NULL AND (NEW.previous_run_id IS NULL OR NOT EXISTS
      (SELECT FROM socai2.results WHERE tenant_id=NEW.tenant_id AND id=NEW.comparison_result_id
       AND case_id=NEW.subject_id AND source_run_id=NEW.previous_run_id)) THEN
    RAISE EXCEPTION 'analysis_comparison_invalid' USING ERRCODE='23503';
  END IF;
  RETURN NEW;
END $body$;

CREATE OR REPLACE FUNCTION socai2.guard_analysis_subject_state() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,socai2 AS $body$
BEGIN
  IF NEW.last_attempt_id IS NOT NULL AND NOT EXISTS (SELECT FROM socai2.analysis_attempts
    WHERE tenant_id=NEW.tenant_id AND id=NEW.last_attempt_id AND subject_type=NEW.subject_type
      AND subject_id=NEW.subject_id AND kind<>'knowledge_sync') THEN
    RAISE EXCEPTION 'analysis_last_attempt_invalid' USING ERRCODE='23503';
  END IF;
  IF NEW.last_completed_attempt_id IS NOT NULL AND NOT EXISTS (SELECT FROM socai2.analysis_attempts a
    JOIN socai2.analysis_tasks t ON (t.tenant_id,t.id)=(a.tenant_id,a.task_id)
    WHERE a.tenant_id=NEW.tenant_id AND a.id=NEW.last_completed_attempt_id
      AND a.subject_type=NEW.subject_type AND a.subject_id=NEW.subject_id
      AND a.kind<>'knowledge_sync' AND t.intent<>'targeted' AND a.outcome='completed'
      AND a.run_id IS NOT NULL AND a.local_state='ended' AND a.local_ended_at=NEW.last_normal_completed_at) THEN
    RAISE EXCEPTION 'analysis_completed_attempt_invalid' USING ERRCODE='23503';
  END IF;
  IF NEW.stopped_task_id IS NOT NULL AND NOT EXISTS (SELECT FROM socai2.analysis_tasks
    WHERE tenant_id=NEW.tenant_id AND id=NEW.stopped_task_id AND subject_type=NEW.subject_type
      AND subject_id=NEW.subject_id AND kind<>'knowledge_sync' AND intent<>'targeted' AND state='failed') THEN
    RAISE EXCEPTION 'analysis_stopped_task_invalid' USING ERRCODE='23503';
  END IF;
  RETURN NEW;
END $body$;

INSERT INTO public.aisoc_schema_migrations(name) VALUES ('133_socai2_analysis_task_times.sql') ON CONFLICT (name) DO NOTHING;
