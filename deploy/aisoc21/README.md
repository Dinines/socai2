# 21 调查服务部署

当前发布为 `v1.2-20261110-r2`，运行入口为 `/opt/sting-aisoc-socai2/current-v1.2`。A/I 及 Case C1/C3/Deep/C6 策略已实际加载，API、Fusion、Agents、projection、工作台及 gateway 六项服务健康。Case/H GET 可用，Case HTTP 写入口关闭，Agents 消费暂停。

## 发布来源

- [统一发布清单](release-v1.2.json)：完整镜像 ID、实际 Compose 来源、挂载和显式策略检查。
- [传输配置](current-rollout.json)：SSH 目标、独立发布目录、超时、包边界及证据位置。
- [处理构建配置](processing-build-case-v1.toml)、[生产 profile](production-v1.2.toml)、[处理策略](../local-investigation/investigation-policy-case-v1.toml)：构建与运行均不回落其他环境。
- [本批发布和读取结果](../../openspec/changes/complete-socai2-investigation-chain/release-current-20261110.md)：修复、测试与完成边界。

源码冻结包含当前工作区内容，通过逐文件 hash 核镜像及运行挂载。发布目录不可覆盖；后续发布填写独立标识并核现场镜像和有效 Compose。构建使用已缓存的固定基础镜像，关闭网络拉取。

## 执行顺序

1. `prepare_processing_release.py --profile <构建配置>` 冻结处理包；使用 `rollout_transport.py --config <传输配置> processing upload/build` 上传及构建。
2. 将构建回执中的镜像 ID、标签、manifest hash 写入统一清单和生产 profile。
3. `release_12.py freeze --config <发布清单> --directory <独立冻结目录>`；通过传输入口执行 `unified upload`、`build`、`preflight`、`prepare`。
4. 按清单只对变化服务执行 `unified rollout --project <项目键> --service <服务键>`。本批只重建 API 和工作台，按需处理入口随发布选择固定镜像。
5. 服务健康后执行 `unified activate`、`verify`，核实际策略、源码、读取权限、当前指针。继承的服务保持容器身份。

`prepare` 会保存有效 Compose、配置和入口的回退快照到受控 private 目录；不得输出其内容。回退用对应冻结目录的 `release_12.py rollback --directory <目录>`，随后重新核验服务。发布不执行 DDL、不重置消费位点、不重派调查。

在 21 只读核验：

```sh
python3 /opt/sting-aisoc-socai2/current-v1.2/deploy/aisoc21/release_12.py verify --directory /opt/sting-aisoc-socai2/current-v1.2
python3 /opt/sting-aisoc-socai2/ops/processing-production.py check
```

## 数据库与读取权限

正式库为 `aisoc.socai2`，29 表、462 列。API 的 `AISOC_STARTUP_SCHEMA_MIGRATIONS=false`；既有数据保持。

已批准的 API 只读授权由 [install_reader.py](../database/install_reader.py) 和 [API reader profile](../database/api-reader-21.toml)管理。新装和升级按同一授权脚本安装；日常发布仅 `verify`。共享库结构与处理角色使用 [install_aisoc21_v1.py](../database/install_aisoc21_v1.py) 的 `verify`，它接受已批准的 API 只读授权并拒绝调查写权限。

凭据存于 21 `/opt/sting-aisoc-socai2/private/`，发布源码及 Git 不含秘密。只读、入站和处理身份按[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)使用。

## 工作台与测试

4177 只绑定回环，沿 [Mac SSH 接入说明](../../docs/operations/mac-ssh-relay-20261107.md)访问。当前 Case 保存记录从正式库读取；已验证的隔离 Case 快照通过 [静态发布配置](workbench-current.json)追加，保留其他记录及原答。静态发布不会启动调查或重启容器。

真实 GET 与数据库对照使用 [verify_current_release.py](../../docs/operations/verify_current_release.py)及独立批次配置。每次指定新输出目录，读取父主体、材料、工件、活动与同租户相关告警；凭据仅从私密文件加载。没有新增真实模型调用时，不报告模型质量或完整真实调查通过。
