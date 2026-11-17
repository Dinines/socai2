-- Additive task/attempt lifecycle. Caller supplies target, transaction and timeouts.
-- No historical Run is rewritten or assigned a fabricated attempt.
DO $preflight$
BEGIN
  IF current_database() IS DISTINCT FROM current_setting('socai2.migration.expected_database', true)
     OR to_regclass('public.aisoc_schema_migrations') IS NULL THEN
    RAISE EXCEPTION 'analysis_migration_target_mismatch';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext('socai2'), hashtext('schema-initialization'));
  IF NOT EXISTS (SELECT FROM public.aisoc_schema_migrations WHERE name='126_socai2_case_page_data.sql') THEN
    RAISE EXCEPTION 'analysis_migration_baseline_missing';
  END IF;
END $preflight$;

CREATE TABLE IF NOT EXISTS socai2.analysis_tasks (
  tenant_id uuid NOT NULL REFERENCES public.tenants(id), id uuid NOT NULL,
  kind text NOT NULL, subject_type text NOT NULL, subject_id uuid NOT NULL,
  intent text NOT NULL, source text NOT NULL, operation_key uuid NOT NULL,
  request_hash text NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
  request_payload jsonb NOT NULL CHECK (jsonb_typeof(request_payload)='object'),
  submitted_at timestamptz NOT NULL, submitted_by uuid REFERENCES public.users(id),
  state text NOT NULL DEFAULT 'accepted', reason_code text, error_detail jsonb,
  merged_into_task_id uuid, retry_count integer NOT NULL DEFAULT 0,
  retry_limit integer NOT NULL, retry_delay_seconds integer NOT NULL,
  next_retry_at timestamptz, started_at timestamptz, ended_at timestamptz,
  observed_input_digest text, source_run_id uuid, source_result_id uuid,
  last_enqueued_at timestamptz,
  PRIMARY KEY (tenant_id,id),
  CONSTRAINT analysis_tasks_operation_once UNIQUE (tenant_id,kind,operation_key),
  UNIQUE (tenant_id,id,subject_type,subject_id,kind),
  CHECK ((kind IN ('alert_triage','knowledge_sync') AND subject_type='alert') OR
         (kind='incident_diagnosis' AND subject_type='incident') OR
         (kind='case_investigation' AND subject_type='case')),
  CHECK (intent IN ('initial','check','rerun','targeted','synthesis')),
  CHECK (source IN ('ingress','case_create','periodic','user','knowledge')),
  CHECK (intent NOT IN ('targeted','synthesis') OR (kind='case_investigation' AND source='user')),
  CHECK (state IN ('accepted','waiting','running','completed','failed','skipped','merged')),
  CHECK (retry_count>=0 AND retry_limit>=0 AND retry_count<=retry_limit AND retry_delay_seconds>=0),
  CHECK ((state IN ('completed','failed','skipped','merged'))=(ended_at IS NOT NULL)),
  CHECK (state NOT IN ('running','completed') OR started_at IS NOT NULL),
  CHECK (ended_at IS NULL OR started_at IS NULL OR ended_at>=started_at),
  CHECK (next_retry_at IS NULL OR state='waiting'),
  CHECK ((state='merged')=(merged_into_task_id IS NOT NULL)),
  CHECK (merged_into_task_id IS DISTINCT FROM id),
  CHECK (error_detail IS NULL OR jsonb_typeof(error_detail)='object'),
  CHECK ((kind='knowledge_sync')=(source_run_id IS NOT NULL AND source_result_id IS NOT NULL)),
  CHECK (kind='knowledge_sync' OR (source_run_id IS NULL AND source_result_id IS NULL)),
  FOREIGN KEY (tenant_id,merged_into_task_id) REFERENCES socai2.analysis_tasks(tenant_id,id),
  FOREIGN KEY (tenant_id,source_run_id) REFERENCES socai2.runs(tenant_id,id),
  FOREIGN KEY (tenant_id,source_result_id) REFERENCES socai2.alert_assessments(tenant_id,id)
);
CREATE INDEX IF NOT EXISTS analysis_tasks_subject ON socai2.analysis_tasks
  (tenant_id,subject_type,subject_id,submitted_at DESC,id DESC);
CREATE INDEX IF NOT EXISTS analysis_tasks_state ON socai2.analysis_tasks(tenant_id,state,submitted_at,id);

CREATE TABLE IF NOT EXISTS socai2.analysis_attempts (
  tenant_id uuid NOT NULL, id uuid NOT NULL, task_id uuid NOT NULL,
  attempt_no integer NOT NULL CHECK (attempt_no>0),
  subject_type text NOT NULL, subject_id uuid NOT NULL, kind text NOT NULL,
  run_id uuid, source_run_id uuid,
  local_state text NOT NULL DEFAULT 'running', started_at timestamptz NOT NULL,
  local_ended_at timestamptz, interruption_observed_at timestamptz,
  outcome text, failed_at timestamptz, error_code text, error_stage text,
  error_detail jsonb, retryable boolean NOT NULL DEFAULT false,
  input_artifact_id uuid, input_digest text, previous_run_id uuid,
  comparison_result_id uuid, policy_artifact_id uuid,
  PRIMARY KEY (tenant_id,id),
  UNIQUE (tenant_id,task_id,attempt_no),
  FOREIGN KEY (tenant_id,task_id,subject_type,subject_id,kind)
    REFERENCES socai2.analysis_tasks(tenant_id,id,subject_type,subject_id,kind),
  FOREIGN KEY (tenant_id,run_id) REFERENCES socai2.runs(tenant_id,id),
  FOREIGN KEY (tenant_id,source_run_id) REFERENCES socai2.runs(tenant_id,id),
  FOREIGN KEY (tenant_id,input_artifact_id) REFERENCES socai2.artifacts(tenant_id,id),
  FOREIGN KEY (tenant_id,policy_artifact_id) REFERENCES socai2.artifacts(tenant_id,id),
  FOREIGN KEY (tenant_id,previous_run_id) REFERENCES socai2.runs(tenant_id,id),
  FOREIGN KEY (tenant_id,comparison_result_id) REFERENCES socai2.results(tenant_id,id),
  CHECK (local_state IN ('running','ended','interrupted')),
  CHECK ((local_state='ended')=(local_ended_at IS NOT NULL)),
  CHECK ((local_state='interrupted')=(interruption_observed_at IS NOT NULL)),
  CHECK ((local_state='running')=(outcome IS NULL)),
  CHECK (outcome IN ('completed','failed','unknown')),
  CHECK (local_state<>'interrupted' OR outcome='unknown'),
  CHECK (local_ended_at IS NULL OR local_ended_at>=started_at),
  CHECK (interruption_observed_at IS NULL OR interruption_observed_at>=started_at),
  CHECK ((outcome IN ('failed','unknown'))=(failed_at IS NOT NULL)),
  CHECK (failed_at IS NULL OR (failed_at>=started_at AND error_code IS NOT NULL)),
  CHECK (NOT retryable OR outcome='failed'),
  CHECK ((input_artifact_id IS NULL)=(input_digest IS NULL)),
  CHECK (input_digest IS NULL OR input_digest ~ '^[0-9a-f]{64}$'),
  CHECK (error_detail IS NULL OR jsonb_typeof(error_detail)='object')
);
CREATE UNIQUE INDEX IF NOT EXISTS analysis_attempts_run_once
  ON socai2.analysis_attempts(tenant_id,run_id) WHERE run_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS analysis_attempts_one_active
  ON socai2.analysis_attempts(tenant_id,subject_type,subject_id,kind) WHERE local_state='running';

CREATE TABLE IF NOT EXISTS socai2.analysis_subject_state (
  tenant_id uuid NOT NULL REFERENCES public.tenants(id),
  subject_type text NOT NULL CHECK (subject_type IN ('alert','incident','case')), subject_id uuid NOT NULL,
  registered_at timestamptz NOT NULL, next_check_at timestamptz,
  last_normal_completed_at timestamptz, last_completed_attempt_id uuid, last_attempt_id uuid,
  stopped_input_digest text, stopped_task_id uuid, automatic_stop_reason text,
  PRIMARY KEY (tenant_id,subject_type,subject_id),
  FOREIGN KEY (tenant_id,last_completed_attempt_id) REFERENCES socai2.analysis_attempts(tenant_id,id),
  FOREIGN KEY (tenant_id,last_attempt_id) REFERENCES socai2.analysis_attempts(tenant_id,id),
  FOREIGN KEY (tenant_id,stopped_task_id) REFERENCES socai2.analysis_tasks(tenant_id,id),
  CHECK (subject_type<>'alert' OR next_check_at IS NULL),
  CHECK ((last_normal_completed_at IS NULL)=(last_completed_attempt_id IS NULL)),
  CHECK ((automatic_stop_reason IS NULL)=(stopped_task_id IS NULL)),
  CHECK (stopped_input_digest IS NULL OR stopped_task_id IS NOT NULL)
);

-- Shared polymorphic subject check; permissions remain the existing tenant RLS.
CREATE OR REPLACE FUNCTION socai2.guard_analysis_subject() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,socai2 AS $body$
DECLARE present boolean;
BEGIN
  CASE NEW.subject_type
    WHEN 'alert' THEN SELECT EXISTS(SELECT FROM socai2.alerts WHERE tenant_id=NEW.tenant_id AND id=NEW.subject_id) INTO present;
    WHEN 'incident' THEN SELECT EXISTS(SELECT FROM socai2.incidents WHERE tenant_id=NEW.tenant_id AND id=NEW.subject_id) INTO present;
    WHEN 'case' THEN SELECT EXISTS(SELECT FROM socai2.cases WHERE tenant_id=NEW.tenant_id AND id=NEW.subject_id) INTO present;
    ELSE present := false;
  END CASE;
  IF NOT present THEN RAISE EXCEPTION 'analysis_subject_not_found' USING ERRCODE='23503'; END IF;
  IF TG_OP='UPDATE' AND (NEW.tenant_id,NEW.subject_type,NEW.subject_id) IS DISTINCT FROM
                       (OLD.tenant_id,OLD.subject_type,OLD.subject_id) THEN
    RAISE EXCEPTION 'analysis_subject_immutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $body$;

CREATE OR REPLACE FUNCTION socai2.guard_analysis_task() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,socai2 AS $body$
DECLARE root socai2.analysis_tasks;
BEGIN
  IF TG_OP='UPDATE' THEN
    IF (to_jsonb(NEW)-ARRAY['state','reason_code','error_detail','merged_into_task_id','retry_count',
        'next_retry_at','started_at','ended_at','observed_input_digest','last_enqueued_at']) IS DISTINCT FROM
       (to_jsonb(OLD)-ARRAY['state','reason_code','error_detail','merged_into_task_id','retry_count',
        'next_retry_at','started_at','ended_at','observed_input_digest','last_enqueued_at'])
       OR (OLD.state IN ('completed','failed','skipped','merged') AND NEW IS DISTINCT FROM OLD)
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
DECLARE task socai2.analysis_tasks; run socai2.runs; prior socai2.runs; expected_kind text;
BEGIN
  IF TG_OP='UPDATE' AND (
      (OLD.local_state<>'running' AND NEW IS DISTINCT FROM OLD)
      OR (NEW.tenant_id,NEW.id,NEW.task_id,NEW.attempt_no,NEW.started_at,NEW.subject_type,NEW.subject_id,NEW.kind,NEW.source_run_id)
         IS DISTINCT FROM (OLD.tenant_id,OLD.id,OLD.task_id,OLD.attempt_no,OLD.started_at,OLD.subject_type,OLD.subject_id,OLD.kind,OLD.source_run_id)
      OR (OLD.run_id IS NOT NULL AND NEW.run_id IS DISTINCT FROM OLD.run_id)
      OR (OLD.input_artifact_id IS NOT NULL AND (NEW.input_artifact_id,NEW.input_digest,NEW.previous_run_id,
          NEW.comparison_result_id,NEW.policy_artifact_id) IS DISTINCT FROM (OLD.input_artifact_id,OLD.input_digest,
          OLD.previous_run_id,OLD.comparison_result_id,OLD.policy_artifact_id))) THEN
    RAISE EXCEPTION 'analysis_attempt_history_immutable' USING ERRCODE='23514';
  END IF;
  SELECT * INTO task FROM socai2.analysis_tasks WHERE tenant_id=NEW.tenant_id AND id=NEW.task_id;
  IF task.state<>'running' OR NEW.source_run_id IS DISTINCT FROM task.source_run_id THEN
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
  IF NEW.outcome='completed' AND NEW.kind<>'knowledge_sync' AND NEW.run_id IS NULL THEN
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
      AND a.local_state='ended' AND a.local_ended_at=NEW.last_normal_completed_at) THEN
    RAISE EXCEPTION 'analysis_completed_attempt_invalid' USING ERRCODE='23503';
  END IF;
  IF NEW.stopped_task_id IS NOT NULL AND NOT EXISTS (SELECT FROM socai2.analysis_tasks
    WHERE tenant_id=NEW.tenant_id AND id=NEW.stopped_task_id AND subject_type=NEW.subject_type
      AND subject_id=NEW.subject_id AND kind<>'knowledge_sync' AND intent<>'targeted' AND state='failed') THEN
    RAISE EXCEPTION 'analysis_stopped_task_invalid' USING ERRCODE='23503';
  END IF;
  RETURN NEW;
END $body$;

DROP TRIGGER IF EXISTS analysis_task_subject ON socai2.analysis_tasks;
CREATE TRIGGER analysis_task_subject BEFORE INSERT OR UPDATE ON socai2.analysis_tasks
  FOR EACH ROW EXECUTE FUNCTION socai2.guard_analysis_subject();
DROP TRIGGER IF EXISTS analysis_task_guard ON socai2.analysis_tasks;
CREATE TRIGGER analysis_task_guard BEFORE INSERT OR UPDATE ON socai2.analysis_tasks
  FOR EACH ROW EXECUTE FUNCTION socai2.guard_analysis_task();
DROP TRIGGER IF EXISTS analysis_attempt_guard ON socai2.analysis_attempts;
CREATE TRIGGER analysis_attempt_guard BEFORE INSERT OR UPDATE ON socai2.analysis_attempts
  FOR EACH ROW EXECUTE FUNCTION socai2.guard_analysis_attempt();
DROP TRIGGER IF EXISTS analysis_state_subject ON socai2.analysis_subject_state;
CREATE TRIGGER analysis_state_subject BEFORE INSERT OR UPDATE ON socai2.analysis_subject_state
  FOR EACH ROW EXECUTE FUNCTION socai2.guard_analysis_subject();
DROP TRIGGER IF EXISTS analysis_state_guard ON socai2.analysis_subject_state;
CREATE TRIGGER analysis_state_guard BEFORE INSERT OR UPDATE ON socai2.analysis_subject_state
  FOR EACH ROW EXECUTE FUNCTION socai2.guard_analysis_subject_state();

DROP INDEX IF EXISTS socai2.runs_one_active_baseline;
CREATE UNIQUE INDEX runs_one_active_baseline ON socai2.runs(tenant_id,case_id)
  WHERE kind='baseline' AND state='running';
DO $rls$
DECLARE tab text;
BEGIN
  FOREACH tab IN ARRAY ARRAY['analysis_tasks','analysis_attempts','analysis_subject_state'] LOOP
    EXECUTE format('ALTER TABLE socai2.%I ENABLE ROW LEVEL SECURITY', tab);
    EXECUTE format('ALTER TABLE socai2.%I FORCE ROW LEVEL SECURITY', tab);
    EXECUTE format('DROP POLICY IF EXISTS tenant_scope ON socai2.%I', tab);
    EXECUTE format('CREATE POLICY tenant_scope ON socai2.%I USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id())', tab);
  END LOOP;
END $rls$;
INSERT INTO public.aisoc_schema_migrations(name) VALUES ('128_socai2_analysis_lifecycle.sql') ON CONFLICT (name) DO NOTHING;
