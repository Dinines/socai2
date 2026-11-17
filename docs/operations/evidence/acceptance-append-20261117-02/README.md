# 3c.2：显式追加与同 Case 后轮验收

2026-11-17，本机新批 `acceptance-append-20261117-02` 已完成两段真实流程及保存/HTTP 读回。两种 Case 均沿原 ID 形成第二轮，旧轮次保留；[测试模块独立结束复核](../test-acceptance-append-20261117-01/independent-review-04.json)已通过。[最终验收](final-validation.json) · [最终会话状态](status-final.json) · [脚本用法](../../../../tools/testdata/ACCEPTANCE.md)。

本批使用新 PostgreSQL 库、Kafka Topic、ClickHouse 库和 Redis 分区，当前业务 HTTP/Fusion/联合调度及真实模型。只复用原业务材料模板，未复制历史业务记录或模型结果；01 的 HTTP 配置失败保留[原结论](../acceptance-append-20261117-01/README.md)。本轮未发布 21、未推送、未归档 change。

## 实际流程

| 阶段 | 首段 part1 | 显式追加 part2 | 核对结果 |
| --- | --- | --- | --- |
| 独立上下文 | 2 条 | 1 条 | 逐条 ACK 后按湖中身份、时间和原值核对，均先于本段告警发送 |
| 告警分诊 | 1 条 | 新增 1 条 | 材料及来源关系保存，真实自动 A 完成后继续 |
| 事件诊断 | 1 个事件首轮；显式 check 为 no_changes | 同事件新增成员后更新 | 两轮 I 保存/读取，未把旧 I 当新结果 |
| 整事件 Case | 1 成员，首轮 | 同 Case 扩到 2 成员并执行后轮 | 两轮各自冻结成员、前轮 Run/Result 与比较上下文匹配 |
| 固定告警 Case | 1 成员，首轮 | 保持 1 成员，实际增量检查产生后轮 | 没有重建 Case，也未将新增告警加入固定范围 |
| 保存/HTTP 读取 | completed，41 步骤/121 工件 | completed，累计 83 步骤/245 工件 | 两段均闭环，4 个 Case Result，旧原件不变 |

最终 2 告警、1 事件、2 Case、9 task、8 attempt/Run、4 Result。唯一 skipped 为首段事件显式检查的 `no_changes`；没有失败任务或在途任务。[追加前快照](prepared/runs/part2/before-records.json)、[后轮核对](prepared/runs/part2/append-readback.json)、[数据库原件](final-records.json)。`status` 为 `all_parts_completed` 且无下一候选；这仍是已存事实，不是持续实时查询。

首段实际 510 次 GET 200、2 次 POST 201、1 次 POST 202；第二段 844 次 GET 200、3 次 POST 202，包含任务轮询和步骤/工件分页。[首段读取](prepared/runs/part1/readback.json) / [后段读取](prepared/runs/part2/readback.json)。额外一次最终只读目标检查另存目录，不计业务执行或模型调用。

## 轮次与原件

| Case | 首轮 Run → Result | 后轮 Run → Result |
| --- | --- | --- |
| 整事件 `7a5aa48c-3465-5bc3-b78f-55f325788f5d` | `e1ffb44c-e7d4-4108-b34e-e9833e0ac81a` → `4a54b8cd-1e8b-4557-9012-14086cd12b17` | `69e13bd9-3293-4027-9847-971357e16097` → `d14e4b4e-313d-4e6f-b2b5-4adb72a725c3` |
| 固定告警 `bd06079e-d6ee-5f84-981e-ebecfa6f0c69` | `0e799965-c10c-4688-87d4-ca077da75fa3` → `bf8a4fe3-0385-40b3-9fec-b4248f18b0b3` | `3a349455-7926-45ac-97b2-138d2ee876e9` → `993d01d4-ba2e-4151-88c8-48d876386275` |

两条后轮的 `comparison_result_id` 均为本 Case 首轮 Result。前轮链接来自冻结 manifest/C1 和任务尝试，Run 表没有虚构 `previous_run_id` 列。旧 Run 按自己的 `run_members` 核对，当前 Case 范围另核。首段 **1037 个文件 SHA 全部不变**；旧任务、尝试、Run、Result、步骤、工件及材料逐值保留，最终实际 PG 再读取与保存快照一致。

## 验证与版本边界

- [48 项定向检查](direct-tests-final.txt)及 Ruff、OpenSpec strict 通过；复用首段、状态、保存读取和源码包检查，只新增直接追加边界。
- 独立预审发现并修复 AP-R1：范围已扩展却无新 Run 时，必须记录 `no_new_case_run_for_current_scope`，旧 Result 不能掩盖后轮缺失。固定范围的合法 no_changes 不受影响。
- 独立预审发现并修复 AP-R2：四份连接配置摘要必须与前段真实 preflight 一致。同一路径改变目标/Topic/库表时，发送前拒绝；前段 preflight 也纳入冻结复验。
- 真实两段运行使用 [freeze02](source-freeze-02.json)。AP-R2 在运行期间补完，**不宣称当时运行了新 guard**；两段实际 preflight 摘要一致，最终当前代码实读连接后执行该 guard，[补验通过](post-implementation-readback/connection-binding.json)，0 新投放/业务写入/模型。[最终源码冻结](source-freeze-final.json)明确两文件差异。
- [测试模块第三轮实现复核](../test-acceptance-append-20261117-01/independent-review-03.json)和[第四轮实际结束复核](../test-acceptance-append-20261117-01/independent-review-04.json)均已通过，分别保留源码/受控边界与真实执行、静态、收尾核对。

实际 8 个尝试的时间区间核得并发峰值 **1**，末尾 **0**。CLI 没有新增任务槽或第二套队列；现有联合调度负责限额。当前验证是显式追加与 check，未等自然 4h/6h 周期，也不是恢复/压力矩阵。

## 模型与保留问题

[13 次实际输入输出索引](model-io/index.json)按 request artifact 区分原件：A×2、I×2、C3×4、C6×4、Deep×1，均 `stop`，合计 **109995 tokens**，usage 无未知、费用未知。输入中本次扫描的 tenant_uid、租户 UUID、批次及测试控制标记无命中；后台租户和来源关联保留。01 另有 2 次/4013 tokens，**本轮两批合计 15 次/114008 tokens**，不隐去失败批消耗。

四份 Case Result 均为 `accepted / uncertain / partial`。C3 结构与范围检查通过不代表正文准确；C6 共 **9 项引用诊断**继续后置：首轮两案各 1 项已答问题缺来源；整案后轮 1 项成员来源范围不符、1 项比较依据不足；固定案后轮 3 项重复来源、2 项成员来源范围不符。原答和判断保留，没有为这些质量问题反复采样或阻断流程。完整[质量与来源诊断](retained-diagnostics.json)保留 C2 来源未接、工具预算保留等原因；未接/未查不记查空或安全。Deep 的一次正常调用属于本案实际路径，不核销 D5/D6 未验边界。正文质量仍未全面验收。

## 展示、收尾与下一步

通过既有 `update_processing_audit.py` 将两案追加到[本机静态查阅](../../../../deliverables/investigation-validation-20261106/processing-audit/index.html)，51→53，旧记录与旧页面 SHA 不变；两案两轮 ID 均可在新页面原件中找到。[静态核对](static-verification.json)。导入使用 `static-export-02`，包含固定案实际关联的事件读取；早期派生目录 `static-export` 未导入。未做新浏览器验收，21/4177 现网仍是已发布版本。

[本轮本地进程、专用模型转发及依赖已停止](cleanup.json)，两批数据库/Topic/湖/Redis 分区与全部证据保留。仅关闭 3c.2；3c.3 交互/全会话报告、3d Docker 封装、任务4及统一发布继续按 OpenSpec 分步推进。
