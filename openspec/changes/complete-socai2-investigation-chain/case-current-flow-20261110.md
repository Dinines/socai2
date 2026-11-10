# 当前 Case 流程实测

## 范围与直接验收

2026-11-10，项目负责人在后续顺序确认后要求“开始推进”。沿现有 3.30／3.7／3.10／3.16 执行独立批次 `case-current-flow-20261110-01`：先验证当前部署的两个 Case 首轮，再选一案核人工反馈后的再次调查。功能必需的读写接线和配置直接随功能处理；告警交接字段、已保存原答及已结束 Run 不改写。

输入复用正式库中两组明确标记的演练告警及已有 A/I 原答，分别来自 `production-multialert-20261108-01` 与 `production-multialert-20261107-01`。每组新建 Case、使用独立 operation key 和 Run；不重派历史任务，不新增原始观测、知识或确定性良恶标签。第一组检查登录、进程、外联之间的关联依据与实际补查；第二组检查未记录的事件归并依据及证据不足。旧 A/I 结果仅作历史判断，不当作独立事实或当前模型的 A/I 验收。

执行前验证部署与本地源文件／策略一致、正式身份、源材料和离线引用映射。模型调用、工具、请求容量和时限按实际加载策略；两个首轮逐案执行，结果明确结束后再推进下一轮。出现连接中断或 unknown 时先核数据库，不盲目重试。没有触发 Deep／知识检索时如实记录未覆盖。

直接验收分别记录：

- C1/C3/Deep/C6 实际可见材料、引用来源／角色／成员范围、必要前序正文及完整请求容量。
- 工具是否实际调用、成功／失败／查空及后续引用；知识指导不作为本案事实或执行授权。
- 原答、纠正、校验、装配、Result、当前判断、证据目录、报告与 GET／数据库逐值对应；交付完整性和正文质量单列。
- H 内容只陈述实际可核的材料缺口及明确范围，不虚构人员授权或调查结论；后轮核新增反馈、历史对照、采用与新鲜度。
- 本机 4177 保留历史并新增本批记录；问题登记、交接和进度同步；结束做独立审计。

本批不以保存成功认定模型正文正确，不因单后端验证勾选整个 3.7，不把手动调查结果推断为自动消费通过。页面写操作和自动流程仍按已确认的顺序另行验收。

## 证据与结果

证据目录：`docs/operations/evidence/case-current-flow-20261110-01/`。两个首轮及一案 H 后调查均已结束，均为 `completed/partial` 且最终结论未采用；原始回执保持。当前模型引用错误由现有校验如实拒收，不通过删改原答追认成功。

用户明确回复“你帮我补充”，授权助手依据实际保存的材料整理 H 内容。本轮反馈限定为“验收过程中的材料完整性核查”，显式说明由助手代拟，不冒充业务人员授权、访谈或额外采集事实。核查覆盖进程启动与命令效果、不同动作 source_ip 的角色区别、关联与因果、实际查询状态及授权缺口。具体正文、三条成员、时间窗口与十项来源见本批 `H-complete-request.json`。

H 验收通过 `production_human_probe.py` 调用当前镜像内的 `HumanTaskService.write`，复用已核对的生产 profile、现有处理账号与正常用户认证；请求和凭据经标准输入传递，凭据只短暂存于容器 tmpfs 私有文件。先创建任务，再完成为独立修订，按既有任务合同保存和 GET 读回。该脚本是服务层验收适配器，不是新的业务接口；`skip_specs: true`，不改 H/告警合同或部署，不宣称已开放 HTTP 写入。后轮仍经当前正式 Case 作业入口启动。

## 本批发现的直接修正

实际 Deep/C6 原答把 `execution_receipt` 用作结论依据，现有接收校验正确拒收，但生成 Schema 的来源枚举也包含这些程序执行回执，前后约束不一致。当前修正限定 `case_followup_output` 的可选证据编号：Deep 的支持／反证和 C6 的 conclusion/comparison/impact/recommendation 依据槽排除执行回执；C6 analysis 仍可引用查询覆盖信息。实际执行状态完整留在输入和来源映射，不能全局删除。无可用证据时仅允许空依据数组，并按原合同说明待核限制。

现有接收校验保持，不修改告警／H／数据库字段，也不改写历史原答或失败。对应规格先严格校验后实施，使用 JSON Schema 与原解析器的配对检查验证，并经统一发布入口部署。此修正不代表事实扩大、C3 成员范围或 C6 发现关联问题已解决。构建目录保留未激活候选，实际生效来源以本报告的激活回执为准。

## 实际调查与质量结论

所有模型调用均发生在发布 `v1.2-20261110-r2`，逐次请求及模型路由由 [run-config.json](../../../docs/operations/evidence/case-current-flow-20261110-01/run-config.json)和保存工件固定。后续部署修正没有重派这些 Run，也没有改写实际执行来源。

| 样本 | Case / Run | 模型调用 | reported tokens | 整轮耗时 |
| --- | --- | --- | --- | --- |
| C01 首轮 | `17fef155-8dc3-532b-891a-b3d362c58fc1` / `6fc71a3d-288a-4a19-a5bb-c70f2c044eb5` | C3、Deep、C6，共 3 次 | 46,862 | 164.465404 秒 |
| C02 首轮 | `f77924b6-be9c-5754-a96e-690db0f904b3` / `a2ffe2df-b311-44e8-a8c5-a6b12bca78d8` | C3、C6，共 2 次；没有触发 Deep | 33,657 | 156.580205 秒 |
| C01 H 后 | 同 C01 / `c0d94909-f0fe-4dbe-9cef-167881c2bb5d` | C3、Deep、C6，共 3 次 | 73,972 | 165.368113 秒 |

合计 8 次、154,491 reported tokens；费用为 unknown/unpriced，不能记零。三轮均保存为 `completed/partial`，`stop_reason=partial_analysis_saved_conclusion_rejected`，最终结论拒收；两案 `current_assessment_id=NULL`。相应 Result 分别为 `c8536bbc-edd9-4bb5-b2c7-ae81ec6abde6`、`086218be-740c-4521-8752-49fb738696d8`、`3b6f9eff-5c8c-4a9a-84de-02ffa76e0e73`。后轮明确比较 C01 首轮 Result，不能把比较对象当作已采用判断。[逐轮统计与工件定位](../../../docs/operations/evidence/case-current-flow-20261110-01/execution-summary.json)

C3 三次都有 `source_member_mismatch`，保留独立有效部分。Deep 两次因 `execution_receipt_is_not_evidence` 拒收。C6 三次分别出现 `invalid_conflict_findings`、`unknown_domain_finding`、`execution_receipt_not_conclusion_evidence`。本批已修正生成 Schema 与接收校验间可确定的执行回执约束差异，成员范围和发现关联没有通过降低校验或伪造引用解决。

正文仍有明确问题：把 `process_start` 成功扩大为 PowerShell 命令完成／用户枚举效果；把登录来源 IP 与外联本机源 IP 的不同角色解释成异常 IP 切换或横向移动；把未执行的资产／历史查询写成查空；把认证活动查询描述为能核实业务授权。H 已指出这些限制，但后轮仍重复部分问题。材料是演练观察，没有独立良恶真值，不报准确率；模型质量为 **NOT_PASSED**。

工具实际状态单列：三轮 threat_intel／ueba 完成且返回 0；两个首轮的 authentication_activity 查询完成且返回 0。assets／history／knowledge 因 `tool_budget_reserved_for_evidence` 跳过，graph 为 `source_not_connected`。没有知识查询或实际使用的正向验收结论，也不因查空认定行为安全。

## H 保存、传递与新鲜度

任务 `77f645bf-a6a4-56fc-aa54-1c1f968bb37b`：创建为修订 1，完成为修订 2，随后只修改负责人／期限为修订 3。范围包含 3 个告警、明确时间窗口及 10 个来源（3 项观察材料、7 项查询执行回执）。核查正文保持来源角色，不把执行回执升级成行为证明。

完成修订 `3a88fefd-a3af-4bc9-8bad-9fdf03ef384c` 的正文完整进入后轮 C3、Deep、C6，分别映射为 `human_statement` 来源；映射依托 C1 输入工件中的冻结反馈路径，并非虚构新的 `task_revision` 来源类型。修订 3 保持正文、范围、来源、完成人和完成时刻；首轮新鲜度为 `stale/human_feedback_changed`，后轮保持 `current`，没有把管理字段变化算作新证据。[修订检查](../../../docs/operations/evidence/case-current-flow-20261110-01/H-metadata-check.json)

H 服务写入、三版不可变保存和五项详情／修订 GET 逐值核对通过。该结论限定传递与保存；模型正确利用、业务人员确认和前端写操作没有因此完成。

## 修正验证及数据库对应

- 模型边界 20 项测试通过，包含执行回执唯一来源／混合来源、Deep 和 C6 四个受限槽、C6 analysis 保留查询覆盖引用的配对 Schema／解析检查。
- 处理及统一发布 26 项测试通过；Ruff、OpenSpec strict 均通过。5 份保存的 Deep/C6 原答离线复验确认受影响引用被修正后的生成 Schema 拒绝；这不是新的真实生成或质量验收。
- 核验器支持空当前判断并拒绝伪造判断，补齐 H 全字段核对；Case 及活动集合从同一只读快照的同租户主体关系取值，不假定只有一个 Case。
- `readback-01` 因核验器未处理空判断中止；`readback-02` 的 365 个 HTTP 状态均符合预期，但有 42 个跨 Case 对账误判。原回执保留，不能称首轮全过。修正后的 `readback-03` 为 365 GET、357 个 200、8 个预期 404，**16,820 项检查零失败**，读取前后快照一致。
- 独立活动检查覆盖 25 条活动、52 个匹配目标，另有 **1,083 项通过**，不混入上述检查数。
- 两组来源原有 199＋167 行没有变更或丢失；ORM、机器字典、JSON 合同及 V1 建表原件与已发布基准一致。本批无 DDL／GRANT，无告警交接字段变化。正常验收身份的临时 API key 使用既有 scopes，有效期一天，凭据仅存私密文件。

[初验](../../../docs/operations/evidence/case-current-flow-20261110-01/local-validation.json) · [最终核验脚本及完整离线重放](../../../docs/operations/evidence/case-current-flow-20261110-01/final-validation.json) · [原答离线复验](../../../docs/operations/evidence/case-current-flow-20261110-01/wire-repair-check.json) · [最终读回](../../../docs/operations/evidence/case-current-flow-20261110-01/readback-03/summary.json) · [独立活动检查](../../../docs/operations/evidence/case-current-flow-20261110-01/independent-activities.json) · [来源保持](../../../docs/operations/evidence/case-current-flow-20261110-01/source-preservation.json)

## 21 与 4177 交付

已激活 `v1.2-20261110-r4`，处理组件 `processing-20261110-r4`，处理镜像 `sha256:c68c72a9cfe6fa04f6963582d65ce49d73cbf5355c0d72dcf1905d3ecb84776c`。统一 manifest 为 `907207f5972c8f20344088ebffbdf01e23425ac309cff9ae9d85b36b5ebf8787`；策略 hash `ea886f6aba7858d7a894efb2659d78d11299e2e30ca40956fcbd80ef0b2f2130` 保持。API、工作台更新，其他继承服务容器身份保持，6 服务健康；实际 A/I/Case profile 核验通过。[激活回执](../../../docs/operations/evidence/case-current-flow-20261110-01/unified-activate-20261110T104633458561Z.json)

Case HTTP 写开关仍关闭，自动消费者暂停，迁移关闭。模型单次 300 秒、Case 1500 秒、C6 预留 300 秒及实际单 Run 上限保持；本批没有通过放大预算追认质量。

4177 从本批最终读回追加两个 Case 的原件和页面：本机保留 49 份记录，21 保留 18 份。静态发布核对 199 个文件和 200 次 HTTP 读取，原有记录／文件及容器保持；三轮均显示部分交付和拒收，不把工件存在当作质量成功。[静态发布回执](../../../docs/operations/evidence/case-current-flow-20261110-01/workbench-publication.json)

## 结束边界与后续

本批完成真实流程执行、H 传递、直接缺陷修正、部署、数据库／字段读回及交接更新。独立结束审计为限定实现与交接 ACCEPT、0 项必须修正，模型质量 NOT_PASSED；[审计回执](../../../docs/operations/evidence/case-current-flow-20261110-01/independent-audit.json)保留边界。Git／父项目发布随实际回执收口。3.7、3.23、3.30 的整体质量范围未完成，不归档 change。

下一步先处理 C3 成员范围、C6 发现关联和正文事实扩大，用独立批次核真实效果；另取适用样本核知识实际查询与使用。页面写操作及 P01–P04、自动流程按既定顺序推进，权限设计不作为独立前置。[当前问题](../../../docs/investigation/current-issues.md)保留各项验收落点。
