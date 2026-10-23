# 告警与调查模块 V1：页面、数据库取数与 HTTP 接口

更新：2026-10-23。本篇是当前唯一交接主文档。按“页面功能与字段 → 数据库表 → 功能取数与实例 → 已有HTTP接口”的顺序组织，产品、前端和业务后端可以分别阅读对应章节。

| 章节 | 回答的问题 |
| --- | --- |
| 第1章 页面、功能与展示字段 | 分几个页面？每页做什么？每个功能显示哪些信息？ |
| 第2章 当前相关数据库表 | 数据库在哪里？有哪些表？表之间如何关联？ |
| 第3章 按功能取数并举例 | 某项页面信息从哪一列/JSON取？如何查？实际能得到什么？ |
| 第4章 已有HTTP接口 | 已有哪个接口可用？请求什么、返回什么、有哪些限制？ |
| 第5章 补充说明 | 状态和空值口径、版本边界、验证记录、V1待补项及附件 |

业务后端可直接查数据库并自行聚合；已有HTTP作为另一种读取方式保留。本文的页面设计不代表前端已实现，本地已测增量不代表已部署。

## 1. 页面、功能与展示字段

### 1.1 第一版分四个页面

| 页面 | 用户主要任务 | 入口与页面关系 |
| --- | --- | --- |
| 告警列表 | 判断当前有哪些告警，优先处理哪一条 | 默认入口；点击告警标题进入详情 |
| 告警详情 | 看清来源事实、对象、分诊理由和当前处理结果 | 从列表进入；有关联调查时直接进入对应Run |
| 调查列表 | 查看实际调查的执行状态、完成度与结果 | 独立列表，或从告警查看关联调查历史 |
| 调查详情 | 阅读调查结论、已有材料、过程、缺口和报告 | 以Run ID定位；不要求自动调查必须先创建Case |

A01—A40是告警字段编号，I01—I50是调查字段编号。第3章使用相同编号对应数据库取法。图、报告、过程作为调查详情内的页签；第一版不再拆出单独的实体页、工作队列页、图页或报告页。

### 1.2 页面一：告警列表

布局：顶部统计 → 筛选与搜索 → 告警表格 → 可选详情侧栏。默认严重程度优先、同级按入库时间倒序。

| 功能 | 功能中展示/输入的字段 | 行为 |
| --- | --- | --- |
| 当前范围统计 | 告警总数、严重数、高危数、未解决数 | 使用完整筛选结果的计数，不使用当前页条数 |
| 筛选与搜索 | 严重程度、处理状态、来源、发生时间起止、对象值、关键词 | 关键词范围为标题/摘要/ID；数据库可自行实现，已有HTTP限制见第4章 |
| 排序和分页 | 排序方式、页码、每页条数、总条数 | 默认严重程度优先；另一选项为入库时间倒序 |
| 告警行 | A01—A12，见下表 | A01—A09默认展示；A10/A11可选列，负责人接通后启用 |
| 查看与定位 | 告警ID、关联Run ID | 查看告警/调查、复制ID；有调查关联才显示跳转 |
| 人工工作队列操作 | 负责人、处理动作、操作理由/回执 | 认领/转派/关闭/暂缓暂不作为本版必须交付；现有接口列于第4章 |

| 编号 | 展示字段 | 展示规则 |
| --- | --- | --- |
| A01 | 告警标题 | 标题一至两行，可点击进入详情。 |
| A02 | 告警来源 | 独立显示来源系统名称/代码，不能用接入类型替代。 |
| A03 | 发生时间 | 发生时刻，显示秒和时区；保留原时间用于复制。 |
| A04 | 严重程度 | 等级中文标签和颜色；保留原枚举，不替换成AI置信度。 |
| A05 | 关联对象 | 主机优先，附账号/IP；最多两个值，其余“+N”；名称为关联对象。 |
| A06 | 来源摘要 | 标题下显示来源描述，最多两行，可展开；与AI分析摘要分开。 |
| A07 | AI 分诊结论 | 良性真阳性/误报/待复核等标签；旁边可查看首次分诊理由。 |
| A08 | 处理状态 | 当前告警业务状态，与分诊结论和调查完成度分列。 |
| A09 | 调查状态/入口 | 显示是否启动调查、运行中/部分完成/失败及查看入口；仅分诊不能标调查完成。 |
| A10 | 告警 ID | 默认短ID，支持复制完整canonical Alert ID。 |
| A11 | 分诊置信度 | 可选列，百分比并注明“AI分诊置信度”，不叫风险分。 |
| A12 | 负责人 | 需要人员目录映射后启用；没有负责人显示“未分配”。 |

小屏保留标题、来源、发生时间、等级、状态，其余放详情。当前不放MTTR、自动处置成功率等缺完整验收依据的运营卡片。

### 1.3 页面二：告警详情

布局：头部标题/等级/业务状态/分诊结论/ID，正文为“概览 / 处理记录 / 原始数据”。头部复用列表字段，不重新定义同名信息。

| 功能区 | 展示字段 | 交互和含义 |
| --- | --- | --- |
| 来源与时间 | A13—A23 | 来源身份、规则、事件引用、各类时间、来源摘要、分类标签 |
| 对象与技术信息 | A24—A30 | 主机/账号/IP、源目的角色、进程命令、IOC、MITRE、Raw与分组/Case |
| 融合解释 | A31—A32 | 融合说明、评分和因子；与来源摘要分区 |
| AI首次分诊 | A33—A36 | 结论、置信度、时间、理由、自动关闭、发现与建议 |
| 资料覆盖 | A37—A40 | 情报、资产/身份/漏洞/历史、查询范围与未配置来源 |
| 处理记录 | 处理时间、事件类型、执行者、摘要、关联Run ID | 查看实际分诊/调查记录；业务发生时间与处理时间分开 |
| 操作与跳转 | 当前告警ID、已有Run、有关联的Case | 查看调查/复制/查看Raw为基础；人工启动与关闭等功能依各自操作验收开放 |

| 编号 | 展示字段 | 展示规则 |
| --- | --- | --- |
| A13 | 来源系统、接入类型 | 来源系统与接入类型分开；未知接入类型显示“未提供”。 |
| A14 | 上游告警 ID、连接器 ID | 上游告警ID与连接器ID分别显示和复制；空值不补造。 |
| A15 | 关联来源事件 ID | 逐个显示来源事件引用和外部引用；不能按引用数量称告警发生次数。 |
| A16 | 规则 ID / 规则名称 | 规则ID/规则名称；没有规则名称时保留ID。 |
| A17 | 发生时间 | 来源报告的告警发生时间。 |
| A18 | 本系统入库时间 | 本系统创建告警记录的时间；不叫上游采集时间。 |
| A19 | 首次/最近见到时间 | 记录的首次/最近见到时间；不能据此推断持续攻击时长。 |
| A20 | 最近更新时间 | 告警记录最近更新时间；与调查报告时间分开。 |
| A21 | 解决时间 | 实际解决时间；未解决显示“—”。 |
| A22 | 原始摘要 | 来源原始描述全文，可折叠；缺失显示“来源未提供摘要”。 |
| A23 | 分类/标签 | 分类和标签为可选信息；无值不编造分类或测试标签。 |
| A24 | 主机 / 用户 / IP | 主机、账号、IP按类型分组，显示类型和值，支持复制。 |
| A25 | 源 IP / 目的 IP | 源IP与目的IP分列；仅有IP集合时不猜角色。 |
| A26 | 进程名 / 命令行 | 来源上报的进程名/命令行；长命令折叠、支持复制。 |
| A27 | 目的端口、域名、URL、文件哈希 | 有值才显示目的端口、域名、URL、文件哈希；按来源适配。 |
| A28 | MITRE 战术/技术 | 显示MITRE战术/技术ID，名称未映射时保留ID；不视为完整攻击链。 |
| A29 | 来源完整载荷 | 原始载荷JSON折叠/复制；说明它是来源正文，不是整个Kafka信封。 |
| A30 | 融合分组 / 人工 Case | Fusion分组和人工Case分别列出；无Case显示“未关联”。 |
| A31 | 融合说明 | 单列“系统融合说明”，与来源摘要、AI理由分区。 |
| A32 | 融合评分及因子 | 显示融合置信评分及等级，展开因子名称、值、权重、贡献；不称恶意概率。 |
| A33 | AI 首次分诊 | 首次分诊结论、AI置信度、分诊时间。 |
| A34 | AI 分诊理由 | 分诊理由全文；明确为自动分析，不冒充人工确认。 |
| A35 | 分诊是否自动关闭 | 显示是否系统自动解决，并核对当前业务状态；冲突时提示待核对。 |
| A36 | 分诊发现/建议 | 分诊发现与建议分组；空建议显示未生成，不能标为已执行。 |
| A37 | IOC 检索状态 | IOC值/类型、查询来源、命中状态、匹配项、查询时间、外部覆盖。 |
| A38 | 资产/身份/漏洞/历史告警补充资料 | 资产、身份、漏洞、历史告警各自显示资料状态/来源/明细/截断情况。 |
| A39 | 上下文查询范围与新鲜度 | 显示当前查询的对象、时间范围、条数上限和查询时间。 |
| A40 | 外部历史 / UEBA | 显示外部历史/UEBA资料覆盖状态；未配置不能写成无异常。 |

来源摘要、系统融合说明、AI分诊理由、调查结论使用四个不同标题。人工发起调查采用已有Case入口；自动调查已经发生时直接看Run，不补建Case作为查看前置。

### 1.4 页面三：调查列表

列表以一次实际调查Run为一行。只有自动分诊、未进入调查的运行留在告警处理记录中，不计作深度调查。已进入调查但尚无报告的运行也必须显示。

| 功能 | 展示/输入字段 | 行为 |
| --- | --- | --- |
| 调查列表 | I01—I11 | 标题、来源、目标、触发方式、三种状态、时间、报告入口 |
| 筛选与排序 | 目标ID、执行状态、完成度、开始时间范围；最新开始时间优先 | 直查方按实际记录聚合；HTTP目前只支持部分条件和最近N条 |
| 运行历史 | 同一目标下的Run ID、开始时间、状态 | 每次独立运行分别保留，不能将旧报告放进新Run |
| 详情入口 | Run ID、关联告警/Case | 可以从自动告警直接进入调查详情 |

| 编号 | 展示字段 | 展示规则 |
| --- | --- | --- |
| I01 | 调查标题 | 调查名称从已确认目标标题组合；无名称时显示调查+短Run ID。 |
| I02 | Run ID / 关联目标 | Run ID、目标类型/ID、来源告警链接、有关联才展示Case链接。 |
| I03 | 触发方式 | 自动升级/人工发起/未知；缺统一来源时不凭模型名称猜测。 |
| I04 | 关联告警等级/来源 | 关联告警的等级和来源，作为处理优先级参考。 |
| I05 | 执行状态 | 运行中/执行结束/执行失败；只表示程序执行状态。 |
| I06 | 调查完成度 | 完整/部分完成/未提供；部分完成突出显示。 |
| I07 | 分析结论 | 显示当次调查结论；未形成时明确提示，不沿用首次分诊冒充。 |
| I08 | 开始/结束时间 | 开始时间、结束时间；运行中结束时间为“—”。 |
| I09 | 运行耗时 | Run总耗时，包含首次分诊；运行中可动态更新。 |
| I10 | 报告可用性 | 可查看报告/尚无报告/读取失败三种情况分开。 |
| I11 | 负责人/复核状态 | 预留人工接手信息；当前缺统一Run责任人/复核字段，不显示已复核。 |

执行状态、调查完成度、分析结论必须三列分开。负责人/复核信息未有统一持久字段时暂不作为有效筛选条件。

### 1.5 页面四：调查详情

头部展示标题、Run/Alert/Case关联、执行状态、完成度、结论、开始结束时间。主体按“概览 / 证据与关联 / 调查过程 / 报告”组织，用量折叠在运行信息中。

| 功能区 | 展示字段 | 页面用途 |
| --- | --- | --- |
| 概览与结论 | I12—I22 | 明确查什么、现有结论、停止原因、缺源与人工接手事项 |
| 证据与关联 | I23—I36 | 材料正文、实际查询、资料读取、关系图及引用状态 |
| 调查过程 | I37—I42 | 实际步骤、模型/工具记录、耗时、错误和留存范围 |
| 报告与运行信息 | I43—I50 | Markdown预览/下载、报告版本、Token、费用、模型和轮数 |

#### 1.5.1 概览与结论字段

| 编号 | 展示字段 | 展示规则 |
| --- | --- | --- |
| I12 | 调查目标与原告警快照 | 展示本次调查收到的来源告警快照；与当前告警记录区分。 |
| I13 | 调查对象范围 | 列出本次调查关联的主机、账号、源/目的IP和成员告警范围。 |
| I14 | 查询范围 | 展示每次查询的实际参数、图范围和窗口；缺绝对起止时不猜测。 |
| I15 | 调查结论与置信度 | 调查结论、分析置信度及其依据；与首次分诊分别展示。 |
| I16 | 调查摘要 | 现版可用确定性状态摘要；没有统一最终摘要字段时不从工具返回拼成AI结论。 |
| I17 | 现有分析记录 | 分析记录逐条折叠；可能包含过程、假设、错误，不统称已证实发现。 |
| I18 | 完成度与停止原因 | 完整性、停止原因、预算/错误提示；即使Run执行结束也保留部分完成提示。 |
| I19 | 缺失数据与覆盖限制 | 未提供的数据类型、覆盖说明、截断状态；作为人工接手的重要信息。 |
| I20 | 后续建议 | 后续核查建议；结构化建议为空时显示未生成。 |
| I21 | 实际执行动作 | 只有实际执行记录才显示动作、结果；建议不当作已隔离/已封禁。 |
| I22 | 根因与影响结论 | 根因/影响只有明确资料支持时才作结论；当前统一合同未具备，保留假设措辞。 |

#### 1.5.2 证据与关联字段

| 编号 | 展示字段 | 展示规则 |
| --- | --- | --- |
| I23 | 材料目录：类型、ID、时间、字节、hash、关联事件 | 材料类型、工件ID、时间、字节数、SHA256和关联步骤。 |
| I24 | 工件正文 | 打开已留存正文，按JSON/Markdown显示；区分无正文、读取失败、截断。 |
| I25 | 已查询工具、请求参数、返回预览 | 已执行工具名称、请求参数、旧版返回预览；不把预览称完整证据。 |
| I26 | 单次工具状态与保留内容 | 工具状态、可用性、调用ID/轮次、已保留返回和截断标记；本地已测，未上线。 |
| I27 | 单次工具留存定位 | 留存事件/工件定位、留存状态、缺口提示；本地已测，未上线。 |
| I28 | IOC 及情报覆盖 | IOC类型/值、来源、引擎数和实际返回评分；无外部判定不能显示安全。 |
| I29 | 知识、身份、组织记忆等读取状态 | 知识/身份/组织记忆/近期处置/技能源的读取状态与采用计数。 |
| I30 | 已采用知识引用 | 有值才列已采用知识引用、来源和引用定位；未命中显示空态。 |
| I31 | 告警关系图 | 本次告警关系图的节点、边、类型/标签；表示关联，不表示攻击因果。 |
| I32 | 关联可达范围 | 可达节点、类型分布、跳数和数量；不把不同类型节点总数称受害主机数。 |
| I33 | 候选告警链 | 候选告警链条、查询窗口和范围；空链明确“此范围未找到候选链”。 |
| I34 | Case 路径 | Case路径、状态和缺失原因；没有Case显示未关联。 |
| I35 | 图的范围与时点 | 图查询时点/范围；默认当次快照，当前查询另行标注。 |
| I36 | 证据—结论对应关系 | 结论与证据引用关系目前缺统一合同；不能用步骤关联自动画支持连线。 |

#### 1.5.3 调查过程字段

| 编号 | 展示字段 | 展示规则 |
| --- | --- | --- |
| I37 | 处理步骤 | 实际步骤的处理时间、类型、执行者、摘要和序号；只展示实际记录。 |
| I38 | graph 节点 | graph节点名称；旧版未留完整独立输入输出，不补造阶段结果。 |
| I39 | 模型调用 | 模型角色、实际解析模型、调用目的、耗时和已记录交换；节点数不等于调用次数。 |
| I40 | 输入/输出留存范围 | 输入/输出留存范围、截断标志、hash及正文；详细内容按权限展开。 |
| I41 | 工具处理耗时/状态 | 工具调用耗时与结构状态；旧版缺状态时明确未提供。 |
| I42 | 运行失败/部分完成提示 | 运行错误、停止原因和部分结果提示；错误字段空不等于调查完整。 |

#### 1.5.4 报告与运行信息字段

| 编号 | 展示字段 | 展示规则 |
| --- | --- | --- |
| I43 | Markdown 报告预览/下载 | Markdown报告预览/下载；始终保留本次Run及部分完成提示。 |
| I44 | 报告元信息 | 报告工件ID、生成记录时间、字节数、hash；支持追溯具体版本。 |
| I45 | Case 报告入口 | 有关联Case时可从Case打开本Run报告；无Case也能查看报告。 |
| I46 | 总 Token / 模型调用数 | Run总Token与实际模型调用数，分别标注。 |
| I47 | 首次分诊与后续调查用量 | 区分首次分诊和后续调查的用量，按实际记录展示。 |
| I48 | 费用及未计价情况 | 实测费用、估算费用、未计价调用数分开；无计价时不显示免费。 |
| I49 | 模型名称 | 模型角色别名与实际解析模型分别展示。 |
| I50 | 轮数与查询数 | 推理轮数、查询类别数、查询记录数各自命名，不当作证据条数。 |

图和报告默认读取当次Run快照；当前图查询另标时点。报告保留原文及部分完成提示，Markdown展示须过滤危险HTML。V1提供Markdown预览/下载，PDF不作本版前置。人工四节点与自动graph按实际记录显示，不强制所有Run出现同一组阶段卡片。

## 2. 当前相关数据库表

### 2.1 数据库位置与连接

| 项目 | 直接交接值 |
| --- | --- |
| 数据库类型 | PostgreSQL |
| 地址 / 端口 | `192.168.1.21:5432` |
| 数据库名 | `aisoc` |
| 表命名空间 | `public`；既有实际盘点按 `information_schema.columns.table_schema='public'` 读取，连接后也可用下方 SQL 确认 |
| 当前生产租户 | `f6a5c700-69b8-44fc-8238-609362fb1a9f` |
| 连接加密 | TLS，`sslmode=verify-full`，使用运维发放的 CA |
| 账号 / 密码 | 使用已授权的数据库查询账号；当前服务运行角色是 `aisoc_app`，不代表已经另行发放查询账号。凭据不放在文档中 |
| 现有配置位置 | 21 主机 `/opt/sting-aisoc-socai2/private/runtime.env` 及各服务受控 env；由运维交接所需连接信息，无需复制整个目录 |
| 完整字段目录 | [table-fields.md](table-fields.md)，[data-catalog.json](data-catalog.json)：实际盘点的25表428字段及约束 |

这些是当前项目库，不是20参考页面自己的数据库，也不是旧 `sting` 库或旧15432端口。沿用已发放连接即可；本次未创建数据库账号或更改权限。详细连接配置仍见 [configuration.md](configuration.md)。

```sql
SELECT current_database(), current_schema(), current_schemas(false);
SELECT to_regclass('public.alerts'), to_regclass('public.investigation_runs'),
       to_regclass('public.investigation_events'), to_regclass('public.investigation_artifacts');
```

查询时每个事务绑定租户，并在 SELECT 中显式加 tenant 条件：

```sql
BEGIN READ ONLY;
SELECT set_config('app.current_tenant_id', 'f6a5c700-69b8-44fc-8238-609362fb1a9f', TRUE);
-- SELECT ... WHERE tenant_id = 'f6a5c700-69b8-44fc-8238-609362fb1a9f'::uuid;
ROLLBACK;
```

`app.current_tenant_id` 是当前代码使用的变量名；只设置变量不能替代显式过滤。下面所有关联都包含租户，避免同名目标或历史资料串读。

### 2.2 六张核心表与关联关系

| 表 | 存什么 | 关键字段 / 如何关联 |
| --- | --- | --- |
| `public.alerts` | 告警基本信息、来源快照、融合说明、首次分诊投影、当前处理状态 | 主键 `id`；`tenant_id`；来源和首次快照在 `enrichment_data` |
| `public.investigation_runs` | 一次分诊/调查的运行信息、状态、起止时间、总用量 | 主键 `id`；`case_id` 是字符串目标，不是 Case 外键；另有 `raw_alert` |
| `public.investigation_events` | 首次分诊结论、调查完成度、处理步骤、工具调用记录 | `run_id → investigation_runs.id`；`kind` 区分事件；结构内容在 JSONB `payload` |
| `public.investigation_artifacts` | 调查结果 JSON、Markdown 报告、模型交换、链图快照、资料读取回执 | `run_id` 关联运行；可用 `event_id` 关联事件；`kind` 区分内容；正文在 TEXT `content` |
| `public.aisoc_run_costs` | 按 Run 和模型角色汇总的调用数、Token、费用来源 | `run_id`、`tenant_id` **为 TEXT**，关联 UUID 表时用 `r.id::text`、`r.tenant_id::text` |
| `public.aisoc_cases` | 人工 Case 的标题、状态、成员告警、责任与协作资料 | `id`；`alert_ids` 是 UUID 数组；自动调查可以没有 Case |

**报告正文直接查 `investigation_artifacts`：`kind='report_md'` 的 `content`。调查结果直接查同表：`kind='graph_result'` 的 `content`，解析成 JSON。** 不需要为了展示这两项再查 Kafka、Redis、Neo4j 或模型服务。

最常用的关系：

```text
同租户 alerts.id
  └─ 普通自动路径：investigation_runs.case_id = alerts.id::text
       （本次两例也可由 investigation_runs.raw_alert->>'id' 核对）
       ├─ investigation_events.run_id = investigation_runs.id
       ├─ investigation_artifacts.run_id = investigation_runs.id
       └─ aisoc_run_costs.run_id = investigation_runs.id::text

人工路径：aisoc_cases.id::text → investigation_runs.case_id
Case成员：alerts.id = ANY(aisoc_cases.alert_ids)，同时限定双方tenant_id
```

上图是两类已知入口，不是任意 Run 都适用的猜测规则。独立 graph 的目标还可能是 Fusion Incident。不要将所有 `run.case_id` 强转 UUID JOIN `aisoc_cases`。`alerts.enrichment_data.socai2_fusion.incident_id` 是融合分组，PG 没有供本流程使用的独立 `incidents` 主表。

### 2.3 调查工件类型

| kind | `content`内容 | 解析后的常用路径 |
| --- | --- | --- |
| `graph_result` | JSON文本，自动调查聚合结果 | `verdict/confidence/findings/investigation_depth/raw_alert/context_bundle` |
| `report_md` | Markdown正文 | 原字符串读取；不能`::jsonb` |
| `attack_chain` | 当次候选告警链/实体图快照 | `attack_chain.status`、`attack_chain.data.chain/entity_graph`、`attack_chain.query` |
| `attack_path` | 当次Case路径快照 | `attack_path.status/data/error` |
| `alert_graph` | 当次告警直接邻域/可达范围 | `alert_graph.data.neighbors/blast_radius` |
| `knowledge_base_read` | 知识读取回执 | `status/source/received_count/adopted_count/citations/cited_sources`等 |
| `identity_context_read` / `organisation_memory_read` / `recent_dispositions_read` / `tenant_skill_read` | 相应资料读取回执 | 各自`status/source`及实际返回的范围/采用记录；不同类型不是相同schema |
| `llm_prompt` / `llm_response` | 留存的模型输入/输出文本 | 原文；结合事件截断标志 |
| `graph_llm_exchanges` | graph模型交换JSON文本 | 按实际JSON结构读取，不假设每轮都有独立费用 |
| `tool_result` | 单次工具结果JSON文本 | `tool/args/call_id/iteration/status/available/result_text/result_truncated`，本地新版 |

同Run可能有多份同kind工件。回看指定结果先固定 `artifact_id`；需要“最新”时明确按`created_at DESC,id DESC`取一份，不跨Run拼正文。`size_bytes/sha256`用于正文校验，不是可信度评分。

### 2.4 补充资料表与其他存储

| 想进一步查什么 | 位置 / 连接方式 | 是否主页面取数前置 |
| --- | --- | --- |
| 资产/漏洞 | 同PG库 `assets`、`asset_vulnerabilities`；`alert_asset_correlations.alert_id/asset_id`关联；漏洞表`asset_id`关联资产 | 否。当前样例无匹配，先展示无资料 |
| 身份权限 | 同PG库 `identity_privilege`，同租户按`principal`匹配账号 | 否；不是调查模型自动创建的人事资料 |
| 历史告警 | 同PG库 `alerts`，按实体与event_time范围检索 | 可按产品需要直查，声明范围和上限 |
| 组织记忆/反馈/知识/技能源数据 | 同PG库 `aisoc_context_statements/aisoc_analyst_feedback/aisoc_kb_documents/aisoc_tenant_skills/aisoc_tenant_skill_versions` | 回看某Run采用了什么时，优先读该Run的`*_read`工件 |
| UEBA结果 | 同PG库 `ueba_entity_baselines/ueba_anomalies/ueba_peer_groups` | 当前生产样例无相关行；不把空记录当无异常 |
| 历史事件湖 | ClickHouse `192.168.1.21:9000`（native）/`8123`（HTTP），库表`aisoc.raw_events` | 需要查事件原文再接；RawAlert不保证向该表生成历史事件 |
| 当前实时关系图 | Neo4j `bolt://192.168.1.21:7687`；Alert/Host/User/IOC/Technique等节点 | 回看既有Run不需要，PG已有当次图工件；当前图查询另按图合同 |
| TI检索/向量 | OpenSearch `192.168.1.21:9200`的`socai2-threatintel-*`；Qdrant `192.168.1.21:6333`的`socai2_threatintel_*` | 主页面不直接依赖；调查已用到的返回看工件 |
| Kafka/Redis | 原输入/运行和TTL状态 | 不作为历史页面结果主库；不用从消息或Redis重拼已入PG的报告 |

完整支撑表字段、图/湖限制沿用 [database.md](database.md)。需要复现当前补充查询时可参考 [processing_context.py](../../../services/api/app/services/processing_context.py)，而不是推测HTTP返回键都是数据库列。

## 3. 按功能从数据库取数，并给出实例

第3.1—3.2节逐项对应页面字段；第3.3节说明需要聚合而不是直接读列的信息；第3.4节用已经处理过的两条合成告警演示取数。先用租户和Alert/Run定位，再读取具体字段，避免将不同Run的资料拼在一起。

### 3.1 告警功能与字段取数映射

为避免重复长路径，定义三个读取表达式（只是本文简写，不是新列或视图）：

```sql
-- a 表示 public.alerts
-- F：来源身份、IOC检索、分组及首次交付材料
a.enrichment_data -> 'socai2_fusion'
-- S：首次融合时保存的来源告警快照
a.enrichment_data #> '{socai2_fusion,delivery_snapshot,fused,alert}'
-- T：本Run首次分诊事件
-- public.investigation_events WHERE kind='triage_verdict'，读取 payload
```

下表 ID 对应第1.2—1.3节的 A01—A40；同一信息在列表/详情重复时合并列出。

| 页面信息 / ID | 表和具体字段或 JSON 路径 | 当前数据说明 |
| --- | --- | --- |
| 标题、来源摘要、告警ID A01/A06/A10/A22 | `alerts.title / description / id` | 两例实值；description 是来源描述 |
| 来源系统 A02/A13 | `alerts.enrichment_data #>> '{socai2_fusion,identity,source}'` | 两例 `v1-functional-test`；**没有 alerts.source 列** |
| 接入类型、来源告警/连接器ID A13/A14 | `alerts.connector_type`；F.`identity.source_alert_id/connector_id`；另有 `alerts.connector_id` 列 | 来源告警ID有值；本例接入类型/连接器ID为空 |
| 发生、入库、首次/最近出现、更新时间 A03/A17—A20 | `alerts.event_time / created_at / first_seen / last_seen / updated_at` | 均有值；不要混用时间语义；`first_seen_at` 是另一个首次人工认领/确认时间字段（当前claim路径写入，非页面查看或自动分诊时间） |
| 解决时间 A21 | `alerts.resolved_at` | 自动关闭例有值；未关闭例为空 |
| 等级、分诊结论、业务状态 A04/A07/A08 | `alerts.severity / disposition / status` | 分别展示；首次结论原件再查 T.`verdict` |
| AI分诊置信度、理由 A11/A33/A34 | `alerts.ai_score / ai_summary`；准确阶段字段 T.`confidence/rationale/verdict`，时间为事件 `ts` | 95%/85%为分诊置信度；理由优先结构T，不解析拼接摘要 |
| 负责人 A12 | `alerts.assigned_to_id / assigned_at` | 两例均未分配；姓名需接人员目录，本批未核人员表映射 |
| 来源事件引用 A15 | `alerts.source_event_ids / external_id` | 引用ID不是事件正文；不能把数组长度当发生次数 |
| 检测规则 A16 | S.`rule_id/rule_name`；数据库另有 `alerts.rule_id/rule_name` | 本次已确认S中rule_id有值；不据列存在宣称直接规则列已填满 |
| 分类、标签 A23 | `alerts.category / tags`；首次来源标签另在S.`tags` | 本例当前tags空而S.tags含synthetic，两个口径不能混用 |
| 主机、用户、IP、实体 A05/A24 | `alerts.affected_hosts / affected_users / affected_ips / entities / iocs` | 有值；entities/iocs保留type/value；页面group/label/pivot是组装信息 |
| 源IP、目的IP A25 | S.`src_ip/dst_ip` | 有方向；不要从affected_ips顺序推断源/目的 |
| 进程、命令、端口及其他扩展 A26/A27 | `alerts.raw_event ->> 'process_name'/'command_line'/'destination_port'`；S.`domain/url/file_hash` | 这两例的来源扩展有相应值，不是全部来源统一字段 |
| MITRE战术/技术 A28 | `alerts.mitre_tactics / mitre_techniques` | 技术ID是映射，不代表完整攻击链 |
| 原始数据 A29 | `alerts.raw_event`；完整首次来源快照另查S | raw_event不是整个Kafka信封 |
| Fusion分组、Case A30 | F.`incident_id`；`alerts.case_id` | 两例有Fusion Incident，无Case |
| 融合说明/评分因子 A31/A32 | `alerts.narrative / confidence / confidence_label / confidence_rationale` | 与AI置信度分开；直查旧行narrative空时不触发HTTP的懒生成 |
| 是否自动关闭 A35 | T.`auto_closed` + `alerts.status/resolved_at` | 首次处理事实与当前业务状态联合看 |
| 分诊发现/建议 A36 | T.`findings/proposed_actions`；`alerts.ai_recommendations` | 本例结构建议为空；HTTP recommended_actions是归一化输出，无同名列 |
| IOC查询/覆盖 A37 | F.`ioc_lookup`，内含`indicators/status/scope/matches/checked_at/external_status` | no_match仅适用于已查来源；未配置外部情报不等于安全 |
| 调查入口/最新状态 A09 | runs + events + artifacts，见第3.2节 | 无独立latest_investigation列，接入方按Run关联后聚合 |
| 资产/身份/漏洞/历史告警 A38 | `assets`、`alert_asset_correlations`、`identity_privilege`、`asset_vulnerabilities`、历史`alerts` | 连接键和字段见第2.4节；本租户样例未匹配这些补充资料 |
| 当前查询范围、新鲜度、外部历史/UEBA状态 A39/A40 | HTTP `processing-context` 执行时生成；没有同名持久结果表 | 直查方可按自己的查询范围展示；要复现原返回语义可参考原服务函数，不能SELECT一个不存在的processing_context表 |

告警列表排序、关键词、来源、时间、对象过滤可以由接入方直接在 `alerts` 查询上实现。现有 HTTP 的 search 未生效、列表缺source等限制保留记录，**不阻止本次按表直查**。统计要使用与列表一致的租户及过滤条件。

### 3.2 调查功能与字段取数映射

约定 `r=investigation_runs`、`e=investigation_events`、`k=investigation_artifacts`；`G` 为同Run `kind='graph_result'` 工件的 `content::jsonb`；`GE` 为 `kind='graph_result'` **事件**的 `payload`。不要把TEXT工件当JSONB列直接用箭头，也不要把Markdown转成JSON。

| 页面信息 / ID | 表和具体字段 / 取法 | 当前数据说明 |
| --- | --- | --- |
| 标题、Run/目标、等级/来源 I01/I02/I04 | `r.id/case_id/raw_alert/alert_summary`；关联当前`alerts`或已确认的`aisoc_cases` | 显示标题可取目标title；不存在统一的r.title/target_type列 |
| 触发方式 I03 | e的`triage_started/triage_verdict`及T.`recovery`，结合已知入口 | 自动两例已确认；无统一trigger_type列，其他来源不猜 |
| 运行状态/时间/耗时 I05/I08/I09 | `r.status/error/started_at/completed_at`；耗时为时间差 | completed只表示运行结束；Run耗时包含首次分诊 |
| 调查完成度 I06/I18/I42 | GE.`completion`；G.`budget_exhausted/budget_exhausted_reason/error` | **完成度在事件payload**，本例G本身没有completion键 |
| 调查结论/置信度 I07/I15 | G.`verdict/confidence/confidence_basis` | partial例needs_review/0.19，不覆盖T的0.85 |
| 报告是否可读 I10 | 同Run k.`kind='report_md'`，检查`content/blob_ref` | 有目录项不保证正文已可读取；两例中仅调查例有MD |
| 调查负责人/人工复核 I11 | 当前无统一Run级责任人/复核持久字段 | 不能用Case负责人或告警状态冒充人工复核结论 |
| 当次告警/对象/查询范围 I12—I14 | G.`raw_alert`；e工具调用的`payload.args`；G.`context_bundle.attack_context.query_scope` | 用快照区分当前Alert；没有统一所有查询的绝对起止字段 |
| 总摘要/分析记录 I16/I17 | G.`findings`；当前无统一final_summary | findings含过程/判断/错误，不全是已确认事实；depth.narrative本例为工具JSON，不作总摘要 |
| 缺源和停止交接 I19 | G.`investigation_depth.unavailable_data/coverage_notes/truncated`；本地另有`stop_reason/error` | 旧生产和本地新版字段分别处理 |
| 建议/执行动作/根因 I20—I22 | G.`proposed_actions/executed_actions`；根因目前无统一已验证合同 | 本例动作为空；人工阶段状态不保证独立持久化，见第3.3节 |
| 材料目录/正文 I23/I24 | k.`id/kind/created_at/event_id/sha256/size_bytes/content/blob_ref` | content内可有JSON或MD；本次21份正文已核字节/hash |
| 工具调用/旧返回预览 I25/I41 | e中`kind='tool_call'`，`payload.tool/args/result_preview`、`duration_ms` | 旧生产预览约200字符，不是完整返回 |
| 新版单次工具结果 I26/I27 | k中`kind='tool_result'`的JSON；G.`investigation_depth.tool_trace/ledger_gaps` | **本地已测未发布**；用相同ledger表，没新增tool_results表 |
| IOC增强 I28 | G.`ioc_enrichments` | 值对应各IOC；来源空/engines=0不代表良性 |
| 资料读取/已采用引用 I29/I30 | k中五类`*_read`工件的JSON，具体kind见第2.3节 | 本例有回执、无匹配知识；回执不是实时源表内容 |
| 关联图/候选链/Case路径 I31—I35 | k中`alert_graph/attack_chain/attack_path`；G.`context_bundle.attack_context.query_scope/queried_at` | 本次快照已在PG；查看既有调查无需重新连接Neo4j |
| 证据—结论引用 I36 | k.`event_id`仅关联步骤；尚无统一每条结论evidence_ids合同 | 不能把event_id当结论逐项证据关系 |
| 处理步骤/节点 I37/I38 | e.`id/ts/seq/kind/agent/summary/payload`；graph_step的`payload.node` | 按ts展示，seq不是严格写入游标 |
| 模型调用/留存范围 I39/I40 | e中llm_call；k中`llm_prompt/llm_response/graph_llm_exchanges` | 截断和hash按实际记录保留；并非每节点都有完整输入输出 |
| 报告内容/版本/Case报告 I43—I45 | k中`kind='report_md'`的`content`；k.`id/created_at/sha256/size_bytes` | 自动、人工持久报告可走同表；有Case才另外关联Case |
| Token/调用数/费用/模型 I46—I49 | r.`total_tokens`及各费用计数；`aisoc_run_costs`各模型行；e中`graph_usage` | call_count来自用量表；不要把r.iterations当模型次数；unpriced>0不能解释为免费 |
| 推理轮数/查询类别/查询记录数 I50 | G.`investigation_depth.iterations/distinct_pivots/ledger_rows`；或统计工具事件 | 6轮、7类、10条记录各有含义，不叫10条已证实证据 |

### 3.3 需要聚合或当前没有持久字段的信息

| HTTP/页面字段 | 直查时怎么处理 |
| --- | --- |
| `fusion_identity/fusion_ioc_lookup/fusion_incident_id` | 分别从alerts.enrichment_data.socai2_fusion的identity/ioc_lookup/incident_id提取 |
| `related_entities/mini_timeline/recommended_actions` | API组装的展示结构；底层是实体、处理/审计记录、建议资料。第一版可直接展示本文已确认的实体与Run事件，不创建同名表假设 |
| `processing-context.dimensions/query/queried_at/priority/partial` | 查询当场生成；数据源表见第2.4节，评分是程序计算。不能用Alert.priority冒充上下文priority |
| Run的`event_count/artifact_count/model_costs` | 分别聚合events、artifacts、aisoc_run_costs；先各自聚合再关联，避免事件×工件×模型行乘积 |
| `latest_investigation/report_available/target_type/trigger_type` | 页面所需聚合/推导信息；当前无统一同名列。按已确认关联取数，未知就标未知 |
| 人工`recon/forensic/responder`独立卡片 | 主要是运行state；本地有采用样例，但未确认全部阶段结构长期单独落库。永久报告查report_md、步骤查events，不能SELECT不存在的forensic表 |

### 3.4 逐功能查询实例

以下实例使用同一生产租户中既有的两条合成告警，查询结果取自已核验资料。片段使用psql变量；通用数据库客户端请改为驱动的绑定参数。它们展示取法，本轮结构调整未重新执行生产SQL。

```sql
\set tenant_id 'f6a5c700-69b8-44fc-8238-609362fb1a9f'
\set alert_id 'e5f593f0-b328-59c3-8238-379db33d8bfe'
\set run_id 'bdccd907-7f36-558f-8ed4-4be2e417b101'
BEGIN READ ONLY;
SELECT set_config('app.current_tenant_id', :'tenant_id', TRUE);
-- 执行所需SELECT，最后ROLLBACK。
```

#### 3.4.1 功能：展示告警来源、时间、摘要、对象和状态

适用页面：告警列表/详情，A01—A08、A13、A17、A22、A25。

```sql
SELECT a.id, a.title, a.description, a.severity, a.status,
       a.event_time, a.created_at, a.disposition, a.ai_score,
       a.enrichment_data #>> '{socai2_fusion,identity,source}' AS source,
       a.affected_hosts, a.affected_users,
       a.enrichment_data #>> '{socai2_fusion,delivery_snapshot,fused,alert,src_ip}' AS src_ip,
       a.enrichment_data #>> '{socai2_fusion,delivery_snapshot,fused,alert,dst_ip}' AS dst_ip
FROM public.alerts a
WHERE a.tenant_id=:'tenant_id'::uuid AND a.id=:'alert_id'::uuid;
```

实际显示：来源`v1-functional-test`；标题`V1 functional example 2: unfamiliar script with outbound connection`；发生时间`2026-10-22 17:10:17.571282 +08:00`；等级high；业务状态triaged；主机`v1-functional-host-2`；源/目的IP为`192.0.2.82 → 203.0.113.82`。description说明脚本内容、执行结果、授权仍未知，不能将这段来源摘要改写为已确认入侵。

完整告警字段查询见附件 [ui-alert-fields.sql](examples/ui-alert-fields.sql)。顶部统计和分页使用与列表相同的租户/筛选条件；不要只统计已加载一页。

#### 3.4.2 功能：从告警找到调查，并展示Run状态和耗时

适用页面：告警“查看调查”入口、调查列表，A09、I01—I10。

```sql
SELECT r.id AS run_id, r.case_id AS target_id, r.status,
       r.started_at, r.completed_at,
       extract(epoch FROM (r.completed_at-r.started_at)) AS elapsed_seconds,
       r.total_tokens, r.error
FROM public.investigation_runs r
WHERE r.tenant_id=:'tenant_id'::uuid AND r.case_id=:'alert_id'
ORDER BY r.started_at DESC, r.id DESC;
```

本例查到Run `bdccd907-7f36-558f-8ed4-4be2e417b101`，执行状态completed，总耗时约21.86秒，total_tokens=29755。这是已确认的自动Alert路径；人工Case用Case ID查，未知入口先核对目标类型。是否确实进入调查再看下一例的graph事件/工件，不能把所有分诊Run计入调查列表。

#### 3.4.3 功能：分开展示首次分诊、调查完成度和最终调查结论

适用页面：告警AI分诊、调查结论卡，A33—A35、I06/I07/I15/I18。

```sql
-- 首次分诊和调查完成度分别是事件payload，不覆盖成同一个status。
SELECT e.kind, e.ts, e.payload->>'verdict' AS verdict,
       e.payload->>'confidence' AS confidence,
       e.payload->>'rationale' AS rationale,
       e.payload->>'auto_closed' AS auto_closed,
       e.payload->>'completion' AS investigation_completion
FROM public.investigation_events e
WHERE e.tenant_id=:'tenant_id'::uuid AND e.run_id=:'run_id'::uuid
  AND e.kind IN ('triage_verdict','graph_result')
ORDER BY e.ts, e.seq;

-- 调查置信度/停止原因取最终结果工件；不要误取首次分诊置信度。
SELECT k.id AS artifact_id,
       k.content::jsonb->>'verdict' AS investigation_verdict,
       k.content::jsonb->>'confidence' AS investigation_confidence,
       k.content::jsonb->>'budget_exhausted_reason' AS stop_reason,
       k.content::jsonb #> '{investigation_depth,unavailable_data}' AS missing_data
FROM public.investigation_artifacts k
WHERE k.tenant_id=:'tenant_id'::uuid AND k.run_id=:'run_id'::uuid
  AND k.kind='graph_result' AND k.content IS NOT NULL
ORDER BY k.created_at DESC, k.id DESC LIMIT 1;
```

| 页面字段 | 实际值 | 应如何展示 |
| --- | --- | --- |
| 首次分诊结论/置信度 | needs_review / 0.85 | AI首次分诊：待复核，85% |
| Run执行状态 | completed | 执行结束 |
| 调查完成度 | partial | 部分完成 |
| 调查结论/置信度 | needs_review / 0.19 | 调查结论：待复核，19% |
| 停止原因 | token budget exhausted (27697 of 20000) | 保留预算停止说明 |
| 缺失数据 | process_tree、network_connections | 提示本次未能检查对应数据 |

对照自动关闭例：Alert `bc625c39-56af-5403-a378-9bfb99c610d2`、Run `4f5a0a57-050a-57a4-8443-504550fbc5fd`，首次BTP/0.95、auto_closed=true、告警resolved；只有分诊，没有graph结果或Markdown，页面应显示“未启动调查”。

#### 3.4.4 功能：展示/下载Markdown报告

适用页面：调查详情“报告”，I10、I43—I45。

```sql
SELECT k.id AS artifact_id, k.created_at, k.sha256, k.size_bytes,
       k.content, k.blob_ref
FROM public.investigation_artifacts k
WHERE k.tenant_id=:'tenant_id'::uuid AND k.run_id=:'run_id'::uuid
  AND k.kind='report_md'
ORDER BY k.created_at DESC, k.id DESC LIMIT 1;
```

本例报告工件ID `72e0c864-41a0-4096-bfa2-8aa0ebe3a641`，content是Markdown，UTF-8大小6413字节；正文与hash已核对。可以直接渲染或下载content，不需要Case，也不重新生成报告。报告原文含旧status=running等质量问题，页面头部仍按Run状态和graph事件完成度显示；不能悄悄重写旧报告。

#### 3.4.5 功能：查看调查过程、查询记录、知识与图材料

适用页面：调查详情“过程/证据与关联”，I23—I42。

```sql
-- 过程和实际工具调用：包括seq=-1，按处理时间展示。
SELECT e.id, e.ts, e.seq, e.kind, e.agent, e.summary,
       e.payload, e.duration_ms
FROM public.investigation_events e
WHERE e.tenant_id=:'tenant_id'::uuid AND e.run_id=:'run_id'::uuid
ORDER BY e.ts, e.seq, e.id;

-- 材料目录；按artifact_id取正文，或在本SELECT按需加content。
SELECT k.id, k.kind, k.event_id, k.created_at, k.size_bytes,
       k.sha256, k.content IS NOT NULL AS has_inline_content
FROM public.investigation_artifacts k
WHERE k.tenant_id=:'tenant_id'::uuid AND k.run_id=:'run_id'::uuid
ORDER BY k.created_at, k.id;
```

本例18条事件、14份工件；其中10条tool_call有tool/args/result_preview，旧预览约200字符。graph_step只有node，不表示该节点独立完整输入输出可读。常见材料取法和实值如下：

| 功能 | 在工件content解析后取什么 | 本例实值 |
| --- | --- | --- |
| 知识读取 | kind=knowledge_base_read的status、received_count、adopted_count、citations | no_match、0、0、[] |
| 候选告警链 | kind=attack_chain的attack_chain.status/data.chain | empty、[]；entity_graph仍有节点边 |
| Case路径 | kind=attack_path的attack_path.status/error | not_linked、no_linked_case |
| 告警关系图 | kind=alert_graph的alert_graph.data.neighbors | 5个直接邻居 |
| 图可达范围 | 同工件alert_graph.data.blast_radius | 3跳可达6个节点，含起点，共5种类型；不是6受害主机 |
| 当次图查询范围 | kind=graph_result的context_bundle.attack_context.query_scope | projection_alert_limit=50、truncated=false |

需要原文时按 `tenant_id + run_id + artifact_id` 从工件表取content；JSON类型解析，Markdown直接读字符串。本地新版的tool_result也在同一工件表，但这两个旧生产Run没有此新类型，不能指望查出完整单次返回。

#### 3.4.6 功能：展示Token、模型调用数和费用

适用页面：调查详情“运行信息”，I46—I50。

```sql
SELECT c.model, c.resolved_model, c.call_count,
       c.total_prompt_tokens, c.total_completion_tokens,
       c.measured_call_count, c.measured_cost_usd,
       c.estimated_call_count, c.estimated_cost_usd, c.unpriced_call_count
FROM public.aisoc_run_costs c
WHERE c.tenant_id=:'tenant_id' AND c.run_id=:'run_id'
ORDER BY c.model;
```

本例首次分诊2058 tokens/1次调用，后续调查27697 tokens/6次调用，合计29755 tokens/7次；7次均未计价，页面显示“费用未计价”。推理轮数6、查询类别7、工具记录10来自调查结果/事件，不能与调用数混用。费用表已经按模型聚合，不要再JOIN多条事件和工件造成重复求和。

上述片段执行完以`ROLLBACK;`结束只读事务。已有完整样例脚本见 [production-two-examples.sql](examples/production-two-examples.sql)，原9个SELECT实际执行通过；本次新增的展示片段仅按既有字段和实值整理，未再次运行生产查询。

## 4. 已有 HTTP 后端接口

### 4.1 地址和认证

API在21主机为`http://127.0.0.1:18000`，同项目容器网络为`http://api:8000`。18000只绑定21本机loopback；远端后端通过获授权代理/隧道或同网络访问，不能直接把自己机器的127.0.0.1当21。

查询使用已发放的`Authorization: Bearer <reader>`及`X-AiSOC-Tenant-ID: f6a5c700-69b8-44fc-8238-609362fb1a9f`。已有reader主要用于查询，写操作按各自权限另行接入。凭据交接及详细配置见 [production.md](production.md)、[configuration.md](configuration.md)。下表列完整业务路径。

### 4.2 告警查询接口

| 方法与路径 | 用于哪个功能 | 主要请求参数 | 返回内容 / 当前边界 |
| --- | --- | --- | --- |
| `GET /api/v1/alerts` | 告警列表、统计、分页 | page/page_size；severity/status/category；assigned_to_me；min_confidence/confidence_label；sort | items、total、page、pages、facets；本次200。min_confidence是Fusion评分；search参数当前无效；未实现来源/发生时间/对象筛选 |
| `GET /api/v1/alerts/{alert_id}` | 告警详情 | canonical Alert UUID | title/description/时间/对象/分诊投影/raw_event；另有fusion_identity/fusion_ioc_lookup/fusion_incident_id及展示结构；本次200 |
| `GET /api/v1/alerts/{alert_id}/processing-context` | 当前资料覆盖/补充上下文 | alert_id | dimensions、query、queried_at、priority、partial等；动态查询视图。本次200，但样例大多no_match/not_configured |
| `GET /api/v1/alerts/{alert_id}/attack-chain?window=24h` | 当前候选告警链 | alert_id、window | chain、entity_graph、generated_at等；本次200，chain为空 |
| `GET /api/v1/graph/investigation-context?alert_id={alert_id}&window=24h` | 当前图资料综合查询 | alert_id、window | attack_chain/attack_path/alert_graph、query_scope、queried_at；本次200。回看历史调查优先用该Run工件 |

列表page_size默认25、最大200；`sort=priority`实际按严重程度再created_at，`sort=newest`按created_at，均不是event_time排序。source只在详情的fusion_identity中，当前列表不带；直查数据库不受该返回形状限制。

### 4.3 调查、步骤、工件和报告查询接口

| 方法与路径 | 用于哪个功能 | 参数/返回 | 验证边界 |
| --- | --- | --- | --- |
| `GET /api/v1/investigations` | 调查列表/目标运行历史 | case_id（目标字符串）、status、limit；返回Run数组 | 本次200；默认50、最大200，仅最近N条，无全量总数/游标，不能按partial过滤 |
| `GET /api/v1/investigations/{run_id}` | Run头部、状态、用量 | Run字段、event_count、artifact_count、model_costs | 本次200；不直接返回全部报告/最终调查JSON |
| `GET /api/v1/investigations/{run_id}/events` | 分诊、完成度、过程 | since、limit（默认200、最大1000）；items/total/since/next_seq | 本次200；首次不传since才包含seq=-1；seq不是严格写入游标 |
| `GET /api/v1/investigations/{run_id}/artifacts` | 材料目录/报告定位 | 工件数组：id/kind/event_id/hash/bytes/时间 | 本次200；只有元数据，无正文 |
| `GET /api/v1/investigations/{run_id}/artifacts/{artifact_id}` | 读取具体材料和Markdown | content、blob_ref和元数据 | 本次21份正文均可读且字节/hash匹配；JSON需解析content，MD直接取content |
| `GET /api/v1/cases`、`GET /api/v1/cases/{case_id}` | 人工Case列表/详情 | Case及成员告警信息 | 本次只查列表，返回空；详情入口源码已存在 |
| `GET /api/v1/cases/{case_id}/investigations` | 人工Case运行历史 | Case下Run列表 | 原入口存在，本次生产租户没有Case，未重验 |
| `GET /api/v1/cases/{case_id}/investigations/{run_id}` | 人工Case运行结果 | Case/Run结果 | 原入口存在，本次未重验 |
| `GET /api/v1/cases/{case_id}/investigations/{run_id}/report.md` | 人工Case报告 | Markdown正文 | 原入口存在，本次无Case，使用通用工件取报告 |

不存在通用`GET /api/v1/investigations/{run_id}/report.md`读取合同。无Case报告按“目录→report_md工件ID→详情content”读取。

运行中事件读取需按事件ID去重并回看，不能只追max(seq)；终态重新拉取/分页核对total，防止高序号工具记录先到、低序号graph结果后到造成漏读。

### 4.4 已有操作接口（本次未执行）

下面是现有源码入口，用于后续选定的人工作业功能；列出不代表本次已完成生产操作验收，也不要求通过直接UPDATE表来触发调查。

| 方法与路径 | 请求/用途 | 需要区分的语义 |
| --- | --- | --- |
| `POST /api/v1/cases` | title；可带description/severity/alert_ids等，创建Case | alert_ids使用canonical Alert UUID；不因创建成功就认定调查已完成 |
| `POST /api/v1/cases/{case_id}/alerts` | alert_ids，关联已有告警 | 仅建立Case成员关系 |
| `POST /api/v1/cases/{case_id}/investigate` | 可带alert_summary，启动人工调查 | 返回run_id后持续读取实际结果；这一步会执行调查 |
| `PATCH /api/v1/alerts/{alert_id}` | status/priority/tags/assigned_to_id（别名assignee）/case_id | 只能更新接受的字段；不能在此随意提交模型结论或正文 |
| `POST /api/v1/alerts/{alert_id}/claim` | 认领当前未分配告警 | 已被他人认领可409；首次成功claim写first_seen_at |
| `POST /api/v1/alerts/{alert_id}/snooze` | duration_minutes或until | 暂缓队列展示，不等于解决告警 |
| `POST /api/v1/alerts/{alert_id}/escalate` | 提高严重程度一级 | **不是启动调查接口** |
| `POST /api/v1/alerts/bulk-close` | alert_ids或限定过滤条件；close_status/max_count/comment等 | 批量业务关闭；不等于调查完成或厂商响应动作 |

### 4.5 用已有HTTP拿到本例报告

```text
1. GET /api/v1/alerts/e5f593f0-b328-59c3-8238-379db33d8bfe
2. GET /api/v1/investigations?case_id=e5f593f0-b328-59c3-8238-379db33d8bfe&limit=20
3. GET /api/v1/investigations/bdccd907-7f36-558f-8ed4-4be2e417b101
4. GET /api/v1/investigations/bdccd907-7f36-558f-8ed4-4be2e417b101/events?limit=1000
5. GET /api/v1/investigations/bdccd907-7f36-558f-8ed4-4be2e417b101/artifacts
6. GET /api/v1/investigations/bdccd907-7f36-558f-8ed4-4be2e417b101/artifacts/72e0c864-41a0-4096-bfa2-8aa0ebe3a641
```

第4步分别取triage_verdict与graph_result事件，第6步响应JSON的content就是Markdown。以上路径已有实读；若选其他Run，应使用其实际工件ID，不能复用本例固定ID。

## 5. 补充说明：版本、口径与交付边界

### 5.1 数据可用性与已完成验证

各章的数据可用性按以下状态理解，不能把它们互相替代：

| 标记 | 意义 | 上线判断 |
| --- | --- | --- |
| **线上实值** | 本次从 21 HTTP 或 PG 读到了实际值 | 可据该路径对接；仍需处理其他告警缺值 |
| **线上空值** | 接口/字段存在，本次值为 null、空数组或未命中 | 可做明确空态；不能宣称丰富资料已具备 |
| **数据库实值/空值** | PG 已确认，但当前业务 API 没返回 | 后端需要聚合/补字段，浏览器不直连数据库 |
| **本地已测** | 当前本地代码有可验证输出，未部署 | 仅进入开发版能力，不能当作生产现成字段 |
| **待补** | 只有设计、源码入口或不稳定文本，没有已确认的读取合同 | 不作为现成可用；排入后端最小补齐项 |

本次 2026-10-23 **14:39（UTC+8）** 实读：41 个 GET 全部 200；2 条既有合成告警的 21 份工件正文 UTF-8 字节数、SHA256 全部匹配。生产镜像 API `5a1e1fd8cf08`、Agents `49643b84b8f7`。生产租户 `f6a5c700-69b8-44fc-8238-609362fb1a9f`，告警列表共 3 条，Case 列表为空。

此前字段核验阶段另跑本地隔离 PG 两例“超时停止/模型报错”，实际 ledger 写入及持久结果读取通过，连同直接交接用例 **8 passed**。模型和查询工具为替身，PG 为独立临时容器/临时表；不是新真实模型调查，也不是本地 HTTP 全链验收。人工四节点校验信息复用当天已留存的真实模型采用样例，未再次调用模型。

完整脱敏实值、查询路径、正文校验和本地样例见 [字段验证数据](ui-field-verification-20261023.json)。自动关闭/自动调查样例分别对应JSON的 `online_samples.closed/partial`；两个本地样例在 `local_samples`。

数据库映射补充和本次结构调整只复用上述证据，未重新访问生产、调用模型、改变表结构、业务源码或部署。本地暂存测试容器已经清理。首次取数误查source列、首次本地连接被沙箱拒绝的记录保留；修正后分别取数/测试通过，不改写原失败。

### 5.2 对象、状态、时间和空值口径

| 对象/概念 | 页面含义 | 规则 |
| --- | --- | --- |
| Alert | 一条已进入本系统的告警 | 详情路由使用 canonical Alert UUID；上游告警 ID 另列 |
| Fusion Incident | 融合分组标识 | 作为关联标识展示，不能当成人工 Case 或完整事件研判结果 |
| Case | 人工案件容器，可关联告警 | 有 Case 才显示 Case 链接；自动调查不保证自动创建 |
| Run | 一次分诊/调查运行 | `case_id` 是历史通用目标字段，可能是 Alert ID、Case ID 或 Incident ID，不能全部 JOIN 到 Case |
| 告警业务状态 | 新建、已分诊、调查中、已解决等 | 来自告警status，保留原枚举；不由 Run 状态推导 |
| 首次分诊结论 | TP/FP/BTP/待复核等 | 来自triage_verdict事件；BTP 表示真实检测到良性活动，不是误报 |
| Run 执行状态 | running/completed/failed | 说明程序运行是否结束，不代表查清或业务结案 |
| 调查完成度 | complete/partial/未知 | 优先取 graph_result **事件** payload.completion；没有该字段的旧/人工运行显示“未提供完成度” |
| 调查分析结论 | needs_review 等实际 verdict | 与首次分诊分别展示；不得把自动判断显示成人工已确认 |

所有时间在界面明确显示时区；默认按 Asia/Shanghai 展示，保留原 ISO 时间用于复制。空值显示“未提供/未关联/未命中/未配置/不可用”，依原状态选词；不能统一显示绿色“正常”。显示文本不反向充当结构化证据。

补充：融合置信评分、AI分诊置信度、调查分析置信度、Alert.priority、动态上下文priority不是同一个分数。样例分别可出现65/100、85%、19%、50，不能统一命名为风险分。费用无计价时显示未计价，不把数值0显示成免费。

### 5.3 人工四节点和本地新版的展示边界

当前自动 graph 与人工四节点是不同运行路径，不能照搬同一组结果卡。人工默认路径可以展示 Recon/Forensic/Responder/Report 的实际步骤和永久 Markdown；结构卡只在**持久读取已确认**时展示。

| 期望卡片 | 本地已存在的实际字段 | 当前证据与 V1 决策 |
| --- | --- | --- |
| Recon 概览 | state.recon.iocs/mitre_techniques/summary 等 | 原结构存在，本次复用样例为空；不作为21所有 Run 必返卡片 |
| Forensic 假设 | state.forensic.summary/root_cause_hypothesis/timeline/artefacts/confidence | 复用本地采用样例有假设、空 timeline/artefacts；没有确认长期独立 JSON API，首版先保留报告呈现 |
| 程序校验结果 | state.forensic.validation.scope/status/reason/unsupported_indicators；groundedness | 本地实值 needs_review、unsupported=203.0.113.178；scope 仅 indicator_presence，不是全面事实核验或质量评分 |
| 响应建议 | state.responder.recommended_actions/risk_level/dry_run/containment_steps/eradication_steps/recovery_steps | 本地采用结果为 verify-only、risk=unknown、dry_run=true、三类步骤为空；不显示“已执行响应” |
| 最终报告 | state.report_md；持久路径以 report_md 工件为准 | 本地真实模型样例采用了 fallback report；该样例 db_writes=false，仅证明本地采用输出，不能声称这个 Run 已在21可查 |

此前真实模型样例 2 回复/2714 tokens 可复用证明“采用后的风险 unknown、只建议核查、报告待复核”；原模型文字仍有遵循问题。**本次没有拿四节点内存 state 冒充数据库永久结果。** 若 V1 要长期展示独立的 Recon/Forensic/Response 结构卡，须新增有版本的阶段结果持久与读取合同；本轮先不扩大编排设计。

此前字段核验的两个隔离样例各执行一次实际本地 runner/Deep/ledger 流程：先完成工具 `read`，再模拟模型报错或外层超时。两个 Run 均保留 `tool_result` 与 `report_md`，`read_persisted_run` 重新从 PG 读取获得 completion=partial。两例 Run ID、正文和 hash 见验证 JSON。

工具条目：call_id=`read-1`、iteration=1、status=success、available=true、result_truncated=false、result_size_bytes=94、留存状态recorded，结果含“已完成的合成查询”。随后停止原因为 `cancelled before investigation completed` 或 `ValueError before investigation completed`。页面应显示“已完成1次查询、随后调查停止、已有材料可查看”，不清空结果，也不把 Run completed 当完全查清。

该测试使用临时表而非完整生产迁移/RLS，验证的是原本地写入和冷读取函数；**不等于 HTTP、真实模型或生产已部署**。相关临时 PG 容器在本批结束后停止删除。

本地tool_result.result_text最多约4000字符，带result_truncated；result_size_bytes/result_sha256描述原始序列化结果。截断时hash不代表原文可以完整恢复。旧生产Run只有返回预览时，页面明确标注留存范围。

### 5.4 第一版仍需接入方处理的事项

| 事项 | 处理方式 |
| --- | --- |
| 列表查询/过滤/分页/统计 | 直查可按现有表自行实现；若用当前HTTP则按第4章限制补充适配 |
| 目标与最新调查关联 | 根据已确认入口解析Alert/Case/Incident；不将case_id一律当Case |
| 数据缺失/查询失败/未配置 | 分别展示，不能用绿色“正常”统一替代 |
| 人工认领/关闭/启动调查 | 接受对应操作接口后再做权限、状态和回执验收；本次未对生产样例执行 |
| 独立根因/影响/证据引用/人工复核卡片 | 当前缺统一持久合同，不能从自由文本猜成结构事实 |
| 人工阶段结构卡 | 默认保留过程与持久Markdown；独立阶段JSON的长期读取另行补齐 |
| 后续HTTP聚合 | 可按页面提供轻量数据；不作为当前直查前置，也不为页面另跑模型总结 |

### 5.5 参考页面与附件

已浏览的 beenur SOC AI 参考入口为 [20 上的 SOC AI 页面](http://192.168.1.20:3000)。它提供 Alerts/Entities、告警侧栏 Story/Details、告警详情 Overview/Timeline/Raw、工作队列，以及 Case 下 Investigation、Attack Path、Attack Chain、Ledger、Report。借用它的信息组织方式，具体数据能力以 **21 当前生产 API/Agents** 和 **本地开发版** 的实读为准。

| 参考页面能力 | V1 取舍 | 原因与页面落点 |
| --- | --- | --- |
| 告警列表、等级/状态筛选、详情侧栏 | 保留；默认进入告警列表 | 值班人员首先需要识别告警来源、时间、对象和处理状态 |
| Story 中 Fusion 与 AI 说明 | 保留但分区 | 来源事实、融合说明、AI 分诊理由的生成方式不同 |
| Entities 默认视图 | 暂不作为主入口 | V1 先保证逐条告警可追溯；实体作为字段和详情关联区 |
| Queue 的 Mine/Unassigned/SLA/Claim/Snooze | 本版不另建队列页 | 它是告警工作队列；不能把它当成调查 Run 列表 |
| Case 的 Investigation/Ledger/Report | 合并为 Run 调查详情的页签 | 线上自动调查没有 Case，也必须能打开结果 |
| Attack Path/Attack Chain | 放在“证据与关联”中，按实际资料展示 | 当前样例有关系图，但无关联链条、无 Case Path；不默认画成完整攻击链 |
| PDF、Replay、反馈、Playbook、真实封禁隔离 | 本版不作为交付前置 | 本轮报告交付为 Markdown；其他功能须另有产品与操作验收 |

| 附件 | 用途 |
| --- | --- |
| [ui-alert-fields.sql](examples/ui-alert-fields.sql) | 告警字段展开查询；38列/两例各8个JSON路径已静态核对，新增SQL未重跑生产 |
| [production-two-examples.sql](examples/production-two-examples.sql) | 两个既有Run完整只读查询；原9个SELECT已在21执行通过 |
| [ui-field-verification-20261023.json](ui-field-verification-20261023.json) | 实际字段值、工件校验、线上/本地版本及来源hash |
| [table-fields.md](table-fields.md)、[data-catalog.json](data-catalog.json) | 完整表字段和约束目录 |
| [configuration.md](configuration.md)、[production.md](production.md) | 连接、认证和生产接入说明 |
| [停止交接回执](../../operations/investigation-result-handoff-20261023.md) | 本地新版结果采用、工具留存和停止交接的验证边界 |

原始读回/探针/测试日志在仓库本地`.local/verification/ui-v1-20261023/`；对外交接使用本主文档和所需附件，不包含认证凭据或完整模型提示词。旧质量、预算和unknown问题仍按原记录保留，资料可读不代表安全分析质量已通过验收。
