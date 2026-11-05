# 当前任务

2026-11-05当前进度：19/26项完成；本机累计48/50次模型尝试。C6已不依赖C3成功，并将案件业务判断与执行原因分字段保存；g首轮及新增三组案例均形成模型Case判断，原页面可回查。三组新增15次DeepSeek，最终均accepted/partial/uncertain；03有事实扩大，模型质量不通过。H后容量、知识实际消费、语义约束、完整页面闭环、远端模型对照及结束审计仍待。用户已授权提交推送到origin/codex/case-baseline-history-20261103；不部署、不归档、不核销旧失败。 待办为3.7、3.10、3.12、3.14、3.16、4.1、4.2；[修改与后续评审清单](../../../docs/investigation/design-audit-and-scenario-evaluation-20261105.md#9-实施变更与后续评审记录2026-11-05提交快照)给出证据及验收要求。

[前一轮调整规划复核](planning-review-20261105.md)已通过；仅适用于该回执所列版本，不自动覆盖后续修订，也不替代3.7真实验收或4.1实施结束独审。

最新执行方式见[本机环境与分阶段模型验证计划](local-first-validation-plan-20261105.md)：专属PG/CH/Kafka/ZooKeeper/Redis均healthy，API/Fusion ready；旧ingest/UEBA/threatintel/realtime已按明确授权停止，旧数据保留。知识沿告警标题→PG全文检索，Qdrant/Embedding和Neo4j不作为前提。常态使用DeepSeek直连；远端对照只切模型地址、认证与协议，数据库、执行记录、工件及页面全程本机。3.14只完成本批资产/SOP函数导入与受限FTS读回，完整来源准备仍待核。

早期a—c固定结果：三批共14次，C6缺字段、C3绑定和C6额外空字段/查询视图容量问题均保原件。后续修复与d—g/三组对比以本文3.15/3.17和local-first计划最新段为准；不能把早期0采用作为当前总数。

## 承接已有实现

- [x] 1.1 将后台、最新设计和预览迁入主目录开发分支，核对迁移文件与备份，注销本任务旧工作树；见execution.md。
- [x] 1.2 保留29表458列物理合同及独立PG验证；见docs/design/socai2-schema-implementation-20261103.md和docs/operations/socai2-contract-final-20261103.json。
- [x] 1.3 保留C存储、C1–C6统一手动执行与Case HTTP/读取；见docs/operations/socai2-baseline-executor-20261103.json、socai2-case-api-20261104.json及其分阶段回执。
- [x] 1.4 保留Fusion新表writer/Case桥接与A/I冻结、结果发布、新鲜度及读取；见docs/operations/socai2-fusion-ingestion-20261104.json、socai2-stage-results-20261104.json、socai2-stage-reader-20261104.json。

## AI问答仅预留接口

- [x] 2.1 添加发送、保存答复和明确采用的最小类型/HTTP入口，统一501，沿用认证、写权限及默认关闭开关；不接Q业务。见docs/investigation/socai2-case-ai-reserved-20261104.md。
- [x] 2.2 直接验证占位响应、权限/开关、请求边界与无业务执行，导出对应OpenAPI合同；3个ASGI检查通过，详见execution.md。
- [x] 2.3 同步主设计/任务范围、执行记录并通过本change的strict校验；CLI有效不代表功能完成，后续任务保持未勾选。

## 服务端字段与流程接线

- [x] 3.1 实现A告警基本查询/分诊执行适配，保存实际请求、返回、步骤、用量和同次解释；复用已有冻结/发布服务。9新+5回归最新通过，见docs/investigation/socai2-alert-basic-executor-20261104.md及对应回执；内部入口已接，生产消费者未切换。
- [x] 3.2 实现I事件诊断执行适配，消费明确成员与同次有效分诊，保存诊断/未决及来源，不将归并摘要当诊断。9新+5回归首次通过，见docs/investigation/socai2-incident-diagnosis-executor-20261104.md及对应5批回执；内部入口已接，生产未切换。
- [x] 3.3 完善告警/事件页面字段DTO逐项对照，包括身份、时间、状态/判定、独立事件事实、来源与已定派生口径；页面功能由其他负责人实现。73项明细及8个GET模板见docs/investigation/socai2-page-reader-20261104.md；8新+2PG回归、3个Q接口回归最新通过，默认关闭。响应实时状态等外部来源保持明确待接，不宣称页面功能/生产完成。
- [x] 3.4 接通显式事件Case关联和移动事务，保持租户、已有来源身份命名空间、成员范围版本及历史来源一致。12新+7PG回归最新通过，详见docs/investigation/socai2-case-relations-20261104.md；124仅给Case补固定source_namespace，当前29表459列。Fusion未提供独立来源环境，不能用fusion.v1/connector冒充；按已定输入限制记录，不宣称环境已核实。生产与页面未切换。
- [x] 3.5 实现H人工任务/结果写读与引用冻结，区分完成/修改事实、范围及来源；新增用户显式baseline/prepare补齐成员不变时H→下一轮C入口，保存H不自动生成Run。10项H+5项prepare+6项C1/model-view回归首过，见docs/investigation/socai2-human-tasks-20261104.md及固定汇总；无DDL/预算/页面修改，旧Run不回算。
- [x] 3.6 按实际来源接通产品主机/认证、UEBA/知识和外部身份图必要字段，缺源/空结果/失败/不确定分开；模型角色及范围保留，完整C2从原4次工具预算内留2次给C4、按冻结对象选择前两项来源，其他来源明确预算跳过。12新+2回归最新通过，见docs/investigation/socai2-external-sources-20261104.md及固定汇总；PG读写真实、模型/湖/产品/身份图返回替身，可选来源默认关闭，不宣称供应商实连或完整攻击拓扑已验收。
- [ ] 3.7 在本机独立数据空间完成真实Kafka/Fusion→A/I/C→明确范围H→下一C，先DeepSeek、后VPN窗口远端部署模型，两个后端同语义配对材料各自留存完整请求/结果。先满足固定小批所需的3.13环境、3.14模型前准备和3.10直接准入，未覆盖范围继续待办；实际模型采用/引用仅在本任务核销，核Tool、知识等实际进入模型的来源、H范围、结论变化与数据库字段，不迁移或写回旧业务数据。a/b/c的限定执行不等于本任务或各准备任务全面通过。见local-first-validation-plan-20261105.md和acceptance-plan-20261104.md。

## 审计后调整与最小页面闭环（实施中）

- [x] 3.8 完成整轮容量核算并实施C6调用/请求输出/时间预留：复用三份固定包，只读保留原usage；按用户明确批准的新完整C共享预算48000（旧Run/A/I不改）构造完整两成员及H/比较输入确定可行范围、资源参数与无法容纳项。以代码、完整wire离线可行及限定隔离验证核销本任务，核必要项零静默遗漏、可选补查让出最终资源、usage未知保持及终态交接；真实有效结果由3.7单独验收，仅提前阻断不算整体修复通过。
- [x] 3.9 接通query直接Tool与Deep动态补查的分流，加入C3可见绑定、优先级及原计划身份映射，按新合同版本保存；直接query额外Deep调用为0，同绑定复用、同问题两路线不互相遮蔽，非法范围/无绑定不扩大；定向核共享4次Tool与C6预留、实际调用和C6引用。
- [ ] 3.10 明确并实现能力/容量限制读取，完成语义与依据状态的直接校验：覆盖仅用户无主机、大材料、进程成功/流量/授权反例、H结果变化与纯元数据编辑、部分采用及外部数据更新边界。复用既有PG证据，仅对新增/受影响合同补检查；形成3.7固定输入、预期事实/真值和候选来源，不把替身或离线结果当真实质量。
- [x] 3.11 补Case集合GET和四指标、分页筛选与所需DTO/OpenAPI/字段字典，沿PRD8.1明确服务端统计范围；提供当前判断覆盖/依据状态、pending与活跃轮、H版本及历史所需真实出口。以同租户/权限的隔离数据核筛选total与总体metrics、任务按Case去重、稳定分页和GET无业务写入。
- [ ] 3.12 在既有页面接入Case队列→资料/判断→prepare/start→历史结果→H→下一轮，并接现有成员关联/移动；服务与演示数据分开，补依据状态直白文案、H明确范围和并发冲突、running+pending、partial/系统交接和Q未开放呈现，按实际交付同步当前PRD。H对象/时间保留原可选规则。按用户最新决定，以真实流程保存的数据库与工件导出完成既有页面宽窄屏和回查验证，服务页面直接保存不再是本阶段必需前提；预置回答不算通过，不扩展通用管理/响应/告警事件全量改版。

## 本机优先的环境与来源复用（环境已验，来源部分完成）

- [x] 3.13 复用本机镜像建立专属PG/CH/Kafka/ZooKeeper/Redis及本机API/Fusion，5项healthy、两应用ready；PG29表459列/强RLS/受限角色、CH47写字段覆盖48列表与分离读写权限、Kafka3topic通过，a批真实2告警/2湖日志→1事件。四旧后台按授权停止、旧数据保留；初环境/DDL脚本失败修后留证，非首轮全过。见[环境回执](../../../docs/operations/evidence/investigation-repair-20261105/local-environment/receipt.json)及local-first计划中的a批入湖回执。仅核销环境与数据路径，远端模型质量和整链不在此项。
- [ ] 3.14 复用知识导入及本轮所需资产、内部IOC代码，完成模型前的实际导入/落表、告警标题→PG全文检索、租户范围与候选模型输入核对；直接seed与实际导入分开留证。本批已直接写1项资产、真实ingest函数生成2个SOP块，两标题FTS/API角色读回通过，HTTP导入鉴权未验；完整来源准备尚未核销。a批C2实际选TI/UEBA，知识未进入调查，不称实际采用/引用通过；这些真实质量仍由3.7验收，不反过来成为模型前准备的循环前提。身份图、UEBA生成、Feed及向量路径仅列已有证据和未接边界，C2预算/选择保持。种子回执路径见local-first计划。

## C6 必须收尾

- [x] 3.15 移除C3成功对C6的阻断；在模型格式错误、无服务及前序中断时保存有来源的系统收尾，保持unknown/范围/新鲜度/既有有效判断保护。只兼容已确认的空额外字段并留原答及适配回执，完成本机PG定向验证、新批DeepSeek及原模板读回；旧a/b/c不改写。

- [ ] 3.16 修复人工材料加入后必需历史判断挤占模型视图的容量问题；冻结新候选后验证H→下一C，不扩大已授权预算、不重派旧Run、不把旧判断冒充已吸收新材料。

- [x] 3.17 复用既有案例管道新增正常/恶意意图三组、6告警，真实本机Kafka→湖→A/I→C6→原模板展示并比对。15次DeepSeek、本机累计48/50，三组均保存model/accepted/partial/uncertain判断；03前序拒收后C6仍收尾，但事实扩大未拦截，质量不通过，归原3.10继续处理。见local-first计划最新对比及local-comparison-summary.json；独审仅通过夹具/驱动，不核销3.7/4.1整体质量。

## 完成条件

- [ ] 4.1 在实施任务完成后，由未参与实现者做结束审计，实际问题修复并复核；保留未知/失败/暂缓项，不核销旧r13的5.3。
- [ ] 4.2 实施及审计达标后再归档并核对规格；不以CLI通过或已有组件通过提前归档。

Q业务暂缓，不列本change的未完成实现项。旧r13/5.3不随本批核销，完成实施和验收后再进行独立结束审计与归档。

限定完成证据：3.8/3.9见 docs/operations/evidence/investigation-repair-20261105/capacity-20261105.json、20261105T071222587635Z-executor、20261105T072810622721Z-executor；59项本地和17项不同隔离PG执行器检查通过，独审两处回执问题修后ACCEPT。3.11见20261105T064743665340Z-case_queue及OpenAPI/字段字典，3项PG和10项本地合同通过；只证明所列范围，不核销真实模型质量。

本机续补：C3动态绑定Schema及仅发送层定义名压缩见[10格容量回执](../../../docs/operations/evidence/investigation-repair-20261105/execution-schema-capacity-20261105.json)，59个不同纯检查通过，独审复跑其中11项并限定ACCEPT；不叠加计为70项。a/b的[页面字段回执](../../../docs/operations/socai2-local-page-field-coverage-20261105.json)只核固定导出与已列页面字段，不核销3.12；c失败及新缺口见local-first计划，真实质量仍未通过。

C6投影续修见[最终查询投影回执](../../../docs/operations/evidence/investigation-repair-20261105/final-query-projection-20261105.json)：41项不同相关检查最新通过，独审复跑其中10项，c完整wire离线准入；旧24k包保最低证据后超限299B明确拒绝，不再援用原紧缩通过结论。已加载API的[就绪回执](../../../docs/operations/evidence/investigation-repair-20261105/local-environment/final-local-readiness.json)只核服务与存量，0新模型，用户延期服务器对照；3.7/3.10/3.12/3.14/4.1/4.2仍未完成。

3.15限定证据见[收尾与业务字段回执](../../../docs/operations/evidence/investigation-repair-20261105/local-c6-business-fields-summary.json)：13不同PG方法最新通过，页面31项通过；g首轮有效模型判断，H后轮未通过，累计33次。技术原因与业务结论分字段保存；d/e/f系统判断新增修正版本，原件不改。
