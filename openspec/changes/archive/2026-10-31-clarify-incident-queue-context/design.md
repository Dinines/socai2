# Design
事件行与侧栏从当前成员只读整理资产标签及主机。资产标签与告警列表使用同一entityIds→assets.tags关系，去重；原incident.tags保留为事件管理标记，不假称资产标签。主机取已保存hostNames及关联device，不从IP猜主机，不补库存关系；多主机显示前两个和余数，完整值可悬停。

已关联调查指标使用当前事件成员的Run关联，沿用alertFlowWorkspace.started判定；部分交付计入，未升级分诊排除。每事件仅计一次。指标与既有活跃事件等使用当前加载事件集合。活跃仍明确New或In progress；Not set不计入，显示状态未提供，原数据不写回。

保留事件优先级原值。真实事件侧栏以成员告警分诊评分（detailMaterial.risk，沿已有alerts.ai_score归一值）和对应判定补充可用依据，不做max/average风险分，不把高置信误报当高风险。原完整演示优先级样例保持。

验证原68项及新增定向字段/聚合/不变性合同、浏览器列表/预览；未参与实现者结束独审。改前文件在.local/versions/incident-queue-before-20261031。
