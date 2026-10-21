# 环境交接

最新限定结果：[C03-R01](c03-triage-review-only.md)代码隔离与定向部署已限定验收：191项断网测试通过（22项新增、169项既有直接测试），0真实模型/新业务写；仅Agents一次构建、一次替换为19f8f1a5，review_only_v1已配置、worker OFF，七只读挂载/60秒宽限保持。旧14材料表、全部告警字段、12预约/240000预留单位/3unknown、十reader、其他35容器/18卷/134迁移及消息水位保持。首次观察脚本RLS错误与189通过/2夹具失败及恢复均保留。当前28层运行定义、185 Agents/770运行Py，prompt/lock v5不变。下一按[人审准入卡](c03-review-only-profile-plan.md)另冻R02，验两条新A/B输入的有限真实main消费与首次结果恢复；原自治质量失败、C04/C05及后续调查/响应仍待验，整体迁移未完成。

以下为 2026-10-20 已保存的环境事实；执行前仍需核实际配置，不含密码或 token。

部署目标为[告警处理服务端](alert-processing-scope.md)，不部署前端/控制台；20的控制台与完整CORE只是历史参考。当前部署计划见[依赖计划](dependency-migration-plan.md)，不能从本页地址表推定新服务已上线或要复用旧卷。

同日初始化补充只读盘点：[20快照](initialization-host20.json)、[21快照](initialization-host21.json)。21共30容器（22运行、8退出）、18卷，与旧服务关闭回执的容器ID/状态/启动时间/重启次数一致；本轮未重配或重启。以上为1A历史快照。1B已复用现有PG/Redis，单独重建Redis且原镜像/卷不变，其余29容器元数据未变，见[1B回执](1b-shared-services.md)；当前资源规划见[依赖迁移计划](dependency-migration-plan.md)。

| 项目 | 记录 |
| --- | --- |
| 新项目部署目标 | **`192.168.1.21`**，用户于2026-10-20确认；当前工作站 SSH `sting-infra21`，实际账号root |
| 参考运行服务器 | `192.168.1.20`，账号 `lychee`，源码/服务目录 `/home/lychee/beenuar` |
| SSH | 当前工作站有 `sting-host20` / `sting-infra21` 已配置免密；不复制私钥到新仓库 |
| 20参考控制台（非本项目交付） | `http://192.168.1.20:3000`，非 demo，版本 19.0.0 |
| 运行版本 | 上游 `34ca18c57dd4175539e5c6dd3d04a72dc057306b`；还包含 embedding overlay |
| 部署范围 | CORE + 独立 embedding，共 16 个运行服务；不是 full 全功能验收 |
| 资源 | 约 32 vCPU、125 GiB RAM；VM 没有已确认可用 NVIDIA GPU |
| 20 模型 | Ollama `0.40.6`，CPU `qwen3-embedding:0.6b`，原生 1,024 维 |
| 对话模型 | `http://192.168.1.43:8000/v1`，`aisoc-test-investigation`，当前为 vLLM compatible API |
| Qdrant | 上游服务 1.7.0；实际进程 nofile 调为 65,536，当前 SDK/search 差异有部署修正 |
| 数据库端口 | AiSOC 容器 PG 仅 `127.0.0.1:15432`；宿主原有 PG `5432` 保留 |
| 21 交接状态 | 四个旧stingAISOC业务容器已停止且restart=no；其他26个容器状态/启动时间/重启次数保持，数据卷保留 |
| 镜像网络 | 原记录中 Docker Hub 直连不可用；基础镜像曾经 DaoCloud 缓存获取，应用镜像来自官方 GHCR |

## 凭据与受控文件位置

- 用户要求记录实际配置后，已于2026-10-20将20运行配置/管理员凭据、21基础设施凭据及旧模型配置保存到新项目被Git忽略的 `.local/configuration/2026-10-20/`。完整变量、地址、文件来源及使用方法见 [配置与凭据索引](configuration.md)。
- 20 的运行 `.env` 和 `docker-compose.override.yml` 在 `/home/lychee/beenuar`，不能把 `.env` 提交 Git。
- 20参考管理员账号 `admin@aisoc.internal`；密码原件在服务器 `deployment/admin-credentials.json`，本地受控副本见配置索引，均不进入公开文档或Git。
- 镜像清单在 `deployment/image-inventory.json`；调用及环境验证记录在 `deployment/`。
- 43 的服务、模型和配置不是本次交接自动修改对象；更换模型需独立核对路由、输出和预算。

## 不能直接推断的事项

早期记录曾只列7个Chat别名，后续配置盘点已确认定义9个别名；真实调用仍只实测一个triage网关smoke，不能推断9角色均可用。独立UEBA、Enrichment、图/湖等full依赖未凭CORE健康状态得到验证；是否需要由当前实际消费路径决定，不自动列为部署目标。

1F已在21部署API/Fusion，见文末；1G Agents/Actions已部署到loopback18004/18005，仅人工调查/结果与dry-run；完整调查/响应尚未验。20 的 Ollama 仅loopback/容器网络可用，21不能直接使用20的localhost或Docker内部服务名；1D已在21独立复现同镜像/模型，实际结构/存取验收见文末。1E已由21真实容器验证五角色到43的路由与JSON结构，详见文末；未证明调查质量或完整业务消费。

## 21 旧服务关闭回执

详见 [host21-legacy-stop.json](host21-legacy-stop.json)。已正常终止：investigation-basic、investigation-api、fusion-api、ueba-api；没有强杀、删除容器/卷或直接更新业务记录。关闭前最近15分钟模型调用0；库中5个running、4个queued的最新更新时间均为历史，未重发或改写。

## 1C共享Kafka补充

已实测21:9092的`confluentinc/cp-kafka:7.5.0`，KRaft broker/controller node1，持久卷`sting-infra21_kafka`；未新增ZooKeeper。LAN advertised listener为21:9092，内部地址`kafka:29092`不供新项目网络直接使用。单broker重启后cluster ID、原镜像/挂载、53个旧用户topic起止offset保持；项目消息及提交进度恢复通过，见[1C回执](1c-shared-kafka.md)。明文无认证、RF1，仅本批合成标记数据验收；后续业务启用前需明确传输配置并保留原生产拒绝机制。

## 1F运行补充

API/Fusion已从本项目固定来源构建，Python3.11.17，非root且只读文件系统；只发布`127.0.0.1:18000`/`18003`，production配置、无demo/匿名绕过。Kafka新增`192.168.1.21:19093`的SECURE→SSL listener，原9092/内部入口保留；仅Kafka容器重建，原镜像与数据卷保持。PG16.15启TLS并重载配置，未重启；新服务采用verify-full和CA文件。原SSL关闭的历史记录仍保留，不能当当前配置。

运行回执见[1F告警数据链](1f-alert-chain.md)，服务使用和停用见[21操作说明](../../deploy/aisoc21/README.md)。自建测试CA与90天服务器证书仅在受控目录；需到期前续签，不把本批配置当生产PKI/高可用验收。测试key已停用，样本数据和审计/消息留作证据。

## 1D运行补充

21独立`socai2-ollama-embedding-1`使用20同一Ollama0.40.6镜像/模型，CPU16核、内存上限32GiB，loopback11435及socai2网络可达；运行qwen3-embedding:0.6b，1024维，size_vram=0。专属bind目录`runtime-data/ollama-embedding`持久化，不复用旧业务卷。内存从8GiB在线提高，无重启。

共享Qdrant1.7.0仅定向重建一次，原镜像/卷/端口/key保留，实际nofile65536/65536。3点写读/查询及恢复通过，仅删除本批集合；现有集合起止为空，其他31容器和18卷名保持。详见[1D回执](1d-vector-embedding.md)，不外推SDK/业务检索质量或Agent消费。

## 1E运行补充

21新增socai2-litellm-1，固定20实际镜像ID、LiteLLM1.106.0，loopback14000/项目网络；4核/8GiB、非root/只读、进程nofile65536。五别名各一次真实43调用及JSON结构通过，共616 tokens；响应deployment ID与实际加载的43路由对应，费用unknown。API/Fusion/embedding仍健康，其余33容器元数据与18卷名保持，无基础设施重启。20原网关和43服务未改，详见[1E回执](1e-model-gateway.md)。

## 1G与模型负载分配

1G源码服务与定向重启结果见[回执](1g-service-baseline.md)，未重建API/Fusion/embedding/gateway或共享服务。用户授权模型按负载分布20、21：两机32核/约126GiB，瞬时可用内存见[资源快照](embedding-host-inventory.json)。本地已有4B模型为下一轮比较候选，优先考虑20新增独立实例；当前0.6B基线保留，尚未切换。计划见[知识复用](knowledge-data-reuse-plan.md)。

## 2A运行差异

仅Fusion升级为`sha256:3c1f8f281901175dc4a4439ee2c78915de5604ac89c97869b03122e9e6bbf0c6`，在保留1F源码镜像上叠加关联成员幂等修复，env与挂载保持。其余35容器/18卷保持，无新模型调用；正常启动必须带[Compose叠加层](../../deploy/aisoc21/compose.correlation-2a.yml)。旧1F镜像/回执保留，详见[2A回执](2a-dedup-correlation.md)。

## 2A-01历史批次：API/Fusion身份版本

该批API为`sha256:d758d6062c613a8fd0dcc9e5d061faf65d6b6974a19a99b39c82298a6595de4c`，Fusion为`sha256:92b0f0696b5fcd5b581b7e409f6a7917d10893396596b3c619fcadc2a779534d`。按consumer→publisher顺序更新并定向重启取证；原私有env保持，仅Compose为API增加`AISOC_ALERT_IDENTITY_VERSION=source-v1`。其余34容器/18卷保持，134迁移记录不变，12条旧告警不可变材料不变。需在前述定义后加[identity叠加层](../../deploy/aisoc21/compose.identity-2a.yml)，旧镜像/回执继续保留，验收见[回执](2a-source-identity.md)。

## 2B-01历史批次：Fusion

该批Fusion升级为`sha256:6ff2a029253adc4301ee8e645ae9fecea218bd592078caf70c94b7de1b3fa3fd`，API仍为2A-01镜像；仅叠加一个RBA源码文件，原env/挂载不变。正常管理在identity层后加[风险层](../../deploy/aisoc21/compose.risk-2b.yml)。仅Fusion重建/定向重启，其余35容器/18卷保持，19条旧材料不变，134迁移保持；两测试key已停用。风险仍为Redis状态；`/ml/status`租户认证材料未配置而返回503。详见[风险回执](2b-risk-idempotence.md)。

## 2B-02历史批次：API/Agents

该批API=`sha256:f88bbcc9579727a8f81acf4e2fb2168485230d7889602943d46e13d711acde54`，Agents=`sha256:4ac381d99e4e68e588f145e51cd2e3e98f02e6d52ce9e9822344ab43edd50b90`；Fusion保持2B-01镜像，env/挂载和自动worker开关不变。正常管理在risk后再加[policy层](../../deploy/aisoc21/compose.policy-2b.yml)。仅API/Agents重建/定向重启，其他34容器/18卷及22条旧告警材料不变，134迁移保持。规则指纹/真实PG/实际方法及30秒TTL/恢复结果见[回执](2b-policy-versions.md)；没有启用自动Kafka分诊。

## 2C-01历史批次：API/Fusion

API=`sha256:53dd54d02169e41fc5d1ed21322c0d66594991d65712f9e0ad0122020ca3eda1`，Fusion=`sha256:106b290cd77ab08f8dfe84563b56e248235012c53ad38d0f639b9b4f52dbccd5`；Agents/Actions保持。policy后加[IOC层](../../deploy/aisoc21/compose.ioc-2c.yml)，只对Fusion开启本地IOC路径，外部增强URL为空；无Go服务或外部信誉请求。25旧告警材料/其他34容器/18卷/134迁移保持，2测试key与2标记IOC均停用。真实证据和限制见[回执](2c-ioc-consumption.md)。

## 2C-02历史批次：API

API=`sha256:b77da9c81bc2868cd5d3bd9f21d02e94316d949b441582324fcdd2da5207214c`，新增只读PG处理上下文接口，IOC层后加[context层](../../deploy/aisoc21/compose.context-2c.yml)。仅API重建/定向重启，env/挂载保持；30旧告警材料、其他35容器/18卷/134迁移保持。测试上下文仅合成fixture，未接真实CMDB/HR/扫描器/普通事件历史；实际消费与限制见[回执](2c-processing-context.md)。

2C-03只读核查21/20已有事件/UEBA入口，见[回执](2c-event-ueba-sources.md)：未启湖/UEBA生产，无服务重启；21共36已有容器/18卷、20共16容器在各自核查前后保持。旧UEBA表为空、20 ClickHouse缺失不等于其他项目没有事件数据；复用其他数据须先明确外部tenant/字段合同。

3A-01只更新/重启Agents为`socai2-agents:suppression-3a-20261020`，其余35容器和18卷保持；真实独立Kafka测试topic/group保留3输入/1DLQ，常驻worker关闭，无基础设施重启或schema变化，见[回执](3a-policy-suppression.md)。

3A-02运行源码/镜像/常驻配置不变，无服务重启，36容器/18卷保持。新独立单分区测试group显式起点0，最终4/3；以同group重启探针无新模型调用。21网关triage成功计数1→7（新增6），其余角色不变；该批API/Fusion/Agents/Actions镜像为context-2c/ioc-2c/suppression-3a/1g。实际边界见[回执](3a-model-triage.md)。

3A-03当时API/Fusion/Agents均为`socai2-<service>:risk-score-3a-20261020`，Actions仍1G；三服务定向重启，其他33容器/18卷保持，无基础设施重启。该批十二层定义见[操作说明](../../deploy/aisoc21/README.md)，各digest/锁依赖/源码检查见[回执](3a-risk-score.json)。网关triage成功计数7→8，其余角色不变；常驻worker继续关闭。新输入允许risk_score=null，旧float-only消费端回退须先核队列兼容。

3A-04当时API/Agents为`socai2-<service>:org-memory-3a-20261020`，Fusion仍risk-score-3a、Actions仍1G；只更新/重启两项，其他34容器/18卷保持。该批十三层定义见[操作说明](../../deploy/aisoc21/README.md)，实际digest/范围见[回执](3a-org-memory.json)。Agents新增UID10001可读的受控只读key目录，无基础设施重启/依赖或DDL变化；网关triage8→9、其余角色保持。两测试tenant读取已验，不等于全tenant配置，常驻worker继续关闭。

## 3A-05历史批次：API/Agents技能读取层

3A-05当时API/Agents为`socai2-<service>:tenant-skill-3a-20261020`，Fusion保持risk-score-3a，Actions保持1G。当前完整运行命令见[21操作说明](../../deploy/aisoc21/README.md)，digest与实测范围见[回执](3a-tenant-skill.json)。仅API/Agents重建及定向重启，其他34容器/18卷/134迁移保持，无基础设施或运行依赖/DDL变更。 该批API image ID=`sha256:645bbdb02e8864c8db5781913ea732f95605194e7d9f59839375c78ede14ec8b`，Agents=`sha256:27ca9899c2674e60714e02f71a431ee37ddae7b4d1cd417050b4396699704f70`。

Agents新增专用`AISOC_TENANT_SKILLS_KEYS_FILE=/run/secrets/tenant-skill/keys.json`及只读目录挂载，宿主`private/tenant-skill-3a`为UID/GID10001、0700，keys.json0600；原组织记忆挂载/env/凭据保持。两测试tenant技能读取及一次真实21→43模型消费已验，网关triage9→10、其余角色不变；重启后A读取v3、B读取v1、两tenant组织记忆均success，原实际模型Run仍为v2。常驻worker、graph及真实响应继续关闭；该批当时KB/处置/身份三类reader仍401，KB后续见下条。

## 3A-06历史批次：API/Agents KB读取层

3A-06当时API/Agents为`socai2-<service>:kb-read-3a-20261020`，Fusion保持risk-score-3a、Actions保持1G；当前完整命令见[21操作说明](../../deploy/aisoc21/README.md)。API image ID=`sha256:95ed232be35add623cbee01595a623df1b0b64715f534d54814502bf57150350`，Agents=`sha256:61b78ddaff810712e4a3f9fccbae9ed9234115886c20f348310114f459d0fa38`。仅API/Agents更新并定向重启；Agents因等义KB boundary note精简额外构建一次，原依赖、共享envelope、系统prompt与lock保持。其他34容器/18卷/134迁移保持，无基础设施重启/DDL/运行依赖变化。

Agents新增`AISOC_TRIAGE_KB_KEYS_FILE=/run/secrets/triage-kb/keys.json`与只读目录挂载，UID/GID10001、目录0700/文件0600，原org/skill四枚key及env/mount/hash/scopes保持。重启后非root实际读取A/B KB各1条、org均success、技能A v3/B v1；常驻worker、graph、审批及真实响应仍关闭。唯一实际模型经21网关→43，1955/140/2095 tokens，网关triage10→11，其余角色不增；两次预算预检未调用模型。PG全文读取与保守更新时间cutoff不等于向量消费或旧正文重建；KB1已提供但模型未引用，该批当时处置/身份两类reader401。详见[回执](3a-kb-read.json)。


## 3A-07历史批次：API/Agents近期处置读取层

3A-07当时API/Agents为`socai2-<service>:dispositions-3a-20261020`，Fusion保持risk-score-3a、Actions保持1G；当前完整命令见[21操作说明](../../deploy/aisoc21/README.md)。最终API image ID=`sha256:41bae3dde2fdccb230622f30af99b6ef807469c930cb7b6aed1baf860eb7cd3d`，Agents=`sha256:90126c76cd8714fafef80c853fec595b0a6c7b702999bd7118e2cab564eae865`。仅API/Agents更新并定向重启，收尾独立导入失败后仅Agents额外构建镜像并重建容器，其他34容器/18卷/134迁移保持；无基础设施重启、运行依赖或DDL变更。

Agents增加`AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE=/run/secrets/dispositions/keys.json`及只读目录挂载，宿主`private/dispositions-3a`为UID/GID10001、0700，keys.json0600；原org/skill/KB六枚key及env/mount/hash/scopes保持。最终非root实际读取A处置3/B1，org均success、技能A v3/B v1、KB用旧原查询各1条。常驻worker、graph、审批与真实响应保持关闭，该批当时身份reader401，后续见下文。

唯一模型在首Agents镜像`sha256:4840767939980238e966007ef4e559f99e7ddfc3fb9c3630fa27d232be16e268`经21网关→43，1779/130/1909 tokens、完整prompt7355字符；网关triage11→12、其他角色不增。三条意见进入输入，note/ID精确引用0，不证明质量。导入环修复后的最终Agents镜像仅做新进程测试和真实常驻读取，模型未重测；后半只读恢复未再次重启或重发输入/模型。实际范围与失败证据见[回执](3a-dispositions.md)、[JSON](3a-dispositions.json)。


## 3A-08历史批次：API/Agents身份读取层

3A-08当时tag为`identity-read-3a-20261020`，API=`sha256:6c5f212bdec86c570fda8b2dad6fe915e683ec7870339deb98f67a491fbc7f8d`，Agents=`sha256:dd64bd753333f1cf705225534b1d0a2430fa43ff38f06a1196f39c67b709e645`；该批仅更新/重启API与Agents，当前完整命令见[21说明](../../deploy/aisoc21/README.md)，Fusion/Actions保持。唯一模型使用同最终镜像，无追加构建；triage12→13、其余角色不增，其他34容器/18卷/134迁移保持。

21 Neo4j5.15 Community本批前0节点/0关系，新增27合成节点/22关系，2 lookup索引/0约束保持，无Neo4j重启或schema初始化。API保持AISOC_DISABLE_NEO4J=true，专用配置按请求READ_ACCESS读取；这是共享高权限账号上的应用访问模式，非数据库只读租户角色，原Bolt未新增TLS。重启后五类reader各用原查询均success；worker/自动graph/审批/真实响应仍关闭。详见[回执](3a-identity-read.md)。


## 3A-09历史复验：当时运行保持

本批运行源码/env/镜像/prompt、十七层定义不变，服务重启0；API6c5f212b、Agentsdd64bd75仍为上文3A-08 digest，Fusion/Actions保持，36个既有容器/18卷/134迁移均保持，图仍为原27/22快照。三次真实模型经原21→43路由，triage13→16、其余角色不增；probe-only方法/失败替身没有额外真实模型。SDK0重试/45秒仅作用于本批探针构造实例，生产默认未改。worker准入不通过，常驻/自动graph/审批/响应仍关闭，见[回执](3a-triage-admission.md)。

## 3A-10-01历史批次：Agents持久确认修复层

3A-10-01当时使用[运行定义](../../deploy/aisoc21/README.md)，API保留identity-read-3a的`sha256:6c5f212bdec86c570fda8b2dad6fe915e683ec7870339deb98f67a491fbc7f8d`；Agents为`socai2-agents:triage-durability-3a-20261020`、`sha256:24071dd2817c34cc7108f38ae931cee43a831c3c5f01f49a65812fb87f51aea1`，Fusion仍risk-score-3a、Actions仍1G。两文件源码差异基于精确旧dd64父镜像，无依赖、schema、prompt、env或挂载变更。仅重建Agents及一次同容器重启回查，35其他容器/18卷/134迁移保持。

143项测试、26项显式HTTP和独立broker/PG边界限定通过；该批后58告警/29Run/78事件/82工件/21成本行，旧14表材料保持。网关各角色计数不增，0真实模型/0新成本行；四次方法替身不是模型质量证据。十枚reader凭据保持，三操作key401，常驻worker/自动graph/审批/真实响应仍关闭，见[回执](3a-triage-durability.md)。

## 当前3A-10-02：Agents首次结果与重投保护层

当前[十九层运行命令](../../deploy/aisoc21/README.md)，Agents为`socai2-agents:triage-recovery-3a-20261020`、`sha256:f7737abde83d288702478806103cd011e4c1552c7851ad9c50e6d0410bcd4569`；API仍identity-read的6c5f212b，Fusion仍risk-score、Actions仍1G。仅Agents基于精确24071dd2父镜像更新三处源码并定向重启，无env/五类挂载、依赖、DDL或prompt变化；35其他容器/18卷/134迁移保持。

当前61告警/32Run/83事件/92工件/21成本行、shadow21；本批两Run完成、一Run只有开始意图，旧14表材料保持。3次发布/7次交付/3次方法替身，网关计数不增、0真实模型。207项测试、55项显式HTTP及重启回查限定通过，十枚reader原文件/hash/metadata/scopes保持、三操作key401；未重测十枚旧查询。实际范围及negative cursor 422见[回执](3a-triage-recovery.md)，常驻worker/自动graph/审批/记忆写回/响应仍关闭。

## 3A-11-02最新配置验收

3A-11-02常驻分诊配置补齐已限定验收，见[回执](3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](3a-triage-reasoning-plan.md)，完整准入/质量未过。

当前补齐的是transport及审批提案禁用，不含常驻topic/group/DLQ项目映射；五reader与通用工具身份仍分开。A积压与unknown不清理/重调；p01理由仍未修，不能将配置就绪当质量或常驻准入。


## C01最新限定验收

C01仅Fusion升级为`delivery-c01-20261020` / `sha256:a8825d41c00dac30682ea273aa502076845df7f04a25a0167b64aa43330391d4`，56个Python文件与107项测试对应；其他35容器/18卷/134迁移保持。当前23层/20来源层，新增5告警/1DLQ，Agents worker及响应仍关闭；真实链路与限制见[C01回执](c01-fusion-delivery.md)。

C03-02D-01当前Agents镜像为`sha256:9cb719ff55d772ebf047f87a06863ae7102feb5be3b9471610113dd9d85728fd`，overlay为`triage-detection-validity-c03`，27配置/24源码层，184/769运行Py及lock对应；原env/七只读挂载/60秒宽限和其他35容器/18卷保持。0真实模型/业务写，worker等保持OFF；[回执](c03-triage-detection-validity.md)只验v5文本和传输，不验质量。

## C03-02D-02验证后的运行状态

[回执](c03-triage-validity-quality.md)：D2质量失败受控停止，2次真实模型回复/4081 tokens；case01过门、case02时区及FP分类/理由未过，case03/04未发，三操作key撤销且逐枚真实401。Agents仍为`socai2-agents:triage-detection-validity-c03-20261021` / `sha256:9cb719ff55d772ebf047f87a06863ae7102feb5be3b9471610113dd9d85728fd`，27Compose/24来源层、184Agents/769运行Py及lock；原env/七只读挂载/60秒宽限与36容器/18卷/134迁移保持，0源码/Compose改动、0重启/DDL。十reader、旧10预约/200000固定单位/3unknown保持，新2responded预约40000单位不等于4081实际tokens。API/Fusion/Actions与原运行来源保持；不新增D2部署层或为此重建服务。下一先另冻人审profile新准入计划，尚未实施或验收；原自治分类/理由质量及常驻准入未过，worker OFF。原C03质量硬门和本批判据保持，C04/C05调查/知识及后续响应仍待逐批验收，整体迁移未完成。
