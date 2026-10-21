# 1A：依赖参考快照与环境盘点回执

日期：2026-10-20。本页记录已执行的1A依赖参考盘点，不作为当前任务表；阶段目标见[服务端路线](service-roadmap.md)，后续批次见[依赖计划](dependency-migration-plan.md)。本页结果没有改变业务行为。

后续职责已明确为[告警及后续处理服务端](alert-processing-scope.md)，无前端交付；以下90文件/13服务数据保留为当时依赖参考快照的实测结果，不代表这些组件全部纳入当前部署范围。

## 本批范围与验收

- 检查 main、未提交文件和远端；保留全部交接内容，不提交或推送。
- 只读核对20的源码、镜像、overlay及21的容器、端口、Compose项目和卷；不重启或重配现有服务。
- 以本地只读参考 `/Users/lychee/Documents/project/SOCAI/opensource/AiSOC` 为复制来源，保持固定 revision `34ca18c57dd4175539e5c6dd3d04a72dc057306b`；只复制依赖声明、锁、构建配方及其最小辅助脚本。
- 依赖快照单独放在 `deploy/aisoc21/dependencies/source/`，保留许可及来源。原有 README、AGENTS、`.env.example` 和私有配置不被上游版本替代。
- 验收：每个依赖文件与本地参考及固定 Git blob 一致，可执行权限一致；依赖可静态解析、上游导出脚本可运行；20源码/镜像/补丁对应关系和21资源归属可查。
- 列出下一批底座迁移及最小验收。本批不代表依赖安装、可复现构建、21部署、模型质量或业务验收通过。

## 执行结果

- Git：main，无提交；origin/upstream配置正确。本批没有提交、推送或变更参考源码。
- 依赖：迁入90个原件，逐一核对本地来源、固定Git blob、SHA-256和执行权限通过；未被Git忽略。包括13份服务Poetry锁、3份Go校验文件、2份npm锁及根pnpm锁。详见[依赖清单](../handoff/dependency-manifest.json)。
- 导出：13个Python服务分别导出main/all两个精确版本清单；上游 `service_requirements.py --self-test` 的26项通过。没有安装包或发起包仓库下载。
- Compose：在21执行只读 `config` 静态解析通过；首次 `--no-interpolate` 因未展开的 `pull_policy` 被Compose拒绝，改用空env文件和默认插值后通过，源码未改。未验证应用文件是否齐全或运行时依赖。
- 20：16容器；AiSOC官方应用镜像revision均匹配固定版本；基础Compose、LiteLLM配置文件与参考源码一致，overlay与交接副本一致；实际模型路由仍由运行env/overlay决定。不能据此认定本地源码已构建。
- 21：30容器（22运行、8退出）、18卷；与关闭回执相比，所有容器ID、状态、启动时间、重启次数一致。旧4个业务容器仍停止，已有项目、卷和端口均未修改。
- 过程调整：最初完整导入的13,635个文件，在用户明确“逐步迁移、先依赖”后全部核对本轮hash并移至Git忽略的 `.local/initialization/full-source-staging/`，没有删除文件；原忽略规则已按hash恢复。这份临时副本不作为迁移完成证据，后续复制仍从用户指定的只读参考取文件。

证据：[20盘点](initialization-host20.json)、[21盘点](initialization-host21.json)、[依赖/Compose核对](dependency-inventory.json)、[静态验证回执](initialization-verification.json)。当时下一批拟独立部署PG/Redis；用户后续确认复用21公开服务并允许适当重启，实际1B已完成，见[共享服务回执](1b-shared-services.md)。当前下一项以[PROGRESS](../../PROGRESS.md)及[依赖计划](dependency-migration-plan.md)为准。
