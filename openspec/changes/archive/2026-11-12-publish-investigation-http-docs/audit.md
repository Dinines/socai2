# HTTP 文档限定独立审阅

审阅者：未参与本项实现的 `http_docs_review`。时间：2026-11-12。

## 范围与方式

只读查看 `deploy/api-docs/catalog.py`、`build.py` 及生成的 OpenAPI、功能映射、示例，参照现有 `socai2_*` 路由、页面/Case/任务合同与读取实现。未执行测试，未请求业务 API、数据库或模型，未修改业务代码；不替代产品、模型或部署验收。

已核对的主要边界：43 个操作仍沿既有路由；Q 问答/保存/采用明确为 501；A/I 手动执行标为已实现但启用待核实；告警/事件完整筛选、Case 通用管理、探索、评论附件、真实响应执行均未冒称实现；125 项逐页功能保留原型/页面/后端与 HTTP 状态区分，未扩入旧 AiSOC 平台。

## 初审需修正

1. **统计示例字段错误。** E26/E27 的 `overall_stats` 使用不存在的 `by_state`，遗漏读取实现平铺的实际指标。应分别采用告警/事件真实字段，防止前端按错误层级取数。
2. **结果示例冻结范围自相矛盾。** E14 的结果有 `input_artifact_id`、`case_impact.affected_scope` 包含一告警，但同响应 Run 输入工件为空，成员为零。需形成一致的独立合成场景。
3. **新增记录 Schema 的可空性误述。** `RecordAlertMember` / `RecordIncidentLink` 将 `correlation_basis`、`basis_version` 写成可空，但当前关联行分别为非空 object/string。保持现有合同。
4. **若干状态/分区示例不是可产生的记录。** E22/E23 无当前指针时原因实际为 null，并无 `not_recorded`；E28 缺事件时间的示例应表达 unknown。E30 自动生成的非空分区记录含“示例”枚举和不满足主体/响应关联约束的全 null 字段，宜整理成有效合成记录，或保留空响应并通过字段字典说明结构。

以上已反馈主实现者。初审结论：修正上述文档问题后再完成限定复阅；未对部署状态作结论。

## 修正后限定复阅

同日读取重新生成的 `examples.json`、`openapi.json`，上述四组问题已修正：

- E26/E27 使用实际平铺统计，告警与事件分别保留自己的指标。
- E14 的 Result/Run 输入工件 ID 一致，成员数为 1，成员状态 `not_analyzed`、`conclusion_covered=false`，结论仍为 unavailable，未将合成失败包装成成功判断。
- 两个事件关联记录类型的 `correlation_basis`、`basis_version` 分别为非空 object/string。
- 无指针原因恢复 null，缺事件时间表达 unknown；E30 各分区响应示例使用明确空集合，结构由相应 Schema 说明，不再伪造不成立的业务行。

补读 HTTP 接入 README 与独立 Compose/profile：文档端口与业务 API 端口明确区分；无业务代理或业务配置改变；本地 arm64、21 amd64 分别显式选择平台及固定镜像；静态挂载只读、在线校验器关闭。镜像拉取、平台运行和页面读回仍由主实现者的部署回执证明，本审阅不代替运行观测。

**结论：本次限定文档审阅通过，所报阻塞已修正。** 该结论仅覆盖交接说明及上述静态修正，不宣称全量接口实测、模型质量通过或主调查 change 完成。整个审阅没有运行测试、业务请求、数据库查询或模型调用。

### 最后文档增补复阅

仅复看 JSONB/枚举提取及 `source_artifacts` 增补：生成器读取当前模型的 CheckConstraint，将工件 `source_refs` 正确记录为 array、`retention` 记录为 object，并保留已存在的枚举及可空性；未修改服务字段。`RecordSourceArtifact` 排除正文、tenant_id、blob_ref，增加实际读取实现提供的 `content_url`，E30 分区映射及空集合示例已接入，未发现新增明确合同错述。README 链接输出指向 `guide.html`；静态 Swagger 配置的 `filter` 为 JSON boolean true。以上只读复阅后，限定结论保持通过；未新增测试或业务调用。

## 发布回执（主实施者补记）

2026-11-12已完成本机ARM64及21 AMD64独立Swagger容器启动。两端首页、功能页、OpenAPI均HTTP200；实际架构分别aarch64、x86_64；OpenAPI摘要相同。详见仓库 `deploy/api-docs/deployment-receipt.json`。只读取文档和本项目容器状态，无业务接口、数据库、模型调用；21使用本机明确导出的amd64镜像，不修改原Docker代理。未提交、推送或变更父项目引用。
