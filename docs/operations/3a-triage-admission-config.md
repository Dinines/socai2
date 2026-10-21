# 3A-11-02：常驻分诊配置补齐回执

2026-10-20，批次`3a-triage-admission-config-20261020`。按[执行卡](3a-triage-admission-config-plan.md)完成限定配置验收并部署到21，**常驻worker和完整质量准入仍未通过**。[机器回执](3a-triage-admission-config.json)、[配置来源](../handoff/3a-triage-admission-config-source-manifest.json)。本批0真实模型、0新消息、0offset提交、0凭据/DDL/运行源码变化，无新增单元测试或全仓回归；验证对象是实际Compose差异和真实容器/TLS/Kafka/PG状态。

## 输入 → 配置 → 实际状态

开始时与3A-11-01审计的14表材料、预算、reader、环境和网关快照完全一致：常驻审批提案guard为True，Kafka三项环境未设置，worker因显式disable保持关闭。使用同一Agents镜像`sha256:ab6f563f65455d4f4bdf0b40f2373d5bf0e6b4303acc69795483a29419ce10f5`；未构建或下载镜像。CA原已通过investigation层只读挂到Agents，本批没有新增或改变挂载。

新增[第二十二层](../../deploy/aisoc21/compose.triage-admission-config-3a.yml)渲染结果只比原21层多四个环境值：

| 配置 | 新值及实测 |
| --- | --- |
| `AISOC_AGENT_RAISE_APPROVALS` | `0`，实际函数True→False |
| `KAFKA_BOOTSTRAP_SERVERS` | `192.168.1.21:19093`，与Fusion当前值相同 |
| `KAFKA_SECURITY_PROTOCOL` | `SSL`，非root实际resolver明确SSL |
| `KAFKA_SSL_CAFILE` | `/run/certs/ca.crt`，与Fusion相同、原CA挂载/hash保持 |

层中还显式保留`AISOC_AGENT_KAFKA_DISABLE=1`，它与原env值相同，不计新增值。完整Compose其他服务/网络及Agents非环境部分逐项相同；重建后原环境加这四项与实际环境精确对应，全部Mounts/HostConfig、用户、启动命令、端口和健康检查保持。仅执行一次`up -d --no-deps --pull never --no-build agents`；新容器健康，API/Fusion/Actions及其他32容器保持，共35其他容器/18卷不变。当前为22层Compose定义，运行源码差异仍为19层。

## 实际验证与保持

- UID10001下worker、graph升级、alert-trigger graph、记忆写回、审批提案五个函数均False；bootstrap存在没有开启消费者。实际服务`/readyz`为ready且无订阅，启动日志未出现`auto_triage_worker.enabled`。这验证本次启动配置，没有审计所有手工入口或历史审批表。
- 使用原生产`kafka_client_kwargs`创建的SSL context完成真实broker握手，`CERT_REQUIRED`和`check_hostname=True`，使用同一CA和IP SAN；另以同broker配错误server_hostname发生`SSLCertVerificationError`。未设置明文豁免、未降级证书校验；该负例是一次TLS握手，不是Kafka发布或消费。
- 在新常驻Agents内使用实际环境读取旧预算批六个测试group的committed/end，全部与重建前由Fusion读取的一致。只assign和查询，不poll、subscribe、join或commit：五组1/end1，`a_denied`仍0/end1。没有新topic/group、消息或模型方法入口。
- API439、Agents184个Python文件逐文件hash与审计/本地相同。SDK仍retry0、整次45秒的现有实现和root timeout45、输出512；仅构造配置对象，没有调用模型。
- PG查询均为显式READ ONLY事务。旧14表全部材料hash、134迁移、预算完整五行及十枚reader文件/active/scope/expiry元数据保持；67告警/37Run/92事件/106工件/21成本行、三条未知预约保持。100000为固定预约单位，五行observed_tokens仍null，不当实际usage。
- 原Agents私有env、五reader映射文件、预算policy和公CA hash保持；五类reader在新容器非root可解析，本批未重复HTTP鉴权矩阵。网关五角色计数仍16/3/5/1/3，无新增模型、费用或usage测量。

prepare/deploy/verify三个检查点一次通过；未发生自动重建重试、回滚或故障后重放。新原始材料目录为21`/opt/sting-aisoc-socai2/evidence/3a-triage-admission-config-20261020`及工作站`.local/aisoc21/3a-triage-admission-config-20261020`，0700/0600。旧3A-09的162份、预算批258份及审计15份原始文件和三份旧机器回执hash在本批前后保持。

## 恢复与限制

变更前完整容器配置、21层/22层渲染及仅Agents的恢复定义已保存在21`/opt/sting-aisoc-socai2/private/triage-admission-config-3a/`，工作站受控副本位于`.local/aisoc21/private/triage-admission-config-3a/`。这些文件含环境秘密，不进入Git、公开回执或原始材料包。恢复文件使用既有外部网络、同一原镜像和原只读挂载；渲染已验证，**未实际演练回滚**。

如需恢复，先核worker仍禁用、没有新增调用或输入，再使用该私有`rollback.agents.json`及回执记录的仅Agents命令；不得清理Run、预算、卷、topic或重置offset。恢复旧环境会同时恢复缺Kafka配置和审批guard默认True的旧限制，不能据恢复成功宣称配置缺口已修。日常管理使用当前22层；不能用旧历史短命令覆盖当前配置。

当前只接通Kafka transport，常驻topic/group/DLQ仍为源码默认且未配置项目映射；本批offset观察显式指定旧测试组，不证明常驻已经选择了项目消费范围。预算仅A/B测试tenant，三unknown和A积压不退款、不删行、不重调，未自然跨24小时验过额度。未验rebalance、负载或生产持续消费。

下一单项为[3A-11-03时间与授权理由修复](3a-triage-reasoning-plan.md)，先改分诊提示词并验证实际输入/预算，仍0真实模型；新质量样例另批固定。p01理由、旧工具身份、事件/UEBA及完整知识/引用质量不因本批配置验收消失。常驻worker、自动graph、记忆写回和真实响应保持禁用，审批提案guard现已明确False；未提交或推送。
