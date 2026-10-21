# 2C-02 PG处理上下文

本批范围：按已授权tenant/告警读取现有assets、identity_privilege、asset_vulnerabilities及历史alerts，返回匹配标识、来源/更新时间、查询时间和状态，并实际调用现有score_alert_priority产生独立的解释结果。不建设库存/采集，不改变原告警严重度、priority、Fusion分数或队列排序，不改写旧材料。

接口为只读GET /api/v1/alerts/{id}/processing-context，要求alerts:read。按精确host/fqdn/IP及已有关联匹配资产，按规范化账号匹配已有权限；仅在唯一资产/身份时评分，多匹配明确ambiguous。失败维度用隔离事务保留其他维度，评分不伪用缺失依赖。历史仅指此前同实体告警，普通事件日志/UEBA明确未配置，不将二者混淆。

验收使用独立tenant中的有来源测试材料及真实告警链：匹配/无匹配、另一tenant、已修复漏洞排除、过去/未来时间界限、材料修改只影响后续查询、重启回查及只读无旧行改写。真实PG与故障替身分层记录；不通过全库/服务停机制造测试条件。2C-02 PG路径限定验收通过，整个2C尚未完成。结构化结果见[JSON](2c-processing-context.json)，来源见[清单](../handoff/2c-context-source-manifest.json)和[补丁](../../deploy/aisoc21/patches/2c-processing-context.patch)。下一项2C-03为已有事件历史/UEBA来源核对与读取。

## 数据与真实消费

本批是明确标记的[合成读取合同材料](../../tests/porting/fixtures/processing-context-2c.json)，没有真实CMDB/HR/扫描器导出。仅使用现有5张表，没有创建库存系统、扫描任务或新表。操作前这些上下文表在本项目库中均无行，旧项目/共享其他库未改。

API按认证tenant与告警ID定位，再按精确主机名/FQDN/IP或现有alert_asset_correlations读取资产；账号规范化后匹配identity_privilege。只读开放漏洞（remediated_at为空），读近7天同实体且时间早于当前告警的历史alerts。每个维度输出source、记录ID/字段/时间、status与truncated，优先级真正调用固定上游score_alert_priority，不是只保存材料后宣称消费。

| 输入 → 实际数据/调用 | 最终值与关系 |
| --- | --- |
| A当前medium告警 → high资产、admin权限、1条开放已利用标记漏洞 → 原算法 | `350 × 1.3 × 1.15 × 1.35 = 706.3875`，取整706；返回3项rationale和确切asset/identity ID |
| 同host/account另一tenant B → low资产、standard权限 | 280；不能读A告警（404），不混入A资产/权限/历史 |
| A无匹配host/account | assets/identities=no_match，vulnerabilities=not_requested，基值350且material_complete=false，不解释为已确认没有风险 |
| 无同名/IP匹配、只有显式关联的告警 | 命中关联的A资产，identity=not_requested，初始评分523，证明现有关联读取生效 |
| A开放与已修复漏洞 | 只返回开放行；已修复行即使含kev标记也不进评分，不伪造KEV暴露 |
| A过去/当前/未来同实体告警 | 只返回先前1条；当前和未来、另一tenant排除。时间是提供的event_time，缺失才用created_at，不验证源时钟真实性 |
| 只改A测试资产criticality为low | 后续当前视图变435，B仍280；此前运维证据706保持，原告警仍medium/priority50、原材料不改 |
| 真实PG错误：独立探针将资产SELECT换为不存在表 | assets/vulnerabilities=unavailable，identities/history仍matched，partial=true、score=null；同一会话恢复原SELECT后435，证明SAVEPOINT真正隔离失败 |
| API重启 | 4组当前上下文及原告警共8次回查保持（除queried_at），未重发输入 |

共6条真实alert-ingress受理、6条新PG/API告警；本批复用既有Fusion链，不另做fused主题全量读取。38项HTTP检查（受理/首次确认/旧接口404共13，更新后14，重启8，停用key3），30项相关测试通过，原测试未改。缺接口在更新前对真实已存在告警返回404，更新后返回结构化视图。

## 读取、评分与原事实的边界

该接口是**当前只读视图**，不是历史as-of快照或新的持久决策账本。当前材料的ID/source/updated_at/last_seen与查询时间分开；identity更新时间是记录更新/导入时间，不代表业务生效时间。各SELECT在READ COMMITTED下顺序读取，不宣称原子跨维度快照。

`priority`是独立解释结果：不覆盖alerts.priority/priority_score、严重度、Fusion置信度或队列顺序。上游队列目前没有自动把资产/身份材料接到排序，本批未改该策略。评分源码SHA256随响应返回；记录来源与参数可复核。`material_complete`只代表唯一资产/权限候选及可用漏洞查询满足本评分所需，不证明owner、HR、所有漏洞、时效或来源真实性完整。

多个候选或所需材料被20行上限截断，返回ambiguous/score=null；依赖失败返回unavailable及partial，不假装为空。无匹配与未提供账号/无资产等not_requested分别说明。缺owner保持null。metadata只投影来源、观测标记及本评分需要的布尔字段，不输出整份任意元数据。

每维度SAVEPOINT与3秒statement_timeout避免一次可选查询错误污染整个PG事务。真实错误注入仅作用于独立探针进程，没有停止共享PG或修改生产查询常量；初始身份/告警查询时数据库全不可用尚未验。

## 部署与保留

仅API更新并定向重启为`sha256:b77da9c81bc2868cd5d3bd9f21d02e94316d949b441582324fcdd2da5207214c`，新增1个服务文件并在现有alerts路由添加入口。无DDL/新依赖/env变化，原全部app文件及99锁依赖核对一致。IOC层后再加[context层](../../deploy/aisoc21/compose.context-2c.yml)，当前完整十层命令见[操作说明](../../deploy/aisoc21/README.md#当前api2c-02-pg处理上下文)。

30条旧告警材料hash保持，新增6行总36；保留本批2资产/2权限/2漏洞/1关联及标记原文。其他35容器/18卷、134迁移保持，3测试key已停用401，Kafka lag0，网关调用数不增。测试记录只用于隔离tenant，不能作真实生产材料；没有清库/清卷。批次有状态工具已执行，不能重跑旧标记/检查点。

回退前停止新输入并核队列，以保留IOC API镜像启动；会失去此新增接口，既有事实/上下文行保持，不改写分数。API只读响应的历史版本在运维回执保留，不冒充已入调查ledger。

## 未完成

- 外部普通事件历史/认证日志与UEBA在本接口明确not_configured；此前告警历史不替代它们，2C-03继续核已有来源，不建设采集/检测生产系统。
- 真实CMDB/HR/扫描器同步、人员/部门/雇佣状态、business-effective/as-of追溯、资料真实性/时效/召回质量未验。
- 并发/大数据量/完整数据库故障/其他坏数据转换未验；行数和3秒限时不是性能承诺。
- 没有向调查模型送入这些材料；模型/知识消费、自动Kafka分诊、抑制持久账本到3A后续分别验。Agents旧增强工具和Fusion ML认证503限制保持。

本批无模型、厂商动作，费用unknown。
