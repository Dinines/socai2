## Scope and decision
三个本地Case由已保存Fusion成员关系组成，独立local ID、sourceCaseId=null、localCollection=true；源Alert.caseId及Run.sourceCaseId保持为空。组织时间与源采集时间分开，业务状态New仅表示本地集合初始状态，负责人未分配，优先级/结论不自动生成。

Case首页汇总当前成员与已引用Run，逐Run保留分诊/调查判定/完整性及材料入口，不产出联合结论。证据页列当前来源告警与既有Run工件、报告；原始工件不强行改成已分类证据。关系图按当前成员原始对象关联；Path仍显示当时未关联Case。活动区取已引用Run真实过程，说明其发生在本地整理之前。

sourceRunIds为本地材料引用，精确Run+环境+租户；不冒充持久Case归属，成员移除仍保留引用Run与冻结输入。当前成员另加可用同来源Run。幂等合并不覆盖浏览器编辑；重置沿原有合并路径。
## Validation
离线核3组/6成员/6Run、92过程/49工具/77工件；源case_id、Run输入和原材料hash保持。直接测试全Case区域、空态、成员变更、同来源隔离、编辑/重置、原告警回归；浏览器核列表→汇总→材料→Run。未参与实现者结束独审，实际通过后归档。
