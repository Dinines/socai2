WITH seeds AS (
 SELECT * FROM jsonb_to_recordset(CAST(:seeds AS jsonb)) AS s(
   id uuid, alert_id uuid, object_type text, namespace text,
   match_value text, algorithm text, event_time timestamptz)
), current_objects AS (
 SELECT o.*, a.event_time,
   CASE WHEN o.object_type='hash' THEN lower(o.normalized_value) ELSE o.normalized_value END AS match_value,
   CASE WHEN o.object_type='hash' THEN upper(replace(replace(o.attributes->>'algorithm','-',''),'_','')) END AS algorithm
 FROM socai2.alert_objects o
 JOIN socai2.alerts a ON a.tenant_id=o.tenant_id AND a.id=o.alert_id AND a.latest_material_id=o.material_id
 WHERE o.tenant_id=:tenant AND a.source_namespace=:source
   AND a.event_time >= :time_from AND a.event_time < :time_to
   AND NOT a.id=ANY(CAST(:seed_alert_ids AS uuid[]))
), pairs AS (
 SELECT o.alert_id, o.id AS candidate_object_id, s.id AS seed_object_id,
   s.namespace, s.object_type, s.match_value, s.algorithm,
   abs(extract(epoch FROM (o.event_time-s.event_time)))::double precision AS delta
 FROM current_objects o JOIN seeds s ON o.namespace=s.namespace AND o.object_type=s.object_type
   AND o.match_value=s.match_value AND o.algorithm IS NOT DISTINCT FROM s.algorithm
), candidates AS (
 SELECT alert_id, count(DISTINCT (namespace,object_type,match_value,algorithm))::int AS shared,
   min(delta) AS delta,
   jsonb_agg(jsonb_build_object('seed',seed_object_id,'candidate',candidate_object_id)
     ORDER BY seed_object_id,candidate_object_id) AS pairs
 FROM pairs GROUP BY alert_id
)
