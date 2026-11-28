# 原型与核心证据纳管边界

本次为源码独审。没有执行 Git 写操作、构建、测试、部署、业务查询或模型调用；未改原型或生产代码，未读取/转述录制文件正文与运行配置值。

## 4173 整组保留本机

按统筹本轮明确范围，`prototypes/security-pages-v2/` 全部当前增量留在本机，不做部分提交。完整生产交付使用 SpiritHub web/API 与 socai2 HTTP/core/Fusion，不把 4173 录制页面并入生产包。

[路径分类与源码指纹](path-classification-manifest.json) 区分了通用 JS/CSS/test/package、带演示接线的 app/HTML、混合场景生成器，以及实际录制/配置文件。对后两种数据材料不输出文件内容或数据指纹。

原型源码引用检查发现：

- `index.html:47` 无条件引用 `socai2-recorded-preview4173-21-20261118-01.js`，`:55` 引用 `case-judgment-data.js`；后者包含固定场景及基于录制来源的演示生成逻辑，不属于通用适配器。
- `tests/functional-flow.test.cjs:7` 会按 HTML 中的 script 顺序直接读取文件。只排除录制文件却提交当前 HTML，会造成干净检出缺文件。
- `app.js:30` 与重置分支对 `judgmentCaseData` 使用可选调用；`platform-preview.js:28` 只在打开对应嵌入页时读取 `platform-preview.json`，失败进入已有空态。不是必须提交私密配置才能运行所有页面。
- 最小设计建议原本是将私密录制/演示 script 留在私密预览入口；统筹已选择整组保留本机，因此本轮不实施该调整，不新造演示数据。

本仓库 `services/`、生产 Dockerfile/启动入口，以及统筹指定的 SpiritHub 最终集成目录内 `backend/src`、`web/src`、两个 Dockerfile 和 Compose，未发现对此原型目录或本批私密文件的引用。三个 `deploy/local-investigation/*release-fragment.json` 中的 `page_delivery.preview4173.source_root` 是历史页面交付元数据，不是生产运行依赖。本次不删除历史文件或改写旧证据。

## 核心证据明确白名单

[evidence-allowlist.txt](evidence-allowlist.txt) 每行一个可纳管证据路径；[分类清单](path-classification-manifest.json) 给出类别和对应源码指纹。范围仅为本轮核心交接直接链接及其明确关联的源码/补丁、离线工程检查、纯源码独审、参数化脚本和 Schema，没有扩大到全部历史目录。

可纳管 Schema 中的 `content_json`、`headers` 等是字段定义，不是实际请求/响应正文。脚本只核源码，未运行脚本读取其指向的数据。白名单不授权执行，也不表示所有运行验收已通过。

混有 `actual_saved_artifact_review`、`saved_result`、运行加载/部署信息等字段的报告，没有仅凭 `review.json` 名称纳入此源码白名单。它们保持原处，由统筹对照已有脱敏及公开范围判断；本执行模块未再次转述这些值。其他 README、运行 env/profile、原答、HTTP body、请求或数据库快照亦不按目录整体纳管。

本清单的“保留/待责任人核实”不等于删除、不否认旧验收，也不替代统筹已取得的具体脱敏授权。最终提交仍以精确白名单和最终文件后像为准。

## 发布手册 §12 源码核对

核对对象为 `docs/operations/investigation-manual-deployment-21-20261127.md` §12；父源码使用统筹指定的 `/Users/lychee/Documents/project/SpiritHub-main-integration-20261128`，没有用旧 canonical 目录代替最终集成目录。

确认了父/子 main 与 gitlink 冻结要求、两个 npm 锁目录及本地生成入口、api/web Compose 服务名、HTTP 完整包与 processing 包的区别、dispatcher 必须覆盖单次 job entrypoint、Fusion 主进程/独立交付 worker、4177 打包入口、已有库增量和 LiteLLM 复用。检查仅针对源码/命令结构，没有构建或在线验证。

初审留一项接线问题：手册要求最大响应字节可配置，但所审父 Compose 的 api 未通过 `environment` 或 `env_file` 接入 `SPIRITHUB_SOC_HTTP_MAX_RESPONSE_BYTES`。仅向 Compose `--env-file` 写入该字段不会自动注入容器。已交统筹处理；独立回执保留所审版本的指纹，修正后的结论另行记录。

最终单点复核：指定集成目录的 Compose 已向 API 透传该字段，`.env.example` 有唯一对应声明，两处默认值均与后端 Settings 定义一致。该源码接线缺口已关闭，见[最终回执](section12-source-review-final.json)；[初审原件](section12-source-review-initial.json) 保持不变。本次仅核该字段，未新增测试、运行读取或部署，也不替代父 Schema 的另行独审。
