# stingAISOC 服务 v1.0.0 发布

状态：**已发布并开启常驻自动分诊/自动调查**。API于16:41:06、Agents于16:41:51（Asia/Shanghai）定向替换到计划候选；模型配置保持。用户已明确授权，并新建独立生产租户。单条全新raw Kafka验证已实际触发调查、交付partial结果及Markdown；内容质量未验收。16:48快照仅API/Agents改变，其他13个选定容器元数据不变。结束独审结果在文末记录。

## 范围和接入

- 租户：`stingAISOC Production` / `stingaisoc-prod`，ID `f6a5c700-69b8-44fc-8238-609362fb1a9f`。
- 正式输入：`socai2.alerts.raw`，消息必须携带上述 `tenant_id`，遵循 [RawAlert 合同](../integration/v1/kafka.md)。HTTP 接收告警仅用于测试。
- Fusion 保持当前版本和配置，持久化告警后发 `socai2.alerts.fused`；新 Agents 消费组 `socai2-agents-v1-prod-20261022` 处理切换起点之后的消息。
- 自动分诊按原规则/模型决定关闭或升级；升级会直接运行调查并保存 Run、事件、工件和报告，无需人工再次点击。没有自动创建 Case 的承诺；结果按 Alert/Run 读取，见[逐步输入输出](../integration/v1/README.md)及[调查读取入口](../integration/v1/investigation.md)。
- 共享正式 topic 切换后只投生产租户。其他租户的新消息缺少本发布预算时会 hold，不会自动放行；历史测试应继续使用隔离 topic。生产预算文件只授权生产租户，旧预算文件和所有旧记录保留。

## 配置与初始容量

复用21的 Kafka、PG、Redis、ClickHouse、OpenSearch、Neo4j、Qdrant、UEBA、TI 和知识库配置。仅替换已构建的 API/Agents 候选镜像并接通已部署 enrichment URL，不升级依赖或执行数据库结构迁移。候选详情见[构建回执](investigation-candidate-images-20261022.md)，仍不含原7项旧C2/文案修正。

模型网关、模型名称、凭据、单次模型参数及调查上限保持当前值，通过配置摘要比较。启动阶段单并发；生产租户普通分诊预算为滚动24小时10次、200000预留tokens、最多1个未结算调用。这是现有预算保护的保守初始容量，不是正式业务吞吐承诺；到限/unknown须人工评估，不能清账或重放来绕过。调查继续使用原独立预算，分诊预留量不代表全链总用量上限。

专用只读服务 key 包含原7个读权限，另一个 key 仅 `alerts:write`，用于调查前可信PG告警投影。它们与生产租户绑定、不创建交互登录用户；凭据仅保存在21 `/opt/sting-aisoc-socai2/private/release-v1-20261022`，0600/UID10001，以只读目录挂载。五类上下文映射保留原映射再加入生产 reader；生产预算使用独立文件。有效期30天，应在到期前轮换。密钥不入文档/代码/发布包。

审批申请、记忆自动写回/抑制、SIEM写回、告警playbook触发保持关闭。本次授权包括自动关闭告警和自动调查，不包括真实厂商响应动作。

## 发布步骤

1. 核对当前 API/Agents 父镜像及配置摘要；只读渲染原33层加 [v1 overlay](../../deploy/aisoc21/compose.release-v1.yml)，检查环境差异、旧只读挂载和安全限制。
2. 将本地已审候选打 `v1.0.0` tag，按精确镜像ID传到21加载，不从脏工作区重新构建。原父镜像保留。
3. 在同一事务新建生产租户及两枚最小权限 key，生成私有映射文件。保留旧租户/凭据/预算，不打印token。
4. 在 worker OFF 时建立新消费组，读取 fused 各分区当前 end 并显式提交为起点，记录时间、分区及offset。只允许空的新组初始化一次，重复运行拒绝执行，不重置。旧group/unknown完全不动。
5. 只定向替换 API、Agents；先确认 API 新路由可用，再开启 Agents。保留33层父定义、七个旧RO挂载、非root/只读/限权/60秒退出配置。
6. 直接向 raw Kafka 投一条全新、明确标记的合成发布验证告警，检查 Fusion 告警/fused、分诊、升级调查、Run事件/工件/Markdown、用量及提交offset；复用旧功能证据，不重调旧输入。部分调查或质量问题如实记录。
7. 由未参与实现者做结束独审，补运行回执、文档和后端实际 tenant/group/config 指引。

## 停止与回退

优先通过原34层再叠加 [rollback overlay](../../deploy/aisoc21/compose.release-v1-rollback.yml)，执行 `up -d --no-deps --pull never --no-build api agents`。回退到已核父镜像并关闭 worker/自动升级，保留生产租户、所有结果、凭据和新组offset。数据库不回滚、Kafka不倒带、旧unknown不清空。回退不是重放授权。

## 已知边界

历史 C1 自动关闭已有实证；C2 已走自动调查，但内容质量未通过、出现预算/工具/截断限制。本候选的 Kafka 写图直接联合已通过，不能替代新发布的常驻业务验证。开启服务不等于调查结论可靠性已验收；新回执必须区分处理完成、部分结果及内容质量。

## 本批执行回执

- 镜像包：`stingaisoc-service-v1.0.0-20261022.tar.gz`，541057968字节，SHA256 `1121cdc7994c651999c16ca2a6b2689ea207fb17a6c110a2cf3c9e3a2b484b3a`。本地导出与21加载时摘要一致，精确API/Agents ID符合[发布计划](../../deploy/aisoc21/release-v1-plan.json)。原父镜像保留。
- 生产tenant及两key于16:34创建，key到期2026-11-21 16:34:33。凭据未打印，私有文件0600、UID10001、目录0700/只读挂载；原五类映射保留，旧预算文件未修改，生产独立预算仅授权新tenant。
- 16:39:54新组显式初始化fused三个分区起点 `{0:30,1:32,2:39}`，只允许空组一次性初始化。前两次取分区的操作失败；第二次私有诊断确认为consumer元数据缓存尚无目标分区，未执行commit。改为Admin `describe_topics`取分区后第三次成功，失败输出/文件仍保留，不重置旧组。
- 发布前33父层加v1 overlay共34层的渲染检查通过：API仅新增attack context开关；Agents仅计划内配置改变；原API2/Agents7只读bind保留，Agents新增1个RO凭据目录，UID10001、read-only、cap-drop及60秒宽限保持。原模型配置摘要发布前后均为 `d89b11c193accb4913999c2736c7080418a193a03ac1a4a88b222914bae5dae2`。
- API/Agents running+healthy，两readyz均200，Agents readyz列出`socai2.alerts.fused`订阅。未替换Fusion/模型/基础设施，不做数据库结构迁移、旧数据/卷清理或Git提交/推送。
- 唯一新合成告警通过直接raw Kafka发送：partition0/offset37；canonical `00a6434c-eaf1-563d-93dc-70946e46e1d1`，Run `39dd7fba-5f42-5b4e-9653-ae7de5fce32c`。首次分诊TP0.85、未关闭；调查前PG投影success，同Alert邻域5节点，Alert无Case，自动走Deep后持久保存15事件/14工件；Alert/Run/events/artifacts/MD正文5个授权GET均200。
- Markdown工件 `f0f36fcf-d491-4802-b238-7b8b4d59fb4a`，6468字节；新组提交 `{0:30,1:33,2:39}`，与观察end一致。普通分诊预算仅1条，`responded/settled`，预留20000，未产生本批unknown。
- 首次分诊2048 tokens，graph26168，合计28216；7次可见回复。graph为partial，六轮后仍未穷尽，软预算检查发现26168/20000，不能宣称硬上限受控或调查完整完成。Run外层completed、graph/报告status running的差异保持。新增接口样例及实际坐标见[生产接入](../integration/v1/production.md)，机器摘要见[发布JSON](../handoff/service-v1-release-20261022.json)。

本次内容质量未验收：首次分诊将`curl|sh`推成经典C2/高置信恶意，并用缺少授权材料强化攻击判断，超出告警单独支持的事实；报告中“无恶意IOC→benign/FP prior”和“Unknown→单阶段攻击”也保持。TI归因401、UEBA/部分processing-context失败、三个未接入数据类及截断原因均留存。沿[已有问题表](upstream-issues.md)后置评估，不重发旧输入/新模型、不抬预算掩盖。本批技术接通不改变原5/15或追认旧质量通过。

操作脚本位于21 `/opt/sting-aisoc-socai2/ops/release-v1-20261022/`，对应仓库[operator](../../deploy/aisoc21/release_v1.py)。`preview/verify`为只读；`prepare/startpoint`只允许首次准备，不可用于轮换或重置；已部署实例不要再次执行它们。当前服务停止/回退用`python3 .../release_v1.py rollback`，保持所有数据/offset。单条canary脚本仅在本批隔离审查目录和21ops留存，不作为持续数据生产者。

结束独审 `service_v1_release_audit`：**限定 ACCEPT，0项本轮必须修正/发布阻塞**。审查范围为本次固定候选发布、配置/身份/新组、模型保持、合成Kafka技术链与如实结果交付，不包含自治结论质量、全量迁移完成或长期容量验收。独立复核两次15容器快照、Run交换工件及公开材料秘密模式扫描；未新增模型/消息。原5/15及旧质量失败保持。
