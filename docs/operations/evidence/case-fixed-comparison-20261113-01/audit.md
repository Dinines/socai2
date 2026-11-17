# 07批真实调查与不可用比较装配的限定独立审计

审计日期：2026-11-13。审计者未参与本轮实现。结论：**本次真实运行的留存读回及后续固定比较程序修复，限定审计通过；未发现本轮新增的功能阻断。真实模型正文质量仍为 NOT_PASSED，修复后的真实生成效果未验。**

本次只读检查相关实现、已保存请求/原答、数据库导出、GET回执、源码摘要和本轮交接文字，没有运行测试、重放脚本、模型、网络或数据库操作；仅新增本文件。该结论不代替主 change 的结束审计，不构成归档、部署或整体验收结论。

## 程序边界

1. `case_followup_input.py` 在新 C6 请求形成时，依据原比较选择及实际可比 Result 来源冻结 `fixed_comparison`。初次调查恢复 `initial/null`；其余无可用指定综合结论的情况恢复 `not_comparable`、配置说明和空引用。该逻辑没有改写来源、成员范围或历史原件。
2. `case_followup_output.py` 的生成与接收使用同一冻结值：Schema 移除 `comparison`，输出适配校验版本、原选择、可比来源及固定值结构后装配。模型额外输出该字段仍拒收，不以程序覆盖原答来制造通过。原引用、成员和其他交付约束继续执行，纠错次数和预算没有增加。
3. 有可用指定 Result 来源时不会冻结不可比结果，比较字段及原依据规则继续保留。旧冻结输入没有新标记时沿用旧接收行为；07批原末答中的错误比较说明仍按旧规则保存、接受，没有回写历史。`runtime_policy.py` 允许旧配置无此项，新项采用明确版本及配置校验。
4. 本轮变化位于内部输入边界、Schema 和装配配置；HTTP `change_kind/change_summary` 合同及数据库表未变。既有四项直接检查覆盖 initial、not_selected、unavailable 的新旧边界，以及可用指定历史继续比较；本审计只核保存证据，没有重跑。

对应实现：[输入冻结](../../../../services/api/app/socai2/case_followup_input.py)、[生成与恢复](../../../../services/api/app/socai2/case_followup_output.py)、[配置校验](../../../../services/api/app/socai2/runtime_policy.py)。验收边界与[第22节](../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#22-不可比较的固定事实由程序装配)一致。

## 真实07批与修复后验证分开判断

| 范围 | 核得事实 | 限制 |
| --- | --- | --- |
| [真实07批](../fixed-investigation-20261113-07/README.md) | 一次新 Run，复用原 A/I/H；C3 一次、C6 两次，合计 3 次生成、41,320 tokens；一次真实嵌入另记。三份实际请求及原答与导出工件对应 | 运行发生在固定比较修复前；没有 Deep 派发，没有修复后的真实生成 |
| 一次实际纠错 | 首个 C6 因 `delivery_source_coverage_missing` 拒收；1,165 字符局部反馈后，末答将 `impact.alert_ids` 从 A1/A2/A3 改为 A1/A3，同时改动 `analysis.questions[4].answer` 的措辞；支持来源未变 | 这是两处实际变化，不是程序代改原答；不据一次接收推断稳定质量 |
| 实际知识输入 | 正常 C2 的 9 个 selector 查询中，两用途返回同一 AN0846；三个实际请求各展示一份 448 字符正文，保留参考角色与范围 | 三份原答均未结构化引用该知识；进入请求不等于合理使用或改善判断 |
| 真实保存读取 | Result `fbe3de16-515c-4bca-b190-c50e2a00b0e8` 为 accepted / uncertain / partial，并形成当前判断；Case/Run/Result/H 的四份原 ASGI GET 回执与保存关系可追溯 | 真实隔离数据库及 ASGI 读取，不是生产或 TCP 验收；执行收尾、采用与正文质量须分开 |
| [修复后隔离库替身](pg-01/checks.json) | 一条场景先保存拒收基线，再显式选择该 Result 创建新 Run；实际替身 C6 原答和 Schema 均无 comparison，冻结值与 Result/GET 的 change_kind、change_summary 相同，当前判断结论与 Result 一致；旧拒收 Result 保持 | 模型、查询为替身，真实数据库保存与原 ASGI GET；Case 只关联告警，不证明事件关联或真实模型效果 |
| [新配置离线预览](verification.json) | C3 业务正文仍与07实际的 10,894 字符逐字一致；新 C6 为 17,116 字符，移除比较输出槽 | 新预览未派发；旧实际请求、原答和采用状态未重写 |

真实07末答仍存在名称推断自动化、威胁情报未查却写成查询无结果，以及 `not_comparable` 说明声称与本轮 A/I/C3 中间判断一致的问题。首答拒收和末答采用均如实保留。后续程序修复只接管程序已知的比较事实，不代表其他正文问题已经修好。依据见[真实原答审阅](../fixed-investigation-20261113-07/review.json)、[旧答兼容](legacy-answer-check.json)和[固定值读回](pg-comparison-readback.json)。

## 原件、摘要与交接

- 06批 115 份原流程文件、07批修复前 33 份文件摘要均保持；当前 17 份 PG 冻结源码与实现一致，`validation.json` 的 28 份最终源码摘要匹配。两目录 manifest 所列 48 / 32 份文件均匹配。本审计未应用源码补丁或重新执行重放入口。
- 初次离线审阅误以为纠错只改一个字段，已保留 `review-attempt-01.json`；当前回执记录上述两处变化。两次静态导入的原错误，以及只读捕获脚本的 JSON 绑定参数失败均保留；后续补取另存展示快照，没有修改原数据库导出、关联或重派业务。
- 本机静态记录分别 79→80、80→81；没有本轮在线4177发布或入口可用性验收。知识临时转发随真实 Run 结束关闭，不宣称常驻转发已恢复，也不据此确定旧503根因。
- 已核两份 README、validation、源码包摘要和现有最终 Ruff/OpenSpec strict/diff 回执；PROGRESS、交接入口、问题清单 F07、任务和固定流程计划均区分真实07、后续替身验证与旧失败。静态检查通过不替代业务或模型质量结论。

主调查仍为 **31/41**；F02 知识合理使用、M01 等正文问题及完整结论质量不核销。本轮模型实现未部署，HTTP并行发布不在本审计范围，流式和自动反馈重算继续后置。
