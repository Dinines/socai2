# 新数据表实现与验证交接

2026-11-04事件Case关系已接通：[25项字段、完整流程和4例](../investigation/socai2-case-relations-20261104.md)。显式事件/成员并集、双Case移动、同事务pending/活动、幂等与冻结历史保护已实现；12新+7PG回归最新通过，首4夹具和1断言失败保留。增量124仅补Case固定source_namespace，29表459列；命名空间不是未提供的来源环境，不猜测。页面/生产未切换，下一H人工写读和引用冻结，随后外部来源及迁移/真实质量；Q仅预留，r13暂停。下方各批保留其发生时点。

当前页面字段读取（2026-11-04）：[73项明细与4例](../investigation/socai2-page-reader-20261104.md)、[8路径OpenAPI](socai2-page-reader-v1.openapi.json)已落新表主体、派生及关系字段/A-I执行留痕出口，默认关闭。8新+2PG回归和3个Q接口回归最新通过，[回执](../operations/socai2-page-reader-20261104.json)保首5个夹具/预期失败。29表458列/DDL/ORM/公共枚举不变，真实响应状态、H与生产迁移仍待，页面和旧库链路未改。下一3.4事件Case关联/移动事务。

当前I执行（2026-11-04）：[32字段、流程与4例](../investigation/socai2-incident-diagnosis-executor-20261104.md)接通完整成员/有效同次分诊冻结、一次模型、成员覆盖/来源及诊断未决原子发布；9新+5回归首次通过，[5批原件回执](../operations/socai2-incident-diagnosis-20261104.json)。旧I快照和Case历史保持，扩展信息仅存input_snapshot正文，29表458列/DDL/ORM/公共枚举与JSON合同保持。生产未接，下一完整页面字段DTO及逐项对照；Q仅预留。下方“I执行待接”为前批时点。

当前A执行（2026-11-04）：[28字段与4例](../investigation/socai2-alert-basic-executor-20261104.md)接通已有表的查询、模型请求回复、步骤用量及分诊/Explain原子发布，9新+5回归最新通过；[原件回执](../operations/socai2-alert-basic-20261104.json)。29表458列/公共合同保持，生产和页面未切换；I执行和完整DTO仍待。下方批次按历史时点阅读。

2026-11-04范围更新：设计和后台现统一在主目录`E:/aisoc/socai2`、分支`codex/case-baseline-history-20261103`。[当前OpenSpec任务](../../openspec/changes/complete-socai2-investigation-chain/tasks.md)区分已有实现、待完成和暂缓项。Q（AI问答）业务暂缓，仅预留接口，本文Q的流程仍是产品目标，不表示已执行或已交付；A/I/C/H职责和既定数据语义保持。

当前读取（2026-11-04）：[20字段/四接口/例子](../investigation/socai2-stage-reader-20261104.md)及[OpenAPI](socai2-stage-reader-v1.openapi.json)。新A/I结果读取和C1同快照新鲜度接通，旧冻结不变；7新+6回归最新通过，原失败保留。实际执行适配/请求回复步骤用量和完整页面DTO仍待，29表458列不变、无生产切换。下方“C1新鲜度未接”为历史时点。

当前A/I存储（2026-11-04）：[28字段、事务与4例](../investigation/socai2-stage-results-20261104.md)。begin/finish/stop/freshness已实现输入冻结、结果及失败尝试、引用/过期/乱序保护，10项不同合成PG检查最新通过；29表458列不变。实际A/I执行器、查询/模型请求回复与步骤用量、新告警事件读取及C1新鲜度接线仍待；没有业务切换。下方为前批记录。

当前Fusion进展（2026-11-04）：[53字段、事务与Case桥接](../investigation/socai2-fusion-ingestion-20261104.md)。告警/材料/来源/对象/事件成员/首次快照的新writer可显式选择，默认public；同源重投、材料增版/旧版不回退、人工移动/状态及业务时间保护已验证。9writer/worker+1Case桥接新检查与10旧路径回归最新通过，[回执](../operations/socai2-fusion-ingestion-20261104.json)保原失败。无新表列/枚举/通用合同变更，原文与C1背景分开且预算保持。下一A/I实际分析产物、新告警/事件读取及事件Case关系；旧消费者/处置回写未切换，配置不能单独上线。以下批次按历史时点阅读。

当前进展（2026-11-04）：[新Case九路径、36字段及4例](../investigation/socai2-case-api-20261104.md)、[运行时OpenAPI镜像](socai2-case-api-v1.openapi.json)。创建/成员更新与手动完整执行接独立命名空间，默认关闭；历史pending/正式AI、Run/Result/报告/冻结材料、当前判断、用量与来源对话按明确ID读。GET同一只读快照，最后记录取全部工件/步骤，未知值及截断明示。11新+2回归最新通过，5批真实独立合成PG、身份/模型/湖替身；[回执](../operations/socai2-case-api-20261104.json)保留网络中断及4夹具失败。原29表458列保持。下一Fusion告警/事件writer、事件Case关系，再外部来源/H/Q与切换验收；页面未改。下方各批按历史时点阅读。

当前进展：[统一手动执行器、字段和4个例子](../investigation/socai2-baseline-executor-20261103.md)已串联同Run C1–C6。按C3需求分配Deep/人工待确认/来源图，记录逐项状态和停止原因，最后一次模型调用保留给C6；不加自动队列或下一轮。Token/时限仍共享原总额，不足保系统交接。新计划和分配快照复用既有表，原通用合同/迁移不变。下一优先业务writer、手动HTTP、Run/Result/详细快照读取DTO，再补外部来源与H/Q。验证边界见[执行器回执](../operations/socai2-baseline-executor-20261103.json)。以下各批是历史时点。

当前进展：[C6最终交付、比较及原子发布](../investigation/socai2-baseline-delivery-20261103.md)已实现；[严格模型合同](socai2-baseline-delivery-v1.schema.json)从运行时导出。最后一次模型同时做整案再分析和交付，JSON/Markdown由程序生成；report_json符合原report_result并关联同一个Result ID，额外来源/执行字段在配套快照。无有效模型结论保系统交接，不自动采用；已有历史未指定基线不假装首次。表/迁移/原通用合同不变。明细见[本批回执](../operations/socai2-baseline-delivery-20261103.json)，合成库与替身模型验证不代表真实语义验收。下一统一执行器/额度预留、writer/HTTP/读取DTO与剩余来源。以下各批是历史时点。

当前进展：[C5来源图、完整例子及C6剩余字段](../investigation/socai2-baseline-graph-20261103.md)。复用run_steps和artifacts的既有graph合同，同事务保存节点/边/原字段引用/查询范围/时间依据/限制，新证据生成新快照，过期图不进入当前再分析。C6逐字段区分“有存储”和“缺生成”，没有新增表或扩大预算。10项新检查及回归结果见[本批回执](../operations/socai2-baseline-graph-20261103.json)，原失败和空选测试批保留；独立合成PG、模型/湖替身，无页面/部署改动。下一C6、完整编排、外部来源和业务HTTP。以下各批是历史时点，顶部及主设计为当前状态。

最新后续：[问题级Deep与补证后再分析](../investigation/socai2-baseline-deep-20261103.md)接同Run动态查询和C3新回合，实际可见来源/查询身份/输入版本/请求回复/usage与停止原因保留。新增[Deep输出合同](socai2-baseline-deep-v1.schema.json)，运行时Pydantic与导出schema一致，业务表/原38通用合同不变。10项新检查＋9项回归最终通过，PG为原独立合成库，模型/CH全替身；C5/C6、完整编排与HTTP仍待。下方各批记录按发生时间阅读。

最新进展：[C4第一批字段、确定查询与例子](../investigation/socai2-baseline-c4-evidence-20261103.md)已实现，11项本批检查＋4项受影响回归最终通过，[明细回执](../operations/socai2-baseline-c4-evidence-20261103.json)保留首轮字段名错误和测试断言错误。复用alert_materials/run_members/run_steps/artifacts，无29表458列/DDL/原38合同变更；新工件内容由程序生成并逐路径引用校验。现有独立PG实测，ClickHouse为替身；没有真实模型/湖/厂商调用或页面改动。C4动态Deep、主机产品/认证适配及再分析仍待，以下C1–C3段落按各批历史时间阅读。

2026-11-03。用户确认D01–D03后，已从字段合同生成迁移、ORM、枚举和JSON schema，并按用户要求使用**21现有PostgreSQL实例中的独立验证库**完成实际建表和直接验证。

同日后续：已在最新后台工作树实现新表的成员→pending→手动领取→结果发布存储服务，并用受限数据库角色完成17项不同Python服务/PG事务检查（最终均通过，另有测试资源清理检查）。[服务实现与边界](../investigation/socai2-baseline-storage-20261103.md)和[本批明细回执](../operations/socai2-baseline-storage-20261103.json)为最新进展；旧HTTP入口和完整执行器仍未接线。以下39项是此前独立的物理约束检查，不能与本批17项合称一次测试。

再后续：已完成并接入[C1整案数据准备](../investigation/socai2-baseline-c1-20261103.md)，11项C1检查及10项原事务回归最终通过。复用现有artifacts.source_snapshot，不改29表458列、迁移、ORM、枚举或原38通用JSON合同；新增[专用C1内容合同](socai2-baseline-context-v1.schema.json)。

最新后续：[C2背景查询与模型输入视图](../investigation/socai2-baseline-c2-20261103.md)已实现；资产、同对象历史告警、租户内部TI三类实际SQL接同一Run，UEBA/知识/Graph未接逐项留因。保存六来源步骤/请求/返回/限制，复用Run额度；查询中禁止发布，重复C2不重查。模型视图保全成员覆盖和六项问题，8192字节总量/2048字节单项及原值guard；准备不等于模型已读。11项C2/视图及8项受影响回归最终通过，[回执](../operations/socai2-baseline-c2-20261103.json)保留首轮失败和定向复用记录。本批不改业务29表/列/DDL，只在原独立验证库添加两张来源夹具；C3–C6、三类余下适配及业务入口仍未接，无模型/部署/页面变化。

## 1. 已固定的决定

最新实现补充：[C3初始主分析与领域结果](../investigation/socai2-baseline-c3-20261103.md)已接同一Run和原模型配置/guard入口；保存原请求/回复、真实上报用量、全成员/六问题、四领域适用性与发现、冲突/替代解释和补查需求。使用一次共享调用，非四个独立专家；不发布Result或自动采用。12项新检查＋7项回归最终通过，[回执](../operations/socai2-baseline-c3-20261103.json)说明合成模型替身范围。新增[专用C3输出合同](socai2-baseline-analysis-v1.schema.json)，业务表、原通用合同保持。C4–C6/再分析回合/完整执行器/HTTP仍待，未调用真实模型。

| 决定 | 当前实现/合同 |
| --- | --- |
| 事件等级 | 保留成员最高等级的派生值；事件可保存人工覆盖等级、理由、人和时间；不修改成员等级。四个覆盖字段必须同时设置或清除 |
| 案件当前判断 | 有效基础结果自动更新；AI结果须明确采用，保存AI答复本身不采用 |
| 执行互斥 | 同Case最多一个活跃baseline，另可有一条pending；AI模型/工具执行可并行，不占基础槽 |
| 特殊Case | 空/已解决Case的D04产品策略仍保留，不因表存在就开放相关动作 |

## 2. 新增代码

| 文件 | 内容 |
| --- | --- |
| [123迁移](../../services/api/migrations/123_socai2_page_data_model.sql) | socai2 schema、29表/458列、枚举CHECK、同租户/同案/同轮关系、索引、严格RLS及冻结/不可变保护 |
| [ORM](../../services/api/app/models/socai2.py) | 29个显式schema映射，458列；独立metadata，未自动接入旧业务写入 |
| [枚举](../../services/api/app/socai2/enums.py) | 36组共享枚举，避免页面标签直接入库 |
| [JSON schema](../../services/api/app/socai2/contracts.schema.json) | 38种结构化输入/产物合同；API接入时必须实际调用校验，文件存在不等于旧API已使用 |
| [生成脚本](../operations/build_socai2_schema_20261103.py) | 从唯一字段字典生成代码；源是[结构化合同](socai2-data-contract-20261103.json) |
| [物理保护SQL](socai2-schema-guards-20261103.sql) | 随迁移原子执行；不是第二份需要另部署的迁移 |
| [PG验证脚本](../operations/verify_socai2_postgres_20261103.py) | 只针对固定独立验证库；不会使用业务DATABASE_URL，不会覆盖已有数据库 |

附加命名CHECK为190个；复合唯一约束42个（另有每表主键和tenant+id唯一）；附加外键179个（另有29个tenant外键）；独立索引49个。数量用于与实际结构核对，不作功能覆盖率。

迁移内部先建表，再加循环外键；FK可延迟到提交，任务当前版本和材料/Run能够同事务发布。迁移本身包含BEGIN/COMMIT，记账也在同一事务；验证库重复应用成功。运行服务不调用create_all替代迁移；ORM未重复声明旧public表外键和部分索引/触发器，以迁移为物理权威。

事件读取DTO应同时提供derived_severity、severity_override及effective_severity：derived按info/low/medium/high/critical从成员计算，effective有覆盖取覆盖，否则取derived。即使人工覆盖存在，derived仍可回查；全体成员等级未知时derived=NULL，不默认补低。

## 3. 自动采用的准确边界

新存储服务发布结果时，在同一事务调用：

```sql
SELECT socai2.auto_adopt_baseline_result(:tenant_id, :result_id);
```

函数已由新BaselineStore.publish在同一事务调用；旧CaseAnalysis尚未改为调用它，不是已经对线上Case生效。

允许自动采用的结果：baseline机器执行已completed，结果validation_state=accepted、conclusion_origin=model、有明确结论，范围版本和成员集合仍匹配当前Case，且本轮开始后没有更新的判断被采用。部分交付可以采用，但只保存conclusion_covered的成员，其他未决仍明确保留。缺任一成员交付记录、无结论覆盖、系统交接、过期范围均不会覆盖当前判断。

采用会原子新增判断版本、具体结果依据和覆盖成员，更新Case当前引用、行版本/业务时间，记录服务主体及实际活动目标；不自动解决Case。重复同一结果返回原采用记录，不重建或把当前指针倒回旧版本。AI结果返回not_eligible，留待明确人工采用入口；人工采用权限和业务接口还要接入。

可能返回：adopted、already_adopted、not_eligible、stale_scope、newer_assessment、no_conclusion_coverage、missing_member_delivery。返回是发布结果，调用方应据此展示/留存原因，不盲写成功文案。

## 4. 范围冻结与并发

基础调查仍是Case→Run锁顺序。所有成员管理在同一事务更新当前关系、scope_revision、pending及活动；数据库保护负责拒绝越界写入，不代替服务构建待更新记录。唯一索引只限制baseline；unknown占基础槽；终态不可再改。

AI新Run无“待更新”业务状态。服务端预生成UUID，在同一事务保存成员、Run和输入工件；可先插入run_members再插入父Run，延迟FK在提交时校验。若父Run已冻结，只允许其创建/领取事务内已约定的新成员同时发布；另一事务即便在父Run提交后再提交，也不能借延迟FK插入成员。已存在Run的成员身份/材料引用不可修改，实际进度单独更新。

数据库保护已真实验证；新存储服务也已实现范围维护并验证，但旧业务路由仍未切换。未引入定时领取、自动接续或新的后台调度模块。

## 5. 实际验证环境与结果

- 主机：21；现有容器：spirithub-postgres-1；PostgreSQL **16.15**。
- 独立库：**socai2_schema_review_20261103_a1**，schema：**socai2**。
- public中的tenant/user/connector是为外键建立的合成占位；新表里全部是明确测试数据，不读取或复制业务库记录。
- 开始创建的临时容器socai2-schema-test-20261103-a1已按用户要求删除；后续全部验证在已有PG实例的新库中完成。
- 测试期间的NOLOGIN角色已删除。验证库保留用于查看；没有切换业务连接、改服务镜像、推送或部署。

[最终PG回执](../operations/evidence/socai2-schema-20261103/postgres-tests.final.json)：**39个不同检查最终通过**，包含表/列实况、枚举/评分/覆盖约束、跨租户FK、严格RLS、任务版本循环和不可变、基础单活跃、AI并行、自动采用/幂等/覆盖/旧范围/较新人工判断、AI保存不自动采用，以及多组真实双会话竞争。458个实际列的类型和nullable逐项与字典相同，见[数据库列目录](../operations/evidence/socai2-schema-20261103/actual-column-catalog.json)。

不是一次首跑39项：首17项通过后，结果发布触发器引用了另一张表没有的字段，出现42703；已改为按表名分支后再访问对应字段，[首轮原件](../operations/evidence/socai2-schema-20261103/postgres-tests.initial.json)保留。随后32项通过；新增AI原子创建和并发边界验证中，外键先行拒绝返回23503，测试原先只接受冻结拒绝23514，保留[当时结果](../operations/evidence/socai2-schema-20261103/postgres-tests.final.initial.json)，核实无残留成员并修正预期，再补“父Run已提交、另一事务随后提交”用例，确认冻结保护也返回23514。未重跑未受影响的通过项；最终回执明确复用范围。

上述均为数据库结构与合成数据事务验证，不是模型/Tool/完整调查链路验收。没有运行真实调查或重试r13。

## 6. 后续工作

1. 新ORM及Case基础调查存储服务已进入最新后台分支；下一逐个业务入口接鉴权/DTO并选择新表，不要先让旧Fusion仅改表名写入。
2. 告警/事件保存收到的材料、来源、分诊、独立事件及成员依据；管理字段按已确认规则写回。
3. Case成员→pending、手动领取及结果发布存储方法已实现；HTTP入口和完整执行器尚待适配。AI明确采用另有入口。
4. C1、C2三类SQL、C3初始及补证后再分析、C4原始字段/确定查询/问题级Deep已实现；下一C5图/C6交付、完整编排，补产品主机/认证与UEBA/知识/Graph适配。结果/逐成员覆盖可存，新服务校验消费子集及引用；全部38类通用合同与页面DTO尚未接通，真实模型/新湖查询质量未验。
5. 人工反馈版本、对话、明确保存、探索、响应关联按合同接入。空/已解决Case及人工采用权限尚未定义的操作先保留限制。

当前已完成新库表及物理约束、Case基础调查核心存储事务；不是页面功能和全部业务服务改造。业务库应用迁移、历史回填、服务切换和端到端验收尚未执行。继续开发时沿服务交接继续，不重复问D01–D03或原16项决定。
