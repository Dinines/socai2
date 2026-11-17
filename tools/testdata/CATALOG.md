# 测试材料使用清单

2026-11-16。当前新业务测试只使用下面的 v2 材料入口；旧批次、历史评估器和答案语料不再作为新一轮盲测输入。实际存储中的历史测试数据已按负责人明确授权清空，详见[清理回执](../../docs/operations/evidence/test-data-reset-20261116-01/README.md)。

| 材料 / 入口 | 当前用途与模型边界 |
| --- | --- |
| `streaming_fixture.py`、`streaming-fixture.example.json` v2 | 当前 S01/S04 新批生成。4 告警、13 上下文、资产事实与两份技术指导；manifest、expected、actions、identity-map 只供程序核对 |
| `alert_scenarios.py` v2 | 上游 55 模板的业务观察。统一中性标题、空描述、无测试标签；作者叙述、答案及标识映射只进 expected 旁路。旧 v1 发送材料拒绝加载 |
| `material-source.json` | 程序识别固定中性来源 `telemetry-channel-01`，不含“测试”字样；`program_classification` 在控制配置中。来源字段不进入已核 A/I/C3/Deep/C6 输入视图 |
| `streaming_send.py`、`alert_kafka.py` | 仅加载显式新批业务材料，不打开 expected。生成/校验不等于获准重派已结束批次；当前消费者停止，无新投递 |
| `investigation_fixture.py` v2、`context_fixture.py` | 已修正中性来源和元数据，用于离线合同检查；历史 plan 中的人为主机/账号/说明未自动洗白，不拿旧 plan 直接跑新盲测 |
| `upstream/` | 固定 revision 的只读作者原件，包含标题/答案。仅经上述 v2 生成器投影使用，禁止整包透传模型 |
| `alert_io_eval`、`alert_prompt_eval`、`incident_io_eval`、`incident_integration` | 历史评估器/样本，含合成来源或作者叙述；退出当前新数据入口，仅供历史复核 |
| `case_io_eval`、`cas                                                                                                                                                                                                                                                                                                                                                                                   e_integration`、`case_followup_eval`、`case_grounding`、`case_evidence_roles`、`case_scope_recovery`、`case_human_http` | 历史范围/合同/原答评估，未作为当前新盲测语料重新认证；不自动回放 |
| `historical_knowledge`、`case_knowledge`、`knowledge_selection`、`knowledge_sync` | 历史索引/选择测试，含人工历史案例与答案。相关活动索引已清空；不导入新调查的模型上下文 |
| `tests/`、服务端单元测试样例 | 可保留错误、答案或注入标记验证防护；不发布到业务模型数据源 |
| 其余根级探针、观察/清理工具 | 历史专用操作入口；完整路径清单见下方，不作为当前新批自动任务 |
| `docs/operations/evidence/`、私密清理备份 | 审计/恢复原件，原失败不改写；不进入活动账本、知识索引或模型输入 |

[本轮完整入口清单](../../docs/operations/evidence/model-blind-data-20261116-01/entry-inventory.json)记录文件路径、分类和摘要。[新材料及模型视图检查](../../docs/operations/evidence/model-blind-data-20261116-01/README.md)覆盖当前新入口。这个结论不表示旧目录全部经过内容清洗或旧模型质量通过；新一轮只能重新生成独立批次。
