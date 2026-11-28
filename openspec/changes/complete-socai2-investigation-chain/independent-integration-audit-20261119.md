# 调查模块独立接入与交付审计

审计日期：2026-11-19。范围：前后端联调、SpiritHub 消息接入、真实数据进入调查的路径、字段缺口和后续顺序。审计未参与被审代码的实现。审计完成后，按负责人最新批注补核 21 现场，并新增独立只读类型盘点工具；后续工具实现不属于本报告对既有系统的独立审计结论。不修改业务代码、不投递日志、不派发模型、不发布核心服务、不提交或推送，也不将本报告作为主调查或流式 change 的结束验收。

## 1. 结论与证据边界

**已有可运行的调查核心和独立 HTTP，但尚不具备“这批 SpiritHub 日志持续进入、全量可靠落湖、按约定选择告警、由产品页面完成调查闭环”的完整交付。** 消息转发、单条告警验证、历史测试链、工作台展示分别有既有证据；它们不能互相替代。

本轮首先核对实际工作树：分支 `V1.1`，已有大量未提交修改，均保留。结论以 **2026-11-19 的 21 实际运行版本、现场 OpenAPI 和已核源码指纹**为当前基线；本地最新未发布修改及目标设计单列。18024 与 18080 均为 `acceptance-http-20261117-r1`，80 个操作的业务合同一致（Swagger 仅重标展示 tags），与仓库发布合同一致。SpiritHub 现场有 85 个操作，包含 79 个通用桥接和 6 个本地业务入口。源码指纹见[来源清单](../../../docs/operations/evidence/investigation-integration-audit-20261119-01/source-manifest.json)，不能用单独一个 HEAD 代替本次审计状态。

| 证据层级 | 本轮处理与限制 |
| --- | --- |
| 当前源码、Schema、配置文件 | 逐项核消息信封、分类、湖写入、查询、接口装配、字段生产及前端接线 |
| 既有发布与联验记录 | 保留原批次结论，仅引用其适用范围；不重新读取真实日志、业务快照或模型原答来评价业务质量 |
| 本轮离线检查 | 39 项 Fusion 信封/湖写入检查、10 项可信 HTTP/Case 提交检查通过；7 项合成结构探针复现本文指出的边界。见[检查回执](../../../docs/operations/evidence/investigation-integration-audit-20261119-01/structural-checks.json) |
| 本轮 21 现场复核 | 已经 `ssh -J sting-win57 sting-infra21-direct` 连通；正式核心/HTTP、r9 工作台及 OCSF 转发器在运行，配置、OpenAPI 和关键源码已读回。旧 2221 转发规则存在但未监听；先前失败保留。见[现场回执](../../../docs/operations/evidence/investigation-integration-audit-20261119-01/README.md) |
| 真实数据与模型 | 审计不读取业务记录或模型正文；后续类型盘点仅由 21 内程序读取固定 Kafka 范围并保存私有统计，不写业务库、不 commit、不触发调查或模型。业务值及统计报告不进入 Codex/GPT；不是落湖/模型验收 |

两个相关 change 的 strict 校验通过，仅说明规格结构合法。49 项既有检查和 7 项探针也不代表生产整链或模型质量通过。

## 2. 消息接入：对方直写指定 Topic，我方负责全量落湖

**按负责人最新方向：后续由 SpiritHub 自行发送到我方指定 Apache Kafka Topic，所有进入该 Topic 的日志由我方存入 ClickHouse。** 当前实时接收 Topic 沿用 `socai2.spirithub.events-ocsf-v1`；对方直写是交接要求，尚未切换，现有 Vector 过渡转发继续有效。对方交付裸 OCSF 及稳定来源身份，我方维护内部信封、后台租户绑定、湖投影及告警适配；不要求对方改写为内部 RawAlert。双方须先约定直写切换及去重，避免两路重复输入。

既有[接入记录](spirithub-integration-check-20261118.md)明确，上次持续转发只交付 Topic 和查看入口；单条告警采用过一次性信封转换，未交付整批持续进入调查的适配器。OpenSearch 副本是查看/检索副本，当前 Case 取证代码查询的是 ClickHouse。

| 层次 | 已有合同或路径 | 本轮判断 |
| --- | --- | --- |
| SpiritHub 正常清洗输出 | Redpanda `events-ocsf-v1`，根对象直接是 OCSF，`metadata.version=1.9.0` | 这是上游 OCSF 合同，不是 socai2 入站信封 |
| 持续跨集群转发 | Apache Kafka `socai2.spirithub.events-ocsf-v1` | Vector 使用 bytes 解码、raw_message 编码，保持 Key/正文；不会自动补租户、包装信封或选择告警 |
| 整批历史测试输出 | `socai2.spirithub.events-ocsf-v1.replay-20261118` | 与实时转发 Topic 分开，不能把历史整批已交付当成实时消费已接通 |
| socai2 湖入口 | 发布配置基线为 `socai2.raw_events.v1` | `validate_raw_event` 要求对象型 `ocsf_event`，并要求可解析为 UUID 的 `tenant_id` 或 `ocsf_event.tenant_uid`；直接发送裸 OCSF 不符合合同 |
| socai2 告警入口 | 发布配置基线为 `socai2.alerts.raw`，`RawAlert` | 需要稳定来源身份、source、title、severity、原件和来源关联；并非把全部日志换 Topic 就能得到合法告警 |
| 当前正式分类开关基线 | 湖写入启用；通用 promotion、native detection、windowed detection 关闭 | 与本仓库“承接已有安全告警”范围一致。不得通过开启通用检测来替代 SpiritHub 告警接入 |

配置依据为[转发配置](../../../deploy/aisoc21/spirithub-ocsf-forward/forward.toml)、[继承的 Fusion 发布配置](../../../deploy/aisoc21/streaming-release-20261116-02/fusion-env.json)与[本次正式 release](../../../deploy/aisoc21/acceptance-release-20261117-01/release.json)的 `prior_runtime_root`；现场环境与挂载配置指纹已核：正式 Fusion 消费 `socai2.raw_events.v1`/`socai2.alerts.raw`，尚未订阅指定 SpiritHub Topic；`AISOC_LAKE_WRITER_ENABLED=true`，promotion/native/windowed detection 仍为 false。转发配置与仓库一致。见[运行配置](../../../docs/operations/evidence/investigation-integration-audit-20261119-01/live-runtime.json)。

**双方需要定稿的一份接入表**应覆盖：源/目的集群和 Topic、实时/回放区别、消费组和起始位点、OCSF 与信封各自版本、后台租户/来源映射、`metadata.uid`/`ingest_id`/Kafka Key/告警身份的职责、`raw_ref` 原件关联、发生时间与接收时间、分类政策、partial/unclassified/DLQ 处理，以及谁维护适配服务。具体地址与凭据走配置；不用源 offset 等同目的 offset。

推荐接线：同一受控适配流程将**所有日志**按原件关联落湖；其中符合双方约定的**已有告警**另外生成 `RawAlert/source-v1`，进入 Fusion→A→I→Case。两条输出保留相同来源事件关联，避免既走手工告警又开启 promotion 生成重复告警。

## 3. 先盘点现有类别，再确定日志用途与告警策略

**不依据理论类别推定本批实际分布。** 只读盘点分别覆盖实时与回放 Topic，输出实际 class/category/activity/type、is_alert、partial 及必要字段覆盖；数据不全保留未覆盖边界。下表仅是 Schema 与代码能力，不是对本批真实数据的统计结论。分类结果经受控审核后，逐类决定作为告警、调查上下文还是待适配材料，工具按实际用途逐项扩展。

上游随带的 OCSF 1.9.0 Schema 中，`2003` 为 Compliance Finding，`2004` 为 Detection Finding；官方[Compliance Finding 定义](https://github.com/ocsf/ocsf-schema/blob/main/events/findings/compliance_finding.json)及[Detection Finding 定义](https://schema.ocsf.io/1.4.0/classes/detection_finding)也与此一致。不能把 2003 当成“所有安全告警”的固定编号。

| 数据类别 | 落湖要求 | 告警/调查入口建议 | 已确认的代码边界 |
| --- | --- | --- | --- |
| `2004` 检测发现 | 全部保留 | 结合 `is_alert`、来源活动语义和身份，选择真正的告警 | 不能把更新/关闭类消息无条件当作新告警 |
| `2003` 合规发现 | 全部保留 | 按失败/违规及上游告警语义选择；通过的检查不自动变告警 | 上游存在 `finding(2003, false)`，也存在按结果计算 `is_alert` 的分支 |
| `4001` 网络活动 | 全部保留，可作上下文 | 普通连接不分诊；上游明确 `is_alert=true` 的已有网络告警可以纳入 | 天眼转换路径实际在代码中生成 `4001 + is_alert=true`，只接 2004 会漏这一类 |
| `1007` 进程、`3002` 认证及其他活动 | 全部保留 | 普通日志供取证；是否有独立告警标记按接入表判断 | 类别与是否告警是两件事，不因 class 属于活动类而丢日志 |
| `2001/2002/2005` 等其他 Findings | 全部保留 | 逐类说明是否属于本轮已有告警处理范围 | 不能沿通用代码将整个 2xxx 默认纳入当前交付 |
| `0`、partial、unclassified | 原件及分类缺口必须留存、可检索 | 未完成映射与已知告警身份分别记录，进入明确待适配分支；不能静默丢弃或假造完整分类 | 上游缺必填字段时会把 class 降为 0，并将原分类/专有字段放在 `unmapped.spirithub.classification/partial_fields` |

上表是本轮建议的合同讨论基准，尚未变成运行策略。需由两端按实际清洗器版本确认，程序按字段/配置处理，不按具体主机、厂商样本或正文值写死。

当前通用 `should_promote()` 的逻辑为 `class_uid // 1000 == 2` 或 `severity_id >= 4`，不读 `is_alert`。本轮合成探针分别复现：2003 且 `is_alert=false` 仍会提升；中等级 4001 且 `is_alert=true` 不会提升；嵌套目标分类不改变 class 0 的判定。因此**直接启用现有 promotion 不是合格的接入方案**。源码：[promoter](../../../services/fusion/app/services/promoter.py:198)、[上游信封校验](../../../services/fusion/app/services/event_schema.py:96)。

## 4. “全量落湖、能检索”还有三处实际缺口

### 4.1 Kafka 消费确认与湖持久化没有绑定

[consumer](../../../services/fusion/app/workers/consumer.py:389)接受 `LakeWriter.write_event()` 返回 false 后仍可继续；返回 true 也可能仅进入内存缓冲。消费循环在 `_process_message` 返回后提交 offset。[LakeWriter](../../../services/fusion/app/services/lake_writer.py:469)在 flush 失败时清空本批缓冲并累计 dropped，没有在这一路径保留待落湖材料。

**开关已开启，后续指定 Topic 接入也按默认消费并落湖设计；当前缺口不是再打开开关。** 开关决定是否调用湖写入，持久确认决定什么时候可以提交消费位点，两者不同。这意味着 lag=0、入站处理成功或有告警，均不能证明所有日志已经落湖。若本轮验收目标是“所有日志落湖”，这是直接功能阻断。后续只需补本路径的持久确认/可追溯未落湖状态，并以一次正常批次及一个受控失败检查证明不静默越过缺口；不扩展成通用容灾框架，也不因未知写入结果盲目重复投递。

### 4.2 原件长度与保留位置必须说清

[event_to_row](../../../services/fusion/app/services/lake_writer.py:329)将 `raw_payload` 限为 65,536 bytes、`ocsf_json` 限为 262,144 bytes；超限保存 hash/长度与 preview，不是完整原文。本轮探针复现该行为。

这里的 **preview 指“截断预览”，不是退款**。这是我们代码为了限制单字段保存长度主动做的处理，不是 ClickHouse 自动截断，也不是 Kafka 丢掉后半段。小记录不受影响；超过各自阈值才用带 hash/原始长度的预览对象替换。两列独立处理：即使 raw_payload 被截断，未超限的 ocsf_json 中仍可能保留完整 raw_data；不能仅凭其中一列截断断言整条原件丢失。这里确认的是代码条件缺口，未读取真实内容来宣称本批有多少条触发。

“全部行入湖”和“完整原件留存”必须分别验收。按负责人最新反馈，本步直接复用现有ClickHouse `ocsf_json/raw_payload` String列保存完整内容，不另建文件原件库；原文两列复用，必要公共接入/查询列按[表结构讨论稿](clickhouse-lake-design-20261119.md)补齐。后续移除存储侧主动截断，页面预览独立控制；保存未知OCSF字段不要求逐字段扩列。不能把 preview 叫作全量原件。当前常量也需要在触及此路径时纳入配置；不据此扩展全仓硬编码清理。

### 4.3 可存与可查的字段并未全部对齐

`device.hostname` 是 [OCSF 1.9 标准字段](https://github.com/ocsf/ocsf-schema/blob/v1.9.0/objects/device.json)，`device.name` 是可选的设备别名，两者不应混称。当前湖投影主机名读 `device.name/src_endpoint.hostname`，SpiritHub 的设备转换使用 `device.hostname`；线上湖写入文件与本地审计指纹相同，属于我方投影遗漏。本轮合成探针证明仅有 `device.hostname` 时 `src_hostname` 为空。Case 工具又要求冻结 host 对象，并在 SQL 中精确匹配 `src_hostname`，因此原件存在仍可能没有查询 binding 或查不到相关日志。

负责人提出的“保留原字段、入湖时再复制到可查询列”可行。具体映射必须按事件角色确定优先级：保留 `device.hostname` 原值，设备/主机活动将其投影到主机查询字段；网络活动的 `src_endpoint` 与 `dst_endpoint` 分别代表连接两端，不能无条件用采集设备名覆盖源端点。必要时保留独立 device 查询列，并同步 Case 的 host/IP 绑定。此处登记为后续落湖步骤，尚未修改线上映射。

还需按字段路径检查 `actor.process/process`、`user/actor.user`、源/目的端点、IP 类型与来源、`finding_info/finding`、`policy/rule`、ATT&CK 标签，以及 partial_fields 的留存与可用性。线上已有 source_ip/dest_ip 列，支持合法 IPv4/IPv6，写入 IPv6 类型列时将 IPv4 转换为映射地址；不能把历史的适配待办笼统写成当前“没有 IP 列”。仍需核本批上游字段路径与 Case 的 IP-only 绑定，空/非法 IP 当前使用空地址占位。本轮未读取真实 IP 数据，不宣称实际字段缺失比例。

[Case 湖工具](../../../services/api/app/socai2/baseline_evidence_tools.py:12)线上实际支持三类（已核部署代码常量和 SQL；本地文件还包含未发布改动）：进程 `1007`、网络连接 `4001`、认证 `3002`；检索条件为租户、源主机、类别、冻结时间窗口。它不是任意 OCSF 检索，也不是 OpenSearch 查询。DNS、HTTP、文件、注册表、设备发现等日志即使入湖，也没有对应的通用 C4 工具。应先根据本次数据的业务用途选择必要补充，不一次铺开全部类别。

时间窗口由[可靠告警发生时间及配置前后范围](../../../services/api/app/socai2/case_execution_input.py:35)生成。历史回放应保留原发生时间并验证相应查询窗口；不能把旧日志改成当前时间来“查到”，也不能把自动更新资格的 7 天与日志查询窗口混为一谈。真实网络告警若只有 IP 没有 host，当前主机绑定策略能否取证必须单列验证。

## 5. 前后端接口：需要升级桥接和页面调用两层

对外首先提供最新入口：[21 Swagger](http://192.168.1.21:18080/)、[同版 OpenAPI](http://192.168.1.21:18080/handoff/openapi.json)、[仓库冻结合同](../../../deploy/aisoc21/acceptance-release-20261117-01/contract/openapi.json)和[已补 11-19 现场更正的交接文档](../../../docs/integration/spirithub-18024-handoff-20261118.md)。迁移应同时核方法/路径、请求参数与正文、响应结构、状态码及异步读取方式。本轮没有另造新接口。

### 5.1 已确认的阻断

1. **写请求仍做旧上游身份预检。** SpiritHub `SocBridge.request` 仅对启用 trusted reads 的 GET 跳过 `GET /api/v1/auth/me`；POST/PATCH/PUT 仍走该地址。socai2 独立 HTTP 已改为配置化业务上下文，现场 `auth/me` 返回 404。部署桥接源码指纹与审查版本一致，该问题仍存在；附件模块还直接调用 `identity()`，所以并非所有 GET（例如附件下载）都能只靠 trusted reads 工作。只修前端路径无法打通写操作。沿 SpiritHub 本地登录/业务校验转发获准请求即可，不另开权限专项。
2. **路由清单落后。** 以两端现场 OpenAPI 规范化方法/路径后，80 个上游操作与 SpiritHub 的 85 个入口匹配 61 个，**19 个当前入口未接**；79 个通用桥接中有 **19 个旧代理入口已不在当前上游**。原“缺20个”仅比较通用桥接，漏计了 SpiritHub 自有的 `POST /cases/{id}/attachments`，现已更正。其余 5 个本地附件/响应入口不是上游退役接口，不能误报。见[最新完整对照](../../../docs/operations/evidence/investigation-integration-audit-20261119-01/live-contract-comparison.json)，[早先局部对照](../../../docs/operations/evidence/investigation-integration-audit-20261119-01/contract-comparison.json)仅留作历史方法记录。这是现场 Schema 和部署源码核对，不是逐个业务请求验收。
3. **成功状态和返回结构也要变。** 桥接 `_send/request` 返回解析后正文，当前动态路由返回 JSON，没有保留上游成功状态码；默认 200 不能表达新的 201 建案和 202 受理。桥接合同文件、路由与页面数据类型需同批更新。
4. **旧筛选可能成功但不生效。** 现有告警/事件列表没有对所有未知参数统一拒绝；旧 `handling_statuses/severity_groups` 不能当作新 `handling_status/severity`。前端迁移应以过滤结果而非 HTTP 200 为验收条件。

### 5.2 最小迁移清单

下表省略 `/api/v1/socai2`。

| 场景 | 当前接法 | 联调验收要点 |
| --- | --- | --- |
| 调查目录 | `/runs` → `GET /analysis-runs` | 使用 `run_kind`、`subject_type/subject_id`、带时区的 `time_from/time_to` 和 cursor；统计改读 `statistics` |
| Run 详情和原件 | 目录 `detail_url`；步骤/工件目录及 `content_url` | URL 保留主体信息，只拼一次公共前缀；翻页后完整可达，失败/unknown 无 Result 也能看 |
| 新建 Case | `POST /cases`，201 `CaseAllocationReceipt` | 读 `primary_case_id/receiving_case_id/allocations[].initial_task`；建案会登记首轮，不再 prepare/start |
| 更新调查 | `POST /cases/{case_id}/investigations`，202 | 只提交 `operation_key` 和 `mode=check/rerun`；受理后按 `status_url` 查任务，Run 尚未产生可以为空 |
| 事件诊断 | `POST /incidents/{incident_id}/diagnose`，202 | 同样按异步任务读取，不能等待同步完整诊断响应 |
| 自动告警分诊 | 正常告警入站登记 A 任务 | 旧 `/alerts/{id}/analyze` 已移除；页面不能继续展示可用的旧分析按钮 |
| 筛选、排序与分页 | 当前各列表独立合同 | 状态/严重度枚举、单值筛选、total/filtered_total、游标和时区分别核；不能按旧多选字段透传 |
| 采用、关系、评论/附件、探索 | 当前 adoption-preview、assessments、related-cases、exploration 等 | 有些能力后端已有，桥接未登记；附件 API 仅引用，文件上传/下载仍归业务后端 |
| 人员和资产 | 业务后端现有目录及真实映射 | `/people` 不属于当前调查接口；owner/assignee UUID 必须匹配实际目标上下文 |

租户与记账操作者由 18024 的配置确定，不因去掉 Token 就自动支持按浏览器用户切换租户/操作者。双方应确认当前固定上下文是否符合本次联调，页面不要把服务记账身份冒称每个登录用户；不据此强制恢复旧鉴权或重做角色设计。

直接验收应选一条产品业务路径：登录→筛选并打开告警→创建 Case→轮询 task→读取 Run/Result→保存一项人工管理或反馈→重新 GET。再复用同案验证一次 check 无变化和一次有新材料的后轮。不能只对 OpenAPI 或 4177 验收产品前端。

## 6. 已知字段问题复核：设计存在，实施仍未完成

专门入口已经存在：[字段基准](../../../docs/investigation/subject-field-baseline-20261118.md)、[OpenSpec 定稿及 S1–S7](subject-field-audit-20261118.md)。归属主调查 3.10/3.12/3.23/3.30。本轮不新增平行 change。负责人对本项方向无异议，继续沿既定字段方案推进，不将“方案无异议”写成缺口已修复。

| 问题 | 当前结论 | 后续归属 |
| --- | --- | --- |
| SF01 系统初值、本轮严重程度意见及依据 | Case 创建只写请求 severity，未给时可空；I 当前有效等级为人工覆盖或成员最高。I/C6 独立等级意见及只升不降链尚未实现 | S1–S4；系统初值、本轮意见、当前生效值分别保存 |
| SF02 优先级 | 有 `priority_value/state/source/basis` 及读取；当前创建/分析链没有系统生产，管理请求没有相应写入 | S1–S4；按已确认五档映射并支持人工覆盖/撤销 |
| SF03 事件等级页面映射 | 后端已提供 `derived.severity_effective/severity_source`；现有字段审查登记 4173 导入遗漏 | S4 接线；不可把展示空值解释为后端未返回 |
| SF04 I/Case 结构化业务判定 | 正文及 `supported/uncertain` 已有，独立恶意/正常/误报/待复核业务判定仍缺；人工 classification 不能替代 | **S1–S7 未覆盖全部 SF04**，保留原任务补设计/实施出口 |
| SF05 建议正文展示 | 已有建议存储，阅读入口及正文投影仍有问题 | 不新增模型调用，读原 recommendations；建议与实际响应分开 |
| SF06 当前判断摘要 | 依据/未确定项漏投影、技术结束码进入业务待核区的问题仍登记 | 读取实际采用 Result，正常技术终态留执行详情 |
| SF07 展示模式与计数 | 4173 混合演示/快照/本地状态及 Case 轮数混算问题仍登记 | 模式/来源明确；Case Run 与关联 A/I Run 分开计数；4177 不代替产品页 |
| 任务时间及文件异常日志 | 已有 submitted/start/end/local_end；HTTP 缺 first/last enqueue、attempt enqueue 和 active_step；当前 logging 配置主要输出 stdout | S5/S6，不能笼统说“任务没有时间”或“完全没有日志” |

S1–S7 当前均未勾选。它解决等级、优先级、对应页面接线、任务时间和文件日志，不能顺带核销 SF04–SF07 的其余内容。

应与前端提前沟通的后续兼容点：Case `severity=null` 将不再清空；Incident `severity_override=null` 的撤销理由合同将变化；`severity_source` 将增加来源枚举；新增 risk 明细和优先级修改字段。**这些是已设计的目标，尚非当前线上合同。** 告警冻结合同保持，任何确需调整的告警交接字段仍按既定确认流程。

## 7. 汇总问题及优先级

P1 表示对应联调或“全量落湖→调查”验收的直接阻断；P2 表示需跟进的展示、交付或能力边界，不等于可以伪称已完成。

| 编号 | 级别 | 问题及实际影响 | 责任/入口 |
| --- | --- | --- | --- |
| IA01 | P1 | 转发 Topic 与 socai2 信封/消费入口未形成持续适配，整批日志不会因转发成功自动进入调查 | SpiritHub 负责直写指定 Topic；我方负责全量湖存储/内部适配；主调查 3.7/3.21 |
| IA02 | P1 | 湖写入失败/缓冲与 Kafka commit 脱钩，“全量落湖”无持久确认 | socai2 湖写入路径；3.7/3.21 |
| IA03 | P1 | 分类策略需同时处理 is_alert、活动类型、class 0/partial；通用 promotion 会漏或误纳 | 两端确认表，socai2 配置化适配；3.7/3.21 |
| IA04 | P1 | 主机等字段投影不齐，Case 仅三类主机查询；原件可见不等于实际取证可用 | socai2 映射/取证，SpiritHub 对齐语义；3.7/3.10 |
| IA05 | P1 | 湖中大原件截为 preview，缺完整原件可解析链时不满足完整保留 | socai2 存储接线；3.7/3.12 |
| IA06 | P1 | SpiritHub 写请求及附件身份调用仍依赖退役 auth/me | SpiritHub 桥接；沿 11-18 交接 |
| IA07 | P1 | 新旧路由、201/202、返回结构、过滤参数未同步 | SpiritHub 桥接及前端；socai2 交付同版 Schema |
| IA08 | P1 | SF01/SF02/SF04 是业务产出缺口，不能用 DB 可空或模型待复核豁免 | 主调查字段计划及未覆盖的 SF04 |
| IA09 | P2 | SF03/SF05/SF06/SF07 与任务时间/文件日志影响用户判断和排错 | 主调查 3.12、S4–S6 |
| IA10 | P1（统一交付前） | D5 写侧、正式核心、HTTP 和 r9 工作台发布范围不同；当前总任务与完整交付未收口 | 流式 change 3.2/4.1；已核核心仍为 11-17 r1；统一交付并读回 |
| IA11 | P2（本轮已更正入口） | 已校正主任务页阶段一发布/4177、导航RV12、交接19/19及工作台配置；阶段一旧计划增加适用时点，原批次失败和原始记录保留 | 主调查任务、导航、交接与本报告；不据文档更正核销业务任务 |

本轮新增确认的重点是 IA02、IA05、device.hostname→src_hostname 缺口、is_alert 与 class_uid 不等价、桥接成功状态丢失；其余为已有问题的结构复核和责任归并。尚无现场证据的范围不写成已复现生产事故。

SF03/SF06 的本轮源码复核还可定位到 [4173 导入器](../../../prototypes/security-pages-v2/socai2-recorded-import.js:130)：事件等级仅取 severity_override，采用判断的 basis/unresolved 固定为空。它们是展示/投影问题，不能通过重新生成模型答案修复。

其他保留边界：人工定向分析、手动全案综合、知识后台异步维护已明确后置；Q 对话、真实响应、未接产品/UEBA/身份图来源仍不能声称可用。已有真实知识使用证据不等于清理后的当前知识库已经重新具备材料。历史自然 4h/6h 周期等待未验，也不能用显式 check 冒充。模型正文、引用/归因、时间比较等既有质量问题继续保留 NOT_PASSED，不因本次结构审计关闭或反复采样。

流式 change 已有[限定结构审计](../schedule-streaming-investigation-updates/audit.md)，但[收口范围](../schedule-streaming-investigation-updates/closeout-scope-20261118.md)仍保留本期总项核销、最新写侧统一交付/读回、Git/父项目同步等条件。主调查另有全阶段业务/质量边界，不能用本次审计将两个 change 一并归档。

## 8. 后续推进顺序与每步出口

按负责人最新方向细化到[现有接入阶段计划](spirithub-integration-check-20261118.md#2026-11-19-最新接入方向及本阶段步骤)。现场核对、只读类型盘点及湖结构实施规划已完成；当前工作清单、跨事项责任和下一步统一见[原任务执行视图](tasks.md#当前范围与顺序)，湖3a字段映射、3b迁移及3c裸输入适配/完整保存已验证，3d消费/持久确认也已通过合成隔离链，3e真实固定范围聚合验收也已通过且报告留21，下一步为3f基本查询。下表保留审计问题的处理依赖，不形成另一套任务计数；后续存储、分类、工具及产品接线继续逐步验证，不扩为一次全阶段修改或自动发布。

| 顺序 | 本步交付 | 直接通过条件 | 依赖/归属 |
| --- | --- | --- | --- |
| 1 | 当前版本/合同核对及类型盘点 | 已完成现场核对及只读固定范围盘点、私有保存/读回；对方直写与我方存储责任明确，真实统计留21，类别规则及工具用途尚待确认 | 已完成可复用；盘点不是落湖验收，不提交消费位点 |
| 2 | 接入适配及全量落湖/原件读取 | 直接读取现有Kafka固定范围，复用现有湖列；程序对照实际条数、逻辑身份数及分组内容摘要，失败/未知单列，不人工逐条比正文或新增业务列用于验收。湖端从实存内容计算摘要，核主机/端点/时间投影 | 主调查 3.7/3.21；先解决 IA01/02/05 |
| 3 | 已有告警分类、去重及 A/I 入口 | 从第2步同批材料选择告警/非告警/partial 代表，证明非告警只落湖、选中告警进入 RawAlert/Fusion、A 及 I；原来源身份和材料可读，不制造新检测 | IA03/04；主调查 3.7/3.10/3.21 |
| 4 | 一条真实 Case 取证闭环 | 选择真实告警及其窗口内上下文，Case 首轮实际 C4 查询命中对应记录→C6 保存→业务 HTTP/4177 读回。若材料只有 IP 或只有未支持类别，先补该必要取证路径；查空/未查/失败分别显示 | 依赖第2/3步；不能用 OpenSearch 搜索截图替代 |
| 5 | SpiritHub 产品联调 | 先桥接写请求与路由/状态码，再页面字段/轮询；按第5节的一条正常业务链验证实际保存读回，并复用后轮证据 | IA06/07；可独立准备合同，实施仍分步验收 |
| 6 | 必需字段补齐 | 依 S1→S7 逐步完成系统初值、I/C6意见、人工修改、时间线、任务时间与文件日志；另外承接 SF04–SF07 未覆盖项 | 主调查原字段计划；不把模型质量后置变成功能豁免 |
| 7 | 各 change 收口与统一交付 | 核范围、直接证据、交接和未参与实现者的结束审计；按当批获准范围发布/读回后统一提交推送及父项目引用，最后正常归档 | 流式 3.2/4.1、主调查 4.1/4.2 分别判定 |

真实测试不需要把全批日志逐条送模型。先全部保存并证实可检索，再选能覆盖本次功能的一条业务链及必要增量。批次、真实输入/提示/Schema、工具回执、原答、装配、保存与读回留在受控证据位置；本轮业务正文及类型统计不读取到Codex；只读程序在21内处理并保存盘点报告。若后续确需 Codex/GPT 对正文作判断，应先说明必要字段、用途及目标服务，只使用用户确认的脱敏版本。

## 9. 给前后端团队的沟通提纲

1. 以 18024/18080 同版 80 操作合同为基线，停止用旧 `/runs`、prepare/start、analyze 和 `/auth/me` 对接；提供最新完整对照的 19 个未接入口、19 个退役代理入口，以及请求/响应 Schema；附件登记已有独立入口，同路径仍须核合同。
2. 保留 SpiritHub 本地登录及业务校验，修正获准写请求转发；说明 18024 的固定租户/记账操作者，明确人员目录、资产、附件文件服务的归属。
3. 要求对方自行向我方指定 Kafka Topic 发送 OCSF 1.9.0，交付稳定身份/来源和时间；内部信封由我方负责。先看现有数据盘点，再确认 `is_alert` 与各 class 的对应，尤其网络告警、合规通过/失败以及 partial 降类；不要仅凭“2003/2004”做筛选。
4. 确认全量日志与告警的两条输出、原始记录/告警/来源事件 ID 关系、主机/IP/时间路径、原件保留和失败去向；明确 OpenSearch 副本与调查 ClickHouse 的不同用途。
5. 页面区分业务状态、任务/Run 状态、交付完整性、判定确定性、采用及模型质量；先修现行合同映射，再按已定字段设计统一升级。不能把尚未实施的 risk/优先级目标字段当成当前返回。

本轮交付为现场校准后的审计、最新交接入口、结构回执及分步计划；另行完成只读类型盘点工具和独立批次运行记录。业务缺口仍保留未修复状态，不将盘点、配置开关或接口连通记为整链完成。


类型盘点步骤已完成：5项合成直接检查、21新批次固定范围扫描、私有报告保存与原环境读回通过；前两批失败保留。详见[盘点回执](../../../docs/operations/evidence/investigation-integration-audit-20261119-01/README.md#类型盘点工具审计后的独立实施步骤)。统计值未发送Codex，不冒称已判断本批实际类别分布、已全量落湖或已确定新增工具优先级。


2026-11-19后续方案澄清：对外直写要求已具体到`192.168.1.21:19093`、SSL、目标Topic和CA交付，见[交接要求](../../../docs/integration/spirithub-18024-handoff-20261118.md#日志直写要求我方向-spirithub-提出2026-11-19)。线上湖结构已核：原文两列为String，ReplacingMergeTree，按原事件时间400天TTL。存储方案复用现有列，回放直接读现有Kafka并做计数/身份/分组摘要聚合校验；不另造原件归档，不人工逐条审查正文。本轮仅更新方案与系统元数据证据，尚未修改消费者、数据库或实际执行落湖回放。


负责人随后要求明确ClickHouse表设计并整理当前工作，已形成[表结构与实施规划](clickhouse-lake-design-20261119.md)及[统一工作清单](tasks.md#当前范围与顺序)：线上23.8/48列基线、统一事件版本表、3a定稿14个公共字段（补device_ip）及48旧列映射，候选SQL/合成检查已交付；负责人确认新接入每次入湖400天、重试刷新。新增发现是租户清理也按事件时间，3b已与TTL同步并通过隔离库验证，正式进程未更新；上游metadata.uid是清洗记录身份，告警更新关联尚需对方确认。3c已验证新裸入口完整保存及身份/角色/时间；3d消费/持久确认已在隔离Kafka/原生库验证，3e真实固定范围聚合验收及3f查询/完整原文关联已通过，随后4a规则和同批只读判定报告保存读回已验；生产者身份语义、4b接收存取及正式交付仍待。已执行测试库DDL和原生写入，正式表未变。此前“String可直接保存JSON”不再延伸为“表结构无需设计或补列”；清单整理不核销现有业务缺口。
