# Case调查报告 a280c884-0abd-458d-bb66-13c06fe9ca5b

告警 A1 与 A2 基于同一主机（3fcd...）、相同源 IP 和目标 IP 段，时间间隔 2 分钟，且详情 E2 确认事件 ID 匹配，存在强共享上下文。然而，进程活动证据 E1 查询结果为空，导致无法确认发起连接的进程身份及业务意图。无法区分是采集盲区、权限不足还是真实存在无对应进程的网络活动（如内核模块直连等）。当前证据不足以断定攻击成功或正常业务，案例保持待核状态。

## 发现与依据
- 告警 A1 (3fcd...) 与 A2 (5272...) 在主机 investigation-ch-20261023-01-host 上几乎同时报告了网络活动，证据 E2 确认了连接目标为 198.51.100.70/71，来源为 192.0.2.70，与告警 metadata 完全一致，证实网络行为发生但线索截断于进程归属。（依据：[A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A1), [A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A2), [H1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1)）
- 关键缺口在于进程活动证据 E1 返回空记录，无法建立从网络连接（IPv4/IPv6）到具体执行进程（PID、名称、命令行）的因果链，亦无法判断是否存在父进程链或未捕获的内核层活动。（依据：[A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A1), [A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A2), [H1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1)）

## 成员覆盖与判断
选定2条，读取2条；给出判断0条，尚未明确2条，未逐项分析0条，材料不可读0条。
给出判断不等于证实攻击或已解决；背景成员不等于已证明安全。
- 3fcd245d-0496-54f3-875e-f9a7eb90ae2d [unresolved/supporting]：A1 的源地网络连接 confirmed by E2，但 E1 缺失导致无法确认进程来源，无法判定为最终安全或告警误报。（依据：[A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A1), [H1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1)）
- 5272ae80-b48e-5ef3-8cdd-805885a558a0 [unresolved/supporting]：A2 与 A1 共享相同的网络连接特征（E2 confirmed），但同样受限于 E1 的空结果，网络行为无法溯源到具体应用程序。（依据：[A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A2), [H1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1)）

## 跨告警关联依据
共同实体或时间接近不等于因果关系。
- 3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0 [shared_context/supported]：双方均指向同一主机，E2 证实了两个独立告警所述的网络连接事件的具体细节（目标 IP、源 IP、Event ID）完全匹配。（依据：[A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A1), [A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A2), [H1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1)）

## 来源时间线
按来源时间排列；候选成员仅表示查询主机/来源范围的匹配，不证明因果。
- 2026-10-23T09:59:00+00:00 [告警时间]：合成测试待核网络活动 c9ee6c8a-d44d-5ffe-a456-594b5555a87c（依据：[A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A1)；来源记录：见原告警；候选成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d）
- 2026-10-23T10:01:00+00:00 [告警时间]：合成测试待核网络活动 951c5352-2df4-53d8-a431-b2763fea5e6e（依据：[A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A2)；来源记录：见原告警；候选成员：5272ae80-b48e-5ef3-8cdd-805885a558a0）

## 未决问题
- 进程活动 E1 为何未返回任何记录？（成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0；依据：[H1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1)） 缺少：更细粒度的进程创建/网络文件句柄关联数据，或操作系统内核网络子系统的原始日志以绕过用户态进程记录的缺失。；建议：检查 E1 查询的时间窗口是否覆盖了实际连接时间；确认采集代理/探针的权限是否足够捕获系统级进程；必要时进行内存取证以恢复瞬态进程信息。
- 目标 IP 198.51.100.70/71 的身份与通信目的为何？（成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0；依据：[H1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1)） 缺少：内部分配表、第三方 IP 信誉数据库、以及该通信对应的具体 HTTP 请求/响应头或二进制特征。；建议：查询内部资产清单；对目标 IP 进行对外信誉扫描；尝试还原 E2 中的 TCP 会话数据以分析应用层协议行为。

## 反证

## 未解问题与限制
- 进程活动 E1 为空：需确认时间窗口、采集探针状态或是否存在无法见（invisible）进程，无法解释为何无进程创建对应的网络连接。
- 目标 IP 身份不明：198.51.100.x 段的具体归属、信誉及业务授权状态未知，无法直接判定危险等级或排除正常代理/备份流量。
- 业务上下文缺失：缺乏该主机的网络策略、服务清单及告警触发源的原始 payload，无法解释通信目的。
- 成员3fcd245d-0496-54f3-875e-f9a7eb90ae2d：A1 的源地网络连接 confirmed by E2，但 E1 缺失导致无法确认进程来源，无法判定为最终安全或告警误报。
- 成员5272ae80-b48e-5ef3-8cdd-805885a558a0：A2 与 A1 共享相同的网络连接特征（E2 confirmed），但同样受限于 E1 的空结果，网络行为无法溯源到具体应用程序。
- 未决问题：进程活动 E1 为何未返回任何记录？
- 未决问题：目标 IP 198.51.100.70/71 的身份与通信目的为何？

## 建议
- 对目标 IP 198.51.100.x 进行资产/信誉核查，确认是否为白名单内资产。
- 检查主机网络栈及内核日志（netfilter/nftables/syslog），确认是否存在无进程可见的网络流量（如 raw sockets、Docker 容器网桥镜像流量等）。
- 扩大进程采集时间窗或更换采样方式（如内存取证），以捕获可能因短暂存在或权限不足而丢失的进程证据。

## 本次范围
Case：a280c884-0abd-458d-bb66-13c06fe9ca5b
时间：2026-10-23T09:58:00+00:00 至 2026-10-23T10:03:00+00:00（不含结束时刻）
选定成员：3fcd245d-0496-54f3-875e-f9a7eb90ae2d, 5272ae80-b48e-5ef3-8cdd-805885a558a0
停止原因：analysis_complete

## 证据索引
- [A1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A1)：告警3fcd245d-0496-54f3-875e-f9a7eb90ae2d，来源事件=c9ee6c8a-d44d-5ffe-a456-594b5555a87c
- [A2](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/A2)：告警5272ae80-b48e-5ef3-8cdd-805885a558a0，来源事件=951c5352-2df4-53d8-a431-b2763fea5e6e
- [H1](/api/v2/investigation/cases/a280c884-0abd-458d-bb66-13c06fe9ca5b/investigations/7b43c909-a450-55da-9a20-c6123dab7658/evidence/H1)：前次调查d957313e-b528-585c-9254-cd7bb8675da7（历史判断，范围见原报告）