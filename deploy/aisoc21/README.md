# 21告警处理服务端部署输入

## 2026-10-21原版full配套

本批在既有运行命令的`compose.integrity.yml`之后加入`compose.full-support.yml`、`compose.ueba.yml`、`compose.enrichment.yml`、`compose.threatintel.yml`。它们分别接API/Fusion的ClickHouse与Neo4j、UEBA及Agents上下文、IOC增强、TI/OpenSearch；保留全部原叠加层，不单独用这些增量文件重建API/Fusion/Agents。只对需要的服务执行`up -d --no-deps --pull never`。原全局Agents worker仍OFF。

新增服务仅绑定21 loopback：enrichment 18002、UEBA 18006、threatintel 18008。TI连接已有`spirithub_default`中的OpenSearch，仅用独立`socai2-*`索引；未改旧OpenSearch服务/端口。湖使用共享ClickHouse中新项目`aisoc`库和独立账号。规范化事件topic为`socai2.raw_events.v1`，UEBA输出为`socai2.ueba.anomalies.v1`，新group为`socai2.ueba.v1`；旧告警topic/group与unknown/积压不重放。

APOC是原Attack Path的直接运行依赖。现有Neo4j共享项目在其`/opt/sting-aisoc-infra/compose.yml`后加本仓库`compose.neo4j-full.yml`，只管理`neo4j`单服务；不要把该文件并入socai2业务项目。使用原5.15镜像附带jar，插件目录为`runtime-data/neo4j-plugins`，原data/logs/端口保留。日常管理继续带此overlay，避免下次重建丢原版插件配置。

本批源码、必要差异、实际数据流、凭据位置及验证边界见[full配套回执](../../docs/operations/full-support-migration.md)。以下各批镜像/层数与说明为历史事实，当前版本以本批回执和PROGRESS优先；原构建/迁移脚本不为日常检查重跑。

当前 API 为 `socai2-api:integrity-20261021`（1be37c38），Agents 为 `socai2-agents:integrity-report-semantics-20261021`（4ccf3a6d），Fusion 为 `socai2-fusion:integrity-b1-20261021`（c52b9aac），Actions 保留1G。正常管理使用文末完整二十九层命令；前文各节属于历史批次。B1已限定验收；candidate03组合383项通过，B4/B5/报告修复与PDF原生依赖已部署；candidate04追加32项引用格式直接测试及原七权限只读服务身份，部署后独审及六项HTTP通过。新人工调查四模型10167 tokens、MD/HTML/PDF均200，但仍有内容超出证据支持，不能写质量通过。candidate05再以24项直接测试及独审修默认两个报告节点的假设/范围/处理时间投影，已仅替换Agents、保持全部env/7RO/60秒，部署后773来源/运行配置独审通过；0模型/消息/业务写。有限自动C1关闭通过，C2自动调查partial/内容失败，原结果封存；C2 graph/deep修复尚未部署。worker仍OFF、review_only_v1保持，整体迁移未完成。

以下历史批次工具固定服务名/路径，仅供21基础设施管理员在核对现场后使用：

- `prepare_1b.py`：本地校验固定源码并复制137个原件，生成静默凭据脚本；不同目标文件拒绝覆盖。
- `shared_1b.py`：21受控创建本项目数据库/账号，按134文件完整清单迁移、检验真实权限及标记数据；默认不重启共享服务。
- `redis_restart_1b.py`：已执行的一次性操作记录；保存全部ACL及原Compose，仅为Redis增加ACL文件并重建单服务。已有备份目录时拒绝再次执行，不应日常重复运行。
- [凭据补丁记录](postgres-init-patch.json)：原脚本保留，生成副本通过环境读取密码并静默输出；只在新库执行凭据保护probe，不用作共享PG首启hook。

21源码在`/opt/sting-aisoc-socai2/source/`；凭据在同级`private/`；原始收据在`evidence/1b-20261020/`。工作站受控配置副本为Git忽略的`.local/aisoc21/private/`。不输出整份配置、ACL LIST或docker inspect环境变量。

只读/标记测试复核（会在新aisoc库临时创建并清理本批测试对象）：

```bash
ssh sting-infra21 'python3 /opt/sting-aisoc-socai2/source/deploy/aisoc21/shared_1b.py --root /opt/sting-aisoc-socai2 --verify'
```

不要重复`--provision`；现有项目状态会拒绝覆盖。迁移失败保留收据和ledger，先查原因再决定续跑，不清库重来。Redis当前已加载持久ACL，通常无需`--restore-redis-user`；恢复账号会重设仅本项目ACL并在已配置ACL文件时保存。

没有独立PG/Redis Compose。Redis共享配置备份含账号密码hash，留在21受控目录；恢复前核对卷与ACL加载，禁止清空共享卷。用户允许必要的适当重启，仍须核影响、限定单服务并记录恢复结果。

## 1C Kafka工具与边界

- `kafka-source/kafka_security.py`是原版transport helper，字节不变；来源与固定锁wheel hash见[1C来源清单](../../docs/handoff/1c-source-manifest.json)。
- `kafka-probe-requirements.txt`仅3项探针依赖，固定Python3.12 x86_64 wheel/hash，使用`--no-deps --require-hashes`安装；不是API/Fusion整套依赖。
- `kafka_probe_1c.py before/after`在一次性缓存Python容器中经21:9092产生/消费合成样本，手动提交后验证重启续读。固定smoke topic已删除，旧回执保留；不要为重测覆盖旧证据。
- `shared_kafka_1c.py restart`只操作现有Kafka，要求before probe成功及所有共享消费组无活跃成员，保留原镜像/挂载/配置。已执行，拒绝重复覆盖重启证据。`cleanup`只删除本批smoke topic/group。
- [kafka-resources.json](kafka-resources.json)记录已创建的3个业务topic及待接线变量/group；1C创建时没有业务消费者，后续Fusion已运行，Agents常驻worker仍关闭；Fusion默认DLQ在PG。不要将资源创建写成DLQ业务通过。

探针缓存镜像为`python@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258`，只作1C兼容证据；Python3.11服务构建到1F执行。原版生产明文拒绝保持，未设置豁免，业务启用前先明确传输配置。

## 1F API/Fusion运行

[compose.services.yml](compose.services.yml)只启动socai2的API/Fusion，镜像来自本项目源码构建，端口仅在21本机18000/18003。production、Bearer认证、非root/只读文件系统，未启模型或响应。测试API key已经停用；后续访问需通过正常受控身份/租户发放流程，不启匿名绕过。

- [来源清单](../../docs/handoff/1f-source-manifest.json)含987原版文件、3个修改文件原/现hash；[补丁](patches/1f-api.patch)可逆向核对原件。原Dockerfile/锁保留，`build/Dockerfile.*`只适配PyPI镜像及API的HTTPS Debian下载源，继续Poetry export和require-hashes。
- `transport_1f.py`已为Kafka新增19093 TLS、PG reload启TLS。是一次性基础设施变更，不重复运行；旧配置/私钥在21 private，旧9092仍保留。CA文件在certificates，服务证书90天，需受控续签并核IP/SAN。
- `prepare_services_1f.py`已生成私有配置和标记身份，存在状态时拒绝再次生成。runtime只含aisoc_app凭据；owner仅供一次性迁移容器。
- `start_services_1f.py`先执行REQUIRED/STRICT迁移检查（134/134/0pending），成功后启动本项目两服务，并保留脱敏startup日志。
- `acceptance_1f.py`保存真实链路证据；第一次主链14个HTTP检查通过，但DLQ脚本错误假定source已解析，已通过`--complete-retained`只按坐标核对，不重发原输入。不要直接重跑固定ID样本覆盖旧记录。
- `verify_services_1f.py`核实际镜像依赖、production保护、禁用任务及consumer assignment；`--revoke-test-keys`仅停用本批3个key，样本/审计/消息保留。

工作站如需受控访问21本机API，可自行保持SSH转发：

```bash
ssh -N -o ExitOnForwardFailure=yes -L 18000:127.0.0.1:18000 sting-infra21
```

停止本项目时在21执行，保留DB/消息及共享服务：

```bash
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.services.yml stop api fusion
```

不对共享infra执行down -v、清库或回滚旧业务SQL。API受理202只代表broker确认，失败/unknown不得盲目重投。1F当时独立发生语义未通过，后续2A-01已验source-v1独立上游UUID；旧legacy归并事实保留。TLS不等于broker客户认证/ACL或生产高可用，原始失败日志、版本指纹和回执都保留。

## 1D向量与embedding运行

[compose.embedding.yml](compose.embedding.yml)新增独立CPU embedding；镜像用20实际image ID固定，模型/链接hash见[1D回执](../../docs/operations/1d-vector-embedding.md)。资源为16核/32GiB内存上限，内存+swap总上限64GiB（不预留资源）；仅21 loopback11435和socai2项目网络可达。runtime-data/ollama-embedding包含模型及新实例自己的身份文件，不进入Git或镜像；没有复制20的私钥。

21后续正常启动/停止只操作本项目服务，合并两个Compose文件以包含完整服务定义：

```bash
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.services.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.embedding.yml up -d --no-deps --pull never ollama-embedding
```

停止时将最后的`up ...`改为`stop ollama-embedding`；保留模型目录和证据。`start_embedding_1d.py --reference reference-model-links.json`是本批首次校验/启动工具，历史回执存在时不重复执行并覆盖。`vector_probe_1d.py before/after`使用固定测试集合/ID，不重复运行来替代新业务验收。共享Qdrant的nofile已由`shared_vector_1d.py restart`单独设65536，恢复证据已保存；不要重跑该一次性操作或down共享infra。

模型空间与业务overlay尚未连接：20生成适配已核源hash但未挂载，1G/3C另核21 Qdrant认证、集合及SDK。现有API/Fusion继续用1F配置；本批未启Agents或响应动作。

## 1E模型网关运行

[compose.gateway.yml](compose.gateway.yml)只新增固定image ID的LiteLLM1.106.0，非root/只读、4核/8GiB、nofile65536；[路由](litellm.config.yaml)发布五角色，使用43既有模型。原件在[infra配置](../../infra/litellm/config.yaml)，[差异](patches/1e-litellm.patch)、[资源表](gateway-resources.json)、[回执](../../docs/operations/1e-model-gateway.md)可查。它是服务依赖，不要求控制台或新的数据库。

21正常启动时合并三个文件，只操作新网关：

```bash
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.services.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.embedding.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.gateway.yml up -d --no-deps --pull never litellm
```

停止时将最后的`up ...`改为`stop litellm`，保留配置/回执，不down共享infra。网关只监听21 loopback14000；需从工作站访问时自行保持`ssh -N -L 14000:127.0.0.1:14000 sting-infra21`，并使用本项目受控网关key，不能拿20旧key或43 provider key替代。

`gateway_1e.py start/verify/linkage`为本批有状态验收工具，历史记录存在时不覆盖重跑。`gateway_probe_1e.py`已完成五个固定标记调用；后续新验收需独立批次，勿重发完成/unknown调用。私有env仅在private，client env未加载到现有API/Fusion，1G再映射实际应用变量。

错误key在无虚拟key DB时原版返回400，未改为匿名或掩盖；超时45秒已加载但故障未注入。五角色JSON通过不等于工具/调查质量，重试/fallback若未来恢复原版配置，需要另做对应调用/usage验收。

## 1G Agents/Actions受控运行

[compose.investigation.yml](compose.investigation.yml)新增源码Agents/Actions，仅21 loopback18004/18005、非root/只读/nofile65536。只发布选定人工调查/结果及Actions discovery/dry-run；自动分诊/升级/记忆写回与真实响应不开放。来源、实际持久结果与限制见[回执](../../docs/operations/1g-service-baseline.md)。

正常启动/恢复仅操作指定服务，合并完整项目定义：

```bash
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.services.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.embedding.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.gateway.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.investigation.yml \
  up -d --no-deps --pull never agents actions
```

停止将末行改为`stop agents actions`，保留共享数据及运行证据。已有镜像/tag必须核实际image ID；1G当时Agents为`sha256:3d92fa4e77083c4c6d9bf237634243446ca22eac8b0601ea4727cdd3a90b992c`，Actions为`sha256:8f449d06f54cd225df3365704384d5465410f05c5964d8234c0ef15b15d25da1`。构建使用缓存Python基底image ID校验、原锁及hash安装，版本另见机器回执；不能只凭可变tag复现。

`prepare_services_1g.py`是一次性配置/标记身份生成器，不重跑或覆盖；后续验收用新批次/身份。`services_1g.py --build`校验基底再构建；无build参数的首次启动模式会写初始回执，已有回执后不重跑，正常管理用上述Compose命令。`acceptance_1g.py`用保留ID验证，不能重复发起成功/unknown调查；`verify_services_1g.py`只对照本批环境/来源并停用本批key，不作为通用清理工具。

Agents直接GET结果/报告依赖进程缓存；重启后应通过API的`/api/v1/investigations/{run_id}`及其`/artifacts`路由取持久结果。Case与Run状态分开。无Realtime已验，但增强服务未连接，实际只读工具失败记partial；不把它当合法空结果或已验真实厂商能力。当前JWT签名和服务token均由私有env提供，不使用临时测试key作为永久身份。

知识/较大模型允许复用旧数据并分配到20/21，执行见[计划](../../docs/operations/knowledge-data-reuse-plan.md)。本批未切换embedding或导入旧向量。

## 2A成员重投修复（历史镜像层，当前还需identity叠加）

当前工作目录在1F来源清单之后多一层[2A差异](../../docs/handoff/2a-source-manifest.json)，旧1F镜像、manifest与回执保持。只改Correlator既有成员幂等，未改env/SQL/告警ID；25项测试和真实独立实体复验通过。不同发生存储仍是2A未完成项，不把这一修复当整批通过。

正常启动Fusion时用以下完整定义，避免误切回旧1F镜像：

```bash
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.services.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.embedding.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.gateway.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.investigation.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.correlation-2a.yml \
  up -d --no-deps --pull never fusion
```

停止改为`stop fusion`，共享基础设施不动。2A当时image ID为`sha256:3c1f8f281901175dc4a4439ee2c78915de5604ac89c97869b03122e9e6bbf0c6`。回退时停本项目新输入，用保留1F镜像和前四个定义启动Fusion；保留本批消息/合成数据与错误快照，不清库或修写历史计数。API/Agents/Actions镜像未变。

`prepare_2a.py`、`acceptance_2a.py`、`deploy_2a.py`、`verify_2a.py`都是本批有状态工具，不重跑覆盖旧证据；`deploy_2a.py --verify-applied`只用于本次已部署后核验恢复，不再次重建。正常管理用上面的Compose命令。下一批必须新建标记和实体：仅换source/tag不能隔离按tenant/entity/tactic形成的关联。


## 2A-01 source-v1基础层（当前还需下方2B风险层）

[身份回执](../../docs/operations/2a-source-identity.md)记录当前独立告警身份。原1F及2A成员修复镜像均保留；下列最后一层同时覆盖API/Fusion，当前API增加一个身份配置flag，私有env/数据库schema保持。

```bash
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.services.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.embedding.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.gateway.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.investigation.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.correlation-2a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.identity-2a.yml \
  up -d --no-deps --pull never fusion api
```

此命令是2A-01当时的运行定义；当前正常管理须使用下文二十一层命令。首次升级使用`deploy_identity_2a.py`的逐个consumer→publisher顺序，不以同时up代替受控切换。通用升级前停新输入并核队列，已受理source-v1消息需由支持该合同的consumer处理完。回退也先停输入，不用旧consumer消费新消息、不重新向旧合同提交已受理输入；保留所有行和消息。停止时改为`stop fusion api`，共享服务保持。

新HTTP payload必须显式提供稳定UUID id；同一告警重试不换UUID，新发生使用新UUID。版本及source_alert_id由服务生成；返回accepted仍只代表broker确认。API详情新增fusion_identity/fusion_incident_id/source_event_ids/external_id，身份/关联以项目JSON元数据持久化，旧行无该信息时为null。

`prepare_identity_2a.py`、`deploy_identity_2a.py`、`acceptance_identity_2a.py`和`finish_identity_2a.py`为本批有状态工具，已完成后不重跑覆盖。三枚测试key已停用，后续使用正常受控身份；本次12条broker记录、7条新告警及首次测试失败均保留。费用unknown；完整风险、知识与真实响应仍按后续阶段验。

## 2B-01风险累计历史基础层

2B-01当时API用identity-2a镜像，Fusion更新为`socai2-fusion:risk-2b-20261020`，image ID=`sha256:6ff2a029253adc4301ee8e645ae9fecea218bd592078caf70c94b7de1b3fa3fd`，详见[回执](../../docs/operations/2b-risk-idempotence.md)。以下七层是2B-01历史基础；当前正常管理使用下文二十一层命令。缺risk层会退回旧RBA实现，缺后续层会退回旧API/Agents：

```bash
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.services.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.embedding.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.gateway.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.investigation.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.correlation-2a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.identity-2a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.risk-2b.yml \
  up -d --no-deps --pull never fusion api
```

只停服务时改为`stop fusion api`。升级/回退前停止新输入并核队列；只回退到identity镜像会恢复已知重复加分问题，保留seen集合与既有分数，不清缓存/数据库或减去旧分数。新镜像只多一个源码文件，env/挂载/依赖不变，无DDL。当前Fusion租户状态接口认证未配置，`/ml/status`503保持；不要通过打开匿名模式获取状态。

本批prepare_risk_2b/deploy_risk_2b/acceptance_risk_2b/verify_entity_risk_2b/finish_risk_2b工具已执行，有一次性检查点；不重跑旧标记和已完成消息。真实Redis验收是直接engine调用，不能当HTTP投递；其2秒TTL仅测试实例、仅本批fixture tenant，服务窗口仍86400秒。两key已停用，测试材料保留。

## 2B-02处理规则历史基础层

2B-02当时API/Agents分别为`socai2-api:policy-2b-20261020`与`socai2-agents:policy-2b-20261020`，digest及边界见[回执](../../docs/operations/2b-policy-versions.md)。以下八层为2B-02历史基础，当前正常管理使用下文二十一层命令：

```bash
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.services.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.embedding.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.gateway.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.investigation.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.correlation-2a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.identity-2a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.risk-2b.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.policy-2b.yml \
  up -d --no-deps --pull never fusion api agents actions
```

不需要全部服务时仅选择对应服务名，停止改用`stop <service>`。env、挂载、依赖及自动worker开关保持。缺policy层将把API/Agents回退到旧镜像；回退先停输入/配置写入并核队列，原规则/材料保留。回退会失去指纹/加载状态字段并恢复缓存污染缺陷，不自动回写原处理结果。

`prepare_policy_2b.py`、`deploy_policy_2b.py`、`acceptance_policy_2b.py`、`finish_policy_2b.py`是已执行的有状态工具，不能直接重跑原检查点。3key停用401，新批次另建身份。实际worker抑制方法在独立探针中调用，未开启常驻自动分诊；抑制摘要尚无持久ledger，3A先补验该记录。

## 2C-01本地IOC历史基础层

2C-01当时API/Fusion分别使用`socai2-api:ioc-2c-20261020`、`socai2-fusion:ioc-2c-20261020`；Agents保持policy-2b，Actions保持1G。digest与限制见[回执](../../docs/operations/2c-ioc-consumption.md)。以下九层是2C-01历史基础，当前使用下文二十一层命令：

```bash
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.services.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.embedding.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.gateway.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.investigation.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.correlation-2a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.identity-2a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.risk-2b.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.policy-2b.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.ioc-2c.yml \
  up -d --no-deps --pull never fusion api agents actions
```

只操作所需服务名；停止改用`stop <service>`。IOC层仅开启Fusion本地PG查询，外部URL为空，原私有env保持；没有Go、provider或IOC目标连接。API详情fusion_ioc_lookup=null代表未记录查询，不代表无匹配；first-write状态与当前IOC停用状态分别保存。

本批prepare_ioc_2c/deploy_ioc_2c/acceptance_ioc_2c/verify_ioc_failure_2c/finish_ioc_2c已执行，不直接重跑旧检查点。2key及2条标记IOC均停用保留；新批次另建tenant/标记。回退先停新输入、核队列，撤IOC层回到policy API/risk Fusion，保留历史证据/源行，不重写或重发旧告警。完整2C及Agents旧增强工具仍待后续。

## 2C-02 PG处理上下文保留层与当前完整运行命令

2C-02当时API为`socai2-api:context-2c-20261020`；digest/范围见[回执](../../docs/operations/2c-processing-context.md)。当前保留风险分与五类读取，叠加3A-10-02首次结果保护及03-01请求/cursor层，完整二十五层命令如下：

```bash
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.services.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.embedding.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.gateway.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.investigation.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.correlation-2a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.identity-2a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.risk-2b.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.policy-2b.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.ioc-2c.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.context-2c.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.suppression-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.risk-score-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.org-memory-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.tenant-skill-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.kb-read-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.dispositions-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.identity-read-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.triage-durability-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.triage-recovery-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.triage-request-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.triage-budget-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.triage-admission-config-3a.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.fusion-delivery-c01.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.triage-material-c02.yml \
  -f /opt/sting-aisoc-socai2/source/deploy/aisoc21/compose.triage-reasoning-c03.yml \
  up -d --no-deps --pull never api fusion agents actions
```

只操作需要的服务；停止改用stop。context层无env/依赖/DDL变化，撤层会回到IOC API并失去新接口，资料保留。升级/回退先停新输入、核队列，不重发未知/已受理消息，不重写旧分数。

GET /api/v1/alerts/{id}/processing-context需alerts:read，返回当前只读材料与独立priority，原alert.priority/priority_score和队列排序保持。多匹配/截断/失败不猜分，普通事件历史/UEBA不在此接口连接。

prepare_context_2c/deploy_context_2c/acceptance_context_2c/verify_context_failure_2c/finish_context_2c是已执行的有状态工具，不重跑旧标记；3key已停用。合成tenant资料保留，只用于合同测试，不冒充生产导出。

## 3A-01规则抑制保留层

[suppression层](compose.suppression-3a.yml)当时只换Agents镜像为`socai2-agents:suppression-3a-20261020`，配置/挂载/依赖/DDL保持，worker仍关闭；实际摘要、原账本行及broker提交证据见[回执](../../docs/operations/3a-policy-suppression.md)。当前还须保留下列risk-score层及上述二十层完整命令，不用早期历史短命令覆盖当前服务。

本批prepare/deploy/acceptance/broker/finish工具已执行，有一次性检查点，不重跑已受理输入；3key已停用，2测试topic/group保留7天retention。回退先停新输入/相关消费者，撤suppression层回policy版Agents，保留账本/消息/卷；旧版缺持久保护，自动worker继续关闭。

## 3A-02有界真实模型验证（常驻配置不变）

操作输入prepare/acceptance/broker/finish_model_triage_3a已执行，有一次性检查点，不盲目重跑；独立探针从空测试topic提交0开始，最终4/3，同group重启无新处理。该批十一层运行命令未变，没有启用常驻Kafka worker。两测试tenant的shadow配置和7条标记告警/Run保留，3key停用；6成功回复/7406 tokens，费用unknown。首轮标签污染和后续盲测、当时risk默认0/context401等限制见[回执](../../docs/operations/3a-model-triage.md)，不能据本次样例直接开放自动分诊。

## 3A-03三服务风险分层（保留）

[risk-score层](compose.risk-score-3a.yml)当时将API/Fusion/Agents更新为`socai2-<service>:risk-score-3a-20261020`；当前Fusion保留该镜像，API/Agents再叠加org-memory、tenant-skill、kb-read、dispositions及identity-read层，Agents另叠加triage-durability/triage-recovery层，Actions仍1G。该批digest、实际输入/模型/账本及恢复限制见[回执](../../docs/operations/3a-risk-score.md)与[JSON](../../docs/operations/3a-risk-score.json)。当前二十五层完整命令在上文，常驻worker关闭。

prepare/deploy/acceptance/finish_risk_score_3a已完成，有一次性检查点，不盲目重跑。四条新告警、1Run与两测试tenant的shadow行保留，3key停用；无group Kafka探针不提交、不新增topic，仅对捕获的缺失分信封作一次真实分诊。两份Connectors静态文件仅供原测试AST读取，未启动或迁入该服务。

回退先停新输入及消费者，保留队列/PG/卷；旧Fusion输入是float-only，不能直接消费新null消息。须用兼容消费者排空或保留本schema层后再撤其他变化，不把未知改写成0、不重发已受理输入。组织记忆批次后续已完成，见下一条。

## 3A-04组织记忆读取保留层

[org-memory层](compose.org-memory-3a.yml)当时只更新API/Agents为`socai2-<service>:org-memory-3a-20261020`，Fusion风险分层及Actions保持。完整digest和实际验收见[回执](../../docs/operations/3a-org-memory.md)、[JSON](../../docs/operations/3a-org-memory.json)。当前二十五层完整命令在上文，只操作所需服务；自动worker、graph、审批与真实响应保持关闭。

Agents新增`AISOC_ORG_MEMORY_KEYS_FILE=/run/secrets/org-memory/keys.json`和只读目录挂载。宿主`/opt/sting-aisoc-socai2/private/org-memory-3a/`归UID/GID10001，0700；keys.json为0600、tenant UUID→各自reader key，禁止写入Git或镜像。仅配置A/B测试tenant，各key只有alerts:read，有效期见回执；3枚操作key停用，2枚reader key保留。GET使用标准Bearer/alerts:read/tenant交集，旧X头单独不能授权。

目录挂载支持原子替换keys.json，保持所有者/权限，下一次读取重新选择映射；映射移除/轮换先于缓存。默认120秒缓存不向API即时重验key，服务端撤销/到期及语句编辑删除要到刷新后生效；每次核已缓存expires_at，不在请求失败时使用旧材料。需要立即停止采用某tenant材料时，移除其映射并核unavailable/not_configured。

prepare/deploy/test/acceptance/finish_org_memory_3a已执行，有一次性检查点。1条告警、1真实模型Run和1独立probe-only事务恢复Run及5条语句保留，失败投影不等于额外模型调用；不盲目重跑已受理输入。回退先停相关消费者、保留PG/队列/工件，再撤org-memory层恢复旧镜像/env/挂载，不删除材料或复发模型。旧能力缺授权/失败来源语义，不视作等同验收。

配置与受控凭据索引见[configuration](../../docs/operations/configuration.md)。技能、KB和处置后续见下文；当前五类reader已接通，完整质量仍未过。

## 3A-05技能读取保留层

[tenant-skill层](compose.tenant-skill-3a.yml)当时只更新API/Agents为`socai2-<service>:tenant-skill-3a-20261020`，Fusion风险分层和Actions保持；须保留上文完整二十五层定义。digest、347项测试、实际Fusion→模型采用与历史工件关系见[回执](../../docs/operations/3a-tenant-skill.md)、[JSON](../../docs/operations/3a-tenant-skill.json)。仅API/Agents重建并定向重启后回查通过，其他34容器/18卷/134迁移保持，3操作key停用401、2技能reader保留200；不启自动worker、graph、审批或真实响应。

Agents增加`AISOC_TENANT_SKILLS_KEYS_FILE=/run/secrets/tenant-skill/keys.json`及只读目录挂载。宿主`private/tenant-skill-3a/`归UID/GID10001、0700，keys.json0600；仅配置A/B测试tenant的独立settings:read reader key，30天，到期2026-11-19T08:36:24.337460Z。原org-memory目录/env/两枚alerts:read key完整保留，权限不能互换。GET /api/v1/tenant-skills/resolved/active采用标准Bearer/settings:read/tenant交集，旧X头不授权。

轮换用原子替换keys.json并保留权限；映射移除/轮换在缓存前生效，默认120秒不保证API端单独撤销/到期/编辑/退休即时生效，缓存每次逐项核expires_at，刷新失败不采用旧材料。需要即时停止采用时移除该tenant映射并核not_configured。选择分数为加法权重，不能解释成严格优先级。

prepare/deploy/test/acceptance/finish_tenant_skill_3a为本批有状态工具，有一次性检查点，不盲目重跑已受理告警/启动的模型调用。合成预激活样例、4条failed/probe-only replay FK占位和v3头轮换只验读取，不是编写/回测/激活流程通过。deep investigation旧版本pin失败仍可落当前，graph关闭，须在3B开放前处理。

回退先停相关消费者，保留PG/队列/工件，再撤tenant-skill层恢复3A-04 API/Agents；保留org-memory层/挂载/身份，不删除合成材料或复发模型。旧镜像缺本批授权与失败/选择来源语义，不等同该批验收。当前还有下文KB/dispositions/identity-read/triage-durability/triage-recovery层，不能只撤中间层管理当前镜像；后续3A-10-01见下文，其余子项仍规划，其他上下文/引用及整体质量另验。

## 3A-06 KB读取保留层

[kb-read层](compose.kb-read-3a.yml)当时更新API/Agents为`socai2-<service>:kb-read-3a-20261020`，Fusion保持risk-score-3a、Actions保持1G；必须使用上文完整二十五层定义。该批API image ID=`sha256:95ed232be35add623cbee01595a623df1b0b64715f534d54814502bf57150350`，Agents=`sha256:61b78ddaff810712e4a3f9fccbae9ed9234115886c20f348310114f459d0fa38`。236项相关测试（API38/Agents198）、真实PG/API/nonce采用块、一次真实模型及重启回查见[回执](../../docs/operations/3a-kb-read.md)、[JSON](../../docs/operations/3a-kb-read.json)；来源见[差异清单](../../docs/handoff/3a-kb-read-source-manifest.json)。只更新并定向重启API/Agents，其他34容器/18卷/134迁移保持，自动worker、graph、审批和真实响应保持关闭。

Agents增加`AISOC_TRIAGE_KB_KEYS_FILE=/run/secrets/triage-kb/keys.json`及只读目录挂载；宿主`private/kb-read-3a/`归UID/GID10001、0700，keys.json0600。仅A/B测试tenant各有独立knowledge_base:read reader key，30天，到期2026-11-19T09:05:50.327428Z；3短时操作key已停用401，2 KB reader保留且200，原org/skill四枚key及映射/env/mount/hash/scopes保持。KB GET采用Bearer/knowledge_base:read/tenant交集，X头不授权，reader的告警/KB写入被拒绝。轮换用原子替换并保留权限，映射移除/轮换在缓存前生效；默认120秒不保证服务端撤销、到期、文档编辑或删除即时生效。

该路径为PG english全文检索，不使用embedding或既有向量索引；created/updated cutoff保守排除后来创建/修改的行，不重建旧正文。六条KB资料及必要检索词/压缩均为合成读样例，不是实际SOP质量。原守卫、JSON转义、UNTRUSTED_DATA/nonce边界及系统prompt/lock保持；KB局部编码避免中文隐式二次截断，等义精简inline note，最终采用子集、确切文本/hash与引用表一致。

两次模型前literal预算预检8717/8105均未调用模型，失败检查点/日志保留；受控压缩本批合成正文/标题并保留旧新hash/更新时间，再精简note后从原告警检查点恢复，未重发已受理输入。最终prompt7861字符未截断，唯一实际模型1955/140/2095 tokens、unpriced1/费用unknown，提供KB1但模型未引用KB标记，引用质量未过。中间note措辞断言失败保留，恢复原短语后198项重测通过；没有删除断言、改共享envelope或运行依赖。

prepare/deploy/test/acceptance/finish_kb_read_3a及追加checkpoint工具均有一次性状态，不盲目重跑accepted ingress或已启动模型。新增1告警、1真实模型Run（2事件/5工件）和1独立probe-only恢复Run（1事件/1 KB工件）保留。回退先停相关消费者、核已受理队列并保留PG/工件，在撤去上层dispositions后，再撤kb-read恢复3A-05镜像/env/挂载；原org/skill层和凭据保持，不删除样例或复发模型。旧镜像缺本批授权、失败状态及确切KB来源语义，不能当同等能力；同时保留risk_score=null的旧消费者兼容限制。

该批当时处置/身份两类reader401，处置后续见下条；知识/引用与完整调查质量另验。


## 3A-07近期处置读取保留层

[dispositions层](compose.dispositions-3a.yml)当时更新API/Agents为`socai2-<service>:dispositions-3a-20261020`，Fusion保持risk-score-3a、Actions保持1G；使用上文完整二十五层定义。最终API image ID=`sha256:41bae3dde2fdccb230622f30af99b6ef807469c930cb7b6aed1baf860eb7cd3d`，Agents=`sha256:90126c76cd8714fafef80c853fec595b0a6c7b702999bd7118e2cab564eae865`。396项相关测试（API91/Agents305）、60项显式HTTP检查、一次真实模型及失败恢复/重启回查见[回执](../../docs/operations/3a-dispositions.md)、[JSON](../../docs/operations/3a-dispositions.json)和[差异清单](../../docs/handoff/3a-dispositions-source-manifest.json)。其他34容器/18卷/134迁移保持，无基础设施重启/DDL/运行依赖变化；常驻worker、graph、审批与真实响应保持关闭。

Agents新增`AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE=/run/secrets/dispositions/keys.json`及只读目录；宿主`private/dispositions-3a/`为UID/GID10001、0700，keys.json0600。仅A/B测试tenant各有独立alerts:read reader，30天，到期2026-11-19T09:43:22.888022Z；三短时操作key停用401，两reader最终200，原org/skill/KB六枚key及映射/env/mount/hash/scopes保持。alerts:read为已有scope，并非本接口专属权限；GET feedback/recent-dispositions使用Bearer/tenant交集/显式RLS，X头不授权，新reader写ingress/反馈403。受控位置见[configuration](../../docs/operations/configuration.md)，不要复活旧操作key或直接重跑prepare生成新副作用。

轮换以原子替换keys.json保留所有者/权限，读取先选专用映射，再按tenant/URL/身份/rule/entities/limit/cutoff选择缓存。默认120秒不保证服务端单独撤销/到期、意见编辑或删除即时生效；实际缓存内撤销仍success，TTL0刷新401且无旧材料，映射移除后须核unavailable/not_configured。同rule优先于仅entity匹配，再按created_at及ID排序；created cutoff不能重建编辑过的旧意见，API投影hash不是历史版本证明。

唯一实际模型在首Agents镜像`sha256:4840767939980238e966007ef4e559f99e7ddfc3fb9c3630fa27d232be16e268`执行，三条个人意见进入1336字符块/7355字符完整prompt，1779/130/1909 tokens、unpriced1/费用unknown；needs_review/自报0.65，note/ID精确提及0，概括参考不证明因果采用或质量。模型Run2事件/6工件，独立probe-only恢复Run1事件/1处置工件；真实PG故障及重复不追加已验，失败投影没有模型。新rule/entity对原skill selection及KB均no_match，原三能力使用原查询独立核保持。

初394项通过后收尾独立进程导入出现ImportError，保留失败证据；移除新reader对app.agents包初始化依赖、用固定的闭合词表并补两种新进程导入顺序测试，最终396项通过。仅额外构建镜像并重建Agents容器，env/mount不变；最终镜像非root读取处置A3/B1、org success、skill A v3/B v1、KB旧查询各1条通过。模型及原重启工件核对来自首镜像，最终镜像模型未重测。后半仅从检查点只读恢复，没有新重启、key变更、输入或模型，不能写成全首次通过。

prepare/deploy/test/acceptance/finish_dispositions_3a是已经执行的一次性有状态工具，原model-call-started/after/verify/restart/撤销检查点保留；不盲重试已受理告警、模型或成功key生命周期。回退先停相关消费者、核队列并保留PG/工件，撤去上层identity-read后，再撤dispositions恢复3A-06 API/Agents及移除本批专用env/mount，保留原三读取层/凭据。旧镜像缺本批授权与明确采用来源语义，不当同等能力；不删除合成行或重发输入/模型，保留risk_score=null消费兼容限制。

该批当时身份reader401，后续见下条；旧增强/工具身份、真实事件/UEBA与完整调查/引用质量仍未过。


## 3A-08历史批次：API/Agents身份读取

[identity-read层](compose.identity-read-3a.yml)当时使用`identity-read-3a-20261020`，API=`sha256:6c5f212bdec86c570fda8b2dad6fe915e683ec7870339deb98f67a491fbc7f8d`，Agents=`sha256:dd64bd753333f1cf705225534b1d0a2430fa43ff38f06a1196f39c67b709e645`。该批为十七层；当前二十五层仅操作所需服务，Fusion/Actions保持；496项/62 HTTP、一次模型1781 tokens及重启回查见[回执](../../docs/operations/3a-identity-read.md)/[JSON](../../docs/operations/3a-identity-read.json)/[来源](../../docs/handoff/3a-identity-read-source-manifest.json)。其他34容器/18卷/134迁移保持，worker/自动graph/审批/真实响应关闭。

API保持AISOC_DISABLE_NEO4J=true，新增`AISOC_IDENTITY_GRAPH_CONFIG_FILE=/run/secrets/identity-graph/config.json`与宿主`private/identity-graph-3a`只读目录；Agents新增`AISOC_TRIAGE_IDENTITY_KEYS_FILE=/run/secrets/triage-identity/keys.json`与宿主`private/identity-read-3a`只读目录。均UID/GID10001、0700/0600；两枚graph:read reader到期2026-11-19T10:31:59.338283Z、最终200，三操作key401，旧八枚/四目录保持。轮换与受控位置见[配置](../../docs/operations/configuration.md)，身份缓存300秒不保证即时撤销。

图原0/0、本批27合成节点/22关系及2 lookup/0约束保持，无Neo4j重启/schema。专用READ_ACCESS不是数据库只读租户角色，原共享高权限/Bolt未新增TLS；导入cutoff不重建旧HR路径或当前授权。唯一模型与最终镜像相同，身份1进入6931字符prompt，不作质量通过。首次after脚本TEXT错绑UUID在输入前失败；仅修脚本、resume-after-matrix从已完成矩阵后继续，无重复撤销/输入/模型，初版operator无独立备份/hash。

有状态工具不盲重跑；恢复先停相关输入/消费者、核队列并保留图/PG/工件，该批回退只撤当时最上层identity-read恢复3A-07镜像及移除本批两个专用env/mount，保留旧四读取层/身份。不开通用图初始化、不清图/库/卷、不重发模型。3A-09受控复验后续见下条。


## 3A-09历史复验：当时未改变运行层

该批不构建/替换镜像，不改运行源码/env/prompt，不重启服务；当时使用identity-read-3a-20261020与十七层。当前须使用上文二十五层命令。三次真实模型/5223 tokens及51项显式HTTP、broker/PG替身边界见[回执](../../docs/operations/3a-triage-admission.md)/[JSON](../../docs/operations/3a-triage-admission.json)/[操作来源](../../docs/handoff/3a-triage-admission-source-manifest.json)。分类3/3仍有p01理由缺陷，可靠性缺口阻止worker准入；常驻/自动graph/审批/真实响应继续关闭。

prepare/acceptance/broker/finish_triage_admission_3a已带一次性检查点执行，固定inputs原样提交、评分材料不挂入进程。探针实例SDK retry0/timeout45不改变生产retry2/timeout None；ack/model-started后不能盲重发。坏schema/ledger False静默提交和冷重投重入模型已复现；暖恢复五类来源被写成not_requested，首次工件保护不能代替完整结果恢复。仅短时独立group停止/恢复，非服务重启或常驻准入。

三操作key已撤销401，十枚reader及旧五挂载保持；新操作配置只在受控private。首次broker import与finish计数断言失败已保留，后者无最初独立完整stderr；修operator后只读恢复，没有重复撤销/输入/模型/重启。保留topic/group/PG/图/工件，不回滚当前运行层或清数据。后续3A-10-01见下文，[可靠性总计划](../../docs/operations/3a-worker-reliability-plan.md)其余子项仍为规划。

## 3A-10-01历史批次：Agents持久确认与坏消息

[第十八层](compose.triage-durability-3a.yml)当时只更新Agents为`socai2-agents:triage-durability-3a-20261020`，image ID=`sha256:24071dd2817c34cc7108f38ae931cee43a831c3c5f01f49a65812fb87f51aea1`。API保留identity-read的6c5f212b，Fusion保留risk-score，Actions保留1G；两处运行源码基于精确dd64父镜像，无env/五类挂载/prompt/依赖/schema变更，常驻worker、自动graph、审批与真实响应保持关闭。该批为十八层，当前正常管理使用上文二十五层，仅操作所需服务。

143项窄测试、26项显式HTTP、7次broker发布/8次交付、真实PG工件及一次同容器重启回查限定通过，见[回执](../../docs/operations/3a-triage-durability.md)/[JSON](../../docs/operations/3a-triage-durability.json)/[来源](../../docs/handoff/3a-triage-durability-source-manifest.json)。只有四次模型方法替身、0真实模型，无伪造exchange/usage。正常一Run/一事件/五来源工件保持，该批后58告警/29Run/78事件/82工件/21成本行；35其他容器/18卷/134迁移及十枚reader保持，三操作key401。

首次测试136通过/7新增替身失败、首次部署Env列表顺序断言失败均留证。前者只修新增测试，后者在已完成构建/重建后只读verify-existing恢复，没有第二次构建或重建；最终另做一次同容器重启。发送/受理/开始检查点存在后不盲重跑；真实无pool样例只恢复DLQ确认，没有恢复PG。

该批回退先停相关新输入/消费者、核队列并保留PG/工件/topic/group，仅撤当时最上层triage-durability恢复旧dd64 Agents，保留五类读取env/挂载。旧镜像有已知静默提交缺陷，回退后继续关闭常驻，不将已确认或unknown消息自动重放。严格schema只覆盖已解码Kafka入口，不证明未知tenant的数据库授权；后续3A-10-02见下文，生产SDK预算仍按[总计划](../../docs/operations/3a-worker-reliability-plan.md)另验。

## 3A-10-02历史层：首次结果与重投保护

[第十九层](compose.triage-recovery-3a.yml)只更新Agents为`socai2-agents:triage-recovery-3a-20261020`，image ID=`sha256:f7737abde83d288702478806103cd011e4c1552c7851ad9c50e6d0410bcd4569`，精确父镜像24071dd2。API保留identity-read的6c5f212b，Fusion仍risk-score、Actions仍1G；三处源码变化，无env/五类挂载/依赖/DDL/prompt变化。该批当时为十九层；当前使用上文完整二十五层，仅操作所需服务，常驻worker/自动graph/审批/记忆写回/响应仍关闭。

207项测试、55项显式HTTP、3次broker发布/7次交付/3次方法替身及一次同容器重启回查首轮通过，见[回执](../../docs/operations/3a-triage-recovery.md)/[JSON](../../docs/operations/3a-triage-recovery.json)/[来源](../../docs/handoff/3a-triage-recovery-source-manifest.json)。0真实模型，两完成Run整产品保持，一Run仅有开始意图；当前61告警/32Run/83事件/92工件/21成本行。旧14表材料及35其他容器/18卷/134迁移保持，原十枚reader文件/hash/metadata/scopes保持、三操作key401；未重测十枚原查询。

保护仅适用于Kafka普通live路径：同worker仅重试原完整材料保存，cold进程只复用可核首次结果，已有开始而无结果则unknown，不自动抢占或重算。direct triage/replay、纯离线shadow与原policy/memory抑制分支不据此扩张。默认API事件可读[-1,1]，但显式负cursor仍422；seq=-1表示处理开始，不证明真实模型请求。unknown若被reaper标failed也不授权重调，SDK预算与负cursor修复见下一3A-10-03[总计划](../../docs/operations/3a-worker-reliability-plan.md)。

回退先停相关输入/消费者、核队列并保留Run/start/verdict/工件/topic/group，只撤最上层triage-recovery恢复24071dd2，保留既有env/挂载。旧版本忽略持久开始保护，回退后常驻必须继续关闭；不删除unknown Run或自动重放原消息。完成复用不重放后续动作，不外推模型恰好一次、rebalance或长期容量。

## 3A-10-03-01保留API层：请求界限与cursor

[第二十层](compose.triage-request-3a.yml)仅指定API/Agents的triage-request-3a-20261020镜像。API image ID=sha256:39f68fdb755ec51f3738a7cbdc4879d8ccfd9850d46e068fcf30cd20089091b2，Agents=sha256:d6b9c7bb7eec6591e152b94a7372ce08289ee7d12b813711ab9c43ddef00c66d；父镜像分别6c5f212b/f7737abd。三份源码变化，无env/挂载/prompt/依赖/DDL变更。triage SDK默认retry0/45秒，auto-triage整次调用45秒截止；负cursor -1已接受、-2仍422。见[回执](../../docs/operations/3a-triage-request.md)/[JSON](../../docs/operations/3a-triage-request.json)/[来源](../../docs/handoff/3a-triage-request-source-manifest.json)。

189项测试、71项HTTP及两服务重启回查通过，0新告警/Run/模型/broker发布。61告警/32Run/83事件/92工件/21成本行及14表材料不变，34其他容器/18卷/134迁移与十枚reader保持，三操作key已停用401。prepare/test/deploy/finish_triage_request_3a均为本批一次性工具，不盲目重跑既有检查点。一次过早finish被入口断言拒绝且无副作用，待部署后完整执行；没有重复构建/部署或模型。

仅客户端界限与cursor通过，不能证明远端停止、usage为零或持久租户额度。下一03-02核调用/tokens额度、并发、积压和停止恢复；常驻worker/自动graph/审批/记忆写回/真实响应关闭。回退仅撤最顶triage-request，保留原十九层、旧镜像/env/挂载/全部PG与队列；旧cursor和SDK限制会退回，不重发unknown或开启常驻。

## Agents保留层：3A-10-03-02持久额度与停止

[第二十一层](compose.triage-budget-3a.yml)只更新Agents，最终image ID=sha256:ab6f563f65455d4f4bdf0b40f2373d5bf0e6b4303acc69795483a29419ce10f5，父镜像d6b9c7bb；原API/Fusion/Actions保持。新增一个policy环境变量和只读挂载，原env/五reader保持；先备份/独立恢复项目库核14表及134原迁移，再应用[migrations/001_triage_budget.sql](migrations/001_triage_budget.sql)。runtime不DDL，原134迁移登记保持。详见[回执](../../docs/operations/3a-triage-budget.md)/[JSON](../../docs/operations/3a-triage-budget.json)/[来源](../../docs/handoff/3a-triage-budget-source-manifest.json)。

263项测试、137项API检查、6发布/14交付/5次模型HTTP替身开始、0真实模型。每次20000固定预留单位不是实际usage或费用；当前5预约/100000单位、三未知占位保留。实际10.012917秒stop后无子任务/offset不前进，fresh未知不重调；显式调测试policy后同group积压恢复没有退款或重发。当前67告警/37Run/92事件/106工件/21成本行，旧14表材料/35其他容器/18卷/十reader保持，三操作key401。

prepare/test/deploy/ingress/run/broker/finish_triage_budget_3a为本批有状态工具，检查点存在后不得盲重跑。恢复校验身份、import、probe权限及operator屏障失败留证；两次受控Agents镜像更新均在验收前，最终再同容器重启。A积压offset0/end1及三未知不清理/抢占；测试policy最终A/B各24小时、3次、60000预留、2未确认，不作生产额度推荐。旧lookup错误仍沿原确认DLQ合同。

下一为3A准入剩余阻塞复核；常驻worker/graph/审批/记忆写回/真实响应OFF。回退只撤最顶budget层，保留独立表/预约/全部PG/消息及原二十层，恢复triage-request Agents和旧env/挂载；旧镜像不执行预算表约束，回退后不启常驻或重调unknown。

## 3A-11-01审计补充（当时为21层，配置补齐见下文22层）

只读[回执](../../docs/operations/3a-admission-review.md)发现常驻Agents的审批提案guard实际True、Kafka bootstrap/TLS未配；worker/graph/记忆写回仍禁用。旧隔离broker探针使用了显式注入的SSL配置。下一按[3A-11-02执行卡](../../docs/operations/3a-triage-admission-config-plan.md)补配置，仍不启worker、不消费积压、不重调unknown；当前命令不冒充已补配置。

## 3A-11-02常驻分诊配置补齐（第二十二层）

[配置层](compose.triage-admission-config-3a.yml)新增审批提案0、Kafka bootstrap/SSL/CA三项；显式保持worker disable1，CA沿用原只读挂载。仅Agents同镜像重建一次，源码/挂载/HostConfig保持；真实TLS/错误主机名拒绝、六测试组只读offset及旧14表/预算/reader/其他35容器保持，0模型/消息/提交。详见[回执](../../docs/operations/3a-triage-admission-config.md)/[JSON](../../docs/operations/3a-triage-admission-config.json)/[来源](../../docs/handoff/3a-triage-admission-config-source-manifest.json)。

该批当时完整22层；当前使用上文完整25层运行定义，只操作所需服务。恢复只用受控`private/triage-admission-config-3a/rollback.agents.json`，命令和hash在回执；它含环境秘密，不输出或提交。仅渲染验证、未演练回滚；恢复会回到缺Kafka/审批默认True的旧限制，仍须worker禁用。该配置保持1G已有项目topic/group及派生DLQ映射，不能据此认定消费起点已验，不可直接移除disable开关启worker。三unknown/A积压保持，下一[理由提示词修复](../../docs/operations/3a-triage-reasoning-plan.md)，完整质量未过。


## C01 Fusion持久交付（第二十三层）

[交付层](compose.fusion-delivery-c01.yml)仅将Fusion更新为`delivery-c01-20261020`（`sha256:a8825d41c00dac30682ea273aa502076845df7f04a25a0167b64aa43330391d4`）；env/挂载/依赖/DDL保持，56个运行Python文件与107项测试对应。真实PG/Redis/SSL Kafka故障恢复、首次材料重投、新legacy和DLQ及升级后HTTP通过，0模型；结束与撤key后独立审计通过，见[回执](../../docs/operations/c01-fusion-delivery.md)/[来源](../../docs/handoff/c01-fusion-delivery-source-manifest.json)。

C01当时23层命令完整保留前22层，只操作所需服务。两枚操作key已撤销401，旧14表/reader/预算/原积压、其他35容器/18卷/134迁移保持。原probe断言和启动失败、无重发的恢复与两次计数补充均保留，不重跑固定批次。回退定义为受控`private/completion-c01/rollback.fusion.json`，仅渲染验有效；回退保留新行/快照/消息，不reset group。

新PG首次快照可在Redis过期后恢复；暖dedup无完整结果、旧PG无snapshot行会hold。Redis全部痕迹过期不保证永久unknown或完整恢复；非法JSON未验持久DLQ，重投保留原fusion_decision，当前重复投递看persist_outcome。后续C02限定通过见下文；Agents worker仍禁用，整体迁移未完成。


## C02 分诊材料、缓存与停止（第二十四层）

[材料层](compose.triage-material-c02.yml)仅将Agents更新为`triage-material-c02-20261020`（`sha256:c9cf8920a8ac2a601acf6f8cab5033f448f22a4aec103f43e94ddfd707ce98d5`），增加`stop_grace_period: 60s`；其余env/挂载/依赖/DDL保持。184份运行Python与118项测试、一次断网生产SDK探针对应，部署前/后独立审计通过；见[回执](../../docs/operations/c02-triage-material-cache-stop.md)/[来源](../../docs/handoff/c02-triage-material-cache-stop-source-manifest.json)。该批当时24层；当前须用上文完整25层，仅操作所需服务。

本批0真实模型/新业务PG写/新凭据/消息读取或发送/offset提交，旧材料、三unknown、积压、十reader、35其他容器/18卷/134迁移保持。第一次部署已完成重建但检查因`HostConfig.Binds`顺序不同退出1；原失败/操作脚本保持，单独只读检查确认仅顺序变化，未重复重建。回退定义在受控`private/completion-c02/rollback.agents.json`，只验证渲染；保留数据/消息，worker须OFF。

普通Kafka live停跨告警pattern结论复用，保留同Run PG恢复和费用限制；direct/replay旧缓存未修。停止测试覆盖协作任务/异常清理，未验实际在途Docker停止，不保证不协作任务的取消时限。模型质量未复测；下一[C03理由与常驻准入](../../docs/operations/c03-triage-reasoning-plan.md)按提示、盲测、窗口逐批审计，不直接启worker。


## C03-01 时间与授权提示词（第二十五层）

[理由层](compose.triage-reasoning-c03.yml)仅将Agents更新为`triage-reasoning-c03-20261021`（`sha256:039f2cb09684c29e170b8907572196ff5559c9d7991837fc431a12d113350985`）；继承C02的60秒停止宽限，env/挂载/依赖/DDL保持。`triage.system`版本2→3、对应lock变化，其他21份prompt和schema保持；184运行Py及非Py lock分别核对。88项测试、一次断网生产SDK探针和部署前/后独立审计通过，见[回执](../../docs/operations/c03-triage-reasoning.md)/[来源](../../docs/handoff/c03-triage-reasoning-source-manifest.json)。

本批0真实模型/业务PG写/新凭据/消息读取或发送/提交；旧14表、5预约/3unknown、六旧group、十reader与35其他容器/18卷/134迁移保持。重复测试入口在Docker前被独占门拒绝，唯一测试88通过；探针路径在首次执行前修正、旧build operator保存，唯一probe通过。受控回退为`private/completion-c03/rollback.agents.json`，仅渲染验证，不能回退数据/消息或重调unknown，worker须继续OFF。

实际完整messages为6560字符/6502规范UTF-8字节，保留8000/16000、retry0/45秒/输出512限制；合成18 tokens不计真实usage。此批仅证明约束/材料传输及版本对应；[C03-02](../../docs/operations/c03-triage-reasoning-plan.md)另冻新样例/判据/额度再复验，质量通过后才验03常驻。主group仍无已提交起点，不能直接依赖`latest`静默排除历史。当前管理须用上文完整25层。

## C03-02受控停止

[本批回执](../../docs/operations/c03-triage-quality.md)：仅一例真实模型1998 tokens后质量未过，后三例未执行；技术持久链通过，3操作key已撤销401。脚本启动前权限失败及独审恢复原件保留。0镜像/配置/运行源码层变化、0服务重启，当前完整25层命令保持，worker仍OFF。现有6预约/120000预留单位含三旧unknown，预约单位不是实际usage；不退款或重放。原quality group end/commit1与DLQ0保留，主组仍无已提交起点；下一新四例须另冻卡，不重跑本批operators或以latest启动主组。

## C03-02B受控停止

[本批回执](../../docs/operations/c03-triage-quality-recheck.md)：新case01一次真实模型1918 tokens，TP分类正确但无据断言未授权，理由质量失败；后三例未执行，三操作key停用并逐枚401。0镜像/配置/运行层变化、0重启/DDL，当前完整25层命令保持，worker OFF。累计7预约/140000预留单位含三旧unknown；原02和新02B两个独立quality组均end/commit1、DLQ0保留，不重放。下一02C-01另卡0模型最小授权prompt澄清，不重跑本批operator，不用latest启动主group。

## C03-02C-01授权事实边界

[回执](../../docs/operations/c03-triage-authorization.md)与[当前来源](../../docs/handoff/c03-triage-authorization-source-manifest.json)：v4/lock、88直接测试/4断网SDK通过，0真实模型/新业务写。仅Agents一次更新9ba6、env/七RO bind/60秒宽限保持，worker OFF。当前运行须使用以下完整26层，前文25层为父版历史；不得直接启主group或以latest跳过历史。

```bash
cd /opt/sting-aisoc-socai2
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f source/deploy/aisoc21/compose.services.yml \
  -f source/deploy/aisoc21/compose.embedding.yml \
  -f source/deploy/aisoc21/compose.gateway.yml \
  -f source/deploy/aisoc21/compose.investigation.yml \
  -f source/deploy/aisoc21/compose.correlation-2a.yml \
  -f source/deploy/aisoc21/compose.identity-2a.yml \
  -f source/deploy/aisoc21/compose.risk-2b.yml \
  -f source/deploy/aisoc21/compose.policy-2b.yml \
  -f source/deploy/aisoc21/compose.ioc-2c.yml \
  -f source/deploy/aisoc21/compose.context-2c.yml \
  -f source/deploy/aisoc21/compose.suppression-3a.yml \
  -f source/deploy/aisoc21/compose.risk-score-3a.yml \
  -f source/deploy/aisoc21/compose.org-memory-3a.yml \
  -f source/deploy/aisoc21/compose.tenant-skill-3a.yml \
  -f source/deploy/aisoc21/compose.kb-read-3a.yml \
  -f source/deploy/aisoc21/compose.dispositions-3a.yml \
  -f source/deploy/aisoc21/compose.identity-read-3a.yml \
  -f source/deploy/aisoc21/compose.triage-durability-3a.yml \
  -f source/deploy/aisoc21/compose.triage-recovery-3a.yml \
  -f source/deploy/aisoc21/compose.triage-request-3a.yml \
  -f source/deploy/aisoc21/compose.triage-budget-3a.yml \
  -f source/deploy/aisoc21/compose.triage-admission-config-3a.yml \
  -f source/deploy/aisoc21/compose.fusion-delivery-c01.yml \
  -f source/deploy/aisoc21/compose.triage-material-c02.yml \
  -f source/deploy/aisoc21/compose.triage-reasoning-c03.yml \
  -f source/deploy/aisoc21/compose.triage-authorization-c03.yml \
  up -d --no-deps --pull never --no-build agents
```

仅该Agents的受控回退定义保存在21私有`completion-c03-authorization/rollback.agents.json`；保持worker OFF，回退不撤销任何旧告警/Run/消息。旧7预约/140000预留单位/3unknown、两旧quality组end/commit1和DLQ0保留；新质量卡尚未执行。初始observer导入副作用及112追加计数已有归属和修订证据，不删除旧目录文件来还原计数。

## C03-02C-02质量受控停止

[本批回执](../../docs/operations/c03-triage-authorization-quality.md)：C03-02C-02三例实际模型共5971 tokens：前两例分类/理由通过，第三例把缺少转移证据误判为FP并推断规则误报，按冻结判据失败停止，第四例未发。三操作key已停用且实际401，技术持久链与结束独审通过；新增3告警/Run、9事件/21工件/3成本/3shadow、3responded预约60000单位，0QA。旧7预约/140000单位/3unknown保持，累计10预约/200000单位；26配置/23源码层保持，0重启。保留quality topic/group最终end/commit3及DLQ0，不重放。当前仍用上文完整26层运行命令。下一C03-02D-01只澄清“无法核查检测条件不等于规则误报”的最小提示词边界，先做0真实模型直接验证和独审；不重调旧三例、不改旧判据。理由/分类质量与常驻准入仍未过，worker OFF，整体迁移未完成。

## C03-02D-01检测有效性边界

[本批回执](../../docs/operations/c03-triage-detection-validity.md)及[当前来源](../../docs/handoff/c03-triage-detection-validity-source-manifest.json)：v5检测有效性提示词及lock已限定验收：88项直接测试、4次断网生产SDK完整body（7827–7917字符/7742–7832规范UTF-8字节），0真实模型/新业务写。仅Agents一次更新至9cb719，原env/七只读挂载/60秒停止宽限保持，当前27配置/24源码层。旧14表、10预约/200000预留单位/3unknown、十reader、其他35容器/18卷/134迁移保持，部署前/运行/收尾三审通过。前三批质量/停止事实及7条旧未发输入保持。当前须用以下完整27层，前文26层为父版历史。

```bash
cd /opt/sting-aisoc-socai2
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f source/deploy/aisoc21/compose.services.yml \
  -f source/deploy/aisoc21/compose.embedding.yml \
  -f source/deploy/aisoc21/compose.gateway.yml \
  -f source/deploy/aisoc21/compose.investigation.yml \
  -f source/deploy/aisoc21/compose.correlation-2a.yml \
  -f source/deploy/aisoc21/compose.identity-2a.yml \
  -f source/deploy/aisoc21/compose.risk-2b.yml \
  -f source/deploy/aisoc21/compose.policy-2b.yml \
  -f source/deploy/aisoc21/compose.ioc-2c.yml \
  -f source/deploy/aisoc21/compose.context-2c.yml \
  -f source/deploy/aisoc21/compose.suppression-3a.yml \
  -f source/deploy/aisoc21/compose.risk-score-3a.yml \
  -f source/deploy/aisoc21/compose.org-memory-3a.yml \
  -f source/deploy/aisoc21/compose.tenant-skill-3a.yml \
  -f source/deploy/aisoc21/compose.kb-read-3a.yml \
  -f source/deploy/aisoc21/compose.dispositions-3a.yml \
  -f source/deploy/aisoc21/compose.identity-read-3a.yml \
  -f source/deploy/aisoc21/compose.triage-durability-3a.yml \
  -f source/deploy/aisoc21/compose.triage-recovery-3a.yml \
  -f source/deploy/aisoc21/compose.triage-request-3a.yml \
  -f source/deploy/aisoc21/compose.triage-budget-3a.yml \
  -f source/deploy/aisoc21/compose.triage-admission-config-3a.yml \
  -f source/deploy/aisoc21/compose.fusion-delivery-c01.yml \
  -f source/deploy/aisoc21/compose.triage-material-c02.yml \
  -f source/deploy/aisoc21/compose.triage-reasoning-c03.yml \
  -f source/deploy/aisoc21/compose.triage-authorization-c03.yml \
  -f source/deploy/aisoc21/compose.triage-detection-validity-c03.yml \
  up -d --no-deps --pull never --no-build agents
```

仅Agents回退定义位于21私有`completion-c03-detection-validity/rollback.agents.json`，回退不撤销PG/消息或旧结果；worker仍OFF。Dockerfile父标签及完整ID检查方式见[勘误](../../docs/operations/c03-triage-detection-validity-source-note.md)。下一C03-02D-02另冻四条新对照输入，验证有反证FP、明确授权BTP、缺证NR及事件窗外NR；本四例不复验v5 TP，后续常驻新TP仍须实际独审。旧三批质量失败与七条未发输入保持，worker OFF，质量/常驻及整体迁移未完成。

## C03-02D-02有界质量验证（运行保持）

[本批回执](../../docs/operations/c03-triage-validity-quality.md)与[证据清单](../../docs/handoff/c03-triage-validity-quality-evidence-manifest.json)：质量失败后已受控停止并完成结束、撤key后及封后独立审计：两次真实模型回复共4081 tokens；case01 FP分类/理由通过，case02时区换算错误且把窗内已授权活动判为FP，分类/理由失败，case03/04未执行。三操作key已停用并逐枚真实401，十reader及旧10预约/200000单位/3unknown保持。新增2告警/Run、6事件、14工件、2成本/2shadow、2responded预约40000单位，0QA；预约单位不是usage。告警仍new、auto_closed=false，不声称发生错误关闭。当前27配置/24来源层、184Agents/769运行Py及lock保持，0源码/Compose改动、0重启/DDL。首次发送前因本地验收算子遗留旧输入SHA/v4合同被拒绝，0业务/模型；原失败、旧stop与显式恢复审计/独立断网合同probe/新质量stop全部保留，未重复freeze、身份、额度或topic，不重调旧输入。运行来源仍为[D1来源](../../docs/handoff/c03-triage-detection-validity-source-manifest.json)，其SHA为`057993d4a2710182c79c33385563fca8bcf86a0f60f0f4bc8f0663cfbb43a612`。上节完整27层命令原样保留，不新建D2 overlay或部署层。下一先另冻人审profile新准入计划，尚未实施或验收；原自治分类/理由质量及常驻准入未过，worker OFF。原C03质量硬门和本批判据保持，C04/C05调查/知识及后续响应仍待逐批验收，整体迁移未完成。


## C03-R01 review_only_v1 人审隔离

[C03-R01](../../docs/operations/c03-triage-review-only.md)代码隔离与定向部署已限定验收：191项断网测试通过（22项新增、169项既有直接测试），0真实模型/新业务写；仅Agents一次构建、一次替换为19f8f1a5，review_only_v1已配置、worker OFF，七只读挂载/60秒宽限保持。旧14材料表、全部告警字段、12预约/240000预留单位/3unknown、十reader、其他35容器/18卷/134迁移及消息水位保持。首次观察脚本RLS错误与189通过/2夹具失败及恢复均保留。当前28层运行定义、185 Agents/770运行Py，prompt/lock v5不变。下一按[人审准入卡](../../docs/operations/c03-review-only-profile-plan.md)另冻R02，验两条新A/B输入的有限真实main消费与首次结果恢复；原自治质量失败、C04/C05及后续调查/响应仍待验，整体迁移未完成。

Agents当前镜像为 `sha256:19f8f1a52875b0a16c75890046eeec3fc308995cf73a5bc52899afa076958110`。模型建议保持unreviewed，effective decision固定needs_review/confidence=null；旧数值0仅为policy sentinel，不是模型估计。canonical Alert全部字段不写，代码阻止自动关闭/QA/剧本/graph/审批及各种写回。SIEM writeback源码默认开启，不能声称其env为0；profile阻止该调用，worker保持OFF。R01只有离线接缝与部署验收，真实新分支留R02。

```bash
cd /opt/sting-aisoc-socai2
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f source/deploy/aisoc21/compose.services.yml \
  -f source/deploy/aisoc21/compose.embedding.yml \
  -f source/deploy/aisoc21/compose.gateway.yml \
  -f source/deploy/aisoc21/compose.investigation.yml \
  -f source/deploy/aisoc21/compose.correlation-2a.yml \
  -f source/deploy/aisoc21/compose.identity-2a.yml \
  -f source/deploy/aisoc21/compose.risk-2b.yml \
  -f source/deploy/aisoc21/compose.policy-2b.yml \
  -f source/deploy/aisoc21/compose.ioc-2c.yml \
  -f source/deploy/aisoc21/compose.context-2c.yml \
  -f source/deploy/aisoc21/compose.suppression-3a.yml \
  -f source/deploy/aisoc21/compose.risk-score-3a.yml \
  -f source/deploy/aisoc21/compose.org-memory-3a.yml \
  -f source/deploy/aisoc21/compose.tenant-skill-3a.yml \
  -f source/deploy/aisoc21/compose.kb-read-3a.yml \
  -f source/deploy/aisoc21/compose.dispositions-3a.yml \
  -f source/deploy/aisoc21/compose.identity-read-3a.yml \
  -f source/deploy/aisoc21/compose.triage-durability-3a.yml \
  -f source/deploy/aisoc21/compose.triage-recovery-3a.yml \
  -f source/deploy/aisoc21/compose.triage-request-3a.yml \
  -f source/deploy/aisoc21/compose.triage-budget-3a.yml \
  -f source/deploy/aisoc21/compose.triage-admission-config-3a.yml \
  -f source/deploy/aisoc21/compose.fusion-delivery-c01.yml \
  -f source/deploy/aisoc21/compose.triage-material-c02.yml \
  -f source/deploy/aisoc21/compose.triage-reasoning-c03.yml \
  -f source/deploy/aisoc21/compose.triage-authorization-c03.yml \
  -f source/deploy/aisoc21/compose.triage-detection-validity-c03.yml \
  -f source/deploy/aisoc21/compose.triage-review-only-c03.yml \
  up -d --no-deps --pull never --no-build agents
```

正常管理保持完整28层、七只读bind和60秒停止宽限。回退先停消费者，只回退Agents定义；不删除数据/预算或重放unknown。受控父定义保存在private/completion-c03-review-only/test-recovery-r03/agents-rollback.json，使用前须root核现场；不据此启动legacy自治worker。


## 完整性修复 B1/B2/B3/I2 组合

B1已完成[入口验收](../../docs/operations/integrity-b1.md)。B2默认调查权限/上下文、B3 PG全文知识消费、I2正常graph用量组合的冻结candidate02通过257项直接测试和独审，API/Agents已定向更新；本节不认定真实模型/自动调查已通过。冻结[源码候选清单](../../docs/handoff/integrity-20261021-source-manifest.json)保留，后续B4工作区变动不混入本次镜像。首个candidate01未部署，普通完成SQL参数类型问题已修正并强化实际状态断言，旧失败证据保留。

第二十九层[compose.integrity.yml](compose.integrity.yml)复用已有API/Agents父定义，只替换镜像；API新增专用Agents服务身份的私有env_file，值与Agents既有token相同，其他原env/bind不变。Fusion使用B1私有认证文件。凭据文件保留在21 private，禁止打印配置全文。Agents七只读bind、60秒停止宽限及worker OFF、review_only_v1、审批/自动graph关闭保持。

```bash
cd /opt/sting-aisoc-socai2
docker compose --project-directory /opt/sting-aisoc-socai2 \
  -f source/deploy/aisoc21/compose.services.yml \
  -f source/deploy/aisoc21/compose.embedding.yml \
  -f source/deploy/aisoc21/compose.gateway.yml \
  -f source/deploy/aisoc21/compose.investigation.yml \
  -f source/deploy/aisoc21/compose.correlation-2a.yml \
  -f source/deploy/aisoc21/compose.identity-2a.yml \
  -f source/deploy/aisoc21/compose.risk-2b.yml \
  -f source/deploy/aisoc21/compose.policy-2b.yml \
  -f source/deploy/aisoc21/compose.ioc-2c.yml \
  -f source/deploy/aisoc21/compose.context-2c.yml \
  -f source/deploy/aisoc21/compose.suppression-3a.yml \
  -f source/deploy/aisoc21/compose.risk-score-3a.yml \
  -f source/deploy/aisoc21/compose.org-memory-3a.yml \
  -f source/deploy/aisoc21/compose.tenant-skill-3a.yml \
  -f source/deploy/aisoc21/compose.kb-read-3a.yml \
  -f source/deploy/aisoc21/compose.dispositions-3a.yml \
  -f source/deploy/aisoc21/compose.identity-read-3a.yml \
  -f source/deploy/aisoc21/compose.triage-durability-3a.yml \
  -f source/deploy/aisoc21/compose.triage-recovery-3a.yml \
  -f source/deploy/aisoc21/compose.triage-request-3a.yml \
  -f source/deploy/aisoc21/compose.triage-budget-3a.yml \
  -f source/deploy/aisoc21/compose.triage-admission-config-3a.yml \
  -f source/deploy/aisoc21/compose.fusion-delivery-c01.yml \
  -f source/deploy/aisoc21/compose.triage-material-c02.yml \
  -f source/deploy/aisoc21/compose.triage-reasoning-c03.yml \
  -f source/deploy/aisoc21/compose.triage-authorization-c03.yml \
  -f source/deploy/aisoc21/compose.triage-detection-validity-c03.yml \
  -f source/deploy/aisoc21/compose.triage-review-only-c03.yml \
  -f source/deploy/aisoc21/compose.integrity.yml \
  up -d --no-deps --pull never --no-build api agents fusion
```

按需把最后操作改为 `stop api agents fusion`；不操作共享基础设施、不清卷、不重放旧unknown。回退须核当前镜像与各自private父定义，保留业务记录和预算；不得用历史28层命令覆盖本层或据此启用自治。
