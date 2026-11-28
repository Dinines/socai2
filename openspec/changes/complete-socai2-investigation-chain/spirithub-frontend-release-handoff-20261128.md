# SpiritHub 四模块源码整合与发布交接

2026-11-28。实际 8181 源树为 `/Users/lychee/Projects/SpiritHub-web-8181`，分支 `codex/spirithub-4173`，HEAD `8051df5008af9e711a2c71890ad9bf111ff82301`。该 HEAD 与本地缓存的同名远端引用一致，分支未设置 upstream。共同基线为 `bb368df8cbebba85516a6fd2a47cc74e4afd75b9`。以标准父项目缓存的 `origin/main` `83a4f5ef3fd893aa7f49f6c71c852cce7428b818` 为本次三方比较目标，主线在基线上已有 143 笔提交。8181 为浅克隆和稀疏检出，生产包从统筹整合后的完整树制作。[当前逐文件清单](spirithub-frontend-release-sources-20261128.json)

## 精确收录范围

45 个路径来自已提交的 `8051df5`，41 个已跟踪文件有工作区差异，36 个为新文件，已提交与工作区重叠 12 个。索引与 HEAD 相同。合计 110 个路径，内含 19 个测试或测试支撑文件、1 份配置示例及 1 份生成的 live 类型。清单逐项记录提交和工作区状态、Git 模式及 blob、当前 SHA-256、main 重叠和删除。对 main 有 49 个新增路径、10 个仅候选修改路径以及 51 个两边均变的路径。

| 归属 | 路径数 | 收录范围 |
| --- | ---: | --- |
| 告警 | 22 | 告警列表和详情、固定分诊入口、相似历史、原件与响应读回，保留旧链接兼容。 |
| 安全事件 | 13 | 列表、预览、详情、已发布诊断、成员与资产、关系、来源和样式。 |
| Case | 39 | 队列和选择器、详情框架、资料与采用来源、故事、调查概览和历史、G1 图、正式分配接口、对应测试。 |
| 调查执行 | 8 | 通用运行目录、运行视图、告警分诊读取、轮次身份和状态展示、对应测试。 |
| 共享前端 | 19 | 路由、记录抽屉、主体命令、筛选和列管理、共享图、API 类型。 |
| 平台中转及合同 | 9 | Python 接线、Settings、桥接与公开 OpenAPI、配置示例、桥接测试。 |

与原 107 路径快照相比，新增 `CaseInvestigationOverview.tsx`、`CaseInvestigationOverview.test.tsx`、`case-fixtures.test-support.ts`，另有 11 个原路径的后像更新。当前清单收录最新后像。测试支撑文件的引用均来自测试。候选生产源的相关静态 import 在 8181 完整源树上均可解析。对候选路径检查了常见嵌入式凭据字面量、本机与原型工件引用以及生产源直接导入测试替身，均无命中。正式构建强制 live 模式，应用的 mock 启动由开发模式门控。原型录入、业务样本、浏览器 profile、私密回执、`dist`、依赖目录均在清单之外。[原盘点及页面逐项核对](spirithub-frontend-precommit-audit-20261128.md) · [构建模式](/Users/lychee/Projects/SpiritHub-web-8181/web/src/app/config/apiMode.ts:5) · [应用启动](/Users/lychee/Projects/SpiritHub-web-8181/web/src/main.tsx:10)

## 4173 迁移与功能边界

| 模块 | 实际源码与当前边界 |
| --- | --- |
| 告警 | 列表、概览、材料、活动与响应读保存记录。固定分诊核 run、step、artifact 和主体身份。相似历史、人工操作及 E01/E08 分配使用正式入口。概览同主机告警 E71 未接平台和页面，完整历史材料目录和响应的旧 Q08 读取仍有缺口。 |
| 事件 | 队列、预览、成员和来源汇总、关系图及保存诊断已接实际合同。E57 已同时登记在平台桥接及公开合同。部分筛选及字段仍有合同缺口，正式重新诊断入口、事件模型正文精简各按原计划后续推进。 |
| Case | 4173 对应的案内十个入口在详情框架可达。队列与 E01/E08 分配、Q36 资料及采用原件、Q13/Q33 故事、Q30/Q31 概览、Q34/Q35 历史及 G1 已保存关系图各有真实接线。成员、对象证据、人工任务、活动、评论附件使用既有读取或操作。下阶段包括对象证据 Q12 和旧 Q08 的缺口、G2/G3 探索保存、E45 严重度原因、E63 采用预览及 review token。助手定向问答、附件字节联调、新响应执行仍按原边界。 |
| 执行 | Q32 通用目录和固定 Run 五视图进入真实发现、执行过程、查询证据、关系图、报告与响应。固定 Case 轮次沿 Q34/Q35、E12/E14 定位。目录停止原因、部分原件来源或目录空态，以及未挂载的探索跳转仍需按原审计处理。 |

共享 `AlertObjectGraph.tsx` 和 `RelationGraph.tsx` 均在范围内。保留共享默认调用，成员工作区属可选接线，实际页待启用后仍需核三栏布局。4173 的 17 组／88 项为逐页对照范围，上表说明当前实现与证据边界。完整布局、所有操作及数据足量的组合验收仍未覆盖。[4173 逐页清单](investigation-page-migration-checklist-20261126.md) · [共享图与业务真实性核对](spirithub-frontend-precommit-audit-20261128.md#纳入本轮的两处共享图形扩展)

正式 Case `check/rerun` 通过异步 POST 受理。平台两份合同一致保留 E01 201、E08 200 的 `Socai2CaseAllocationReceipt`，以及新 POST 202 的 `Socai2AnalysisTaskReceipt`。普通 8181 已采集过一次由原生入口受理的新任务三页只读证据并交统筹核对。平台新 POST 的部署与通过普通 UI 的真实写入仍待，当前冻结 HTTP 的固定轮 lookup 缺注册也应在统一 HTTP 发布中补齐。[Case 概览接线](case-multirun-frontend-handoff-20261127.md) · [限定批次统筹审查](../../../docs/operations/evidence/previous-normalization-release-coordinator-20261128-01/review.json)

## main 整合要点

1. 保留 `83a4f5e` 的非 SOC 路由和导出。候选整份 `web/src/app/router.tsx` 仍引用旧 `ScanRunsPage`，该依赖在目的主线已不存在。沿主线路由合入四模块登记。对旧 `web/src/features/soc-alerts/AlertWorkbenchDetail.tsx` 的删除，先核主线剩余调用及旧链接再整合。
2. 将候选的 SOC 路由与组件合入 `schemas/platform-api.v1.json` 和 `backend/src/spirithub/soc/bridge_contract.json`。候选公开合同变更 19 个 SOC 方法，其中 15 个与 main 同方法异改。main 的 17 个非 SOC 方法增量均需保留，包含新扫描/PDF API。桥接合同并行异改 20 个方法，另有一个方法已等同。逐方法合并 Schema、状态及错误，核平台路由登记、桥接 allowlist、原生合同，然后再生成 Web 类型。
3. 保留候选 `backend/src/spirithub/config.py` 和 `.env.example` 的 SOC 增量。当前 main Settings 缺 `soc_http_trusted_reads`、`soc_http_trusted_origin`、`soc_http_execution_timeout_seconds`，候选 `SocBridge` 初始化直接访问这些字段。两个基线继承的运行依赖在清单另列。由 `docker-compose.yml` 合入 `api.environment` 的 `SPIRITHUB_SOC_HTTP_EXECUTION_TIMEOUT_SECONDS`，由 `deploy/nginx/default.conf` 合入 SOC 长执行 location，对应旧 Run start、Case AI messages、告警 analyze 和事件 diagnose。短请求继续使用现有通用代理，新 Case POST 保持快速回 202。保留当前主线的其他 Compose 设置、Nginx location 和 Dockerfile。
4. `server` gitlink 由统筹在 socai2 的完整变更进入目标远端 main 后更新到该提交。前端源树原 gitlink 为 `09010dc`，目标 main 当前为 `39917f9`。源清单以浏览器、中转、合同为边界。[当前三方合同和依赖指纹](spirithub-frontend-release-sources-20261128.json)

## 可复用检查

| 已有检查 | 对当前后像的复用范围 |
| --- | --- |
| 21 已发布告警构建 | 原冻结 37 路径中当前 30 个匹配。旧镜像及静态入口 SHA 可作发布方式和已发布告警切片证据。 |
| 相似历史及事件 | 相似历史最终候选 2/4。已发布诊断 2/9，图选择 1/2。保留各自已核切片，不整体追认后续组合。 |
| Case 队列、故事、固定轮 | 队列与通用目录 9/14，故事 5/7，历史 5/7。G1 为 7/8，资料采用来源读回 8/8。 |
| E01/E08 分配 | 两个已挂载源码后像均匹配。旧组合三个依赖仅一个匹配，旧 live 类型已变。组件测试及原类型检查按原覆盖保留。 |
| Case 概览 | 已审补丁六个挂载文件与五个组合依赖全部匹配。复用已记录的直接用例、Q36 终态刷新和组合类型检查。 |

本次盘点复核源码、文件指纹、合同、配置及静态导入，沿用既有测试。合入 main 产生新组合后，按受影响入口运行现有检查。先生成类型和检查 TS 项目，再选对应的桥接、告警固定轮、事件、Case 及默认共享图用例。合并树通过离线构建后，以直接读取和原先获准的业务路径验收实际运行版本。[当前匹配明细](spirithub-frontend-release-sources-20261128.json) · [原告警构建](../../../docs/operations/evidence/alert-git-21-release-20261125-01/frontend-build.json) · [Case 分配挂载](/Users/lychee/Documents/project/socai2/.local/validation/spirithub-case-association-20261128-01/8181-mounted-typecheck.json) · [Case 概览挂载](/Users/lychee/Documents/project/socai2/.local/validation/spirithub-case-overview-20261128-02/8181-mounted.json)

## 构建、部署和回退

以下命令对应新的整合产物。Node 24、npm 11、锁文件及所需依赖在离线制品准备环境备齐。Web 生产构建输出 `web/dist`，包括入口、版本化 CSS/JS、字体及许可。普通 8181 当前使用 Vite，源目录无本轮生产 `dist/index.html`。以发布记录中已验证方式封装 Nginx 镜像，或从完整整合树使用 `web/Dockerfile` 构建。主线 Dockerfile 保留现有构建输入，含非 SOC 测试夹具引用。候选本轮合并后的镜像、摘要与端到端结果待生成。[Web 构建入口](/Users/lychee/Projects/SpiritHub-web-8181/web/package.json) · [SpiritHub 离线交付约定](/Users/lychee/Projects/SpiritHub-web-8181/docs/离线交付目录.md) · [原 Web 镜像发布回执](../../../docs/operations/evidence/alert-git-21-release-20261125-01/frontend-web-release.json)

```sh
npm ci --prefix web/tools/openapi
npm ci --prefix web
npm run api:generate --prefix web
npm run typecheck --prefix web
VITE_API_MODE=live npm run build --prefix web
```

`api:generate` 同时生成 live 和 mock 类型。核对 mock 类型与主线的 mock Schema 一致。主线旧的 21 Web 发布记录采用已构建 `dist` 与 Nginx 配置，加已锁定的运行基镜像，用 `web/offline.Dockerfile` 封装最终静态服务。独立发布 Web 与平台 API 时分别锁定 `spirithub-web:<release>` 和 `spirithub-backend:<release>` 的镜像 ID、归档 SHA 和配置。离线加载镜像后，沿已运行的 Compose project、env、网络、挂载及端口使用逐服务 image override。

| 服务 | 产物、配置和上线验证 |
| --- | --- |
| socai2 调查执行与相关处理服务 | 以本轮确认的核心清单冻结处理包，通过 `python3 deploy/aisoc21/prepare_processing_release.py --profile <profile>`、`python3 deploy/aisoc21/build_processing_image.py --release-directory <已安装包目录>` 生成固定依赖、禁网构建的镜像。处理 profile 显式指定租户、DB/Redis 文件与 TLS、lifecycle、`executor_config_file`、模型/内网工具和日志 profile。Fusion 与监听器如纳入对应批次，沿其独立配置和原放行边界。核没有在途任务后切换唯一批准的进程，读回实际镜像、源码、profile 和保存记录。 [核心依赖](core-production-commit-dependencies-20261128.md) · [处理发布入口](../../../deploy/aisoc21/README.md) · [配置示例](../../../deploy/local-investigation/analysis-dispatch.example.json) |
| socai2 对外调查 HTTP | 使用 `python3 deploy/http-service/manage.py --profile <profile> package --output <新目录>` 冻结完整 `app`/`investigation_http`。运行侧沿同包 `manage.py --profile profile.json prepare/build/start/verify` 对应动作。显式配 release、image、base image、bind/port、database、`runtime_environment_file`、只读策略/挂载和日志目录。以实际 OpenAPI、readiness、Q34/Q35、Q36、E01/E08 和 202 契约及相应保存路径核对。 [HTTP 部署步骤](../../../deploy/http-service/README.md) · [配置字典](../../../deploy/http-service/CONFIGURATION.md) |
| SpiritHub Python 平台 API | 完整父项目树用 `docker compose build api`，对应 `backend/Dockerfile`、Python 3.13 与 `uv.lock`。发布前固定 `SPIRITHUB_SOC_HTTP_BASE_URL`、`SPIRITHUB_SOC_HTTP_CREDENTIALS_FILE` 和只读 secret 挂载、租户、超时及响应上限。可信读取/来源取环境已批准配置，默认关闭。保持现网 `SPIRITHUB_PUBLIC_ORIGIN`、Cookie、数据库和附件配置。切换 `api` 后核镜像、readiness、实际路由、同源经中转的身份和真实 HTTP 状态。 |
| SpiritHub Web | 交付校验过的静态镜像。开发 8181 的 `VITE_API_MODE`、`SPIRITHUB_API_PROXY_TARGET`、`SPIRITHUB_PUBLIC_ORIGIN` 取原本机 profile。生产使用同源 Nginx 的 `/api/v1/socai2/` 中转到 Python API，并保留 SPA fallback。API 可用后切 Web，查首页与深链接、入口/资源/字体和四模块直接读取。 |
| 4177／Swagger | 属独立测试查阅和交接服务。若本批纳入 4177，用 `python3 deploy/investigation-test/build.py build --profile <新包配置>` 生成版本目录、tar.gz 和回执，再按该服务的运行配置与只读账本安装。Swagger 按同期已核调查 HTTP 合同更新。 [4177 构建与部署](../../../deploy/investigation-test/README.md) · [Swagger](../../../deploy/api-docs/README.md) |

发布顺序由统筹依据本批 profile 核数据库增量和依赖，先让原生调查 HTTP 与执行端合同配套，再切平台 API，最后切 Web。API/Web 在已核 Compose 配置上分别使用 `up -d --no-deps --no-build --pull never api` 或 `web`，每次核实际加载和旧服务影响。现网单服务切换和回退均用各自已保存的旧镜像 ID、Compose override 和原受控配置。若新数据格式与旧版兼容，可先回 Web，再按需回平台 API 或后端。若已经写入旧版无法读取的新记录，停止新任务，保留兼容读侧和数据，修当前版本后继续。调查调度保持唯一运行实例，历史数据、原回执、迁移和队列无需清理来实现回退。[21 回退边界](../../../deploy/aisoc21/README.md#回退边界) · [已验证的 Web 切换命令及回退配置](../../../docs/operations/evidence/alert-git-21-release-20261125-01/frontend-web-release.json)
