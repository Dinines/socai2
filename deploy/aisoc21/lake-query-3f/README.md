# 湖3f查询配置与候选交付

本目录是候选配置，未部署。正式 HTTP 仍是 11-17 r1 的 80 操作；3f 候选新增两个读取入口，原有 80 操作及结构不变。正式表仍须在统一交付时执行 005，新消费者也须按3d配置启动，不能单独把查询 profile 指向48列表。

1. 按环境填写 `query.example.json` 的 database、scopes 和查询上限；scopes 的 tenant/source/mapping 必须与入湖 profile 一致。连接凭据继续保存在受控运行配置。
2. 通过 `SOCAI2_LAKE_QUERY_PROFILE_FILE` 显式选择挂载后的绝对路径；库名须与 `CLICKHOUSE_DATABASE` 一致。HTTP业务上下文使用既有 `SOCAI2_HTTP_CONTEXT_FILE`。缺少或错配配置返回503，不静默换库。
3. 外部 HTTP 与内部 Case 查询进程使用同一来源/查询 profile；C4 v2 冻结 profile 摘要，运行中配置漂移使该绑定不可用。已有 v1 工件仍按原版本识别。Case 的工具说明同步使用当前 `deploy/local-investigation/investigation-policy-case-v1.toml`，当前统一本地 profile 也已更新对象角色描述；不要改写历史发布配置。
4. 查询上限、时间窗、结果字节数及 native transport 时限均在 profile。超限返回失败或未知，不以截断正文冒充完整材料。后台存储保留期仍按3b/3c规则，查询不修改TTL。

接口使用和验证边界见[3f交付回执](../../../docs/operations/evidence/lake-query-3f-20261119-01/README.md)，候选[OpenAPI](../../../docs/operations/evidence/lake-query-3f-20261119-01/candidate-openapi.json)。本步不触发正式发布、消费者恢复或Git同步。
