# 采用调查结果：后端调用指南

本批接口与发布进度见[交付记录](../../openspec/changes/archive/2026-11-13-adopt-investigation-results/validation.md)。路径前缀为`/api/v1/socai2`，后端使用21的`18024`；当前服务及Swagger版本以[总交接指南](../../FRONTEND_BACKEND_HANDOFF.md)为准。

“采用”就是用户选择一份已经保存的调查结果，作为该案件目前认可的判断。例如几轮调查有不同结论，用户对比后选择其中符合当前依据的一轮。它不重新执行模型，不结案，也不会把未完成任务标成完成。

## 调用顺序

1. 从调查历史E10或正式结果E14取得本案`result_id`。
2. E63 `GET /cases/{case_id}/results/{result_id}/adoption-preview`。展示`current_assessment`旧判断、`candidate`候选结论/未解决问题/限制、`members`覆盖、`input_freshness`以及未完任务/调查。`can_adopt=false`时展示`refusal_reasons`，不要提交。
3. 用户填写理由。如果`requires_pending_work_acknowledgement=true`，展示`unfinished_tasks/unfinished_runs`，让用户明确知晓它们仍未结束。
4. E21 `POST /cases/{case_id}/results/{result_id}/adopt`，按下例提交。`expected_review_token`必须使用刚才预览的原值。
5. 成功后E03重新读取案件当前判断，E64 `GET /cases/{case_id}/assessments?limit=20&offset=0`读取版本历史，E17读取采用活动。E64按版本倒序，`next_offset=null`表示结束。

```json
{
  "operation_key": "00000000-0000-4000-8000-000000000901",
  "expected_review_token": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "reason": "保留本轮待复核结论，运维核实任务继续跟进。",
  "acknowledge_pending_work": true
}
```

以上UUID和摘要仅说明格式，实际须换成本次操作UUID与预览响应。理由去除两端空白后1–4000字符。没有未完工作时确认字段可省略，默认false。旧E21一直是501占位，只有`operation_key/expected_scope_revision`；启用后需改用上述请求，旧`expected_scope_revision`会422。

## 成功返回什么

| 字段 | 含义 |
| --- | --- |
| `case_id` | 案件UUID |
| `result_id` | 用户选择的原结果UUID |
| `assessment_id` | 本次追加的判断UUID |
| `previous_assessment_id` | 被替换的旧判断UUID；此前没有为null |
| `assessment_revision` | 本次判断版本序号 |
| `case_row_version` | 本次保存后的案件行版本 |

原Result、原结论内容及所有旧判断保留。人工选择模型结果，结论来源仍是`model`；实际采用人和理由单独记录。未解决问题继续随结论展示，用户有需要时另建人工任务。

历史中的`validity=accepted`表示当时校验通过，不表示模型质量已验收，也不证明依据目前仍有效。当前判断的新鲜度读取E03；E64保存各版本当时内容。候选即使是`uncertain/partial`，只要符合当前依据及全员有效覆盖等核心条件仍可采用，不能因此隐去待核事项。

## 未完成工作和后续结果

采用不修改任务、Run或案件处理状态。已开始的旧调查在人工采用后完成，不覆盖更晚的人工选择；之后用户显式启动的新调查仍可按原规则自动采用。后续有效人工反馈可能使当前判断变为依据过期，需要时显式准备和启动新调查，本接口不自动重算。

相同key、操作者、目标与完整请求重试会返回原回执。即使当前判断后来变化，旧请求重试也不回滚指针，所以拿到旧回执后仍应E03读取最新案件。改变理由、确认字段或目标属于新意图，应生成新key。

## 错误怎么处理

| HTTP/原因 | 后端处理 |
| --- | --- |
| 404 | 核对Case及Result是否真实存在且属于同案 |
| 409 `result_adoption_preview_changed` | 保留用户理由，重新预览并展示变化，再由用户确认；不要自动换摘要重试 |
| 409 `result_adoption_pending_work_confirmation_required` | 展示未完任务和Run，用户明确知晓后再提交 |
| 409 `case_reopen_required` | 已结案须先显式重开 |
| 409 结果/范围/覆盖/依据不合格 | 按`refusal_reasons`说明原因；不能强行采用局部、过期或未完成结果 |
| 409 `operation_key_conflict` | 同key不能改意图；新操作使用新key |
| 422 | 修正请求格式、理由、旧多余字段或分页参数后再提交 |

完整输入、所有固定/动态字段、独立合成示例及错误分支在Swagger的E21/E63/E64。文件附件与人工结果采用无自动关系：附件登记不会使候选重新分析或变成新证据。
