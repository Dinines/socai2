# 数据对照与完整演示回执

2026-10-31，仅4174本地页面、数据、工具和文档。用户要求对齐已有AiSOC实际数据，缺失列文档，完整展示事件/告警功能；未授权也未执行线上重查/重放/模型/写库/部署或Git提交推送。

## 原件及映射

原版20离线重新export与当前aisoc20-data.js逐值一致；17份源文件SHA及21 observed-final SHA共18通过。source-audit.json记录具体ID/缺值/成员。20三事件成员2/2/1，上传告警无事件保持；20六条Explain缺失、库存匹配缺失、事件管理/规则缺失均明列。原始页已有source回退到告警source，缺source_ref呈—，不变更raw值。

## 完整样例

新增page-showcase-data.js及离线构造器，固定ID/时间、内部fixture来源。3事件/11告警/18对象/2Case/3Run/11证据/14活动，完整/partial/仅分诊及有/无Case分支；原67/18/19/15逐记录保持，总78/21/21/18、13实际Run保持。关系只追加设计模型、实体和来源告警可对照，真实sourceGraph不借用。页签布局不变，新增明确关联依据；告警完整交付/技术/建议按材料显示。新增fixture的不可用工具步骤标失败。

## 验证

语法及94测试（原88+新6）通过，日志/tmp/socai2-showcase-final-tests.log。6新合同包括原记录/编辑保持、关联端点/时间/工件hash、全部3×5事件及11×4告警页签、无Case创建、分配→处理中/人工解决、反馈与候选同来源范围、实际分数与缺值。首次检查记录中的旧总量/日期预期已随追加更新；新测试一处跨VM Array原型断言调整后通过。

IAB仅独立后台tab读取及打开/取消弹窗，没有保存管理/反馈/Case或重置。1600概览/图/关系来源/响应/告警概况已核，700告警/图文档clientWidth与scrollWidth均685；viewport已恢复。截图在.local/verification/incident-alert-showcase-20261031（incident-overview、incident-graph、alert-overview、alert-response、no-case-dialog、alert-narrow、graph-narrow）。

历史14文件及SHA在.local/versions/incident-alert-showcase-before-20261031。缺口/覆盖统一docs/design/incident-alert-data-showcase.md，README/分析26节/验证/工具说明/AGENTS/PROGRESS已同步。

独立结束审查发现：仅分诊样例的input包含未来人工关闭材料、跨主机查询只写单主机。已修为分诊前原始记录快照（不带当前反馈/历史），args/返回scope显式同一主机列表、账号与绝对窗口；新增时间/范围断言后6定向通过。

未参与实现者current_workspace_review结束复核限定ACCEPT、0项剩余必须修。独立重跑6项新增合同通过；重新离线投影逐值相同，18原件SHA、14历史备份SHA匹配，5原数据模块字节不变；生成器输出与保存模块一致、实际sourceGraph未接入演示关系，宽窄截图与文档相符。结论仅覆盖本批本地页面、样例及对照文档，不代表后台接入或真实调查质量验收。

已执行openspec archive align-incident-alert-data-showcases --yes，归档为2026-10-31-align-incident-alert-data-showcases，同步1项新增规格。归档后严格校验当前9项、历史53项全部通过，git diff --check通过；未提交或推送。
