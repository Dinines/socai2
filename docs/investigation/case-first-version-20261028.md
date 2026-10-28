# Case创建后的调查初版

2026-10-28。以用户最新范围为准：从**已有Case及其成员**开始，完成调查功能；Case如何触发、自动目标选择和F5接线不属于本次目标。事件层继续保留汇总与AI概况，不增加另一套调查循环。

初版代码提供：选定范围和材料预览→发起调查→模型按需查询进程/网络→保存步骤和证据→结构化报告与Markdown→历史读取→追加问题形成新Run。当前交付为独立API v2代码，不是已部署服务或前端页面。

## 入口与输入输出

路径前缀为`/api/v2/investigation/cases/{case_id}`。Case为真实案件UUID，已有成员来自`Case.alert_ids`。Case创建/加成员可使用已有案件管理接口或[F4](case-linking-20261028.md)，不要求自动触发链路先完成。

| 方法和后缀 | 输入 | 输出与作用 |
| --- | --- | --- |
| `POST /investigation-context` | start、end；可选question、selected_member_ids | 当前Case材料、实际可读成员、缺失成员、Tool定义、执行限制；不创建Run、不调用模型或查询工具 |
| `POST /investigate` | 上述范围＋operation_key；可选previous_run_id、refresh_queries | 同步执行一次调查，返回Run、固定范围、报告及读取链接 |
| `GET /investigations` | limit、cursor | Case调查历史；含previous_run_id、结果/步骤/下载链接 |
| `GET /investigations/{run_id}` | Case与Run ID | 当前状态、固定范围、步骤摘要、已存结果或null |
| `GET /investigations/{run_id}/steps` | after_seq默认0；limit默认20，1–50 | 已保存步骤按seq升序，items及next_after_seq；无下一页为null |
| `GET /investigations/{run_id}/steps/{seq}` | 正整数seq | 对应步骤的实际输入或输出data，以及时间、类型、摘要 |
| `GET /investigations/{run_id}/report` | Case与Run ID | 已保存的UTF-8 Markdown附件；尚无报告返回409 case_report_not_ready |

所有入口继续使用已有用户身份及Case/Alert读取权限；启动另需investigation:run。没有新增权限体系。Case或当前租户/Case下的新版Run不存在返回404；未知步骤404 case_analysis_step_not_found；参数校验422。

材料预览与实际启动使用同一范围模型：带时区的正时间窗口，最多7天，左闭右开；selected_member_ids省略时选择当前Case全部成员，指定时为非空、无重复的成员子集。预览不是快照承诺，实际启动重新读取并固定本次材料。

## 从已有Case到报告的例子

以下ID和时间是调用示例，不是生产运行回执。假设C1已有A1可疑进程、A2异常外联两条成员。

先向`/investigation-context`提交：

```json
{
  "start": "2026-10-28T01:00:00Z",
  "end": "2026-10-28T02:00:00Z",
  "selected_member_ids": ["00000000-0000-0000-0000-000000000001"],
  "question": "核对可疑脚本的行为证据及缺口。"
}
```

返回context含Case标题、完整/选定/实际读取成员、主机、窗口、问题、A类告警和T类分诊材料；tools在事件湖已配置且成员有主机时列出process_activity与network_connections的名称、说明、参数schema。没有可用工具时返回空列表，不伪造支持能力。

随后给相同范围添加新的非零UUID operation_key，POST到`/investigate`。模型按需选择工具，程序固定tenant、主机与窗口，保存Tool结果并以同一tool_call_id传回下一轮模型。正常形成结论或因限制停止后，返回run_id、status、scope、result及result_url/steps_url/report_url。POST在本请求内执行，不返回后台202。

通过steps_url可逐步查看：

| 步骤类型 | data实际保存的内容 |
| --- | --- |
| case_analysis_started | 本Run固定的Case成员、窗口、问题、已有材料 |
| case_analysis_model（准备） | 发给模型的messages及tools定义 |
| case_analysis_model（返回） | 模型可见回复、tool_calls及usage；不包含隐藏推理 |
| case_analysis_tool（准备） | call_id、工具名、解析后的arguments |
| case_analysis_tool（返回） | call_id、完整evidence与发送给模型的model_message；可区分成功空结果、失败、截断与复用 |
| case_analysis_finished | stop_reason和completion |

准备和返回各是一条步骤，依靠seq、call_id及消息中的tool_call_id核对。步骤GET只读已保存工件，不重新执行模型/工具。report_url返回与result.markdown一致的已存报告，可保存为`.md`。

## 追加问题与重新查询

向相同Case的`/investigate`提交新operation_key，指定previous_run_id、新question以及原成员/窗口：

```json
{
  "operation_key": "00000000-0000-0000-0000-000000000102",
  "previous_run_id": "00000000-0000-0000-0000-000000000101",
  "start": "2026-10-28T01:00:00Z",
  "end": "2026-10-28T02:00:00Z",
  "selected_member_ids": ["00000000-0000-0000-0000-000000000001"],
  "question": "继续核对脚本启动来源，现有证据是否足够？",
  "refresh_queries": true
}
```

- 前次Run必须属于当前租户及同一Case，且已有终止报告；running或无报告为409 previous_analysis_not_finished。成员集合或窗口不同为409 followup_scope_changed；要换范围时不指定previous_run_id，作为独立新调查。
- 前次报告作为H1历史判断提供给模型，标明原Run与范围；原报告中的编号仍属于原Run，不能当成本次新查询证据。旧报告不会被新问题覆盖。
- refresh_queries默认false。追加问题时，仅在当前材料指纹与原Run一致、Tool及参数一致且历史结果可用时复用，并保留reused_from。原Run无material_hash时不复用。普通新Run继续按原相同来源指纹规则复用。
- refresh_queries=true表示本次跳过历史查询缓存；模型仍决定是否需要调用Tool，不代表必然发出查询。新调用结果、用量和缺口属于新Run。
- 同一operation_key及同意图只读原Run；更换问题、前次Run或refresh_queries须使用新key。省略新增字段的旧请求保持原意图格式，不因升级变成冲突。

历史列表和结果详情都返回previous_run_id，可沿此字段查看前后两次调查。初版不提供恢复中断Run、撤销、自动续跑或自动处置。

## 运行与完成范围

独立入口：`app.investigation_v2.case_analysis_api:create_app`，同时已由program_result/start组合factory继承。配置和既有数据库依赖沿用[F3说明](case-investigation.md)。本轮使用原ledger的Run JSON、步骤和报告工件，不新增表或迁移；已有Case直接调查不依赖F4迁移121。旧服务main未自动注册这些新路由。

验证命令：`python -B -m unittest discover -s services/api/tests -p test_case_analysis_api.py -v`。

7个直接用例通过：原完整分析/查询/报告链路、空结果与失败、适用历史查询复用、未知用量停止，以及本轮新增的预览/步骤/下载、追加问题/重查/旧报告保留、追加范围/前次未结束拒绝。另验证1个受影响的Case历史列表用例通过。使用实际ASGI路由、模型HTTP协议、工具SQL及ledger读写代码，PG、模型和事件湖由替身提供；不宣称真实数据库、模型自主选工具或业务判断质量已经验证。没有扩展恢复、可用性或压力测试。

初版能力止于Case内的主分析和已接入的进程/网络工具。产品HTTP Tool、专项Deep、额外数据源和前端接入仍按实际需求后续增量；不把它们写成已完成。Case创建/触发政策与F5自动入口依用户最新要求移出本次目标。
