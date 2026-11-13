# 独立结束审计

## 本地审计（发布前）

2026-11-13，由未参与本项实现的 `subject_management_audit` 独立只读审阅并复验。

结论：本地代码、直接验收及交接通过，无剩余本地阻断；尚未发布，不能据此完成发布任务或归档。

核对对外包、业务端口、适配层、旧入口/端点转接、配置、候选打包及文档。外部路由不直接使用Session、SQL、模型或消费者；内部HTTP应用未混入。核心可在禁止导入对外HTTP包时正常加载。共享业务合同和运行依赖的范围已说明，未夸大为全部第三方依赖独立。

独立复跑首次34项及18子检查通过，完整OpenAPI逐值保持。首次审计另复现原只读校验的 `configured_database_name` 导入失败，并指出旧独立包生成器遗漏新包；这两项作为真实缺口保留记录，修正后复核通过。

结束复验6项通过：边界3项、原只读校验1项、旧/新包布局冻结和构建替身2项。旧导出与runtime为同一函数；26源码与profile、reviewed tar及source-manifest完全一致。reviewed tar SHA-256：`6c85ee34b80d3394c31d2359e60ad962a40bdac99b4b081a730f5436fa0a4d1b`。

主API `release_12.py` 的freeze/build/image/runtime均逐包处理；现有源配置只增加additional_packages映射，旧独立打包器已收集/COPY新包。标准Dockerfile原本COPY完整服务目录。处理核心不增加对外HTTP依赖。

审计读取24次TCP及实际PG回执，没有重派已结束批次，没有新数据库、模型或真实Docker操作；构建测试中的Docker是替身。线上18024/21/Swagger未因本项切换，临时候选18026验收后已停止。任务1.4可完成，1.5保持未完成。

## 发布后限定审计（2026-11-13）

**限定结束审计通过，无剩余交付阻断；可以完成任务1.5并进入归档。** 本节核对本轮发布回执、保存的HTTP响应、SQL核验记录、配置和冻结源码；审计者没有重新发送数据库／业务HTTP／模型请求，没有重派写入、部署、归档或Git操作。前节“尚未发布”是发布前结论，本节记录其后的实际状态。

- 发布来源：[21构建](../../../../docs/operations/evidence/http-boundary-20261113-01/21-build.json)及[21服务回执](../../../../docs/operations/evidence/http-boundary-20261113-01/21-api-release.json)一致指向`http-boundary-20261113-r1`，镜像`sha256:b9316a414bf8bc1c388f02cf1edf7137f7ff096a9d05d22559f0acc62b045f3c`，18024已就绪且53操作齐全。发布只覆盖原审计的26个HTTP包／兼容文件，其他生产容器保持；主API、处理服务及并行模型代码没有随本项发布。
- 源码与本机运行：[source-manifest.json](../../../../docs/operations/evidence/http-boundary-20261113-01/source-manifest.json)的26个摘要与当前源码、发布覆盖清单及[local-source.json](../../../../docs/operations/evidence/http-boundary-20261113-01/local-source.json)逐项一致。独立读取普通项目目录`../socai2-http-runtime/http-boundary-20261113-r1`的622个文件，全部匹配该冻结清单；来源镜像与21实际发布一致。[本机发布回执](../../../../docs/operations/evidence/http-boundary-20261113-01/local-api-release.json)记录新PID、ARM64原生Python及18024就绪。根local/aisoc21 profiles与本批profiles逐值相同，显式运行新入口；本机连接`v12_upgrade_dev`，21 reader/writer均为`aisoc`。source-manifest中的发布前标记保留为固定候选记录，实际部署状态以本节发布回执为准。
- 本机保存读取：[新批HTTP回执](../../../../docs/operations/evidence/http-boundary-20261113-01/local-release-http/verification.json)与原始responses共9次请求，8次200、1次预期501，覆盖新Case、任务创建／修订、当前／历史版本和pending Run读取；新Case为`704fec1e-7533-57e8-9ea9-b662f38b928f`，未启动Run。任务修改后另取最新Case；[SQL回执](../../../../docs/operations/evidence/http-boundary-20261113-01/local-release-sql.json)确认Case、任务修订及Run保存读取一致。本机实际写入继续与发布前24次TCP及A/I替身证据区分。
- 生产只读验收：[21读回](../../../../docs/operations/evidence/http-boundary-20261113-01/21-readback.json)的12份原始响应均为GET／200。独立对照上一批原始回执，6个告警／事件的全部facts以及Case、任务和Run响应均相同，Run只排除读取时生成的`observed_at`；其余管理条件、任务列表和历史读取成功。[21只读SQL](../../../../docs/operations/evidence/http-boundary-20261113-01/21-readonly-sql.json)核对9个对象并记录实际reader／writer数据库身份。没有将只读结果写成生产写入验收。
- 验证范围变化：[production-validation-scope.json](../../../../docs/operations/evidence/http-boundary-20261113-01/production-validation-scope.json)明确自动审批拒绝正式库新增合成Case／任务的请求，该操作未执行；本轮生产业务写入为0，采用既有记录GET和显式只读SQL。对本次合同及核心行为不变的边界重构，本机真实保存读取、同源发布及生产只读核验支持上述限定通过；不宣称本轮已完成生产写入测试。[读回检查修正](../../../../docs/operations/evidence/http-boundary-20261113-01/readback-check-correction.json)保留动态时间、HistoryPage字段及旧Case快照比较的初次失败原因，未改接口或业务数据追认成功。
- Swagger与文档：[本机](../../../../docs/operations/evidence/http-boundary-20261113-01/local-swagger.json)和[21](../../../../docs/operations/evidence/http-boundary-20261113-01/21-swagger.json)六个入口均200，摘要彼此相同并与上一批docs7完全一致；合同不变，未重启文档容器，实际服务版本以本轮发布回执和交接入口为准。PROGRESS、根交接、架构和部署说明准确区分当前两端版本、旧主API、冻结源码及生产只读范围；审计发现的README第7行旧发布名已修正。

本结论只覆盖`separate-investigation-http`的代码边界、兼容、发布和上述验收范围。内部HTTP原协议与组件调用保持；没有新增表或迁移、恢复自动消费者、调用真实模型或完成列表扩展。`query-investigation-lists`及并行模型质量未完项继续保留。汇总见[delivery-summary.json](../../../../docs/operations/evidence/http-boundary-20261113-01/delivery-summary.json)；该汇总的审计状态由主执行者据本结论回填。

## 归档与封后结构核验（主执行者）

独审通过且任务1.5完成后，执行 `openspec archive separate-investigation-http --yes`，已归档至本目录并建立主规格 `investigation-http-boundary`。归档CLI生成的Purpose占位首次严格校验失败，随后补为本能力用途；最终活动变更及主规格26项通过、归档24项通过。已更新归档相对链接，22个受影响链接无缺失；列表change继续保留未实施状态。此封后核验没有业务代码或运行变更，归档核验阶段尚未执行Git推送。回执见[archive-check.json](../../../../docs/operations/evidence/http-boundary-20261113-01/archive-check.json)。
