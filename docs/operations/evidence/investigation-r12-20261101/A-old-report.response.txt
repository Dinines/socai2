# Case调查报告 5fbb643b-975b-4798-8729-801b50ba956f

本次Case调查未形成完整结论，请结合已保存材料和缺口继续处理。

## 查询来源与成员对应
以下由保存的来源生成；事件ID对应不证明因果，未匹配不等于无关。
- [E1](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/E1)：本次工具返回。
  process_activity：查询成功，返回1条记录；范围与截断状态见原证据。
  - E1/rows/0：[A1](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/A1)
- [E2](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/E2)：本次工具返回。
  network_connections：查询成功，返回1条记录；范围与截断状态见原证据。
  - E2/rows/0：[A2](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/A2)

## 发现与依据

## 成员覆盖与判断
选定2条，读取2条；给出判断0条，尚未明确0条，未逐项分析2条，材料不可读0条。
给出判断不等于证实攻击或已解决；背景成员不等于已证明安全。
- d495a0b5-6937-5de1-a7aa-a14af48f8bfe [not_assessed/undetermined]：模型未提供该成员的逐项判断（依据：无）
- 9f3dc42e-087f-5184-801a-d26f11e0ecf9 [not_assessed/undetermined]：模型未提供该成员的逐项判断（依据：无）

## 跨告警关联依据
共同实体或时间接近不等于因果关系。
未给出明确关联条目，不代表已证明全部成员互不相关。

## 来源时间线
按来源时间排列；候选成员仅表示查询主机/来源范围的匹配，不证明因果。
- 2026-10-31T16:01:00+00:00 [告警时间]：[SYNTHETIC INVHTTP-20261101-r11-positive-01] Office启动PowerShell（依据：[A1](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/A1)；来源记录：见原告警；候选成员：d495a0b5-6937-5de1-a7aa-a14af48f8bfe）
- 2026-10-31T16:01:00+00:00 [来源事件时间]：进程：powershell.exe；路径：C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe（依据：[E1/rows/0](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/E1/rows/0)；来源记录：791205b5-b02e-5b67-98ee-20f5779cde43；候选成员：9f3dc42e-087f-5184-801a-d26f11e0ecf9, d495a0b5-6937-5de1-a7aa-a14af48f8bfe）
- 2026-10-31T16:02:00+00:00 [告警时间]：[SYNTHETIC INVHTTP-20261101-r11-positive-01] PowerShell的TCP连接（依据：[A2](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/A2)；来源记录：见原告警；候选成员：9f3dc42e-087f-5184-801a-d26f11e0ecf9）
- 2026-10-31T16:02:00+00:00 [来源事件时间]：powershell.exe：::ffff:192.0.2.80 → ::ffff:198.51.100.80:443（依据：[E2/rows/0](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/E2/rows/0)；来源记录：0f6ef369-c253-51f3-838b-e6e800743bdf；候选成员：9f3dc42e-087f-5184-801a-d26f11e0ecf9, d495a0b5-6937-5de1-a7aa-a14af48f8bfe）

## 未决问题
- 模型未提供该成员的逐项判断（成员：d495a0b5-6937-5de1-a7aa-a14af48f8bfe；依据：无） 缺少：可支持该成员判断的材料或明确分析；建议：补充材料或明确问题后发起后续调查。
- 模型未提供该成员的逐项判断（成员：9f3dc42e-087f-5184-801a-d26f11e0ecf9；依据：无） 缺少：可支持该成员判断的材料或明确分析；建议：补充材料或明确问题后发起后续调查。

## 反证

## 未解问题与限制
- 未取得完整可引用的模型结论，停止原因：invalid_or_unreferenced_conclusion
- 成员d495a0b5-6937-5de1-a7aa-a14af48f8bfe：模型未提供该成员的逐项判断
- 成员9f3dc42e-087f-5184-801a-d26f11e0ecf9：模型未提供该成员的逐项判断
- 未决问题：模型未提供该成员的逐项判断

## 建议

## 本次范围
Case：5fbb643b-975b-4798-8729-801b50ba956f
时间：2026-10-31T16:00:00+00:00 至 2026-10-31T16:04:00+00:00（不含结束时刻）
选定成员：d495a0b5-6937-5de1-a7aa-a14af48f8bfe, 9f3dc42e-087f-5184-801a-d26f11e0ecf9
停止原因：invalid_or_unreferenced_conclusion

## 证据索引
- [A1](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/A1)：告警d495a0b5-6937-5de1-a7aa-a14af48f8bfe，来源事件=791205b5-b02e-5b67-98ee-20f5779cde43
- [A2](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/A2)：告警9f3dc42e-087f-5184-801a-d26f11e0ecf9，来源事件=0f6ef369-c253-51f3-838b-e6e800743bdf
- [E1](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/E1)：process_activity，来源可用=True，记录ID=791205b5-b02e-5b67-98ee-20f5779cde43
- [E2](/api/v2/investigation/cases/5fbb643b-975b-4798-8729-801b50ba956f/investigations/22b48b78-3716-5a64-994f-788d020dc760/evidence/E2)：network_connections，来源可用=True，记录ID=0f6ef369-c253-51f3-838b-e6e800743bdf
