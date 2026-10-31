# r10 完整原始告警与实际 Tool 查询核验

源码 `51086a4` 已部署至 21 独立调查 API。唯一 Run `4f094ed4-b4f9-5db9-8cc2-b5f8c781858e` 为 **completed/partial**；功能合同核验通过，**报告语义未验收通过**。本批没有重试或第二个 Run。

两条已有 Office/网络演示告警的 description 与 raw_event，在冻结证据及全部三次模型请求中逐字段一致。raw_event canonical UTF-8 长度分别为 219、251 字节，均未截断；“完整”指现有已存原文，不代表完整厂商载荷、脚本内容或真实攻击事实。

| 实际步骤 | 核验结果 |
| --- | --- |
| 第一次模型调用 | 原生 process_activity，参数 DEMO-FIN-11 / limit 20 |
| 第二次模型调用 | 原生 network_connections，同主机、同固定窗口 |
| 第三次模型调用 | 首次正式报告使用 strict JSON Schema；正文合法，无纠错 |
| 成员映射 | 模型 A1/A2 映射至原两条 UUID；无遗漏或重复成员判断 |
| 原始输入 | 两条 description/raw_event 在三次模型请求全部完整；旧 AI 摘要省略单独标明 |
| 实际数据库 | 两个 query_id 均有 ClickHouse QueryStart/QueryFinish，exception_code=0；各扫描6行，匹配0行 |
| 历史复用 | refresh_queries=true，无 previous_run_id，复用0、H证据0 |
| 结果持久化 | POST/GET结果一致；12事件14工件；20 HTTP、42原始文件hash核对 |
| 用量 | 3模型调用、2真实Tool、10292已知tokens；3调用未定价，不能计免费 |

查询窗口为 `2026-10-25T03:29:00Z` 至 `03:34:00Z`，结束时刻不含。事后另按同租户和两条 source_event_id 只读查库，也未找到行；这些核验查询没有加入模型或改写本次报告。不能据此断定记录为什么不存在。

报告仍有三个具体问题：

1. relationships[0].basis 写“高置信度告警矛盾”。成功空查询只能说明本来源、本范围没有返回匹配记录，不能反证原告警。
2. summary、成员判断、未决问题及缺口猜测近似重放、采样、离线推断、日志未持久化、阻断或丢失。部分使用“可能”，但没有来源支持；缺口文字还把日志缺失当作既定原因。
3. 出现无来源的“粉红路径”和 pass_process_activity / pass_network_connections 名称，实际工具名不含 pass 前缀。

本次正确的有限结论是：**原文声称同主机 Office→PowerShell→网络连接；两个实际查询均成功但没有匹配记录，尚不能独立证实或反证该行为及因果关系。缺少记录的原因未知。**

下一步应聚焦空结果的推理边界及实际原始事件与告警的对应数据。不能通过补造湖数据、隐藏缺口或重复调用挑选好报告来完成验收。本轮停止在已要求的一次真实调查，OpenSpec仍16/17、5.3待办。

部署首次因打包源码权限过紧而启动失败，尚未调用调查。只修正应用目录0755/文件0644后，同一源码重新构建成功；首次失败保留。共享网关、core、agents、配置和已有开发Key保持。

- [原始报告（未人工改写）](final-report.md)
- [机器核验](verification.json)
- [ClickHouse执行证据](clickhouse-query-proof.json)
- [请求、响应与所有步骤](results/summary.json)
- [完整回执](../../../investigation-structured-report-20261031.json)
