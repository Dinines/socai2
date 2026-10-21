# 3A-04：组织记忆认证读取与失败语义

2026-10-20；批次`3a-org-memory-20261020`。**每租户授权读取、当前材料/失败状态、真实模型消费及账本限定验收通过。** 已部署21，仅更新和定向重启API/Agents，常驻worker和自动响应保持关闭。

## 认证与读取合同

更新前真实HTTP复现：Agents发送共享X服务头返回401，API没有配置相同token；只有`settings:read`的key却能在旧GET读取组织记忆，返回200。旧直接函数测试模拟token成功，未证明实际HTTP认证可用。

现有`GET /api/v1/feedback/context-statements`使用标准Bearer身份、`alerts:read`、显式tenant交集及查询前RLS上下文。仅共享X头不授权；标准AuthUser支持的身份仍保留，其他路由未改。实际API验证A读A200、A请求B403、缺scope403、匿名/错误key/仅X头401，reader尝试写入告警403；未开放管理员或匿名回退。

Agents按tenant从受控JSON选择各自API key，无映射明确未配置。两个测试tenant各有独立禁口令登录服务账号和只含`alerts:read`的reader key，30天有效，保留供已配置读取路径使用；三枚短时操作key已停用。没有给全部既有tenant配置访问，也不外推全API授权覆盖。

读取结果区分success、no_match、disabled、unavailable及具体原因；包含来源、时间、缓存、实际采用语句及hash。`no_match`只代表本次视图没有有效tenant语句，该接口不按告警做语义检索。最多采用12条、每条300字符，经清理后的实际子集和完整建议性prompt块一起记录；组织习惯不能替代当前告警佐证或扩大工具权限。

## 输入 → 实际中间产品 → 结果

PG直接插入可识别合成编译语句，保留有效期与tenant；不是实际分析员反馈产物。原编译、双人佐证和TTL逻辑由原测试覆盖，本批不宣称真实反馈写入链已经通过。

| 输入/故障 | 实际调用或中间材料 | 结果 |
| --- | --- | --- |
| A有效语句及过期语句 | 实际API、生产reader | success，只采用有效A语句 |
| B初始只有过期语句 | 实际API200空列表 | no_match，明确不是“没有相关历史” |
| 缺映射、reader禁用 | 生产reader，探针进程配置 | unavailable/not_configured、disabled，不发无授权请求 |
| A配置B的key | 实际HTTP403 | unavailable/auth_failed，不采用材料 |
| 暂停A reader key，探针TTL设0强制刷新 | 已有缓存→实际HTTP401 | unavailable/auth_failed，不回用旧材料；恢复key后重新成功 |
| 独立探针地址设为本地闭合端口 | 实际连接失败 | unavailable/transport_error，不代表无历史 |
| 两秒有效语句进入默认缓存 | 真实PG→API→缓存；2.2秒后再读 | 缓存采用数2→1，expired_count1；API也排除该语句 |
| B新增有效语句 | 真实PG及两租户再次读取 | B只采用B材料，A不混入B材料 |

默认TTL为120秒；缓存命中不再向API校验key，服务端撤销/到期及语句编辑、删除在刷新后才体现。逐条检查的是已缓存的`expires_at`。本批撤销探针显式强制刷新，**没有证明默认配置可即时撤销**。映射移除或轮换会在缓存查询前读取文件，按tenant/URL/凭据hash隔离；请求失败或过期缓存不采用旧语句。

一条新告警实际经认证ingress→项目SSL Kafka→Fusion→PG/API；无group消费者捕获实际fused信封，不提交offset。生产worker通过原reader port读取A记忆，真实21网关→43模型调用的safe-call输入含完整采用块，不含过期、短时及B语句。模型明确引用02:00备份习惯，同时要求当前时间/作业/认证佐证，返回`needs_review`、自报confidence0.95；未自动关闭或执行动作。

真实模型Run为`2e2b115f-7938-5505-9ad6-457fa01aeaea`。捕获点为`safe_ainvoke`入口；只读重建当前同配置确认本地LiteLLM路径的egress pseudonymization关闭，但不是网络抓包证据。prompt/response未截断，全文受控，公开hash与工件关系。原始usage→CostTracker→Run/成本行均为1377输入、146输出、**1523 tokens，unpriced1，费用unknown**；网关triage8→9，其他角色不增。

失败状态另经实际401读取→生产prompt投影→probe-only账本验证，未作第二次模型调用。probe-only Run为`b369e8c8-d79d-5011-a386-4b6b52cb2af7`，不是模型结论。对其记忆工件INSERT位置注入真实PG `SELECT 1/0`，得到LedgerPersistError/DivisionByZeroError，Run/事件/工件全为0；原连接池恢复、同Run写入后为1/1/1，重复同输入不追加或更改回执工件。新回执随verdict在同一事务首次写入，RLS设置移到该事务内；原通用Run/告警重试更新逻辑保持，不宣称整个结果完全不可变。

## 持久回查与保留

真实模型Run有2事件/3工件（prompt、response、organisation_memory_read）；probe-only Run有1事件/1记忆读取工件。API核工件内容等于verdict payload，hash、事件关系和租户拒绝一致。API/Agents定向重启后原结果可查，常驻UID10001实际读取两个tenant成功，无新模型或输入。共46项显式HTTP验收检查，生产reader内部HTTP结果另存，不计中间轮询。

194项相关测试通过（Agents125/API69），含认证依赖链、过期/失败/预算、冻结replay和账本事务边界。API首次测试配置空DSN在收集阶段失败，改为无网络、语法有效的测试DSN后通过；未删除或跳过原断言，失败日志保留。

旧49告警、13Run、54事件、16工件、13成本行、4shadow配置、8shadow决策及2规则集摘要保持。新增1告警、2Run（含1个probe-only）、3事件、4工件、1成本行、2shadow配置、1shadow决策及5条合成语句；总告警50。其他34容器/18卷/134迁移保持，API/Agents99/142锁依赖及运行源码hash对应。只有Agents增加凭据路径与只读目录，既有env/mount保留，无DDL、依赖或评分算法变化。

## 使用限制与下一项

两枚reader key只绑定A/B测试tenant，到期为2026-11-19T07:52:59.737539Z；受控路径、权限和轮换见[配置索引](configuration.md)。目录挂载支持原子替换keys.json，文件保持0600、目录0700/UID10001，下一次读取采用新映射；不要把key写入公开文件。三操作key停用401，两reader key保留且实测200。

技能、KB、近期处置、身份四类reader仍401；真实反馈写入、真实事件/UEBA、技术引用及宽样本质量仍未过。一次模型示例不能证明质量校准；无常驻消费、rebalance或真实厂商动作验收。

当前十三层命令及撤层步骤见[部署说明](../../deploy/aisoc21/README.md)。回退先停相关消费者、保留队列/材料，不重发已受理模型或输入；撤org-memory层会恢复旧认证/读取行为，不能把它当同等能力。下一单项：[3A-05技能读取认证及失败语义](3a-tenant-skill-plan.md)。完整3A/2C及服务端基线仍未冻结。

来源见[差异清单](../handoff/3a-org-memory-source-manifest.json)，完整关系见[JSON回执](3a-org-memory.json)；受控原始材料在工作站`.local/aisoc21/evidence/3a-org-memory-20261020/`及21同名evidence目录。既有回执与原始证据不改写。
