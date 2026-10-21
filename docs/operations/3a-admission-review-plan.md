# 3A-11-01：剩余准入阻塞只读复核范围

本批承接[可靠性计划](3a-worker-reliability-plan.md)最后一项，先核p01理由缺陷、普通分诊与旧调查工具的实际身份边界、预算unknown与积压。它是只读审计，不修改运行代码、prompt、schema、policy、凭据或Kafka offset，不重启服务、不启动worker，不调用真实模型。旧3A-09及3A-10回执和原始材料保持冻结。

验收固定为：

1. 从旧p01实际发送messages、原模型回复、worker结果与原评分核hash；用当前生产indicator scorer及worker gate离线重放原理由，说明时间/授权语义是否被覆盖。另一个auto-closeable verdict接缝仅为反事实gate探针，不是新模型分类或质量样本。
2. 固定21当前四服务镜像、API/Agents源码hash、worker/graph/审批/写回开关、SDK参数；核五类reader映射及十枚原key元数据保持。只观察旧工具认证配置是否存在/匹配，不冒充新HTTP授权或工具质量验收。
3. PG显式READ ONLY事务读取14表材料hash、134迁移、预算行、关联Run/事件及现有测试policy；Kafka仅assign后读取committed/end，不poll、不subscribe、不join消费组、不提交。核六个旧测试group和三条未知预约；不发布新消息、不重试未知结果。
4. 审计前后对比上述数据、镜像/容器和网关计数；形成阻塞矩阵、明确unknown保留合同及下一单项修复卡。上批限定验收不扩张为完整准入。

原始证据新增在独立`3a-admission-review-20261020`目录，0700/0600，旧目录只读取。公开只保存hash、计数、合成对象关系与结论；不保存key、连接密码、模型隐藏推理或原始敏感资料。此范围在运行探针前固定；实际结果另见回执。
