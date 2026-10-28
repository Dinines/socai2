# Case调查报告 be4aeda2-a89b-47e6-a6f9-285b1a7e8723

告警 A1 和 A2 均指向主机 DEMO-FIN-11 上的可疑活动，涉及 Office 启动隐藏 PowerShell 和脚本进程向 198.51.100.41 建立连接。然而，工具查询（E1, E2）在告警指定的时间窗口内均未返回任何进程或网络连接记录。网络锥和记录存在显著的证据缺口：告警主张的具体进程（如 WINWORD.EXE、PowerShell、脚本进程）无法在工具结果中得到验证，且网络连接工具的无结果无法排除历史流失或采集失败。现有材料难以确认攻击是否发生或仅共享上下文。

## 发现与依据
- 告警 A1（Office启动隐藏PowerShell）和 A2（脚本进程向文档地址建立HTTPS连接）均报告于同一主机 DEMO-FIN-11 和相似时间窗口内，涉及同一账户 demo.finance 和相同的目标 IP 198.51.100.41，显示共同背景。（依据：[A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A1), [A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A2), [T1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T1), [T2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T2)）
- 工具查询（E1, E2）在指定时间窗口内对 DEMO-FIN-11 无任何进程或网络连接记录返回，无法验证告警中提及的进程行为或网络连接。（依据：[E1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E1), [E2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E2)）
- 分诊判断 T1（true_positive）和 T2（needs_review）引发不同结论。T1 基于纯净告警断言隐藏 PowerShell 为恶意，T2 则保留疑问，认为无法仅凭合成 IP 断定安全或危险。（依据：[T1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T1), [T2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T2)）

## 成员覆盖与判断
选定2条，读取2条；给出判断0条，尚未明确2条，未逐项分析0条，材料不可读0条。
给出判断不等于证实攻击或已解决；背景成员不等于已证明安全。
- 4c71eec2-77da-5b81-b68a-72801d55ea24 [unresolved/background]：告警 A1 声称 Office 启动隐藏 PowerShell，但工具查询结果不支持，存在证据缺口。（依据：[A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A1), [E1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E1)）
- f7af404b-26a6-5d15-bd6c-3a872bdaf451 [unresolved/background]：告警 A2 声称脚本进程向文档地址建立连接，工具查询结果不支持，需要进一步调查。（依据：[A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A2), [E2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E2)）

## 跨告警关联依据
共同实体或时间接近不等于因果关系。
- 4c71eec2-77da-5b81-b68a-72801d55ea24, f7af404b-26a6-5d15-bd6c-3a872bdaf451 [shared_context/hypothesis]：共同主机 DEMO-FIN-11、用户 demo.finance 和 IP 198.51.100.41，以及相似时间。（依据：[A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A1), [A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A2), [T1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T1), [T2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T2)）

## 来源时间线
按来源时间排列；候选成员仅表示查询主机/来源范围的匹配，不证明因果。
- 2026-10-25T03:30:16.539577+00:00 [告警时间]：Office启动隐藏PowerShell [DEMO-FIN-11]（依据：[A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A1)；来源记录：见原告警；候选成员：4c71eec2-77da-5b81-b68a-72801d55ea24）
- 2026-10-25T03:32:16.539577+00:00 [告警时间]：脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11]（依据：[A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A2)；来源记录：见原告警；候选成员：f7af404b-26a6-5d15-bd6c-3a872bdaf451）

## 未决问题
- 告警 A1 和 A2 的时间窗口内为何工具查询返回无记录？（成员：4c71eec2-77da-5b81-b68a-72801d55ea24, f7af404b-26a6-5d15-bd6c-3a872bdaf451；依据：[E1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E1), [E2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E2)） 缺少：扩展事件湖覆盖范围或验证采集系统状态；建议：检查事件湖配置，确认是否遗漏进程或数据记录。
- 告警 A2 中的 'synthetic address'（198.51.100.41）是否真实被连接，或者仅作为日志标记？（成员：f7af404b-26a6-5d15-bd6c-3a872bdaf451；依据：[A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A2), [E2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E2)） 缺少：验证网络连接记录的存在与否和路径信息；建议：确认 IP 198.51.100.41 在主机或网络日志中的实际使用情况。

## 反证
- 工具记录 E1 和 E2 在无结果情况下不提供正面否认，但工具记录 E1 和 E2 不返回告警 A1 和 A2 中描述的任何内容，与事件湖查询结果不一致。

## 未解问题与限制
- 缺少进程树（父/子进程链）以确认告警 A1 中声称的 WINWORD.EXE 启动 PowerShell 的因果关系。
- 缺少脚本进程的确切身份、路径和命令参数，无法验证告警 A2 中提及的进程。
- 工具在告警时间窗口内无记录返回，原因可能是采集失败、时间窗口不匹配或流量未记录，需确认事件湖覆盖范围。
- 没有脚本内容或哈希值，无法确认进程的真实性和意图。
- 198.51.100.41 的合成地址特性未经验证，需确认该 IP 在时间窗口内的使用情况。
- 部分历史告警摘要仅提供前600字符，未核对完整摘要。
- 成员4c71eec2-77da-5b81-b68a-72801d55ea24：告警 A1 声称 Office 启动隐藏 PowerShell，但工具查询结果不支持，存在证据缺口。
- 成员f7af404b-26a6-5d15-bd6c-3a872bdaf451：告警 A2 声称脚本进程向文档地址建立连接，工具查询结果不支持，需要进一步调查。
- 关联待核实：共同主机 DEMO-FIN-11、用户 demo.finance 和 IP 198.51.100.41，以及相似时间。
- 未决问题：告警 A1 和 A2 的时间窗口内为何工具查询返回无记录？
- 未决问题：告警 A2 中的 'synthetic address'（198.51.100.41）是否真实被连接，或者仅作为日志标记？

## 建议
- 扩大进程和连接查询的时间窗口，确认事件湖是否覆盖告警时间段 2026-10-25T03:28:00+00:00 至 03:37:00+00:00。
- 请求使用其他工具（如安全组件日志或主机资产管理）对 warnings to get process and network activity logs during the alert window.
- 针对 IP 198.51.100.41 查询威胁情报或确认是否为文档解释的合成地址，并确认脚本进程的身份。
- 确认过程事故是否记录了进程的执行情况，无记录不等于安全。

## 本次范围
Case：be4aeda2-a89b-47e6-a6f9-285b1a7e8723
时间：2026-10-25T03:28:00+00:00 至 2026-10-25T03:37:00+00:00（不含结束时刻）
选定成员：4c71eec2-77da-5b81-b68a-72801d55ea24, f7af404b-26a6-5d15-bd6c-3a872bdaf451
停止原因：analysis_complete

## 证据索引
- [A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A1)：告警4c71eec2-77da-5b81-b68a-72801d55ea24，来源事件=bdb56855-5018-567e-b10d-68e7e7bb7073
- [T1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T1)：分诊记录1c92c9d5-e2e8-453e-ac8d-1bf074629692（分诊判断）
- [A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/A2)：告警f7af404b-26a6-5d15-bd6c-3a872bdaf451，来源事件=2d58f3fd-0e29-5e9b-bf0e-8fabe878cd72
- [T2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/T2)：分诊记录066e345c-6212-41fa-8425-efd9c24fe757（分诊判断）
- [E1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E1)：process_activity，来源可用=True，记录ID=无
- [E2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/218257e8-0611-5a59-b13d-6d86f06a9413/evidence/E2)：network_connections，来源可用=True，记录ID=无