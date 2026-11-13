# 独立结束审计

## 代码与本机验收范围（2026-11-13）

审计者：`subject_management_audit`，未参与本change实现。本轮只读审查实现、规格、测试、候选和已有回执，并运行必要离线检查；没有执行本批PG/TCP写入、模型或部署。按主执行者授权，仅写本审计文件。

**代码与本机直接验收限定通过，当前未发现代码阻断。** 功能／Swagger交接文档尚在同步，发布尚未发生；本节不替代文档终审或发布后核对，不据此提前完成任务1.5／1.6或归档。

- 范围：三类既有列表的筛选、排序和续页，仍为E02／E26／E27；告警／事件只增加获准的`filtered_total`、`next_cursor`封套字段。检查`list_query*.py`、两类合同／reader、外部HTTP合同／错误和两个列表路由，以及直接验收脚本。不将并行模型修改或完整调查质量未完项纳入本次完成判断。
- 筛选：标题／UUID、字面`%`／`_`、等级、状态、负责人、分配状态按真实字段查询；Case原metric／classification路径保持。带时区时间归一到UTC，使用`[from,to)`且起点必须小于终点。事件起止条件位于同一个成员告警的EXISTS子查询，不以两个不同成员分别满足边界；未知发生时间不由入库时间补齐。
- 事件等级与排序：人工覆盖优先，未覆盖时采用成员最大等级；严重度按既有info至critical等级序，时间及等级空值均排最后，同值由同方向UUID决定。游标保存实际排序值及ID，seek条件与升／降序和空值尾部一致；绑定租户、主体、筛选和排序，limit不改变筛选指纹。
- 兼容与统计：旧Case默认查询继续使用v1结构及原指纹，新增日期／排序字段未混入旧指纹；旧`before_id`在无新增条件时继续适用，混用新筛选／排序／cursor返回422。告警／事件`total`和`overall_stats`保持全租户口径，`filtered_total`在游标之前计算；Case的筛选total及全局metrics保留。行字段、详情DTO、数据库表和模型调用未改变。
- 边界：查询条件验证及HTTP错误转换归外部包，SQL选择和游标规则归调查核心；路由没有Session／SQL／模型调用，核心没有新增对外HTTP反向依赖。读取继续使用现有只读快照；`_list_sort_value`不进入对外交接行字段。
- 离线复验：独立运行`test_socai2_list_query.py`、`test_socai2_case_queue.py`、`test_socai2_page_reader.py`及`test_socai2_http_boundary.py`，共15项通过；OpenSpec strict校验通过。合同检查允许的差异只有三个列表新增参数和SubjectPage两键，其他路径、请求／响应和组件合同保持。
- 真实本机证据：[local-http-02/verification.json](../../../../docs/operations/evidence/list-query-20261113-01/local-http-02/verification.json)与原始响应共117次GET，98次200、19次预期422；其中111次访问候选18026，6次访问原18024作兼容对照。9种排序、双向逐页、同值／空值、筛选和变更条件拒绝、旧before_id及旧Case v1均由实际PG/TCP验证。审计未重派该批次。
- 数据保持：独立比较`local-http-02/sql-before.json`与`sql-after.json`，8告警、6事件、6Case、7关联逐值相同；快照摘要为`78284f9e37624b9cda88b1e5bb35dc54cc5e9016d75910e2acb0da8aad8d2665`。原[日期倒置500失败](../../../../docs/operations/evidence/list-query-20261113-01/local-http/failure.json)保留，修正为不将datetime输入放入HTTP校验错误正文；当前三类非法日期离线检查及新批真实响应均为JSON 422。
- 发布范围：[source-manifest.json](../../../../docs/operations/evidence/list-query-20261113-01/source-manifest.json)的10个文件与当前源码及普通项目目录中的冻结候选逐项匹配，且恰为`list-query/aisoc21.json`列出的10文件。基底为已发布`http-boundary`镜像，不混入并行模型变更。正式运行服务和文档发布仍需后续证据。

## 后续限定复核

1. 功能清单、Swagger参数／示例／错误与交接说明完成后，核对实现状态、旧参数兼容和两个封套字段的实际含义。
2. 按本批授权发布后，核对实际服务版本、10文件／配置来源、列表合同与只读业务结果、Swagger实际内容；保留未执行及未通过范围。
3. 以上完成后补本文件最终结论，再完成change的发布收口和归档。

## 文档候选与发布前复核（2026-11-13）

**发布前限定通过，无剩余实现或交接文档阻断，可以进入本批已授权的统一发布。** 这不表示两端服务或Swagger已经替换；发布后实际版本、只读结果及文档读回仍须复核，不能提前归档。

- 复阅三列表功能清单、业务数据交接、接口字段审计和`/private/tmp/socai2-docs8-preview`静态候选。E02／E26／E27的用途、可选参数、输入输出及当前实现状态与已验收代码一致；既有125项功能、53个操作及告警／事件／调查分类保持，不增加数据库字段或页面实现声明。
- 总数和续页已明确：告警／事件使用`filtered_total`显示筛选结果数，`next_cursor`续页，`total/overall_stats`仍为整体；Case的`total`仍为筛选总数、`metrics`仍为整体。F01-04原先仅写`total/next_before_id`的遗漏已经修正；旧`before_id`仅用于无新增条件的调用。功能清单批次范围已经改为三个列表，未实现的CSV完整导出、统一归并统计和偏好持久化保留。
- 时间、排序及兼容说明与实现一致：事件须同一成员告警满足区间，Case日期按业务更新时间；缺失时间不填入库时间，缺值排最后；非法排序枚举返回422。旧Case v1兼容条件、游标随条件变更失效及每次请求为实时快照均已说明。
- 独立静态复验：53个E编号及顺序保持，三个列表参数的名称、位置、必填及Schema逐项匹配真实候选OpenAPI；补旧`before_id`不存在时的404后，共448个成功／错误响应示例通过JSON Schema校验。E02的403示例已改为读取权限拒绝，E26／E27已列`page_subject_not_found`，没有据此增加权限专项实现或测试。该验证只说明合成示例与合同一致，不替代真实请求证据。
- docs8保持127种类型、542个固定字段出现位置；源OpenAPI摘要为`618171641f6fb3dd454bb45ac3fda2e677b32994887dfdb22deb50f0b43b1699`。候选中预备的目标服务版本说明只在本批实际发布成功后交付为当前状态，最终以发布回执为准。

后续只需按本批范围完成两端18024、docs8发布与只读复核；不要求重复本机PG写入、真实模型或扩大测试矩阵。

## 发布后限定结束审计（2026-11-13）

**本change限定通过，无剩余收口或归档阻断。** 直接验收、交接、独立审计及两端发布读回均有相应证据，可完成任务1.6、更新交付摘要并归档。本批没有Git提交／推送或父项目引用更新，不将服务发布表述为源码已同步远端。

本轮仍只读取源码、配置及已有回执；没有发起新的HTTP／数据库／模型请求，没有重跑样本或参与部署。审计范围限三类列表查询，不核销完整调查模型质量、页面接线、自动消费或后续接口工作。

- **版本及范围一致。** [生产发布](../../../../docs/operations/evidence/list-query-20261113-01/21-api-release.json)实际镜像为`sha256:bf0b7beb96d72b25bc92e31da4eae631e93dddc6fce9aaed0954779dd2275bbd`，服务`list-query-20261113-r1`；[本机发布](../../../../docs/operations/evidence/list-query-20261113-01/local-api-release.json)为`list-query-20261113-r1-local`，入口同为`investigation_http.main:app`。根profile与本批profile逐值一致。独立比较当前源码、普通项目目录冻结源、候选包manifest、21发布overlay及两端runtime回执，10个覆盖文件摘要逐项相同；候选Dockerfile只COPY这10文件，基底为前批已发布HTTP边界版本，未带入并行模型修改。
- **实际读取与SQL相符。** 对[21原始响应](../../../../docs/operations/evidence/list-query-20261113-01/21-http/responses.json)的50次GET和[本机正式入口原始响应](../../../../docs/operations/evidence/list-query-20261113-01/local-release-http/responses.json)的30次GET，独立离线按SQL快照重新计算筛选命中、有效等级、同成员日期、排序及游标续页，逐页身份、总数、整体统计和主要事实字段相符。21为44次200／6次预期422，本机为24次200／6次预期422；错误均为非法游标或倒置日期。该离线核对没有再调用服务。
- **数据及环境保持。** `21-sql-before.json`和`21-sql-after.json`逐值相同，包含原有3告警、3事件、1Case和3成员关系，reader／writer实际均连接`aisoc`。本机`local-sql-after.json.rows`与已验收`local-http-02/sql-after.json`完全一致，为8告警、6事件、6Case及7关系，实际目标`v12_upgrade_dev`。生产只读复用既有合成记录，没有新建生产测试主体；本批无迁移、模型调用或Run启动。[runtime回执](../../../../docs/operations/evidence/list-query-20261113-01/21-runtime.json)及其只读采集脚本按容器ID／镜像／启动时间核对其余36个容器保持；本机18026候选已停止，正式18024健康。
- **Swagger内容一致。** 两端各9个入口返回200且完整响应摘要一致，运行架构分别为`aarch64`和`x86_64`。其中8个`/handoff/`载荷独立按文件字节校验，与仓库交接包、已审候选和本机冻结挂载完全一致；根入口两端摘要一致。OpenAPI摘要为`df19a6a15bff2b5ef75b0ef655669d20ca254c8cf4ef748bab81aa106bd2784d`，docs8保持53操作、125功能、542固定字段位置及28动态结构；此前448个示例校验结果对应当前包。固定[docs8回执](../../../../deploy/api-docs/receipts/20261113-docs8.json)与当前发布回执逐值相同。
- **交接范围准确。** 根README、交接指南、当前进度、部署说明、业务数据说明和实施计划已按两端实际版本更新；搜索已实现、完整导出等后续缺口分别说明，未宣称并行模型已部署或正文质量通过。原日期500和种子失败证据保留。结束前再次运行OpenSpec strict校验通过。

最终结论仅覆盖已确认的列表参数及两个HTTP封套字段增量；原行字段、表结构、整体统计口径和旧调用兼容保持。交付摘要的发布后审计状态与归档路径由主执行者据本结论收口，不需要新增业务测试或重复发布。

## 归档封后检查（主执行者）

独立发布后审计通过后完成1.6并运行OpenSpec archive，归档为2026-11-13-query-investigation-lists。新主规格Purpose已写明业务目的；all/archived strict校验均通过，归档内相对链接核对无断链。此段仅记录主执行者的归档检查，不改写上方独立审计。Git提交与推送未执行；并行模型工作保持。
