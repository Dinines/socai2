# Investigation test records — W1–W5

独立测试账本和只读HTTP组件，当前包版本`0.6.1`，已部署到21的4177 r8。本包发布明确提供的测试记录、保存证据并读取；显式提供`serve --upstream-config`时启用单环境调查HTTP只读代理。不连接调查数据库、Redis、Kafka或模型，不执行、恢复或调度调查。

工作台任务1/2已发布：Case默认，事件/告警从业务HTTP直接发现；Case和事件按实际Run分轮，无账本也可查业务对象。每轮展示冻结A/I来源、沿用/新增、源Run步骤及原答；选入、保留单元和本案交集分别显示，来源失败不遮挡Case流程。静态资源使用no-store避免更新混用缓存模块。4b进一步支持报告直接打开指定Case/Run，并按该轮冻结告警来源显示紫色测试标识；新测试源默认以lyc开头，后台来源和tenant关联保留，控制标记不进入分析模型。实际4177的两轮1/2成员、刷新/重载及无效目标不回落latest均已验证，见[4b发布与限定独审](../../docs/operations/evidence/workbench-4b-release-20261117-01/README.md)。

任务3a–3d的[材料与Docker验收CLI](../../tools/testdata/ACCEPTANCE.md)已完成转换、检查、发送/等待、显式追加同一Case后轮和会话汇总。它是独立执行入口，不由只读服务启动或调用；[21两段完整流程](../../docs/operations/evidence/acceptance-fullflow-21-20261117-01/README.md)已实际验证。程序功能通过不代表模型正文质量通过；5项质量问题及D5/D6未完边界见当前进度和统一设计。

部署步骤、账本9项、代理10项及页面3项配置的类型/示例/必填/加载/验证、私密路径与4177后续边界统一见[测试服务部署与配置](../../deploy/investigation-test/README.md)。本页只维护使用与HTTP合同。

## 启动与发布

在仓库根目录，使用现有Python环境和显式配置：

```sh
PYTHONPATH=services .local/conda-envs/socai2/bin/python -m investigation_test serve \
  --config deploy/investigation-test/read-only.example.json
```

示例配置的端口为14178，目录相对配置文件解析。可先复制配置选择自己的账本目录和端口；全部参数必须显式提供。启动和GET不创建账本目录，也不会自动加载测试数据。临时验证使用明确的回环端口；W5的4177常驻入口由独立发布profile配置，实际状态见PROGRESS。启用viewer时，`/`及旧`/index.html`书签跳转到`/viewer/`。

发布是独立本地入口，没有HTTP写路由。例如将已保存的F5回执作为archive读取：

```sh
PYTHONPATH=services .local/conda-envs/socai2/bin/python -m investigation_test publish \
  --config deploy/investigation-test/read-only.example.json \
  --document docs/operations/evidence/test-ledger-w1-20261115-01/tcp-01/inputs/w1-f5-archive/document.json \
  --expected-revision 0
```

`0`表示新建；更新须提供当前revision。已结束批次不能修改，复验使用新batch。原文件只读复制，旧revision保留；未完成发布的目录不参与读取，不自动续跑。证据源仅接受document所在目录内的非隐藏相对普通文件，不能用绝对路径、上溯或符号链接；必须登记`visibility=public`，发布者负责提供可公开的非私密内容。

## HTTP合同

独立OpenAPI在`/openapi.json`。8个业务GET均以`/test-api/v1`为前缀，不混入调查业务Swagger：

| 路径 | 用途 |
| --- | --- |
| `/capabilities` | 服务/Schema版本、只读能力、环境标签及保存的准备观察时间；viewer_version仅在显式挂载页面时为实际版本，否则为空 |
| `/batches` | 按environment/status过滤、分页 |
| `/batches/{batch_id}` | 批次、revision、计数、证据元数据与读取链接 |
| `/batches/{batch_id}/cases` | 测试用例，按scenario_id/status过滤、分页；不是业务Case列表 |
| `/batches/{batch_id}/operations` | 操作与真实身份映射，按use_case_id过滤、分页；run_id可空，多Run保留数组 |
| `/batches/{batch_id}/preparation` | 准备及清理事实；不执行准备/清理 |
| `/batches/{batch_id}/quality-issues` | 按use_case_id/run_id过滤、分页；未评估质量与无问题分开 |
| `/batches/{batch_id}/evidence/{evidence_id}` | 默认元数据，`format=content`按原字节返回附件，核size/hash |

列表返回items/total/next_cursor/observed_at。cursor绑定路径、过滤条件、limit及修订；修订改变409 `cursor_stale`，未知记录404，非法参数422，账本或已登记证据不可读/损坏503。写方法无路由，405。错误不回显源文件路径或配置原件。

输入字段及约束见[models.py](models.py)和[W1设计](../../openspec/changes/schedule-streaming-investigation-updates/w1-test-ledger-design-20261115.md)。`live/archive`与`live_execution/saved_evidence/synthetic_fixture`是来源说明；live须另行显式配置上游代理并核真实身份，标签本身不证明当前上游可用。

## 验证及未完边界

[本步回执](../../docs/operations/evidence/test-ledger-w1-20261115-01/README.md)记录16项组件测试、真实回环TCP保存/读取/重启及原文件摘要。首版只验证单机本地文件存储，不宣称共享网络文件系统或跨主机发布支持。

W2代理组件及真实候选TCP空态/错误已通过[原回执](../../docs/operations/evidence/test-http-proxy-w2-20261115-01/README.md)；当时0.2.0同一源码进一步完成[真实非空/跨Run读取](../../docs/operations/evidence/test-http-proxy-w2-live-20261115-01/README.md)：9账本/24业务代理/1合同GET共34次、107检查通过，live映射保留真实S01两案与S04失败/3skip，Case C1经返回content_url读取原I输入，账本未变。原失败及前次隧道地址错误保留，临时服务/隧道已停止。没有同Case新轮或步骤直接reused跨Run样本，不计这些真实覆盖。

代理按照已冻结实际OpenAPI只转发55个业务GET；保留DTO、分页、错误、来源身份及原件流，业务前缀不计入测试8GET的OpenAPI。capabilities返回所选环境/tenant/合同摘要，不自动执行健康检查或创建业务映射。账本archive/live标签不自动把历史ID转成当前环境ID，读取通过不改变来源调查失败或质量结论。

W3同源页面已实现并通过本机临时服务→21候选真实浏览器读取，见[W3回执](../../docs/operations/evidence/test-viewer-w3-20261115-01/README.md)。W4包及W5实际4177结果见部署说明和对应回执。W5的0.4.1入口读取通过，随后0.5.1按负责人反馈恢复旧式执行流程；当前0.6.1进一步交付主体分类、冻结轮次、报告跳转和紫色来源标识。实际发布状态以PROGRESS为准。当前API没有网页启动测试、清理、模型执行或自动恢复入口，不以组件通过核销业务流程或模型质量问题。

## W3可选查阅页面

在上述serve命令加入`--viewer-config deploy/investigation-test/viewer.example.json`后访问`/viewer/`。页面和静态资源不进入8个测试GET的OpenAPI；不传viewer-config时不挂载页面。公开`/viewer/config.json`只给版本、轮询/超时和页大小。所有动态内容通过同源账本GET和已配置的只读代理取得；无需重新生成HTML。

默认按案例/事件选择执行轮次，沿旧4177的主线、组件分支和固定节点详情查看真实执行，紫色“测试执行”标识与红色错误分开。HTTP接入（已登记原件）或自动触发、真实任务/attempt、全部阶段及组件、保存结果和本次HTTP读回连成主线。右侧可读提示词、输入、输出、模型原答及完整记录；原答只接受实际raw choices，程序装配输出不冒充原答。Case历史完整分页，轮次切换重绑task/Run/Result。测试计划、发起记录、环境与材料、质量问题及核对记录保留在“测试管理”；live核批次/代理环境一致，archive只查登记记录。真实task→attempt→选中Run/结果保持身份，accepted无Run、skipped、failed/unknown、partial、采用、当前新鲜度及质量分别显示。用例导航按use_case_id取分页、再以具体TestCase.id筛Operation.case_id，避免同功能的多个用例混入。

当前可见活动记录按配置刷新；终态/隐藏停止，返回可见不自动刷新终态。展开目录/原件期间暂停父Run轮询，避免刷新覆盖正在阅读内容；手动刷新恢复主记录。失败保留上次观察并明确过期，不回落archive。步骤/工件用实际游标完整分页，正文沿返回链接按需完整读取；原JSON可展开/下载。C1来源保留原主体、原Run、输入摘要及原事件/本案交集范围；比较只展示已返回身份/链接。

真实验证复用已执行S01/S04，不新增模型/业务写；26业务GET、14账本GET和11页面/资源GET保存，113项离线读取核对通过；当前源码8项Python/8项JS直接检查通过。模型质量与S04成功链仍未通过。真实批次没有活动/unknown、Case后轮、直接reused和大原件/补答合并；相应最小状态/完整字节检查明确使用受控数据，不能当21实际覆盖。

独立包构建和配置化运行见[W4部署入口](../../deploy/investigation-test/README.md#w4独立完整包)。发布包保留同样的services/tools目录关系，离线生成器的合同摘要来自包内原文件，发送仍须显式选择新批次并提供受控连接；serve/publish不自动调用生成或发送驱动。

已保存HTTP接入记录可在新观察批次登记`http-exchanges`证据，内容schema为`socai2.test-http-exchanges.v1`；每条exchange严格匹配subject_type/subject_id/task_id/run_id，request和response保留原件字段与来源摘要。没有证据时明确未登记，不从接口文档推断已执行；自动任务不冒充HTTP提交。旧批次不可改写。
