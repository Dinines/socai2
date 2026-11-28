# 告警两页后端合同复核：相似历史 F03-05

2026-11-24。按用户最新“先完成告警列表和告警详情”范围，本轮只核现行告警相似历史读取合同及其必要的告警详情、材料来源。服务端工作树为 `V1.1`、HEAD `167b596f6`；8181 工作树为 `/Users/lychee/Projects/SpiritHub-web-8181`、HEAD `bb368df`，均有前轮未提交修改，以下以实际文件为准。未改业务代码、平台或 8181 源码，未修改根进度、主任务或统筹审计。

## 本步安排与结论

本步沿现有 F03-05：核原功能要求 → 核源码与已保存的实际 Schema → 对照 8181 请求、候选字段和分页 → 保存可直接接线的合同及未验边界。通过条件是解释已有 422、明确正常读取与原件回查、区分参数更名和真实能力缺口；页面修复及实际有值/空态联验由页面步骤完成。本次没有规格级行为变化，不新增规格或平行任务树。

**现行 E70 已提供 F03-05 所需的三类相似历史并集查询。当前错误同时涉及请求参数、响应层级和分页方式，不能只删除 `match` 后继续按旧 `Socai2CandidatePage` 读取。** 无需为旧客户端增加服务端别名或反向兼容接口。原功能要求只规定按同主机同战术、同 IP/文件哈希看最近候选；没有要求按规则单选过滤、任意共有对象或指定种子对象检索。

- 原功能依据：[F03-05](../../../deliverables/investigation-validation-20261106/frontend-feature-list.md)、[讨论原则 §4](../../../docs/design/ui-discussion-principles.md)（91 行）、[现行规格](../../specs/alert-review-candidates/spec.md)。默认最近 5 条与同主机最近 7 条是两个功能。
- 运行结构依据：[已保存三处 Schema 结构](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/runtime-contract-structure.json)。调查 HTTP 为 `c173-q04-release-20261123-01`，Swagger 为 `c173-release-20261121-04`；这一个 E70 操作的请求及已保存响应结构一致。平台仍声明旧候选合同，不能用平台生成类型反推调查服务支持的行为。
- 既有实际依据：[8181 已知问题复测](es-ocsf-test-chain-20261124.md#spirithub-8181-已知问题复测)已经记录旧请求 422、仅带支持的 `limit` 返回 200 空列表。本轮复用该回执，不再次请求业务记录。

## 请求、匹配与分页

正式路径为 `GET /api/v1/socai2/alerts/{alert_id}/review-candidates`。路径中 `alert_id` 为当前告警 UUID。

| 查询参数 | 合同及使用方式 |
| --- | --- |
| `time_from`、`time_to` | 可选，必须同时提供、带时区且前者小于后者；按候选真实发生时间取 `[time_from, time_to)`。界面本地日期转为带时区时间后提交。 |
| `limit` | 整数，默认 5，范围 1–100。旧客户端的 30 本身合法，但与原“最近 5 条”默认口径不同。 |
| `cursor` | 首次不传，后续原样传上页 `next_cursor`，最长 4096 字符；没有 `offset`。不能传字符串 `null` 或 `undefined`。 |

未知参数和重复参数均返回 422 `alert_review_query_parameter_not_supported`，包括旧 `match`、`seed_object_id`、`window_start`、`window_end`、`offset`。这不是可以静默忽略的扩展参数集合。

未传时间窗时，以起点告警的真实 `event_time` 为上界，按配置 `default_lookback_days` 回看；仓库默认 30 天，配置入口为 `SOCAI2_ALERT_REVIEW_CONFIG_FILE`。本轮没有重新读取 21 运行配置，30 天不作为新现场配置核验结论。起点时间未知返回 422 `alert_review_explicit_window_required`，需显式时间窗，不能改用入库时间。显式窗口可以包含起点之后的记录，响应为 `scope.window_basis=explicit`。

三个规则取并集，同一告警去重，全部匹配依据保留：

| `matched_rules[]` / `matches[].rule` | 实际匹配行为 |
| --- | --- |
| `same_host_and_tactic` | 双方当前材料的 host 对象 `normalized_value` 相同，且 `detection.tactics` 至少一个非空原字符串完全相同。单独同主机或单独同战术不命中。 |
| `same_ip` | 双方当前材料的 ip 对象 `normalized_value` 完全相同。 |
| `same_hash_algorithm_and_value` | 双方明确算法及有效哈希值相同。支持 MD5/SHA1/SHA256/SHA512；算法写法规范化、哈希值大小写不敏感，核十六进制格式及长度。不猜算法或用文件名代替。 |

共同约束是同租户、同告警 `source_namespace`、同对象 `namespace` 和类型，只用双方 `latest_material_id` 的对象/检测战术，排除起点本身及发生时间未知的候选。已关闭或已有人工反馈不排除，事件/Case 原归属保留。战术大小写及名称/编码不互转，也不从技术编号推导。**这里的战术来源是材料的 `detection.tactics`，不是 `triage.attck_mappings`；页面有 AI 战术展示不能据此推定同主机规则可用。** 匹配及条数均不证明恶意或因果。

排序固定为 `event_time DESC, alert_id DESC`；`total` 是完整时间范围内去重候选总数，不是当前页数。游标绑定租户、起点告警/最新材料、起点对象及战术和时间窗；范围或起点变化返回 409 `alert_review_cursor_scope_changed`，清空旧页和游标后重读。坏游标返回 422 `invalid_alert_review_cursor`。单次查询是只读一致快照，跨页请求不冻结整个候选集合，仍须按 `items[].alert.id` 去重。改变起点或时间窗时重置分页与选中项。

## 响应字段和来源回查

| 路径 | 类型 / 用法 |
| --- | --- |
| `items` | `AlertReviewCandidate[]`，不是扁平告警行。 |
| `items[].alert` | 原 `AlertFacts`。表格及选择使用其中 `id`、`title`、`severity`、`event_time`、`handling_status`、`disposition`、`row_version`；原材料/分诊/人工反馈指针仍在该对象。名称、等级、时间、判定允许的空值沿原 DTO，不补造。 |
| `items[].matched_rules` | 三种规则枚举的数组，描述该候选满足哪些规则。 |
| `items[].time_delta_seconds` | `number|null`，候选与起点真实发生时间的绝对秒差；起点时间未知为 null。 |
| `items[].matches` | `AlertReviewMatch[]`，全部真实对象对，包含 `rule`、`seed`、`candidate`、`shared_tactics`。 |
| `items[].matches[].seed` / `candidate` | `ExplorationObject`：`id`、`alert_id`、`material_id` 为 UUID；`object_type`、`namespace`、`object_key`、`raw_value`、`normalized_value`、`source_path` 为字符串，`algorithm` 为字符串或 null。 |
| `items[].matches[].shared_tactics` | 每项为 `label`、`seed_source_paths[]`、`candidate_source_paths[]`；路径指向双方材料的 `$.detection.tactics[index]`。IP/哈希规则为 `[]`。 |
| `items[].incident_ids` / `case_ids` | UUID 数组，仅有归属 ID，没有内嵌标题，也没有旧 `cases[]` 对象。 |
| `total`、`next_cursor` | 非负整数、字符串或 null；`next_cursor=null` 才表示末页。没有 `next_offset`。 |
| `scope` | 本次起点及检索范围，见下表。没有顶层 `window_start/window_end` 或 `limitations`。 |
| `observed_at` | 数据库本次只读快照时间。 |

| `scope` 字段 | 类型 / 用法 |
| --- | --- |
| `source_alert_id`、`source_material_id` | UUID、UUID 或 null；起点告警及实际最新材料。 |
| `source_event_time`、`source_namespace` | 时间或 null、字符串；保留真实时间和来源范围。 |
| `time_from`、`time_to`、`window_basis` | 实际窗口两端及 `seed_lookback` / `explicit`；界面检索范围从这里读取。 |
| `unavailable_rules` | 规则枚举数组；起点缺少所需对象/有效战术使规则不可用，不是查询失败。 |
| `excluded_objects` | `{object_id, reason}[]`；原因枚举为 `unsupported_object_type` / `hash_algorithm_or_value_invalid`。 |

回查候选详情用 `items[].alert.id`；回查匹配原件用同一个 `seed` 或 `candidate` 内的 `alert_id` 和 `material_id`，请求 `/alerts/{alert_id}/materials/{material_id}`，再对照该对象的 `source_path` 或共同战术路径。不要混用起点告警 ID 与候选材料 ID，也不要用当前材料覆盖匹配响应指向的版本。

候选的 `alert.disposition` 是当前保存的判定，不含完整人工记录。若表头明确标“人工判定”，应沿告警详情独立的 `feedback` 识别人工来源及理由，不能只把 `disposition` 当人工证明。选择候选不写反馈；用户后续明确提交前，沿既有人工反馈流程重新读取各目标当前 `row_version`，查询本身不自动复制当前告警判定。

## 8181 对照及旧控件边界

本轮读取时的路径均位于 `/Users/lychee/Projects/SpiritHub-web-8181/web/src/`。页面聊天可能随后修改，以下是复核时定位，不代表修复已落地。

| 位置 | 发现与必要适配 |
| --- | --- |
| `features/soc-alerts/SimilarAlertReview.tsx:17–30` | 使用 Case 的 `CandidateFilters` / `caseApi.candidates`，默认 `match=all`，时间发送 `window_start/window_end`；告警请求需单独使用正式四参数。 |
| `features/soc-cases/workbench-api.ts:11,19` | 共用请求注入 `offset`，并按 `Socai2CandidatePage` 经 `offsetPage` 处理；告警读取应直接保留正式 `next_cursor`。不因修告警而同步展开 Case 功能。 |
| `features/soc-alerts/SimilarAlertReview.tsx:30,33–34` | 行键/勾选/预览读 `row.id`，正文读 `row.title/event_time/disposition/shared_objects/cases`，窗口读顶层 `window_*`；应分别取 `row.alert.*`、`row.matches`、`row.case_ids`、`scope.time_*`。 |
| `features/soc-workbench/presentation.ts:39–40` | `offsetPage` 会把不存在的 `next_offset` 变成字符串 `undefined` 并覆盖真实游标；不能套在 E70 响应上。 |
| `shared/query/useInfiniteTableQuery.ts:35–42` | 按传入行键合并页。若仍用 `String(row.id)`，多条 E70 候选的键都为 `undefined`，会被合并丢行；必须用 `row.alert.id`。 |

| 旧字段 / 控件 | 是否有现成等价合同 |
| --- | --- |
| `window_start/window_end` | 有：同一时间范围意图对应 `time_from/time_to`，仍须成对、带时区。 |
| `match=all` | 不发送 `match` 即现有三个规则的并集；这满足原 F03-05。 |
| `match=host_tactic/ip/hash` | 没有等价服务端查询参数。`matched_rules` 可用于解释已返回行，但仅过滤已加载页不等于该规则全库查询，`total` 也仍是三规则并集总数。若保留单规则检索，应登记为未支持，不伪装成完整检索。 |
| `match=shared_object` | 没有等价 E70 合同。E30 `records/related_alerts` 是同类型、同命名空间、同对象键的一般关系，排序/范围/来源依据不同，不能替代相似历史。 |
| `seed_object_id` | 告警复核没有同名或等价参数。实际 `SimilarAlertReview` 没有种子对象选择控件；此字段来自共用类型，并由 `CaseExploration.tsx:72` 的图“展开关联”写入。Case 探索另有 `object_id` 且要求 Case 上下文，不是本告警读取的别名，本轮不展开。 |
| `offset` / `next_offset` | 没有数值偏移的等价转换；按服务端返回 `cursor` / `next_cursor` 续页，不能将偏移量编码为游标。 |

真实缺口是旧页面所额外承诺的规则单选、任意共有对象、指定种子对象检索，不是缺少 F03-05 的基本查询。将告警页接到既有三规则并集、显示完整依据和实际窗口即可推进本步；不能通过本地一页筛选静默改变检索口径。

平台已保存 OpenAPI 仍声明 `match/window_start/window_end/seed_object_id/limit/offset` 及 `Socai2CandidatePage`。已有 8181 只带 `limit` 的 200 回执证明该路径的正常读取曾通过，但不证明 `time_from/time_to/cursor` 的完整转发和正例结构已在 8181 验收。页面接线后需核实际请求与响应，不能只通过旧生成类型的编译检查。

## 告警详情所需的既有 GET

以下均以 `/api/v1/socai2` 为前缀；只交接相似历史及告警详情必要读取，不重做统一调查目录复核。

| 读取目的 | 既有合同 |
| --- | --- |
| 从列表打开告警 | `/alerts` 的 `items[].facts.id` → `/alerts/{alert_id}`；列表游标是该列表自己的 `next_cursor`，不能与 E70 混用。列表 `filtered_total` 是筛选总数，`total` 是全租户总数；E70 `total` 则是本次匹配总数。 |
| 当前分诊与人工记录 | `/alerts/{alert_id}` 分别返回 `triage`、`feedback`、`analysis_url`、`material`、`section_urls`。保持 AI、人工及执行状态的边界。 |
| 当前/历史分诊及保存的解释 | 沿 `analysis_url`，正式为 `/alerts/{alert_id}/analysis`，参数 `limit`（默认20，1–50）、`before_run_id`。指定轮次为 `/alerts/{alert_id}/analysis/runs/{run_id}`；历史原件按该轮 `result.input_material_id` 读取。当前建议沿 `current.explanation.content.recommendations`，不为缺失建议生成新答案。 |
| 当前或匹配时材料 | 当前沿 `material.content_url`，历史/匹配原件用 `/alerts/{alert_id}/materials/{material_id}`。返回 `metadata/availability/content_json/content_text`，OCSF 在 `content_json.ocsf_json`，单独原文在 `content_text`；缺失按实际空值/可用性处理。 |
| 已保存引用工件 | 沿返回的来源链接；Run 工件为 `/alerts/{alert_id}/analysis/runs/{run_id}/artifacts/{artifact_id}`，非 Run 来源为 `/alerts/{alert_id}/artifacts/{artifact_id}`。保留来源所属告警和轮次。 |
| 同主机近期 | `/alerts/{alert_id}/same-host-alerts` 是 E71，读取最近 7 条其他告警，不要求相同战术；该路由拒绝任何查询参数。不得将 E70 的 `limit/cursor` 通用注入此请求。 |
| 一般关联/对象/已有响应 | 沿 `section_urls` 读 `/alerts/{alert_id}/records/{section}`，参数 `limit`（默认50，1–200）、`offset`（默认0，0–100000），按 `next_offset` 续页；与 E70 的游标合同分开。 |

同批按源 UID 独立读取 OCSF、湖 scope 配置、告警过程入口的 `/runs/context` 错位等原未完项保持，不因当前材料或 E70 已有合同而核销；原 Case 首轮及统一 Run 合同继续保存在 [既有交接](backend-resume-handoff-20261124.md)，本轮没有重复复核。

## 按 F 编号定位链路缺口

以下用于组织者逐步派工，不是本轮新增实施清单。链路按“输入/原件 → 处理 → 保存 → HTTP → 平台 → 页面 → 操作保存/刷新”定位；本轮只复核已有结构和证据，不重新执行上游步骤。后续明确派发的 socai2 修改由服务端执行聊天负责，SpiritHub 转发、生成类型及 8181 页面由页面执行聊天负责，组织者规划并独立审计。

| 功能与缺口 | 实际已有能力 | 所缺环节、责任与未验边界 |
| --- | --- | --- |
| F03-05：422 与时间参数错位 | 处理 → 保存后的材料读取 → 正式 HTTP 已有三规则并集；旧 422 和仅带 `limit` 的正常空态均有回执。 | **HTTP → 平台 → 页面**：对齐四参数和生成类型，页面方负责。正式有界时间窗/游标经平台转发未在本轮实测，不需先改 socai2。 |
| F03-05：候选层级、行身份、分页和范围展示错误 | 正式 HTTP 有 `alert`、`matches`、`scope`、`next_cursor`。 | **平台 → 页面 → 刷新/续页**：修正适配、去重键和游标，页面方负责；修复后有值/空态、续页及范围重置尚待验，删除参数并返回 200 不足以关闭。 |
| F03-05：单规则、任意共有对象、指定种子对象检索 | F03-05 原要求的三规则并集已存在；返回依据可解释具体命中规则。 | **额外筛选意图 → 处理/HTTP 合同**：告警复核没有这些查询能力。它们来自旧共用客户端/控件，不能倒推为本轮已确认的新后端需求；若后续明确保留为检索能力，由组织者限定变更范围后派服务端实施，不在本轮补接口。 |
| F03-05、F05-01：候选依据及对应原件 | **输入/原件 → 保存 → HTTP**：按实际材料/对象身份返回双边来源，并已有告警材料 GET。原合成验收证明过匹配路径和版本回查。 | **HTTP → 平台 → 页面**：本轮未验当前 8181 正例展开和同版本原件跳转，页面方按真实 `alert_id/material_id/source_path` 接线与读回；缺当前正例时保留缺证。 |
| F03-04：候选“人工判定”来源及勾选后操作 | 候选有当前保存的 `disposition`；详情另有独立 `feedback`，既有反馈流程继续沿用。 | **HTTP → 页面 → 操作保存/刷新**：核人工标签来源及提交前最新 `row_version`。本轮没有执行反馈写入，也未重新验其保存/刷新；不能用候选查询通过替代 F03-04。 |
| F03-03、F27-01：告警过程/响应关联 Run 入口（既有问题） | 正式告警分析目录、指定 Run、trace 和工件读取已有合同及原回执。 | **HTTP → 平台 → 页面**：原 `/runs`、`/runs/{id}/context` 错位与必要转发沿既有交接，页面方后续限定处理。本轮未重复复核，不新增兼容路由。 |
| F04-01、F05-01：源 UID 独立取原件与湖 scope（既有问题） | 已存告警材料可按告警/材料版本 GET，原始/标准化正文路径已明确。 | **查询入口/配置 → HTTP → 平台 → 页面**：已有回执记录独立 UID 操作缺口及 `lake_query_scope_not_configured`；这两项并非当前材料 GET 已通过就消失。待组织者分别限定服务端合同/配置工作后派发，本轮未实施或实测。 |

## 核验依据、结果与未验边界

| 依据 | 本轮核对范围 |
| --- | --- |
| [HTTP 路由](../../../services/api/investigation_http/external_routes/alert_review.py)（22–31 行） | 四查询参数、默认/约束、未知及重复参数 422。 |
| [请求与响应 DTO](../../../services/api/app/socai2/alert_review_contracts.py)（14–75 行）、[AlertFacts](../../../services/api/app/socai2/page_contracts.py)（26–67 行）、[匹配对象 DTO](../../../services/api/app/socai2/exploration_contracts.py)（31–52 行） | 参数组合、响应层级、字段类型/空值、规则/来源路径及游标。 |
| [读取实现](../../../services/api/app/socai2/alert_review.py)（33–38、63–133 行）、[SQL](../../../services/api/app/socai2/alert_review_query.sql)（1–43 行）、[哈希匹配](../../../services/api/app/socai2/exploration_matching.py)（21–36 行） | 默认窗口、当前材料、规则并集、原归属、精确匹配、稳定排序、scope 指纹和只读实现。 |
| [一般关联实现](../../../services/api/app/socai2/page_reader.py)（315–327 行） | E30 不是 E70 的单规则或单对象等价查询。 |
| [告警分析路由](../../../services/api/investigation_http/external_routes/analysis.py)（25–40、63–67 行）、[材料/工件路由](../../../services/api/investigation_http/external_routes/pages.py)（120–122、131–166、182–220 行）、[同主机路由](../../../services/api/investigation_http/external_routes/alert_hosts.py)（21–25 行） | 必要 GET 来源回查及各自不同分页参数。 |
| [实际 Schema 结构](../../../docs/operations/evidence/integration-coordination-audit-20261124-01/runtime-contract-structure.json)（11019、23283、29244 行附近） | 调查/Swagger E70 四参数、`AlertReviewPage` 顶层及 scope 字段；平台旧六参数/旧包络。已保存结构未展开 `AlertReviewCandidate` 全部嵌套字段，嵌套说明依据源码 DTO，未冒称本轮实际逐值读回。 |
| [E70 原验收](../../../docs/operations/evidence/alert-review-20261113-01/README.md)及[原独审](../archive/2026-11-13-query-alert-review-candidates/audit.md) | 复用本机合成正例/负例、分页/原件及只读验证结论；当批 21 只读到空候选。未重新跑原批，历史“同主机尚未实现”仅适用其原时点，现有 E71 单独保留。 |

上述合同结构复核不将业务记录、原始正文或模型原答送入 Codex；该阶段新增业务 HTTP、数据库写入、业务投递、模型调用、迁移和部署均为 0。通过范围为合同/源码及已有结构证据复核，不代表 8181 修复完成、正式正例/多页已经验证或告警两页整体完成。后续另行派发的实际只读补核见本文末节，分开记录。

必要后续验收仍在本 F03-05 步骤内：页面实际请求不带旧参数；已有有值与空态分别显示正确；多页按真实游标且以 `alert.id` 去重；匹配依据能回查对应材料；窗口改变清空旧游标/选择，409/422/读取失败与空候选分开。无现成正例时保留缺证，不能新增投递/模型调用来替代本轮授权范围，也不能把历史合成正例当作当前 8181 正例。

本 change 的 `openspec validate complete-socai2-investigation-chain --strict --no-interactive` 在本步开始及文档完成后均通过。离线结构对照已通过：路由签名及允许参数集合与请求 DTO 一致；源码 `AlertReviewPage` / `AlertReviewScope` 字段与已保存的调查/Swagger 结构一致；两处已保存 E70 操作结构相同；平台仍为旧六参数及 `Socai2CandidatePage`。该检查未实例化业务服务或访问数据库，不是新业务验收。新文档 UTF-8 读回、仓库文件链接、尾部空白及新增文件 diff 空白检查通过；没有业务记录 UUID 字面值。只新增本文件，原未提交修改和历史回执保持，本轮不提交、推送或继续展开其他独立问题。

## 对齐独立验收计划后的本步收口

已对照[告警链执行路径与独立验收](alert-chain-acceptance-plan-20261124.md)的 F03-05 及第 1 步。新增定向离线复核确认：候选主体类型是 `AlertFacts`；`matches.seed` 与 `matches.candidate` 各自携带告警 UUID、材料 UUID 和来源字段路径；E70 使用 `next_cursor` 而无 `next_offset`；已保存平台声明仍为旧六参数及旧包络。主 change 严格校验再次通过。

工程结论：**本步服务端合同复核完成，供组织者独立审计及页面方接线。** 这是源码/已保存 Schema 的工程检查；不据此判定 F03-05 候选页面、正式读取或整链通过。本回执仍缺当前正式非空、多页及 8181 双边原件回查的实际证据，既有采样和空页不升级为正式正例。页面可能并行修改，本节工程收口时未重新判断其最新实现状态，也未新增业务读取、写入或模型调用。连续接收的既有阻断保持原结论。

合同复核当次交付后停在此步。评论、历史材料、UID、连续接收及其他独立实现均待组织者按依赖另行派工，不修改上述验收计划或扩大本步交付范围。

## F03-05 现有验证记录可用性：追加只读步骤

组织者随后明确派发本步实际读取依赖：只核同一 21 正式环境的既有记录能否支持 E70 非空/续页及双方材料读取，不新增业务数据或模型执行。复用 `.local/validation/spirithub-pagination-20261124-01/runtime.json` 和 `page-handoff-private.json` 的显式环境、既有告警定位与时间窗；新回执独立保存在 `.local/validation/alert-review-availability-20261124-01/`，不覆盖原批。

执行边界：先核既有配置与已保存正式 Schema 地址一致，再核实际服务版本及容器数据库配置；只从原定位文件选最多 3 个有序起点，每个最多读取默认窗口与原批显式窗口各一次（`limit=5`），找到有续页的结果即停止选取。若有续页，只取一次真实 `next_cursor`；回查首页和续页各首条候选对应的双方材料，去重后最多 3 份原件。材料检查限定为响应可读、告警/材料身份及匹配来源绑定，不扩展全表、全页原件或正文质量检查。

完成证据：实际身份、窗口、游标、响应和原件留受控文件；向 Codex 仅返回工程条件是否满足和文件路径。有非空但无续页、只有显式窗口可用、读取失败或所选范围未找到均分别保留，不推断全库无数据，不将本步 HTTP 证据写成 8181 浏览器验收。无可用受控连接/定位时报告具体读取条件，停止扩大搜索。本步骤不写库、投递、运行模型、恢复消费者或部署。

执行中的限定补核：首个网络尝试被本机沙箱阻止，另一次实际 GET 已确认正式版本/数据库配置及起点 ID，但原定位文件的来源范围与 E70 scope 不一致。保留两次原回执；对同一已选身份补读详情，只有详情与 E70 的来源范围及当前材料相符才继续，最多每个已选起点一次详情读取，不扩展告警集合。重用已取得的 E70 响应，不重写冻结定位文件。默认窗口上界不含起点发生时间；后续显式窗口沿原批实际时间范围，不能由当天日期推定。

### 追加只读步骤结果

| 工程条件 | 本步结论 |
| --- | --- |
| 同一正式环境与现行 E70 | **通过**：实际容器数据库配置、发行标识与 HTTP OpenAPI 均与明确选择的正式目标一致。没有切换环境或数据库。 |
| 起点身份与来源绑定 | **通过当前详情/E70 一致性核对**。原定位文件来源范围与当前返回不一致的检查失败保留；同一已选 ID 的详情、E70 来源范围及当前材料绑定相符后才继续，不覆写原选择器。 |
| 显式窗口依据 | **通过**：沿原批带时区时间窗，已在受控端核窗口确实覆盖各已选起点的实际发生时间，E70 回显范围与请求一致；没有以今天日期构造窗口。 |
| 非空及真实续页可用性 | **本次有界选择范围未取得可用正例**。不扩展搜索，不推断正式库没有其他记录，也不将空页成功记为非空/分页通过。 |
| 双方原件可读性 | **未执行、仍缺实际证据**：本次没有取得可选匹配对象对，未生成双方材料回查结论；这不表示原件不可读。 |
| 回执与原件保护 | **通过**：原输入文件指纹保持，私密原始 HTTP 回执摘要核对一致，实际请求均为 GET；受控目录/文件权限分别为 0700/0600，目录被 Git 忽略。没有业务写入、投递、模型、消费者恢复、迁移或部署。 |

受控证据目录：`.local/validation/alert-review-availability-20261124-01/`。`attempt-01/` 保存沙箱连接失败；`attempt-02/` 保存正式环境检查及来源范围不符的原回执；`attempt-03/readback-private.json` 保存复用原响应、同 ID 详情核对及默认/显式窗口的实际读取。`attempt-03/input-private.json` 保存本次受控定位、输入和来源文件指纹；`verification.json` 仅含工程检查状态及证据位置。业务身份、时间值、正文和查询结果均留这些受控文件，不转发到 Codex。

**未生成 `page-selector-private.json`**，因当前没有经验证可用于非空/续页与双边原件的定位；不能将原分页选择器直接当作该正例交给页面方。当前 F03-05 的缺项仍是实际非空、续页和双边原件证据，已有候选实现、正式空态及历史合成验收各自保留原范围。此次有界可用性检查已结束，交组织者判断后续依赖；不继续尝试其他批次或展开下一功能。
