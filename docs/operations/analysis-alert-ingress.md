# 新告警自动分诊运行说明

2026-11-15，第3步本地验收完成，待整个流式change统一发布。正常原生告警保存会在同一PG事务创建一份`alert_triage / initial / ingress`任务；投影成功后才确认原Kafka偏移。生产者不调用模型，调度器从任务记录补投Redis并领取。重复投递保留既有告警、首份投递快照和任务，不重新分诊。同事件新增A3只分诊A3。第4步现已接入事件initial及周期诊断，见[事件运行说明](analysis-incident-diagnosis.md)；Case仍待后续步骤。

实际执行前读取最新A材料，创建并保存Run、输入及策略工件，同时绑定attempt；提交后才查询背景、调用模型。每次有限重试使用同task下的新attempt/Run。已知尚未发出的连接等待超时可按默认60秒、最多一次重试；响应超时记录unknown并结束本地尝试，不自动重试或阻塞其他告警。输入、工具请求/回执、实际模型请求/Schema、原答、结果与失败均沿原执行器保存。任务completed只表示程序交付，不代表正文质量合格。

## 配置与统一发布

- 先安装128及选定入站角色的普通授权：`python deploy/database/install_reader.py analysis-ingress --profile /absolute/private/reader-install.toml`。`[analysis_ingress]`选择已有角色及锁/SQL时限；只新增任务和主体状态表的SELECT/INSERT，不新设业务角色。新装`initialize-current`使用同一授权文件。V1原件不变。
- native sink必须显式获得生命周期JSON（`SOCAI2_ANALYSIS_TASKS_CONFIG_FILE`或投影profile的`analysis_policy_file`）。缺失配置或登记失败使本次入站失败，不能只保存告警而漏掉任务；不回填已有告警。
- 复制[投影示例](../../deploy/aisoc21/analysis-projection.example.json)，明确topic/group、bootstrap、源代码/策略/状态路径、连接和SQL时限、单次读取额度及健康期限。保持原topic/group及activation文件，已有消息由保存偏移接续。失败日志含topic/group/partition/offset/error；查明并修正原因后重启同一实例，不跳位或删除activation记录。
- 生产处理profile的`paths`明确`projection_file/mount`和`analysis_tasks_file/mount`；启动器同步环境与只读挂载，Compose使用所选profile导出的镜像和路径变量。构建必须同时包含新版Fusion sink/helper、核心A适配器和projection/config模块，旧r3镜像不能与新脚本混用。当前仓库旧镜像ID不是本步发布回执，统一发布时选择新候选及验证过的digest。
- 新目标版本复制[A/I调度示例](../../deploy/local-investigation/analysis-ai-dispatch.example.json)及[执行器配置](../../deploy/local-investigation/analysis-ai-executors.example.json)，配置同一租户、PG、Redis、唯一进程锁/持久目录，以及`investigation_policy_file`。该文件内容必须与`SOCAI2_INVESTIGATION_POLICY`选择的一致；模型网关地址/密钥和协议沿受控运行配置。默认禁用；第4步联合工厂同时注册A/I，原A-only示例仅为第3步历史边界。不要另开一个进程获得额外N。
- 合并[本步发布片段](../../deploy/local-investigation/analysis-alert-release-fragment.json)、原任务/调度片段及HTTP侧E36删除与查询变更，再统一发布。目标版本不再提供手动告警同步启动；内部A执行能力保留。旧生产Agents消费者保持关闭。本轮未发布、未恢复消费者。

已有分诊后知识同步仍由原知识profile控制，计划在第10步接入低优先级队列。本步新验证租户显式关闭外部知识写入；不得据此宣称知识队列已实现。

## 验证边界

[本步回执](evidence/analysis-alert-auto-20261115-01/README.md)包含真实隔离PG/Redis、实际A执行器的8项检查、一条真实模型、HTTP同源读取及4177快照。Kafka提交顺序由现有消息替身测试覆盖，本步没有启动真实生产消费者。真实模型正文不完整，质量NOT_PASSED，原答保留且不重复采样。统一发布后的实际服务版本、配置及消息接续读回仍须随change收口完成。
