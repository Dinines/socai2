# v1 数据库表与结果关联

[返回入口](README.md)。本篇为当前告警/调查主链的数据字典索引。按2026-10-23最新交接要求，业务后端可以按已授权身份直接查询已有表，自行完成页面聚合；HTTP说明仍保留。先看[数据库位置、页面字段与SQL](alert-investigation-ui.md)，本篇补充表关系与其他存储。

22:56实际PG盘点已保存：25张表、428字段及实际主外键/约束，见[表与落地盘点](data-inventory.md)、[字段目录](table-fields.md)及[机器字典](data-catalog.json)。本轮2例的21条步骤事件、21份工件正文已读回，完整性与缺口分开记录；生产租户总量含此前发布canary。

## 1. ID关系

| ID | 产生位置 | 关联方式 |
| --- | --- | --- |
| source_alert_id | 上游稳定告警UUID | 与tenant/source/connector组成source-v1身份，不等于PG alerts.id |
| canonical Alert ID | Fusion确定性UUID | alerts.id、fused.id/alert_row_id/alert.id；Case.alert_ids用这个UUID |
| source_event_ids/external_id | 上游原事件/finding引用 | 回溯原厂资料，不作为canonical指纹的替代 |
| Fusion incident_id | Fusion关联器 | Redis摘要；PG在alerts.enrichment_data.socai2_fusion.incident_id留关联，无独立PG incidents主表 |
| Case ID | Case API | 正式PG表aisoc_cases.id；与Incident并非自动一对一 |
| Run ID | Agents对应入口 | investigation_runs.id；事件/工件通过run_id关联 |
| Run.case_id | 外部关联字符串 | VARCHAR(200)，不是Case外键；普通自动分诊常为Alert UUID，人工为Case，独立graph可为Incident |

后端应保存自己触发时取得的tenant+Alert/Case/Run对应关系；不要对Run.case_id无条件CAST UUID后JOIN Case。自动升级沿同Run时`start_run ON CONFLICT DO NOTHING`通常保留首次Alert关联。

## 2. 主表字典

完整字段以顺序应用后的SQL迁移为准，ORM/单份早期DDL不能单独代表现有schema。

| 表 | 主键/关系 | 主要字段及类型 | 写入者/读取方式 |
| --- | --- | --- | --- |
| tenants | id UUID PK | name/slug、is_active、settings/limits JSONB | 管理配置；租户必须真实存在 |
| connectors | id UUID PK，tenant_id | connector_type/vendor、config/credentials_enc JSONB | 原连接器配置；直接Kafka仍由受控生产者映射connector |
| alerts | id UUID PK，tenant_id FK tenants | title VARCHAR(500)、severity VARCHAR(20)、status VARCHAR(30)、priority INTEGER；raw_event/entities/iocs/mitre_*/source_event_ids JSONB；event_time/created_at/updated_at/resolved_at TIMESTAMPTZ | Fusion AlertSink写首次结果；Agents投影分诊；GET /alerts/{id} |
| alerts扩展字段 | 同上 | enrichment_data JSONB、dedup_hash VARCHAR(64)、confidence INTEGER及label/rationale、disposition/ai_score/ai_summary/ai_recommendations、case_id UUID | 身份/Incident和首次快照在enrichment_data.socai2_fusion；confidence通常0–100，非fused 0–1 |
| alert_source_links | id UUID PK；tenant_id、alert_id FK | vendor/external_id TEXT；UNIQUE(alert_id,vendor,external_id)；executed BOOLEAN、最后回写结果 | Fusion建来源关联，受控source-writeback记录；不证明已执行厂商动作 |
| aisoc_cases | id UUID PK，tenant_id；tenant+case_number唯一 | case_number TEXT、title/status/severity；alert_ids UUID[]；observable_graph/evidence_chain/mitre_* JSONB；opened/triaged/resolved/closed时间 | Case API创建和关联；正式Case表不是旧cases |
| investigation_runs | id UUID PK、tenant_id FK；case_id VARCHAR(200)非FK | raw_alert JSONB、alert_summary TEXT、model_used、status/error；iterations/total_tokens；cost与measured/estimated/unpriced计数；started/completed/created时间 | Agents ledger；GET /investigations及/{run_id} |
| investigation_events | id UUID PK；run_id FK、tenant_id FK；UNIQUE(run_id,seq) | seq INTEGER可-1；ts、kind VARCHAR(40)、agent VARCHAR(80)、summary TEXT、payload JSONB、input/output_hash、duration_ms | 追加步骤与结论；events/explain读取；有不可改删保护 |
| investigation_artifacts | id UUID PK；run_id FK、event_id可空FK、tenant_id | kind VARCHAR(40)、content TEXT或blob_ref、sha256 VARCHAR(64)、size_bytes、created_at | prompt/response、graph_result、report_md及读取回执等；列表/详情API |
| aisoc_run_costs | 复合PK(run_id TEXT,tenant_id TEXT,model TEXT)；非UUID FK | tokens、call_count、latency、measured/estimated/unpriced费用/次数、resolved_model | CostTracker写；Run成本聚合及costs接口读，关联时谨慎用文本 |
| aisoc_dead_letters | Fusion失败账本，tenant可能未知 | topic/reason/schema_version/payload_excerpt/source_event_id/topic_partition/kafka_offset | Fusion DLQ sink；不是Agents Kafka DLQ表，不盲目原文重放 |

字段来源：[001 alerts](../../../services/api/migrations/001_init.sql)、[008 ledger](../../../services/api/migrations/008_investigation_ledger.sql)、[012 Case](../../../services/api/migrations/012_case_management.sql)、[057来源关联](../../../services/api/migrations/057_alert_source_links.sql)、[063成本](../../../services/api/migrations/063_cost_provenance.sql)、[083 Case整合](../../../services/api/migrations/083_one_case_table.sql)、[Fusion实际写入](../../../services/fusion/app/services/alert_sink.py)、[Agents实际写入](../../../services/agents/app/investigator/ledger.py)。

旧`cases`已整合为`aisoc_cases`，历史表`cases_pre_consolidation`不作新业务数据源。`alerts.idempotency_key`的部分唯一索引属于HTTP submit辅助路径，不是Kafka幂等合同。API模型可能不返回所有DB列，不能把直表列名当同名API字段都存在。

## 3. 直接支撑数据

| 表/表组 | 用途及关键关联 | 输入与输出 |
| --- | --- | --- |
| assets / asset_vulnerabilities / alert_asset_correlations | tenant资产、资产漏洞、Alert与资产/漏洞关联 | 已有资产模块提供；processing-context消费，非告警模块自动采集CMDB |
| identity_privilege | tenant+principal权限层级/特权账号属性 | 身份权限来源→上下文；与identity_nodes/identity_edges关系图不同 |
| identity_nodes / identity_edges | tenant身份实体/关系 | 已有导入/身份图读取，不等于当前HR授权事实 |
| aisoc_context_statements | 组织事实、scope、expires_at | 配置/分析员反馈→组织记忆读取；null expires_at表示永久 |
| aisoc_analyst_feedback | AI/人工disposition、reason_code/note/context、可空alert_id | 分析员意见→近期处置上下文，个人意见不直接变成现场事实 |
| aisoc_kb_documents | tenant文档分块，title/content/doc_kind/chunk/tags，PG全文索引 | 文档导入→知识读取与prompt采用；不是已完整建成向量RAG |
| aisoc_tenant_skills / aisoc_tenant_skill_versions | tenant+skill_id，版本、body/source_yaml、expires_at | 技能配置→固定版本读取；版本历史与当前头分开 |
| ueba_entity_baselines / ueba_anomalies / ueba_peer_groups | tenant/entity_type/entity_id；feature_stats/window、异常score/risk/z_scores/source_event_id | 规范化事件→UEBA消费/基线/异常；独立Alembic版本表alembic_version_ueba |

来源：[资产](../../../services/api/migrations/013_asset_inventory.sql)、[权限](../../../services/api/migrations/085_asset_context_scoring.sql)、[反馈及组织事实](../../../services/api/migrations/052_analyst_feedback.sql)、[知识](../../../services/api/migrations/016_knowledge_base.sql)、[技能](../../../services/api/migrations/070_tenant_skills.sql)、[UEBA](../../../services/ueba/alembic/versions/0001_initial_ueba_tables.py)。原processing-context按维度有条数/时间边界，不能因接口200就当完整资产/权限历史。

## 4. 其他存储的真实数据对象

| 存储 | 对象 | 输入→输出 | 接口边界 |
| --- | --- | --- | --- |
| Redis Fusion DB9 | aisoc:fusion:dedup:*、correlation:*、incident:*、delivery:v1:*，chain:*等TTL状态 | 告警/异常→去重/关联/恢复/评分 | key内部格式不是对外长期合同，Incident不是PG独立表 |
| ClickHouse aisoc.raw_events | event_id/tenant_id UUID、event_time DateTime64(3,UTC)、实体/进程/OCSF/raw数据 | Kafka规范化事件→湖→SQL/调查工具 | ReplacingMergeTree(ingest_time)，不是实时唯一主键；去重查询按FINAL或适当LIMIT 1 BY |
| ClickHouse其他定义 | aisoc.alert_metrics、aisoc.ioc_enrichments等DDL | 以实际writer/已有资料为准 | DDL存在不等于每张表已持续写入或有完整数据 |
| OpenSearch | socai2-threatintel-iocs / socai2-threatintel-actors | TI导入/Feed代码→IOC/actor检索 | 仅IOC/actor项目索引已有基本实证；原始事件全文索引未接 |
| Neo4j | Alert/Host/User/IOC/Case、共享Technique；OBSERVED_ON/INVOLVES_USER/MAPS_TO/CONTAINS_IOC/CONTAINS_ALERT等 | 已有关系及候选PG投影→上下文/Path | v1.0.0已部署；本轮两Alert直接关系3/5条已读回；关系连通不等于攻击因果 |
| Qdrant | socai2_threatintel_iocs / socai2_threatintel_actors（1536维） | TI向量集合→语义读者 | 已配置/创建但已有实测为空；1D1024维smoke集合不作同空间证据 |

[ClickHouse DDL](../../../services/api/clickhouse/001_init.sql)、[Redis关联器](../../../services/fusion/app/services/correlator.py)、[图写读实现](../../../services/api/app/services/graph_service.py)、[TI存储实现](../../../services/threatintel/app/storage/opensearch.py)、[full净化回执](../../operations/full-support-migration.json)。

## 5. 租户与只读查询

API在事务里设置`app.current_tenant_id`，同时加tenant条件。直连后端也必须每次事务绑定并显式过滤，连接池归还后下次重设；变量不是`app.tenant_id`。

```sql
BEGIN READ ONLY;
SELECT set_config('app.current_tenant_id', '实际租户UUID', TRUE);
-- 随后所有SELECT仍加 tenant_id = 实际租户UUID
ROLLBACK;
```

当前若干RLS policy包含`current_tenant_id() IS NULL`兼容分支，部分内部角色还可绕过RLS；**未设置变量不能当作自动拒绝跨tenant查询**。直查沿用已授权的只读身份和表范围，并显式绑定/过滤租户；连接凭据由运维交接，不把runtime/owner作为后端管理员发放。[RLS实际实现](../../../services/api/app/db/rls.py)、[初始policy](../../../services/api/migrations/002_rls.sql)、[补充policy](../../../services/api/migrations/060_rls_coverage.sql)

可交给数据后端的完整只读样例见[read-results.sql](examples/read-results.sql)：Alert→常见自动Run→步骤→工件摘要，以及独立Case关系读取。样例只读、不执行DDL/INSERT/UPDATE/DELETE，不修改历史步骤或报告。另有[本轮两个真实Run SQL](examples/production-two-examples.sql)，按实际字段整理；实际定向PG查询及正文校验见[核验回执](../../operations/service-v1-functional-20261022.md)。

## 6. 字段解释规则

事件发生时间、模型/工具查询时间、入库时间分别保留；统一对外ISO8601带时区。risk_score缺失/null是未知，明确0不是缺失。fused.confidence_score 0–1、PG confidence 0–100、分诊ai_score/模型自报confidence和风险优先级不同。

`measured_call_count=0`时total_cost_usd数字0不能显示为实际免费；estimated与measured分开，unpriced保留。报告/工具错误/部分结果不改写成“未发现攻击”；旧Run与失败证据不由这次文档补齐或重调。
