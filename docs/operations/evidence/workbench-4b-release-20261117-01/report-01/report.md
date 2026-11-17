# 验收会话报告

会话：`acceptance-fullflow-20261117-01`。环境：21 正式调查服务（aisoc.socai2）。
保存记录状态：**全部段已完成保存和读回**。

本报告只读取这一个 prepared 会话中的已存原件；未查询远端当前状态，未发送告警，未调用模型。
执行完成、结果交付、业务判定和正文质量分别列出。模型正文正确性尚未全面验收；质量问题保留，不中断独立流程。

## 各段执行

| 段 | 计划上下文 / 告警 | 已记录发送上下文 / 告警 | 保存状态 | 保存与读回 |
|---|---:|---:|---|---|
| part1 | 2 / 1 | 2 / 1 | 已完成 | 已核对 |
| part2 | 1 / 1 | 1 / 1 | 已完成 | 已核对 |

### part1

- 连接与配置核对：通过
- 上下文投递与读回：通过
- 告警投递与分诊：通过
- 事件诊断：通过
- case_creation_and_wait：通过
- 保存与 HTTP 读回：通过
快照：observed；本段新观察 Run 3，Result 1；快照累计 Run 3。

### part2

- 追加前状态核对：通过
- 上下文投递与读回：通过
- 告警投递与分诊：通过
- 事件诊断：通过
- 等待同一调查后轮：通过
- 保存与 HTTP 读回：通过
快照：observed；本段新观察 Run 3，Result 1；快照累计 Run 6。

## 实际主体和轮次

以下按保存的主体、任务、尝试、Run、步骤和工件 ID 去重；后段累计快照不会重复加总。

| 告警 | 事件 | Case | 任务 | 尝试 | Run | 步骤 | 工件 | Result |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 1 | 1 | 7 | 6 | 6 | 48 | 142 | 2 |

工作台链接打开保存的指定主体和Run，页面实时只读；缺失时不会改选最新轮次。

### 调查 Case `8bf67e9e-a46a-58ba-a3ad-73a70ca64258`

- 第 1 轮：已完成；交付：部分交付；本轮选入告警 1 / 当时范围总量 1 条。Run `c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d`。
  流程：C1.executor / execution_plan（已完成） → C2 / baseline_background_enrichment（已完成） → C2 / knowledge（已完成） → C2 / assets（已完成） → C2 / threat_intel（跳过） → C2 / history（跳过） → C2 / ueba（跳过） → C2 / graph（跳过） → C4.materials / frozen_material_semantics（已完成） → C3 / initial_main_and_domain_analysis（已完成） → C3 / bounded_reasoning_step（已完成） → C4.query / f29523eb89bfb4adf671c6b81fe8a4e6246f6ad6ded82ff457cdfb94ce12d56c（已完成） → C4.query / 1dcc60c92009c4241eec6e7b787e0789f1be87d76e0fe6b62a307d0e70400b90（已完成） → C5 / bbd37db0d758dcbd15dcde3327a80d5a4ead927c3eee48c5c466bac8606a5537（已完成） → C4.routing / followup_dispatch（已完成） → C6 / final_delivery（已完成） → C6 / bounded_reasoning_step（已完成）
  [在工作台打开第 1 轮](http://127.0.0.1:4177/viewer/?subject_type=case&subject_id=8bf67e9e-a46a-58ba-a3ad-73a70ca64258&run_id=c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d&environment=acceptance-release-20261117-01)
  尝试 `d7966034-f206-483d-8920-6d23b16594da`：本地已结束 / 已完成；结束记录 2026-11-17T12:21:46.22435+00:00。
  结果 `e51072c6-1dab-4101-ac8d-85bc08654d86`：接收 已接收；判定 待复核；交付 部分交付。
- 第 2 轮：已完成；交付：部分交付；本轮选入告警 2 / 当时范围总量 2 条。Run `57683158-b770-4697-8ca3-a2707ed0af1b`。
  流程：C1.executor / execution_plan（已完成） → C2 / baseline_background_enrichment（已完成） → C2 / knowledge（已完成） → C2 / assets（已完成） → C2 / threat_intel（跳过） → C2 / history（跳过） → C2 / ueba（跳过） → C2 / graph（跳过） → C4.materials / frozen_material_semantics（已完成） → C3 / initial_main_and_domain_analysis（已完成） → C3 / bounded_reasoning_step（已完成） → C4.query / 5d23af662aa864f9d8e1c4f651ffe49f1c65613bbac33e1eb949f95f44322efd（已完成） → C4.query / 9019fd12e9f608de5dbbefe28eca9172cfb7a56e23e15ee91e16753f8989b2b4（已完成） → C5 / 3d1fcbe16596ce094dde729b03f67151a0ff08a8831af7f01b494e2b05a82c4a（已完成） → C4.routing / followup_dispatch（已完成） → C6 / final_delivery（已完成） → C6 / bounded_reasoning_step（已完成）
  [在工作台打开第 2 轮](http://127.0.0.1:4177/viewer/?subject_type=case&subject_id=8bf67e9e-a46a-58ba-a3ad-73a70ca64258&run_id=57683158-b770-4697-8ca3-a2707ed0af1b&environment=acceptance-release-20261117-01)
  尝试 `f328a85b-18b7-472b-ba71-3886e7288113`：本地已结束 / 已完成；结束记录 2026-11-17T12:30:22.171247+00:00。
  结果 `0823a02c-2270-43e4-891a-ffa3a2a95314`：接收 已接收；判定 待复核；交付 部分交付。
  前轮：`c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d`。
  比较基线 Result：`e51072c6-1dab-4101-ac8d-85bc08654d86`。

### 事件 `93fbd228-68a1-4ecf-b9dc-014a269a2bf7`

- 第 1 轮：已完成；交付：complete；本轮选入告警 1 / 当时范围总量 1 条。Run `0ebbdc73-98e2-57ef-8d79-591df28c7d07`。
  流程：I / incident_member_synthesis（已完成）
  [在工作台打开第 1 轮](http://127.0.0.1:4177/viewer/?subject_type=incident&subject_id=93fbd228-68a1-4ecf-b9dc-014a269a2bf7&run_id=0ebbdc73-98e2-57ef-8d79-591df28c7d07&environment=acceptance-release-20261117-01)
  尝试 `f120d39d-e32d-4924-a2d4-8e3ab46be4a8`：本地已结束 / 已完成；结束记录 2026-11-17T12:17:26.230059+00:00。
- 第 2 轮：已完成；交付：complete；本轮选入告警 2 / 当时范围总量 2 条。Run `bb1eabaa-fc49-57fa-9387-a076181202a9`。
  流程：I / incident_member_synthesis（已完成）
  [在工作台打开第 2 轮](http://127.0.0.1:4177/viewer/?subject_type=incident&subject_id=93fbd228-68a1-4ecf-b9dc-014a269a2bf7&run_id=bb1eabaa-fc49-57fa-9387-a076181202a9&environment=acceptance-release-20261117-01)
  尝试 `ab4305e5-d675-4481-bd49-3b91662c1aec`：本地已结束 / 已完成；结束记录 2026-11-17T12:26:34.339825+00:00。

### 告警 `eae52a23-632a-5cfe-9d6f-7f3e70f18847`

- 第 1 轮：已完成；交付：complete；本轮选入告警 1 / 当时范围总量 1 条。Run `60162cf6-e0a2-5fc2-8f04-513893e405df`。
  流程：A / alert_basic_analysis（已完成） → A / assets（已完成） → A / history（已完成） → A / threat_intel（已完成） → A / alert_triage_and_explanation（已完成）
  [在工作台打开第 1 轮](http://127.0.0.1:4177/viewer/?subject_type=alert&subject_id=eae52a23-632a-5cfe-9d6f-7f3e70f18847&run_id=60162cf6-e0a2-5fc2-8f04-513893e405df&environment=acceptance-release-20261117-01)
  尝试 `912d7ee0-9070-42aa-b23c-a85d01a840dc`：本地已结束 / 已完成；结束记录 2026-11-17T12:16:10.466429+00:00。

### 告警 `557b7a3c-5271-5130-b9d5-eed824ff76b0`

- 第 1 轮：已完成；交付：complete；本轮选入告警 1 / 当时范围总量 1 条。Run `45c3da88-a30d-5b1a-a5c7-6fead1fd2932`。
  流程：A / alert_basic_analysis（已完成） → A / assets（已完成） → A / history（已完成） → A / threat_intel（已完成） → A / alert_triage_and_explanation（已完成）
  [在工作台打开第 1 轮](http://127.0.0.1:4177/viewer/?subject_type=alert&subject_id=557b7a3c-5271-5130-b9d5-eed824ff76b0&run_id=45c3da88-a30d-5b1a-a5c7-6fead1fd2932&environment=acceptance-release-20261117-01)
  尝试 `53d84d7b-9e06-4b87-8db4-f20ef30a8a51`：本地已结束 / 已完成；结束记录 2026-11-17T12:24:10.902587+00:00。

## 模型输入输出

已保存请求 8 个；本会话请求总量：8。本次生成报告新增调用 0。
Token：输入 30612，输出 14595，总计 45207；费用未知。
已知 Token 小计 45207；总量 usage 未知请求 0 个。

筛选导出仅包含消息 role/content、已保存 Schema 和可见原答；输出保留原空白，不含隐藏推理或 HTTP 认证字段。完整原件仍在来源快照。

| 请求 / Run | 输入 | Schema | 可见原答 | 结束 | Token |
|---|---|---|---|---|---:|
| `108c9a88-6708-4456-853d-691e7269a86d` / `45c3da88-a30d-5b1a-a5c7-6fead1fd2932` | [输入](models/108c9a88-6708-4456-853d-691e7269a86d/messages.json) | [Schema](models/108c9a88-6708-4456-853d-691e7269a86d/schema.json) | [原答](models/108c9a88-6708-4456-853d-691e7269a86d/output.txt) | stop | 1938 |
| `483023c4-352a-4cf0-a297-b2fcc5ea7e7b` / `60162cf6-e0a2-5fc2-8f04-513893e405df` | [输入](models/483023c4-352a-4cf0-a297-b2fcc5ea7e7b/messages.json) | [Schema](models/483023c4-352a-4cf0-a297-b2fcc5ea7e7b/schema.json) | [原答](models/483023c4-352a-4cf0-a297-b2fcc5ea7e7b/output.txt) | stop | 1659 |
| `67c52c10-5e94-45d7-9470-8271172046d1` / `57683158-b770-4697-8ca3-a2707ed0af1b` | [输入](models/67c52c10-5e94-45d7-9470-8271172046d1/messages.json) | [Schema](models/67c52c10-5e94-45d7-9470-8271172046d1/schema.json) | [原答](models/67c52c10-5e94-45d7-9470-8271172046d1/output.txt) | stop | 12879 |
| `76f73cde-ff3f-4136-93b0-469561a30ba6` / `bb1eabaa-fc49-57fa-9387-a076181202a9` | [输入](models/76f73cde-ff3f-4136-93b0-469561a30ba6/messages.json) | [Schema](models/76f73cde-ff3f-4136-93b0-469561a30ba6/schema.json) | [原答](models/76f73cde-ff3f-4136-93b0-469561a30ba6/output.txt) | stop | 3993 |
| `8a7d1ca0-4fed-4e0e-ba01-bb2e60fe71cf` / `c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d` | [输入](models/8a7d1ca0-4fed-4e0e-ba01-bb2e60fe71cf/messages.json) | [Schema](models/8a7d1ca0-4fed-4e0e-ba01-bb2e60fe71cf/schema.json) | [原答](models/8a7d1ca0-4fed-4e0e-ba01-bb2e60fe71cf/output.txt) | stop | 7162 |
| `d00c97cd-6a28-4070-8aac-bfd57e9e1ed2` / `0ebbdc73-98e2-57ef-8d79-591df28c7d07` | [输入](models/d00c97cd-6a28-4070-8aac-bfd57e9e1ed2/messages.json) | [Schema](models/d00c97cd-6a28-4070-8aac-bfd57e9e1ed2/schema.json) | [原答](models/d00c97cd-6a28-4070-8aac-bfd57e9e1ed2/output.txt) | stop | 2546 |
| `e41a51d9-e921-491b-915c-b526fe8cbaf6` / `57683158-b770-4697-8ca3-a2707ed0af1b` | [输入](models/e41a51d9-e921-491b-915c-b526fe8cbaf6/messages.json) | [Schema](models/e41a51d9-e921-491b-915c-b526fe8cbaf6/schema.json) | [原答](models/e41a51d9-e921-491b-915c-b526fe8cbaf6/output.txt) | stop | 9064 |
| `fabcc4a9-1524-4eab-a7cf-1cf4fa3b2c8a` / `c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d` | [输入](models/fabcc4a9-1524-4eab-a7cf-1cf4fa3b2c8a/messages.json) | [Schema](models/fabcc4a9-1524-4eab-a7cf-1cf4fa3b2c8a/schema.json) | [原答](models/fabcc4a9-1524-4eab-a7cf-1cf4fa3b2c8a/output.txt) | stop | 5966 |

## 问题与未验边界

模型质量诊断 4 项；步骤跳过或错误记录 8 项，分别计数。
按阶段：C6 2 项，I 2 项。
- 质量：`empty_sources` × 1。
- 质量：`delivery_source_coverage_missing` × 1。
- 质量：`source_scope_diagnostic` × 2。
- 步骤：C2 / history，跳过，`tool_budget_reserved_for_evidence`；Run `c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d`。
- 步骤：C2 / graph，跳过，`source_not_connected`；Run `c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d`。
- 步骤：C2 / ueba，跳过，`source_not_connected`；Run `c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d`。
- 步骤：C2 / threat_intel，跳过，`tool_budget_reserved_for_evidence`；Run `c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d`。
- 步骤：C2 / ueba，跳过，`source_not_connected`；Run `57683158-b770-4697-8ca3-a2707ed0af1b`。
- 步骤：C2 / graph，跳过，`source_not_connected`；Run `57683158-b770-4697-8ca3-a2707ed0af1b`。
- 步骤：C2 / threat_intel，跳过，`tool_budget_reserved_for_evidence`；Run `57683158-b770-4697-8ca3-a2707ed0af1b`。
- 步骤：C2 / history，跳过，`tool_budget_reserved_for_evidence`；Run `57683158-b770-4697-8ca3-a2707ed0af1b`。

未执行段仍可在核对状态后显式选择；生成报告或退出查看不会关闭业务会话。未在本步重跑真实业务、验证远端实时状态或重新评估正文。

## 原件与读回

[结构化报告](report.json) · [文件 SHA 与来源清单](manifest.json)

下列 SHA 对应 prepared 原件；导出文件的 SHA 单独保存在 manifest.json。JSON 中的 pointer 可定位具体行。

- [runs/part1/readback.json](../../results/prepared/runs/part1/readback.json)：`1f010a0376b62505262b796f545c6f3aa9933dfc49dbd3b7111555cc43511e67`。
- [runs/part1/saved-records.json](../../results/prepared/runs/part1/saved-records.json)：`a75150cf8f80451bac65a09bb4c3ec238b90ebc905a5dd76848d35225cd1f322`。
- [runs/part1/state.json](../../results/prepared/runs/part1/state.json)：`6aaa6e9ee48b198f8ec42e1dc364437630bf2116f9bba768f0ec79d4832d27e3`。
- [runs/part2/readback.json](../../results/prepared/runs/part2/readback.json)：`4fd1721f82b0e04576cb21ad1442f163d5db550b219bb7bcc16d37dc80b1676c`。
- [runs/part2/saved-records.json](../../results/prepared/runs/part2/saved-records.json)：`fb68772006cb977726fa474a27c6f4a1600c9772cd9f94d8607b800f4d19dbc5`。
- [runs/part2/state.json](../../results/prepared/runs/part2/state.json)：`b8569d53047b122e087cd8f1378486a95d6353340c788a5484e18874e878ee27`。
