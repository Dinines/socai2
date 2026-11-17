# 阶段一步骤4：C3缺字段补答

2026-11-14，状态：**步骤4本地实现、真实模型补答及保存读取通过，未发布**。实施前已在[阶段一第四步](../../../../openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#本轮步骤4c3有界缺字段补答及可追溯合并)明确目标、顺序和验收安排，并完成[OpenSpec严格校验](openspec-before.txt)。本轮只完成这一步；主change仍31/41，模型正文质量仍NOT_PASSED。

## 目标与实现

C3截断或缺顶层字段时，先识别可靠的完整字段并验证结构、主体和数量，再由程序重带冻结业务材料及映射，最多调用一次模型补缺失字段。完整字段原值保留，初答、补答和程序合并分别追溯。沿用现有单Run预算和C6预留。

| 环节 | 本轮实现及直接验证 |
| --- | --- |
| 字段识别 | 严格读取JSON完整顶层值，不猜测半个字符串、数组或对象；拒绝重复键、主体歧义及已知格式错误。仅缺外层闭合且七字段完整时，程序可装配，不另调用模型 |
| 冻结补答输入 | `case-input-v1.json`新增版本化`c3_completion`：最多1次、补答指令和字段依赖。新C3边界冻结策略，补答重用保存请求中的业务消息及短号映射，必要的已完成分析标为`prior_analysis`；Schema仅允许缺失键 |
| 执行和合并 | 补答使用原ModelSteps的计量、调用数、token及时限门；未知执行或用量不续派。关闭补答自身的纠正重试；只接受完整的缺字段集合，保留初答字段原值后重新校验七部分 |
| 保存及下游 | 原请求、原答、原失败不改写；额外保存补答请求/原答/响应、保留方案、合并结果和每字段原答工件及hash。失败时保留可确定部分供C6读取，C4不接收半条计划 |

本轮改动9个现有文件、新增3个C3模块；[implementation.patch](implementation.patch)相对本轮开始快照生成，保留前轮和既有未提交修改。[范围核对](scope-checks.json)确认现有所有运行TOML、C3七部分/8192/最多5发现合同、C6预留实现均未改变，profile只新增`c3_completion`。旧工件无该冻结版本时沿原路径读取。

## 真实模型与保存读取

实际运行见[执行脚本](run.py)、[配置](config.json)和[检查结果](attempt04/checks.json)。本机隔离PostgreSQL为`v12_upgrade_dev`；模型通过已有内网网关与tokenizer调用。仅使用项目已保存的虚构演练材料，数据范围及内网路径核对见[model-boundary-review.json](model-boundary-review.json)。首次自动审批因尚未说明材料和目标边界拒绝执行；补齐上述证据后同一路径获准，本批没有绕过审核。

| 项目 | 实际结果 |
| --- | --- |
| 新Case / Run | `c2dbff3c-f67a-43ab-be1f-6473f1289a04` / `3b8a547a-84ee-4acc-b908-edd583ca31f3` |
| 初答来源 | 从[历史C02真实截断证据](../c3-capacity-20261114-01/README.md)导入旧请求、原答及已知usage，并明确保存历史来源；原Case/Run没有重派或回写 |
| 本批新生成 | **1次真实模型补答，0次模型替身**；请求只补`followups`，真实返回也只有该字段，`finish_reason=stop` |
| 保留和合并 | `summary/members/findings/questions/domains/conflicts`六字段原值不变；合并七部分可解析，每字段的初答/补答工件来源和hash一致 |
| 新补答用量 | 输入10,192、输出806，共10,998tokens；模型HTTP约17.14秒，含传输约17.84秒；费用未知，未记为零 |
| 初答计账 | 历史初答7,022输入+4,096输出，共11,118tokens计入新验证Run；累计22,116tokens |
| 预算保持 | Run最多6次模型、4次工具、131,072tokens及1500秒；C3输出8192，C6仍预留2次、51,200tokens及300秒 |
| 保存及HTTP读回 | **19次GET**：Case、Run和17个工件；JSON/文本与数据库一致，GET前后快照不变，不触发派发；原Case/Run保持 |
| 原问题和范围 | 初答`length`及failed继续保留，合并仍记录7项原引用问题。补答提出2项Deep建议，未执行Deep、C6或来源查询；没有本批Result及采用结论 |

初答明确为历史4096额度的真实回执，**不代表本轮重新调用8192初答或验证截断发生率**。新补答按当前8192额度及既有Run/C6限制执行。初答/补答的模型原件与程序合并分开存储；字符边界仅用于定位初答值，不将合并JSON的排版视为模型原文。

HTTP证据来自真实服务的ASGI路由加鉴权/依赖覆盖，不冒充生产TCP验收。保存结果见[database.json](attempt04/database.json)、[api-responses.json](attempt04/api-responses.json)、[c3-outcome.json](attempt04/c3-outcome.json)，请求和实际回执见[model目录](attempt04/model)，文件hash见[manifest.json](attempt04/manifest.json)，预留见[reservation.json](attempt04/reservation.json)。147个运行源文件hash与本轮最终代码一致。

## 直接检查及保留的失败

65项不同直接检查通过：新增16项C3字段识别/冻结补答/合并/部分结果进入C6检查，加步骤3的48项接收、Case输入、程序装配、引用诊断及配置检查，再复用1项既有预算/unknown预留检查。没有为真实补答验收接入模型替身。

```sh
PYTHONPATH=services/api:services/api/tests .local/conda-envs/socai2/bin/python -m pytest -q \
  services/api/tests/test_socai2_c3_completion.py \
  services/api/tests/test_socai2_c3_output_contract.py \
  services/api/tests/test_socai2_case_model_boundary.py \
  services/api/tests/test_socai2_case_program_output.py \
  services/api/tests/test_socai2_case_citation_quality.py \
  services/api/tests/test_socai2_runtime_policy.py --tb=short
SOCAI2_INVESTIGATION_POLICY="$PWD/deploy/local-investigation/investigation-policy-case-v1.toml" \
  PYTHONPATH=services/api:services/api/tests .local/conda-envs/socai2/bin/python -m pytest -q \
  services/api/tests/test_socai2_execution_capacity.py::test_reservation_protects_tokens_time_and_unknown_usage_without_changing_old_run --tb=short
```

日志保留实际过程：[offline-tests.txt](offline-tests.txt)为64项通过及预算检查因相对配置路径失败；改用绝对路径后[budget-tests-final.txt](budget-tests-final.txt)该项通过。最终代码对新增16项、配置6项及预算1项的定向复验为[23项通过](focused-final-tests.txt)，不重复计数。此前误选旧测试的归档辅助文件缺失/未指定policy失败也保留在`offline-tests-initial.txt`及`offline-tests-02.txt`，未扩大本轮修复范围或宣称全仓回归通过。

真实验收脚本的`attempt01–03`均在模型生成前因程序接线问题停止：ORM表引用、直接插入running Run被数据库状态守卫拒绝、Python空值序列化成JSON null被约束拒绝。相应事务未提交/已回滚，错误原件保留。修正为正常pending→running和SQL NULL后，`attempt04`一次真实补答通过，没有重复采样模型。以上失败不改写成成功。

最终[Ruff](ruff-final.txt)及[OpenSpec严格校验](openspec-final.txt)通过。现有发布器按目录收集新增模块，runtime_policy仍可被构建入口独立加载；本轮未构建或切换发布版本。

## 交接与停止位置

已同步OpenSpec任务、设计、规格状态、PROGRESS、前后端交接、问题清单和部署说明。本轮没有新增迁移或改告警交接字段。

使用现有`update_processing_audit.py`追加本机静态运行记录，8条中旧7条及348份既有非索引文件保持，4个本批链接可读，见[audit-readback.json](audit-readback.json)。实际4177仍为既有SSH转发，未发布本批材料或修页面。

本轮停在步骤4。步骤5补查能力分流、超限存取及4177展示修复尚未推进；真实模型引用准确性和正文质量仍未通过。本轮未部署、提交、推送、归档或勾选主change整体完成。
