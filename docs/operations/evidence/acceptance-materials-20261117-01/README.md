# 任务3a：材料转换与计划的本机验收

2026-11-17。对应[统一设计§12.8](../../../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#128-任务3整体实施顺序与3a材料入口2026-11-17)。只实施离线材料入口；业务连接、Kafka投放和模型调用均为0，未构建Docker镜像、未发布21，任务3整体未完成。

[使用入口](../../../../tools/testdata/ACCEPTANCE.md)提供同一个`acceptance.py convert / inspect`。场景、profile和转换recipe的Schema及示例已落地。报告由程序读取材料生成，不靠模型计数或写验收结论。

| 实际输入包 | 转换、保存、重新读取的结果 | 未执行边界 |
| --- | --- | --- |
| 已冻结干净streaming v2 | part1=3告警/12独立context，part2=1告警/1context；17条记录逐字段保留，来源关系与整事件/固定告警两Case计划可读 | 默认只选part1；两段均not_executed，旧ID/时间保留，发送前必须实例化新执行身份 |
| 显式选择的两个中性模板 | 2条告警、0独立context；5条内嵌telemetry仍只保存在告警材料中，2条记录原值保持 | 无Case计划，查询分支not_covered，不能称湖中查空或已供模型查询 |

[实际转换与读回](direct-readback-01.json)记录两套命令、退出码、数量和核对结果；[输入hash](source-inputs-01.json)确认两个源目录均未修改。转换器按旧manifest核原字节hash，不要求历史源码或candidate仍等于当前环境；不读取旧作者答案/控制回执来拼发送材料。

两包的程序计划与单独inspect逐值一致：

- [streaming计划](packages/streaming/plan.json)、[逐记录来源](packages/streaming/conversion.json)、[再次读取](streaming-inspection.json)。
- [templates计划](packages/templates/plan.json)、[逐记录来源](packages/templates/conversion.json)、[再次读取](templates-inspection.json)。

[直接检查](local-checks-01.json)：16项材料检查通过，覆盖真实两包、原值/hash、旧源码/环境脱钩、数值排序、重复身份、必需时间、控制字段、未来引用、Case选择、opaque来源、前段context及默认选择。网络调用在直接检查中禁用，连接文件不会被读取。4项既有包检查通过，含在源码树外运行新CLI转换与再次检查；这是离线源码包验证，不是Docker运行验证。Ruff与OpenSpec strict通过。[实施源码冻结](source-freeze-01.json)、[包验证源码](package-check-source-01.json)保留。

[测试模块独立复核](../test-acceptance-materials-20261117-01/independent-review-01.json)通过：16个源码摘要一致，两包19条业务记录原值/来源保持，另行运行转换/inspect与无part1/显式选择检查；Python审计钩子未观察到网络、子进程、连接配置或历史答案文件读取尝试。该结论只覆盖3a离线材料入口。后续3b负责新身份/实际连接及单段发送→保存→读取，3c负责交互追加与实际报告，3d负责Docker封装；新小场景完整链在任务4验收。旧模型引用/正文问题仍保留原结论，本步没有采样或修复这些质量问题。
