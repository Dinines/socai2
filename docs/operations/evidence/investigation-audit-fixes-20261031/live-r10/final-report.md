# Case调查报告 be4aeda2-a89b-47e6-a6f9-285b1a7e8723

告警 A1 声称 WINWORD.EXE 启动了隐藏 PowerShell 进程 (PID 4200)，告警 A2 声称该进程 (PID 4200) 向 TCP/443 连接到了 IP 198.51.100.41。然而，直接调用 process_activity 和 network_connections 工具查询 DEMO-FIN-11 在相关时间窗口内的记录均为空 (0 行)。两种可能的原因：1) 告警依赖全量日志保留的近似值或重放逻辑，而事件湖中不存在原始精细日志；2) 检测基线对瞬时行为反应但未写入持久化活动表。由于直接观察缺失，无法证实‘隐藏窗口’工艺或建立具体网络连接发生，也无法将告警中的 IP 198.51.100.41 与工具端口统计关联。证据缺口导致粉红路径‘Office->PowerShell->外联’的因果关系被阻断。

## 查询来源与成员对应
以下由保存的来源生成；事件ID对应不证明因果，未匹配不等于无关。
- [E1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E1)：本次工具返回；成功、空结果或不可用状态见原证据。
- [E2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E2)：本次工具返回；成功、空结果或不可用状态见原证据。

## 发现与依据
- 告警 A1**原始陈述**：WINWORD.EXE(PID 4100) 在 DEMO-FIN-11 启动了 powershell.exe(PID 4200) 且窗口隐藏。告警 Rationale**推断**：这是文件无/LOL 攻击的强信号。（依据：[A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A1), [T1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/T1)）
- 告警 A2**原始陈述**：PID 4200 向 198.51.100.41:443 发送了 8192 字节出站流量。告警 Rationale**推断**：目标可能是 C2 或外泄，因是‘合成文档地址’需人工审查。（依据：[A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A2), [T2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/T2)）

## 成员覆盖与判断
选定2条，读取2条；给出判断0条，尚未明确2条，未逐项分析0条，材料不可读0条。
给出判断不等于证实攻击或已解决；背景成员不等于已证明安全。
- 4c71eec2-77da-5b81-b68a-72801d55ea24 [unresolved/supporting]：A1 的‘Office->Ps'触发器因缺乏直接进程表证据无法证实是否真实发生；告警可能是基于采样或离线分析推断。（依据：[A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A1), [T1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/T1), [E1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E1)）
- f7af404b-26a6-5d15-bd6c-3a872bdaf451 [unresolved/supporting]：A2 的'PID4200->Net'行为因网络流表缺失无法验证是否真实外连；通信请求是否被阻断或未记录。（依据：[A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A2), [T2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/T2), [E2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E2)）

## 跨告警关联依据
共同实体或时间接近不等于因果关系。
- 4c71eec2-77da-5b81-b68a-72801d55ea24, f7af404b-26a6-5d15-bd6c-3a872bdaf451 [shared_context/not_supported]：高置信度告警矛盾：告警内宣称存在父子进程链(PID4100->4200) 及延迟性外联，但工具查询该主机当前窗口内为空。（依据：[A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A1), [T1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/T1), [A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A2), [T2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/T2), [E1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E1), [E2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E2)）
- 4c71eec2-77da-5b81-b68a-72801d55ea24, f7af404b-26a6-5d15-bd6c-3a872bdaf451 [shared_context/not_supported]：告警内宣称的应用行为 (隐藏 PowerShell->外连) 在事件湖中不可见，可能源自近似/采样/离线推断。（依据：[A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A1), [T1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/T1), [A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A2), [T2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/T2), [E1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E1), [E2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E2)）

## 来源时间线
按来源时间排列；候选成员仅表示查询主机/来源范围的匹配，不证明因果。
- 2026-10-25T03:30:16.539577+00:00 [告警时间]：Office启动隐藏PowerShell [DEMO-FIN-11]（依据：[A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A1)；来源记录：见原告警；候选成员：4c71eec2-77da-5b81-b68a-72801d55ea24）
- 2026-10-25T03:32:16.539577+00:00 [告警时间]：脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11]（依据：[A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A2)；来源记录：见原告警；候选成员：f7af404b-26a6-5d15-bd6c-3a872bdaf451）

## 未决问题
- 进程表或活动日志是否在检测到‘隐藏窗口’后，因安全策略、工具上限或存储问题而未持久化记录？（成员：4c71eec2-77da-5b81-b68a-72801d55ea24；依据：[E1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E1), [A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A1)） 缺少：进程树记录 (Sysmon EventID 1 或 3) 的原文存储缺失导致无法反查隐藏/子进程信息。；建议：尝试直接查询 Sysmon/Windows 事件日志存档 (若存在) 而非事件湖过滤接口。
- 告警中提到的‘合成文档地址’198.51.100.41:443 是否因防火墙/IDS 拦截导致网络记录缺失？（成员：f7af404b-26a6-5d15-bd6c-3a872bdaf451；依据：[E2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E2), [A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A2)） 缺少：网络流表记录 (DNS/Flow Logs/SNI) 缺失，无法确认外部通信是否存在。；建议：查询防火墙/IDS 阻断日志或威胁情报 IP 特征库，判断‘合成地址’是否为误报或内部测试段。

## 反证
- 工具调用 E1(pass_process_activity) 结果显示 DEMO-FIN-11 在 2026-10-25 03:29:00 - 03:34:00 之间无进程活动记录。
- 工具调用 E2(pass_network_connections) 结果显示 DEMO-FIN-11 在同一时间窗口内无任何网络连接记录。

## 未解问题与限制
- 告警中声称的父子进程链(PID 4100->4200) 和隐藏参数在现代进程表中不可见；是否有日志回滚或存储限制导致丢失。
- 告警中声称的 TCP/443 外连行为缺失于网络流表；是否因目标为‘合成地址’而被防火墙/IDS 拦截或未记录到事件湖。
- 部分历史告警摘要仅提供前600字符，未核对完整摘要。
- 成员4c71eec2-77da-5b81-b68a-72801d55ea24：A1 的‘Office->Ps'触发器因缺乏直接进程表证据无法证实是否真实发生；告警可能是基于采样或离线分析推断。
- 成员f7af404b-26a6-5d15-bd6c-3a872bdaf451：A2 的'PID4200->Net'行为因网络流表缺失无法验证是否真实外连；通信请求是否被阻断或未记录。
- 未决问题：进程表或活动日志是否在检测到‘隐藏窗口’后，因安全策略、工具上限或存储问题而未持久化记录？
- 未决问题：告警中提到的‘合成文档地址’198.51.100.41:443 是否因防火墙/IDS 拦截导致网络记录缺失？

## 建议
- 检查日志收集代理是否对 window/spawning 事件有过滤规则或磁盘配额限制。
- 核实 IP 198.51.100.41 的定义：若是‘文档合成’地址则可能非恶意，若是‘保留空间误报’则需关联外泄检测。
- 增量补查：若存在历史全量日志 (如 Sysmon 事件 ID 1 或 3)，则需单独查询而非依赖当前事件湖接口。

## 本次范围
Case：be4aeda2-a89b-47e6-a6f9-285b1a7e8723
时间：2026-10-25T03:29:00+00:00 至 2026-10-25T03:34:00+00:00（不含结束时刻）
选定成员：4c71eec2-77da-5b81-b68a-72801d55ea24, f7af404b-26a6-5d15-bd6c-3a872bdaf451
停止原因：analysis_complete

## 证据索引
- [A1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A1)：告警4c71eec2-77da-5b81-b68a-72801d55ea24，来源事件=bdb56855-5018-567e-b10d-68e7e7bb7073
- [T1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/T1)：分诊记录1c92c9d5-e2e8-453e-ac8d-1bf074629692（分诊判断）
- [A2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/A2)：告警f7af404b-26a6-5d15-bd6c-3a872bdaf451，来源事件=2d58f3fd-0e29-5e9b-bf0e-8fabe878cd72
- [T2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/T2)：分诊记录066e345c-6212-41fa-8425-efd9c24fe757（分诊判断）
- [E1](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E1)：process_activity，来源可用=True，记录ID=无
- [E2](/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e/evidence/E2)：network_connections，来源可用=True，记录ID=无
