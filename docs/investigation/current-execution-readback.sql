-- PostgreSQL / psql. Read-only inspection of one current investigation.
-- Set these to explicit IDs before execution; never supply secrets here.
-- \set tenant_id '...UUID...'
-- \set case_id '...UUID...'
-- \set run_id '...UUID...'
\connect socai2_next_20261104
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT set_config('app.current_tenant_id', :'tenant_id', true);

-- 1. Every Run under this Case; A/I use alert_id / incident_id instead.
SELECT id, kind, case_id, alert_id, incident_id, title, purpose, trigger,
       state, scope_revision, window_start, window_end, input_artifact_id,
       comparison_result_id, requested_at, started_at, ended_at,
       stop_reason, stop_detail, delivery_state, limits
FROM socai2.runs WHERE tenant_id=:'tenant_id'::uuid AND case_id=:'case_id'::uuid
ORDER BY requested_at,id;

-- 1b. A/I Runs for current Case members and linked/member incidents.
-- This is a navigation list. C1 artifacts, not this current relation, prove what a frozen Run used.
WITH member_alerts AS (
  SELECT alert_id FROM socai2.case_alerts
  WHERE tenant_id=:'tenant_id'::uuid AND case_id=:'case_id'::uuid
), linked_incidents AS (
  SELECT incident_id FROM socai2.case_incidents
  WHERE tenant_id=:'tenant_id'::uuid AND case_id=:'case_id'::uuid
  UNION
  SELECT ia.incident_id FROM socai2.incident_alerts ia
  JOIN member_alerts ma ON ma.alert_id=ia.alert_id
  WHERE ia.tenant_id=:'tenant_id'::uuid
)
SELECT r.* FROM socai2.runs r
WHERE r.tenant_id=:'tenant_id'::uuid
  AND (r.alert_id IN (SELECT alert_id FROM member_alerts)
    OR r.incident_id IN (SELECT incident_id FROM linked_incidents))
ORDER BY r.requested_at,r.id;

-- 2. The selected Run, usable for baseline, A or I.
SELECT * FROM socai2.runs
WHERE tenant_id=:'tenant_id'::uuid AND id=:'run_id'::uuid;

-- 3. Every executed or skipped step, with exact request and response content.
SELECT s.id,s.seq,s.kind,s.stage_code,s.name,s.question_id,s.parent_step_id,
       s.state,s.started_at,s.ended_at,s.actual_args,s.returned_rows,s.usage,s.error,
       s.input_artifact_id,s.output_artifact_id,
       req.kind AS input_kind,req.content_json AS input_json,req.content_text AS input_text,
       res.kind AS output_kind,res.content_json AS output_json,res.content_text AS output_text
FROM socai2.run_steps s
LEFT JOIN socai2.artifacts req ON req.tenant_id=s.tenant_id AND req.run_id=s.run_id AND req.id=s.input_artifact_id
LEFT JOIN socai2.artifacts res ON res.tenant_id=s.tenant_id AND res.run_id=s.run_id AND res.id=s.output_artifact_id
WHERE s.tenant_id=:'tenant_id'::uuid AND s.run_id=:'run_id'::uuid
ORDER BY s.seq;

-- 4. All artifacts, including snapshots/domain/graph/report not in a primary step pointer.
SELECT id,step_id,kind,schema_version,captured_at,material_state,sha256,size_bytes,
       content_json,content_text,source_refs,retention
FROM socai2.artifacts WHERE tenant_id=:'tenant_id'::uuid AND run_id=:'run_id'::uuid
ORDER BY captured_at,id;

-- 5. Exact frozen member versions; current pointers do not replace them.
SELECT rm.*,mat.revision AS material_revision,mat.raw_text,mat.raw_json,mat.ocsf_json,
       mat.detection,mat.enrichment,mat.source_scope,
       to_jsonb(triage) AS frozen_triage,to_jsonb(feedback) AS frozen_feedback
FROM socai2.run_members rm
LEFT JOIN socai2.alert_materials mat ON mat.tenant_id=rm.tenant_id AND mat.alert_id=rm.alert_id AND mat.id=rm.material_id
LEFT JOIN socai2.alert_assessments triage ON triage.tenant_id=rm.tenant_id AND triage.alert_id=rm.alert_id AND triage.id=rm.triage_id
LEFT JOIN socai2.alert_assessments feedback ON feedback.tenant_id=rm.tenant_id AND feedback.alert_id=rm.alert_id AND feedback.id=rm.feedback_id
WHERE rm.tenant_id=:'tenant_id'::uuid AND rm.run_id=:'run_id'::uuid ORDER BY rm.alert_id;

-- 6. A and I publications belonging to this Run.
SELECT * FROM socai2.alert_assessments WHERE tenant_id=:'tenant_id'::uuid AND source_run_id=:'run_id'::uuid;
SELECT * FROM socai2.incident_diagnoses WHERE tenant_id=:'tenant_id'::uuid AND source_run_id=:'run_id'::uuid;

-- 7. Case result, every member delivery, and whether it became a current judgment.
SELECT * FROM socai2.results WHERE tenant_id=:'tenant_id'::uuid AND source_run_id=:'run_id'::uuid;
SELECT * FROM socai2.result_members WHERE tenant_id=:'tenant_id'::uuid AND run_id=:'run_id'::uuid;
SELECT a.*,s.result_id,(c.current_assessment_id=a.id) AS is_current
FROM socai2.case_assessments a
JOIN socai2.case_assessment_sources s ON s.tenant_id=a.tenant_id AND s.assessment_id=a.id
JOIN socai2.results r ON r.tenant_id=s.tenant_id AND r.id=s.result_id
JOIN socai2.cases c ON c.tenant_id=a.tenant_id AND c.id=a.case_id
WHERE r.tenant_id=:'tenant_id'::uuid AND r.source_run_id=:'run_id'::uuid;

-- 7b. Every stored source and covered member of the judgment adopted from this result.
WITH adopted AS (
  SELECT s.assessment_id FROM socai2.case_assessment_sources s
  JOIN socai2.results r ON r.tenant_id=s.tenant_id AND r.id=s.result_id
  WHERE r.tenant_id=:'tenant_id'::uuid AND r.source_run_id=:'run_id'::uuid
)
SELECT a.id AS assessment_id,to_jsonb(s) AS source,to_jsonb(m) AS member
FROM socai2.case_assessments a
LEFT JOIN socai2.case_assessment_sources s ON s.tenant_id=a.tenant_id AND s.assessment_id=a.id
LEFT JOIN socai2.case_assessment_members m ON m.tenant_id=a.tenant_id AND m.assessment_id=a.id
WHERE a.tenant_id=:'tenant_id'::uuid AND a.id IN (SELECT assessment_id FROM adopted)
ORDER BY a.id,m.alert_id;

-- 8. Case activities with actual before/after targets (not a universal row audit log).
SELECT a.id,a.action,a.actor,a.occurred_at,a.summary,a.detail,
       t.run_id,t.result_id,t.alert_id,t.incident_id,t.case_id,t.task_id,t.before_value,t.after_value,t.result_state
FROM socai2.activities a
LEFT JOIN socai2.activity_targets t ON t.tenant_id=a.tenant_id AND t.activity_id=a.id
WHERE a.tenant_id=:'tenant_id'::uuid AND a.subject_case_id=:'case_id'::uuid
ORDER BY a.occurred_at,a.id,t.id;

-- 9. Current human task plus every saved revision; C1 input artifact identifies its cited version.
SELECT t.id AS task_id,t.current_revision_id,v.*
FROM socai2.tasks t JOIN socai2.task_revisions v
  ON v.tenant_id=t.tenant_id AND v.task_id=t.id AND v.case_id=t.case_id
WHERE t.tenant_id=:'tenant_id'::uuid AND t.case_id=:'case_id'::uuid
ORDER BY t.id,v.revision;
-- 10. Current committed-input freshness of this frozen baseline (migration 125).
SELECT socai2.baseline_input_freshness(:'tenant_id'::uuid,:'run_id'::uuid) AS input_freshness;
ROLLBACK;
