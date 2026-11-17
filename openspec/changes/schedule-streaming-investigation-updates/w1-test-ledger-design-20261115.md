# W1：最小测试账本与只读API

2026-11-15，负责人明确授权先完成不依赖调查接口的W1，验证后才进入HTTP取数和4177；21实际测试等第7步交接和版本就绪，先单点后集成。本步隶属原测试服务W1与主任务2.7/3.1/3.2，不增加业务任务树。

**当前状态：W1已实现并完成本组件验证。** [回执](../../../docs/operations/evidence/test-ledger-w1-20261115-01/README.md)记录16项直接测试、8个GET的真实回环TCP读取、保存及重启核对；34次带断言GET和3次启动探测均符合预期，原证据与账本摘要保持。服务已停止，业务连接/真实模型/Kafka投递均为0。下一步按总计划先完成T2最小S01/S04生成及候选参数对齐，再接W2；W2–W4与21联验未完成。

## 目标与边界

让测试执行方能通过明确本地入口保存批次、用例、操作、准备/清理事实、质量问题及可查阅证据；查阅方用独立HTTP读取同一份持久记录。排队无Run、历史真实Run、失败/unknown、未检查质量和明确质量问题分别可见。

本步只实现`services/investigation_test/`独立Python包、文件发布入口、DTO及只读API、配置示例和直接验证。无调查业务包/数据库/Redis/Kafka/模型依赖，不提供业务代理、4177页面、执行器或部署服务。使用本机临时目录及回环HTTP做本组件验证，不恢复本机调查运行环境，也不冒充21联验。W2/W3/W4保持后续步骤。

## 持久化与输入合同

- 显式JSON profile提供ledger_root、监听host/port、分页与文件大小上限；相对路径相对profile目录解析，不回落其他环境。配置不得含业务连接或凭据。
- `BatchDocument(schema_version=1)`包含batch、cases、operations、preparation、quality_issues和evidence；Pydantic严格拒绝未声明字段并检查内部引用。业务身份只保存映射数组，不解析或生成调查Run；没有Run保持null。
- 发布入口`python -m investigation_test publish --config … --document … --expected-revision N`仅保存已提供的测试记录和明确登记的可查阅证据。N=0创建；更新须匹配当前revision。单写锁、原子替换当前ledger、保存不可变revision；终态finished/failed/interrupted禁止改写，复验使用新batch。启动/GET不调用发布入口。
- evidence按登记ID查阅，源文件必须在输入document所在目录内，禁止绝对/上溯/隐藏路径和符号链接；必须显式`visibility=public`，发布者负责只登记已脱敏可公开证据。原字节以sha256保存，不执行内容、不根据source_ref读取任意文件。API验证size/hash，不静默显示损坏原件。
- 账本仅记录测试元数据。批次`mode=live/archive`和`provenance=live_execution/saved_evidence/synthetic_fixture`明确来源；W1保存历史业务身份不代表正在查询调查接口。用例status为not_run/blocked/passed/failed/deferred/not_covered；batch执行状态、用例判据和模型质量分别表达。quality_status为not_assessed/issues_recorded/assessed_no_issues，不能凭空列表判无质量问题。

## HTTP合同

沿[既定草案](test-service-and-4177-http-20261115.md#3-测试专属http草案)提供8个GET，独立OpenAPI不混入业务Swagger：capabilities、batches、batch详情、cases、operations、preparation、quality-issues、evidence。详情包含证据元数据和链接；evidence默认返回元数据，`format=content`返回原字节（attachment、hash/size，不接受文件路径）。

列表返回items/total/next_cursor/observed_at。批次按started_at（未开始排后）/batch_id稳定倒序，其余按自身ID升序。cursor绑定路径/筛选/limit及当前记录修订摘要，数据变化返回409 cursor_stale并要求重新读取，不悄悄跨页重漏。非法参数/游标422、未知批次/证据404、账本或证据不可读/损坏503；错误为可读code/message，不返回磁盘绝对路径或原始异常。写方法无路由，405；读取和服务重启不创建账本目录或续跑任务。

## 本步顺序与通过证据

1. 先补本设计和规格，运行OpenSpec strict。实现DTO/文件发布，验证保存、内部引用、修订冲突、终态保护和原证据保持。
2. 接只读API，验证同一批次全部读取、筛选/分页/空态/404/422/503、质量与流程分离、无Run映射、多Run数组、证据登记和完整字节。复用历史Run只读回执，不重新执行调查。
3. 临时回环TCP启动本组件，保存已结束核心HTTP来源回执的归档映射及独立合成状态；逐项GET、停止后重启再读取，并比对账本/原来源文件前后hash。记录实际请求/响应、断言、版本和配置；0业务连接/0模型。
4. 定向pytest、Ruff和strict通过后输出本步回执、API OpenAPI、启动方式与未验边界。W1通过后按总计划先做T2数据及候选参数，再接W2；本轮不同时实施后续独立模块。

回执保存至`docs/operations/evidence/test-ledger-w1-20261115-01/`。不把W1组件成功计入52组业务用例通过；TC-V01只完成账本API部分，21实际部署、业务实时取数及4177展示未验。历史失败和quality NOT_PASSED均保留。

## 本次实施的最小字段与保存方式

F1–F5本机修复/HTTP回执齐备后，按负责人原W1授权继续本步。文件边界为`services/investigation_test/`独立包及其组件测试、`deploy/investigation-test/`只读配置示例和本步证据；不修改调查核心、业务HTTP或4177。测试方先完成本步并报告，W2–W4继续后续独立步骤。

| 记录 | 首版字段与约束 |
| --- | --- |
| batch | id、environment、title、scenario_version、execution_state、mode、provenance、started_at/updated_at、quality_status；时间带时区，来源/质量分开 |
| cases | id、use_case_id、scenario_id、status、expected、actual、operation_ids、evidence_ids；passed必须有actual和已登记证据，不能仅凭布尔值通过 |
| operations | id、case_id、intent、execution_state、occurred_at、mappings、evidence_ids；映射保存subject_type/id及可空task_id/run_id/result_type/result_id，Result需有对应Run |
| preparation | status、cleanup_mode、summary、resources、observed_at、evidence_ids；只保存事实，不实现检查、清理或恢复执行器 |
| quality_issues | id、case_id、run_id、stage、category、description、status、affects_flow、evidence_ids；有问题时batch必须为issues_recorded，无记录不默认为assessed_no_issues |
| evidence | 发布输入为id、相对path、label、mime_type、visibility=public及可选source_ref；保存后仅暴露id、label、mime_type、size、sha256、source_ref和API链接，不返回源文件路径 |

所有内部ID使用不含目录分隔符的有限字符串，业务身份为UUID。批次内ID不重复，case/operation/quality/evidence引用必须能解析；操作和case的双向关联一致。文档与证据大小、分页/游标上限、监听和目录全部来自显式profile；未知字段拒绝，profile不接受业务连接配置。

单发布锁下，先在本批独立临时revision目录保存完整JSON和证据，fsync后以唯一revision目录保留；最后原子替换`current.json`指针作为发布生效点。指针含内容hash，读取核revision/批次身份及JSON完整性。旧revision不可变，发布失败留下的未指向目录不作为有效记录、不自动续跑；不建设跨服务恢复框架。GET不创建目录、锁或文件。

必要直接检查限于本组件：CAS/终态及旧revision保持、引用与质量约束、8个GET的分页/过滤/合法空态/错误、cursor跨修订409、登记证据完整字节及丢失/篡改503、非法/符号链接来源拒绝、HTTP启动与重启无写入/执行。真实TCP验证使用新临时账本和显式回环profile，复用已结束批次的保存原件作archive，并把合成状态样本独立标为synthetic_fixture；不将合成状态记入业务通过数。
