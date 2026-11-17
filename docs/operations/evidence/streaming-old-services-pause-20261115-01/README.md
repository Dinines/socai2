# 21旧调查业务服务暂停

负责人2026-11-15明确允许先暂停原服务。北京时间17:21完成9个旧业务容器停止，[配置清单](../../../../deploy/aisoc21/streaming-candidate-20261115-01/pause-old-services.json)、[实际驱动](pause_services.py)、[完整前后回执](pause-01.json)。本操作是候选验证前的暂停，不是新版本正式发布。

| 停止范围 | 容器 |
| --- | --- |
| 旧HTTP/Swagger/查阅 | socai2-http-api、socai2-api-docs-swagger-1、socai2-production-workbench |
| 旧API入口 | socai2-api-1、socai2-next-api、socai2-investigation-api |
| 旧归并/投影/执行服务 | socai2-fusion-1、socai2-investigation-projection、socai2-agents-1 |

先停业务入口，再停Fusion，最后停投影/Agents。[在途核对](preflight-02.json)显示当前socai2无running/pending、旧public调查无running；3条历史unknown保留。第一次只读检查误用了status字段，原[失败说明](preflight-01.txt)保留，修正为state后核对，未改业务记录。

9个容器全部停止，ID、镜像、restart policy保持；没有删除容器/卷、清理数据或改执行状态。旧查阅和投影在30秒停止宽限后退出码137，其余7个为0；不将137写成正常优雅退出。暂停后独立docker ps确认旧容器均未运行。

其余29个已有容器前后状态完全一致，PostgreSQL、Kafka、Redis、ClickHouse、Qdrant、Neo4j、OpenSearch、网络代理、LiteLLM/嵌入及工具依赖仍运行，其他项目保持。零模型请求、Kafka投递和数据库写入。

恢复使用回执`restore_commands`中原容器的`docker start`，先下游后入口；不重建、不清卷。当前不会自动恢复，候选整链及统一发布按[第11步设计](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-candidate-design-20261115.md)继续。恢复前须核所选版本、消费起点及现行计划，不能把旧入口与新候选混用。
