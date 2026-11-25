# 告警字段必需性与 Fusion 评分就绪核查

本批记录已验收的规则接收映射、A 置信度提示、单条首次接收与真实 A，以及旧查询跳过原因。整项 change 和未完成的模型质量问题保持各自状态。

## 第 1 步湖接收规则映射

2026-11-25。湖接收 `adapt_alert()` 从同版 `finding_info.analytic.uid/name` 分别填既有 `RawAlert.rule_id/rule_name`。按当前字符串投影解析根及 partial，实际路径保存在 `field_metadata.rule_id_source/rule_name_source`。显式空值保留为空及原路径，缺失字段无来源路径，根与 partial 确有冲突时沿 `projection_field_conflict` 暂留。材料的 `detection.rule_id/rule_name` 继续走现有投影和查询。

接收、快照恢复及材料投影定向测试 **17 项通过**。获准同一原件的本地布尔对照通过，候选规则和两条来源路径可恢复，原件字节、原始置信度、其他检测字段、告警及湖版本身份一致。用已捕获的旧接收数据重建快照并通过连接替身走已提交回执的读取路径，返回原材料 ID 和首次 A 任务。首个本地对照脚本漏传选择策略指纹，纠正测试接线后通过。0 新投递、0 业务写入、0 模型调用。 [源码、指纹及直接验证](../../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/core-verification.json)

第 1 步本地验证结束时，21 镜像及归档运行文件仍为修改前版本，接收映射的部署差异只有 `services/fusion/app/services/lake_alert_receiver.py`。后续已按下文“恢复发布回执”将该文件安装到 21 独立源码目录并核加载。以后获准新首次接收时，独立 `app.workers.lake_alert_delivery` 显式选择该工作目录和 `PYTHONPATH`，沿已批准的启用评分 profile 加载。已存材料的规则可沿同版 E31 原件读取，正式首次接收的保存正例仍待验。

### 已确认的 AI 空值口径

新答复能合理估计本轮判定时给出有限 0–1 数值。完成必要核对后仍因依据不足、证据矛盾或其他该轮明确限制而无法估计时，可以返回显式 `null`，在既有 `rationale` 中说清本轮无法估计的具体原因。`needs_review` 本身仍可给出数值自评，源检测及 Fusion 评分各有独立语义。页面分别显示尚无已发布分诊、该次执行失败及已发布但未评分。历史空值使用原结果未给评分的说明，只有同轮已存理由明确说明未评分原因时才展示该原因。统筹已确认此口径，后续页面说明由前端执行。

## 第 3 步 AI 评分提示与实际加载方案

2026-11-25。第 2 步源检测展示通过统筹独审后，已确认上面的 AI 空值口径，并在中央规格加入对应场景。本步修改 `alert-input-v1.json` 的 `confidence` 提示，让新 A 请求在可合理估计时要求有限 0–1 数值，无法估计时在既有 `rationale` 说明本轮具体原因。需要复核的判定仍可给出自评数值，来源及 Fusion 评分保留各自用途。改动范围是提示及与所选配置加载直接相关的既有测试。

直接验证沿现有请求装配、输出适配和运行策略测试，核实际加载的配置及请求指纹、数字与显式空值兼容，以及输出 Schema、升级门控文件和阈值。测试产物及基线保存于本机受控目录，工程结果保存为本批 `core-ai-null-*` 回执。本步使用本地验证，新的真实模型输出及首次接收保存留待有获准业务输入时验收。

发布准备只读核对 21 实际进程、文件挂载、配置加载与运行任务状态，分别确认湖接收映射和 A 提示应更新的准确文件、入口及重启条件。先交统筹审核最小差异和独立发布目录，批准后按确认范围执行。中央任务、进展和页面说明由对应执行者维护。

### 提示改动和直接验证结果

配置只修改 `system_prompt` 中 `confidence` 的说明。既有请求装配测试改为核所选 profile 的系统提示和保存指纹，原历史 V3 提示留在原件。请求装配、输出适配及所选运行策略共 **13 项通过**。以同一既有测试材料分别装配修改前后 profile，用户材料、来源映射及实际输出 Schema 一致。配置加载通过，原 nullable 合同、升级门控源码和配置阈值指纹核对一致。新提示 SHA-256 为 `563db55ead3aa256ac37ba187b265fb54abc1b70b0cf929c69d1688d0aebd5c6`。

首轮定向测试缺少显式运行策略路径，补齐测试环境后复验通过。只读探针的本地字符串语法已在远端执行前修正。原失败记录保存在本机证据目录。本步新模型调用、业务写入和运行服务变更均为 0。新提示下的真实模型遵循情况待有获准业务输入时核验。 [直接验证回执](../../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/core-ai-null-verification.json)

### 21 加载与限定发布提案

2026-11-25 12:13（Asia/Shanghai）只读核查，唯一在运联合调度为 `socai2-analysis-c173-attck-release-20261123-01`，入口 `app.socai2.analysis_dispatch_runtime --profile /run/c173-release/config/dispatcher.json`，执行器工厂为 `app.socai2.analysis_case_executor:executors`。配置租户范围内未见运行中的 Run、分析尝试、任务或 accepted/waiting 任务。独立湖交付进程未见运行。进程与任务状态是本次观察，实际切换前需再次核对。 [运行只读回执](../../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/core-ai-null-runtime-readonly.json)

| 变更 | 实际加载和精确差异 | 拟发布操作与生效条件 |
| --- | --- | --- |
| 新 A 评分提示 | 联合调度沿 `/run/c173-release/config/investigation-policy.toml` 的 `[alert_io]` 选择，与 `runtime_policy.py` 同目录加载 `/app/app/socai2/alert-input-v1.json`。当前文件为修改前 `cd21c01de15b5143f606af57bea0189fc22acf8b057ef744f58afa9faf475ee3`。 | 审核后把候选单文件放入新发布目录的 `ai/alert-input-v1.json`，在同镜像的新调度容器只读挂载到原加载路径。`active_policy()` 在进程内缓存，需以该挂载替换调度容器，沿实际原启动参数、挂载及配置启动唯一实例。离线加载核所选新指纹与 Schema，再核运行配置及调度状态。 |
| 新首次湖接收的规则 | 独立 `app.workers.lake_alert_delivery` 导入 `app.services.lake_alert_receiver`。已核归档源码根为 `/opt/sting-aisoc-socai2/validation/spirithub-online-alert-20261124-01/fusion`，接收旧指纹为 `3cb72ade674d303541c3abba81dc93287ca141548695a447cc2d78bcb3054471`。 | 审核后从该归档复制独立 `fusion/`，只替换 `app/services/lake_alert_receiver.py` 为已独审的 `29f40cc176576a8fced6a7519a705a5dcca317301b2676150b4ba6e0d11d7c9e`。以后获准新首次接收时，把工作目录及 `PYTHONPATH` 同时显式设为此源码根，选用已安装 `delivery-confidence-enabled.json` 加载。当前入口已退出，安装候选后的直接验证使用离线配置和导入。 |

新发布目录为 `/opt/sting-aisoc-socai2/deployments/alert-rule-source-confidence-20261125-01`。两项候选单文件已在本机 `ai-null/release-payload/` 冻结并保存清单。镜像、挂载目标、配置路径及校验条件详见 [精确发布提案](../../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/core-ai-null-release-plan.json)。统筹已完成 9 项独立核对并批准限定发布。 [独立审查和授权](../../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/independent-core-release-review.json)

### 发布执行阻断

获准发布后，整体准备命令及工具允许的一次重试均在自动权限审核阶段超时。随后按统筹确认的分步安排，单独提交文件安装步骤，仍在 `CreateProcess` 前因同一审核超时被拒。工具说明超时本身不表示操作不安全。三次命令均未创建进程，本轮对 21 的安装、容器创建和切换均为 0，候选仍保存在本机。同步消息也遇到审核超时，统筹随后直接读取本会话并指示保留回执，停止反复提交同一阻断动作。

上轮阻断时未完成的工作为安装两个已批准文件、离线加载、切换前空闲核对、替换唯一分析实例及实际加载和正常调度读回。当时现场观察沿发布尝试前的只读回执，尚无发布后读回。 [上轮发布阻断及执行状态](../../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/core-release-result.json)

### 恢复发布回执

负责人在统筹会话再次明确授权调查核心把规则映射和新提示发布到 21，由统筹核实际加载及页面后独立验收。2026-11-25 12:38（Asia/Shanghai）重新只读确认原调度器、镜像、提示及湖配置仍与已审基线一致，目标目录和候选容器均未创建。沿同一批准清单执行文件安装、离线加载、停止候选创建、空闲核对和单实例切换，12:43 实际运行读回通过。前轮阻断和独审回执保留原结论。 [本次恢复发布回执](../../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/core-release-resume-result.json)

新分析实例为 `socai2-analysis-alert-rule-source-confidence-20261125-01`，沿原镜像 `sha256:3688f5ad8c2c2144abe88ef5ce7c717f20de6a73130c2a40c9d2bf67a297cdf7` 及实际启动配置，增加单个提示文件只读挂载。`/app/app/socai2/alert-input-v1.json` 的实际加载指纹为 `563db55ead3aa256ac37ba187b265fb54abc1b70b0cf929c69d1688d0aebd5c6`。新实例已出现成功的正常调度检查，重启次数为 0。切换前后未见在途、待处理任务或未写回完成回执，发布观察期间未见新模型步骤。旧实例已停止保留，原只读配置和其他在运服务状态核对一致。

规则接收候选已安装到新发布目录的 `fusion/app/services/lake_alert_receiver.py`，与归档源码只有该文件一处差异，实际指纹为 `29f40cc176576a8fced6a7519a705a5dcca317301b2676150b4ba6e0d11d7c9e`。原 Fusion 镜像以显式工作目录和 `PYTHONPATH` 加载此目录通过，所选交付、接收、选择及连接配置加载通过，启用评分 profile 指纹仍为 `371e3a9d29624907f4f60360eb083bac96a020f8dd8fe5cb3f53e5c3f15cf3bd`。当前交付为独立入口源码安装及加载验证，首次接收持久正例待有获准新输入时核验。

创建候选后第一次规格核对发现 Docker 将 `OomKillDisable` 默认表示由 `null` 转为 `false`。记录该差异并修正校验中的默认值比较后，复用停止中的同一候选完成核对和切换，其余启动字段及原挂载一致。第一次校验回执保留于本机 `resume-release/create-01.json`。

本次复用原候选及页面测试，新增告警投递、显式模型派发和历史回填均为 0。新的真实 A 输出及新首接收保存仍未验。受控证据保存在本机 `.local/validation/alert-rule-source-confidence-20261125-01/resume-release/` 和 21 新发布目录的 `private/`，其中安装、离线加载、准备、切换和最终读取各有独立回执。统筹随后另行 SSH 读回运行配置及指纹，11 项通过；发布后 8181 同一告警／材料的实际页面已读回，最终源码和既有证据指纹核对通过。[本次限定发布独审](../../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/independent-release-resume-review.json)已收口，交负责人再看 8181。


## 一条正常链补验的输入预检

2026-11-25。负责人要求使用原批准 OCSF 组，从 Kafka 发布者补验新告警首次保存、Fusion 实际评分和新提示下的真实 A 输出，最终到 8181。本步按统筹要求先核输入可行性，批次为 `alert-score-first-receive-20261125-01`。13:17（Asia/Shanghai）仅查原组 10 个 UID 及两段历史来源，确认 ACK 10 条、湖中原件 10 条、已提交首次回执 10 条，未发送和未首次接收均为 0。湖字节及 Kafka 坐标、PG 原材料和首次 A 登记核对一致。当前新提示、接收源码和启用评分 profile 的指纹与已发布回执一致。 [本步只读预检](../../../docs/operations/evidence/alert-score-first-receive-20261125-01/core-input-preflight.json)

### 输入选择与去重影响

| 输入方式 | 对首次保存的作用 | 本轮适用性 |
| --- | --- | --- |
| 原 UID 在原正式范围重发 | 命中已有全局来源身份和回执，读取原首快照与材料 | 可核幂等，无法补新首次评分保存 |
| 原 UID 改 Topic、来源或租户 | 全局 `source_subject_id` 仍相同，来源或租户不同会触发范围冲突 | 无法产生新的首次回执 |
| 一条私有副本明确更换 `metadata.uid` | 新全局来源身份、新湖版本／交付键、新 Fusion 去重指纹、告警和材料身份 | 负责人确认身份变动并按新 UID 查重后，可验正式 21 一条派生测试记录的首次保存及新 A |
| 原 UID 放入空的隔离存储 | 能在隔离数据库、缓存与湖中形成首次保存 | 证据适用于隔离环境。正式 21／8181 的发布效果需沿正式入口核对，本步未建立新环境 |

接收 v2 的 `source_subject_id` 由全局根路径 `metadata.uid` 派生，`lake_alert_receipts` 以该身份唯一保存。`source-v1` Fusion 指纹包含该身份，明确更换身份的副本会产生新的缓存去重键和告警 ID。选定原件的业务对象与战术保持，关联键也保持，仍可能按正常逻辑归入既有事件。关联属于成员归组，首次告警和材料按新的身份保存。A/I 初始任务及后续自动处理继续沿原策略，验收范围为新告警及其 A。

### 获准的一条私有副本

选原批准文件第 1 行，其中源规则 ID、名称及源置信度已存在。原行摘要为 `000a1fa293650f4451aea96fea115de36ea0458ff435afaaefef6128b781ed55`，副本摘要为 `427a0e84822ad4bf3d5bbe6ba1d1091c126e4f4757c606c6af50ed4107708b38`。唯一 JSON 差异路径为 `$.metadata.uid`，该字符串 token 之外的原字节完整保持，发生时间、正文和所有其他字段核对一致。原文件及原行副本、获准副本、原／新 UID lineage 保存在 `.local/validation/alert-score-first-receive-20261125-01/private/`。统筹独立比对 8 项通过后，负责人明确选择“允许仅替换测试 UID（建议）”，授权回执见 [input-authorization.json](../../../docs/operations/evidence/alert-score-first-receive-20261125-01/input-authorization.json)。本次发送只使用该固定副本。

本地准备最初读取到旧模板库绑定，停止后改读 21 本组实际非凭据 profile，再完成输入选择、映射及各层身份变化核对。原失败状态保留。身份方案获确认后，21 按该单一 UID、派生告警／材料身份、来源和 Fusion 去重键做只读查重，均不存在；当前连接、风险配置、规则源码及 A 提示／运行策略指纹核对一致。

本批使用新专用 Topic、消费组及 `lyc` 来源，选择、消费批大小和交付各限 1 条。六份 profile 均沿 21 实配，只调整本批来源、Topic／消费组、单条上限和既有连接文件引用。使用已发布独立 Fusion 源码、开启评分的 delivery profile 和当前新提示，模型路由及单 Run 预算保持。通过标准包括实际 `created`、首快照 `computed`、同材料 `available` 与有限 Fusion 数值保存及读回，再核同轮实际 A 请求指纹、原答、保存和 8181。[执行准备与顺序](../../../docs/operations/evidence/alert-score-first-receive-20261125-01/core-execution-preparation.json)保留精确命令及各阶段受控交接文件。

### 单次执行与实际保存结果

Kafka 发布器确认 **1 条 ACK**，湖内原字节、Topic／分区／偏移及消费者提交一致。独立交付只执行一轮，持久尝试为 **`created`**，新告警、材料、首快照和 A 初始任务已真实提交。同材料 Fusion 为 **`computed`／`available`**，数值有限，因子、规则 ID／名称及原来源路径已保存；原 OCSF 材料字节与批准副本完全一致。该结果来自首次入库的实际快照。[首次保存回执](../../../docs/operations/evidence/alert-score-first-receive-20261125-01/core-first-receive.json)

正常调度产生本条 **1 次 A 尝试、1 个真实模型请求、1 份原答**，Run 与交付均完成。实际请求正文等于已发布 system prompt 与 ATT&CK 指令，提示指纹一致。原答、解析、PG assessment、同材料及固定 Run 的 HTTP 结果核对一致。**本次模型仍给出 `confidence=null`**，未取得数字正例；非空 rationale 和 Schema 通过不等于 null 原因语义通过。本批不补值、不改原答、不重复采样，正文质量不据执行成功追认。[实际 A 读回](../../../docs/operations/evidence/alert-score-first-receive-20261125-01/core-a-readback.json)

保持正常自动处理，发送后关联事件实际新增 **1 个 I Run、1 个模型步骤**，关联初始 I 任务已完成；未关联 Case，未观察到本条关联的新 Case Run。上述状态仅适用于本条范围，不能推断全局自动建 Case 开关。人工派发 I／Case 为 0。本机及 21 的原 10 条母本 SHA-256 仍一致，未覆盖原批文件、回执或原材料。[正常关联处理的只读状态](../../../docs/operations/evidence/alert-score-first-receive-20261125-01/core-automatic-state.json)

### 4177 记录与交接

复用既有作用域查询导出本条告警及固定 A，使用 `update_processing_audit.py` 在本地保存归档新增 1 条记录，原登记保持。当前本机 4177 是转发到 21 的实时工作台；实际核其 viewer、同告警／材料／固定 A、5 个步骤、14 份工件目录及模型输入／输出正文，共 9 次只读 HTTP，均与保存证据一致。没有为了归档重启或变更工作台服务。[4177 实际读回](../../../docs/operations/evidence/alert-score-first-receive-20261125-01/core-workbench-readback.json)

归档准备的失败均保留。首次导入选择了 manifest 的父目录，在写入前被拒绝，改为 manifest 所在目录后完成；首次本机 HTTP 被沙箱网络限制，获准网络访问后继续；随后静态文件字节比较发现 4177 为转发的实时 viewer，按现行部署入口核对实际同 Run 读回，未向旧静态部署写入。上述问题没有重发输入或重跑模型。

固定新告警／材料／A Run 的私有交接为 `.local/validation/alert-score-first-receive-20261125-01/readback-21/09-fetch/private/a-handoff-01.json`，实际请求、原答和保存结果为同目录 `a-observation-01.json`。业务值与正文保留受控文件。HTTP／8181 最终同条核对及统筹[限定独立验收](../../../docs/operations/evidence/alert-score-first-receive-20261125-01/independent-closeout.json)已完成：正式存取和页面刷新通过，AI 数值正例缺失、null 具体理由语义未验的边界保持。本工作单不据本轮正常链完成核销整个告警模块或 change。

### 查询跳过截图的只读定位

负责人后续截图对应原批准组第 1 条旧告警及其固定 A，与本批新身份不同。旧 Run 的 `assets`、`history`、`threat_intel` 三项均实际保存 `skipped`／`no_supported_frozen_objects`，选择器和对象键均为 0。每项 `started_at=null`、`ended_at` 已保存，`query_id`、`rows`、`returned_rows` 均为 null，未开始查询，不能当作查空或执行后漏记耗时。其历史工具／行数预算为正、结束时未到 deadline；三源代码已接线，没有这三项独立的关闭开关。截图跳过状态与后台一致；具体前端原因文案由页面方核对。

根因在旧批接收投影配置。原 OCSF 实际有 `$.unmapped.spirithub.legacy.source.ip`，旧 `projection.entity_paths.src_ip` 仅设 `src_endpoint.ip`，原件不存在后一路径。旧首快照的 `src_ip` 为空、首次材料对象为 0，冻结的同一材料对象也为 0；不是 A 冻结遗漏了已保存对象。当前批的同一母本仅换 UID，实用配置改取原有 legacy 路径，实际首存及冻结均有 1 个 IP 对象，三项查询完成。两批对象投影和 sink 源码指纹相同，现有适配器对同一输入只交换两版字段投影，即可分别复现无对象和正确取到原 IP。责任范围为旧 Fusion 湖接收 profile 的字段映射，当前批接线有效；旧首存、旧 Run 和原答未回填，不据此声称所有来源映射均已修复。

最小后续是在旧 Run 展示其真实跳过原因及“未执行”，查看新链效果时定位本批固定 A；本次定位不要求新的查询或模型运行。两次限定只读取证及本地结构对照保存在 `.local/validation/alert-score-first-receive-20261125-01/query-skip-review/`，公开回执含三项状态、字段路径、实现位置、配置指纹与工具失败范围。[查询跳过原因回执](../../../docs/operations/evidence/alert-score-first-receive-20261125-01/core-query-skip-review.json)。业务写入、配置／运行源码修改、新任务、Kafka 发送及模型调用均为 0。

统筹独立对照旧固定 A、两版接收配置及新 A 原件，10 项检查通过，[原因独审](../../../docs/operations/evidence/alert-query-skipped-display-20261125-01/independent-cause-review.json)确认上述因果及范围。本步核心只读定位结束，不扩大其他来源排查。前端明确原因、“未执行”及参数入口的调整由页面方实施、统筹另行验收。
