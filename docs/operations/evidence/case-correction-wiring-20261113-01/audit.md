# 局部纠错调用接线限定独立审计

日期：2026-11-13。审计者：未参与本轮实现的 `/root/historical_release_audit`。

**限定审计通过，未发现直接阻塞。** 结论只覆盖本轮离线重放脚本、已保存轨迹及说明，不构成主 change 全面验收。主任务保持 **31/41**，M01/F02、真实可采用 C6 及模型质量仍未通过；未发布、未开展流式工作。

## 实际接线与结果

已只读审阅 [replay.py](replay.py)、实际 `ModelSteps.call`、既有内存 `Ledger`、CaseReview/FinalReview 和 Publication 装配函数。脚本未重写调用/纠错算法：它继承实际 `ModelSteps.call`，由实际接收器拒收后产生反馈，递归调用以 `allow_correction=False` 限定一次纠正；C6 随后执行实际 `make_publication`。锁、事务存储、网关和计量均显式替换，内存 Run 身份不代表创建了数据库 Run。

- 成功重放的 [C3 轨迹](C3-trace.json)、[C6 轨迹](C6-trace.json)各记录首答和一次纠正，共四份历史响应。四份响应摘要与固定05批 C3 原答1/2、C6原答5/6一致；脚本同时断言内存保存的原响应逐值相等，没有去重、补引用或改写旧答。
- 实际调用代码发出的 [C3 纠错请求](C3-correction-request.json)、[C6 纠错请求](C6-correction-request.json)与上一轮预览逐值相等，最后反馈消息分别为 **949 / 467 字符**。脚本从正常 adapter 构造 Schema，再经过正常转换；首份请求与原冻结请求逐值相等，没有混入上一轮新 C3 字段筛选视图。
- 第二份请求携带第一份响应工件 ID 和输入关联，`correction_result` 指向对应的第二份响应。两轮均保留原拒收原因：C3 为 `source_member_mismatch`，C6 为 `delivery_source_not_visible_or_duplicate`。
- C3 返回3条独立有效发现；错误成员项为 `not_analyzed`。第二步 `completed` 是局部分析可保留的执行状态，仍同时记录原答拒收原因，不表示整份原答通过。
- C6 两个模型步骤均为 `failed`；实际 Publication 预览为 `completed` 收尾、`rejected / partial / conclusion=null`、`conclusion_state=unavailable`，建议为空，三个成员的 `conclusion_covered` 均为 false。独立分析保留，不具备总体结论采用资格；本轮没有调用数据库保存、采用或 GET。

## 证据真实性与边界

[summary.json](summary.json)列出的 **92 份前批文件**和 **12 份本轮源码/配置文件**摘要均匹配当前文件。只读对照纠错请求、响应摘要、错误状态和工件 ID 关系，与脚本断言及轨迹一致。[attempt-01.json](attempt-01.json)保留首次脚本重复转换已压缩 Schema、导致首份请求一致性断言失败的事实；这是重放脚本接线错误，不是产品失败，后续改为正常构造后仅转换一次，没有覆盖旧批次原件。

已核 [README](README.md)、[validation.json](validation.json)及根进展/交接中本轮相关表述，均区分替身与真实执行：历史第二答并非模型对新反馈的响应，不能据此判断反馈有效或无效；旧 usage 不是新用量，替身计量不能证明真实预算或时限。内存存储也不证明真实事务、保存读取或采用执行。真实拒收存取沿用[固定05批](../fixed-investigation-20261112-05/flow/readback-checks.json)，接受路径沿用[07批隔离数据库替身流程](../model-input-selection-20261112-07/README.md)，本轮不新增或扩大这些验收结论。

本审计仅新增本文件，未改业务源码、证据、根文档或并行 HTTP 工作；未执行测试、重放、模型、网络或数据库调用。当前可确认精简反馈经过实际调用接线、失败及局部保留处理如实保存到内存轨迹；真实模型纠正效果与完整固定流程仍未验证通过。
