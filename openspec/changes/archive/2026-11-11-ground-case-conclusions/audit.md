# 独立结束审计记录

审查者：`/root/current_release_audit`，未参与业务代码实现。只读检查本 change 差异及已保存的原答、输入、数据库和原 GET 内容；没有再次开展全面审计，没有修改业务文件或调用新模型。

**当前补充结论：ACCEPT，限于项目负责人允许保留已知模型问题后的程序交付范围。模型正文仍 NOT_PASSED；下述原 REVISE 发现保留，不追认为修复。**

2026-11-11 用户明确要求持续问题先记录、推进后续。[范围决定](scope-decision.md)改变发布前置，不改变实际证据。独审复用已有差异检查、定向回执和第五批保存读回，未发现剩余程序功能阻断；没有重跑测试、模型或修改业务文件。发布、归档及 Git/父项目按后续实际回执收口。

## 已核实的实现边界

| 检查范围 | 独立结论 |
| --- | --- |
| C3 数量约束 | 冻结、生成、接收、partial 一致；超限拒收、无截断派发；历史读取与 C6 建议容量保持 |
| 冲突来源与依赖 | 逐 finding/成员需原始 observation 支持，反馈/partial 同一校验；不以引用合法代替正文互斥判断，拒收的 C6 总结不重新采用 |
| 程序所有字段 | observed 原值按来源装配；C6 coverage 由程序补齐六问；越权字段与超长原值拒收，typed 占位不能采用；partial 重算保留结果，历史无标记合同可读 |
| C4 保存回执 | 原 $.state 路径未注册的缺口已修为既有整份 execution_receipt，source_path=null；投影/依赖恢复一致，保存门禁直接检查通过 |
| 材料读取状态 | 实际 material.members 与视图成员数分开；状态/限制/遗漏保留，缺记录 unrecorded，available 不表示全文或业务结论已证 |
| 读取摘要容量 | 逐成员串导致 40 成员/6 回执超限的反例修为按状态计数；完整明细和全部引用保留，7 项定向检查回执一致，未重跑测试 |
| 输入与依赖恢复 | Case title/description 按相同字段投影排除、原件保留；字段含义提示不改原值；无已证影响时范围为空与现合同兼容 |

## 第五批发现（现登记后置）

1. **Deep 将来源标签提升为环境事实。** call-3 的 limitations 仅凭 N2_S15/S41/S69（tags.0=synthetic）断言“非真实生产环境事件”。Case 登记内容已不在当前模型视图，说明输入隔离生效，但标签→环境事实仍是模型问题。该正文已保存并经原 GET 返回：[数据库证据](../../../../docs/operations/evidence/case-grounding-20261111-01/real-model-05/export/database.json#L47732)。
2. **C6 在自由正文重写查询状态。** F1.alternatives 中“所有背景查询均查空”进入 Result.findings[].limitations，与同一 Result.coverage 的 2 completed/empty、4 skipped/not_queried 矛盾。该错误也经 Result GET 返回：[数据库证据](../../../../docs/operations/evidence/case-grounding-20261111-01/real-model-05/export/database.json#L71671)。behavior_nature 仍把 synthetic 标签解释为强烈暗示非真实攻击或测试环境。

程序 coverage、读取计数、观察原值与命令结果未知边界已有改善，不能据此核销其他字段中的错误。第五批实际 C6 accepted/uncertain 并更新 current_assessment，只说明现有结构/引用合同接收；不能记为语义质量通过。

54 次 GET 全部 200，Result 六项关键字段与数据库一致，两份 Deep 工件逐值一致；原材料未改。[第五批审查](../../../../docs/operations/evidence/case-grounding-20261111-01/model-05-review.json) · [受影响读回](../../../../docs/operations/evidence/case-grounding-20261111-01/real-model-05/affected-readback.json)。

## 调整范围前的收口记录

保持 task 2.2、3.2、4.1、4.2 未完成；当前交接与本地 4177 静态资料已更新，五批原答和失败保留。停止本轮继续采样合理，不通过同类提示试到一份可通过的答案，也不降低标准归档。

最小后续是先明确一项职责设计：环境判断所需的直接业务材料或相应人工陈述、标签仅作来源说明的范围、自由正文使用程序状态的约束。若现合同无法约束这些断言，保留未决与人工复核交接，不宣称自动判断已满足目标。确定可执行边界后再定向验收，见 [后续入口](design.md#本次未通过后的推进边界)。

前四批失败、静态修正和对应范围均见 [validation.md](validation.md)，不改历史原答或采用状态。21 仍为 r6，本次未更新、未重启、未归档或 Git 推送。

## 按负责人决定的交付

任务 2.2 的功能保存读取和 3.2 的限定程序审查已完成；两项正文问题继续开放，不再阻塞 4.1/4.2 和后续 Case/H 功能。

21 已一次统一发布 `v1.2-20261111-r1`，仅 API rollout 一次，其余五容器保持；实际 Case profile 与上限 2 核对通过。4177 追加五批共 34 份，原记录保持；三次 Case/Run/Result GET 成功、六项结果字段匹配，前后快照不变。[交付汇总](../../../../docs/operations/evidence/case-grounding-20261111-01/delivery-summary.json)及其直接回执记录实际结果，没有生产模型重测或调查数据写入。

Git 交付使用 `V1.1` 的包含本审计文件及冻结 manifest 的提交，并由 `SpiritHub/add-server-submoudle` 的 `server` gitlink 指向该提交；远端实际 hash 按 Git 引用读回，不在本提交内写自指 hash。归档与封后校验另记录实际执行结果。

### 发布回执独立复核

`/root/current_release_audit` 再次只读复用现有审查，结论 **限定 ACCEPT，未发现新的归档前阻断**。独立确认 r1 API 更新、其余五容器 ID/镜像/启动时间保持，rollout/activate exit 0；三次 GET 均 200、六项字段逐值匹配、快照不变；4177 29→34 与原回执一致。当前文档明确 M01-A/M01-B 后置及 NOT_PASSED，r6 参照与本批区分，未提前宣称 Git 推送完成。

复核没有新增测试、模型或网络操作，不证明新生产模型、Case/H 写入或全面接口验收通过。归档前 49 份当前 Markdown 链接目标有效、git diff --check 与 change strict 校验通过；历史原件的原相对链接保留并由历史导航解释。

### 归档与封后核验

`openspec archive ground-case-conclusions --yes` 已成功，9/9 任务完成，向主规格同步 6 项程序合同及明确后置口径；归档路径为本目录。历史批次原答与失败不改写，主调查仍 31/41。封后 strict 校验回执见 [archive-validation.json](../../../../docs/operations/evidence/case-grounding-20261111-01/archive-validation.json)；本记录描述已实施的程序范围，不把模型质量写成通过。
