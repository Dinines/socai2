# Case调查报告 183c059b-2413-4d24-a4aa-dcebe3ad1e55

针对警案例 INVHTTP-20261028-01 archive-upload 的告警 A1、A2，告警内容描述在主机 DEMO-DATA-13 上涉及用户 demo.export 执行批量文件读取并生成归档操作。告警 A1 被标记为 true_positive，断言为未经授权的活动；告警 A2 被标记为 false_positive，断言为模拟演示行为。当前运行中，使用 process_activity 和 network_connections 针对主机 DEMO-DATA-13 进行了查询，但均返回空结果，无实际可用作进一步分析的证据记录。目前无进程执行的确切时间线、文件路径、账号哈希、连接记录等数据，无法确认活动性质。

## 发现与依据
- 告警 A1 主张 host 上 demo-export 用户执行批量读取与归档操作，判定为未授权活动 (true_positive)。（依据：[A1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A1), [T1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T1)）
- 告警 A2 主张 host 上 archive-demo 进程向 demo IP 传输数据，判定为虚假警报 (false_positive)。（依据：[A2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A2), [T2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T2)）

## 成员覆盖与判断
选定2条，读取2条；给出判断0条，尚未明确2条，未逐项分析0条，材料不可读0条。
给出判断不等于证实攻击或已解决；背景成员不等于已证明安全。
- 6373220a-2f25-541e-ab89-9c3a2e611140 [unresolved/supporting]：告警 A1 标记为 true_positive，暗示 unauthorized 活动，但无工具证据支持，结论之真实性无法确认。（依据：[A1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A1), [T1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T1), [E1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E1)）
- 4eb06dee-c5a0-5f08-ace7-08caa2952db5 [unresolved/supporting]：告警 A2 标记为 false_positive，主述为演示活动，但工具查询同样空值，无法验证该行为确实仅属于模拟。（依据：[A2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A2), [T2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T2), [E2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E2)）

## 跨告警关联依据
共同实体或时间接近不等于因果关系。
- 6373220a-2f25-541e-ab89-9c3a2e611140, 4eb06dee-c5a0-5f08-ace7-08caa2952db5 [shared_context/hypothesis]：两者均涉及同一主机 DEMO-DATA-13，同一用户/进程，同一外部 IP 198.51.100.43，时间接近。（依据：[A1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A1), [A2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A2), [T1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T1), [T2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T2)）
- 6373220a-2f25-541e-ab89-9c3a2e611140, 4eb06dee-c5a0-5f08-ace7-08caa2952db5 [behavioral_link/not_supported]：告警描述行为模式不同（批量归档 vs 演示数据上传），但无工具记录可证实或证伪实际行为是否发生变化。（依据：[A1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A1), [A2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A2), [E1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E1), [E2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E2)）

## 来源时间线
按来源时间排列；候选成员仅表示查询主机/来源范围的匹配，不证明因果。
- 2026-10-25T03:32:20.781813+00:00 [告警时间]：服务账号批量读取并生成归档 [DEMO-DATA-13]（依据：[A1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A1)；来源记录：见原告警；候选成员：6373220a-2f25-541e-ab89-9c3a2e611140）
- 2026-10-25T03:34:20.781813+00:00 [告警时间]：归档进程向文档地址上传字节 [DEMO-DATA-13]（依据：[A2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A2)；来源记录：见原告警；候选成员：4eb06dee-c5a0-5f08-ace7-08caa2952db5）

## 未决问题
- 是否有模拟/演示脚本的授权背景下运行，且与告警 A2 一致？（成员：4eb06dee-c5a0-5f08-ace7-08caa2952db5；依据：[A2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A2), [T2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T2)） 缺少：模拟授权证明、脚本部署记录、用户确认；建议：核查模拟/演示平台日志及审批记录，确认相关操作是否确为授权演示
- 告警 A1 中的疑似未授权归档操作是否真实存在？（成员：6373220a-2f25-541e-ab89-9c3a2e611140；依据：[A1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A1), [T1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T1)） 缺少：文件操作审计记录、审批拒绝记录、用户日志；建议：确认是否存在授权审批流程异常或被忽略的存档服务
- 为何 process_activity 与 network_connections 均未返回数据？（成员：本次全案；依据：[E1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E1), [E2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E2)） 缺少：日志收集范围、探针部署状态、采集时间窗口对齐情况；建议：核查数据采集代理是否正常工作，确认事件湖完全覆盖该主机在告警时间窗口内的数据

## 反证

## 未解问题与限制
- 两个告警描述的主机操作（demo.export 或 archive-demo）均无对应进程执行记录证实
- 缺少文件路径、账号哈希、文件完整性等关键信息
- 告警提及的 IP 198.51.100.43 和 10.78.30.13 无网络连接记录支持
- process_activity 与 network_connections 均返回空值，无法形成完整证据链
- 无父进程链数据，无法确认进程来源
- 无法验证是否有授权审批记录缺失（A1 主述）或 dismissed 模拟行为属性（A2 主述）
- 成员6373220a-2f25-541e-ab89-9c3a2e611140：告警 A1 标记为 true_positive，暗示 unauthorized 活动，但无工具证据支持，结论之真实性无法确认。
- 成员4eb06dee-c5a0-5f08-ace7-08caa2952db5：告警 A2 标记为 false_positive，主述为演示活动，但工具查询同样空值，无法验证该行为确实仅属于模拟。
- 关联待核实：两者均涉及同一主机 DEMO-DATA-13，同一用户/进程，同一外部 IP 198.51.100.43，时间接近。
- 未决问题：是否有模拟/演示脚本的授权背景下运行，且与告警 A2 一致？
- 未决问题：告警 A1 中的疑似未授权归档操作是否真实存在？
- 未决问题：为何 process_activity 与 network_connections 均未返回数据？

## 建议
- 确认是否存在模拟/演示脚本的使用记录及对应授权审批流程
- 核对 host 上是否部署了相关监测代理或进程忽略规则
- 尝试从权限合规审计记录、审批日志、时间线回溯中获取 manual 痕迹
- 确认告警时间窗口是否有覆盖不足或日志采集失败的可能
- 若告警过程中无数据源访问权限或系统缺失记录，应标记为信息高度不确定性事件

## 本次范围
Case：183c059b-2413-4d24-a4aa-dcebe3ad1e55
时间：2026-10-25T03:28:00+00:00 至 2026-10-25T03:37:00+00:00（不含结束时刻）
选定成员：6373220a-2f25-541e-ab89-9c3a2e611140, 4eb06dee-c5a0-5f08-ace7-08caa2952db5
停止原因：analysis_complete

## 证据索引
- [A1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A1)：告警6373220a-2f25-541e-ab89-9c3a2e611140，来源事件=aa28cadb-7857-5886-8ad8-9dceb311f0f5
- [T1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T1)：分诊记录41ac2058-c23a-4bef-8f06-1832d52d5516（分诊判断）
- [A2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/A2)：告警4eb06dee-c5a0-5f08-ace7-08caa2952db5，来源事件=990457e1-b97e-5a6b-9b01-e2eb6747ade4
- [T2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/T2)：分诊记录e457d951-3aea-4594-b2ba-2b520a5a765a（分诊判断）
- [E1](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E1)：process_activity，来源可用=True，记录ID=无
- [E2](/api/v2/investigation/cases/183c059b-2413-4d24-a4aa-dcebe3ad1e55/investigations/ebe2c07b-cc2d-5062-be00-cd73fccfc9fa/evidence/E2)：network_connections，来源可用=True，记录ID=无