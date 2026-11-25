# 调查 HTTP 告警发布候选

2026-11-25。Git 基准为 `167b596f6625635d347ecaefadf5d050a0e5eb19`。按 E54、Q04、告警管理三层既有冻结源码依次覆盖，12 处前置文件指纹及 1 处新增文件状态逐项相符。重建后共有 751 个应用文件，总 SHA-256 为 `458441e571ba4ab6cf504cf1d716181a08b2cbaae8d5d5fd3b7315deb6167d14`，与 21 的 `c173-alert-management-20261124-01` 发布回执相同。核对沿现有回执和本机源码完成。 [在运发布回执](../alert-management-feedback-21-20261124-01/deployment.json) · [在运独立复核](../integration-coordination-audit-20261124-01/alert-management-21-release-review.json)

## HEAD 到切换前 HTTP 的在运源码

以下是 11 个相对 HEAD 有差异的运行文件。路径以 `services/api/` 为前缀。统筹生成的在运补丁 SHA-256 为 `9eec69e51367f700373ca69790a6dc20286661ba42cead54f8c40c4d209b7bdb`，文件及校验清单在 `.local/validation/alert-git-21-release-20261125-01/http-runtime-candidate.patch` 和 `http-runtime-candidate-manifest.json`。

| 在运文件 | 应纳入的运行行为 | 在运 SHA-256 |
| --- | --- | --- |
| `app/socai2/list_export.py` | E54 告警选择 ID 与租户及其他筛选取交集 | `a55929c51340dc762b12b9b44e9612de1a695f51afe27771f84a33d0476b7cd1` |
| `app/socai2/list_query_contracts.py` | E54 专用 `AlertExportQuery.ids` | `b5a34244b890d3889bd0c47da59d487dce59e80c56bf8c90ec2728122e5ac4d5` |
| `app/socai2/owner_directory.py` | Q04 目录 DTO、显式 profile 和范围内投影查询 | `abae0d4803ca76256970f397c7ed7c268da7f9003ab9b45b84fb4047bd6f12b2` |
| `app/socai2/page_reader.py` | Q04 导入和 `PageReadService.people`，E30 告警活动按发生时间及 ID 倒序 | `674add39635fe1633786a3b08fcb4cb969206f56cee1d4bd81cddee015a98558` |
| `app/socai2/subject_management.py` | 告警锁定最新行后应用显式字段，事件原版本冲突分支继续生效 | `c8447404ae36caf9736a4681c3ca6143a892c16e92752da7a1647ab08e581fc4` |
| `app/socai2/subject_management_contracts.py` | E48–E51 告警专用版本、选中项及批量管理 DTO，批量拒绝显式 `tags` | `d5f98da880041d6f5f3ac066c0e4786e439498c7f2ea5219265d051861feb0d7` |
| `investigation_http/contracts.py` | E54 查询 DTO 与 Q04 查询、分页 DTO 导出 | `ea7281b5159eec9e974968682d0f6001179e0c68db7d0a8195c8757cf52a94e9` |
| `investigation_http/csv_export.py` | E54 单独允许 `ids` | `b301a3a995c7ab1d90ef3bb0e852b715419af99b1fdd304634a7c466194a9fcd` |
| `investigation_http/external_routes/exports.py` | E54 重复 UUID 参数和现有导出服务接线 | `241482713aaf2b9d3a423b2b93d4e28bd013b60e632d280774941dc9175b61c7` |
| `investigation_http/external_routes/pages.py` | Q04 `GET /people` 参数、租户上下文和调用 | `d0b95dcfe4c1388c525c016e67e63a786df462c134ef02493124fc49b2e373c4` |
| `investigation_http/ports.py` | Q04 `PageReads.people` | `0b4243cbf480cbbd73d0c7b5fed7d045a075efd11cea34a159dc4b9dbc8d04f2` |

E48–E51 路由文件 `investigation_http/external_routes/subject_management.py` 已在 HEAD，21 SHA-256 为 `3e24d8349edbcb68fbdb0b2f41dbb65b01541f6cde260ab9139194a46f136b85`。单条与批量业务路由复用同一事务和既有管理配置。E26、E28、E31、固定 A 及 Q27 实际读取依赖原有 `PageReader`、`page_contracts.py`、`material_json.py`、`adapters/material_response.py`、`stage_reader.py`、`external_routes/analysis.py`、`run_records.py`、`external_routes/run_records.py` 及其 DTO 和适配器。Q27 的旧查询跳过状态、`error.code`、计划参数及空返回已能从当前在运版本读取。 [材料及固定 Run](../alert-detail-material-support-20261124-01/verification.json) · [查询跳过独审](../alert-query-skipped-display-20261125-01/independent-review.json) · [新告警 E28/E31 和固定 A](../alert-score-first-receive-20261125-01/http-readback.json)

## 已验页面依赖的 21 补丁

负责人确认告警列表、预览、概况展示最近一轮**已发布**的 AI 判定及同轮 ATT&CK。切换前，21 要求 `valid_for_current_input` 才返回映射。页面直接消费 `triage.attck_mappings`，因此当前已失效评估会缺少已保存映射。候选沿现有已完成 Run、指针、告警归属及解释工件条件读取同一轮映射，新鲜度及采用资格仍按原规则计算。 [负责人确认与本机验证](../../../../openspec/changes/complete-socai2-investigation-chain/alert-attck-mappings-20261123.md#最新分诊与人工判定的展示)

| 路径及精确改动 | 21 基线 SHA-256 | 候选 SHA-256 |
| --- | --- | --- |
| `services/api/app/socai2/page_reader.py`，`@@ -110,7 +110,7 @@`，将读取 ATT&CK 的条件从当前有效改为该 Run 已完成 | `674add39635fe1633786a3b08fcb4cb969206f56cee1d4bd81cddee015a98558` | `4bc37066d723475e8a000d24cfd2be24a043e6b729df6cc3809ce1bdda249533` |
| `services/api/app/socai2/page_contracts.py`，`@@ -117,7 +117,7 @@`，更新 `SubjectView.triage` 描述 | `af25016c086b83619b9c6f102651a66a794111725ddd835991a1b997d71a51af` | `ee1cb3a4d1c6f95a60a8975b82e5d43587d6cb7378ae7806f98042f1fac79fe1` |

补丁为 `.local/validation/alert-git-21-release-20261125-01/http-attck-readback-candidate.patch`，SHA-256 为 `7e86c9d4a2e0aaf05e61fe28dce3b0908a26dc9c1ce7dba83e401302381e6dea`。两文件补丁已在独立临时目录按在运基线检查及应用，结果逐文件匹配并通过 Python 编译。仅加这两处变更所得 751 文件的总 SHA-256 为 `ac9f488175226d0b2e4d19cad870899e5d50b652e94b71e60f42fda0fc7571f4`。统筹已审两处补丁并确认按本批授权执行。21 已完成窄切换及工程读回。 [发布回执](http-attck-release-result.json)

## 当前配置与已有直接测试

Q04 依赖实际 `SOCAI2_OWNER_DIRECTORY_PROFILE_FILE` 指向绝对路径的只读配置。21 使用 `/run/c173-release/config/owner-directory.json`，文件结构只有 `tenant_id` 与非空 `user_ids`。同一租户的候选人由既有 `public.users` 中 `is_active=false` 的 SpiritHub 投影供给，使用相同平台 UUID 和 `preferences.socai2_owner_projection`。实际配置与投影由现有环境提供。样例只含结构及占位 UUID。 [负责人目录配置样例](../../../../deploy/http-service/owner-directory.example.json) · [正式目录与分配读回](../alert-owner-identity-support-20261124-01/verification.json)

保留实际读写连接、`SOCAI2_HTTP_CONTEXT_FILE`、`SOCAI2_CASE_API_ENABLED`、`SOCAI2_PAGE_READ_ENABLED`、`SOCAI2_ANALYSIS_READ_ENABLED` 以及 `SOCAI2_MANAGEMENT_CONFIG_FILE`、`SOCAI2_RUN_RECORDS_CONFIG_FILE`、`SOCAI2_EXPORT_CONFIG_FILE` 的现行绑定。管理通过已有具备 `alerts:write` 的用户身份和写连接保存，目录通过读连接。数据库、租户、人员投影、材料和已存 Run 沿既有环境。 [HTTP 配置](../../../../deploy/http-service/CONFIGURATION.md)

| 最小直接测试 | 候选源码和既有实测证据 |
| --- | --- |
| E48–E51 DTO 与真实最后写 | `services/api/tests/test_socai2_alert_management_contracts.py` 完整文件 SHA-256 `d664a276c1df9719d90698af747509c8b2558ae4399065ca783e42dadf565639`。隔离 TCP HTTP 已核旧版本的后一次显式保存、标签替换/清空/省略、无理由分配、批量反馈及 PG/E30。正式 8181 三笔单条、两笔明确选中反馈有独审。 [现行合同和隔离验收](../../../../openspec/changes/complete-socai2-investigation-chain/specs/alert-incident-management/spec.md) · [实际页面收口](../integration-coordination-audit-20261124-01/alert-management-ocsf-step4-closeout.json) |
| E54 可选重复 UUID 及原筛选 | `services/api/tests/test_socai2_list_export.py::test_export_parameters_and_empty_csv_use_dedicated_routes` 告警导出测试增量，完整文件 SHA-256 `ad15dba86bc44e8fa4e09ec1f49079315354c3f040a581f4fe58e777ede684ac`。本机八项记录及 21 已验勾选、重复去重、原排序和缺省 CSV。 [开发及发布证据](../../../../openspec/changes/complete-socai2-investigation-chain/specs/investigation-list-export/spec.md) |
| Q04 和 E30 | Q04 隔离九项覆盖按 ID、查询、分页和范围以及正式读取、原 PATCH 分配和列表/详情。E30 两个小页验证时间倒序、无重复续页和目标归属。 [Q04 实测](../alert-owner-identity-support-20261124-01/verification.json) · [E30 排序及保存](../integration-coordination-audit-20261124-01/alert-management-ocsf-step4-closeout.json) |
| E28/E31、固定 A、Q27 | 复用 HEAD 中 `test_socai2_page_reader.py` 的配对、材料类型、trace 测试，`test_socai2_stage_reader.py` 的固定轮归属和新鲜度，以及 `test_socai2_run_records_pg.py` 的目录覆盖。 [正式材料及引用](../alert-detail-material-support-20261124-01/verification.json) · [固定 A 读取](../f03-03-alert-triage-run-20261124-01/verification.json) · [Q27 同轮页面](../alert-query-skipped-display-20261125-01/independent-review.json) |
| 已失效分诊的同轮 ATT&CK | `services/api/tests/test_socai2_alert_basic_executor.py` 中 `test_alert_attck_mappings_saved_and_read_for_current_material` 的三个断言，完整文件 SHA-256 `dbdcca010f1cefe2a8d83d04c71d056138d015a2b448202c92088d8f4a33dd9a`。隔离 PG 和 HTTP 的现有回归及 9 项直接读回已验。页面 14 项及 TypeScript 已验。模型使用受控替身。 [存取和页面证据](../../../../openspec/changes/complete-socai2-investigation-chain/alert-attck-mappings-20261123.md#最新分诊与人工判定的展示) |

旧通用 `deploy/http-service/verify_subject_management.py` 同时写入事件和 Case，告警分支仍提交批量标签并断言旧版本 409。本批沿上表的限定证据。该脚本的当前工作区差异属于事件分支。当前广域 `test_socai2_http_boundary.py` 的工作区差异对应湖查询及事件/Case 风险口径。两者均不在这次告警候选。 

## 21 单服务切换方案

1. 以已验证在运的 `c173-alert-management-20261124-01` 镜像和完整应用清单为底。离线替换两文件，复核前后指纹、完整清单和 OpenAPI 的 83 个业务操作。预期合同差异为发行号及 `SubjectView.triage` 的描述。`IncidentSubjectView` 从同一字段继承该描述。保留在运只读配置和其实际内容，尤其 Q04 目录、运行上下文、数据库读写、任务和 Run 配置。按在运端口、用户、网络、启动参数和安全配置准备候选。
2. 候选离线检查通过后仅切换调查 HTTP 18024。原 HTTP 容器、镜像、挂载及日志保留为回退点，候选使用独立日志目录。Swagger、平台、分析调度、Fusion 和数据库维持原运行版本。
3. 切换后核 `/readyz`、在线 OpenAPI、两文件及配置挂载指纹。Q04 只取 HTTP 状态。业务存取沿前述既有证据，本批工程发布命令不采集业务响应体。读回失败恢复上一 HTTP 容器。
