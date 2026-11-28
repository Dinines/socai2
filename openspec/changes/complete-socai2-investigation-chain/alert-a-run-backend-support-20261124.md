# F03-03：已有告警 A Run 的后端读取支撑

2026-11-24。按[告警依赖安排](alert-chain-acceptance-plan-20261124.md)只支撑当前告警自身 A Run、步骤、工件和冻结材料读取。SpiritHub 负责必要 GET 转发、类型及页面；本步服务端复用已有合同和受控定位，不实施评论、历史目录、UID、连续接收、事件或 Case 功能，不部署或推送。

## 本步安排与直接出口

已有定位为 `.local/validation/workbench-alert-io-20261124-01/viewer-private.json` 的 `target`，包含告警、Run、请求及应答工件身份。原 `io-proof.json` 保存过同轮输入/输出及读取检查。只使用这个定位自身的告警/Run 组合，不把其他首页样本、当前 latest 或其他批次代表自动替换进来。

正式环境沿既有 `spirithub-online-alert-20261124-01/runtime.json`，与已保存正式 Schema 地址核对；实际读取前核正式容器数据库配置和发行号。通过条件是：`source_run_id` → Run 目录真实主体 → 同一告警 → 同轮步骤与原件来源 → 该轮 `input_material_id` 与输入快照中的材料一致，所有选定原件可读。由已有回执定位后，只补同一 Run 的必要 GET，业务身份和值留受控文件。

步骤目录取首页及存在时的一次真实续页，验证顶层身份和游标；工件目录有界分页至定位到已有请求/应答、Run 输入快照及可用解释，读取所定位模型步骤和这些工件，再按 `result.input_material_id` 回查冻结材料。目录或原件缺失时保存失败，不回退到当前 Run。未覆盖的失败 Run、跨 Run 复用和页面浏览器行为仍分别保留，不扩展测试矩阵。

本步受控目录为 `.local/validation/alert-a-run-support-20261124-01/`。通过后形成 `page-selector-private.json`，供页面方直接读取固定身份、正式路径和来源文件位置；公开文档/会话只保存检查结论和路径。

### 旧定位失败与明确的新定位来源

原 IO 定位在当前正式上下文中，步骤目录、同告警详情及同主体 Run 均返回404，分别保存在 `attempt-01/` 与 `attempt-02/`；不能把它当作只有目录接口故障。原 `viewer-private.json` 记录工作台 URL 和身份，未记录数据库或发行标识，原证明也不足以核定它与当前正式 profile 同环境同版。实际检查确认当前正式容器配置和 HTTP 发行号符合本次目标；404仅说明这些身份在该读取上下文不可用，不据此断言已删除或已迁库。

组织者看到该失败后明确授权另起本批既有记录的新只读定位。复用 `.local/validation/alert-review-availability-20261124-01/attempt-03/readback-private.json` 中已核正式环境的告警详情回执，限定为原 `spirithub-pagination-20261124-01/page-handoff-private.json` 已保存的告警集合，从其中已有 `triage.source_run_id` 与 `input_material_id` 冻结一个新定位。该选择直接在受控端读取原回执完成，没有全库搜索，也没有将旧404页面回退到 latest。

新来源及指纹保存在 `replacement-locator-private.json`、`replacement-selection-checks.json`，后续单一 Run 读回写 `attempt-03/`。请求/应答工件改由该明确 Run 的模型步骤已有输入/输出引用定位，再与目录、内容及冻结材料核对；只读取最多一页模型步骤定位，不运行模型。只有新读取链通过才生成页面选择器，旧失败与原 IO 证明继续保留各自范围，新定位不能写成原定位恢复。

## 当前页面所需合同

以下路径以 `/api/v1/socai2` 为前缀；它们均已在调查服务存在，旧平台声明和当前候选是否已接通分别由页面方核对。[原结构交接](backend-resume-handoff-20261124.md)保留其他主体背景，本步不实现全局目录。

| 目的 / GET | 请求参数与输出 |
| --- | --- |
| `/alerts/{alert_id}` | 读取同一告警；当前分诊来源为 `triage.source_run_id`。分诊不存在或来源为空时保留空态，不能凭材料或最新任务虚构 Run。 |
| `/alerts/{alert_id}/analysis` | `limit` 默认20、1–50；`before_run_id` 为历史续页。响应为 `StagePage`：`subject_id/kind/current/current_pointer_id/current_unavailable_reason/entries/next_before_run_id`；不是统一目录的 `items/next_cursor`。 |
| `/alerts/{alert_id}/analysis/runs/{run_id}` | 无查询参数；`StageEntry` 包含 `run/result/explanation/partial_analysis/freshness/is_current_pointer/valid_for_current_input`。`result` 可为空，已保存结果的 `source_run_id` 必须属于该轮；其 `input_material_id` 才是冻结材料身份。不能按 Case `RunDetail` 或当前分诊补齐历史结果。 |
| `/alerts/{alert_id}/analysis/runs/{run_id}/trace` | 无查询参数；提供 `steps_url/artifacts_url`。trace 的内嵌步骤/工件有总数和截断标志，不能代替完整目录。**告警 `StageEntry` 本身没有这两个目录链接。** |
| `/analysis-runs/{run_id}/steps` | `limit/cursor/kind`；`RunStepPage` 顶层含 `run_id/subject_type/subject_id/total/next_cursor/observed_at`。仅持 `run_id` 的刷新可从这里解析主体，不需 `/runs/{id}/context` 或扫描全局目录。 |
| `/analysis-runs/{run_id}/steps/{step_id}` | 无查询参数；`RunStepView` 含步骤状态、错误、输入/输出/复用工件 ID 及 `artifact_refs[]`。单步必须属于路径中的 Run。 |
| `/analysis-runs/{run_id}/artifacts` | `limit/cursor/step_id`；`RunArtifactPage` 与步骤页具有同样的主体身份包络，行中有工件元数据及 `content_url`。 |
| 工件 `artifact_refs[].content_url` / 行 `content_url` | 沿真实来源链接请求。引用含 `role/artifact_id/run_id/subject_type/subject_id/content_url`；复用工件不能改写成当前 Run。告警同轮内容路径为 `/alerts/{alert_id}/analysis/runs/{run_id}/artifacts/{artifact_id}`，非 Run 来源另走 `/alerts/{alert_id}/artifacts/{artifact_id}`。 |
| `/alerts/{alert_id}/materials/{material_id}` | 固定告警和材料版本，历史读取不能换成当前 `material.content_url`。返回 `metadata/availability/content_json/content_text`。 |

步骤/工件目录的 `limit` 下界为1，默认及上界来自所选运行 profile，不能从告警历史列表的50上限套用。`cursor` 最长4096，按 Run、目录、筛选和排序绑定；续页保持 `kind` 或 `step_id` 条件。步骤按 `seq,id` 升序，工件按 `captured_at,id` 升序。目录主体类型是单数 `alert`，Run 类型是 `alert_basic`；返回完整相对 URL 时避免重复拼接 `/socai2`。

执行状态 `run.state/stop_reason`、交付 `delivery_state`、当前指针/新鲜度、业务分诊判定各自显示。旧失败 Run、未保存结果、不可用内容均保留实际状态，HTTP 200 不等于原件可用或模型质量通过。

## 错误结构必须分开适配

| 接口组 | 结构与边界 |
| --- | --- |
| 步骤/工件目录及单步 | 业务错误为 `detail:{code,message,context}`（`RecordError`）。404 包括 `run_not_found/step_not_found`；422 包括 `invalid_input/invalid_cursor`；503 为 `service_unavailable`。未知或重复参数返回422 `invalid_input`。非法 UUID、参数类型等框架校验也可返回 `detail:[...]`，不能只支持字符串错误。 |
| 告警主体 Run、trace、材料及内容 | 原用例错误沿 `detail:<code string>`，例如404 `stage_subject_not_found/stage_run_not_found/stage_artifact_not_found/alert_material_not_found`；框架参数校验仍可能是 `detail:[...]`。不能强制转换成目录的嵌套错误模型。 |
| 内容不可用 | 内容 GET 可能为200但 `availability` 不是 `available`；解释另有 `available/reason`。显示实际可用性，不当作已读到正文。 |

本步目录坏游标/范围不符是 **422**；不要沿用 E70 的范围变化409逻辑。404保留原指定 Run，不退到 latest。平台自己的登录错误仍保留，不混为调查服务查空。

结构依据：[Run 目录 DTO](../../../services/api/investigation_http/run_record_contracts.py)、[目录路由](../../../services/api/investigation_http/external_routes/run_records.py)、[错误转换](../../../services/api/investigation_http/errors.py)、[A/I DTO](../../../services/api/app/socai2/stage_read_contracts.py)、[主体 Run 归属与结果读取](../../../services/api/app/socai2/stage_reader.py)、[来源链接装配](../../../services/api/investigation_http/adapters/run_records.py)、[真实来源及游标](../../../services/api/app/socai2/run_records.py)。当前已有服务能力足够支撑本步骤；实际读取结果及未验边界如下。

## 直接核验结果

**本步已有 A Run 的正式读取支撑通过，已生成新的受控页面定位。** 旧定位的404保留；不是旧定位恢复，也不代表 SpiritHub 候选运行或浏览器验收完成。本步没有发现需要修改服务端业务代码的直接阻断。

| 核验链 | 结果 |
| --- | --- |
| 新定位来源及环境 | 新定位来自已核正式环境的既有告警 GET，身份仍在原授权批次选择器内；当前实际容器数据库配置与 HTTP 版本一致。来源文件和选择器指纹未变。 |
| `source_run_id` → Run → 告警 | 步骤目录顶层的 `run_id/subject_type/subject_id`、同 ID 告警详情、主体 Run 的 `run.id/kind` 与 `result.source_run_id` 一致。 |
| trace → 步骤/工件目录 | trace 的目录链接属于同一固定 Run。步骤首页及一次真实 `next_cursor` 续页通过，身份保持且页间记录不重复。 |
| 模型步骤 → 输入/输出工件 | 从该 Run 已保存模型步骤定位输入/输出；单步、工件目录及 `artifact_refs` 的工件身份、来源主体、Run 和内容链接一致。 |
| 选定工件内容 | Run 输入快照、模型步骤输入/输出及解释工件均按目录 `content_url` 读取，元数据身份一致且 `availability=available`。仅核所选原件，没有据此宣称全量原件或正文质量通过。 |
| 结果 → 冻结材料 | `result.input_material_id` 与新定位来源回执、输入快照中同一告警的材料 ID 一致；指定版本材料 GET 身份一致且可读，没有换成最新材料。 |
| 错误结构 | 复用旧失败回执核到步骤目录404的 `detail:{code,message,context}` 与主体读取404的 `detail` 字符串，保留两种结构。其余错误语义沿源码/Schema说明，本步未新造反例矩阵。 |
| 回执保护 | 实际请求均为 GET；原始响应摘要读回、页面定位与回执逐字段一致、受控权限0700/0600及 Git 忽略检查通过。 |

页面方只需读取以下文件，不应把其身份或正文转发到 Codex：

- **已验证定位：** `/Users/lychee/Documents/project/socai2/.local/validation/alert-a-run-support-20261124-01/page-selector-private.json`。
- 来源：同目录 `replacement-locator-private.json` 和 `replacement-selection-checks.json`；前者保留原正式读回位置、选择器和指纹，明确区别于旧失败定位。
- 完整正式读回：同目录 `attempt-03/readback-private.json`；输入及代码/配置来源指纹在 `attempt-03/input-private.json`。
- 工程检查：同目录 `verification.json`；旧失败完整保存在 `attempt-01/`、`attempt-02/`。

页面选择器含 `alert_id/run_id/source_run_id/material_id/input_snapshot_artifact_id/model_step_id`、模型输入/输出及解释工件 ID、`paths`、步骤首/次页查询、工件目录查询和 `selected_artifacts[].content_url`。HTTP origin/发行标识只用于核环境；产品请求仍经页面明确选择的候选平台，不直接改为访问另一个环境。使用 `run_id` 固定页面深链，刷新由步骤目录解析主体；没有新的旧 context 兼容接口。

**未验边界：** 本回执是所选一个已有 A Run 的正式后端读取；未运行新的业务模型、创建数据或执行业务写入，未复验失败/无结果 Run 的实际数据、跨 Run 复用、所有步骤/全部工件、平台会话、候选部署或浏览器。页面方下一步应以该文件中的固定身份核进入、步骤/原件点击、返回同告警和深链刷新；正文质量、相似历史正例缺证及其他告警功能不随本步核销。

实施前及完成后主 change 严格校验均通过；脚本语法、受控文件保护、9个仓库链接、文档空白和交接文件可读性检查通过。只新增本支撑文档及受控脚本/回执，没有改业务源码、平台源码、主任务、根进度或运行配置，没有部署、提交或推送。服务端本步支撑到此结束，交组织者审核后再派下一步。
