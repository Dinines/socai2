# 同批已受理A/I任务：实际执行与交接

本步沿S01-r3已通过的Kafka入站材料和4条initial任务，不再投递，也不建Case。调查独占配置/唯一调度器和运行观察；测试负责最小资产来源、PG/原件验证和实际身份映射；HTTP按同批快照读回结果。

## 配置与准入

采用[显式分析配置](../../../../deploy/aisoc21/streaming-candidate-20261115-01/analysis.json)和analysis/目录，已有r3镜像、普通候选writer、Redis DB1、真实A/I/Case联合工厂。N=1、轮询1秒，I20秒/Case30秒、活动86400秒、已知暂时故障重试1次等5秒；当前无Case任务，Case专用知识/日志工具未验。正式默认不改。HTTP在最终读取前加载同一份lifecycle。

模型沿当前case-v1策略：LiteLLM aisoc-investigation实际路由到43的aisoc-test-investigation，context65536；A/I每Run输出3000、总token24000、最多2次生成（含有界引用纠正）、300秒。没有增加预算或重复采样。

[首次准备](prepare-01.json)在导入阶段发现处理镜像未安装HTTP侧psycopg，未启动任务或生成。原输入脚本在prepare-invocation-01.json，私密诊断留21受控目录；本步改用处理镜像现有asyncpg，单一显式路径，无驱动回退/业务代码变化。

[实际预检](preflight-02.json)通过普通writer/TLS1.3、来源表可读、Redis DB1空、当前联合工厂、同租户resolver及模型目录、真实tokenizer计量；5份挂载配置摘要与本机一致。该预检时0attempt/Run/Case，tokenizer计量不计生成。原失败URL/env备份在21私密目录，不记录凭据。

## 来源与范围

测试[本步计划](../test-streaming-ai-20261115-01/README.md)只供给1条标记为synthetic的主机资产，同资产host/IP可命中两行。history读真实同命名空间历史告警；threat_intel没有已知声明，0导入并验真实查空。不造恶意情报、授权或历史分析。账号用途当前未单独接入，知识/UEBA/图/产品及C4日志不在本步，不以已入湖冒称工具查询。

## 当前执行出口

状态：本步真实执行、保存及HTTP读取的程序流程通过，模型正文质量NOT_PASSED。[启动](start-01.json)后，首次运行观察为3A完成/I运行；[第二次观察](observation-02.json)为新4任务全部completed、各1次attempt且无在途，旧关闭批4任务实际skipped/closed_before_start且无attempt。随后[正常停止](stop-01.json)exit0，没有取消分析或重写业务数据。测试和HTTP各自完成以下同源核验，不由运行计数推断内容通过。

[测试保存核验](../test-streaming-ai-20261115-01/analysis-validation-01.json)通过：4个真实Run/4次生成、9次真实PG背景查询；每A资产2行同1记录，history为0/3/6行且分别0/1/2个历史告警，threat_intel均实际查空。I冻结3条A均usable/current（程序合同状态，不等于语义真实），配对9份已保存查询回执，结构覆盖3/3，旧批无新Run/结果，入站原件不变。测试快照首次脚本误用Case results.run_id失败，修正为实际source_run_id后取得一次完整快照；原失败/脚本保留，没有重执行模型。[实际身份map](../test-streaming-ai-20261115-01/actual-analysis-map-01.json)一次性交HTTP。

[同批62次HTTP GET](../streaming-ai-http-20261115-01/README.md)全部通过：4task/4Run/3分诊1诊断、17步骤及45份Run工件目录完整，29份必要正文（输入/策略/模型请求、原答、校验/9查询回执）与PG快照一致，当前/历史及task→attempt→Run→结果链接正确；旧4task实际跳过且无attempt/Run，I的1天资格摘要与同份lifecycle一致。HTTP没有直查数据库、写业务或调用模型，也没有重复35次入站。结果摘要SHA256为`4178c5b3fae56c9250d9b552c1a3504f483ef74b8f7dfdeb6b6489bff574f1b4`。

本步实际[usage](../test-streaming-ai-20261115-01/usage-01.json)输入10652、输出3370、共14022 tokens，费用未知，不记零。正文质量[NOT_PASSED](../test-streaming-ai-20261115-01/quality-findings-01.json)：3A解释仅“告”且重复引用、I正文几乎均“A”；原答及已保存结论保留，程序completed不代表这些判断正确。根侧[离线请求复核](saved-request-review-01.json)只确认原答已如此、非保存时截断，当前资料不足以确认根因。按明确后置范围记录，不调整Schema、追加采样或重写答案。

当前推荐的analysis-aic-dispatch示例及部署说明已同步asyncpg参数，保持正式默认时限；本机loader直接检查通过。本步脚本Ruff、OpenSpec strict通过；未重跑已验入站、源码单测或HTTP空态，无正式发布或Git推送。

下一子步准备Case实际查询/知识来源与完整profile，由HTTP按同批真实事件/告警建案，核受理无Run后再执行首轮。Case/S04更新/比较、W2代理非空/跨Run、W3/W4、独立结束审计及正式发布继续待办；当前无Case，不提前把整体验收勾完。
