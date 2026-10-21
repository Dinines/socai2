# 1F：API/Fusion告警主链回执

2026-10-20，批次`1f-20261020`。已从固定来源迁入API/Fusion构建上下文并在21跑通标记告警主链及所列边界；完整服务端基线尚未冻结。详细原值见[证据JSON](1f-alert-chain.json)，受理合同见[alert-ingress](1f-alert-ingress-contract.md)，源码/差异见[来源清单](../handoff/1f-source-manifest.json)。

## 实际交付

固定上游`34ca18c57dd4175539e5c6dd3d04a72dc057306b`，API872、Fusion115，共987个原版文件（含此前134份SQL），保留完整直接测试和构建输入。3个原文件作最小适配：注册认证入口、让已有图/湖禁用设置在startup生效、增加可关闭的war-room定时任务（原默认开启保留）。原件hash及可逆[补丁](../../deploy/aisoc21/patches/1f-api.patch)独立记录；未改上游参考目录。

新增`POST /api/v1/alert-ingress`只接已有告警，要求Bearer及`alerts:write`，认证主体确定tenant；202返回broker确认坐标和canonical查询路径，不表示融合完成。原submit直写入口未作为主链替代，也未将采集/检测迁入职责。

| 服务/依赖 | 实际状态 |
| --- | --- |
| API | `socai2-api-1`，21 `127.0.0.1:18000`，production、非demo、无匿名绕过 |
| Fusion | `socai2-fusion-1`，21 `127.0.0.1:18003`，实际只订阅`socai2.alerts.raw` |
| 运行隔离 | 两服务均UID10001、只读文件系统、独立socai2网络；API12项后台worker关闭，无Agents/Actions |
| PostgreSQL | aisoc库/aisoc_app runtime；启TLS并reload，无PG重启；新连接verify-full、受控CA/IP校验 |
| Kafka | 新增21:19093 SECURE→SSL listener、CA/IP校验；原9092及内部listener保留，原镜像/数据卷不变 |
| 迁移 | 独立owner容器，REQUIRED/STRICT=1；134文件、134已有ledger、0pending，exit0；运行服务无owner配置 |
| 镜像依赖 | Python3.11.17；API99、Fusion52项实际main依赖均匹配导出requirements；runtime不含Poetry |
| 测试 | Fusion40项、API30项相关测试通过（含7项新入口单测）；替身证据与下面真实基础设施结果分开 |

最终镜像：API `sha256:480ee56324225c3f7981abbd194eeedb25ed3b763041649fb74adbfad76edbd7`；Fusion `sha256:e426842d23dec0ebb408b396343690e907bd0679f28df7f5341cc71993922d8f`。运行镜像中438/55个Python源文件分别与迁入/适配源码一致。

原Dockerfile及锁保留；生成构建配方只切换可达PyPI镜像和API的HTTPS Debian源，仍按Poetry导出、require-hashes安装。基础镜像digest、实际包清单及首次失败日志均已保留；APT仓库/Poetry自身bootstrap闭包没有另行全部锁定，不宣称整个OS镜像已实现长期逐字节重建。

## 输入 → 中间产品 → 最终值

真实输入均为合成、带`1f-20261020`标记的已有告警，不含真实厂商材料。共14次HTTP检查。

| 场景 | 实际调用/中间产品 | 最终值与关系 |
| --- | --- | --- |
| A正常告警 | HTTP202 → raw partition2/offset0 → Fusion new_incident/inserted → PG → HTTP GET200 | tenant A=`5594ae90-f57c-50f5-8332-328b3cad1679`；input=`ace8ad67-be06-57d9-a68d-b2af4ee61e24` → canonical/row/API=`12985175-01aa-54cb-8b53-3578457851cd`；来源与原raw_event保留 |
| 未授权/权限/租户 | 无Bearer401；只读key403；body指定另一tenant403；v2/空来源/未知字段各422 | 被拒绝请求期间topic end offsets不变，无对应发布 |
| 完全相同重投 | 再202 → raw partition2/offset1 → duplicate | 同canonical，无第二告警行，persist_outcome=duplicate |
| 不同发生同指纹 | 新input/event_time/external_id/source → raw partition2/offset2 → duplicate | 仍归入A；新增来源ID和新input ID保留在source_event_ids，PG仍为首条event_time/raw_event；不证明独立发生语义通过 |
| B同特征告警 | B受理→raw partition0/offset0→inserted→B GET200 | B=`968573d9-74cc-5a67-9d50-639e0edcedc4` → canonical=`b314b661-b51f-590a-823d-051ec2d3c3a6`，与A不同；A/B交叉GET均404 |
| broker坏schema | 定向发送v999 → raw partition2/offset3 → PG DLQ | dead letter=`cb94a5c8-8a90-4789-a454-431a639557a5`，reason=unknown schema；按相同partition/offset重读原消息，ID/hash对应 |
| TLS/启动保护 | 实际PG连接查询pg_stat_ssl；无私有CA连接Kafka；production尝试PLAINTEXT resolver | PG使用TLS；不信任CA的Kafka连接被拒绝；原生产明文拒绝仍有效，无明文豁免 |
| 收尾 | 停用本批3个API key，再HTTP请求 | revoked key实际401；保留两tenant各1条告警、审计、DLQ和标记消息 |

不同发生的原始消息和source引用可以对应，但同一PG告警行不保留第二条独立event_time/raw_event/external_id。该原版语义必须在2A进一步核定，冻结前不能承诺按每个发生独立存储或回查完整材料。

未知schema在可信字段解析前已拒绝，DLQ的tenant/source为NULL，不能假定它会出现在租户查询中；回查依据是broker坐标，不擅自给未可信消息分配租户。

## 首次失败与修正

- Docker daemon旧代理失效；经独立containerd下载并导入基础镜像，未重启/修改全机Docker代理。官方包源和HTTP Debian缓慢，改生成配方的下载源，未改锁或跳过hash校验。
- macOS传输伴随文件被`*.sql`计入，首次严格检查发现268文件并失败。只清理141个经AppleDouble签名确认的传输文件，补Docker忽略规则；134个原SQL不变，重新检查成功。
- 首次探针挂到容器根目录导致import路径错误，在发请求前修正。
- 主链首轮14个HTTP检查已成功，脚本最后错误假定未知版本DLQ有source_event_id。实际DLQ已入库；保留首轮failed JSON/log，只按持久坐标与broker原消息定向核对完成，没有清数据或重发主链输入。

## 运维与未验范围

当前32容器，新增两业务容器；除授权重建Kafka并挂TLS材料外，原其余29容器元数据未变，18个旧卷保持。53个旧用户topic起止offset及cluster ID不变。其他项目仅核容器元数据，未执行其业务交易。

凭据在21 `private/`及工作站Git忽略的`.local/aisoc21/private/`，不写入本页。测试key已停用，未发放永久管理员/业务key。使用、停止和受控SSH访问见[21说明](../../deploy/aisoc21/README.md)。CA与旧配置在`private/transport-1f/`，服务证书90天，需续签并验证SAN/IP及单服务恢复；不要重复执行一次性transport准备脚本。

TLS验证服务器，不等于broker客户认证/ACL；旧明文入口保留，单broker无高可用保证。上游runtime未绑定tenant仍可跨tenant读，本批只验证所列API身份/读写路径，不外推全API。Redis逻辑库不是ACL隔离，PG/Kafka/Redis也不是单事务。

模型/向量/调查/审批响应、真实厂商和独立发生语义均未通过本批证明。下一单项按规划为1D Qdrant/embedding结构与存取验收，后续2A及冻结必须处理上述原版归并边界。
