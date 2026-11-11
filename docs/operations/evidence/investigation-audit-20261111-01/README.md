# 调查流程审查证据

2026-11-11，本地独立审查；[报告](../../../investigation/investigation-flow-review-20261111.md)。未修改业务实现，未连接数据库/模型，未部署或 Git 提交/推送。上一轮文档归档与独立未提交模型工具保持。

| 文件 | 实际含义 |
| --- | --- |
| `baseline.json` | 分支、commit、初始工作树、2,788 个已跟踪服务/配置/合同/测试/工具文件指纹 |
| `probe_current.py` | 4 个当前主线反例/约束检查；真实候选/解析/Schema/派发函数，工具 service 为 spy，不连接 DB/模型 |
| `probe_agents.py` | 2 个保留 Hunt 反例；真实 ASGI/loader/scheduler/engine/store，认证 principal、遥测与 DB IO 指定替换 |
| `api-tests.xml` | 40 通过：4 新探针 + 36 既有 Case 边界检查 |
| `stage-boundary-tests.xml` | 14 通过：A/I 身份与字段恢复、无效核心、过期/错配回执 |
| `agents-tests.xml` | 2 通过：**确认 Hunt 两项缺陷存在**，不代表该功能验收通过 |
| `followup-limit.json` | 三项合法 C3 query 通过 Schema/接收，派发器调用三次 spy；没有实际三次外部查询或证明绕过总预算 |
| `semantic-boundary.json` | 合成无依据文本搭配合法来源被接收，仅说明引用校验不是语义真值校验；并非真实模型原答 |
| `hunt-tenant.json` | 两个认证身份在真实路由下均采用 default 目标；未调用真实 JWT 或数据库 |
| `hunt-failure.json` | 注入数据源 timeout 后真实 store 生成 completed/0/null SQL 参数；SQL 只被捕获，未执行 |
| `historical-model-review.json` | 只读复查前批真实输入/原答/落库及采用关系、原件 hash；98 个冻结来源与当前一致，无新模型调用 |
| `verification.json` | 本轮检查数、初次失败原因、未覆盖项、受保护文件无差异 |
| `independent-audit.md` | 未参与报告编写者的结束审查回执 |
| `openspec-validation.json` | 归档后活动规格/变更 15 项及归档 change 9 项严格校验通过 |
| `document-checks.json` / `closure-checks.json` | 文档链接、最后源码保护、主任务计数及审查文件指纹 |

所有探针断言记录的是**实际观察行为**；其中有缺陷断言，不能直接当修复后必须仍通过的回归标准。修复验收须将相应缺陷断言改为预期行为。

## 复现

在仓库根目录，使用已安装环境，不安装依赖、不读取私密运行配置。按独审建议，探针再次执行时将 4 份 JSON 输出写入系统新建的 `socai2-audit-current-*` / `socai2-audit-agents-*` 临时目录，保留本批已结束回执；断言及数据不变：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/api:services/api/tests:docs/operations:. \
.local/conda-envs/socai2/bin/python -m pytest -q -p no:cacheprovider \
  docs/operations/evidence/investigation-audit-20261111-01/probe_current.py \
  services/api/tests/test_socai2_case_followup_boundary.py \
  services/api/tests/test_socai2_case_scope_recovery.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/agents \
.local/conda-envs/socai2/bin/python -m pytest -q -p no:cacheprovider \
  docs/operations/evidence/investigation-audit-20261111-01/probe_agents.py

PYTHONDONTWRITEBYTECODE=1 \
SOCAI2_INVESTIGATION_POLICY="$PWD/deploy/local-investigation/investigation-policy-case-v1.toml" \
PYTHONPATH=services/api:services/api/tests:. \
.local/conda-envs/socai2/bin/python -m pytest -q -p no:cacheprovider \
  services/api/tests/test_socai2_alert_model_boundary.py::test_five_fields_restore_original_contract_without_rejudging \
  services/api/tests/test_socai2_alert_model_boundary.py::test_invalid_core_is_failed_not_unknown_or_rewritten \
  services/api/tests/test_socai2_incident_model_boundary.py::test_output_restores_original_ids_fields_and_exact_sources \
  services/api/tests/test_socai2_incident_model_boundary.py::test_bad_receipt_pairing_integrity_or_scope_fails_before_model \
  services/api/tests/test_socai2_incident_model_boundary.py::test_stale_triage_and_its_receipts_cannot_be_used_as_current
```

留存的首次 Case 命令还列有 `test_socai2_stage_execution_api.py`，该文件通过嵌套 `run_checks` 供 PG 验证器调用，pytest 此次收集 **0 项**；上述复现命令移除这一无效参数，实际 40 项不变。没有执行其数据库入口。

## 首次失败与证据限制

- `api-tests-initial.xml`：39 通过、1 失败，审计探针尝试对 frozen Pydantic 对象赋值；改用 `model_copy(update=...)` 后 40 通过，业务源码未改。
- `stage-boundary-tests-initial.xml`：7 通过、7 失败，首次调用漏显式策略文件；补上上面同一仓库策略的绝对路径后 14 通过，未修改测试或业务以消除错误。
- 历史真实模型/PG 数据来自 `case-evidence-roles-20261110-01/real-model-01`；真实模型处理的是已存演练材料，无独立业务真值，不能计算准确率。历史生产 GET 也不是本轮生产观测。
- 主线实际工具超时/权限拒绝、并发恢复、真实动态证据对比、非空知识、完整 HTTP 写和自动消费者未做本轮集成验证。受控纯函数通过不扩展到这些范围。
