# 任务3b首段执行：独立本机审阅

2026-11-17复核03：**实际链部分通过，Case未恢复，3b未完成。** 实施方实际原件取回后，测试侧独立核对了Kafka回执、材料/湖/PG原值、模型原答及HTTP原始响应；没有新连服务、投递、调用模型或改动实现。结论见[独立结论03](independent-review-03.json)，核对过程为[review-actual-03.py](review-actual-03.py)，读取原件摘要见[review-evidence-03.json](review-evidence-03.json)。

| 本轮边界 | 独立核对结论 |
| --- | --- |
| PART1材料与处理 | 2条context、1条告警的Kafka ACK与prepared原件摘要一致；2条湖记录的身份、时间、类型及OCSF原值一致，告警PG原件和来源关联一致；A/I各1个完成Run |
| 保存与HTTP读取 | 使用修正校验器按实际请求顺序重放已保存的37次GET，无组装目录或替换响应；7步骤、21工件及结果核对通过。初次/修验PG快照相同，修验PG前后摘要一致；这些GET由实施方实际执行，本轮只审原件 |
| 模型与无变化检查 | A/I共2次真实请求及原答与PG工件相同，均stop，共4068tokens；明确列出的输入标记扫描0命中。显式I check为no_changes，0 attempt/Run。正文质量未全面验收，费用未知 |
| Case失败 | 创建201，但初始task在input阶段DBAPIError，0 Case Run/Result；客户端completed_with_issues和原失败保留。创建及等待终态不等于调查成功；PART2未执行，后续上下文查询/Case处理未完成 |
| C1修正 | 最小变更只将嵌套取数绑定到唯一外层任务别名，逆转该变更后的摘要与21部署源文件一致。实施方保存的真实只读记录中，旧SQL在两个Case均21000；修正后分别取1/4成员。测试侧再与新/旧真实PG快照的冻结输入、Run、任务、原答和回执逐一核对，重装材料与两份C1上下文完全相同，成员互不混入 |
| 部署与复验 | 三个活动服务的前后容器/镜像身份一致。C1修正仅在独立只读进程验证，尚未发布、未恢复Case；17项既有终结材料检查及Ruff独立通过，见[local-checks-03.json](local-checks-03.json)。本轮没有独立执行真实数据库查询 |

C1取数修复的源码和只读证据可接受；这不替代修正发布后的Case真实执行、结果保存/读取或3b整体验收。原01失败、02本机复核及实际执行02终态均保持。

## 复核02：客户端三项修正

2026-11-17复核02：**F1–F3三项修正的本机独立复核通过，21真实首段验收仍未由本轮核销。** 对照实现方`source-freeze-02.json`的9个文件摘要，独立复跑32项定向检查及受影响文件Ruff，均通过；复核前后源码摘要一致。实际回执见[local-checks-02.json](local-checks-02.json)、[独立结论02](independent-review-02.json)。

[probe-02.py](probe-02.py)复用01的受控对象材料，确认context、告警和对象形式raw_data的同源身份一致，类型与时间保持，prepare保存/读取一致且原材料未改。另以已保存真实A/I响应重放9项检查：两类正常结果均通过，修改正文或移除task/Run目录结果引用均被拒绝；历史I冻结3成员、当前4成员仍通过，篡改冻结范围则被拒绝。详见[probe-results-02.json](probe-results-02.json)。这只核保存读取合同，不验模型正文正确性。

复核02没有连接真实服务、投递Kafka或调用模型；响应重放中Run目录项为明确组装的离线输入。01失败回执、原始材料和历史真实响应保持不变。实际执行02及其Case结果仍需另交同一执行的PG/HTTP和模型原件，不能由本次离线通过追认为完整链通过。

实施方随后交接实际执行02的终态：2条context入湖，1A/1I完成，显式I check为no_changes；Case创建201，但initial task在input阶段以DBAPIError失败，Case Run/Result均为0，客户端报告completed_with_issues。此段是实施方交接，测试侧尚未收到并独立核对完整实际回执。只读实现源码可确认`source_sql()`将`:id`替换为`i.id`，嵌套的`SOURCE_SQL`同样声明`incidents i`，使parent筛选成为`i.id=i.id`；这与实施方在同租户两个事件下复现的SQLSTATE 21000一致。修复验收须保留多事件共存，核对每个Case只取本事件的冻结材料；不能用只剩单事件或加LIMIT 1掩盖串案。修正源码、只读C1验证及后续真实Case流程分别记录，原失败task和本批未完成结论不改写，不临时替换21活动服务。

## 审阅01：原发现与范围

2026-11-17，**需要修改，暂不判定本机验收通过**。本轮只读实现源码，复跑原16项材料检查及新增5项执行检查，21项通过；另做三个直接离线补查，发现如下缺口。没有修改工具实现、原材料或历史回执，没有连接21、发送数据或调用模型。

源码绑定与测试输出见[source-read-01.json](source-read-01.json)，补查脚本为[probe-01.py](probe-01.py)，实际结果见[probe-results-01.json](probe-results-01.json)。脚本只在本目录创建一次性受控副本与输出；其中已保存HTTP响应的重放和受控修改不代表真实HTTP/模型执行。

| 编号 | 位置与问题 | 直接复现及建议 |
| --- | --- | --- |
| F1 / P2 | `acceptance_session.py:81`仅映射字符串形式的raw_data | 将已有OCSF JSON字符串改成同值JSON对象，告警和context材料均可通过prepare，但外层event_id/uid已改新UUID，raw_data.uid仍旧值。应在已识别OCSF对象内同步同源身份，或在prepare前明确拒绝不能保持一致的形式；不要带着不一致wire继续 |
| F2 / P2 | `acceptance_verify.py:26`只核Case结果，未核A/I结果内容 | 保存的真实I1回放基线通过（2steps、7artifacts、9次保存响应读取）；只把HTTP Run详情的`result.summary`改为与PG不同的受控值，校验仍passed。snapshot已取A/I结果，应按真实结果ID/source_run_id及当前HTTP投影核原值/结果引用；这是保存读取一致性，与模型正文质量无关。本轮直接复现I，A存在同一未比较分支 |
| F3 / P2 | `acceptance_verify.py:71`将历史I冻结总成员数与当前成员数强制相等 | 真实02的I1冻结3成员，当前事件4成员；原I响应未改即触发`incident_frozen_membership_mismatch`。单part多告警逐条处理，I initial先完成、后续check再更新时同样会出现合法历史范围。各Run应对照其冻结输入/成员，当前事件全量单独核对，不能用当前范围覆盖旧轮 |

F2的离线基线只取真实I1记录，当前成员集合限制到其冻结3成员；Run目录项由该保存Run组装，步骤/工件目录及正文使用实际保存响应。F3恢复真实当前4成员，其余响应不变。原PG/HTTP文件摘要在补查结果中保留，受控差异不回写历史文件。

当前可确认的源码边界：context ACK及湖读回先于告警；逐告警等待initial A；事件initial后单次check；Case沿allocations/initial_task等待；质量诊断未作为下游硬门槛。执行目录独占、HTTP写前意图和Kafka ACK回执保留，主入口拒绝重复run，未知发送停止依赖动作。此处为源码与现有受控测试范围的结论，尚不是21真实链验证。

新增正常流程测试使用FakeConnections，且替换verify_readback，只证明编排分支；不能据其通过宣称真实PG/HTTP合同已验。修复F1–F3并冻结后，定向补查即可，不新增压力或恢复框架。21真实1A+2context/1事件Case原件仍待实现方交接；另part保持只准备，3a历史验收不改，任务3整体及正式Docker交付仍未完成。
