# 1C：21共享Kafka实际回执

2026-10-20，批次`1c-20261020`。按已确认的复用公开数据服务、允许适当重启的范围执行。本批通过Kafka基础设施验收；API/Fusion业务服务仍未导入、构建或部署。原始值与坐标见[证据JSON](1c-shared-kafka.json)，客户端来源见[来源清单](../handoff/1c-source-manifest.json)。

## 实际资源与差异

复用`sting-infra21-kafka-1`，`confluentinc/cp-kafka:7.5.0`，镜像ID `sha256:fbbb6fa11b258a88b83f54d4f0bddfcffbf2279f99d66a843486e3da7bdfbf41`。现有KRaft单节点兼任broker/controller，cluster ID=`MkU3OEVBNTcwNTJENDM2Qg`；保留`sting-infra21_kafka`持久卷，不新增ZooKeeper或broker。

LAN bootstrap及实际advertised broker均为`192.168.1.21:9092`；内部`kafka:29092`未用作本项目跨网络地址。已创建如下空业务topic，未启动业务consumer。

| topic | 分区 | RF/minISR | 保留 |
| --- | --- | --- | --- |
| `socai2.alerts.raw` | 3 | 1/1 | 7天 |
| `socai2.alerts.fused` | 3 | 1/1 | 7天 |
| `socai2.alerts.fused.dlq` | 1 | 1/1 | 7天 |

实际分区/leader/ISR及全0 end offset在证据JSON中。服务变量和计划group见[资源映射](../../deploy/aisoc21/kafka-resources.json)。名称分配不构成broker ACL隔离。

## 输入 → 实际调用 → 最终结果

探针使用独立的一次性Docker容器、bridge网络，经LAN listener访问现有broker。缓存镜像Python3.12.15；从固定Fusion锁按wheel hash安装`aiokafka0.10.0`、`async-timeout5.0.1`、`packaging26.3`，没有安装整套业务依赖。

| 验收 | 实际过程 | 最终值/关系 |
| --- | --- | --- |
| 来源与transport | 复制原`kafka_security.py`，逐字节/hash核对；实际调用production resolver | 原版拒绝PLAINTEXT生效，未设置明文豁免；合成探针显式使用development transport |
| broker地址 | producer经21:9092 bootstrap，读取返回metadata | node1，host=192.168.1.21、port=9092；证明容器能连接返回的地址 |
| 明确发送确认 | 专用topic`socai2.verify.1c-20261020`，发送sequence1/2合成JSON；`send_and_wait`，acks=all、idempotence=true | partition0，broker确认offset0/1；不是仅调用send便称发布成功 |
| 消费/提交 | group=`socai2.verify.1c-20261020.reader`读sequence1，比较原字节/hash；只提交offset+1 | committed next offset=1；sequence2留待恢复后消费 |
| 受控重启 | 所有共享消费组均无活跃成员；保存cluster/topic起止offset/容器元数据，再仅重启Kafka | cluster ID、容器/镜像/挂载/配置保持；53个旧用户topic起止offset不变 |
| 新会话续读 | 重启后同group新consumer读取 | 首条为sequence2、offset1，没有从已提交的offset0重新开始 |
| 重启后新写 | 新producer发送sequence3，再由同consumer读取并提交 | 发送与消费均offset2，最终committed next offset=3 |
| 独立回放 | 无group consumer从earliest重读 | sequence1/2/3对应offset0/1/2，三条原字节、SHA-256和坐标一致 |
| 清理与影响 | 只删除本批smoke topic/group，保留3个空业务topic | 53个旧用户topic和旧group名称保持；仍为30容器/18卷，其余29容器元数据未变 |

初次创建topic后首次produce遇到一次`NotLeaderForPartitionError`，aiokafka在leader就绪后自动重试，最终取得offset0/1确认；该瞬态保留在observations中，不抹掉后称首次无重试。三条消息内容均为`batch/sequence/kind/text`的合成标记，不含真实告警材料。

## 验收限制与下一项

单broker、RF1的重启恢复不证明高可用，也不证明PG/Kafka/Redis间事务一致性或业务exactly-once。现有broker明文无认证，本批仅合成数据测试；业务开启前到1F明确传输配置，保留原版生产/staging明文拒绝，不隐式改变环境或添加豁免绕过保护。其他项目只检查容器元数据，未做其业务交易探测。

实际服务计划使用Python3.11，构建与运行兼容性到1F验证，不能从Python3.12探针外推。Agents main未把group_id传给worker，仍有上游默认组名；1G需明确接线。Fusion主入口默认DLQ落PG，创建Kafka DLQ topic只为Agents预留，不代表两条DLQ路径均已验证。

操作工具及恢复边界见[21部署输入](../../deploy/aisoc21/README.md)。项目回退只停本项目producer/consumer，不清旧topic或共享卷；本次已完成受控单broker重启，保留现场和回执，不重复覆盖。下一单项为1F：API/Fusion源码构建、传输与身份接线、已有告警→Kafka→Fusion→PG/API的首条数据链。
