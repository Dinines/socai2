# 两个暂停项目恢复执行记录

2026-10-22（Asia/Shanghai）。用户明确要求继续此前因额度中断的两个项目，并记录每一步。原暂停点见[收尾记录](../handoff/session-closeout-20261022.md)，本次恢复不改写旧失败或已有回执。

## 范围与执行步骤

| 步骤 | 输入与操作 | 结果及证据 |
| --- | --- | --- |
| 1．找回暂停点 | 读取「继续推进迁移」和「astra评估模块迁移并制定后续推进方案」原会话及本地收尾记录 | 前者测试工具真实联测未完成；后者237行建议正文及限定ACCEPT已保存，未交付最终回复 |
| 2．确认当前状态 | 核v1发布/两例落库回执、原测试探针与OpenSpec | v1已上线、生产worker已启；本次工具仍只走隔离topic和本地Fusion。restore strict通过，原5/15保持 |
| 3．恢复测试工具验证 | 复用8项离线＋2项替身合同结果；复核探针日志修正；准备全新attempt02，最多3条已有告警 | 已执行attempt02：3条新输入，原8离线＋2替身结果复用；attempt01保持 |
| 4．真实输入到落库 | 本地最小认证API→21独立raw topic→原Fusion方法→独立fused topic/PG/Redis快照 | 已通过：raw/fused各3消息、PG3行new、首次快照匹配；本地API/客户端已停，Run0/模型0 |
| 5．完成产品建议交接 | 保留已审建议，在明确区分历史的补充段中同步v1实际状态、留存缺口与后续建议 | 已补v1发布/两例数据与留存缺口，四合同/场景路线保持建议，未实施全部方案 |
| 6．结束检查与独审 | 仅直接检查本批差异，由未参与实现者做一次结束审计；补原change记录和本地版本 | 独审限定ACCEPT、0本轮必须修项；64链接/围栏/JSON/diff/strict通过，选定文件与证据已留存，原5/15保持 |

逐步时间、命令和净化结果另留`.local/versions/two-projects-resume-20261022/steps.jsonl`。既有修改保持，不自动Git提交/推送。本批不改业务源码/运行配置，不部署或更改常驻worker，不执行真实厂商动作；生产服务维持此前已授权状态。

## 实际结果补充

23:22启动attempt02，退出码0。完整输入ID/canonical ID/消息坐标与实际逐步结果见[工具回执](testdata-tools-20261022.md)及[机器摘要](../handoff/testdata-tools-20261022.json)。原尝试失败和本次本地材料核对的一次假设错误均已保留：Fusion按原合同向source_event_ids追加上游Alert ID，修正观察后通过，未改业务或重投。产品建议已交接到当前v1事实，优先范围/真实数据、证据与报告一致性、停止后交接，未变更运行。

## 结束结论

两个原暂停项目的本次交付已完成：测试工具真实隔离接线通过，产品/工程建议已补最新v1事实并完成交接。`resumed_projects_end_audit`未参与实现，只读结束独审限定ACCEPT、0项本轮必须修项；独审未重新联网或跑测试/业务。该结论不替代原restore全change的验收，原5/15与调查质量失败保持。

选定文件、逐步日志、原失败/新合成回执和审查回复保存在`.local/versions/two-projects-resume-20261022/`，`snapshot/`保留项目路径，`manifest.json`记录字节/hash，排除私有配置；不作生产运行包或Git提交。

## 原始证据入口

- [测试工具原回执](testdata-tools-20261022.md)、[工具使用方法](../../tools/testdata/README.md)、[真实探针](../../deploy/aisoc21/probe_testdata_ingress.py)。
- [产品与工程建议](../architecture/investigation-product-engineering-roadmap-20261022.md)、[原建议独审](../../openspec/changes/restore-alert-investigation-integrity/audit.md)。
- [v1发布](service-v1-release-20261022.md)、[生产两例](service-v1-functional-20261022.md)、[后端数据盘点](../integration/v1/page-data-mapping.md)。
