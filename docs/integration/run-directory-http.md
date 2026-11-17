# 统一分析记录查询接口

2026-11-15更新。`GET /api/v1/socai2/analysis-runs`已完成本地实现和真实数据库验证，候选OpenAPI已生成。**本地常驻服务和21尚未发布此接口，正式Swagger仍为原71项操作。** 完整change验收后统一发布；候选代码80项操作。

11-15[告警自动分诊查询联验](alert-auto-http.md)已完成，候选移除旧E36；原批OpenAPI/验收计数保留历史时点，当前候选见[80操作合同](../operations/evidence/alert-auto-http-20261115-01/candidate-openapi.json)。

接口属于独立对外HTTP服务，通过只读用例读取调查模块保存的数据。它不受理任务、不启动调查、不调用模型；任务执行、调度和业务表由调查模块负责。此项为[OpenSpec任务2.7](../../openspec/changes/schedule-streaming-investigation-updates/tasks.md)中的R1。

## 功能和调用结果

后端可一次查到告警分诊、事件诊断和案件调查记录，不必先列出全部对象再拼历史。没有案件关联、失败、结果未知、尚无结果的分析记录也会返回。每项提供对象、任务、执行和交付状态、冻结输入数量、时间及详情/结果链接；同时返回整个筛选范围的统计。

## 输入参数

所有参数都可省略。不需要登录或Token，租户和记录身份使用服务配置。

| 参数 | 含义和规则 |
| --- | --- |
| subject_type | alert告警、incident事件、case案件；省略则查询三类 |
| subject_id | UUID；提供时必须同时提供subject_type |
| run_kind | alert_basic告警分诊、incident_diagnosis事件诊断、baseline完整案件调查、ai_question历史AI记录、targeted定向调查；只读存在的记录，不代表对应启动能力已交付 |
| intent | initial首次、check检查更新、rerun重跑、targeted定向、synthesis综合；取真实任务意图。无任务关联的历史记录不命中此筛选 |
| state | pending_update待启动、running执行中、unknown执行结果未知、completed已完成、failed失败、cancelled已取消 |
| time_from、time_to | 带时区时间，按Run.requested_at筛选，前闭后开；不是任务submitted_at。开始必须早于结束 |
| limit | 单页数量；默认50、最大100来自显式读取profile。没有整份目录的总量截断 |
| cursor | 上页next_cursor；保持全部筛选不变，可变更合法页大小。按requested_at DESC、run_id DESC排序 |

非法枚举、无时区日期、反向/相等时间窗、未知参数、重复参数、超限页大小及跨筛选游标返回422。合法但无匹配记录返回200和空列表。

## 输出字段

| 字段 | 含义 |
| --- | --- |
| items | 本页分析记录；每项字段见下表 |
| total | 全部筛选命中的Run数，不是本页条数 |
| next_cursor | 下一页游标；没有下一页为null |
| observed_at | 本页和统计的数据库观察时间 |
| statistics | 同一只读快照内、全部筛选范围的统计，翻页不缩小统计范围 |

| items中的字段 | 含义 |
| --- | --- |
| run_id | 一次分析记录的ID；同一任务重试可产生多个Run |
| subject_type、subject_id、subject_title | 实际分析对象的类别、ID和当前标题；标题可空 |
| run_kind | 本次执行类型，与输入run_kind枚举相同 |
| task_id、intent | 从同租户attempt.run_id关联到真实task.id/intent；历史没有关联时明确为null，不根据trigger推测 |
| state | Run真实执行状态，枚举同输入state；unknown不改写为成功或失败 |
| delivery_state | none没有交付、partial部分交付、complete完整交付、unknown未知；与执行状态分别表示 |
| requested_at、started_at、ended_at | Run请求、开始、结束时间，未记录为null；任务本地结束不伪造unknown Run的结束时间 |
| input_member_count | 本次冻结输入成员数，未知为null；只有明确保存的空数组才为0，不取主体当前成员数 |
| results | 实际保存的结果引用，无结果为[]；同Run多个Case结果版本全部保留 |
| detail_url | 读取该Run详情的相对HTTP地址 |

results每项为`{result_type,id,source_run_id,kind,url}`。result_type为alert_assessment、incident_diagnosis或case_result；id为结果ID，source_run_id等于所在项run_id，kind为保存的结果种类。url指向真实结果入口：告警/事件在Run详情的result中，Case结果有独立详情。步骤和原件沿[完整目录接口](run-records-http.md)继续读取。

| statistics字段 | 统计口径 |
| --- | --- |
| total_runs | 全部筛选命中的Run数，与total相同 |
| by_state | 所有Run状态的数量，未出现为0 |
| by_delivery_state | none/partial/complete/unknown各自数量，未出现为0 |
| without_related_case_count | 当前没有实际案件关联的Run数量 |
| related_case_count | 当前实际关联的不同案件数，多Run、多关联路径去重 |

Case Run关联自身；告警沿case_alerts；事件取case_incidents显式关联和共享告警成员关联的并集。关系表示当前观察，不冒充执行时关系，不包含候选案件。结果版本和关联数量不放大Run计数。

只有已存在Run的分析进入本目录；任务已受理但尚未创建Run时不造一行记录。每页与统计使用同一只读快照，跨HTTP分页不承诺永久冻结；变更筛选需重新取第一页。

## 请求和响应示例

发布后可调用：

```http
GET /api/v1/socai2/analysis-runs?subject_type=alert&intent=initial&limit=1
```

[请求与完整JSON示例](../operations/evidence/run-directory-http-20261114-01/examples.json)来自本机隔离库实际ASGI读回，包含正常分页、历史null、意图筛选、无Run任务空集和参数错误。示例UUID是保留的合成样本，仅在该隔离库存在，不是21的测试数据。

错误有两种结构：字段校验为422 `{"detail":[...]}`；业务参数/游标错误为422 `{"detail":{"code":"invalid_cursor","message":"分页游标无效或不属于当前查询","context":{}}}`，code也可为invalid_input。读取配置或数据库不可用为503，code为service_unavailable；接口不返回虚假任务ID或执行成功回执。

## 数据依赖和验证

需同一目标数据库已应用调查侧迁移128，并使用配套ORM；不检测缺表后回退旧版。读取runs、analysis_attempts、analysis_tasks及主体、成员、输入工件和结果表，不创建/维护它们。迁移保证非空(tenant_id,run_id)只关联一个attempt；同任务重试的新Run各自保留，真实无关联的历史Run返回null。

[本轮回执](../operations/evidence/run-directory-http-20261114-01/README.md)：真实核心受理→尝试→合成Run和输入保存→绑定→结束，再由HTTP读回；32次ASGI请求（其中1次503使用依赖替身），10次基础查询，15类测试记录读取前后内容摘要一致。覆盖混合分页、意图和状态筛选、重试关联、历史null、无Run任务、冻结输入数量和实际结果URL。没有真实模型或工具调用，未部署、提交推送。

[任务列表与详情](analysis-tasks-http.md)随后也已完成本地验收，待统一发布；异步提交、调度及整个2.7仍未完成，按原依赖顺序推进。
