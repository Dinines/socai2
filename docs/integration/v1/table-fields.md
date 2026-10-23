# v1 PG实际字段与约束目录

[返回数据盘点](data-inventory.md) · [机器字典](data-catalog.json)

采集时间：`2026-10-22T22:56:23.350081+08:00`。只读查询21 PG public元数据；25张实际表，计数仅生产租户。本页不执行DDL，不包含凭据或业务正文。类型按data_type/udt_name如实记录；未采集varchar长度与numeric精度时不猜测，完整建表定义仍以部署迁移为准。

每字段列出是否可NULL及当前默认表达式；PK/FK/UNIQUE/CHECK来自实际pg_constraint。后端优先使用查询API；此字典用于字段映射及获授权的只读SQL。

## tenants

生产tenant行数：**1**；字段数：15。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | uuid_generate_v4() |
| name | character varying | varchar | NO | — |
| slug | character varying | varchar | NO | — |
| plan | character varying | varchar | YES | 'starter'::character varying |
| is_active | boolean | bool | YES | true |
| settings | jsonb | jsonb | YES | '{}'::jsonb |
| limits | jsonb | jsonb | YES | '{}'::jsonb |
| created_at | timestamp with time zone | timestamptz | YES | now() |
| updated_at | timestamp with time zone | timestamptz | YES | now() |
| parent_tenant_id | uuid | uuid | YES | — |
| mssp_role | text | text | NO | 'standalone'::text |
| provisioned_from_waitlist_id | uuid | uuid | YES | — |
| provisioned_at | timestamp with time zone | timestamptz | YES | — |
| data_region | text | text | YES | — |
| residency_enforced | boolean | bool | NO | false |

实际约束：

- `tenants_mssp_role_check`：`CHECK ((mssp_role = ANY (ARRAY['standalone'::text, 'parent'::text, 'child'::text])))`
- `tenants_parent_tenant_id_fkey`：`FOREIGN KEY (parent_tenant_id) REFERENCES tenants(id) ON DELETE SET NULL`
- `tenants_provisioned_from_waitlist_fk`：`FOREIGN KEY (provisioned_from_waitlist_id) REFERENCES aisoc_waitlist_entries(id) ON DELETE SET NULL`
- `tenants_pkey`：`PRIMARY KEY (id)`
- `tenants_slug_key`：`UNIQUE (slug)`

## connectors

生产tenant行数：**0**；字段数：29。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | uuid_generate_v4() |
| tenant_id | uuid | uuid | NO | — |
| name | character varying | varchar | NO | — |
| connector_type | character varying | varchar | NO | — |
| connector_config | jsonb | jsonb | YES | '{}'::jsonb |
| auth_config | jsonb | jsonb | YES | '{}'::jsonb |
| is_enabled | boolean | bool | YES | true |
| health_status | character varying | varchar | YES | 'unknown'::character varying |
| last_sync | timestamp with time zone | timestamptz | YES | — |
| events_ingested | bigint | int8 | YES | 0 |
| created_at | timestamp with time zone | timestamptz | YES | now() |
| updated_at | timestamp with time zone | timestamptz | YES | now() |
| category | character varying | varchar | NO | ''::character varying |
| last_health_check | timestamp with time zone | timestamptz | YES | — |
| error_count | integer | int4 | YES | 0 |
| tags | jsonb | jsonb | YES | '[]'::jsonb |
| schema_fingerprint | text | text | YES | — |
| last_schema_drift_at | timestamp with time zone | timestamptz | YES | — |
| last_drift_details | jsonb | jsonb | YES | — |
| events_dropped | integer | int4 | NO | 0 |
| last_event_at | timestamp with time zone | timestamptz | YES | — |
| last_event_kind | text | text | YES | — |
| ingest_token | text | text | YES | — |
| oauth_provisioned | boolean | bool | NO | false |
| allowed_capabilities | jsonb | jsonb | YES | — |
| oauth_refresh_failures | integer | int4 | NO | 0 |
| oauth_last_refresh_at | timestamp with time zone | timestamptz | YES | — |
| last_outage_at | timestamp with time zone | timestamptz | YES | — |
| last_backfill_at | timestamp with time zone | timestamptz | YES | — |

实际约束：

- `connectors_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `connectors_pkey`：`PRIMARY KEY (id)`
- `connectors_ingest_token_key`：`UNIQUE (ingest_token)`

## alerts

生产tenant行数：**3**；字段数：63。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | uuid_generate_v4() |
| tenant_id | uuid | uuid | NO | — |
| title | character varying | varchar | NO | — |
| description | text | text | YES | — |
| severity | character varying | varchar | NO | 'medium'::character varying |
| status | character varying | varchar | NO | 'new'::character varying |
| priority | integer | int4 | YES | 50 |
| category | character varying | varchar | YES | — |
| mitre_tactics | jsonb | jsonb | YES | '[]'::jsonb |
| mitre_techniques | jsonb | jsonb | YES | '[]'::jsonb |
| connector_id | uuid | uuid | YES | — |
| connector_type | character varying | varchar | YES | — |
| source_event_ids | jsonb | jsonb | YES | '[]'::jsonb |
| ocsf_class_uid | integer | int4 | YES | — |
| ai_score | double precision | float8 | YES | — |
| ai_summary | text | text | YES | — |
| ai_recommendations | jsonb | jsonb | YES | '[]'::jsonb |
| false_positive_score | double precision | float8 | YES | — |
| anomaly_score | double precision | float8 | YES | — |
| iocs | jsonb | jsonb | YES | '[]'::jsonb |
| entities | jsonb | jsonb | YES | '[]'::jsonb |
| raw_event | jsonb | jsonb | YES | '{}'::jsonb |
| dedup_hash | character varying | varchar | YES | — |
| case_id | uuid | uuid | YES | — |
| first_seen | timestamp with time zone | timestamptz | YES | now() |
| last_seen | timestamp with time zone | timestamptz | YES | now() |
| event_time | timestamp with time zone | timestamptz | YES | now() |
| resolved_at | timestamp with time zone | timestamptz | YES | — |
| created_at | timestamp with time zone | timestamptz | YES | now() |
| updated_at | timestamp with time zone | timestamptz | YES | now() |
| snoozed_until | timestamp with time zone | timestamptz | YES | — |
| snoozed_by_id | uuid | uuid | YES | — |
| disposition | text | text | YES | — |
| first_seen_at | timestamp with time zone | timestamptz | YES | — |
| confidence | integer | int4 | YES | — |
| confidence_label | text | text | YES | — |
| confidence_rationale | jsonb | jsonb | YES | — |
| narrative | text | text | YES | — |
| affected_ips | jsonb | jsonb | NO | '[]'::jsonb |
| affected_hosts | jsonb | jsonb | NO | '[]'::jsonb |
| affected_users | jsonb | jsonb | NO | '[]'::jsonb |
| affected_assets | jsonb | jsonb | NO | '[]'::jsonb |
| parent_alert_id | uuid | uuid | YES | — |
| child_alert_ids | jsonb | jsonb | NO | '[]'::jsonb |
| is_merged | boolean | bool | NO | false |
| assigned_to_id | uuid | uuid | YES | — |
| assigned_at | timestamp with time zone | timestamptz | YES | — |
| enrichment_data | jsonb | jsonb | NO | '{}'::jsonb |
| tags | jsonb | jsonb | NO | '[]'::jsonb |
| idempotency_key | text | text | YES | — |
| rule_id | text | text | YES | — |
| rule_name | text | text | YES | — |
| triage_groundedness | double precision | float8 | YES | — |
| triage_ungrounded | boolean | bool | YES | — |
| is_synthetic | boolean | bool | NO | false |
| synthetic_source | text | text | YES | — |
| synthetic_scenario | text | text | YES | — |
| external_id | text | text | YES | — |
| priority_score | integer | int4 | YES | — |
| priority_rationale | jsonb | jsonb | NO | '[]'::jsonb |
| session_id | uuid | uuid | YES | — |
| session_key_kind | text | text | YES | — |
| originating_human | text | text | YES | — |

实际约束：

- `ck_alerts_confidence_label_enum`：`CHECK (((confidence_label IS NULL) OR (confidence_label = ANY (ARRAY['high'::text, 'medium'::text, 'low'::text]))))`
- `ck_alerts_confidence_range`：`CHECK (((confidence IS NULL) OR ((confidence >= 0) AND (confidence <= 100))))`
- `alerts_session_id_fkey`：`FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL`
- `alerts_snoozed_by_id_fkey`：`FOREIGN KEY (snoozed_by_id) REFERENCES users(id) ON DELETE SET NULL`
- `alerts_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `alerts_pkey`：`PRIMARY KEY (id)`

## alert_source_links

生产tenant行数：**0**；字段数：15。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | uuid_generate_v4() |
| tenant_id | uuid | uuid | NO | — |
| alert_id | uuid | uuid | NO | — |
| vendor | text | text | NO | — |
| connector_instance_id | uuid | uuid | YES | — |
| external_id | text | text | NO | — |
| external_url | text | text | YES | — |
| last_disposition | text | text | YES | — |
| last_writeback_action | text | text | YES | — |
| last_writeback_status | text | text | YES | — |
| last_writeback_at | timestamp with time zone | timestamptz | YES | — |
| last_writeback_detail | text | text | YES | — |
| executed | boolean | bool | NO | — |
| created_at | timestamp with time zone | timestamptz | NO | now() |
| updated_at | timestamp with time zone | timestamptz | NO | now() |

实际约束：

- `alert_source_links_alert_id_fkey`：`FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE`
- `alert_source_links_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `alert_source_links_pkey`：`PRIMARY KEY (id)`
- `uq_alert_source_link`：`UNIQUE (alert_id, vendor, external_id)`

## aisoc_cases

生产tenant行数：**0**；字段数：48。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | YES | — |
| title | text | text | NO | — |
| description | text | text | YES | — |
| severity | text | text | NO | 'medium'::text |
| status | text | text | NO | 'new'::text |
| assignee | text | text | YES | — |
| mitre_techniques | jsonb | jsonb | YES | '[]'::jsonb |
| alert_ids | ARRAY | _uuid | YES | ARRAY[]::uuid[] |
| observable_graph | jsonb | jsonb | YES | '{}'::jsonb |
| evidence_chain | jsonb | jsonb | YES | '[]'::jsonb |
| compliance_frameworks | ARRAY | _text | YES | ARRAY[]::text[] |
| opened_at | timestamp with time zone | timestamptz | NO | now() |
| triaged_at | timestamp with time zone | timestamptz | YES | — |
| resolved_at | timestamp with time zone | timestamptz | YES | — |
| closed_at | timestamp with time zone | timestamptz | YES | — |
| created_at | timestamp with time zone | timestamptz | NO | now() |
| updated_at | timestamp with time zone | timestamptz | NO | now() |
| created_by | text | text | YES | — |
| tags | jsonb | jsonb | YES | '{}'::jsonb |
| sla_due_at | timestamp with time zone | timestamptz | YES | — |
| case_number | text | text | YES | — |
| priority | text | text | YES | — |
| case_type | text | text | YES | — |
| mitre_tactics | jsonb | jsonb | NO | '[]'::jsonb |
| assigned_to_id | uuid | uuid | YES | — |
| assigned_at | timestamp with time zone | timestamptz | YES | — |
| created_by_id | uuid | uuid | YES | — |
| sla_deadline | timestamp with time zone | timestamptz | YES | — |
| sla_breached | boolean | bool | NO | false |
| ioc_ids | jsonb | jsonb | NO | '[]'::jsonb |
| artifact_ids | jsonb | jsonb | NO | '[]'::jsonb |
| ticket_refs | jsonb | jsonb | NO | '[]'::jsonb |
| summary | text | text | YES | — |
| resolution | text | text | YES | — |
| lessons_learned | text | text | YES | — |
| queue_id | uuid | uuid | YES | — |
| sla_policy_id | uuid | uuid | YES | — |
| ack_due_at | timestamp with time zone | timestamptz | YES | — |
| resolve_due_at | timestamp with time zone | timestamptz | YES | — |
| acknowledged_at | timestamp with time zone | timestamptz | YES | — |
| escalation_level | integer | int4 | NO | 0 |
| reopened_at | timestamp with time zone | timestamptz | YES | — |
| reopen_count | integer | int4 | NO | 0 |
| reopen_reason | text | text | YES | — |
| merged_into_id | uuid | uuid | YES | — |
| merged_at | timestamp with time zone | timestamptz | YES | — |
| merged_by | text | text | YES | — |

实际约束：

- `aisoc_cases_severity_check`：`CHECK ((severity = ANY (ARRAY['info'::text, 'low'::text, 'medium'::text, 'high'::text, 'critical'::text])))`
- `aisoc_cases_status_check`：`CHECK ((status = ANY (ARRAY['new'::text, 'triaged'::text, 'investigating'::text, 'contained'::text, 'resolved'::text, 'closed'::text])))`
- `aisoc_cases_merged_into_id_fkey`：`FOREIGN KEY (merged_into_id) REFERENCES aisoc_cases(id) ON DELETE SET NULL`
- `aisoc_cases_queue_id_fkey`：`FOREIGN KEY (queue_id) REFERENCES case_queues(id) ON DELETE SET NULL`
- `aisoc_cases_sla_policy_id_fkey`：`FOREIGN KEY (sla_policy_id) REFERENCES case_sla_policies(id) ON DELETE SET NULL`
- `aisoc_cases_pkey`：`PRIMARY KEY (id)`

## investigation_runs

生产tenant行数：**3**；字段数：18。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | uuid_generate_v4() |
| tenant_id | uuid | uuid | NO | — |
| case_id | character varying | varchar | NO | — |
| alert_summary | text | text | YES | — |
| raw_alert | jsonb | jsonb | YES | — |
| model_used | character varying | varchar | YES | — |
| status | character varying | varchar | NO | 'running'::character varying |
| error | text | text | YES | — |
| total_tokens | integer | int4 | NO | 0 |
| total_cost_usd | numeric | numeric | NO | 0 |
| iterations | integer | int4 | NO | 0 |
| started_at | timestamp with time zone | timestamptz | NO | now() |
| completed_at | timestamp with time zone | timestamptz | YES | — |
| created_at | timestamp with time zone | timestamptz | NO | now() |
| measured_call_count | integer | int4 | NO | 0 |
| estimated_cost_usd | numeric | numeric | NO | 0 |
| estimated_call_count | integer | int4 | NO | 0 |
| unpriced_call_count | integer | int4 | NO | 0 |

实际约束：

- `investigation_runs_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `investigation_runs_pkey`：`PRIMARY KEY (id)`

## investigation_events

生产tenant行数：**36**；字段数：13。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | uuid_generate_v4() |
| run_id | uuid | uuid | NO | — |
| tenant_id | uuid | uuid | NO | — |
| seq | integer | int4 | NO | — |
| ts | timestamp with time zone | timestamptz | NO | now() |
| kind | character varying | varchar | NO | — |
| agent | character varying | varchar | NO | — |
| summary | text | text | NO | — |
| payload | jsonb | jsonb | YES | — |
| input_hash | character varying | varchar | YES | — |
| output_hash | character varying | varchar | YES | — |
| duration_ms | integer | int4 | NO | 0 |
| created_at | timestamp with time zone | timestamptz | NO | now() |

实际约束：

- `investigation_events_run_id_fkey`：`FOREIGN KEY (run_id) REFERENCES investigation_runs(id) ON DELETE CASCADE`
- `investigation_events_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `investigation_events_pkey`：`PRIMARY KEY (id)`
- `investigation_events_run_id_seq_key`：`UNIQUE (run_id, seq)`

## investigation_artifacts

生产tenant行数：**35**；字段数：10。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | uuid_generate_v4() |
| run_id | uuid | uuid | NO | — |
| event_id | uuid | uuid | YES | — |
| tenant_id | uuid | uuid | NO | — |
| kind | character varying | varchar | NO | — |
| content | text | text | YES | — |
| blob_ref | text | text | YES | — |
| sha256 | character varying | varchar | NO | — |
| size_bytes | integer | int4 | NO | 0 |
| created_at | timestamp with time zone | timestamptz | NO | now() |

实际约束：

- `investigation_artifacts_event_id_fkey`：`FOREIGN KEY (event_id) REFERENCES investigation_events(id) ON DELETE CASCADE`
- `investigation_artifacts_run_id_fkey`：`FOREIGN KEY (run_id) REFERENCES investigation_runs(id) ON DELETE CASCADE`
- `investigation_artifacts_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `investigation_artifacts_pkey`：`PRIMARY KEY (id)`

## aisoc_run_costs

生产tenant行数：**5**；字段数：15。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| run_id | text | text | NO | — |
| tenant_id | text | text | NO | — |
| model | text | text | NO | — |
| total_prompt_tokens | integer | int4 | NO | 0 |
| total_completion_tokens | integer | int4 | NO | 0 |
| total_cost_usd | double precision | float8 | NO | 0 |
| total_latency_ms | double precision | float8 | NO | 0 |
| call_count | integer | int4 | NO | 0 |
| recorded_at | timestamp with time zone | timestamptz | NO | now() |
| measured_cost_usd | double precision | float8 | NO | 0 |
| measured_call_count | integer | int4 | NO | 0 |
| estimated_cost_usd | double precision | float8 | NO | 0 |
| estimated_call_count | integer | int4 | NO | 0 |
| unpriced_call_count | integer | int4 | NO | 0 |
| resolved_model | text | text | YES | — |

实际约束：

- `aisoc_run_costs_pkey`：`PRIMARY KEY (run_id, tenant_id, model)`

## socai2_triage_budget_reservations

生产tenant行数：**3**；字段数：9。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| run_id | uuid | uuid | NO | — |
| tenant_id | uuid | uuid | NO | — |
| policy_sha256 | character varying | varchar | NO | — |
| charged_tokens | integer | int4 | NO | — |
| reserved_at | timestamp with time zone | timestamptz | NO | clock_timestamp() |
| request_started_at | timestamp with time zone | timestamptz | YES | — |
| settled_at | timestamp with time zone | timestamptz | YES | — |
| outcome | character varying | varchar | NO | 'reserved'::character varying |
| observed_tokens | integer | int4 | YES | — |

实际约束：

- `socai2_triage_budget_reservations_charged_tokens_check`：`CHECK ((charged_tokens > 0))`
- `socai2_triage_budget_reservations_check`：`CHECK (((((outcome)::text = 'reserved'::text) AND (settled_at IS NULL)) OR (((outcome)::text <> 'reserved'::text) AND (settled_at IS NOT NULL))))`
- `socai2_triage_budget_reservations_check1`：`CHECK ((((outcome)::text <> 'responded'::text) OR (request_started_at IS NOT NULL)))`
- `socai2_triage_budget_reservations_observed_tokens_check`：`CHECK ((observed_tokens >= 0))`
- `socai2_triage_budget_reservations_outcome_check`：`CHECK (((outcome)::text = ANY ((ARRAY['reserved'::character varying, 'responded'::character varying, 'no_request'::character varying])::text[])))`
- `socai2_triage_budget_reservations_run_id_fkey`：`FOREIGN KEY (run_id) REFERENCES investigation_runs(id)`
- `socai2_triage_budget_reservations_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id)`
- `socai2_triage_budget_reservations_pkey`：`PRIMARY KEY (run_id)`

## aisoc_dead_letters

生产tenant行数：**0**；字段数：12。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | YES | — |
| topic | text | text | NO | — |
| reason | text | text | NO | — |
| schema_version | text | text | NO | 'unknown'::text |
| payload_excerpt | text | text | NO | ''::text |
| source_event_id | text | text | YES | — |
| occurred_at | timestamp with time zone | timestamptz | NO | now() |
| acknowledged_at | timestamp with time zone | timestamptz | YES | — |
| acknowledged_by | text | text | YES | — |
| topic_partition | integer | int4 | YES | — |
| kafka_offset | bigint | int8 | YES | — |

实际约束：

- `aisoc_dead_letters_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `aisoc_dead_letters_pkey`：`PRIMARY KEY (id)`

## assets

生产tenant行数：**0**；字段数：19。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | NO | — |
| asset_type | text | text | NO | 'host'::text |
| name | text | text | NO | — |
| fqdn | text | text | YES | — |
| ip_addresses | ARRAY | _text | YES | — |
| cloud_provider | text | text | YES | — |
| cloud_region | text | text | YES | — |
| cloud_account | text | text | YES | — |
| os | text | text | YES | — |
| os_version | text | text | YES | — |
| criticality | text | text | NO | 'medium'::text |
| tags | ARRAY | _text | YES | — |
| owner_email | text | text | YES | — |
| last_seen | timestamp with time zone | timestamptz | NO | now() |
| first_seen | timestamp with time zone | timestamptz | NO | now() |
| metadata | jsonb | jsonb | NO | '{}'::jsonb |
| created_at | timestamp with time zone | timestamptz | NO | now() |
| updated_at | timestamp with time zone | timestamptz | NO | now() |

实际约束：

- `assets_asset_type_check`：`CHECK ((asset_type = ANY (ARRAY['host'::text, 'container'::text, 'cloud_resource'::text, 'user_account'::text, 'service'::text, 'network_device'::text, 'domain'::text, 'ip'::text])))`
- `assets_criticality_check`：`CHECK ((criticality = ANY (ARRAY['critical'::text, 'high'::text, 'medium'::text, 'low'::text, 'info'::text])))`
- `assets_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `assets_pkey`：`PRIMARY KEY (id)`

## asset_vulnerabilities

生产tenant行数：**0**；字段数：21。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | NO | — |
| asset_id | uuid | uuid | NO | — |
| cve_id | text | text | YES | — |
| title | text | text | NO | — |
| description | text | text | YES | — |
| severity | text | text | NO | 'medium'::text |
| cvss_score | double precision | float8 | YES | — |
| cvss_vector | text | text | YES | — |
| epss_score | double precision | float8 | YES | — |
| is_exploited | boolean | bool | NO | false |
| source | text | text | NO | — |
| external_id | text | text | YES | — |
| first_found | timestamp with time zone | timestamptz | NO | now() |
| last_found | timestamp with time zone | timestamptz | NO | now() |
| remediated_at | timestamp with time zone | timestamptz | YES | — |
| metadata | jsonb | jsonb | NO | '{}'::jsonb |
| created_at | timestamp with time zone | timestamptz | NO | now() |
| environment | text | text | YES | — |
| patch_due_date | date | date | YES | — |
| patch_status | text | text | NO | 'tracked'::text |

实际约束：

- `asset_vulnerabilities_severity_check`：`CHECK ((severity = ANY (ARRAY['critical'::text, 'high'::text, 'medium'::text, 'low'::text, 'info'::text])))`
- `asset_vulnerabilities_asset_id_fkey`：`FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE`
- `asset_vulnerabilities_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `asset_vulnerabilities_pkey`：`PRIMARY KEY (id)`

## alert_asset_correlations

生产tenant行数：**0**；字段数：8。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | NO | — |
| alert_id | uuid | uuid | NO | — |
| asset_id | uuid | uuid | YES | — |
| vuln_id | uuid | uuid | YES | — |
| match_field | text | text | NO | 'ip'::text |
| confidence | double precision | float8 | NO | 1.0 |
| created_at | timestamp with time zone | timestamptz | NO | now() |

实际约束：

- `alert_asset_correlations_asset_id_fkey`：`FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE SET NULL`
- `alert_asset_correlations_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `alert_asset_correlations_vuln_id_fkey`：`FOREIGN KEY (vuln_id) REFERENCES asset_vulnerabilities(id) ON DELETE SET NULL`
- `alert_asset_correlations_pkey`：`PRIMARY KEY (id)`

## identity_privilege

生产tenant行数：**0**；字段数：8。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | NO | — |
| principal | text | text | NO | — |
| privilege_tier | text | text | NO | 'standard'::text |
| is_service | boolean | bool | NO | false |
| is_break_glass | boolean | bool | NO | false |
| source | text | text | YES | — |
| updated_at | timestamp with time zone | timestamptz | NO | now() |

实际约束：

- `ck_identity_privilege_tier`：`CHECK ((privilege_tier = ANY (ARRAY['standard'::text, 'elevated'::text, 'admin'::text, 'domain_admin'::text])))`
- `identity_privilege_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `identity_privilege_pkey`：`PRIMARY KEY (id)`
- `identity_privilege_tenant_id_principal_key`：`UNIQUE (tenant_id, principal)`

## identity_nodes

生产tenant行数：**0**；字段数：13。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | NO | — |
| node_type | text | text | NO | — |
| external_id | text | text | NO | — |
| display_name | text | text | YES | — |
| source_system | text | text | NO | — |
| risk_score | double precision | float8 | NO | 0.0 |
| privilege_tier | integer | int4 | NO | 0 |
| is_active | boolean | bool | NO | true |
| last_activity | timestamp with time zone | timestamptz | YES | — |
| attributes | jsonb | jsonb | NO | '{}'::jsonb |
| created_at | timestamp with time zone | timestamptz | NO | now() |
| updated_at | timestamp with time zone | timestamptz | NO | now() |

实际约束：

- `identity_nodes_node_type_check`：`CHECK ((node_type = ANY (ARRAY['human_user'::text, 'service_account'::text, 'device'::text, 'application'::text, 'group'::text, 'role'::text])))`
- `identity_nodes_privilege_tier_check`：`CHECK (((privilege_tier >= 0) AND (privilege_tier <= 3)))`
- `identity_nodes_risk_score_check`：`CHECK (((risk_score >= (0.0)::double precision) AND (risk_score <= (100.0)::double precision)))`
- `identity_nodes_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `identity_nodes_pkey`：`PRIMARY KEY (id)`
- `identity_nodes_tenant_id_source_system_external_id_key`：`UNIQUE (tenant_id, source_system, external_id)`

## identity_edges

生产tenant行数：**0**；字段数：10。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | NO | — |
| source_id | uuid | uuid | NO | — |
| target_id | uuid | uuid | NO | — |
| edge_type | text | text | NO | — |
| weight | double precision | float8 | NO | 1.0 |
| valid_from | timestamp with time zone | timestamptz | NO | now() |
| valid_until | timestamp with time zone | timestamptz | YES | — |
| evidence | jsonb | jsonb | NO | '{}'::jsonb |
| created_at | timestamp with time zone | timestamptz | NO | now() |

实际约束：

- `identity_edges_edge_type_check`：`CHECK ((edge_type = ANY (ARRAY['member_of'::text, 'manages'::text, 'owns'::text, 'delegates_to'::text, 'authenticated_to'::text, 'assumed_role'::text, 'accessed'::text, 'created'::text, 'lateral_movement_candidate'::text])))`
- `identity_edges_source_id_fkey`：`FOREIGN KEY (source_id) REFERENCES identity_nodes(id) ON DELETE CASCADE`
- `identity_edges_target_id_fkey`：`FOREIGN KEY (target_id) REFERENCES identity_nodes(id) ON DELETE CASCADE`
- `identity_edges_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `identity_edges_pkey`：`PRIMARY KEY (id)`
- `identity_edges_tenant_id_source_id_target_id_edge_type_key`：`UNIQUE (tenant_id, source_id, target_id, edge_type)`

## aisoc_context_statements

生产tenant行数：**0**；字段数：10。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | uuid_generate_v4() |
| tenant_id | uuid | uuid | NO | — |
| statement | text | text | NO | — |
| reason_code | text | text | NO | — |
| scope | text | text | NO | — |
| scope_value | text | text | NO | ''::text |
| observations | integer | int4 | NO | 1 |
| expires_at | timestamp with time zone | timestamptz | YES | — |
| created_at | timestamp with time zone | timestamptz | NO | now() |
| updated_at | timestamp with time zone | timestamptz | NO | now() |

实际约束：

- `aisoc_context_statements_pkey`：`PRIMARY KEY (id)`
- `uq_context_statement`：`UNIQUE (tenant_id, reason_code, scope, scope_value)`

## aisoc_analyst_feedback

生产tenant行数：**0**；字段数：12。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | uuid_generate_v4() |
| tenant_id | uuid | uuid | NO | — |
| alert_id | uuid | uuid | YES | — |
| ai_disposition | text | text | NO | — |
| analyst_disposition | text | text | NO | — |
| reason_code | text | text | NO | — |
| scope | text | text | NO | — |
| scope_value | text | text | NO | ''::text |
| analyst_id | text | text | NO | — |
| note | text | text | NO | ''::text |
| context | jsonb | jsonb | NO | '{}'::jsonb |
| created_at | timestamp with time zone | timestamptz | NO | now() |

实际约束：

- `aisoc_analyst_feedback_pkey`：`PRIMARY KEY (id)`

## aisoc_kb_documents

生产tenant行数：**0**；字段数：12。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | YES | — |
| title | text | text | NO | — |
| source_url | text | text | YES | — |
| doc_kind | text | text | NO | 'runbook'::text |
| content | text | text | NO | — |
| chunk_index | integer | int4 | YES | 0 |
| chunk_total | integer | int4 | YES | 1 |
| tags | ARRAY | _text | YES | ARRAY[]::text[] |
| created_at | timestamp with time zone | timestamptz | NO | now() |
| updated_at | timestamp with time zone | timestamptz | NO | now() |
| created_by | text | text | YES | — |

实际约束：

- `aisoc_kb_documents_doc_kind_check`：`CHECK ((doc_kind = ANY (ARRAY['runbook'::text, 'policy'::text, 'playbook'::text, 'sop'::text, 'wiki'::text, 'other'::text])))`
- `aisoc_kb_documents_pkey`：`PRIMARY KEY (id)`

## aisoc_tenant_skills

生产tenant行数：**0**；字段数：18。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | NO | — |
| skill_id | text | text | NO | — |
| version | integer | int4 | NO | 1 |
| status | text | text | NO | 'draft'::text |
| name | text | text | NO | — |
| owner | text | text | NO | — |
| expires_at | timestamp with time zone | timestamptz | NO | — |
| body | jsonb | jsonb | NO | — |
| source_yaml | text | text | NO | — |
| backtest_evaluation_id | uuid | uuid | YES | — |
| backtest_baseline_id | uuid | uuid | YES | — |
| backtest_version | integer | int4 | YES | — |
| activated_at | timestamp with time zone | timestamptz | YES | — |
| activated_by | uuid | uuid | YES | — |
| created_by | uuid | uuid | YES | — |
| created_at | timestamp with time zone | timestamptz | NO | now() |
| updated_at | timestamp with time zone | timestamptz | NO | now() |

实际约束：

- `aisoc_tenant_skills_active_is_backtested`：`CHECK (((status <> 'active'::text) OR ((backtest_evaluation_id IS NOT NULL) AND (backtest_baseline_id IS NOT NULL) AND (backtest_version = version))))`
- `aisoc_tenant_skills_skill_id_check`：`CHECK ((skill_id ~ '^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$'::text))`
- `aisoc_tenant_skills_status_check`：`CHECK ((status = ANY (ARRAY['draft'::text, 'backtested'::text, 'active'::text, 'retired'::text])))`
- `aisoc_tenant_skills_version_check`：`CHECK ((version >= 1))`
- `aisoc_tenant_skills_activated_by_fkey`：`FOREIGN KEY (activated_by) REFERENCES users(id) ON DELETE SET NULL`
- `aisoc_tenant_skills_backtest_baseline_id_fkey`：`FOREIGN KEY (backtest_baseline_id) REFERENCES aisoc_replay_evaluations(id) ON DELETE SET NULL`
- `aisoc_tenant_skills_backtest_evaluation_id_fkey`：`FOREIGN KEY (backtest_evaluation_id) REFERENCES aisoc_replay_evaluations(id) ON DELETE SET NULL`
- `aisoc_tenant_skills_created_by_fkey`：`FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- `aisoc_tenant_skills_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `aisoc_tenant_skills_pkey`：`PRIMARY KEY (id)`
- `aisoc_tenant_skills_tenant_id_skill_id_key`：`UNIQUE (tenant_id, skill_id)`

## aisoc_tenant_skill_versions

生产tenant行数：**0**；字段数：17。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | NO | — |
| skill_row_id | uuid | uuid | NO | — |
| skill_id | text | text | NO | — |
| version | integer | int4 | NO | — |
| name | text | text | NO | — |
| owner | text | text | NO | — |
| expires_at | timestamp with time zone | timestamptz | NO | — |
| body | jsonb | jsonb | NO | — |
| source_yaml | text | text | NO | — |
| backtest_evaluation_id | uuid | uuid | YES | — |
| backtest_baseline_id | uuid | uuid | YES | — |
| authored_by | uuid | uuid | YES | — |
| authored_at | timestamp with time zone | timestamptz | NO | now() |
| activated_at | timestamp with time zone | timestamptz | YES | — |
| activated_by | uuid | uuid | YES | — |
| retired_at | timestamp with time zone | timestamptz | YES | — |

实际约束：

- `aisoc_tenant_skill_versions_version_check`：`CHECK ((version >= 1))`
- `aisoc_tenant_skill_versions_activated_by_fkey`：`FOREIGN KEY (activated_by) REFERENCES users(id) ON DELETE SET NULL`
- `aisoc_tenant_skill_versions_authored_by_fkey`：`FOREIGN KEY (authored_by) REFERENCES users(id) ON DELETE SET NULL`
- `aisoc_tenant_skill_versions_backtest_baseline_id_fkey`：`FOREIGN KEY (backtest_baseline_id) REFERENCES aisoc_replay_evaluations(id) ON DELETE SET NULL`
- `aisoc_tenant_skill_versions_backtest_evaluation_id_fkey`：`FOREIGN KEY (backtest_evaluation_id) REFERENCES aisoc_replay_evaluations(id) ON DELETE SET NULL`
- `aisoc_tenant_skill_versions_skill_row_id_fkey`：`FOREIGN KEY (skill_row_id) REFERENCES aisoc_tenant_skills(id) ON DELETE CASCADE`
- `aisoc_tenant_skill_versions_tenant_id_fkey`：`FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE`
- `aisoc_tenant_skill_versions_pkey`：`PRIMARY KEY (id)`
- `aisoc_tenant_skill_versions_tenant_id_skill_id_version_key`：`UNIQUE (tenant_id, skill_id, version)`

## ueba_entity_baselines

生产tenant行数：**0**；字段数：11。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | NO | — |
| entity_type | character varying | varchar | NO | — |
| entity_id | character varying | varchar | NO | — |
| feature_stats | jsonb | jsonb | NO | '{}'::jsonb |
| window_start | timestamp with time zone | timestamptz | NO | — |
| window_end | timestamp with time zone | timestamptz | NO | — |
| observation_count | integer | int4 | NO | 0 |
| created_at | timestamp with time zone | timestamptz | YES | now() |
| updated_at | timestamp with time zone | timestamptz | YES | now() |
| peer_group_id | character varying | varchar | YES | — |

实际约束：

- `ueba_entity_baselines_pkey`：`PRIMARY KEY (id)`

## ueba_anomalies

生产tenant行数：**0**；字段数：14。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | uuid | uuid | NO | gen_random_uuid() |
| tenant_id | uuid | uuid | NO | — |
| entity_type | character varying | varchar | NO | — |
| entity_id | character varying | varchar | NO | — |
| event_type | character varying | varchar | NO | — |
| anomaly_score | double precision | float8 | NO | — |
| risk_level | character varying | varchar | NO | — |
| features | jsonb | jsonb | NO | '{}'::jsonb |
| z_scores | jsonb | jsonb | NO | '{}'::jsonb |
| peer_group_id | character varying | varchar | YES | — |
| peer_deviation_score | double precision | float8 | YES | — |
| source_event_id | character varying | varchar | YES | — |
| detected_at | timestamp with time zone | timestamptz | YES | now() |
| acknowledged | boolean | bool | NO | false |

实际约束：

- `ueba_anomalies_pkey`：`PRIMARY KEY (id)`

## ueba_peer_groups

生产tenant行数：**0**；字段数：8。

| 字段 | SQL类型 | UDT | 可NULL | 默认表达式 |
| --- | --- | --- | --- | --- |
| id | character varying | varchar | NO | — |
| tenant_id | uuid | uuid | NO | — |
| label | character varying | varchar | NO | — |
| entity_type | character varying | varchar | NO | — |
| feature_stats | jsonb | jsonb | NO | '{}'::jsonb |
| member_count | integer | int4 | NO | 0 |
| created_at | timestamp with time zone | timestamptz | YES | now() |
| updated_at | timestamp with time zone | timestamptz | YES | now() |

实际约束：

- `ueba_peer_groups_pkey`：`PRIMARY KEY (id)`
