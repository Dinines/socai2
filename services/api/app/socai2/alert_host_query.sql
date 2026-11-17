WITH seeds AS (
 SELECT * FROM jsonb_to_recordset(CAST(:seeds AS jsonb)) AS s(id uuid, namespace text, value text)
), pairs AS (
 SELECT a.id AS alert_id,a.event_time,s.id AS seed_object_id,o.id AS candidate_object_id
 FROM socai2.alerts a JOIN socai2.alert_materials m
   ON m.tenant_id=a.tenant_id AND m.alert_id=a.id AND m.id=a.latest_material_id
 JOIN socai2.alert_objects o
   ON o.tenant_id=a.tenant_id AND o.alert_id=a.id AND o.material_id=m.id AND o.object_type='host'
 JOIN seeds s ON s.namespace=o.namespace AND s.value=o.normalized_value
 WHERE a.tenant_id=:tenant AND a.source_namespace=:source AND a.id<>:seed_alert_id
   AND a.event_time IS NOT NULL
), candidates AS (
 SELECT alert_id,event_time,jsonb_agg(jsonb_build_object('seed',seed_object_id,'candidate',candidate_object_id)
   ORDER BY seed_object_id,candidate_object_id) AS pairs
 FROM pairs GROUP BY alert_id,event_time
)
