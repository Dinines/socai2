# 展示数据与取数参考

[返回导航](../guide.html) · [字段对照](../docs/data-mapping.html)

页面运行只加载根目录 data.js 和 replayed-alerts.js。这里的 JSON 是方便前后端阅读、查字段的副本，修改 JSON 不会改变页面。

| 文件 | 内容 / 用途 |
| --- | --- |
| [reference-data.json](reference-data.json) | 原设计数据：52 条告警、12 个事件、12 个 Case 及实体等 |
| [replayed-alerts.json](replayed-alerts.json) | 6 条实际测试处理结果的完整前端投影及其实体，和 replayed-alerts.js 中数据一致 |
| [alert-database-sample.json](alert-database-sample.json) | 这6条 public.alerts 的原始字段白名单及提取的 Fusion 来源 / 事件关系；保留字段名与空值，不是整库备份 |
| [explain-responses.json](explain-responses.json) | 当时6次 Explain 请求的返回，含 HTTP 状态与告警 ID；本批 llm_used=false |
| [replay-comparison.json](replay-comparison.json) | 20 / 21 的分诊、评分、状态、调查完整性、最终结论对照 |
| [alert-read-queries.sql](alert-read-queries.sql) | 使用本批6个告警 ID 的只读查询示例，需要后台已有授权的数据库连接；浏览页面无需执行 |

数据日期为 2026-10-25。6条输入来自20测试场景，在21从Kafka实际处理，不是真实攻击；原52条是设计样例，二者不合并当作线上业务数据。原库 is_synthetic 标识存在历史缺口，不能据此把测试输入认定为真实攻击。

6条实际处理记录：

| 告警 | ID | 前端状态 |
| --- | --- | --- |
| Office启动隐藏PowerShell | 4c71eec2-77da-5b81-b68a-72801d55ea24 | 进行中 |
| 脚本进程建立HTTPS连接 | f7af404b-26a6-5d15-bd6c-3a872bdaf451 | 进行中 |
| 进程读取LSASS内存 | c929a0c7-69b5-5617-b830-a701e8bae72f | 进行中 |
| 同账号SMB远程服务访问 | 6b9b6217-fdd6-59a0-b02f-93267050cd5f | 进行中 |
| 服务账号读取并生成归档 | 6373220a-2f25-541e-ab89-9c3a2e611140 | 进行中 |
| 归档进程上传字节 | 4eb06dee-c5a0-5f08-ace7-08caa2952db5 | 已解决 |

20/21分诊分类4/6相同；5条进入Graph的记录均为partial，最终结论20为confirmed_incident、21为needs_review，不能宣称结论完全一致或调查质量通过。

本批实际数据缺少资产库存关联和负责人，所以资产标签为空、负责人未分配；原始实体用于展示但不伪造资产台账。事件、Case 页面仍沿用设计样例，实际告警的事件 UUID 不自动打开样例详情。

包内不包含账号口令、API key、完整模型提示词、私有数据库备份或清理命令。只读SQL不是接收方必须运行的步骤。本轮仅整理已有本地文件，没有重新访问或清理20/21。
