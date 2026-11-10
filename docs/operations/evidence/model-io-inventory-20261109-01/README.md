# 模型实际输入输出原件

从保存原件逐值提取；0 新模型调用、0 数据库连接。失败和截断按原样保留。

| 环节 | 版本/结果说明 | 完整输入 | 原始输出 | 要求的输出结构 |
| --- | --- | --- | --- | --- |
| 告警分诊：登录 | 21 已部署版本；本次失败，输出截断 | [输入](A-logon/input.txt) | [原答](A-logon/output-original.txt) | [Schema](A-logon/output-schema.json) |
| 告警分诊：进程 | 21 已部署版本；本次引用拒收 | [输入](A-process/input.txt) | [原答](A-process/output-original.txt) | [Schema](A-process/output-schema.json) |
| 告警分诊：网络 | 21 已部署版本；completed，needs_review | [输入](A-network/input.txt) | [原答](A-network/output-original.txt) | [Schema](A-network/output-schema.json) |
| 事件诊断 | 21 已部署版本；整体失败、独立有效局部保留 | [输入](I/input.txt) | [原答](I/output-original.txt) | [Schema](I/output-schema.json) |
| Deep 单问题补查 | 旧业务模式历史实测；answer/unresolved，新输入设计未接入 | [输入](Deep/input.txt) | [原答](Deep/output-original.txt) | [Schema](Deep/output-schema.json) |
| C6 最终分析 | 旧业务模式历史实测；结构通过不代表正文质量通过 | [输入](C6/input.txt) | [原答](C6/output-original.txt) | [Schema](C6/output-schema.json) |
| C3 新版主分析 | 新版格式最近一次真实离线生成；严格校验未通过，有独立有效局部；不是新建业务 Run | [输入](C3/input.txt) | [原答](C3/output-original.txt) | [Schema](C3/output-schema.json) |

每个目录同时保存 `request.json`，可核对消息、Schema 和实际调用参数；输入文本中的消息边界由本导出器标注，消息正文不改写。

C3.reanalysis 是可选入口，本目录没有该环节的新样例；职责和合同见[完整清单](../../../investigation/model-input-output-current-20261109.md)。
