# 湖3b存储配置与升级入口

本目录是待统一发布的交付材料，不代表21正式表已迁移。只支持已核实的单节点48列基线及其005兼容增量；集群、其他列类型或TTL先核差异。示例不含凭据，运行账号继续从部署既有受控配置读取。

1. 复制`storage.example.json`到受控部署目录，明确`database`，保留已确认的映射及两项400天设置。`database`必须与当前进程`CLICKHOUSE_DATABASE`一致；不存在、漏字段或不同库均拒绝执行。此次接入采用每次INSERT的`ingest_time`，重试刷新400天。旧映射租户策略仍按`event_time`，上限取profile的`legacy_days`。
2. 新装用API镜像执行`python -m app.scripts.lake_schema --profile <storage.json> --output <schema.sql>`，审阅并在所选空库执行生成的SQL。参考`services/api/clickhouse/001_init.sql`同样由这份列定义和示例profile生成；其他辅助表保持原样。不要仅替换库名便假定另一环境保留策略相同。
3. 升级及新装收尾均在已选择的运行配置下执行`python -m app.scripts.lake_schema --profile <storage.json> --apply`。会先读结构，核48旧列、已有新增列、默认值、键、TTL和约束；只在匹配时注册/执行005并读回账本。旧001–004由当前48列基线核验后登记，不重放历史TTL。中途失败保留已完成的增量，下次复验后续做；不删除表或改写旧行。
4. 让API/实际湖清理进程加载同一文件：`AISOC_LAKE_STORAGE_POLICY_FILE=<storage.json>`。`compose.override.yml`为已有`api`服务提供挂载示例，主机路径从选定compose配置的`LAKE_STORAGE_PROFILE`读取；其他服务名按实际清单挂载同一文件。该层不启用清理worker、消费者或自动告警。
5. 验证005、62列及条件TTL后，核实际worker配置及同一profile下COUNT/DELETE条件。此后才进入3c/3d接入发布。旧进程未更新时不得启动新映射写入，否则旧清理代码可能提前删除历史回放日志。

迁移关闭`materialize_ttl_after_modify`，不主动重算旧分片，不MATERIALIZE列/索引。TTL后台合并仍正常执行；本次不承诺立即物理删除。未配置profile的湖清理失败并记录错误，不会默用旧事件时间删除条件；其他数据类保留既有处理。发布前须核对所有实际运行湖清理进程，不能只挂载一个服务便认定同步完成。
