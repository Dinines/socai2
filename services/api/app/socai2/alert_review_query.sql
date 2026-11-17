WITH seeds AS (
 SELECT * FROM jsonb_to_recordset(CAST(:seeds AS jsonb)) AS s(
   id uuid, object_type text, namespace text, match_value text, algorithm text)
), seed_tactics AS (
 SELECT * FROM jsonb_to_recordset(CAST(:tactics AS jsonb)) AS t(label text, source_paths jsonb)
), current_materials AS (
 SELECT a.id AS alert_id, a.event_time, m.id AS material_id, m.detection
 FROM socai2.alerts a JOIN socai2.alert_materials m
   ON m.tenant_id=a.tenant_id AND m.alert_id=a.id AND m.id=a.latest_material_id
 WHERE a.tenant_id=:tenant AND a.source_namespace=:source AND a.id<>:seed_alert_id
   AND a.event_time>=:time_from AND a.event_time<:time_to
), candidate_tactics AS (
 SELECT m.alert_id, v.value#>>'{}' AS label,
   jsonb_agg('$.detection.tactics['||(v.ordinality-1)||']' ORDER BY v.ordinality) AS source_paths
 FROM current_materials m CROSS JOIN LATERAL jsonb_array_elements(
   CASE WHEN jsonb_typeof(m.detection->'tactics')='array' THEN m.detection->'tactics' ELSE '[]'::jsonb END
 ) WITH ORDINALITY AS v(value,ordinality)
 WHERE jsonb_typeof(v.value)='string' AND btrim(v.value#>>'{}')<>''
 GROUP BY m.alert_id,v.value#>>'{}'
), shared_tactics AS (
 SELECT c.alert_id, jsonb_agg(jsonb_build_object('label',c.label,'seed_source_paths',s.source_paths,
   'candidate_source_paths',c.source_paths) ORDER BY c.label) AS labels
 FROM candidate_tactics c JOIN seed_tactics s ON s.label=c.label GROUP BY c.alert_id
), current_objects AS (
 SELECT o.*, m.event_time,
   CASE WHEN o.object_type='hash' THEN lower(o.normalized_value) ELSE o.normalized_value END AS match_value,
   CASE WHEN o.object_type='hash' THEN upper(replace(replace(o.attributes->>'algorithm','-',''),'_','')) END AS algorithm
 FROM current_materials m JOIN socai2.alert_objects o
   ON o.tenant_id=:tenant AND o.alert_id=m.alert_id AND o.material_id=m.material_id
), pairs AS (
 SELECT o.alert_id,o.event_time,o.id AS candidate_object_id,s.id AS seed_object_id,
   CASE s.object_type WHEN 'host' THEN 'same_host_and_tactic' WHEN 'ip' THEN 'same_ip'
     ELSE 'same_hash_algorithm_and_value' END AS rule,
   CASE WHEN s.object_type='host' THEN t.labels ELSE '[]'::jsonb END AS tactics
 FROM current_objects o JOIN seeds s ON o.namespace=s.namespace AND o.object_type=s.object_type
   AND o.match_value=s.match_value AND o.algorithm IS NOT DISTINCT FROM s.algorithm
 LEFT JOIN shared_tactics t ON t.alert_id=o.alert_id
 WHERE s.object_type<>'host' OR t.labels IS NOT NULL
), candidates AS (
 SELECT alert_id,event_time,jsonb_agg(jsonb_build_object('seed',seed_object_id,'candidate',candidate_object_id,
   'rule',rule,'shared_tactics',tactics) ORDER BY seed_object_id,candidate_object_id) AS pairs
 FROM pairs GROUP BY alert_id,event_time
)
