## Decisions

1. 从`.local/aisoc21/attack-context-20261021/case-v2`白名单读取实际case-created、run-detail、run-events、Run工件与节点采用结果，校验身份/成员/工件hash/报告一致；不读取凭据或导出完整prompt/messages/模型回复。
2. 使用真实Case UUID 82b1246f-9f34-463c-8c2d-27d2b075c741及Run e998308a-a353-4647-99f6-10f94ced0ecf；新增三告警只采用保存的raw_alert.alerts输入，不借草稿补当前状态/评分。Case状态new与Run completed分开。未记录交付完整性则未知，不从Run completed推导完整交付。
3. 5条链候选保留顺序、分数、distance与shared_entities，2条是本Case成员、3条是历史外部候选；只导入本Case3条输入。Path11节点15边、图可达16不等于确认受害。三工件保留同一查询时间与来源，不以当前关系重建替代。
4. 四阶段分别展示已采用的recon/forensic/responder/report结果；forensic置信度单独标注，响应dry_run建议不等于执行。工具完整保存结果与旧200字符摘要分型。历史事件ts与Run时间原值存在8小时时差，保留来源值并注明，不猜测校正。
5. 历史Case来源提示与本地整理Case分别表达；重复导入不覆盖本地编辑。旧样例和新旧六条告警保持。Case附件/资产库存未知不继承模板值；联合调查通过Case链接显示，不生成三份单告警调查。

## Verification

核对实际POST Case201、启动200、最终Run200；工件hash、三告警范围、四阶段、5候选/11节点15边/16可达、报告及4调用18388tokens。直接回归、浏览器链/路径/阶段及来源切换验证后按仓库约定独审归档。

身份补充：Agent内部Run为12522217-c0ef-4222-8522-ee0fb680c0e6，与API持久Run不同。通过同Case/tenant、29条audit与持久events逐序kind/agent/summary/hash/duration/metadata完整相等、四阶段采用值与报告一致校验归属；两ID分别保留。真实Case历史按sourceCaseId/tenant/environment保留，即使当前成员全移走也不丢调查历史。
