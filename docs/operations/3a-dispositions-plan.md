# 3A-07：近期分析员处置读取与采用来源

状态：限定验收完成，原计划及实施前缺口保留如下。实际结果见[3A-07回执](3a-dispositions.md)及[结构证据](3a-dispositions.json)；身份读取另列[3A-08计划](3a-identity-read-plan.md)，常驻worker、自动graph、审批与真实响应保持关闭。

## 实施前计划与缺口（历史）

当时路径是[API feedback](../../services/api/app/api/v1/endpoints/feedback.py)的`GET /feedback/recent-dispositions`→[Agents dispositions](../../services/agents/app/context/dispositions.py)→reader port/worker→prompt。API仅校验共享X头，tenant不是身份交集；reader先查tenant/query缓存再核共享token，禁用、缺配置、HTTP/格式错误与有效空集可表现为相同空结果。响应不带原反馈行ID，采用文本又在渲染时才清理截取，实际来源及模型看见的子集不易对应。这些是实施前静态缺口，后续实际复现与修复见回执。

原SQL按同rule优先，再按created_at倒序，实体匹配取host/principal等值；只接受既有rule/entities输入，不借此扩成任意SQL或改风险评分。`as_of`只按created_at切断；冻结reader当前对未honour的响应只累计统计，能否拒绝晚到材料须直接验证。上游“append-only”注释不等于数据库禁止修改或能恢复历史正文。

实施前保存源码前值、固定上游hash及旧材料摘要，形成精确文件范围。最小目标：

1. 内部GET使用标准Bearer、tenant交集、明确既有最小读取permission及RLS。现有组织记忆GET使用alerts:read，可作核权限依据，但须检查处置内容和既有权限目录后再定；不扩大组织记忆、技能或KB reader key。用独立受控tenant映射与专用reader key，无共享或匿名回退。
2. 保留`RecentDispositions`及reader port的CUTOFF合同，区分success/no_match/disabled/unavailable/not_requested与原因；记录rule/entities、tenant、来源、请求/echo时间、缓存、HTTP、返回/采用/拒绝数量。tenant/echo/结构错误不当空结果，缓存绑定地址/身份/查询，刷新失败不用旧材料，映射在缓存前校验。默认120秒并不保证服务端即时撤销或数据修改即时生效。
3. 反馈行ID及实际created_at、rule/entity匹配依据与采用文本/hash一起记录；只清理、限长一次并保存确切prompt块。保持top5、note240字符及现有“个人意见、不能替代当前佐证”的措辞。不要把历史benign当本次授权，也不要从意见扩大工具权限。
4. frozen使用split，校验服务端echo和行时间；不honour不采用。核真实表有无更新时间或历史版本；缺历史不能宣称可还原后来修改的笔记。通过同rule/实体、前后split、缺时间戳和错echo边界，明确真实PG与测试替身证据。
5. 读取/实际采用来源随verdict首次事务写入独立工件，模型是否提到其意见按实际回复记录。工件错误回滚、同Run恢复/重试不追加；旧反馈、组织记忆、技能、KB及历史Run不改写，不外推整个Run完全不可变。

验收使用A/B标记样例，覆盖同rule、另一rule同实体、无匹配、缺scope/越权/匿名、配置/缓存/失败/恢复、cutoff及笔记预算。先核`aisoc_analyst_feedback`真实约束/FK；合成直接入表仅证明读取，不冒充真实分析员反馈写入、双人编译或结案闭环。不得关约束、清全表或用旧数据的人工标签做盲测答案。

一次有界新告警经真实ingress/Kafka/Fusion/worker→现有21网关/43，核实际prompt及记录；模型可以采纳、反驳或未引用，均如实记录，不为取得预定分类追加调用。失败状态另用真实拒绝读取→生产prompt投影→probe-only账本，区分模拟故障、实际基础设施、真实模型和厂商动作。核usage/Run/成本行、费用unknown、原告警人工状态及API/Agents定向重启回查；原三类已接reader须保持。

优先复用[Agents处置/身份测试](../../services/agents/tests/test_triage_dispositions_and_identity.py)、[模型处置测试](../../services/agents/tests/test_auto_triage_dispositions.py)、[API反馈测试](../../services/api/tests/test_analyst_feedback.py)和既有replay/ledger测试，只补本批直接边界。预计只更新API/Agents，无DDL、运行依赖或检测算法变化；若实际阻塞扩大范围，先修订本计划。全部实际数据、最小scope、时间语义、模型消费和重启保持目前均待实测，整体3A/服务端基线未冻结。

## 本批具体范围与验收补充

源码限API feedback内部GET/响应/既有SQL，Agents dispositions reader、frozen reader、state、worker、prompt、ledger及必要直接测试；端口返回类型已有RecentDispositions，非必要不改port。GET复用既有alerts:read、tenant交集/RLS，新专用AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE，不复用前六枚reader key。无DDL/依赖/新评分算法。原始feedback表created_at NOT NULL但无updated_at/版本或禁止UPDATE约束，createdcutoff只证明返回行记录的创建时间，不证明后来编辑的历史不变或能重建旧笔记；不为缺时间样例禁约束。

保留原auto整体3000字符上限、top5和note240；将完整advisory、最终采用行及文本/hash统一预算，避免末尾二次清理截断丢失对应关系。真实model前literal上限仍8000。新模型告警用R-DISP-A/DISP-HOST-A，与旧技能/KB样例自然不匹配，实际读取须明确success无选择/no_match；原三类reader再用其原查询独立回查保持，不修改旧数据来凑全prompt。六个旧reader身份保留，只新增A/B两枚独立alerts:read reader，三操作key收尾撤销。

## 实施结果与发现

最终396项测试（API91、Agents305）及60项显式HTTP检查通过；五条合成反馈证明读取，未验实际反馈写入/编译/结案。一条真实Fusion→worker→43调用采用三条意见，7355字符完整prompt，needs_review/自报0.65，1909 tokens/费用unknown。创建时间cutoff不重建后来修改的笔记。模型概括提到近期意见，未精确引用笔记或ID，不外推因果采用或质量。

初394项通过后，定向重启及原Run回查成功，但独立新进程先加载reader暴露本批新增的循环导入。去掉跨agents包初始化依赖、保留相同闭合词表并补两种新进程导入顺序测试；保留原失败、仅额外重建Agents，后半只读恢复通过，无新告警/模型调用或重复重启。唯一模型来自初次镜像，最终镜像只读验证另列，不宣称最终镜像模型重测。源码7个运行文件/3个原测试差异、14个新增输入，无DDL/运行依赖变更，详细镜像、材料关系和恢复见回执。
