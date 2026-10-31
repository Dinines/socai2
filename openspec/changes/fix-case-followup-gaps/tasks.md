2026-10-31执行补充：[审计修复实施](../../../docs/investigation/audit-fixes-implementation-20261031.md)已完成包含新材料的组合验证，Office纠错16929/17018，原报告保持；required/reuse/correction组合通过。当前候选tag为20261031-r3，未部署；下列最后任务继续待办，不以新本地数字替代真实模型复验。

- [x] Implement compact follow-up model view and recorded-budget reconstruction.
- [x] Add explicit required_tools/native tool_choice with compatible empty intent.
- [x] Clarify identifier, empty-result and saved-analysis semantics.
- [x] Run only affected direct examples; preserve all previous failures.
- [ ] Prepare a reviewable resident update and targeted live retest, then record actual outcome.

2026-10-31 规划衔接：新增 [fix-investigation-audit-gaps](../fix-investigation-audit-gaps/proposal.md)
处理进程类型、概况失败模式和原始取材。上述未完成任务由新 change 的 B4 汇总实际组合版本，
同一真实批次回执供两处引用，不重复实施/测试，也不在只有本地结果时勾选。
新材料可能影响追加预算，必须核新的实际组合输入；原 16786/17018 仍只属于原记录。
本次仅补最后一条 Requirement 缺少的 Scenario 并重新做 CLI 结构校验，未新增业务通过项。

原 2026-10-29 记录：OpenSpec CLI unavailable; no strict CLI validation/archive claimed.

Local checkpoint (2026-10-29): six affected direct examples passed. The recorded
Office correction reconstruction falls from 19137 to 16786 allowance units,
below its recorded remaining 17018; this is offline reconstruction, not a new
model result. Full saved evidence and previous failures remain unchanged.
See [local evidence](../../../docs/operations/investigation-followup-fix-local-20261028.json).
The r2 installer/compose and required-Tool runner changes are preparation only;
no resident replacement, new credentials or live retest has occurred. The user
requested a local commit at this checkpoint, so the live task remains pending.
