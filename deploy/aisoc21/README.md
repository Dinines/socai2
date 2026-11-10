# 21 调查服务部署

主发布为 `v1.2-20261110-r6`，运行入口为 `/opt/sting-aisoc-socai2/current-v1.2`；处理组件为 `processing-20261110-r6`，4177 工作台独立组件保持 `workbench-20261110-r2`。A/I 及 Case C1/C3/Deep/C6 策略已实际加载，API、Fusion、Agents、projection、工作台及 gateway 六项服务健康。Case/H GET 可用，Case HTTP 写入口关闭，Agents 消费暂停。

## 发布来源

- [统一发布清单](release-v1.2.json)：完整镜像 ID、实际 Compose 来源、挂载和显式策略检查。
- [传输配置](current-rollout.json)：SSH 目标、独立发布目录、超时、包边界及证据位置。
- [处理构建配置](processing-build-case-v1.toml)、[生产 profile](production-v1.2.toml)、[处理策略](../local-investigation/investigation-policy-case-v1.toml)：构建与运行均不回落其他环境。
- [本批流程实测和发布](../../openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)：修复、测试与完成边界；[发布回执](../../docs/operations/evidence/case-evidence-roles-20261110-01/delivery-summary.json)记录实际来源及读回。
- [工作台组件配置](workbench-runtime-current.json)：4177 的实际源码挂载、Compose、固定镜像和独立发布回执；主服务和处理策略保持。

源码冻结包含当前工作区内容，通过逐文件 hash 核镜像及运行挂载。发布目录不可覆盖；后续发布填写独立标识并核现场镜像和有效 Compose。构建使用已缓存的固定基础镜像，关闭网络拉取。

## 执行顺序

1. `prepare_processing_release.py --profile <构建配置>` 冻结处理包；使用 `rollout_transport.py --config <传输配置> processing upload/build` 上传及构建。
2. 将构建回执中的镜像 ID、标签、manifest hash 写入统一清单和生产 profile。
3. `release_12.py freeze --config <发布清单> --directory <独立冻结目录>`；通过传输入口执行 `unified upload`、`build`、`preflight`、`prepare`。
4. 按清单只对变化服务执行 `unified rollout --project <项目键> --service <服务键>`。本批只重建 API，其余五项服务保持容器身份；按需处理入口随发布选择固定镜像。
5. 服务健康后执行 `unified activate`、`verify`，核实际策略、源码、读取权限、当前指针。继承的服务保持容器身份。

`prepare` 会保存有效 Compose、配置和入口的回退快照到受控 private 目录；不得输出其内容。回退用对应冻结目录的 `release_12.py rollback --directory <目录>`，随后重新核验服务。发布不执行 DDL、不重置消费位点、不重派调查。

在 21 只读核验：

```sh
python3 /opt/sting-aisoc-socai2/ops/processing-production.py check
```

## 数据库与读取权限

正式库为 `aisoc.socai2`，29 表、462 列。API 的 `AISOC_STARTUP_SCHEMA_MIGRATIONS=false`；既有数据保持。

已批准的 API 只读授权由 [install_reader.py](../database/install_reader.py) 和 [API reader profile](../database/api-reader-21.toml)管理。新装和升级按同一授权脚本安装；日常发布仅 `verify`。共享库结构与处理角色使用 [install_aisoc21_v1.py](../database/install_aisoc21_v1.py) 的 `verify`，它接受已批准的 API 只读授权并拒绝调查写权限。

凭据存于 21 `/opt/sting-aisoc-socai2/private/`，发布源码及 Git 不含秘密。只读、入站和处理身份按[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)使用。

## 工作台与测试

4177 只绑定回环，沿 [Mac SSH 接入说明](../../docs/operations/mac-ssh-relay-20261107.md)访问。当前 Case 保存记录从正式库读取；本批一轮真实本地模型与两类 PG 替身流程共 3 份资料通过 [静态发布配置](workbench-current.json)追加，服务端合计 29 份，保留其他记录及原答。233 文件／234 HTTP 核验通过；静态发布没有启动调查或重启容器。

节点详情使用 `workbench-20261110-r2` 的源码：左侧流程、右侧提示词／输入／输出／失败原因；缓存按展示源码指纹刷新。组件保留主发布的固定镜像、环境、命令及数据挂载，只重建工作台容器。当前现场核验从本机执行：

```sh
python deploy/aisoc21/publish_workbench_runtime.py --config deploy/aisoc21/workbench-runtime-current.json --verify
```

后续仅更新工作台时，准备独立组件配置及证据目录，再使用同一入口的 `--publish`；先检查当前挂载和 Compose，按清单继承基础源码并替换所列展示文件。有效配置与回退 Compose 只保存在配置指定的 21 private 目录。统一主发布核验包含工作台挂载，后续整批发布需纳入本组件的实际挂载和 Compose，不再直接套用前批的工作台来源。

真实 GET 与数据库对照使用 [verify_current_release.py](../../docs/operations/verify_current_release.py)及独立批次配置。每次指定新输出目录，读取父主体、材料、工件、活动与同租户相关告警；凭据仅从私密文件加载。没有新增真实模型调用时，不报告模型质量或完整真实调查通过。

本批 86 项相关检查、两项真实 PostgreSQL 完整流程通过；一轮真实模型共 4 次调用、38,844 reported tokens，6 条 observed 支持角色及成员合规，实际 completed/partial、C6 采用，模型整体质量仍 NOT_PASSED。52 次本地 GET／3,225 字段检查及发布后 365 次生产 GET／16,820 字段关联检查通过。模型与工具替身、真实模型和生产读取分开计数，费用未知；后续问题见[问题清单](../../docs/investigation/current-issues.md)。

H 验收入口 [production_human_probe.py](../../docs/operations/production_human_probe.py)使用生产 profile 和既有 `HumanTaskService.write`，凭据由私密文件加载；它只用于明确批次的服务层验收，不能替代产品 HTTP 写入和页面操作验收。
