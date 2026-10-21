# 3A-06：KB认证读取、确切采用文本与引用来源

2026-10-20；批次`3a-kb-read-20261020`。**每租户KB全文读取、失败/缓存/cutoff语义、实际模型采用及事务工件限定验收通过。** 21当前使用十五层配置，仅API/Agents更新和定向重启，常驻worker、自动graph、审批和真实响应关闭。一次模型没有使用KB引用标记，引用正确性和完整检索/调查质量仍未通过。

## 读取及时间合同

更新前真实Bearer和原共享X头均401，旧reader得到空结果。现`GET /api/v1/kb/runbooks/for-triage`使用标准Bearer、既有`knowledge_base:read`、tenant交集与显式RLS；省略tenant归自身，仅X头不授权。A/B实际有同词资料，读取各自200、越权/缺scope403、匿名/错误key/X头401；KB reader的告警写入、KB写入和删除均403，其他公开KB路由权限保持。

Agents独立`AISOC_TRIAGE_KB_KEYS_FILE`按tenant选key，不复用组织记忆/技能权限或共享token。两个测试tenant各有独立禁口令登录用户和仅`knowledge_base:read`的30天reader；三操作key停用401，两reader保留200，到期2026-11-19T09:05:50.327428Z。原组织记忆两枚alerts:read和技能两枚settings:read的key、文件hash、env、挂载全部保持。

查询仍为PG english全文检索、plainto_tsquery/ts_rank排序、同分按ID，限runbook/playbook/sop，默认3条；没有接embedding或调用带LLM synthesis的KB query。状态分success/no_match/disabled/unavailable/not_requested，记录tenant、query、scope、HTTP、缓存、时间与采用/拒绝数。无法确认tenant、cutoff echo、行结构或有限数值，不伪装空集。

cutoff现在同时要求created_at和updated_at不晚于split：创建后到和较早创建但后来修改分别计数，另给不重复的总数。原表两列NOT NULL，未为测试禁约束或改DDL；缺时间戳仅由测试替身/投影覆盖。无版本历史，保守排除修改后的行，不宣称还原旧正文或完整历史语料。live继续原无cutoff语义，合成未来行可被live查询返回。

## 输入 → 实际中间产品 → 结果

21原KB表精确0行。本批直接新增6条可识别合成词法检索材料，不是实际tenant SOP、导入/编写流程或向量质量成绩；旧资料未改。

| 输入/故障 | 实际调用或中间材料 | 结果 |
| --- | --- | --- |
| A/B同查询词，A另有policy/wiki | 真实API、PG生产FTS和reader | A live3个runbook，B只有自身1条；policy/wiki不采用 |
| split前资料、split后创建、旧创建后修改 | API/生产SQL/frozen reader | frozen只1条，creation排除1/update排除1/总排除2；更早cutoff全排除3 |
| 空query、合法无命中、关闭、无映射、A配B key | 生产reader/实际HTTP | not_requested、no_match、disabled、not_configured、403 auth_failed分开 |
| A key在服务端停用，先默认缓存、再探针TTL0 | 实际缓存命中→真实401→恢复 | 默认缓存仍成功，强制刷新不可用且不回旧材料，恢复network成功 |
| 探针URL闭合端口 | 实际连接失败 | transport_error，不当作租户没有文档 |
| 同连接SAVEPOINT SELECT1/0后恢复 | AST提取的实际生产SQL/formatter及hash，真实PG参数绑定 | 除零回滚后同查询结果一致；不是线上HTTP/共享PG outage或API503传播成绩 |
| 工件INSERT SELECT1/0 | 独立probe-only Run，真实PG事务 | Run/事件/工件0/0/0；恢复同Run1/1/1，重试不追加 |

默认缓存120秒，身份/URL/query/limit/cutoff隔离，先核映射再查缓存；刷新失败不采用旧材料。服务端撤销、到期、编辑或删除不保证即时生效，默认缓存成功后的401探针明确用了TTL0。映射移除或轮换在下一次读取前生效，不能把缓存与ACL隔离混为一谈。

KB实际采用片段、引用表与最终渲染预算统一：正文每条900、整体3000、实际编码data块3400字符，保留预算弃用、截断、原/采用hash、时间和chunk ID。控制字符/角色清理、注入扫描、nonce移除、不可信标签和nonce fence保留；Unicode按UTF-8 JSON字面计算，避免原通用第二次6000截断却仍保留旧引用表。引用只来自真正进入prompt的行；可解析标记不代表模型主张有证据支持。

## 模型前预算阻塞与一次真实调用

生产build_state会把Fusion narrative拼进摘要，实际400字符query比样例标题更长。先捕获真实信封，再用原query核A/B命中；仅新A/B合成正文追加明确测试词，记录旧/新正文和updated_at，cutoff验收在修改前完成。原query、告警和信封保持，不能将新正文称为split前历史内容。

初次完整literal为8717字符，预检在模型/模型Run之前停止。新A/B标题和正文压成synthetic短SOP及真实PG词项，最多38步通过生产FTS确认删除冗余词仍匹配；仍为8105，再次停止。随后仅将KB inline重复边界说明作等义精简，保留不可信DATA、可能过时/不适用/第三方或攻击者内容、不服从system/policy/playbook/manager权限声明、不得改verdict/close/contain/skip/reveal、报告注入并忽略等约束。共享envelope、standing system_rule、注册system prompt/lock和8000上限不改。

原相关测试要求保留`“suspected prompt-injection attempt”`措辞，首轮精简重测197通过/1失败；恢复该措辞且不删断言，198项通过后，仅再次更新Agents。最终预算**7861≤8000**，从同一告警/信封/probe继续，没有重投告警、重复故障探针或模型重试。两次超限、失败测试及部署保护日志保留，完整关系见[JSON回执](3a-kb-read.json)。

唯一新告警经认证HTTP→SSL Kafka→Fusion→PG/API；独立无group消费者读取实际fused信封，不提交offset。实际worker→21网关→43模型的输入含完整A KB块、A组织记忆及skill-a-rule@v3，无B/policy/wiki材料；prompt/response未截断。Run为`553b01c5-033a-5f9d-a557-4b9a82405bd6`，返回`needs_review`、自报confidence0.95，未触发审批、响应或告警人工状态变更。

真实usage→CostTracker→Run/成本行均为1955输入、140输出、**2095 tokens，unpriced1，费用unknown**。网关triage10→11，其他角色保持。提供marker为KB1；实际model_citations和unresolvable_citations均为空，说明材料已提供和来源可回查，**不能据此称引用质量通过**。未为取得引用再调模型。捕获点是safe-call入口；同配置只读重建的egress关闭证明不是网络抓包。

## 持久化、恢复与下一项

KB读取/确切采用/实际引用随verdict在原首次写入事务保存，独立knowledge_base_read工件与payload完全相同，bytes/hash/事件关联一致。模型Run有2事件/5工件（prompt、response、组织记忆、技能、KB）；probe有1事件/1 KB工件。失败读取只经实际401→生产prompt投影→probe账本，不是第二次真实模型。首次工件原子性不外推原通用Run/alert完全冻结。

API/Agents重启后同一材料可查，常驻UID10001实际读取A/B各自KB一条成功，组织记忆和技能v3/B v1也保持。236项相关测试通过（API38、Agents198，重复执行不重复计数），最终60项HTTP检查复用先前成功阶段且不重复加resume。来源见[清单](../handoff/3a-kb-read-source-manifest.json)，层叠源码、原始证据、链接、凭据与依赖核对见[本地校验](3a-kb-read-local-verification.json)。

旧51告警、17Run、60事件、25工件、15成本、6shadow配置、10shadow决策、2规则、5组织语句、10技能/12版本及4 failed FK材料保持。新增1告警、2Run（含probe）、3事件、6工件、1成本、1shadow决策及6 KB行，总告警52。其他34容器、18卷和134迁移保持，API99/Agents142锁依赖及运行源码对应，无新运行依赖或DDL。

受控目录`private/kb-read-3a/`→`/run/secrets/triage-kb`，UID/GID10001、0700，keys.json0600，只读挂载；原件/本地受控副本和轮换见[配置索引](configuration.md)。当前十五层及撤层方法见[部署说明](../../deploy/aisoc21/README.md)，回退保留旧reader层、队列和材料，不重发已受理输入/模型。原始证据在工作站`.local/aisoc21/evidence/3a-kb-read-20261020/`和21同名目录，旧冻结回执不改写。

近期处置和身份两类reader仍401，真实事件/UEBA、旧增强工具身份、宽样本知识/引用/模型质量尚未验。下一单项：[3A-07近期分析员处置读取与采用来源](3a-dispositions-plan.md)。完整3A/2C及服务端基线未冻结。
