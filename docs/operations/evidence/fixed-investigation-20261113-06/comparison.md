# 固定调查三场景对照结果

三个场景已执行，共13次真实模型调用、183,058 tokens。三个Run均正常结束，三个Result均为 **rejected / unavailable / partial**，当前判断均为空，没有形成可采用的综合结论。请求、模型原答、拒收、局部保存、H版本和GET读回均已留存；这批证明了真实输入及失败保存读取，不能宣称模型质量通过。

## 共同材料与变化

同一组三条合成告警：06:38:27登录成功，06:38:47启动PowerShell `Get-LocalUser`，06:39:07建立TCP出站连接。共用主机/账号并不直接证明同一会话或因果。`process_start success`只限定进程启动，不能证明命令完成、读到用户清单或传输了数据。复用固定05批A/I：登录A原失败保留，另外两条有效A及partial I保持，没有重算前序。

预先定义的变化、H原文和预期见[原配置](config.json)。B01无H；H01在同Case新增材料复核意见并指定B01比较；H02另建Case，仅进程成员有明确标注的模拟业务反馈。H01还带有前轮历史、比较条件及不同查询时刻，不能当作只改变H的受控A/B。H02明确否认真实生产授权，所以只能检查归因和范围，**不能证明通常业务场景下的有效授权陈述已被正确采纳**。

## 逐例结果

| 案例 | 实际调用与总tokens | 实际响应及仍存问题 | C6接收 |
| --- | --- | --- | --- |
| B01 无H | C3×2、Deep×1、C6×2；74,030 | 最终正文列出登录/启动/连接三类事实；仍从名称和synthetic标签推自动化。C3纠正成员错配后遇观察原值容量约束，局部结果保留；C6两次缺最终成员依据 | 两次`delivery_source_coverage_missing`，拒收 |
| H01 核查反馈 | C3×1、Deep×2、C6×1；44,069 | C3引用校验通过；C6明确人工材料不是授权，并区分进程启动和命令完成；仍重复名称→自动化推断。指定B01不可用，却把当前A/I/C3/Deep当成旧基线回答unchanged | `comparison_not_available`，拒收；当时缺纠错诊断 |
| H02 单成员模拟陈述 | C3×2、C6×2；64,959；未派发Deep | H版本/进程范围进入模型；C6明确未确认登录和出站连接。C3两次answered问题无来源，C6影响块声明三成员却无来源；正文仍把时间邻近写为“完整的行为链”并在限制中承认无直接链路证据 | 两次`delivery_source_coverage_missing`，拒收 |

上述“C3引用校验通过”仅是格式/引用检查，不证明正文有据。三例正文虽均写待复核，程序仍须拒收有范围/依据错误的最终交付，不能直接把模型自由文本变成当前判断。

原答中的代表性差异保存在以下字段，可直接逐字核对：

- B01最终`analysis.questions[authorization]`称未发现演练标签，但原材料含synthetic；并把查询失败/未执行混写为查空。标签存在也不等于业务授权。
- H01最终`analysis.questions[authorization]`明确引用H且说明不是业务人员授权；`impact`明确数据读取/外传未知。`comparison`却将本轮前序判断当成指定旧Result，属本次真实拒收。
- H02最终`analysis.questions[authorization]`明确“仅模拟确认PowerShell命令，未确认登录和出站连接”；`member_relationships`中的行为链断言仍超出关联证据。命令结果、业务损失保持未知不抵消其他无据正文。

持续正文质量问题保持M01/M02 **NOT_PASSED**，本批完成后停止采样。没有为通过而补引用、改答案或放宽接收。

## 知识与运行条件

三例正常C2都尝试知识查询，向量集合可读，但嵌入POST均返回503，`knowledge_embedding_request_failed`；没有取得本轮新知识正文。资产查询为空，其余来源的未查/缺连接与知识失败分别留在原回执；低优先来源因C2为后续取证预留工具名额被跳过，是原配置行为。

因此本批不能评价“正常检索知识进入模型后的收益”，也不能据此否认固定05批已有知识传递证据。精确来源回执在[程序对照数据](comparison.json)，另存一次[只读诊断](knowledge-query-diagnostic.json)；没有导入、重建索引、重启服务或为了可用性继续跑模型。

三个Run均未因模型调用次数、token或时限预算停止，保留原6次/131072tokens/1500秒限制，未提高预算。总量183,058是三Run合计；费用未知，不记为零。模型路由见[实际路由核验](model-route.json)；不做不同模型或温度的比较。

## 实际程序修正与验证

H01暴露“不可用比较基线”在生成/纠错端与严格接收端不一致。已在全部真实调用结束后离线修正：共享指定Result可比性判断，不可比时生成Schema仅允许`not_comparable`及非空说明；错误答复提供comparison根字段、原值和允许值，进入原有最多一次纠正。可比Result、初次无比较、严格接收、来源角色及存取合同保持。

4项定向检查通过。用H01原请求/原答重放：[新反馈](comparison-fix/C6-feedback.json)555字符；旧Schema允许的unchanged被新Schema拒绝，严格接收仍报原错误，局部分析保留、最终结论不能采用。[离线回执](comparison-fix/summary.json)核原件及来源映射不变；[纠错消息预览](comparison-fix/C6-correction-preview.json)没有发给模型。**新纠错的真实模型效果尚未验证，原H01仍拒收。**

B01/H01业务执行完成后的验收驱动先后误处理read_run的dict/嵌套Pydantic返回值，原`execution.json`异常保留。最终按HTTP正常序列化修正，独立只读快照确认两Run已结束并完成GET，不重派模型；H02使用修正后的驱动。驱动三个版本、实际plan和失败回执均在[重放清单](replay-manifest.json)。汇总脚本首次读取B01旧intent缺少plan_file也已按其已保存hash适配，只重做离线汇总，没有业务副作用。

## 实际模型输入与重放

以下正文由程序从实际请求逐字导出，完整messages/Schema、所有初答/纠正原答及source_map在各例calls和export中。字符数只计主业务消息，系统、Schema、工具及一次纠错消息另存，不用压缩率代表质量。

| 案例 | C3实际输入 | C6实际输入 | 原答与保存核对 |
| --- | --- | --- | --- |
| B01 | [9,141字符](flow/B01/review/call-01-C3-input.txt) | [15,979字符](flow/B01/review/call-04-C6-input.txt) | [最终原答](flow/B01/review/call-05-C6-answer.txt) · [逐调用回执](flow/B01/summary.json) |
| H01 | [10,217字符](flow/H01/review/call-01-C3-input.txt) | [18,868字符](flow/H01/review/call-04-C6-input.txt) | [最终原答](flow/H01/review/call-04-C6-answer.txt) · [逐调用回执](flow/H01/summary.json) |
| H02 | [9,696字符](flow/H02/review/call-01-C3-input.txt) | [17,083字符](flow/H02/review/call-03-C6-input.txt) | [最终原答](flow/H02/review/call-04-C6-answer.txt) · [逐调用回执](flow/H02/summary.json) |

`summarize.py --scenario B01`（或H01/H02）离线重新核对请求/原答与数据库快照；`compare.py`核三例材料/前序和当时业务代码一致、各自实际plan及驱动hash；`replay_comparison.py`复现原拒收和新诊断，均零网络/模型调用，已有文件不同则报错。各例旧summary的plan_sha256指原始基准计划；**实际执行计划以execute-intent和replay-manifest逐例映射为准**。

真实重放使用已保存完整请求和新的批次/调用身份，不能复用已结束或unknown的Run/operation key。业务源码在`source-replay.json`所指Git基点加原补丁可还原；三个plan保存实际源码摘要。修正后的程序版本另见comparison-fix，不能与原运行混称。当前数据库有后续历史，重新查询所得输入不再自动算同材料对照。

本机4177静态包已追加三份快照，75→78；在线服务未新增发布。本批不改HTTP字段或数据库表、不部署模型代码、不实现流式或H自动重算。主调查31/41保持；下一步优先处理固定流程仍未通过的可采用综合结论，已登记正文问题无需反复采样。
