# F2 事件 AI 概况

2026-10-27审计补充：[当前实现详解](current-implementation-reference-20261027.md)补齐完整返回字段、数据表、首次任务触发和证据范围；本版事件职责继续保持汇总与概况。

2026-10-25。功能代码及直接验证已完成，尚未部署、执行数据库迁移或启动任务。概况只汇总已保存材料，不创建调查Run、不调用调查工具。

## 接口

- `GET /api/v2/investigation/incidents/{incident_id}`：原F1当前数据，附加`ai_overview`和`ai_overview_metadata`。读取不会调用模型。
- `POST /api/v2/investigation/incidents/{incident_id}/overview/refresh`：无请求体，用当前事件材料生成并保存概况，然后返回同样的事件结构。复用已有`alerts:write`和`alerts:read`权限。

接口已在独立的`incident_api`及兼容结果/启动app中注册。运行新版前须按现有迁移方式应用[120迁移](../../services/api/migrations/120_fusion_incident_summaries.sql)，增加`fusion_incident_summaries`表。此迁移未在本轮执行；F2代码的事件读取会使用这张新表。

返回示意（省略其他当前字段）：

```json
{
  "ai_overview": "主机出现脚本行为告警，当前待进一步核对……",
  "ai_overview_metadata": {
    "status": "ready",
    "generated_at": "2026-10-25T10:01:00Z",
    "source_updated_at": "2026-10-25T10:00:00Z",
    "is_stale": true,
    "source_refs": {
      "member_ids": ["本次提供给模型的Alert UUID"],
      "triage_run_ids": [],
      "source_member_count": 3,
      "omitted_member_count": 2,
      "fields_truncated": false,
      "investigation_results_status": "not_linked"
    },
    "model": "所用模型",
    "last_attempt_status": "succeeded",
    "last_error": null
  }
}
```

当前成员/分诊始终来自F1读取。当前材料与生成时不同，`is_stale=true`，旧概况文本和生成时间保留；用户手动刷新后更新。首次失败返回空概况、`status=not_generated`和失败信息；刷新失败保留旧文本，`last_attempt_status=failed`。失败以字段返回，调用方须读取这些字段，不能仅凭HTTP 200提示生成成功。

## 首次自动生成

新增独立v2任务：[incident_summary_worker](../../services/api/app/investigation_v2/incident_summary_worker.py)。它读取PG已提交的事件归属，为所选租户的新事件生成第一份概况，保留原Fusion worker及运行配置。

在API依赖环境中运行，例如：

```text
python -m app.investigation_v2.incident_summary_worker --tenant-id <tenant-uuid>
```

- 默认从任务启动时刻开始选择新形成的事件，每30秒检查一次，单批最多20个；不自动补生成历史事件。
- `--since <带时区的时间>`可显式指定形成时间下限；按该事件最早一条PG成员的`created_at`判断。
- `--once`只处理一批后退出；`--interval`调整检查间隔。
- 已有首次尝试记录的事件不再自动生成，包括首次失败；之后由手动刷新重试。普通成员/分诊变化不会自动重写概况。

上述命令仅为接入说明，本轮没有启动任务或改变现有部署。

## 材料与模型

[生成服务](../../services/api/app/investigation_v2/incident_summary.py)复用租户模型配置、安全调用、air-gap检查及现有费用表。费用归于`incident:<uuid>`，返回已知token用量，估算与实测费用保持原区分。

模型输入为当前事件及成员的有限材料，不发送完整原始告警。输入限制为16000字符，过长字段/成员省略会在来源范围中明示；概况不得因此声称覆盖全部事件。模型输出限650 tokens，空文本、工具调用或明确截断的回答不替换旧概况。

Case内F3第一版已实现，但F2没有读取其结果，来源标记仍为`investigation_results_status=not_linked`。这意味着“概况材料未包含深入调查结论”，不能解释为“历史上从未调查”，也不能据F3存在说本概况已纳入Case报告。

## 直接验证

运行：`python -B -m unittest discover -s services/api/tests -p 'test_investigation_incident*.py' -v`。

本轮8项通过：F1相关4项，以及F2的生成/读取/过期/手动刷新、失败保留、首次任务只生成一次、材料范围标记4项。使用实际ASGI路由、实际模型请求包装和HTTPX模型替身、数据库替身；没有真实PG写入、真实模型调用或额外可用性/恢复测试。

后续深入调查统一在Case中，当前[F3第一版](case-investigation.md)已有代码及替身验证；下一功能是F4告警/事件成员转Case入口。事件概况不增加独立深入分析流程。
