# 空查询原因与报告边界修复（2026-11-01）

**后续状态：** 49a04eb 已随 r11/a543ad6 部署。用户选择新建 synthetic 样本后，两次正式查询各返回 1 行，报告仍未通过；见[r11回执](../operations/investigation-r11-positive-fixture-20261101.json)和[当前审阅指南](review-guide-20261101.md)。

下文保留部署前的只读来源核对与本地直接验证记录。当时线上为 r10/51086a4，没有新 Run、模型调用、数据写入或更新；当时的数据数量不能用来描述新增 r11 样本后的全库状态。

## 查明的数据情况

两个已授权租户中，6条非空 raw_event 告警均属于生产租户。该租户湖内有6行，class_uid全部为3002；另一个fixture租户只有3条4001网络记录。查询数量少于本次100条上限，列表没有因该上限截断。

Office主机的两条湖记录与告警时刻相近，但 raw_payload 明确是 `user.session.start`，描述为成功登录，process_name为空；event_id也不同于告警的source_event_ids。它们是不同类别的数据，不能作为Office进程或外联证据。当前进程1007/网络4001过滤正确，不能为了非空结果放宽类别过滤。

此前仅凭精确来源ID未命中，尚不能判断湖里有哪些数据；本轮补查确定当前湖内只有该组登录数据，没有对应的进程/网络记录。仍不能据此判断历史上是否入过库、何时清理或哪段管道遗漏。本轮未把同主机、近时间当作来源身份匹配。

## 已完成的最小功能修复

- 查询、正式报告、紧凑纠错共用证据规则：空结果只表示本来源、本范围无匹配，不反证告警，不推断安全、采样、阻断或丢日志；无依据原因只作待核问题。
- 主调查模型视图仅在同一告警的旧摘要与T理由完全相同，或明确截断且是其前缀时去重，保留saved_analysis_refs；不同判断保留，原始账本和raw不改。追加沿原省略规则。
- 空结果给模型明确coverage/absence_reason=unknown。程序生成的query_sources增加tool/query_scope/query_status/returned_count，Markdown明确成功零条与不可用（数量null），保持历史复用说明。

7个不同受影响直接用例的最新结果通过，含2新增：原r10完整输入去重且不改账本；空/失败状态跨模型阶段、报告、读回保持。另覆盖首次Schema报告、两组旧真实输入的预算、来源复用和产品Tool。不是单次7项重跑；初次额度超限及旧精确字段断言失败均保留。最终冻结Office主调用14182≤15074、网络12244≤12296；原预算和一次纠错保持。

**尚未证明新真实报告语义通过。** 这次修正输入规则和程序事实展示，没有新增通用自由文本语义校验器；旧r10错误文字不会因为此次修复自动被校验拒绝。其原报告仍保留，OpenSpec仍16/17、5.3未完。

当时所缺正向样本已在后续 r11 批次由用户选择新建，旧登录记录和旧报告保持，未回填旧证据。r11 非空结果没有验证空查询推理和 T 摘要去重的真实模型效果；这两项边界仍保留。当前用户要求只整理文档，后续不自动派发新调查。

[完整回执](../operations/investigation-source-boundaries-20261101.json) · [来源清单](../operations/evidence/investigation-source-boundaries-20261101/source-alignment.json) · [Office湖内原文](../operations/evidence/investigation-source-boundaries-20261101/office-lake-payloads.json) · [最后定向验证](../operations/evidence/investigation-source-boundaries-20261101/direct-final.txt)
