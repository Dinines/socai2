# 告警事件与 Case 逐页产品功能清单

更新于 2026-11-12。本清单按现有页面设计说明“有什么、为什么需要、操作后发生什么、做到哪一步”。适用范围是告警分诊、事件诊断、Case 调查及其阅读和人工协作；资产库存、用户基础资料由业务后端提供，不要求迁入旧 AiSOC 的其他模块或数据表。

**本清单按后端实际能力标状态。** 现有页面只作测试与设计参考，本轮不要求修改页面；125项功能的目的和结果保留，逐项给出对应HTTP、已实现部分和缺口。具体输入输出、字段与错误沿接口链接读取。当前47个HTTP操作中44已实现、3预留501；组合功能不等于新增接口。

[产品规则](../../docs/design/alert-incident-case-product-requirements.md) · [规则确认记录：D01–D07 已确认](../../docs/design/investigation-product-decisions.md) · [字段与 J01–J14 跳转合同](frontend-data-navigation-contract.md) · [当前问题](../../docs/investigation/current-issues.md)

## 本轮先确定的功能范围

以现有页面设计和已确认D01–D07为依据，**共125项功能，按告警22项、事件15项、调查88项集中整理**。这是产品需要的功能，不由当前有哪些接口反推范围；有设计不等于已经实现。下面每项继续保留为什么需要、操作结果、后端状态和接口说明。

| 业务类别 | 页面与功能范围 | 业务闭环 |
| --- | --- | --- |
| [告警功能](#一告警功能22项) | 列表/预览、概况与检测信息、AI分诊与过程、人工判定、相关对象与历史参考、所属事件/Case、时间线、原始数据及响应建议 | 找到告警 → 看事实和判断 → 人工反馈或关联调查 → 回查依据和活动 |
| [事件功能](#二事件功能15项) | 列表/预览/指标、管理、概览与当前诊断、时间线、关联分析、成员告警、对象资产匹配、活动及进入Case | 理解多个告警为何组成事件 → 看整体诊断和成员依据 → 决定是否进入Case |
| [调查功能](#三调查功能88项) | Case列表、资料、故事、概览、历史、成员、关系图/探索、对象证据、人工任务、活动/评论附件、同案助手，以及单轮调查的发现/分析/查询/图/报告 | 组织调查范围 → 明确启动 → 形成并阅读结果 → 用户补充人工事实 → 明确发起下一轮，保留历史 |

共用的A/I/Case运行详情归入“调查功能”集中说明，并保留从告警/事件进入的入口。未解决问题随调查结论显示；需要人工核实时由用户创建任务，不另设问题管理。资产库存/人员目录/真实响应审批执行由业务后端承接；本服务保留所需读取、引用和建议展示，不增加旧AiSOC平台功能。

**本轮工作顺序：功能范围 → 接口用途与输入输出审计 → 差异清单 → 文档发布。** 审计已完成，负责人已授权将补充同步本地和21 Swagger，按三类展示接口、输入输出和实现状态；不修改业务代码或扩展功能范围。实际发布结果见根交接与部署回执。

## 如何阅读实现状态

| 状态 | 含义 |
| --- | --- |
| 已实现 | 已有后端处理或读取；输入、输出、结果见该行接口 |
| 已实现，需组合接口 | 对应数据或操作都可调用，需要按说明组合读取；不承诺另有一个聚合接口 |
| 部分实现 | 只完成说明中的部分，缺失能力明确列出 |
| 未实现 | 不能完成对应业务；有参考读取或预留501不算实现 |
| 无需独立后端接口 / 调用方处理 | 选列、展示跳转、已加载内容下载等交互使用既有数据；不因此新增接口 |

E01–E47是Swagger接口编号，点击可看路径、参数、输入输出及错误；文末E1–E5仅为历史证据索引，两者不是同一编号。模型质量未通过仍单列，不以HTTP200代替结论质量。

下文沿用 F01–F28 并细分子项，技术附录仍可按原 F 编号查字段。未注明新的规则时沿用现有产品规则。关联、保存、启动、采用、审批和执行分别表达；取消未提交表单不保存，写入成功后按服务回执刷新，异常或版本冲突不假报成功。

**未解决问题的展示规则（D07 已确认）：** 未解决问题作为调查结论的一部分，在对应结果、案件当前判断及其摘要中展示。它没有独立的负责人、状态、关闭或跨轮合并流程。需要人工确认时，由用户明确创建人工任务；不自动转任务。人工任务完成沿现有结果引用规则处理，不新增“关闭问题”操作，不改写历史结论。概览的待办数只统计实际人工任务。

## 页面导航与职责

| 页面 | 用户来到这里要解决的问题 |
| --- | --- |
| 告警列表及四个详情页签 | 哪条检测需要处理，原始依据和人工意见是什么 |
| 事件列表及五个详情页签 | 哪些告警归为一组，为什么关联，是否进入 Case |
| Case 列表 | 哪些案件需要分配、处理或人工跟进 |
| Case 十个页面 | 案件资料、故事、调查概览、调查历史、成员、关系图、对象证据、人工任务、活动、评论附件 |
| Case 助手 | 围绕同案明确范围提问，保存值得保留的回答 |
| 调查运行列表及五个视图 | 某次执行查了什么、交付了什么、用了哪些依据 |

告警、事件、Case、Run 各自保持身份。点名称进入详情，预览图标打开侧栏；Case 默认进入案件资料。切换 Run 保留阅读页签并清除上一轮材料定位。

## 一、告警功能（22项）

### 告警列表与预览

设计依据：[告警页已确认约定](../../docs/design/ui-discussion-principles.md#4-告警页已确认的具体约定)、产品需求第 6 节。后端已有列表及详情读取，未实现写入按下表说明。

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F01-01 默认九列 | 快速了解检测和处理责任 | 展示名称、严重程度、告警时间、资产标签、处理状态、类别、检测源、涉及资产、负责人；资产标签不取告警标签替代 | 已实现，需组合接口 | [E26](http-handoff/endpoints.md#e26)、[E30](http-handoff/endpoints.md#e30)。读取告警基础信息、负责人名称和汇总；涉及资产通过 /alerts/{alert_id}/records/assets 查询库存匹配和标签。资产、人员目录由业务后端维护。 |
| F01-02 搜索与快捷筛选 | 找到当前要处理的告警 | 按名称、等级、状态、时间和全部／分配给我缩小列表；不改告警本身，“我”取实际登录人 | 部分实现 | [E26](http-handoff/endpoints.md#e26)。只分页；名称/等级/时间/分配给我尚无对应服务筛选参数，已加载集合可本地过滤。 |
| F01-03 排序与列选择 | 按紧急程度或时间阅读 | 仅严重程度、告警时间支持排序；列选择影响显示，不改变数据；发生时间不能用入库时间补齐 | 部分实现；展示交互由调用方处理 | [E26](http-handoff/endpoints.md#e26)。对已加载列表排序、选列；全量服务排序和偏好持久化未实现。 |
| F01-04 指标与分页 | 了解工作量，避免把当前页当全部 | 显示统计范围及已载入数量；高严重度统计含 high、critical；调查中按运行中的基础调查去重告警 | 已实现 | [E26](http-handoff/endpoints.md#e26)。读 overall_stats、total、next_before_id；高等级含high/critical，统计范围不可拿当前页替代。 |
| F01-05 预览及打开详情 | 不离开列表先判断是否深入 | 侧栏只展示概览；打开详情保持选中告警 ID，详情仍保留相关告警 | 已实现 | [E28](http-handoff/endpoints.md#e28)。选 alert_id→详情，预览与跳转为前端交互，404展示不存在。 |
| F01-06 导出与批量选择 | 交接当前结果或对明确对象操作 | 导出当前可用列表；勾选仅建立选择范围，确认管理才改变所选对象 | 部分实现 | [E26](http-handoff/endpoints.md#e26)。前端导出已加载数据和维护选中ID；全量导出及批量写管理未实现。 |
| F01-09 刷新与清除条件 | 恢复阅读范围并查看更新 | 刷新已有列表，移除单个条件或重置筛选；不重跑分诊，不改变告警状态 | 部分实现 | [E26](http-handoff/endpoints.md#e26)。刷新GET和重置before_id；刷新不分诊，完整筛选仍缺。 |

### 告警概况与公共操作

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F01-07 标题、属性与来源 | 确认看到的是哪条告警 | 阅读等级、处理状态、负责人、租户、来源号、发生／入库时间；来源未知如实显示 | 已实现 | [E28](http-handoff/endpoints.md#e28)。facts/owner_name/owner_resolution/derived；来源不明和时间缺失按原值展示。 |
| F02-01 检测信息与 ATT&CK | 理解哪个检测触发及其标签 | 展示实际规则、检测置信度及量纲、战术技术；点击可回到原材料，不把标签认定为攻击事实 | 已实现，需组合接口 | [E28](http-handoff/endpoints.md#e28)、[E31](http-handoff/endpoints.md#e31)、[E30](http-handoff/endpoints.md#e30)。详情取得 material.id→正文及 section=objects/sources；检测标签不当事实结论。 |
| F03-01 AI 分诊与评分 | 理解系统对该条检测的判断 | 判定、置信度、理由来自同一次分诊；与检测分数分开，名称按已确认 D04 使用“AI 分诊置信度” | 已实现，需组合接口 | [E28](http-handoff/endpoints.md#e28)、[E22](http-handoff/endpoints.md#e22)、[E24](http-handoff/endpoints.md#e24)。triage百分数与指定Run confidence区分量纲；判定/理由来自同一分诊版本。 |
| F03-02 发生了什么与依据 | 用可读解释理解原始记录 | 展示已保存解释、关键依据、原文中实际存在的限制和建议；无建议不补造 | 已实现，需组合接口 | [E22](http-handoff/endpoints.md#e22)、[E24](http-handoff/endpoints.md#e24)、[E33](http-handoff/endpoints.md#e33)。沿 explanation 实际来源定位工件读正文；GET不重新生成解释。 |
| F03-03 查看分诊过程 | 复核结论如何产生 | 从分析目录进入指定 A Run；失败尝试和已发布分诊分别可查 | 已实现，需组合接口 | [E22](http-handoff/endpoints.md#e22)、[E24](http-handoff/endpoints.md#e24)、[E32](http-handoff/endpoints.md#e32)、[E33](http-handoff/endpoints.md#e33)。目录选run_id→Run→trace→工件，保留失败尝试。 |
| F08-01 实体、IOC 与相关告警 | 找到值得核对的共同线索 | 查看对象及来源，打开候选自己的告警；同主机近期候选与同对象匹配集合标明筛选口径 | 部分实现 | [E30](http-handoff/endpoints.md#e30)、[E28](http-handoff/endpoints.md#e28)。section=objects/related_alerts 后打开候选；服务同对象集合不等同近期同主机专项集合。 |
| F03-04 人工判定及理由 | 让分析员记录与 AI 不同的意见 | 真实威胁、误报、正常行为、需人工跟进；误报／预期正常关闭；已关闭告警改判真实威胁／需跟进时记录理由并恢复处理中；其他反馈不自动改状态，关联事件／Case 只提示变化，D02 已确认 | 部分实现 | [E28](http-handoff/endpoints.md#e28)。feedback可读；人工判定写入及D02状态联动无API，不能用Case任务替代。 |
| F03-05 相似历史复核 | 人工反馈前对照类似情况 | 按同主机同战术、同 IP／文件哈希查看最近候选，逐条打开核对；不自动批量判定 | 未实现 | [E30](http-handoff/endpoints.md#e30)。只有一般 related_alerts 可参考；同主机同战术/同IP哈希的最近专项候选及反馈未交付。 |
| F23-01 管理告警 | 分配责任并维护处理信息 | 管理负责人、状态和标签；仅分配不改变处理状态，人工直接关闭须说明原因并保留原判定，D02 已确认 | 未实现 | [E28](http-handoff/endpoints.md#e28)。属性可读，无负责人/状态/标签管理写接口。 |
| F13-01 查看所属事件和 Case | 找到集合背景及后续调查 | 事件进入其详情；一个 Case 直达，多个供选择，零个明确无关联 | 已实现，需组合接口 | [E30](http-handoff/endpoints.md#e30)、[E29](http-handoff/endpoints.md#e29)、[E03](http-handoff/endpoints.md#e03)。section=incidents/cases→相应详情，零/一/多关系按返回值显示。 |
| F13-02 关联／新建与准备调查 | 将告警带入持续调查上下文 | 普通关联只保存成员；“准备调查”按零／一／多 Case 选择后打开同案助手，不自动发送。建案／关联后形成待更新范围 | 部分实现 | [E30](http-handoff/endpoints.md#e30)、[E01](http-handoff/endpoints.md#e01)、[E08](http-handoff/endpoints.md#e08)、[E19](http-handoff/endpoints.md#e19)。先查cases，选择已有案关联或新建，返回pending；打开助手/发送尚501。 |

### 时间线、原始数据与响应

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F01-08 时间线 | 分辨发生与处理的先后 | 最新在上显示真实发生、检测、调查及人工活动；点击回到对应来源，不造缺失时间 | 已实现，需组合接口 | [E28](http-handoff/endpoints.md#e28)、[E30](http-handoff/endpoints.md#e30)、[E22](http-handoff/endpoints.md#e22)。facts时间、section=activities与A目录按真实事件时间合并；缺时间单列。 |
| F04-01 原始记录阅读 | 验证解释是否符合收到的材料 | 查看原始 JSON／文本、标准化记录、富化内容和版本；缺正文保留版本与可用性 | 已实现，需组合接口 | [E28](http-handoff/endpoints.md#e28)、[E31](http-handoff/endpoints.md#e31)。当前material.id→原始JSON/文本/标准化/富化，保留版本与availability。 |
| F05-01 来源引用与历史版本 | 确认材料出自哪里，复查当时输入 | 显示命名空间、来源 ID 及路径；回查某轮时读冻结版本，不能换成当前材料 | 已实现，需组合接口 | [E30](http-handoff/endpoints.md#e30)、[E24](http-handoff/endpoints.md#e24)、[E33](http-handoff/endpoints.md#e33)、[E18](http-handoff/endpoints.md#e18)。section=sources/source_artifacts；历史A取当轮输入工件，Case取冻结materials，不替换为当前材料。 |
| F27-01 响应建议与自动处理 | 区分建议和真实动作 | 阅读解释／调查各自建议，打开既有 Run、查询及真实回执；没有 Case 仍能看已存自动处理 | 部分实现 | [E22](http-handoff/endpoints.md#e22)、[E24](http-handoff/endpoints.md#e24)、[E33](http-handoff/endpoints.md#e33)、[E30](http-handoff/endpoints.md#e30)。建议从解释/结果取，section=responses读已有关联；审批及实际执行未接。 |

## 二、事件功能（15项）

### 事件具体展示与跳转

这里集中说明展示字段、点击行为、目标及取数方式。页面路由来自现有设计/测试页面，后续产品可以调整路由；业务身份和关联应保持。下面HTTP路径均加 `/api/v1/socai2` 前缀，详细输入输出沿E编号查Swagger。

| 功能位置 | 展示什么 | 点击及目标 | 数据和接口 | 缺值或未实现时 |
| --- | --- | --- | --- | --- |
| 列表、搜索（F06-01） | 名称、处理状态、有效严重度、成员告警数、涉及对象/资产、负责人；分别来自facts、derived、负责人解析结果 | 点事件名称进 `#/incidents/{incident_id}/summary`；搜索/筛选只改变列表 | E27 `GET /incidents`；行身份取 `facts.id` | 分页可用；完整名称/时间/等级筛选未实现，不把当前页过滤当全库搜索 |
| 四项指标（F06-02） | 活跃事件、待分配事件、近24小时有新告警的事件、高严重程度事件 | 若作快捷筛选，只改变列表范围，不修改状态 | E27的 `overall_stats`；近24小时这一项数事件而非告警条数 | 指标可读；未提供的筛选参数不能传给API |
| 预览（F06-03） | 所选事件说明、状态、成员/对象数、有效等级、已有诊断摘要和关联Case | 预览打开侧栏；“打开详情”进入同一事件summary，不换成第一条告警 | E29 + E23诊断目录 + E30 `/incidents/{id}/records/cases` | 当前诊断为空时显示“尚无诊断”，仍能看事件事实 |
| 处理中及队列压缩（F06-06） | 处理中事件数；相同统计范围的告警数、事件数和比例 | 查看对应列表范围，不触发归并、不改状态 | E26/E27统计需核相同范围 | 当前统一压缩统计仍缺；口径不一致时不显示伪造比例 |
| 刷新、日期、列、导出（F06-07） | 当前条件、已加载量、可见列及导出范围 | 刷新重读；换条件清游标；选列只改显示；导出注明已加载范围 | E27分页；显示交互由调用方处理 | 全量日期筛选、任意排序、全量导出和偏好持久化未实现 |
| 单个/批量管理（F23-02、F23-06） | 当前负责人、状态、等级覆盖及理由、标签；批量展示所选事件 | 按所列目标规则确认后保存，仅影响所选对象；分配进入处理中、已解决仅改负责人不重开、解决需理由，均为目标规则 | E29可读字段 | 事件管理写接口未实现，不能把测试页面本地保存当实际保存 |
| 概览、ATT&CK（F06-04） | `facts.title/description/handling_status/owner_id`；`derived.severity_effective/severity_source/member_count/object_count/first_activity_at/last_activity_at/unknown_event_time_count`；成员真实检测标签 | 默认summary；点成员到告警；检测依据回相应告警材料 | E29 + E30成员 + E28/E31告警材料 | 缺时显示未记录及缺失数，不用入库时间补；战术标签不是攻击结论 |
| 当前诊断与最近尝试（F07-01） | 当前有效诊断摘要、结论、发现及待核问题；最近尝试状态/错误另列 | 点尝试进 `#/investigations/{run_id}/overview`，保留父事件ID | E23目录 → E25指定Run → E32/E33步骤/工件 | 无有效诊断也能读失败尝试，不能用最近失败替换当前判断 |
| 时间线、共同线索（F06-05） | 成员发生时间、名称、共同对象和已保存归并依据 | 点告警开预览；点来源读原文；排序不改变成员 | E30 `/records/members`、`/records/objects`；E28/E31原件 | 未知时间单列；同主机/相近时间只表示关联 |
| 关联分析（F08-02） | 本事件告警/对象节点、关联边和依据 | `#/incidents/{id}/attack`；点节点读对象，点边看依据；固定本事件范围 | E30成员/对象/依据，由调用方组图 | 不自动跨事件扩展，无依据保留未知，不新增攻击溯源接口 |
| 成员告警（F08-03） | 名称、等级、发生时间、状态、涉及资产 | `#/incidents/{id}/alerts`；标题先预览，“打开告警页”进 `#/alerts/{alert_id}/overview` | E30 `/incidents/{id}/records/members` 的 `items[].id` → E28 | 无成员显示空列表，不能用事件ID代替告警ID |
| 对象与资产（F08-04） | 来源中的主机/IP/账号、类型、来源告警；库存匹配后增加设备信息及标签 | `#/incidents/{id}/assets`；对象点开来源；有真实asset_id且业务后端提供地址才进入资产详情 | E30 `/records/objects`、`/records/assets`；E28来源告警 | 无库存仍显示来源对象；本服务不创建资产、不提供资产管理路由 |
| 处理活动（F23-03） | 操作者、时间、动作、目标、前后值和结果 | `#/incidents/{id}/activities`；按目标真实类型/ID回事件、告警或Case | E30 `/incidents/{id}/records/activities` | 空列表显示暂无活动；模型步骤不冒充管理动作，外部目标无URL仅显示编号 |
| 进入/创建/关联Case（F13-03） | 关联Case、标题和关系来源：成员关系或显式事件关系 | 先查关联：1个进 `#/cases/{case_id}/case-info`；多个供选择；0个显示无关联并提供新建/关联已有。确认保存后用回执Case ID跳转 | E30 `/records/cases`；E01新建带title/key/incident_ids；E08关联带目标Case、范围版本/key/incident_ids | 成员由服务展开并集去重；incident_id不是case_id。新建/关联不启动调查 |

共用规则见[技术附录J01/J03/J04/J05/J14](frontend-data-navigation-contract.md#跳转与关联规格)。404或错误父主体应停止下钻并提供返回入口，不回退到其他事件/告警来填数据。

### 事件列表与预览

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F06-01 列表与搜索筛选 | 安排多告警集合的处理顺序 | 查看事件名称、状态、有效等级、成员、资产和负责人；搜索／筛选只改变列表 | 部分实现 | [E27](http-handoff/endpoints.md#e27)。列表/分页可用；完整搜索筛选参数缺失。 |
| F06-02 四项指标 | 找到待处理、待分配及近期变化 | 活跃事件、待分配、24h 有新告警、高严重程度均数事件；缺负责人不自动算未分配 | 已实现 | [E27](http-handoff/endpoints.md#e27)。读取overall_stats，按事件统计和观察时间展示。 |
| F06-03 预览与进入详情 | 快速了解整件事 | 侧栏看事件整体说明、成员／资产／调查及已有优先级；进入默认概览，不用告警评分列表代替事件说明 | 已实现 | [E29](http-handoff/endpoints.md#e29)。incident_id→事实与派生摘要；诊断补E23。 |
| F06-06 处理中与队列压缩 | 分别看处理进度和告警归并规模 | 处理中按事件业务状态计数；队列压缩显示同一数据范围的告警与事件数量及比例，不代表准确率或已解决率 | 部分实现 | [E27](http-handoff/endpoints.md#e27)、[E26](http-handoff/endpoints.md#e26)。两主体统计的观察时间/范围不同不能直接认定为同口径压缩比，统一统计仍缺。 |
| F06-07 刷新、日期、列和导出 | 适配阅读及交接需要 | 刷新、选时间范围、排序／选列／分页、导出已载入筛选结果；复制列表链接保留筛选条件 | 部分实现 | [E27](http-handoff/endpoints.md#e27)。刷新分页和已加载数据列/排序/导出为前端；完整日期筛选缺失。 |
| F23-06 批量管理事件 | 对明确选中的事件统一处理 | 勾选后管理负责人／状态等，按所选范围确认；沿用事件状态联动，不改未选事件 | 未实现 | [E29](http-handoff/endpoints.md#e29)。批量负责人/状态等管理无HTTP写入口。 |
| F23-02 事件管理 | 指定负责人与处理结果 | 分配后进入处理中，已解决案仅改负责人不重开；人工解决需说明；严重度覆盖保留理由且不改成员等级 | 未实现 | [E29](http-handoff/endpoints.md#e29)。管理字段可读，负责人/状态/严重度覆盖写回未实现。 |

### 五个事件详情页签与 Case 入口

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F06-04 概览与 ATT&CK | 理解事件是什么及大致范围 | 显示说明、阶段计数、成员／资产、首次末次发生时间和缺时间数量；阶段覆盖不等于防御覆盖率 | 已实现，需组合接口 | [E29](http-handoff/endpoints.md#e29)、[E30](http-handoff/endpoints.md#e30)。derived与section=members/objects，阶段来自真实成员材料。 |
| F07-01 当前诊断和最近尝试 | 分开看可引用判断及执行是否成功 | 已发布诊断保留；最近尝试失败单列原因；无发布结果仍可看成员和尝试 | 已实现，需组合接口 | [E23](http-handoff/endpoints.md#e23)、[E25](http-handoff/endpoints.md#e25)、[E32](http-handoff/endpoints.md#e32)。current与entries分别显示；current_unavailable_reason和失败尝试保留。 |
| F06-05 时间线与共同线索 | 看告警如何在时间和对象上相连 | 按成员发生时间阅读并回查共有对象；未知时间单列，不编造归并规则 | 已实现，需组合接口 | [E30](http-handoff/endpoints.md#e30)、[E29](http-handoff/endpoints.md#e29)。members/objects/activities及关联来源按真实时间组合。 |
| F08-02 关联分析图 | 解释为何属于同一事件 | 固定本事件范围，筛选来源、聚焦告警／对象，查看节点和边依据；不跨事件扩展 | 已实现，需组合接口 | [E30](http-handoff/endpoints.md#e30)、[E23](http-handoff/endpoints.md#e23)、[E33](http-handoff/endpoints.md#e33)。members/objects及诊断依据组装本事件图；对象共现不标因果，无跨事件扩展。 |
| F08-03 成员告警 | 逐条核实组成事件的告警 | 查看等级、时间、状态及资产；点标题开预览，再打开对应告警详情 | 已实现 | [E30](http-handoff/endpoints.md#e30)、[E28](http-handoff/endpoints.md#e28)。subject=incidents,section=members；告警ID打开详情，按next_offset分页。 |
| F08-04 涉及对象与资产匹配 | 确认主机、账号等从哪里出现 | 查看对象、来源告警及库存匹配；同名不等于同一资产，无库存仍保留来源对象 | 已实现，需组合接口 | [E30](http-handoff/endpoints.md#e30)。objects与assets连接；assets是对象匹配边，total不是去重资产数，未匹配仍保留对象。 |
| F23-03 处理活动 | 复查谁改了什么 | 显示操作者、时间、目标、前后值及结果；点目标回相应对象，步骤不冒充管理活动 | 已实现 | [E30](http-handoff/endpoints.md#e30)。section=activities；显示matching_targets和截断，不按共享Case泛化主体活动。 |
| F13-03 进入／创建／关联 Case | 将集合推进到深入调查 | 一案直达、多案选择、无案新建或关联；新建带事件名称及全部合法成员，整体校验、并集去重 | 已实现，需组合接口 | [E30](http-handoff/endpoints.md#e30)、[E01](http-handoff/endpoints.md#e01)、[E08](http-handoff/endpoints.md#e08)、[E03](http-handoff/endpoints.md#e03)。事件cases关系→新建/关联，incident_ids保留显式关系并展开成员；不自动start。 |

## 三、调查功能（88项）

### Case 列表与公共页头

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F09-01 四项案件指标 | 安排负责人和人工跟进 | 待分配、处理中、高严重程度、待人工跟进均按案件计数；点击替换指标条件，其他筛选保留 | 已实现 | [E02](http-handoff/endpoints.md#e02)。metrics整体四项，high_severity仅high；与筛选total分开。 |
| F09-02 搜索筛选和分页 | 在真实案件库定位案件 | 按标题／完整 ID、状态、等级、负责人 ID、分配状态、指标查；换条件回首页 | 已实现 | [E02](http-handoff/endpoints.md#e02)。q及已声明筛选+cursor；条件改变丢弃旧cursor。 |
| F09-03 列选择与排序 | 按工作习惯阅读 | 仅改变列表显示；服务当前按业务更新时间与 ID 排序，不将本地偏好写成服务能力 | 部分实现；展示交互由调用方处理 | [E02](http-handoff/endpoints.md#e02)。保留服务固定排序/游标，列选择前端；自定义服务排序/偏好保存缺失。 |
| F09-08 日期范围与导出 | 按工作时段查找并交接案件 | 选择最近时段／自定义范围，导出当前已载入筛选集合；不代表完整服务库导出 | 部分实现 | [E02](http-handoff/endpoints.md#e02)。已加载结果可前端导出，完整日期筛选/导出无接口。 |
| F09-09 手动与自动刷新 | 保持列表便于持续查看 | 手动刷新重读；原型自动刷新定时重绘当前集合，不代表后台持续取新数据或自动调查 | 部分实现；展示交互由调用方处理 | [E02](http-handoff/endpoints.md#e02)。手动GET刷新；自动刷新调度由前端实现，当前正式接线未完成。 |
| F09-10 案件预览 | 不离开队列先了解案件 | 从行／预览入口看摘要，再进入默认案件资料；保持选中案件身份 | 已实现 | [E03](http-handoff/endpoints.md#e03)。队列item.id→详情预览，保留当前列表位置。 |
| F09-11 调查运行与管理设置入口 | 提供跨案运行入口并说明占位边界 | 查看调查运行进入全局目录；案件管理设置当前只是占位，不据按钮增加设置功能 | 部分实现 | [E02](http-handoff/endpoints.md#e02)、[E10](http-handoff/endpoints.md#e10)、[E22](http-handoff/endpoints.md#e22)、[E23](http-handoff/endpoints.md#e23)。运行入口需要组合；管理设置模块没有对应实现。 |
| F09-04 新建 Case | 为明确材料建立工作区 | 输入名称并选择至少一项告警／事件；保存后打开新案及待启动记录，不能创建成功就报调查完成 | 已实现 | [E01](http-handoff/endpoints.md#e01)、[E03](http-handoff/endpoints.md#e03)、[E12](http-handoff/endpoints.md#e12)。选择告警/事件创建→回执Case与pending→资料；不自动启动。 |
| F09-05 资料页头与刷新 | 随时知道当前案件及管理状态 | 显示标题、等级、状态、负责人和显式关联事件；刷新读真实状态，未知优先级不造值 | 已实现 | [E03](http-handoff/endpoints.md#e03)。Case身份/资料刷新；owner_id名称由业务后端解析。 |
| F23-04 管理 Case | 调整责任与管理信息 | 管理名称／说明、负责人、状态、等级和标签；运行中／执行不明不能结案；未完任务提醒后可说明理由结案且任务原状保留；人工重开不自动启动调查，D01 已确认 | 已实现 | [E03](http-handoff/endpoints.md#e03)、[E04](http-handoff/endpoints.md#e04)、[E44](http-handoff/endpoints.md#e44)、[E45](http-handoff/endpoints.md#e45)、[E46](http-handoff/endpoints.md#e46)、[E47](http-handoff/endpoints.md#e47)。E44读取版本与结案条件，E45管理标题/说明/负责人/等级/标签及未结案状态，E46结案、E47重开；E04保持分类/期限。D01已实现，前端页面接线另验。 |
| F14-01 跨页执行提示 | 切页后仍知道调查进行到哪 | 查看活跃运行并返回该轮，保持与任务状态独立 | 已实现，需组合接口 | [E03](http-handoff/endpoints.md#e03)、[E10](http-handoff/endpoints.md#e10)、[E12](http-handoff/endpoints.md#e12)。定位baseline_records/历史→各Run状态/资格；全站提示为页面接线。 |

### 案件资料

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F09-06 案件说明和范围概况 | 先理解背景，再深入调查 | 阅读说明、成员、资产、材料、记录数量和活动时间；进入成员／对象／历史 | 已实现，需组合接口 | [E03](http-handoff/endpoints.md#e03)、[E39](http-handoff/endpoints.md#e39)、[E10](http-handoff/endpoints.md#e10)。范围成员/事件、历史、人工任务计数；缺数据不填0。 |
| F10-01 案件分类与截止时间 | 支持管理标记和跟进时限 | 保存分类、期限后重新读取；无值显示未分类／未设期限，版本冲突不能覆盖 | 已实现 | [E03](http-handoff/endpoints.md#e03)、[E04](http-handoff/endpoints.md#e04)、[E05](http-handoff/endpoints.md#e05)。读版本→同时提交分类/期限+source_note→刷新；409保留编辑内容。 |
| F11-01 当前采用判断 | 确认案件当前认可什么 | 阅读结论、形成／采用时间和来源；没有就显示尚无判断，不取最近 Run 标题拼接 | 已实现 | [E03](http-handoff/endpoints.md#e03)、[E05](http-handoff/endpoints.md#e05)。current_assessment/assessment及来源；不取最新失败Run覆盖。 |
| F12-01 判断覆盖与依据变化 | 知道结论能否用于当前成员 | 分开显示判断覆盖、尚未调查成员及依据 current／stale／unverified；保留旧判断并指出限制 | 已实现，需组合接口 | [E03](http-handoff/endpoints.md#e03)、[E05](http-handoff/endpoints.md#e05)、[E14](http-handoff/endpoints.md#e14)。采用判断覆盖范围与当前成员比较，按真实freshness展示变更。 |
| F12-02 回查判断来源 | 让判断可复核 | 点击 Result、工件、人工版本回到形成时的记录；不能用今天的任务内容替换旧依据 | 已实现，需组合接口 | [E03](http-handoff/endpoints.md#e03)、[E14](http-handoff/endpoints.md#e14)、[E24](http-handoff/endpoints.md#e24)、[E25](http-handoff/endpoints.md#e25)、[E43](http-handoff/endpoints.md#e43)。按来源类型和身份打开指定结果/分诊/诊断/人工版本，不跳当前版本冒充旧引用。 |
| F11-02 结论中的未解决问题 | 说明当前判断仍有哪些事实未查清 | 随当前采用判断展示未解决问题及限制，回查对应调查；需要人工确认时由用户创建任务，不单独管理问题或计入任务待办 | 已实现，需组合接口 | [E03](http-handoff/endpoints.md#e03)、[E14](http-handoff/endpoints.md#e14)、[E15](http-handoff/endpoints.md#e15)。questions及原结论限制一并展示；用户需要时自行E38创建任务，无问题状态/关闭/合并接口。 |
| F09-07 ATT&CK 阶段与详细信息 | 看成员检测涉及哪些阶段 | 同层级展示阶段、告警数及管理资料；阶段标签不证明完整攻击链 | 已实现，需组合接口 | [E03](http-handoff/endpoints.md#e03)、[E28](http-handoff/endpoints.md#e28)、[E31](http-handoff/endpoints.md#e31)。遍历当前成员读取材料阶段标签，原字段不足就显示未知。 |
| F11-03 显式采用其他结果 | 有意改变当前案件判断 | 仅采用明确保存的调查结果；先展示原／新判断及覆盖，填写理由并留旧版本；局部回答作补充、普通消息不可直接采用，D03 已确认 | 未实现 | [E21](http-handoff/endpoints.md#e21)。adopt返回501；D03理由/覆盖确认尚无已实现HTTP参数。 |

### 案件故事

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F20-01 事实与认识时间线 | 理解事情和调查怎样发展 | 倒序组合告警发生、Run 开始／结束、已保存回答和人工完成；无时间排后，活跃轮不提前给结论 | 部分实现；现有材料可组合读取 | [E03](http-handoff/endpoints.md#e03)、[E28](http-handoff/endpoints.md#e28)、[E10](http-handoff/endpoints.md#e10)、[E14](http-handoff/endpoints.md#e14)、[E39](http-handoff/endpoints.md#e39)、[E42](http-handoff/endpoints.md#e42)。成员事实+Run结果+H版本按来源时间组装故事；Q保存尚缺。 |
| F20-02 搜索与等级筛选 | 从长故事找相关活动 | 按告警名、主机、账号及等级缩小阅读，不改变正式成员或已存历史 | 部分实现 | [E03](http-handoff/endpoints.md#e03)、[E28](http-handoff/endpoints.md#e28)、[E10](http-handoff/endpoints.md#e10)、[E39](http-handoff/endpoints.md#e39)。已加载故事本地搜索/等级筛选；无全故事检索接口。 |
| F20-03 单选／多选告警 | 结合共同对象理解局部范围 | 右侧看所选告警、共有对象及相关调查；可开原告警 | 部分实现；展示交互由调用方处理 | [E03](http-handoff/endpoints.md#e03)、[E28](http-handoff/endpoints.md#e28)。维护当前选择ID，组合已读故事；不修改Case成员。 |
| F20-04 围绕条目或全案提问 | 让问题有明确上下文 | 带入全案、多条告警、某轮结果或人工结果至同案助手；打开和选择均不执行 | 未实现 | [E19](http-handoff/endpoints.md#e19)。仅助手预留501，不能将故事选中范围当新成员写入。 |
| F20-05 回到结果和人工版本 | 从摘要追到形成依据 | 点击指定 Run／任务修订，保留当时范围、时间与结果 | 已实现，需组合接口 | [E14](http-handoff/endpoints.md#e14)、[E43](http-handoff/endpoints.md#e43)、[E28](http-handoff/endpoints.md#e28)。条目保存真实主体/结果/revision_id后导航；故事页面接线待补。 |

### 调查概览

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F14-02 活跃与待启动分开 | 不把排队当执行或丢失下一轮 | 同时显示 running／unknown 和 pending_update；打开相应 Run，未知执行不能视为结束 | 已实现，需组合接口 | [E03](http-handoff/endpoints.md#e03)、[E12](http-handoff/endpoints.md#e12)。running/unknown与pending分组，can_start/reason决定启动按钮。 |
| F14-03 准备新一轮 | 明确下一次要调查的范围 | 保存或更新待启动记录，合并未开始变更；当前活跃输入不变；可回查范围变化 | 已实现 | [E03](http-handoff/endpoints.md#e03)、[E11](http-handoff/endpoints.md#e11)、[E12](http-handoff/endpoints.md#e12)。scope_revision→prepare→pending读取；准备不执行。 |
| F14-04 确认启动 | 由用户明确发起一次调查 | 按资格确认后冻结本轮输入并启动；空案、已解决或范围冲突不能启动；结束后不自动接续 | 已实现 | [E12](http-handoff/endpoints.md#e12)、[E13](http-handoff/endpoints.md#e13)、[E14](http-handoff/endpoints.md#e14)。确认时间/比较对象→start；GET读进度，终态读result_ids；异常不盲目重复POST。 |
| F16-01 已有结果摘要 | 判断下一步应看哪一轮 | 先读结论（含未解决问题）、变化、影响，再开完整结果；不另设问题队列；失败轮保留已存材料，已有采用判断单列 | 已实现，需组合接口 | [E10](http-handoff/endpoints.md#e10)、[E12](http-handoff/endpoints.md#e12)、[E14](http-handoff/endpoints.md#e14)。历史→选Run→结果摘要，区分当前采用与历史结论。 |
| F22-01 人工摘要与待办 | 知道还缺哪些人工确认 | 未开始／进行中计待办，完成／取消不计；进入任务详情，不把任务数写成案件数 | 已实现，需组合接口 | [E39](http-handoff/endpoints.md#e39)。取完任务分页后按state计待办；不把questions纳入待办数。 |
| F14-05 历史与故事入口 | 从当前工作切回演变过程 | 全部历史进入轮次列表，故事进入事实时间线 | 已实现，需组合接口 | [E10](http-handoff/endpoints.md#e10)、[E03](http-handoff/endpoints.md#e03)、[E39](http-handoff/endpoints.md#e39)。历史直接读；故事按F20组合，暂无独立故事接口。 |

### 调查历史

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F14-06 历史记录分类与选择 | 区分首次、更新和保存的 AI 结论 | 按目标、原因、时间、范围、状态选择指定轮次；切轮保留阅读视图 | 已实现，需组合接口 | [E10](http-handoff/endpoints.md#e10)、[E22](http-handoff/endpoints.md#e22)、[E23](http-handoff/endpoints.md#e23)。本案baseline/ai_saved历史和成员A/I目录分别组合；当前Q无新保存记录。 |
| F15-01 状态、交付与投入 | 判断哪轮可用及为何未完整交付 | 分开执行状态、完整性、停止原因、耗时、模型次数及 Tokens；未知值不记零 | 已实现，需组合接口 | [E12](http-handoff/endpoints.md#e12)、[E14](http-handoff/endpoints.md#e14)。state/delivery_state/usage/validation分开展示；none与缺值不同。 |
| F16-02 结果比较 | 看这次增加了什么认识 | 以明确 comparison_result_id 比对新增输入、发现和判断；不随当前最新结果漂移 | 已实现，需组合接口 | [E14](http-handoff/endpoints.md#e14)、[E13](http-handoff/endpoints.md#e13)。读取当前和comparison_result_id两份结果；新启动可指定同案比较对象，不自动改历史。 |
| F12-03 历史范围与冻结引用 | 避免用当前成员误读旧结论 | 打开当轮输入、任务版本及来源；后续成员和人工编辑不改旧引用 | 已实现，需组合接口 | [E12](http-handoff/endpoints.md#e12)、[E18](http-handoff/endpoints.md#e18)、[E15](http-handoff/endpoints.md#e15)、[E43](http-handoff/endpoints.md#e43)。run.members指定材料、输入工件及冻结H修订，不能拿当前资料替换。 |

### 成员告警

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F13-04 当前成员及事件 | 清楚哪些材料正式属于本案 | 阅读成员和显式事件，区分间接共享告警关系；分页／截断显示数量 | 已实现，需组合接口 | [E03](http-handoff/endpoints.md#e03)、[E28](http-handoff/endpoints.md#e28)、[E29](http-handoff/endpoints.md#e29)。Case members/linked_incidents→对应主体详情；member_count与截断保留。 |
| F13-05 添加告警／事件 | 扩大正式调查范围 | 搜索、选择并确认，整体校验同来源同租户；并集去重，重复加入不重复更新，回查新增数 | 已实现 | [E26](http-handoff/endpoints.md#e26)、[E27](http-handoff/endpoints.md#e27)、[E03](http-handoff/endpoints.md#e03)、[E08](http-handoff/endpoints.md#e08)。分页选候选→读scope_revision→associations→刷新Case。 |
| F13-06 移动成员 | 将告警明确交给另一案件 | 指定源成员和目标案，核两案版本，同步更新两案范围；原历史不变 | 已实现 | [E03](http-handoff/endpoints.md#e03)、[E09](http-handoff/endpoints.md#e09)。两案各读范围版本→move→刷新两案；事件显式关系不随告警移动。 |
| F13-07 管理所选告警 | 对明确范围统一维护处理信息 | 仅影响勾选告警，不借“添加”从别案移走，不把选中视为提交 | 未实现 | [E28](http-handoff/endpoints.md#e28)。所选告警通用管理无写接口。 |
| F13-08 成员变化后的提示 | 防止新增材料被误认为已分析 | 显示待更新及未覆盖成员，保留当前轮固定输入，引导准备／启动下一轮 | 已实现，需组合接口 | [E03](http-handoff/endpoints.md#e03)、[E12](http-handoff/endpoints.md#e12)。保存后读scope_revision/pending_run_id；提示范围更新，自动跟随/调度未实现。 |

### 案件关系图与关联探索

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F19-01 当前底图与阅读 | 理解案件内对象如何关联 | 使用有资格的已完成调查图；无完成调查按成员关系；纯文本答复不换底图，缺图不借其他轮伪补 | 已实现，需组合接口 | [E03](http-handoff/endpoints.md#e03)、[E30](http-handoff/endpoints.md#e30)、[E14](http-handoff/endpoints.md#e14)、[E15](http-handoff/endpoints.md#e15)。当前成员对象组合底图，已存图按graph_artifact_id读取并标历史轮次。 |
| F19-02 筛选、布局与节点详情 | 从复杂关系定位对象和依据 | 筛选等级／状态／来源，缩放、分组、布局、重置视角；点节点或边看来源，不认定因果 | 部分实现；展示交互由调用方处理 | [E30](http-handoff/endpoints.md#e30)、[E15](http-handoff/endpoints.md#e15)。布局/筛选/聚焦前端处理；节点详情来自原料，正式交互未接。 |
| F25-01 推荐线索与候选预览 | 找到值得进一步核查的案外材料 | 在同租户、来源可核对的已有告警／对象中查候选，可含其他案记录；默认围绕本案告警发生时间，用户可调整；展示时间差、共享对象、范围和归属，分数只表排序 | 未实现 | [E30](http-handoff/endpoints.md#e30)。related_alerts仅参考，不符合D05完整候选/窗口/来源校验能力。 |
| F25-02 实体扩展与撤销 | 逐步探索而不立即扩大案件 | 预览后展开节点，区分新增关系，可撤销／重置；战术节点不能当实体扩展起点 | 未实现 | 暂无对应接口。无探索查询、扩展、撤销状态服务。 |
| F25-03 保存／恢复探索 | 中断后继续当前思路 | 保存起点和画布状态，不生成 Run、不改变成员；新结果不偷偷替换已有探索 | 未实现 | 暂无对应接口。无保存恢复API，未使用探索表已删除，不能据此恢复旧表。 |
| F25-04 正式加入本案 | 把查到的有效告警纳入调查 | 明确确认后以关联加入，不从原案移走；记录实际新增及待更新；只预览／保存探索不会加入 | 部分实现 | [E03](http-handoff/endpoints.md#e03)、[E08](http-handoff/endpoints.md#e08)。已确认真实候选可复用关联命令；候选产生和图到命令闭环缺失。 |
| F26-01 询问所选对象 | 针对关系提出具体问题 | 将对象及关联告警带入同案助手，打开不扩展、不加成员、不发送 | 未实现 | [E19](http-handoff/endpoints.md#e19)。对象范围问答尚501，scope字段未实现。 |

### 对象与证据

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F21-01 按对象浏览 | 直接回答某台主机有什么依据 | 左侧搜索、按类型筛选和相关告警数；选中后右侧看资料、来源告警及调查 | 已实现，需组合接口 | [E03](http-handoff/endpoints.md#e03)、[E30](http-handoff/endpoints.md#e30)、[E05](http-handoff/endpoints.md#e05)。遍历成员objects→按命名空间/类型/键聚合，连接evidence；无Case对象聚合端点。 |
| F21-02 按调查浏览 | 保留难以归类到对象的材料 | 按 Run 看查询、报告、工件；无当前对象仍可读历史，打开对应轮次查询页 | 已实现，需组合接口 | [E10](http-handoff/endpoints.md#e10)、[E12](http-handoff/endpoints.md#e12)、[E14](http-handoff/endpoints.md#e14)、[E15](http-handoff/endpoints.md#e15)。选择历史Run→其工件与结果，保留当轮范围。 |
| F21-03 证据、威胁与覆盖 | 区分材料数量和有效判断 | 展示有效证据、威胁身份、覆盖及限制；无索引为未记录，有效空索引才为 0 | 已实现，需组合接口 | [E05](http-handoff/endpoints.md#e05)、[E06](http-handoff/endpoints.md#e06)、[E15](http-handoff/endpoints.md#e15)。读取evidence及对应工件；发布已有目录用E06，非自动生成证据。 |
| F21-04 原件和引用回查 | 检查材料是否支持结论 | 定位来源告警、查询、结果、人工版本或回执；只有摘要、受限、缺原件分别显示 | 已实现，需组合接口 | [E15](http-handoff/endpoints.md#e15)、[E16](http-handoff/endpoints.md#e16)、[E18](http-handoff/endpoints.md#e18)、[E31](http-handoff/endpoints.md#e31)、[E33](http-handoff/endpoints.md#e33)、[E34](http-handoff/endpoints.md#e34)、[E35](http-handoff/endpoints.md#e35)。按引用所属Case/Run/A/I选对应正文路由；availability不足保留来源。 |

### 人工任务

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F22-02 列表、状态和待办数 | 知道谁还需要确认什么 | 显示事项、说明、负责人、期限、状态和结果；徽标表示未完成数量，不等于总数 | 已实现 | [E39](http-handoff/endpoints.md#e39)。当前任务/状态列表，offset分页；待办只统计not_started/in_progress。 |
| F22-03 用户新建与分配 | 承接需要人工确认的业务事实 | 用户阅读结论后明确创建任务，填事项，按需填说明、负责人、期限、来源调查及参考；保存后在同案任务页出现，不自动从未解决问题生成任务 | 已实现 | [E03](http-handoff/endpoints.md#e03)、[E38](http-handoff/endpoints.md#e38)、[E41](http-handoff/endpoints.md#e41)。用户明确创建，标题/负责人/期限/来源→回执任务；人员目录/通知由业务后端。 |
| F22-04 编辑、取消及状态更新 | 在同一事项内继续协作 | 所有状态均可编辑，取消不删除历史；编辑带入原值，明确保存产生新版本 | 已实现 | [E41](http-handoff/endpoints.md#e41)、[E03](http-handoff/endpoints.md#e03)、[E40](http-handoff/endpoints.md#e40)。完整带回TaskFields和双版本后PUT，取消为state=cancelled，不删除旧版本。 |
| F22-05 完成结果与适用范围 | 防止一句人工确认被推广到全案 | 完成须有非空结果及明确成员范围；对象范围需对象键；时间可不填，填写须成对；不强制工单或附件 | 已实现 | [E41](http-handoff/endpoints.md#e41)、[E03](http-handoff/endpoints.md#e03)、[E40](http-handoff/endpoints.md#e40)。completed需正文及有效result_scope；完成不会自动改调查判定。 |
| F22-06 完成人、修改人与历史 | 能复核是谁在何时确认什么 | 分开负责人、实际完成者、修改者；看指定修订，元数据编辑不改变原事实或扩大范围 | 已实现，需组合接口 | [E41](http-handoff/endpoints.md#e41)、[E42](http-handoff/endpoints.md#e42)、[E43](http-handoff/endpoints.md#e43)。当前完成人/时间及修改历史按固定revision_id读取。 |
| F22-07 并发冲突处理 | 不丢自己的输入也不覆盖他人 | 409 保留输入，查看最新；明确重新编辑才装入最新值，不自动重提交 | 已实现 | [E40](http-handoff/endpoints.md#e40)、[E41](http-handoff/endpoints.md#e41)、[E03](http-handoff/endpoints.md#e03)。409保留用户输入→读最新版本→显示差异再确认；不能自动覆盖重试。 |
| F22-08 保存后的调查影响 | 让人工事实进入后续判断 | 保存只确认人工结果；后续手动准备／启动 C 可引用，故事和助手后续可见；不自动改当前判断或结案 | 部分实现 | [E40](http-handoff/endpoints.md#e40)、[E11](http-handoff/endpoints.md#e11)、[E13](http-handoff/endpoints.md#e13)。保存H仅生成修订；显式下一轮冻结新版本；自动C6复核和故事/Q仍未接。 |

### 处理活动、评论与附件

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F23-05 处理活动与目标 | 交接时说明谁做过什么 | 展示管理、成员、人工变更的时间、操作者、前后值、结果；展开目标并回原对象 | 已实现 | [E17](http-handoff/endpoints.md#e17)。读取匹配活动与目标前后值，按next_offset分页。 |
| F24-01 评论阅读与提交 | 记录协作说明，不混入 AI 结论 | 查看作者、正文、时间；提交后形成同案备注，不能自动作为已核实事实 | 未实现 | 暂无对应接口。Case评论完整读写无API；A/I records/comments只读不能充当Case评论服务。 |
| F24-02 已有附件查看／下载 | 回看补充资料的原件 | 查看文件名、类型、大小及归属，按受控入口打开本案附件；无附件与未接入分别显示 | 部分实现 | [E15](http-handoff/endpoints.md#e15)、[E16](http-handoff/endpoints.md#e16)。已知工件正文可读；通用附件目录/文件下载闭环未实现。 |
| F24-03 上传补充附件 | 让协作材料能持久交接 | 提交后才出现真实文件记录，并能再打开；失败不得显示已上传 | 未实现 | 暂无对应接口。无上传或附件保存接口。 |

### Case 案件助手

这是现有设计中的同案能力，全部保留为未交付项，不因本轮补写清单而启动开发。Q 的提问、保存、采用三个正式服务入口目前返回 501。

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F26-02 同案统一对话 | 各页面提问能接续同一上下文 | 页头／故事／结果／图进入同案对话；切案切换历史与范围，不串案 | 未实现 | [E19](http-handoff/endpoints.md#e19)。无正式会话目录/历史读写；预留结构不算可用。 |
| F26-03 范围选择与问题编辑 | 让 AI 知道要回答什么 | 可带全案、告警、Run、对象、人工事实；范围展示且问题可编辑；打开不执行 | 未实现 | [E19](http-handoff/endpoints.md#e19)。产品范围选择尚无DTO字段，当前多传scope将422。 |
| F26-04 建议问题 | 帮用户发现值得问的问题 | 历史对话存在时仍显示建议；点击只填输入框，由用户修改后发送 | 未实现 | 暂无对应接口。无建议问题生成API。 |
| F26-05 发送与只读分析 | 直接处理用户问题 | 发送后分析已有材料或按需查询，显示进度、结论、依据、影响及限制；需澄清则询问 | 未实现 | [E19](http-handoff/endpoints.md#e19)。发送返回501，无真实工具或模型调度。 |
| F26-06 失败与人工事实续接 | 不把失败当无风险，并补齐缺事实 | 显示未查／失败原因；需要人确认时建立事项，收到事实后续接原问题 | 未实现 | [E19](http-handoff/endpoints.md#e19)。问答执行和人工续接未实现；现有任务不自动恢复Q。 |
| F26-07 保存到调查记录 | 保留有价值的答复用于交接 | 确认标题与结论后冻结问题、回答及材料；进入故事／历史；取消不保存、重复不重建、不再执行 | 未实现 | [E20](http-handoff/endpoints.md#e20)。save返回501，不会保存/采用/重跑。 |
| F26-08 引用与继续追问 | 复核回答并延续问题 | 展开当时来源，允许回查当前任务但保留旧快照；新问题按新范围处理 | 未实现 | [E19](http-handoff/endpoints.md#e19)、[E20](http-handoff/endpoints.md#e20)。尚无冻结Q引用与连续追问服务。 |

### 共用的调查运行详情

Case 内从调查历史进入；A/I 从各自分析目录进入；全局列表用于跨主体回查。五个主视图固定为调查发现、AI 分析、查询与证据、调查关系图、报告与响应。执行明细是 AI 分析的次级入口。

### 调查运行列表

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F14-07 跨主体运行目录 | 找到没有 Case 或不同案件的既有执行 | 按主体、轮次、状态、时间查看并打开指定 Run；不将候选 Case ID 当实际业务案 | 已实现，需组合接口 | [E26](http-handoff/endpoints.md#e26)、[E27](http-handoff/endpoints.md#e27)、[E02](http-handoff/endpoints.md#e02)、[E22](http-handoff/endpoints.md#e22)、[E23](http-handoff/endpoints.md#e23)、[E10](http-handoff/endpoints.md#e10)。分页枚举有权读取主体→各分析/历史→按真实run_id去重；无全局Run接口，不能保证未编目运行的全量覆盖。 |
| F15-02 运行统计和卡片摘要 | 了解已有运行及其交付情况 | 统计运行记录、部分交付、未升级调查及关联 Case；卡片展示状态、输入数量、时间、摘要和 Run ID；当前原型没有搜索筛选控件 | 已实现，需组合接口 | [E22](http-handoff/endpoints.md#e22)、[E23](http-handoff/endpoints.md#e23)、[E10](http-handoff/endpoints.md#e10)、[E12](http-handoff/endpoints.md#e12)。统计已聚合目录并标范围/观察时间，不能声称全系统统计。 |

### 调查发现

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F16-03 目标、结论、发现与限制 | 先知道这一轮得到什么及哪些仍未查清 | 阅读原始范围、结论（含未解决问题）、依据、变化与案件影响；未解决问题保留在本轮结论中，无独立处理状态；系统收尾和模型判断分别标明 | 已实现，需组合接口 | [E14](http-handoff/endpoints.md#e14)、[E15](http-handoff/endpoints.md#e15)、[E24](http-handoff/endpoints.md#e24)、[E25](http-handoff/endpoints.md#e25)。按主体读正式结果/交付原件，questions随本轮结论；系统收尾和业务判断分开。 |
| F15-03 执行、交付及用量 | 判断结果可用程度及停止原因 | 状态、完整性、覆盖、用量分别展示；unknown 保持待核实，有工件不代表成功 | 已实现，需组合接口 | [E12](http-handoff/endpoints.md#e12)、[E32](http-handoff/endpoints.md#e32)。state/delivery/usage/时间及unknown独立展示，费用缺失不填0。 |
| F12-04 查看当轮原始输入 | 确认这轮究竟调查了谁 | 查看被冻结的告警版本、范围和人工事实；当前新增成员不并入旧轮 | 已实现，需组合接口 | [E12](http-handoff/endpoints.md#e12)、[E18](http-handoff/endpoints.md#e18)、[E15](http-handoff/endpoints.md#e15)、[E32](http-handoff/endpoints.md#e32)、[E33](http-handoff/endpoints.md#e33)。当轮input_artifact_id和冻结材料/任务版本，不加载当前替代历史。 |
| F22-09 用户创建人工任务／询问结果 | 对结论中需要核实的内容开展后续工作 | 需要人工确认时由用户创建任务并带来源；也可打开助手带本轮范围，明确发送后处理；不自动生成任务，不设置问题转派或关闭流程 | 部分实现 | [E38](http-handoff/endpoints.md#e38)、[E19](http-handoff/endpoints.md#e19)。用户从结论手动创建任务并带来源；询问结果仍501，不自动转任务。 |

### AI 分析与执行明细

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F17-01 已保存分析过程 | 理解结论如何从材料得到 | 阅读已保存分析、采用材料与引用；正式 AI 保存记录应显示当时问题及回答 | 部分实现；现有材料可组合读取 | [E12](http-handoff/endpoints.md#e12)、[E32](http-handoff/endpoints.md#e32)、[E15](http-handoff/endpoints.md#e15)、[E33](http-handoff/endpoints.md#e33)。按真实步骤/工件阅读已保存分析；Q记录缺失。 |
| F17-02 步骤账本 | 定位哪一步失败或未产出 | 按本轮顺序和父子层级展开步骤、错误、状态及来源；不把运行结束当分析全通过 | 已实现，需组合接口 | [E12](http-handoff/endpoints.md#e12)、[E32](http-handoff/endpoints.md#e32)。steps按seq/parent_step_id组织；检查截断，无进一步步骤分页API。 |
| F18-01 步骤输入／输出原件 | 复核实际收到与返回的内容 | 打开所选工件，区分初始输入、步骤参数、复用原件；正文受限／缺失分别提示 | 已实现，需组合接口 | [E12](http-handoff/endpoints.md#e12)、[E32](http-handoff/endpoints.md#e32)、[E15](http-handoff/endpoints.md#e15)、[E33](http-handoff/endpoints.md#e33)。步骤引用工件ID→正文，依父主体取对应路径。 |
| F17-03 当轮能力与投入 | 解释该轮能做什么和实际花费 | 阅读冻结能力摘要、调用和已知用量；未知费用不记零，不按当前配置回算旧轮 | 已实现，需组合接口 | [E12](http-handoff/endpoints.md#e12)、[E32](http-handoff/endpoints.md#e32)。execution_summary/usage/tool_calls保留未知值；能力快照不是质量证明。 |

### 查询与证据

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F28-01 查询目录和结果 | 知道访问了哪些来源 | 按实际工具步骤查看来源、参数、状态、返回及错误，定位同轮请求／结果 | 已实现，需组合接口 | [E12](http-handoff/endpoints.md#e12)、[E32](http-handoff/endpoints.md#e32)、[E15](http-handoff/endpoints.md#e15)、[E33](http-handoff/endpoints.md#e33)。步骤中的工具调用与输入/输出工件组合查询目录。 |
| F28-02 查询状态区分 | 避免“没查到”被误读为安全 | 分别显示未执行、跳过、失败、成功零行、复用；来源可用不代表本轮查过 | 已实现，需组合接口 | [E15](http-handoff/endpoints.md#e15)、[E33](http-handoff/endpoints.md#e33)。按真实工具回执分未查/失败/成功空/有结果；HTTP200不等于查询成功。 |
| F18-02 摘要、原文与引用 | 让引用能够逐项复查 | 打开证据原件、冻结材料或引用路径；只有摘要就说明，不换其他轮材料 | 已实现，需组合接口 | [E15](http-handoff/endpoints.md#e15)、[E16](http-handoff/endpoints.md#e16)、[E18](http-handoff/endpoints.md#e18)、[E31](http-handoff/endpoints.md#e31)、[E33](http-handoff/endpoints.md#e33)、[E34](http-handoff/endpoints.md#e34)、[E35](http-handoff/endpoints.md#e35)。引用→所属原件读取，保留摘要与完整正文的差别。 |

### 调查关系图

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F19-03 历史图只读与来源 | 重现当轮实际关系范围 | 读所选 Result 的图、节点和边，聚焦／回查来源；缺图显示缺图 | 已实现，需组合接口 | [E14](http-handoff/endpoints.md#e14)、[E15](http-handoff/endpoints.md#e15)。graph_artifact_id→历史图，标冻结范围且只读。 |
| F19-04 转入当前案件探索 | 继续查线索而不改历史 | 明确离开历史图进入案件关系图；历史图不扩展、不重写，关联线不证明攻击因果 | 未实现 | 暂无对应接口。当前探索服务未实现；不能在历史图上偷偷改Case成员。 |

### 报告与响应

| 功能 | 为什么需要 | 操作后结果与回查位置 | 后端实现状态 | 接口及实现说明 |
| --- | --- | --- | --- | --- |
| F16-04 阅读报告及收尾说明 | 向同事交接该轮结果 | 打开本轮报告；无正式 Result 时仍可读已保存系统说明及失败材料，不补造结论 | 已实现，需组合接口 | [E14](http-handoff/endpoints.md#e14)、[E15](http-handoff/endpoints.md#e15)。report_artifact_id及delivery正文→报告，系统closing_note独立显示。 |
| F18-03 下载已有报告 | 便于离线交接和留存 | 下载已保存内容，保持轮次和来源；缺报告不能导出伪造的完整成果 | 读取已实现；下载由调用方处理 | [E14](http-handoff/endpoints.md#e14)、[E15](http-handoff/endpoints.md#e15)。读取已保存报告content_text→浏览器Blob下载；无单独文件下载API，不调用模型重写。 |
| F27-02 响应建议卡片 | 让建议目标、理由和影响可评估 | 展示具体动作、目标、依据、审批要求；未记录审批要求与无需审批分开 | 已实现，需组合接口 | [E14](http-handoff/endpoints.md#e14)、[E15](http-handoff/endpoints.md#e15)、[E24](http-handoff/endpoints.md#e24)、[E25](http-handoff/endpoints.md#e25)。按本轮recommendations展示建议目标/依据，不能显示为已执行。 |
| F27-03 审批与意见 | 明确是否允许某个动作 | 按具体目标批准／拒绝并说明；批准绑定动作／目标，改变须重审；拒绝后修改重提，批准仅变待执行，D06 已确认 | 未实现 | 暂无对应接口。审批和意见链由业务后端承接，本服务无批准或执行接口。 |
| F27-04 执行记录与回执 | 确认实际做了什么 | 按动作身份关联回执；执行不明先核回执，不自动重复；明确失败后由人决定重试，无回执不宣称已处置 | 部分实现 | [E30](http-handoff/endpoints.md#e30)、[E15](http-handoff/endpoints.md#e15)、[E33](http-handoff/endpoints.md#e33)。responses及原件读取已有回执；Case真实执行闭环由业务后端，unknown不能自动重试。 |

## 操作后的结果必须在哪看

| 操作 | 保存或执行的结果 | 用户应能回查 | 当前边界 |
| --- | --- | --- | --- |
| 建案／加关联／移动 | 案件身份、成员范围和待启动记录 | 成员、资料、概览、活动 | 命令、详情、活动读取已实现，使用返回的真实ID回查 |
| 准备／启动 | 前者保存待启动记录；后者冻结输入并执行 | 概览、历史、指定 Run | 当前需明确启动；未启用自动接续 |
| 完成人工任务 | 同任务的新修订、结果及声明范围 | 任务当前／历史版本，后续 C 的冻结输入 | 任务版本传递已验；助手未实现 |
| 人工告警反馈 | 告警意见及按规则产生的处理变化 | 告警概况、时间线 | D02规则已确认；告警反馈写接口未实现 |
| 保存助手回答 | 正式 AI 记录和当时依据 | 历史、故事、原问题与引用 | 接口返回501，未实现 |
| 保存探索／加入成员 | 前者保存画布；后者改变成员 | 探索恢复／成员及概览 | 探索保存未实现；成员关联接口可用 |
| 审批／执行响应 | 前者许可；后者真实动作及回执 | 同一建议卡和回执 | 真实链路未接，不能混为处置成功 |

## 已规划但尚未实施的更新行为

负责人已明确先完成[固定范围调查](../../openspec/changes/complete-socai2-investigation-chain/fixed-flow-plan.md)，再推进[更新和流式](../../openspec/changes/schedule-streaming-investigation-updates/proposal.md)。下列是已有后置规划，不覆盖上表当前手动行为，也不列入本轮待批准规则。

| 已确认的目标方向 | 将来影响的页面 | 当前实现状态 |
| --- | --- | --- |
| 新告警自身分诊，实质材料／成员／采用结果变化合并到相关 I／Case 待办 | 事件诊断、调查概览、历史 | 调度待办及自动接续未实施，Agents自动分析关闭；入站/Fusion/数据整理运行 |
| 整事件关联的活动 Case 跟随事件新成员；单告警关联不扩大，人工移出不加回，已结束案不自动重开 | 成员、覆盖、概览 | 自动跟随未实施 |
| 每对象单活跃、一个合并待办；运行输入冻结，后续变化进入下一轮 | 概览、历史、Run 输入 | 现有 Case 手动单活跃与冻结已实现；统一队列未实施 |
| 只有有效 H 变化走 C6 综合复核，同时有材料／成员变化则完整调查 | 人工任务、当前判断、调查历史 | 自动反馈复核未实施，当前保存 H 后仍手动准备／启动 |
| 复核复用原调查知识，历史知识维护进入低优先级待办 | 单轮材料及处理记录 | 现有知识读取／同步另有交付；上述队列化方式未实施 |

## 功能范围和未完成项

D01–D07已确认；未实现能力按上表及[接口实施计划](../../docs/investigation/http-implementation-plan-20261112.md)推进。资产、人员目录、外部日志等由业务后端提供，不复制旧AiSOC的平台功能和数据表。页面只用于测试，功能完成情况只按接口能力说明。

## 跳转与关联规格

原有 J01–J14 保留在[技术附录](frontend-data-navigation-contract.md#跳转与关联规格)。每条主功能沿原 F 编号查字段及跳转；任何入口必须保留主体与 Run 身份，缺值、无权、未找到时停止错误下钻并给返回入口。

## 案例签收

固定四案及逐字段样例保留在[技术附录案例签收](frontend-data-navigation-contract.md#案例签收)，仅用于复现原始读取、跳转和空态，不把旧案例更新成新通过结论。本轮只做文档整理，没有运行模型或业务写入，也没有完成新的产品页面验收。

## 实现状态依据

| 编号 | 资料及可以证明的范围 |
| --- | --- |
| E1 | [当前前后端交接](../../FRONTEND_BACKEND_HANDOFF.md)、[页面数据合同](../../docs/investigation/socai2-page-data-handoff-20261106.md)、[字段样例](page-field-samples.md)：已存字段、来源与读取；具体批次保留日期 |
| E2 | [Case/H 直接验收](../../openspec/changes/archive/2026-11-11-enable-case-human-http-flow/validation.md)、[交付回执](../../docs/operations/evidence/case-human-http-20261111-01/delivery-summary.json)：本机两轮／H 修订传递与生产正常身份写读；不证明产品完整交互 |
| E3 | [现有原型入口](../../prototypes/security-pages-v2/index.html)、[服务模式页面](../../prototypes/security-pages-v2/service-workspace.js)：页面已接线范围；未开放导航按实际代码列出 |
| E4 | [产品需求](../../docs/design/alert-incident-case-product-requirements.md)、[页面约定](../../docs/design/ui-discussion-principles.md)、[上一轮产品评审](../../docs/design/investigation-product-page-review-20261112.md)：现有设计目的及本次拆分来源 |
| E5 | [当前问题](../../docs/investigation/current-issues.md)、[当前调查表](../../docs/investigation/investigation-table-scope.md)：未完成项、模型质量与 28 表边界；预留表不等于已完成功能 |
