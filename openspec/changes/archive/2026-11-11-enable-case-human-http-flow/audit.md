# 独立结束审计

审查者：`/root/current_release_audit`，未参与本 change 实现。审查基线为 `V1.1@97953643c20ee543f6e7c9d8d5e050e7eebd849b`，日期 2026-11-11。

**结论：限定 ACCEPT。** 本地 Case/H HTTP 接线、人工版本传递、保存读取及候选发布配置未发现必须修正项，可以进入本 change 的一次统一发布。此结论不表示 21 已更新或生产写读已通过；任务 3.2/3.3、归档和 Git/父项目交付仍须按实际回执完成。模型质量继续 **NOT_PASSED**，M01-A/M01-B、F01 和其他未验范围不核销。

## 实现与发布范围

- [Case 写入连接](../../../../services/api/app/db/case_database.py)只读取显式 `SOCAI2_CASE_DATABASE_URL`，没有缺配置回退；配置为空或无效返回不含原 DSN 的错误。连接池按需建立、同进程复用，变更配置要求重新加载，关闭时释放。
- [Case](../../../../services/api/app/api/v1/endpoints/socai2_cases.py)和[人工任务](../../../../services/api/app/api/v1/endpoints/socai2_tasks.py)的原依赖均为 GET 选择原 `AsyncSessionLocal`、写操作选择新会话。原写开关、认证 actor/tenant、服务事务、请求/响应字段和版本规则沿用；本 change 未改变告警字段或 V1 表列。
- [发布映射](../../../../deploy/aisoc21/release_12.py)只生成清单允许的目标键，当前清单将处理 `DATABASE_URL` 映射为 Case 专用键。通用 `DATABASE_URL` 不在目标键、API 允许变更键或显式覆盖中；已有有效 Compose 的环境优先级由 `processing_environment_overlay` 处理，不依赖 env_file 覆盖旧的显式值。
- 审查期间补齐的 UEBA/knowledge/graph/product-host 四项来源开关及 `SOCAI2_LAKE_DATABASE` 同时进入 `api_model_keys` 和 `allowed_env_changes`，沿用处理 profile 的显式值。依据为 [API 来源配置回执](../../../../docs/operations/evidence/case-human-http-20261111-01/api-source-prerequisite.json)。没有映射其他 API 的 ClickHouse 凭据或连接身份；真实非空湖/知识仍未在本批验证。
- 候选 r2 仅构建、更新 API，处理镜像保持 `processing-20261111-r1`，其余五容器及消费者保持。已有只读 CA 挂载见[连接前提](../../../../docs/operations/evidence/case-human-http-20261111-01/api-connection-prerequisite.json)。新增发布核验在只读事务中核 Case 开关、实际数据库及角色；其结果须发布后取得，不能由静态配置代替。
- [生产核验入口](../../../../tools/testdata/case_human_http/production.py)使用既有账号正常登录，只读原 Case，在独立验收 Case 创建和修订一项材料核查任务并读回；代码没有 Run start 调用，保留 pending Run，遇失败/未知停止并保留回执。凭据经 stdin 传递且登录内容不进入普通回执。此次仅静态审阅，未执行该入口。

## 独立核对的原件事实

审阅 [11 项直接检查回执](../../../../docs/operations/evidence/case-human-http-20261111-01/direct-tests.txt)及相应直接用例，未重新运行测试。另以本地只读 JSON/hash 比较独立核对以下事实，未连接数据库、网络或模型：

1. [原 HTTP 回执](../../../../docs/operations/evidence/case-human-http-20261111-01/real-http/api-responses.json)为 13 次请求，全部 200，顺序包含建案、首轮 start/读取、H 创建/修订/版本读取、显式 prepare、后轮 start/读取。驱动仅替换 `get_current_user` 和模型网关传输 factory；路由、`get_service`、Case/H 服务、执行器及存储未替换。本地实际 reader/writer 分别是 `v12_reader_dev` / `v12_developer`，同属隔离库 `v12_upgrade_dev`。
2. 同一任务的 revision 1、2 原文均与请求配置逐值一致，当前指针为 `fb5d503e-f4b5-4c6a-9684-7fa711d56424`。H 当前 GET 与 PUT 返回的 task 完全相同；当前修订的 id/task_id/case_id/revision/result_text/result_scope/source_refs/state 与落库一致。版本列表与库中两版的公开字段一致，时间仅有等价的 `Z` / `+00:00` 序列化差异，API 按原合同不返回 tenant_id。
3. 首轮冻结 `task_revisions=[]`；后轮仅冻结第二版，并登记 `task_revision/human_statement`。后轮 C3、两份 Deep、C6 的四份实际请求 body 均包含第二版完整正文而不含第一版完整正文；保存的请求 body 与调用 intent 逐值相同。各自 source_map 的 human_statement 引用恢复到原快照后，修订 id、正文和范围均匹配所选第二版，未将人工核查改成业务授权。
4. 两个 Run 均 `completed/partial`。首轮 C6 两个失败步骤仍记录 `delivery_source_not_visible_or_duplicate`，对应 Result 为 `rejected/unavailable`、conclusion=null；后轮 Result 为 `accepted/uncertain`。两份 Result 的 conclusion、conclusion_state、validation_state、findings、questions、recommendations 均与原 GET 逐值一致。结构采用不等于语义质量通过。
5. 原调用回执分别为 5/4 次，reported tokens 独立合计为 71,723/45,452，与交接一致；费用未知。三份演练材料的原字段与冻结计划一致。导出 manifest 所列 database、case-page-data、api-responses 三个文件 hash 均匹配。
6. 执行时冻结的 HTTP 驱动、会话模块、通用数据库模块和两路 endpoint 的 hash 与当前文件一致。`core/config.py` 仅 Ruff 导入换行：重建执行时导入文本后 hash 匹配，AST 完全一致。采用[本地收口回执](../../../../docs/operations/evidence/case-human-http-20261111-01/local-closeout.json)中的定向检查范围，不把既有通用 lint 项作为新增业务失败。

上述原件位于[本批证据目录](../../../../docs/operations/evidence/case-human-http-20261111-01/README.md)，摘要为[保存读取核验](../../../../docs/operations/evidence/case-human-http-20261111-01/real-http/export/verification.json)及[实际请求 body 核验](../../../../docs/operations/evidence/case-human-http-20261111-01/real-http/export/model-input-verification.json)。

## 限制及收口要求

本次仅审当前差异和直接证据，未重跑模型、业务测试、全仓回归、权限矩阵或可用性检查，也未执行部署或 Git 操作。首次离线打印脚本读取 C3 不存在的展示键 `stage` 中断，改用 artifact id 后完成原件比较；未改原证据或业务逻辑，不计业务失败。

本地 ASGI 的认证主体及真实模型 SSH 传输适配已在交接中明示；不能据此声称正常登录、21 的 TenantChatGateway 凭据解析、产品页面或生产新 Run 已验收。发布后计划仅验证正常登录及独立 Case/H 写读，不包含新生产模型调用。M01-A/M01-B、F01 的完整语义质量、非空知识、产品页面和自动消费保持开放；主调查整体任务不能由本次局部接通直接完成。

PROGRESS、根交接、设计/规格/任务、验收及部署说明均区分了当前 r1 与候选 r2、本地已验与生产待验，并保留首轮失败和 NOT_PASSED。发布后补实际版本、连接及来源配置、Case/H 写读、静态记录和未变容器回执，再完成归档前一致性及最终 Git/父项目交付记录。

## 发布后补核（2026-11-11，同一次审计）

**交付补充结论：限定 ACCEPT，未发现新增阻断。** 上述段落保留发布前审计时点；现已只读核对[交付汇总](../../../../docs/operations/evidence/case-human-http-20261111-01/delivery-summary.json)、实际运行、生产 HTTP/落库原件和静态发布回执。r2 的唯一一次 API rollout、activate、verify 均 exit 0；实际 API 镜像匹配目标，六容器健康。逐项比较本批 prepare 的 before_id 与发布后容器 ID，确认五项继承容器保持，只有 API 更新；冻结 manifest 文件 hash 与交付摘要一致。实际 Case 开关为 true，写连接只读身份探针返回 aisoc/socai2_prod_processor；五项来源配置与摘要相符，运行回执确认通用数据库连接保持。

[生产 HTTP 原件](../../../../docs/operations/evidence/case-human-http-20261111-01/production-http/http.json)的 8 次业务请求全部 200，正常登录及主体核对按既有驱动执行，敏感认证响应不保存。独立 Case `9c1b65d3-e7e7-5b99-8bf1-eea8ebd8283c` 的 H 原版与修订版各 8 项公开字段均与[落库快照](../../../../docs/operations/evidence/case-human-http-20261111-01/production-http/database.json)匹配；当前 GET 与 PUT 返回完全一致，当前指针和两版号正确。Run 保持 pending_update、started_at/ended_at 为空、result_ids 为空，Case 当前 assessment 为空；没有 Run 启动或生产模型结果，原 Case 的回执只有 GET。交付汇总中的 production_http 与独立 verification.json 完全一致。

[4177 回执](../../../../docs/operations/evidence/case-human-http-20261111-01/static-publication.json)记录 34→35、143 文件/144 HTTP，原记录及展示源码保持，与汇总和根交接一致。PROGRESS 的 Git 句已明确为归档后的交付规则，不提前宣称远端完成。此次仅比较已保存回执，未新增网络、模型、数据库、部署或测试调用；没有重新验证模型质量或生产新 Run。M01-A/M01-B、F01、非空知识、产品页面和自动消费仍未核销。任务 3.3 的最终链接/冻结一致性检查、归档及 Git/父项目实际远端回执由主流程继续完成，不计入本次已核发布事实。

## 归档与最终交付锚点

主流程已执行 `openspec archive enable-case-human-http-flow --yes`，归档为本目录并向主规格添加 4 项合同。原模型失败和未验范围保持；主调查仍 31/41。发布回执/源码 manifest 与完成状态见 [交付汇总](../../../../docs/operations/evidence/case-human-http-20261111-01/delivery-summary.json)，封后校验另留实际回执。

Git 使用包含本目录及冻结 manifest 的 V1.1 提交，父项目 SpiritHub/add-server-submoudle 的 server 引用应指向该提交；执行顺序为归档、提交/推送子仓库、更新父引用、读回两端。实际 hash 在推送后单独记录，不在当前提交内写自指 hash。

封后严格校验：活动/主规格 16 项通过，归档 11 项通过。首次主规格校验发现 CLI 自动生成的 Purpose 占位句；已补成该能力实际用途，未改变需求，原失败和复验回执分别保留（validate-all.json / validate-all-final.json）。当前链接与冻结源码一致性核验见本批 archive-validation.json。
