# 3A-05：技能认证读取、选择与实际采用来源

2026-10-20；批次`3a-tenant-skill-20261020`。**每租户授权读取、明确失败状态、实际技能选择/模型输入及事务工件限定验收通过。** 21仅更新和重启API/Agents，常驻worker、自动graph、审批和真实响应继续关闭。

## 认证与读取

更新前真实Bearer和共享X服务头均返回401，旧reader得到空列表。现在`GET /api/v1/tenant-skills/resolved/active`使用标准Bearer身份、既有`settings:read`、tenant交集及显式RLS；省略tenant归自身。真实API验证读自身200、跨tenant/缺scope403、匿名/错误key/仅X头401，reader写入告警及技能均403。其他编写、回测、激活和退休接口未改。

Agents使用独立`AISOC_TENANT_SKILLS_KEYS_FILE`，每tenant选择自己的只读key，无组织记忆或共享token回退。A/B各有独立禁口令登录用户及仅`settings:read`的30天reader；到期为2026-11-19T08:36:24.337460Z，保留供已配置读取使用。三枚操作key已停用401。原组织记忆两key、`alerts:read`权限、私有文件hash、env和挂载保持。

结果区分success、no_match、disabled、unavailable、not_requested，保存reason、HTTP、缓存、期限和候选数。读取成功但没有选择命中与读取失败分别记录；无映射明确not_configured。返回tenant/版本/结构校验失败不假装空集，刷新失败不采用旧技能。

默认TTL120秒；每次检查已缓存的expires_at，但缓存命中不重验服务端撤销/到期及技能编辑、退休或删除。实际撤销探针显式TTL0强制刷新401，**不证明默认可即时撤销**。读取映射在查缓存前进行，tenant/URL/凭据hash隔离；移除或轮换映射不复用旧身份缓存。

## 输入 → 实际调用 → 结果

样例直接写入真实PG，是合成预激活读取材料，不是实际编写/回测/激活成绩。初始8个技能头、9条历史版本，随后短期/B样例和v3轮换后共10头/12历史。保留原FK/CHECK，4条replay占位明确failed/probe_only/not_actual_backtest，分数和报告均NULL、没有执行replay，不能当作回测通过。

| 输入/故障 | 实际中间产品 | 结果 |
| --- | --- | --- |
| A有效、过期及退休技能；B初始仅过期 | 实际API及生产reader | A有效5条，B为no_match；过期/退休不采用 |
| rule、source、原始MITRE子技术、平局、无匹配 | 生产build_state及worker attach，未发broker/模型 | 分别选rule v2/20、source v1/5、parent technique v1/10、ID较小技能/2、无选择 |
| 缺映射、禁用、A配B key、暂停A key后强制刷新 | 生产reader及实际HTTP | not_configured、disabled、403/401 auth_failed；无旧材料，恢复成功 |
| 探针URL指向闭合端口 | 实际连接失败 | transport_error，不代表租户没有技能 |
| 两秒有效技能进入默认缓存 | PG→API→缓存，2.2秒后读取和选择 | 有效数6→5、expired_count1；过期技能不再选择，API也排除 |
| B新增有效技能 | 两tenant实际读取及worker选择 | B只选B，A不混入B材料 |
| 真实PG在skill工件INSERT位置SELECT1/0 | 独立probe-only Run，恢复原池并重试同Run | 故障0Run/0事件/0工件；恢复1/1/1，重复不追加 |

选择沿用原加法权重：rule20、technique10、source5、每keyword2，父技术可匹配子技术，同分按ID，最多扫描前50候选。这不是严格优先级，多关键词可超过rule分数。生产worker补保留source，技能匹配补原始MITRE fallback，不重写整体技术映射或评分算法。

指导语按原有效2000字符预算只清理/限长一次，保存确切prompt块及SHA256，实际prompt直接采用该块。注册system prompt及lock未变。冻结replay仍经reader port/split快照，不实时调用API或按今天的日期筛历史，保留skills_under_test例外。

## 一次真实模型与持久回查

一条新告警经认证ingress→SSL Kafka→Fusion→PG/API，无group消费者捕获实际fused信封且不提交offset；生产worker实际选择`skill-a-rule@v2`，得分20。safe-call输入含完整技能块及既有A组织记忆，排除过期、退休、短时及B技能。

Run为`a1d5e5be-1766-5fed-80fe-6081e674f086`，模型返回`needs_review`、自报confidence0.95：组织备份惯例不足以证明本次活动授权，仍要求当前认证、进程树、作业归属与时间。没有自动关闭、审批或响应。真实路由21网关→43；usage、CostTracker、Run及成本行均为1572输入、105输出、**1677 tokens，unpriced1，费用unknown**；triage计数9→10，其他角色不增。一次示例不证明分类或技能内容质量。

捕获位置是safe_ainvoke入口；持久prompt是JSON消息数组，解码后每条content与捕获消息一致，prompt/response未截断。只读重建同配置确认本地LiteLLM路径的egress pseudonymization关闭；这不是网络抓包。

真实模型Run有2事件/4工件：prompt、response、organisation_memory_read、tenant_skill_read；技能工件内容等于verdict payload，bytes/hash/事件关联一致。失败读取另经真实401→生产prompt投影→probe-only账本，不是第二次模型调用或模型判定。新读取回执和工件在原verdict事务首次写入；原通用Run/alert重试更新保持，不宣称整个Run完全冻结。

模型完成后只更新本批新技能头到v3、追加v3历史；刷新读取采用v3，没有新模型/持久分诊。原v1/v2历史hash及原Run的v2回执、字面文本和工件保持。API/Agents重启后同一Run材料一致，常驻UID10001实际读A为v3、B为v1，两个tenant组织记忆也成功。此证据不外推deep investigation版本pin：原代码在指定旧版本不可得时仍可能落当前版本，graph关闭，列为3B开放前门槛。

## 验证、保留与下一项

347项相关测试通过（API142、Agents205）；复用原生命周期、权限、worker、ledger和replay测试，另补3个本批测试文件。最终验收检查48项显式HTTP；首轮只读verify的11次GET单列保留，reader内部请求与中间轮询不重复计数。

失败记录完整保留：原SQLite测试镜像缺aiosqlite；新NaN测试响应构造在到达解析器前失败；归档摘要/路径操作错误；verify直接匹配序列化JSON文本误判；finish在成功重启和key收尾后受stdout日志前缀干扰。测试镜像补固定上游dev wheel aiosqlite0.22.1/hash，生产镜像确认不存在该包。修正探针解析后，按检查点只读恢复，没有重复告警、模型、服务重启或key写入；没有跳过原验收断言。具体日志和关系见[JSON回执](3a-tenant-skill.json)。

旧50告警、15Run、57事件、20工件、14成本行、6shadow配置、9shadow决策、2规则和5组织语句摘要保持。新增1告警、2Run（含probe-only）、3事件、5工件、1成本、1shadow决策；总告警51。其他34容器、18卷和134迁移保持；API99/Agents142锁依赖、全部运行源码hash对应，无生产依赖、DDL或评分算法变化。

凭据目录为21 `private/tenant-skill-3a/`→容器`/run/secrets/tenant-skill`，UID/GID10001、0700，keys.json0600，只读挂载。受控原件和本地副本见[配置索引](configuration.md)，不进Git或镜像。当前十四层命令及撤层恢复见[部署说明](../../deploy/aisoc21/README.md)；恢复先停相关消费者、保留队列/材料，不重发已受理输入/模型，保留org-memory层及原身份。

KB、近期处置和身份三类reader仍401，真实事件/UEBA、旧增强工具授权、引用/完整调查质量仍未过。下一单项：[3A-06 KB认证、引用与实际采用文本](3a-kb-read-plan.md)。完整3A/2C及服务端基线仍未冻结。

来源见[差异清单](../handoff/3a-tenant-skill-source-manifest.json)；受控raw在工作站`.local/aisoc21/evidence/3a-tenant-skill-20261020/`及21同名目录。[本地校验](3a-tenant-skill-local-verification.json)另核层叠源码、旧冻结证据、依赖、链接与凭据泄漏；旧回执及原始材料不改写。
