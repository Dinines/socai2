# Case 有据结论与补查上限验收

状态：本地程序修正、直接检查、实际保存读取、限定独审及一次 21 发布后读回已完成；第五批正文仍 NOT_PASSED。负责人明确将持续模型问题记录后置，独审补充 ACCEPT（限定程序范围）；不改原失败或追认质量通过。[范围决定](scope-decision.md)。下文各批失败及发布前状态按发生时点保留，最终发布事实见末节。

## 改动与边界

分支 `V1.1`，起始 HEAD `45063c97f81b4f2d6bf504a6261ee7087a2353ca`。沿用已完成审计的 A01/A02 及原始失败，不重新全面审查。直接源文件基线见 [baseline.json](../../../../docs/operations/evidence/case-grounding-20261111-01/baseline.json)。

- Case profile 的 Deep/C6 指令明确缺资料、实际反证、已证影响和条件风险的区别；输入中 `$.case` 单独标为案件记录说明，不表示原事件环境或授权。原正文、来源映射和查询实际状态保持。
- `c3_output.max_followups=2` 与指令一起进入 Case profile 指纹，随输入冻结；生成 Schema、普通接收及 partial 使用同一冻结上限。超限记录 `case_followup_limit_exceeded`，不截断、不派发、不额外重试。
- 保留历史 `ExecutionAnalysis` 容量与原结构恢复，C6 后续建议不受 C3 派发数量约束。未变更数据库、告警交接字段、A/I 指令和单 Run 预算。

## 直接检查

[结果](../../../../docs/operations/evidence/case-grounding-20261111-01/direct-tests.txt)：11 passed，Ruff 通过。仅新增 `test_socai2_case_grounding.py` 并复用两个原文件的直接相关检查。

| 检查 | 实际覆盖 |
| --- | --- |
| C3 两项 / 三项 | 真实生成 Schema、解析器、partial 和派发器；两项进入服务 spy，三项在两条接收路径均失败、零派发，原答不被截断 |
| 历史和 C6 | 无新上限字段的历史 boundary 可恢复、读取三项；C6 三项建议仍可按原合同接收 |
| 材料用途 | Deep/C6 的 Case 记录说明独立标注，引用、输入原件不变 |
| 实际查询状态 | 复用 completed/零行、failed、unknown、skipped 的四项查询投影检查 |
| 冻结与局部保留 | 原 profile 漂移拒收、合法范围内的局部保留用例保持 |

上述不连接数据库或模型，派发服务为明确 spy。首次运行 10 passed / 1 failed，失败来自新增测试漏填比较合同的 `result_id`；补齐测试夹具后本组通过，未因该失败修改生产逻辑。不重跑原 56 项审查或全仓测试。

## 独立本地真实链路

入口沿用 `tools/testdata/case_scope_recovery/real_model.py`；新配置为 [real-model.json](../../../../tools/testdata/case_grounding/real-model.json)。使用现有本地 `v12_upgrade_dev`、真实网关与正常 CaseService C1–C6，三条原演练材料在新身份下原值复制。既有业务授权仍未知，不代造业务确认。

证据目录：[real-model-01](../../../../docs/operations/evidence/case-grounding-20261111-01/real-model-01)。模型调用前冻输入、源码和 profile；沿用 6 模型 / 4 工具 / 131,072 token / 1500 秒及 C6 预留 300 秒。没有新生产模型作业。

第一次仅 SSH 预检被本机沙箱拒绝，尚未创建 Case 或发送模型请求；回执另存 `preflight-sandbox-denied.json`。获得网络工具授权后重新进行预检并执行；不重派未知模型调用。

### 首轮实际结果与定向续修

Run `394f505b-b58e-4f98-a33d-ce6ed1212b81`，Case `29826c34-c3e0-55f1-a8e3-5c422521bd33`。C3、两个 Deep、C6 共 4 次真实调用，reported tokens 41,035、费用未知；completed/partial，C6 uncertain 并采用。原材料逐值保持，原 GET 处理函数 52 次读取无 HTTP 错误；没有再跑全字段对账。这只能证明本条保存读取成立。

[正文审查](../../../../docs/operations/evidence/case-grounding-20261111-01/model-01-review.json)判 NOT_PASSED：Deep reason 将 Case 元数据与无引用前序判断当“无人确认授权/查询没返回审批”的事实依据；C6 summary 将 assets 的 completed/empty/0 写成 skipped；conflicts 将命令行为与 synthetic 标签当矛盾。独立审查者同时确认前序事实化及伪冲突是本 change 阻断，数量约束实现未发现阻塞。不能因 uncertain/结构通过/落库成功忽略这些问题。

续修保留全部原答与快照，增强前序原文的待核用途说明和阶段约束，并直接投影程序 C2 回执的简明状态表。新增 Deep/C6 两项状态投影检查，证明前序说法错误不会改变程序摘要；复验两项原分区检查，共 4 passed，见 [input-fix-tests.txt](../../../../docs/operations/evidence/case-grounding-20261111-01/input-fix-tests.txt)。首次这组 2 failed / 2 passed 仅因测试用英文字段名断言中文呈现，修正断言后通过，生产逻辑未因该失败修改。全轮直接检查共 13 个不同用例，未重跑全面审计。

第二批配置 [real-model-02.json](../../../../tools/testdata/case_grounding/real-model-02.json)，沿用材料、环境和预算，新 Case/Run 身份；只针对上述已确认的阻断复验。

Run `b9f5227d-334e-436b-9ede-c24969a71197`，Case `f11ffb73-cbe4-5a0c-b259-e9e33a0b585a`，5 次调用、66,967 reported tokens，含原有一次 C6 引用纠正；completed/partial，54 次原 GET 读取通过。Deep 授权按未知交接，C6 主摘要和覆盖问题逐项区分查空与未查，影响不写成已证损害；但 C6 继续照搬前序无资料的 F2/F3 与 F1 的伪冲突，仍 NOT_PASSED。[原答审查](../../../../docs/operations/evidence/case-grounding-20261111-01/model-02-review.json)

### 冲突来源与依赖校验

按独立复核的最小建议，当前 Case 新响应的冲突须逐 finding、逐成员覆盖其直接 observation 支持，至少两个不同原始来源；生成排除标签、回执及仅查询绑定来源。没有强制所有 finding 使用 observed，保留有原始支持的 inferred 表达。Case 适配器启用同一校验，反馈按具体路径指出缺口；现有 partial 增加可选单元校验，默认历史及其他调用不变，C6 被拒收的总结不重新采用。

[本次定向检查](../../../../docs/operations/evidence/case-grounding-20261111-01/conflict-tests.txt) 11 passed，涵盖新增两项 C3/C6、此前受影响边界及两项原局部保留用例。另对第二批真实 C3/C6 原答作[两项离线回放](../../../../docs/operations/evidence/case-grounding-20261111-01/conflict-replay.json)，伪冲突均明确拒收，独立 finding 保留，原答 hash 不变，没有数据库或模型调用。检查合法引用不代表检查正文真伪。

第三批配置 [real-model-03.json](../../../../tools/testdata/case_grounding/real-model-03.json)，对应上述实际程序修正，仍使用原环境、材料与单 Run 限制。Run `f8cbcde3-09da-4a3f-95ff-048da167a2f1`，Case `296c5ddf-0c63-5067-9c23-8bab829d2b76`；4 次调用、42,281 reported tokens、无纠正，completed/partial，52 次原 GET 读取通过。C3/C6 conflicts 均为空，授权与影响边界改善；但 C6 coverage 声称缺乏已有回执，且把前序错误网络方向升级为 observed，两项均保存并读回。独审 REVISE，不能作为正文通过。[第三批审查](../../../../docs/operations/evidence/case-grounding-20261111-01/model-03-review.json)

### 程序所有字段的职责调整

按设计 2.1 增加冻结 `socai2.case-program-output.v1` 标记及原观察字段表。新 C3/C6 observed 不接收模型 statement，程序逐来源呈现原路径和值；程序所有字段越权提交拒收。原值超出既有文字容量时明确失败，typed 占位只用于逐单元审查，校验仍拒收，不能作为观察保存采用。C6 模型只生成五个业务问题，程序综合材料视图、分析/问题状态、实际查询、冲突与后续/执行记录补齐 coverage；partial 根据保留结果重算。

[14 项直接检查](../../../../docs/operations/evidence/case-grounding-20261111-01/program-output-tests.txt)及[原 C6 反馈检查](../../../../docs/operations/evidence/case-grounding-20261111-01/program-feedback-tests.txt)通过，Ruff 通过。检查包含真实原值装配、擅自提交程序字段拒收、超长明确失败及局部保留、有效零行与未查询/未知数量区别、保留单元重算，以及无标记历史边界保持原文/六问。首次 7 passed / 2 failed 发生于原测试辅助生成器仍给新 C6 生成六问，已按模型边界更新辅助生成器；既有对外合同仍为六问。

第四批配置 [real-model-04.json](../../../../tools/testdata/case_grounding/real-model-04.json)对应这一实际职责改动，已完成。Run `bdecd631-a47f-436e-b3d5-24eabcbbe996`，Case `2a777f77-cbe3-55ab-9c16-e9703727169e`；5 调用、65,360 reported tokens，含一次既有 C6 纠正；completed/partial，54 次原 GET 读取通过。C6 两次来源覆盖错误，最终结论为 unavailable/rejected、没有采用；保留的 impact 问题回答仍把命令行写成已取得用户信息，Deep 把 Case 说明用于非生产业务环境判断，仍 NOT_PASSED。程序覆盖逐项状态正确不能核销正文问题。[第四批审查](../../../../docs/operations/evidence/case-grounding-20261111-01/model-04-review.json)

独审指出的两项实现缺口已修正：C4 查询/材料读取使用现有整份工件 execution_receipt，source_path=null，依赖恢复使用同一字段投影；coverage 单列真实 material.members 状态/限制/遗漏，缺回执 unrecorded，不从视图包含推读取。6 项直接检查通过，包含实际 BaselineStore 保存门禁（仅 SQL 返回替身，无数据库调用）。

第四批正文的定向修正按设计 2.1：配置排除 Case 登记 title/description 并记录遗漏，依赖恢复同样排除；命令/action/outcome 字段旁标注含义，impact 问题旁区分动作、结果、未知影响。无已证变化时，C6 impact 范围与支持不复制全体成员。15 项受影响检查及 Ruff/OpenSpec 通过，见 [action-boundary-tests.txt](../../../../docs/operations/evidence/case-grounding-20261111-01/action-boundary-tests.txt)。首次 13 passed/2 failed 来自测试将“排除两字段”错误断言为“整份 Case 原对象消失”，改为核两字段和原件不变后通过；未因该断言改变生产投影。

第五批配置 [real-model-05.json](../../../../tools/testdata/case_grounding/real-model-05.json)仅针对该实际改动复验，预算与原材料保持；实际结果见下节。五批原答/失败和快照均保留，本地 4177 静态资料为 63 份，21 仍为其独立的 29 份；没有更新 21、归档或 Git 推送。


### 读取摘要容量与本批执行记录

独审发现逐成员读取串在合法的 40 成员/6 回执下超出既有 1200 字符合同，会在整份、feedback、partial 共同入口失败。已改为正文按读取状态计数，完整逐成员明细和引用保留，不截断原回执。[7 项定向检查](../../../../docs/operations/evidence/case-grounding-20261111-01/material-coverage-tests.txt)通过，独审只读确认该静态阻断消除。

第五批首次启动被自动审批拒绝（尚未创建进程/Run），理由为未确认向模型网关发送调查材料。核查三条原材料均为既有 validation/LabTelemetry 演练夹具，现有路由为内网 `192.168.1.43:8000`；保存 [检查记录](../../../../docs/operations/evidence/case-grounding-20261111-01/real-model-05/approval-review.json)，补充事实后同一命令获准执行。未绕过审批、未修改原材料或路由，未部署 21。


## 第五批实际结论与本轮收口

Case `c0ac559a-7272-5ee7-b5f2-9533ab952cc5`，Run `535fc703-4d8a-4274-92ec-c8000c8816a7`。5 次真实模型调用、60,968 reported tokens、费用未知；含一次既有 C3 纠正，首答 `domain_finding_scope_mismatch` 明确失败，原答未改。Run completed/partial，C6 uncertain/accepted，实际更新 current_assessment；该接收状态不能代替独立正文审查。

54 次原 GET 均为 200；Result 的 conclusion/conclusion_state/validation_state/findings/questions/recommendations 六项与数据库一致，两份 Deep 工件内容逐值一致；仅核本批受影响结果，没有全表或全接口矩阵。[读回证据](../../../../docs/operations/evidence/case-grounding-20261111-01/real-model-05/affected-readback.json)。原材料保持，Case 登记字段在当前模型视图中排除。程序 coverage 正确区分 3 个可读取选择字段的成员、模型分析状态、两项完成零行和四项未查询；完整材料回执仍可引用。影响回答保留命令结果/数据访问未知，impact 不伪造变化或影响范围。

[第五批正文审查](../../../../docs/operations/evidence/case-grounding-20261111-01/model-05-review.json)仍 NOT_PASSED：Deep 仅凭 synthetic 标签断言非生产环境；C6 F1 的替代解释写所有背景查询均查空，与同一结果的程序 coverage 矛盾。两项均已保存并读回。另记录时间间隔 1–2 分钟与原三条记录 40 秒不符的质量限制，没有改原答追认正确。独审最终 REVISE，详情见 [audit.md](audit.md)。

实际流程与程序修正可追溯，但任务 2.2 的正文目标未通过；3.2 的阻断未解决，4.1/4.2 未执行。当前不继续通过同类提示和重复模型采样求得一份通过答案；剩余职责设计仍在本 change 明确后再实施。告警交接字段、数据库和部署配置保持，现服务不更新，Git 不推送。

## 负责人决定后的交付口径

上述第五批及当时 REVISE 原结论保持。2026-11-11 负责人明确持续模型问题先记录、推进后续；M01-A/M01-B 开放后置，程序功能/保存读取作为本 change 的已验证交付范围。限定独审补充 ACCEPT，任务 2.2/3.2 按更新范围完成；发布和 Git 回执另按实际补齐。没有追加模型或业务测试。

## 一次统一发布及读取

21 当前 `v1.2-20261111-r1`，处理组件 `processing-20261111-r1`，统一 manifest `a516e85880af8ee14f24077e9e0b3493498215f8076e211e051b05463d9290e5`。本地来源冻结、构建、准备后只进行一次 API rollout，激活核验成功；五项继承服务容器保持。实际加载 `max_followups=2`、`socai2.case-program-output.v1`、Case 登记字段排除配置与本次 profile 指纹一致。[实际运行](../../../../docs/operations/evidence/case-grounding-20261111-01/runtime-after.json)

4177 原 29 份记录保留并追加五批，共 34 份；本地静态资料库独立为 63 份。374 静态文件/375 HTTP 核对通过，工作台容器与运行源码保持。[静态回执](../../../../docs/operations/evidence/case-grounding-20261111-01/static-publication.json)

仅对一个已存在 Case 做 Case/Run/Result 三次 GET，均 200，六项受影响 Result 字段与正式库一致，读取前后相同范围快照不变。[读取回执](../../../../docs/operations/evidence/case-grounding-20261111-01/production-readback.json)。验证脚本错误字段查询及过期 API key 的失败分别保留；改用既有账号正常登录，未新增账号、key 或权限。无新生产模型作业、调查数据写入、DDL 或告警字段变更，不以历史结果读取推断生产新跑模型质量通过。

完整来源及实际边界见[交付汇总](../../../../docs/operations/evidence/case-grounding-20261111-01/delivery-summary.json)。Git 来源锚点为包含本回执的子仓库提交及父项目 `server` gitlink；不把起始 commit 当作含工作树修改的发布源码。
