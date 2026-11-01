# r11 完整原文、对应湖事件与唯一调查复验

2026-11-01：r11 已部署，数据与真实 Tool 查询链路通过，最终报告未通过。Run `22b48b78-3716-5a64-994f-788d020dc760` 为 `failed/partial`，停止原因为 `invalid_or_unreferenced_conclusion`。本批已结束，不重试挑选结果。

## 实际输入与执行

用户明确选择新建标记的测试样本并保留旧数据。专用 fixture 租户 `53824f24-d1d4-5820-8147-f6cfda8a1247` 新增 2 条告警、2 条湖事件、1 个 Case，实际发起 1 次主调查。数据库告警 `is_synthetic=true`，标题、raw 和 Case 描述均声明测试数据；未触发采集、检测、分诊或生产端点行为。

Case `5fbb643b-975b-4798-8729-801b50ba956f` 的两条原文分别陈述 Office 启动 PowerShell 和随后 TCP/443 连接。时间窗口为 UTC 2026-10-31 16:00–16:04，主机 `INV-R11-FULL-RAW-01`。原始材料只含已固定的示例内容；没有脚本正文、审批记录、应用协议或恶意目的的事实依据。

| 项目 | 真实结果 |
|---|---|
| 完整 raw | canonical 371 / 425 字节；冻结材料及全部 4 次模型请求均完整、未截断 |
| 进程 Tool | 本次查询返回 1 条 class 1007、action=start、outcome=success 记录，event_id 精确对应 A1 |
| 网络 Tool | 本次查询返回 1 条 class 4001、protocol=TCP、dst_port=443 记录，event_id 精确对应 A2 |
| 查询证明 | 2 个正式查询均有 ClickHouse QueryStart/QueryFinish，read_rows=2、result_rows=1、exception_code=0 |
| 历史复用 | 0；两项 required_tools 使用原生 function call，不能据此声称模型自主选择了任意工具 |
| 模型调用 | 4 次完整回复，12,728 已知 tokens，4 次未定价，不能称免费 |
| 输出结构 | 首份及纠错报告均通过保存的 JSON Schema；成员 A1/A2 各一次，未出现 UUID 重复问题 |
| 最终结果 | 两份模型结论均被协议校验拒绝；保存的是带真实证据与缺口的失败报告，成员 not_assessed |

另有 2 次入库后 Tool 预检查询，各返回 1 行。它们与正式调查的 2 次查询 ID 不同，没有作为历史结果复用。正式查询 ID 为 `323d0bf1-13a7-48a0-92dd-f22c8bebdf51` 和 `50a8fbb5-0f20-4ead-bc13-226ab632a2d4`。

## 拒绝原因与报告质量问题

1. **首份报告只触发一个协议校验错误。** `member_assessments[1].summary` 写“未决点需确认协议为 HTTPS/TLS 及目的合法性”。当前校验未将这种待核措辞识别为明确不确定，要求将协议问题移到 gaps。该句也没有写清“是否”，不能把它解释成协议已获证实。
2. **纠错提示进入了报告正文。** 第二份 summary 出现“在总结中必须明确指出……不得……”等写作要求，gaps 直接输出内部错误码 `unobserved_application_protocol_use_gaps`。这属于内容质量问题，JSON Schema 无法排除。
3. **协议校验存在真实误拒。** 保存原答的正则重放确认：`HTTPS/TLS 状态尚未确认`、带空格和结束引号的 `'HTTPS/TLS 尚未确认'`、`'HTTPS尚未确认'` 未被有限句式识别。当前后置句式没有覆盖空格/状态词，边界也未包括引号。同一字段还混有“无握手特征”等未被识别的表述，不能只修一处就认为整份报告通过。
4. **模型独立编造和混淆来源仍然存在。** 首答把 Case 描述称为“告警原文”，又称 synthetic 标志“仅见于 case_material”，实际两条 raw 都有 `synthetic=true`。纠错后将 documentation address 延伸为“文档服务器”，断言“故意缺失或本环境未集成”，提出无来源的“奇偶校验工具”；`missing_evidence` 甚至只有 `Expect `。这些都不是查库失败造成的。
5. **关系判断仍不稳定。** 首答称共同主机、账号和时间连续，却将 shared_context 标为 not_supported；纠错改为 supported behavioral_link，并称“合成攻击链”。来源支持示例进程与连接的观察及原文中相同 PID 的陈述，不足以证明攻击目的。

因此，格式与成员引用改善已得到这次样本的实际支持；不能通过放宽协议校验来宣称报告质量通过。本轮均为非空结果，也没有同源 T 分诊摘要，故未直接验证 r10 空查询推理和摘要去重在真实模型中的效果。

下一功能修复应限定为：让协议校验接受明确的不确定语义及常见空格/引号；纠错提示只用于修改错误字段，不进入用户报告；继续区分告警原文、Case 描述、湖内列和未知原因。当前没有新增 r12 实现或再次派发调查。

## 部署与保留情况

发布提交 `a543ad6d043c35ec17fe792885ab48a11d325e4e`，功能修复 `49a04eb73d765b42bb23ea0ae0b2cfc4a50a1845`；镜像 `sha256:59d9fe097588dad6c019797a9ba635f5f2126ae66ffddbdc3e466447ebc3ffcb`。实际工作目录 `/opt/investigation/app` 的 472 个源码 hash 与候选清单一致。第一次核对误读基础镜像的 `/app/app`，已明确记录并纠正；不是部署失败。

core、agents、网关及原配置保持；原开发 Key 只读取使用。fixture 租户旧告警整行 hash 前后相同，r10 原报告与历史文件逐字节相同。新数据、失败输出及报告均保留，无删除、历史回填、旧报告改写、预算提高或额外纠错。

记录 16 事件、18 工件，30 个批次 HTTP 请求/响应；另有 1 次只读状态查看，不混作已保存完整响应。取回 75 个远端文件逐字节核验，详见 [verification.json](verification.json)、[post-batch-proof.json](post-batch-proof.json)、[protocol-match-analysis.json](protocol-match-analysis.json) 和 [live/remote-file-hashes.json](live/remote-file-hashes.json)。

OpenSpec 仍为 16/17，5.3 未完成，不归档、推送或合并。
