# S01 Case首轮候选验收

当前状态：本步Case创建、真实首轮执行、保存及HTTP读取的程序联验通过。两案均completed/accepted/uncertain/partial；10项引用问题保持NOT_PASSED，正文未做全面质量验收。整体change仍未验收，未正式发布。

沿用`s01-ingress-20261115-02`真实Kafka材料与已完成的3A/1I，只新增整事件Case和固定A01 Case的首轮。不重投Kafka、不重跑A/I、不投S04、不改变旧失败或模型原答。来源供给和保存由测试唯一负责，HTTP创建和读回由HTTP模块唯一负责，调查只负责当前profile和唯一调度。

- [当前运行配置](../../../../deploy/aisoc21/streaming-candidate-20261115-01/analysis.json)：同r3镜像、候选PG普通writer/TLS1.3、候选CH普通reader；N1，轮询1秒，I20秒/Case30秒/活动86400秒，重试1次/5秒。单Run模型预算和HTTP生命周期保持已有值。
- [来源预检](prepare-02.json)：现行A/I/Case工厂、候选知识表读写、真实embedding模型目录、Qdrant独立集合空起点；正常LakeGateway查询同批3条进程记录，0生成/0embedding/0Case。这是依赖预检，不是Case C4执行证明。
- [知识配置](../../../../deploy/aisoc21/streaming-candidate-20261115-01/analysis/knowledge-profile.json)：qwen3-embedding:0.6b、1024维；独立候选集合；三用途/阈值/适用规则保持，分诊后历史同步关闭。技术解释与取证指导两份原文由正常来源程序导入；无真实历史源卡的第三份叙述不索引，不构造历史判断。
- [原A/I配置](previous-analysis.json)保留；受控env旧文件和远端config另有历史归档。仅当前配置可用于后续运行。

[初次SSH调用](prepare-invocation-01.json)因命令引用错误在执行前失败，原空stdout保留；修正引用后prepare-02通过。没有由此产生业务任务或模型调用。来源预检脚本的直接Ruff已通过，活动OpenSpec strict通过。

[来源验收](../test-streaming-case-initial-20261115-01/source-acceptance-01.json)已完成：2份原文正常ingest/普通reader读回/唯一索引及一次检索，PG与索引内容hash一致。真实embedding两请求分别2文档和9查询、70及591输入tokens，费用未知；9次向量搜索返回4适用行，2条跨适用范围候选被排除，3次历史目的真实查空。未产生分析生成或Case执行，不能代替Run内实际C2/C4证据。

来源读回首次遇脚本sslmode适配失败、第二次遇普通reader缺知识表SELECT，原两份失败保留；[补齐只读接线](knowledge-reader-access-01.json)后同一reader读回通过，没有重复导入。新装/升级共用片段及verify同步，表/字段/RLS及写权保持；[安装器直接检查](reader-installer-check-01.json)9通过、3项需显式隔离PG profile而跳过，实际候选读回另有上述证据。[Case创建准入](readiness-01.json)记录实际来源及运行配置摘要。

| 本步出口 | 实际结果与证据 |
| --- | --- |
| HTTP受理 | [2 POST/5 GET](../streaming-case-http-20261115-01/acceptance-01.json)通过；整事件Case含3成员、单A01案含1成员；受理时均无attempt/Run。I01唯一接收目标仍是整事件案。[实际身份](../streaming-case-http-20261115-01/actual-case-map-01.json) |
| 唯一真实执行 | [13:20:16Z启动](start-01.json)同r3正常调度，两个initial各1次attempt/Run，N1串行、0重试。各C3/C6真实生成一次，共4生成/48239tokens，费用未知；各2次C4，共4真实湖查询。整案network/process，对照process/auth；Deep未选择，不冒称已验 |
| 正常停止 | [13:25:22Z状态](observation-05.json)为全部任务终态、0在途，随后[正常exit0停止](stop-01.json)。原A/I停止容器保留；没有S04、旧任务重派或业务结果改写 |
| 保存核验 | [一次普通reader快照](../test-streaming-case-initial-20261115-01/case-pg-01.json)、[277项直接核对](../test-streaming-case-initial-20261115-01/case-validation-01.json)通过。两案各17步骤/48工件，范围3/1；原I覆盖保持3、单案仅取交集1及范围限制。C2知识命中4/2行，原文实际进入C3/C6；[既有A/I保留](../test-streaming-case-initial-20261115-01/upstream-preservation-01.json)逐项通过 |
| 结果读取 | [58次同源GET](../streaming-case-result-http-20261115-01/result.json)通过，34步骤/96工件目录及44必要正文与快照一致，含task→attempt→Run→Result、当前判断与首轮比较空态。首次离线核对误取不存在字段的失败保留，仅重验已保存响应，未重复HTTP |
| 质量和部分交付 | [具体缺口](../test-streaming-case-initial-20261115-01/partial-delivery-01.json)：未接来源、预算保留导致跳过查询、成员未决及每案3个未解问题等。任务完成、结构accepted、待复核和partial分别记录。[10项引用问题](../test-streaming-case-initial-20261115-01/quality-findings-01.json)保留判断、不改原答；单案提及“补查到网络连接”的措辞另待正文复核，无新采样 |
| 查阅材料 | 用现有update_processing_audit.py从唯一保存快照[离线导出并追加两卡](audit-export-01.json)，原38卡/83历史Case文件保持，现40卡。没有新DB查询或模型；实际4177仍未切换，W3仍待 |

两案首轮后，仍须S04新增Kafka告警经I推动活跃Case后轮及上一轮比较、W2代理非空/跨Run、W3/W4、独立结束审计，才能按既定授权统一正式发布。已有A/I正文质量NOT_PASSED原样保留，不把任务completed等同正文通过。
