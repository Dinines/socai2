# 独立结束审计

审计者：`alert_review_end_audit`，未参与本变更实现。2026-11-13。

## 当前结论

**ACCEPT，可归档。** 本地核心、直接验收、冻结文件、E70文档和本机/21统一发布回执均已独立复核，未发现阻塞本功能的业务缺陷。生产只读回了空候选，未取得生产正例匹配证据，说明已准确保留。本结论不核销 F08-01 的单纯同主机近期展示、AI 对话、页面接线或模型质量。

## 规则与实现

- 三规则取并集：同对象 namespace 的 host 值完全相同且当前材料 detection.tactics 至少一个原字符串相同；或者相同 IP；或者明确合法算法和值相同的 hash。同主机无共同战术不够，同战术无共同主机不够；不根据文件名、技术编号、文字相似或模型判断补匹配。
- 起点和候选均读取 latest_material_id 的对象/战术，SQL 同时限定租户、告警 source_namespace 和对象 namespace，排除起点自身。跨事件/Case 保留原归属。候选的 AlertFacts 原样返回，查询不复制起点判定，也不排除已关闭/已有误报判定的记录。
- 默认窗口由独立文件的30天配置和起点 event_time 计算，前闭后开；显式窗口可包含起点之后记录并标为 explicit。未知起点时间无显式窗返回422，候选未知时间被窗口排除，不用入库时间代替。
- SQL 按告警去重后统计和分页，event_time/UUID 均倒序。游标绑定实际种子、战术、材料和窗口；范围/源材料变化409，格式无效422。单次事务为 REPEATABLE READ READ ONLY，跨请求不承诺冻结候选集合。
- 外部路由只通过独立 contracts/dependencies/ports 调用核心；核心未依赖外部HTTP，没有数据库修改、模型调用或调查调度。适配器只沿已有页面读取开关，不依赖 Case 写入能力。

## 独立复核的证据

证据目录：[alert-review-20261113-01](../../../../docs/operations/evidence/alert-review-20261113-01/)。

- 复算 `verify-http.json`：23次全部为GET，13次200、1次404、2次409、7次422。第一完整窗口仅命中 multi、ip、hash、boundary 四条；顺序符合事件时间倒序及相同时间UUID倒序，默认总数4。原 source/namespace/旧材料/仅主机/仅战术/非法hash/文件名等反例均未混入。
- `sql-before.json` 与 `sql-after.json` 的10表原行完全相等：alerts、alert_materials、alert_objects、alert_assessments、incident_alerts、incidents、case_alerts、cases、runs、results。后两次HTTP前的合成源材料指针变化是测试夹具操作，不纳入“前后只读不变”声明；它用于验证旧游标409及新材料空候选。
- 另对回执中19个匹配对象对逐项比对原数据库快照的对象/告警/材料ID、namespace、类型、对象键、字段路径、原值、规范值和latest_material关联。2组重复出现的共享战术逐数组索引回查原 detection.tactics；标签及双方路径相符。hash值及算法长度由审计脚本独立核对。
- 10个补丁文件的当前源码、冻结目录 `/private/tmp/socai2-http-runtime/alert-review-20261113-r1` 和 `frozen-files.json` hash一致。`contract-check.json` 记录旧69操作/145运行schema保持、新增1操作/5schema。
- 审计者另执行本 change 的 OpenSpec 严格校验和现有 HTTP 边界3项测试，均通过；未重跑全仓或新模型、未写业务数据。
- 首次验收脚本误用不存在的 AlertFeedback 模型，在任何HTTP前停止；更正为 AlertAssessments 后沿原独立批次验证，失败说明已保留。该错误不冒充业务接口失败或业务验证成功。

## 收口条件

- 已复阅 [E70指南](../../../../docs/integration/alert-review-http.md)及 `.local/api-docs/alert-review-preview`：E70归告警，输入仅alert_id、time_from、time_to、limit、cursor；5个新schema的27个字段均有对应含义。成功示例的对象/材料/告警ID、战术路径、30天窗口及86400秒差一致，11个E70响应示例由审计者另用JSON Schema校验通过。旧判定不复制、显式时间窗可包含起点之后、F08-01单纯同主机最近7条未完成均准确说明。
- 首次复阅发现指南承诺空态示例但E70的200只有contract例，主代理已补 `empty`。审计者确认 items=[]、total=0、next_cursor=null 且 scope保留；最终docs-check记录27请求/628响应JSON及3CSV通过。该修正只影响静态文档。
- 冻结候选实际读回8次GET均200，实际70操作，candidate_total=3；起点告警两次完整返回相等。该结果对应本轮合成数据、0写入/0模型，不冒充生产验收。
- 两端发布与静态包一致性已按下节复核；0模型和0生产业务写入边界保持。最终回执齐全，归档操作及归档后链接/严格校验由主代理完成。

## 发布后独立复核

- API为 `alert-review-20261113-r1`，本机后缀`-local`、PID42000；21镜像为`sha256:16d00e1910a1b069c512814ec61a520d178f56622708e45c4a61563de848b2be`。两端读回的OpenAPI均实际包含70操作。
- `local-loaded-files.json`、`21-loaded-files.json` 与 `frozen-files.json` 的10文件hash完全相同；审计者另逐文件计算当前仓库源码及正式本机运行目录，均与回执一致。本次仅复核本轮叠加文件，不把并行模型源码纳入已发布范围。
- 正式本机8次GET均200，命中3条并读取候选/材料；21既有记录5次GET均200，命中0条。两端都按实际源告警ID定位前后两次完整告警返回，逐值相等。审计初次辅助脚本把本机候选详情也计入源告警集合，断言停止；改为按回执的source_alert_id精确筛选后复算通过，没有重新请求业务服务或改变数据。
- 21的证据仅证明已发布、默认窗口空态和起点保持，不能证明生产正例匹配。`delivery-summary.json`、证据README、validation及交接指南明确保留该限制；本机独立合成正例/反例验证仍适用于程序规则，不冒充真实模型准确率。
- Swagger `2026-11-13.docs17` 的两端13个HTTP入口回执逐项一致且均200；37文件manifest与当前仓库生成包、正式本机冻结目录逐项hash相等，各HTTP内容hash也与manifest一致。聚合 `deploy/api-docs/deployment-receipt.json` 已指向本批，OpenAPI SHA为`d1bf79a7986bd5b6c717b29b85a3d05c72c3b8d2243177d13b4d8a921c6bd110`。
- 文档保持70操作/68实现/2对话暂缓，159文档schema、752固定输出字段，125功能分组22/15/88；27请求、628响应JSON及3CSV示例回执齐全。E70成功和空页示例、默认窗口、来源路径和错误对齐；F03-05已完成，单纯同主机近期展示仍保留未完成。
- `other-containers.json`记录除本轮API/Swagger外36个21容器未改变；`preview-stop.json`记录临时18026停止且端口关闭，正式服务保留。0生产业务写入、0模型调用、无迁移或消费者变更。此次审计未再发送业务请求、未写业务数据、未提交或推送Git。

## 归档回执

主代理已执行 `openspec archive query-alert-review-candidates --yes`，归档至本目录，新增主规格 `alert-review-candidates` 的2条要求。归档后已更新主规格Purpose、当前入口与相对链接；`openspec validate --all --strict --no-interactive` 为35/35通过，`--archived --strict --no-interactive` 为34/34通过。归档只整理规格和记录，未再次发布或改变业务数据。
