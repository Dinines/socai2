# Case Finding 角色验收证据

本批对应 [align-case-finding-evidence-roles](../../../../openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)。真实本地数据库、测试替身、真实模型、离线回放与生产读取分别记录。

| 位置 | 用途 |
| --- | --- |
| `baseline-replay.json` / `candidate-replay.json` | 前批三份原失败的只读回放，保原文 hash；0 模型调用 |
| `roles-tests-01.xml` / `contract-tests-01.xml` | 17 项专项／合计 86 项相关测试通过 |
| `local-pg-01` | 时间上下文被误选为角色错误的两项测试断言失败原件 |
| `local-pg-02` | 两项完整真实 PG 场景通过；模型、数据湖为替身；29 表／462 列不变 |
| `real-model-01` | 冻结计划、调用 intent／回执、实际 wire／原答和最终数据库、GET 导出；4 次真实模型调用 |
| `real-model-replay.json` | 当前真实 C3/C6 原答的生成／接收回放，原件保持 |
| `execution-summary.json` | 6 条 observed 支持逐项角色及成员核对、38,844 reported tokens、52 GET／3,225 字段检查 |
| `published/model-01` | 4177 使用的校验清单和原件副本；与本地导出同内容 |
| `static-manifest.json` | 3 份记录、233 个文件的静态发布清单；实际新增 3 份至 29 份，234 HTTP 核对通过 |

真实 Run 终态 completed/partial，C6 采用，但正文质量 **NOT_PASSED**。原 `execution.json` 的 running 是启动回执，终态以导出的 Run 为准。没有独立业务真值，不报准确率；费用未知不写零。原始材料为已存演练材料，新身份仅隔离本轮验证，不构成已核实业务授权。

独审 ACCEPT 后统一发布 21 r6；365 GET／16,820 字段检查、原生产数据及五项继承服务容器保持，详见 [delivery-summary.json](delivery-summary.json)。`runtime-probe-initial.json` 保留首个只读探针对显式 Env 的错误假设；`runtime-after.json` 改从实际应用 settings 核开关，没有更改运行配置。源码与包逐文件核对见 [source-release-match.json](source-release-match.json)。
