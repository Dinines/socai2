# 3c.1会话状态独立复核

2026-11-17，**第二轮定向复核通过，仅关闭3c.1只读会话状态及下一段候选检查。** 对照第二版冻结清单核14份文件，只有状态实现及对应测试两份文件变化；独立复跑32项相关pytest、Ruff及OpenSpec strict通过。原S1/S2输入逐文件同SHA重放：坏steps、坏HTTP response、孤立attempt.task_id均经CLI保存固定诊断、返回needs_review且无next_part，正常基线仍列part2。已结束unknown及无Run的终态失败保留，不被改成成功。

见[独立复核02](independent-review-02.json)、[检查记录](local-checks-02.json)、[同输入重放](probe-results-02.json)和[历史01/02离线复验](offline-02/verification.json)。真实历史01仍未完成、0发送、无候选；02仍保留Case failed、0 Case Run/0 Result，只按已存终态给part2候选。成功Result的关联校验使用本机续验03自己的快照，未混入21会话。旧失败及所有原回执摘要不变，新增业务连接、投递、模型调用均0。追加时仍须重查实时状态；3c.2/.3、3d、任务4及21统一发布尚未验收。

## 第一轮原结论（保留）

2026-11-17，**需要修改，暂不判定3c.1通过。** 本轮独立核对14份冻结文件并复跑26项定向pytest及Ruff，均通过；两份真实历史01/02回执的离线CLI复验通过，原件字节与输入摘要保持。另做正常基线及三个直接受控变体，复现两项P2缺口。没有修改实现、连接服务、投递或调用模型。

结论见[independent-review-01.json](independent-review-01.json)，源码绑定与测试结果见[local-checks-01.json](local-checks-01.json)。真实历史离线报告为[01](offline-01/status-01.json)、[02](offline-01/status-02.json)，执行与无副作用证据见[verification.json](offline-01/verification.json)。复现脚本为[probe-01.py](probe-01.py)，观察结果见[probe-results-01.json](probe-results-01.json)。受控变化仅写入本目录副本，未改写真实回执。

| 问题 | 直接复现与影响 | 必要修正 |
| --- | --- | --- |
| S1 / P2：坏嵌套回执未按合同兜底 | `acceptance_status.py:95`对steps成员直接`.get()`，`:138`对HTTP response直接`.get()`；真实02副本中仅将steps成员改为字符串，或HTTP response改为数组，均抛未捕获AttributeError。JSON可解析但结构损坏时不能正常给出needs_review。`observe_part`未捕获此异常，CLI也仅兜底ValueError/OSError | 对必要嵌套类型直接检查并返回固定诊断/原件路径，或在该读取边界做窄范围兜底；不给next，不回显原始内容，不修改旧回执 |
| S2 / P2：未核任务—尝试关联仍给准入 | `acceptance_status.py:105`起只核集合/终态；把真实02一条已结束attempt的task_id改为不存在的合法UUID，其余原值不变，结果仍closure_verified=true、waiting_append、next_part=part2。该快照已无法证明该Run来自本会话有效任务 | 最少核task→attempt→Run及Result→Run/主体的实际关联与必要租户/主体一致性。不一致应needs_review且无next；不新增全表/模型正文校验框架 |

已通过的范围：未执行材料不填实际身份；按声明顺序与首段选择要求给候选；已有空目录/未完成/绑定错误/未决ACK和HTTP意图不自动重发；结束未知Run在已结束尝试下保留unknown；报告外置且独占新文件；源码包在树外可运行status。实际01保持incomplete、0发送、无next；实际02保持completed_with_issues、Case task failed、0 Case Run/Result并候选part2，没有混入本机续验03结果。socket尝试和连接文件读取均0，未导入执行/连接客户端入口。

当时要求修正后只重放上述直接边界与必要受影响检查，保留本次失败结果。现修正结果见页首第二轮回执；第一轮报告、原复现输入及失败输出保持不变。
