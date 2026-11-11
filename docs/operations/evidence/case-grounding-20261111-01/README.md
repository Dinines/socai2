# Case 程序事实与补查约束交付证据

`ground-case-conclusions`，分支 `V1.1`，起始 commit `45063c97f81b4f2d6bf504a6261ee7087a2353ca`。实现来源包含本次工作树差异，以冻结 manifest 为准，不能只用起始 commit 指代实际部署。

程序范围限定独审 ACCEPT；模型质量 **NOT_PASSED**。负责人决定将持续的标签推环境、未查询说成查空记录后置，原始 REVISE、五批原答、失败及采用状态不改写。[范围决定](../../../../openspec/changes/archive/2026-11-11-ground-case-conclusions/scope-decision.md)与[验收](../../../../openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)说明边界。

| 证据 | 实际含义 |
| --- | --- |
| `baseline.json`、各 `real-model-0*/plan.json` 与 `preflight.json` | 实施/运行来源与输入冻结；原始回执按各批实际路径保留 |
| `*-tests.txt`、`conflict-replay.json` | 直接受影响行为的隔离检查及原答回放，非完整业务质量证明 |
| `real-model-01` 至 `real-model-05`、`model-0*-review.json` | 真实本地 PostgreSQL、内部模型网关、实际 CaseService 链及逐批质量发现；无厂商实连证明 |
| `real-model-05/affected-readback.json` | 第五批 54 次原 GET，六项 Result 字段和两份 Deep 工件与保存一致 |
| `local-closeout.json` | 负责人后置决定前的当地收口快照，REVISE/未发布是当时事实，不能作为当前交付状态 |
| `runtime-before.json`、`runtime-after.json` | 21 从 r6 切至 r1，只更新 API 容器；实际 Case 上限 2、程序职责标记及 profile 指纹 |
| `processing-*`、`unified-*` | 处理组件与统一发布的冻结、构建、准备、一次 API rollout、激活核验 |
| `static-publication.json` | 4177 追加 5 份，21 共 34 份；本地 63 份独立计数，原资料保持 |
| `production-readback.json`、`production-reads.json`、读取前后快照 | 发布后 3 次 Case/Run/Result GET，六项字段一致，快照不变；没有生产模型调用/调查写入 |
| `delivery-summary.json` | 按上述实际回执汇总的交付范围、来源、限制与 Git 锚点约定 |

读取脚本首次错误使用 `run_id`，SQL 在查询阶段失败，修为既有 `results.source_run_id`；原日志 `production-readback-initial.log` 保留。这是验收脚本问题，无业务代码变化。随后旧 API key 过期，三个 GET 返回 401，保存在 `expired-credential-read/`。使用已有账号正常登录后复读成功；`authentication.json` 仅含非秘密元数据，令牌保存于忽略提交的受控文件，没有新增账号、key 或权限。

本次没有数据库迁移或告警交接字段变更，没有提高单 Run 额度、恢复消费者或开启 Case HTTP 写操作。生产读取为已有 Case 的历史结果兼容性检查，不能推断该模型问题已修复，也不能推断当前代码在生产新跑一轮质量通过。
