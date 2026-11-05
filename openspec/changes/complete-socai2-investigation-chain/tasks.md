# 当前任务

当前开发与验证状态见[执行记录](execution.md)、[当前执行账本](../../../docs/investigation/current-execution-ledger.md)和[审计与修复](../../../docs/investigation/current-investigation-audit-20261105.md)。本轮修复输入新鲜度、确定Schema拒绝、SHA256投影和C2来源选择；C6装配恢复，但三份冻结样本计入前序用量后仍无足够额度派发最终模型。独立服务尚未同步本次修改，真实C→H→第二C及双模型整链未验收，不勾选3.7/4.1/4.2。

125仅增加/替换数据库函数，29表459列保持；只应用于既有隔离验证库。没有修改原服务配置、页面或真实历史记录，没有增加预算、调度器或记忆库。

## 承接已有实现

- [x] 1.1 将后台、最新设计和预览迁入主目录开发分支，核对迁移文件与备份，注销本任务旧工作树；见execution.md。
- [x] 1.2 保留29表458列物理合同及独立PG验证；见docs/design/socai2-schema-implementation-20261103.md和docs/operations/socai2-contract-final-20261103.json。
- [x] 1.3 保留C存储、C1–C6统一手动执行与Case HTTP/读取；见docs/operations/socai2-baseline-executor-20261103.json、socai2-case-api-20261104.json及其分阶段回执。
- [x] 1.4 保留Fusion新表writer/Case桥接与A/I冻结、结果发布、新鲜度及读取；见docs/operations/socai2-fusion-ingestion-20261104.json、socai2-stage-results-20261104.json、socai2-stage-reader-20261104.json。

## AI问答仅预留接口

- [x] 2.1 添加发送、保存答复和明确采用的最小类型/HTTP入口，统一501，沿用认证、写权限及默认关闭开关；不接Q业务。见docs/investigation/socai2-case-ai-reserved-20261104.md。
- [x] 2.2 直接验证占位响应、权限/开关、请求边界与无业务执行，导出对应OpenAPI合同；3个ASGI检查通过，详见execution.md。
- [x] 2.3 同步主设计/任务范围、执行记录并通过本change的strict校验；CLI有效不代表功能完成，后续任务保持未勾选。

## 服务端字段与流程接线

- [x] 3.1 实现A告警基本查询/分诊执行适配，保存实际请求、返回、步骤、用量和同次解释；复用已有冻结/发布服务。9新+5回归最新通过，见docs/investigation/socai2-alert-basic-executor-20261104.md及对应回执；内部入口已接，生产消费者未切换。
- [x] 3.2 实现I事件诊断执行适配，消费明确成员与同次有效分诊，保存诊断/未决及来源，不将归并摘要当诊断。9新+5回归首次通过，见docs/investigation/socai2-incident-diagnosis-executor-20261104.md及对应5批回执；内部入口已接，生产未切换。
- [x] 3.3 完善告警/事件页面字段DTO逐项对照，包括身份、时间、状态/判定、独立事件事实、来源与已定派生口径；页面功能由其他负责人实现。73项明细及8个GET模板见docs/investigation/socai2-page-reader-20261104.md；8新+2PG回归、3个Q接口回归最新通过，默认关闭。响应实时状态等外部来源保持明确待接，不宣称页面功能/生产完成。
- [x] 3.4 接通显式事件Case关联和移动事务，保持租户、已有来源身份命名空间、成员范围版本及历史来源一致。12新+7PG回归最新通过，详见docs/investigation/socai2-case-relations-20261104.md；124仅给Case补固定source_namespace，当前29表459列。Fusion未提供独立来源环境，不能用fusion.v1/connector冒充；按已定输入限制记录，不宣称环境已核实。生产与页面未切换。
- [x] 3.5 实现H人工任务/结果写读与引用冻结，区分完成/修改事实、范围及来源；新增用户显式baseline/prepare补齐成员不变时H→下一轮C入口，保存H不自动生成Run。10项H+5项prepare+6项C1/model-view回归首过，见docs/investigation/socai2-human-tasks-20261104.md及固定汇总；无DDL/预算/页面修改，旧Run不回算。
- [x] 3.6 按实际来源接通产品主机/认证、UEBA/知识和外部身份图必要字段，缺源/空结果/失败/不确定分开；模型角色及范围保留，完整C2从原4次工具预算内留2次给C4、按冻结对象选择前两项来源，其他来源明确预算跳过。12新+2回归最新通过，见docs/investigation/socai2-external-sources-20261104.md及固定汇总；PG读写真实、模型/湖/产品/身份图返回替身，可选来源默认关闭，不宣称供应商实连或完整攻击拓扑已验收。
- [ ] 3.7 按用户最新决定单开独立服务，保原服务/数据/消费者；在现有PG/CH上使用新空间，完成真实身份、合成Fusion材料到A/I/C/H及新一轮C的真实模型/来源质量验收。无旧数据迁移或消费者切换；见acceptance-plan-20261104.md。

## 完成条件

- [ ] 4.1 在实施任务完成后，由未参与实现者做结束审计，实际问题修复并复核；保留未知/失败/暂缓项，不核销旧r13的5.3。
- [ ] 4.2 实施及审计达标后再归档并核对规格；不以CLI通过或已有组件通过提前归档。

Q业务暂缓，不列本change的未完成实现项。旧r13/5.3不随本批核销，完成实施和验收后再进行独立结束审计与归档。
