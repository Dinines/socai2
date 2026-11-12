# 知识用途筛选直接验收

复用历史卡片及 Case HTTP 驱动，只创建 `knowledge-selection-20261112-01` 一条新批次。明确构造历史来源，保存一次人工反馈第二版；该陈述是测试材料，不是真实人工核查。原方法资料正文不改写，仅新副本显式标注两个目的及进程／动作条件。独立 Qdrant 集合不影响旧批次。

沿 `run.py prepare|knowledge|run|export --config tools/testdata/knowledge_selection/local.json` 顺序执行；每一步写排他意图／结果，已开始的批次禁止盲目重发。`run` 只有一次 Case，自然经过后续和既有有界纠正；不为模型正文质量另行重跑。原文、源映射、实际调用、保存读回和失败均在 output 目录。

知识操作走原 HTTP 入口。来源初始分诊／人工陈述及第二版以隔离演练 SQL 准备，不冒充生产人工反馈接口验收。卡片更新后旧 GET 保持，C2 只选当前内容。与新批次无关的旧卡、旧 Run 和旧失败保持。

本批已经结束，证据见 `docs/operations/evidence/knowledge-selection-20261112-01/`，不得重发。生产配置为 `production.json`：`python -m tools.testdata.knowledge_selection.production import|probe --config <配置>` 复用方法资料写读／只读探针；历史沿 `python -m tools.testdata.historical_knowledge.production import|probe --config <配置>`。本轮两路均已完成并撤销临时 key，没有生产 Case／Run／分析模型；调用回执与本地完整流程分开记录。新验收必须使用新批次和明确范围。
