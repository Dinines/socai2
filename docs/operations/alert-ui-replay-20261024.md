# 告警 UI：20 选样、21 重放与真实数据展示

**后续用户修正：页面接入已撤回，恢复原设计、原52条展示数据与交互，去掉本轮新增的快照/缺口/只读标签。三条新增重放数据仍保留在21及离线取数材料；本文件下方为已发生的历史执行回执，不代表当前页面状态。**

2026-10-24。分支 `codex/security-pages-replica`，change `replay-alert-ui-real-data`。用户明确授权从20挑几条测试告警，在21重放并读取真实库表后用于告警页面；缺失信息须标明后续补齐。事件/Case页面取数不在本轮范围。

## 执行范围与结果

先只读核20 `aisoc.public.alerts` 三条、21现有运行配置和预算，再按新source-v1来源身份逐条发往21已有 `socai2.alerts.raw`。原始描述、原始事件和发生时间保留，没有复制20的状态、判定或Run作为21结果。每条先保存intent再单次发送并留ACK，观察完成后才发下一条；没有未知结果重发。

21租户 `f6a5c700-69b8-44fc-8238-609362fb1a9f`，数据库 `aisoc`，schema `public`。最终取数时间 `2026-10-24T13:01:09.146149+00:00` ，原快照现保留于 `.local/verification/alert-ui-replay-20261024/withdrawn-ui/real-alert-data.js`。

| 20 原告警 | 21 canonical Alert | 标题 | 21结果 |
| --- | --- | --- | --- |
| 6b75ea5e-ce23-598c-9e63-90043bcb53f4 | 92070605-0aa0-5e8f-8f0f-4a44222a0146 | Office启动隐藏PowerShell [DEMO-FIN-11] | triaged / true_positive，展示新建（待处理）；调查partial / needs_review |
| d71b5c96-361d-5c21-b234-0b9ad3f854b2 | 56fbc8de-9b62-5ac3-8f85-79dabc7be3a8 | 脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11] | resolved / false_positive，自动分诊关闭，未进入Graph调查 |
| ef9c21f4-d703-5be8-a6d2-63195e09da36 | 59f41776-1dca-5ba0-ad64-a95746ea78a5 | 归档进程向文档地址上传字节 [DEMO-DATA-13] | resolved / false_positive，自动分诊关闭，未进入Graph调查 |

ACK均在partition1，offset18/19/20。对应Run：`1dca2710-fe8c-5e21-b4e3-ef2449dc2d7f`、`0addb8f4-ac13-5406-84b6-02df8b9ca54c`、`29ef7222-3fbf-531c-b87b-a1c82bec6375`，三者执行状态均completed；第一条调查完整性为partial，不能展示“完整调查成功”。总计20事件、28工件，28份UTF-8字节与SHA-256均一致；9模型调用、32667tokens，全部未定价。三条分诊预算预约均responded；这些预约tokens仅计首次分诊，不能当全Run总量。

现有运行配置、预算、旧记录、offset消费策略及服务镜像均未修改；没有重新部署、写湖、真实厂商动作、Git提交或推送。复用已有worker自动链，未新起后台消费者。

## 数据展示与缺口

上一轮列表、预览抽屉和四详情页签曾改读 `real-alert-data.js`，由 `build_alert_snapshot.py` 从本批实际观察数据投影。上述接入现已撤回；新增快照、渲染器、生成脚本均保留于本批私有证据的 `withdrawn-ui/`，活动页面不再加载。完整私有原件留`.local`，页面投影排除提示词、完整模型交换、owner_token等内部材料；模型报告作为不执行的转义文本。原本事件与Case的fixture/localStorage保持独立。

详见[字段合同第7节](../design/alert-ui-data-contract.md#7-21-本次实际字段值与缺口2026-10-24-2101-utc08)及[只读SQL](../design/alert-ui-snapshot-queries.sql)。

- 三条`assigned_to_id=NULL`：显示未分配，区分“字段已有但为空”和“未接登录身份”。分配给我暂禁用，不沿用Alex示例用户。
- 资产关联0行：保留源实体/主机文本，明确资产匹配待补齐；资产标签不能从告警标签代替。`assets`及关联表已有，不宣称系统没有资产表。
- 三条`category=NULL`：待补齐，不把MITRE战术暗中当类别。
- 预生成Explain、统一风险口径、独立检测时间、完整人工变更历史、反馈/分配/响应写回：未接入或待确认，页面显式列出。
- 三条有真实事件ID，无业务Case；不把旧自动Run.case_id（装告警ID）当业务Case。仅文字展示关联，真实ID不链接旧示例详情。
- 发生/入库/关闭与账本时间线按真实时间倒序，没有添加模拟分配或取证成功事件。
- 响应无结构化建议/执行记录，不生成隔离主机建议。第一条真实报告和调查结果保留，并标记模型内容质量尚未验收。
- 只读快照可本地搜索、筛选、排序、导出；刷新只重显快照。管理/反馈/Case关联/发起调查均禁用，不能声称已写回21。

## 保留的质量问题

第一条既有自动调查达到软预算后停止：`token budget exhausted (26309 of 20000)`，调查partial、模型原文未作质量通过。工具返回存在查无行、不支持、LakeQueryError及200字符预览截断；完整进程/网络背景资料本轮未入湖。另两条模型利用文档IP/测试说明判误报，**不代表真实语义分类质量已通过**。原输入synthetic标签在canonical `is_synthetic` 中仍为false；本轮显示为测试重放并记录缺口，不修改服务端补标。

## 验证与证据

私有证据根目录：`.local/verification/alert-ui-replay-20261024/`。

- `source20.json`、`preflight21.json`、`runtime21.json`：20实际行、21预算/运行前提。
- `manifest.json`、`wire-1..3.json`、`validated.json`、`intent-1..3.json`、`ack-1..3.json`：来源/身份/单次发送证据。
- `before.json`、`observation-1..3.json`：重放前后租户限定只读行、Run、事件、工件、关联及schema列；没有覆盖失败或旧记录。
- `direct-checks.json`：3条字段与真实观察一致、28工件hash/字节、Run状态/调用和tokens核对。
- `browser-checks.json`、`overview.png`、`response.png`、`list.png`：浏览器观察，排序前后列宽、筛选/搜索、详情/空值/只读、原始JSON、调查partial与自动关闭分支。
- `npm --prefix prototypes/security-pages run check`：六份JavaScript语法通过。

独立结束审阅由未参与实现的 prototype_end_review 完成：初审发现事件/Case旧告警详情被标成21只读来源的问题；已为旧详情/抽屉显式标记本地原型，并区分顶栏来源。修后窄复核限定 ACCEPT / 0 剩余必须修。独审核源码、投影逐字段、工件hash/bytes、ACK关联、3条×4页签及旧列表的本地VM；浏览器验证由主代理独立完成并留12组观察，控制台错误0、排序列宽相等。

交接SQL已在21只读事务完整执行，结果ROLLBACK（见sql-check.json）。OpenSpec strict通过并按流程归档；真实模型分类和旧调查完整性不属于本次UI交付通过范围。

## 原页面恢复（用户修正范围）

`restore-approved-alert-ui`按已知编辑逆向撤回本轮app/index/styles/package/README增量，data.js、alert-detail.js、icons.js、资产文件与localStorage不重置。浏览器恢复52条原告警、原统计、可用的“分配给我”和管理操作；新标签/缺口面板已移除。新增3条数据库记录及SQL/取数证据保留，本轮恢复不联网或写库。恢复前文件及hash见`withdrawn-ui/restore-manifest.json`。

恢复直接验证：npm check通过；浏览器52条原告警及原详情、可用管理/分配给我、无新增快照标签。独立结束审阅限定ACCEPT / 0必须修，归档`2026-10-24-restore-approved-alert-ui`；新数据仅保留证据，不覆盖当前页面。
