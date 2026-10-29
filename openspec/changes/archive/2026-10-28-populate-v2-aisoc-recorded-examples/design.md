## Decisions

1. source20.json 提供 canonical 告警，final-N.json 提供原场景输入，delivery 和 final-read-verification 提供 Run/工件目录。白名单导出，不携带完整模型提示词或隐藏分析；报告正文原样保留。
2. 本地 Case 使用 local-aisoc20-N ID 和 localCollection 标记，sourceCaseId=null；告警 caseId 维持 null。只按已知 alert_id/run_id 精确关联，incident_id 未知不补。此轮不构造后端事件行。
3. 不同环境/租户的同名主机不能形成“相关告警”候选。实体无库存关系时不显示编造的资产 ID、风险、所属组织。
4. graph_step.payload.step_status=skipped 优先于模板 completed 摘要；材料缺少工件 ID/hash/时间则显示未记录。关系图仅使用既有图快照中与这六告警直接连接的边，作为案件材料，不宣称被 Run 消费或已确认攻击因果。
5. 已有六条21结果和52样例保留。新增数据只在 V2 入口加载，重复加载不覆盖本地操作；本地整理日期与历史运行时间分开。

## Verification

用户在预览时指出“攻击链与路径”没有数据：该页签同时呈现已有案件关系图与告警时序，明确标为历史关系线索，单次Run的未保存/路径跳过状态单列。图中只绘制源快照已有边，告警时间先后与共享对象不转成攻击因果。与当前Case成员/原Run输入分别标识；独立Run可展示同批次共享主机/账户/IOC的相关告警，按源ID限定，不能跨环境补关联。

核对六告警/六 Run/五报告/三本地 Case；原文报告一致、来源身份及空值保留、无 prompt/response 导出、同名跨环境不关联、跳过阶段、目录空值、只读渲染。运行现有 V2 测试并浏览实际 Case 与 Run 切换，结束独审后归档。
