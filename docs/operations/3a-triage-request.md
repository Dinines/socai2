# 3A-10-03-01：分诊请求界限与开始游标回执

2026-10-20，批次 `3a-triage-request-20261020`，**请求/cursor小批限定通过，整个3A-10-03及worker准入仍未通过。** [范围](3a-triage-request-plan.md)、[机器记录](3a-triage-request.json)、[来源差异](../handoff/3a-triage-request-source-manifest.json)。189项直接相关测试（Agents144/API45）、71项显式真实HTTP检查、0次真实模型。仅更新并重启API/Agents，常驻worker、自动graph、审批、记忆写回和真实响应保持关闭。

## 输入、修改与实际结果

生产旧Agents内实际构造 `make_chat_model("triage", max_tokens=512, json_output=True)`：模型max_retries/request_timeout均None，SDK底层async client为retry2/timeout None。新增回归在修改前为Agents3通过/5失败、API4通过/4失败：两种配置、500/timeout单次请求、整次deadline和负cursor缺陷得到复现，原失败日志保留。不是所有旧测试均失败，也未调用真实模型重现。

三份运行文件最小修改，无依赖、schema、prompt或workflow版本变化：

- factory对逻辑triage角色明确默认SDK `max_retries=0`、`timeout=45.0`。实际生产auto-triage构造不覆盖这些值；BYOK仍走同一默认。其他角色保持原样，调用方仍可显式覆盖factory默认，不能将其宣称成全入口强制策略。
- auto_triage_agent在原safe_ainvoke外增加 `asyncio.timeout(45.0)`；SDK单个传输阶段超时不能代替整个await的截止时间。512输出上限、原成功账本和原异常回退保持。timeout沿原typed error进入确定性回退，高危自动关闭继续被hold为needs_review；外部取消作为CancelledError向上传播，不触发该回退。没有新增自动模型重试。
- investigations的 `since` 下界从0改为-1，SQL仍严格 `seq > since`，原排序/limit/tenant/权限语义保持；-2仍422。

缓存依赖镜像、network=none的真实ChatOpenAI SDK+httpx传输替身验证：500和ReadTimeout各恰好一次请求，成功响应保留18个**合成**usage tokens及JSON/512参数，取消后无重试。整次deadline用0.01秒测试替身缩短等待，实际镜像常量仍45秒；不将该测试记成真实43超时、自然45秒故障或服务端停止证据。直接相关原suite及上一批保存恢复边界合计189通过，首轮修复后无失败。

## 真实API、部署与重启

未创建新告警/Run或发布broker消息，使用3A-10-02既有两份完成Run和一份start-only unknown Run只读核对。生产旧API默认start-only结果为 `items.seq=[-1], next_seq=-1`，随后 `since=-1` 实际422。新API：

| 输入 | 实际中间查询与最终结果 |
| --- | --- |
| 完成Run，limit=1 | 首页只含-1、next_seq=-1；再次传since=-1只得seq1，与默认完整[-1,1]的后一项完全相同 |
| start-only Run，limit=1 | 首页next_seq=-1；since=-1为200、items空、total0、next_seq=null |
| since=0 / since=1 / since=-2 | 分别保持只读seq1、空集、422 |
| B tenant / 无cases:read / 无Bearer | 分别404 / 403 / 401；接受负cursor不改变身份边界 |
| 各单服务同容器重启后 | 三Run完整API产品及负cursor结果与重启前逐值一致，实际SDK根客户端0/45，五类reader映射对A/B可读 |

总71项显式HTTP为旧API2项、新API重启前后各33项、三操作key停用后各1项。没有重测全部十枚reader各自旧查询，也没有本批真实Kafka吞吐、停止恢复或模型质量复验。

20层Compose新增顶层仅指定API/Agents两个镜像，保留原env、五类挂载、非root和只读根文件系统。API新image ID=`sha256:39f68fdb755ec51f3738a7cbdc4879d8ccfd9850d46e068fcf30cd20089091b2`，父镜像6c5f212b；Agents=`sha256:d6b9c7bb7eec6591e152b94a7372ce08289ee7d12b813711ab9c43ddef00c66d`，父镜像f7737abd。完整运行源码逐文件hash与测试时一致；仅三文件替换，没有重新解析/安装生产依赖。Fusion/Actions及其余34容器、18卷、134迁移保持。

14表旧材料hash完全一致，仍61告警/32Run/83事件/92工件/21成本行、21shadow决定。本批新增均0，网关五角色计数不变，模型usage/费用未新增测量。十枚reader原文件/hash/metadata/scopes及图配置保持；三枚短期cases:read/拒绝样例操作key已停用，均401，凭据仅在受控private及本地忽略目录。

初次宿主命令使用不存在的python，改为python3后才执行operator；一次过早finish在deployment.json尚未产生时由入口断言拒绝，在finish检查点/HTTP/重启/停用前停止。等待部署成功后执行一次完整finish，没有重复构建/部署/输入或模型。这些操作前置失败保留，不能写成全部操作首次通过。

## 限制、下一项与恢复

客户端超时/取消只证明停止等待，不能证明远端未执行或已停止；没有响应时usage与远端费用未知，tracker的零观测值不是远端零消耗。本批保留原timeout回退，不新增持久模型调用意图、失败用量或额度扣除账本；进程退出后普通Kafka路径仍按上批claim/unknown保护停止，不靠TTL重调。

下一单项为3A-10-03-02：持久单tenant调用/tokens额度、跨进程并发、积压和停止恢复。先固定原失败/unknown消耗及可恢复状态合同，再以模型替身+真实PG/SSL Kafka验证；不以SDK0/45或内存美元governor代替持久预算。完整质量仍受3A-09 p01时间/授权理由等限制，不开放常驻worker。

回退先停相关新输入/消费者并保留全部Run/start/verdict/工件/topic/group，撤最上层triage-request，恢复API identity-read/Agents triage-recovery，既有十九层与env/挂载保留。旧API可能重新拒绝-1 cursor，旧SDK缺本批界限；回退后继续关闭常驻，不盲重放既有输入或未知调用。正常管理用[二十层运行命令](../../deploy/aisoc21/README.md)。
