# 部署适配交接

当前目标见[告警处理服务端范围](../../docs/operations/alert-processing-scope.md)，执行批次见[依赖计划](../../docs/operations/dependency-migration-plan.md)。本目录保留20完整参考部署的原适配，不要求把其控制台、ingest等所有服务迁入21；只复用范围内实际需要的配置和补丁。

本目录从旧工程部署资料迁入；不含真实 `.env`、凭据、生成的上游模块、完整情报payload或远程运行日志。后续按用户要求另将真实配置存入被Git忽略的 `.local/configuration/2026-10-20/`，见 [配置索引](../../docs/operations/configuration.md)。

用户最新确认 **21 为新项目部署环境**；这里的 `aisoc20` 是20参考部署的原样适配，不表示新项目部署目标仍为20，也不是可直接覆盖21现有Compose的配置。21的端口、独立项目/卷、embedding与模型路由需在第一阶段明确并验证。

- [原部署说明](README.md)：运行目录、已测证据、三条 embedding 接线及限制。
- `docker-compose.override.yml`：需要与固定版本完整上游 Compose 合并，不是独立 Compose 应用。
- `embedding/prepare.py`：显式 `--source` 指向完整上游源码，核3个文件固定hash，再生成运行覆盖模块；hash不符需审查，不强行改校验值。
- `embedding/aisoc_local_embeddings.py`：本地调用、批量/维度/非零校验与调用记录。
- `embedding/reindex_intel.py`：需要实际原情报输入，不能对空库盲跑或改写旧集合。
- `embedding/verify_memory.py`：对运行 API 的带标记测试及清理；执行前核目标。
- `embedding/test_embeddings.py`：离线替身合同，与真实服务分开。

## 启动前仍需准备

若在20复现原参考部署，需要其完整Compose及全部挂载输入。21则按所选服务准备源码/初始化/构建输入、独立受控配置、对应镜像/模型及实际需要的generated/helper/calls挂载；只有需要重建原TI数据时才使用 `original-iocs.json`。这份20 override不直接作为21启动文件，不能在输入缺失时执行 `compose up` 并假定正常。

实际43模型路由和网关配置来自服务器运行文件；已在上述私有目录保留原件及secret，不放在本部署目录或Git中。移植时先核角色别名、凭据引用和实际请求，再决定目标环境接线。
