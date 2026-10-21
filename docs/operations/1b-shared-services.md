# 1B：21共享PG/Redis实际回执

2026-10-20，批次`1b-20261020`。用户确认可复用21公开数据服务、允许适当重启。本批完成基础设施层验收，业务服务尚未导入或部署。结构化原值见[证据JSON](1b-shared-services.json)，下一批见[依赖计划](dependency-migration-plan.md)。

## 来源与实际资源

固定参考`34ca18c57dd4175539e5c6dd3d04a72dc057306b`，从指定只读目录复制137个原件：134份完整文件名SQL、2个init脚本、LICENSE；原件hash/权限见[导入清单](../handoff/1b-import-manifest.json)。没有导入API业务实现，没有构建业务镜像。

| 项目 | 实际结果 |
| --- | --- |
| PostgreSQL | 复用`spirithub-postgres-1`，16.15，经21:5432访问；新库`aisoc` |
| 数据库角色 | `aisoc` owner、`aisoc_app` runtime，独立密码；均无superuser/BYPASSRLS/CREATEDB/CREATEROLE |
| SQL | 134/134成功，按完整文件名排序；ledger完整集合一致，不按数字前缀去重 |
| Redis | 复用`sting-infra21-redis-1`，7.4.11，经21:6379；新ACL账号`socai2` |
| Redis逻辑分配 | API8、Fusion9、Agents10、Actions11、TI12；配置输入尚未接业务进程 |
| 项目目录 | 21 `/opt/sting-aisoc-socai2`，含source、generated、private和evidence |
| 容器与卷 | 没有新增服务/卷；仅重建现有Redis容器，镜像与挂载保持 |

## 输入 → 实际调用 → 最终结果

| 验收 | 输入及实际过程 | 最终值/关系 |
| --- | --- | --- |
| 迁移完整性 | 核134文件hash → 逐文件psql严格执行 → 对比`aisoc_schema_migrations`与完整文件名集合 | 134成功/134 ledger项；原SQL未修改。061仅集群角色属性块由基础设施管理员执行，其余schema/default grants归新owner |
| 角色登录/持久提交 | owner/runtime经21:5432真实TCP登录；写入2个标记tenant/alert → runtime更新A → 新TCP会话读取 | 身份分别`aisoc\|aisoc`、`aisoc_app\|aisoc`；两行及A更新值可回读，synchronous_commit=on，记录WAL flush LSN |
| tenant边界 | 绑定tenant A/B分别查询两条告警；A尝试向B插入；runtime尝试public DDL | A只见A、B只见B；跨tenant写报RLS policy错误；DDL报schema权限拒绝 |
| 未绑定会话 | runtime不绑定tenant，读取同两条测试告警 | 实际可见2条；保留原worker语义，不能宣称外部租户隔离已通过 |
| Redis身份/写读 | 专用账号在DB8写批次key → WAITAOF → 新连接GET | WHOAMI=socai2；本地AOF fsync确认1；回读原值 |
| Redis危险命令边界 | 管理员ACL DRYRUN检验FLUSHALL/FLUSHDB/CONFIG/SHUTDOWN | 四项均拒绝；没有执行清库/关闭等真实危险命令 |
| 密码输出保护 | 非敏感哨兵运行原脚本 → 补丁 → 原脚本负对照 → 补丁读取实际新凭据 | 原版输出哨兵、补丁不输出、负对照再次输出；实际凭据不出现在补丁输出。原件保留，[生成副本差异](../../deploy/aisoc21/postgres-init-patch.json)单独记录 |
| Redis重启恢复 | 保存全部ACL及Compose → 增加aclfile → 仅`up -d --no-deps --pull never redis` → 新连接认证/读取重启key | default/socai2及全部ACL规则和密码hash保持；项目账号无需恢复命令即可登录；重启前key原值恢复，镜像和卷不变 |
| 清理与影响 | 仅删两条测试告警、两个测试tenant和本批唯一Redis key；对比前后容器元数据 | 测试对象清理；仍为30容器/18卷，其余29容器ID、状态、启动时间、重启次数不变 |

tenant A=`54d95191-37b2-59cc-b0bd-8e4579913742` → alert A=`9a7f7fb2-2c33-5afb-941e-18e782aa12ab`；tenant B=`05ef6dc3-aa51-509f-8623-eb0f17240649` → alert B=`987f887d-db51-5492-9059-4f82ce049efa`。Redis重启key=`socai2:1b:restart-20261020`，实际重启后值=`socai2-1b-restart-persistence`，已仅清理该key。

## 运行与恢复边界

执行器、生成补丁和受控重启操作见[21操作说明](../../deploy/aisoc21/README.md)。新凭据只在21 `private/`及本机Git忽略的`.local/aisoc21/private/`，目录0700/文件0600；不覆盖旧配置快照。

Redis现有Compose只增加`--aclfile /data/socai2-users.acl`，保留requirepass及AOF。原Compose和全部ACL备份在21 `private/redis-restart-before/`，含受控密码hash，不能公开。后续ACL变更须`ACL SAVE`。初始独立Compose草稿已停用，保留本地忽略目录，未部署。

PG未重启，本批只证明WAL提交和新TCP连接回读。Redis DB8—12为逻辑分配，ACL不能限制用户仅SELECT特定数据库；应用账号只供受控服务，API身份/tenant绑定待1F。其他项目只核容器元数据，未执行其业务交易。当前结果不证明API、Kafka、Fusion、模型或完整告警链可用。

失败恢复保留本项目库、ledger与现场；不对共享实例执行`down -v`、清库、旧业务反向SQL。若恢复Redis旧Compose，仍需保留ACL文件加载，避免项目账号丢失。下一单项：1C复用21 Kafka，验证版本/listener、项目topic/group和消息坐标。
