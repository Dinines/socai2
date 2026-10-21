# 3A-11-02：常驻分诊配置补齐执行卡

状态：**限定配置验收完成**，实际见[回执](3a-triage-admission-config.md)。以下保留本批原范围，执行前原件另存受控证据。依据[只读审计](3a-admission-review.md)发现的配置缺口，下一单项先补环境配置；p01理由仍为质量阻塞，修复边界见审计回执。此卡不授权开启常驻消费、重调unknown、退款预约或新增真实模型。

拟变更只涉及21 Agents的新增Compose叠加层：显式`AISOC_AGENT_RAISE_APPROVALS=0`；复用Fusion已生效的项目Kafka bootstrap、`SSL`及CA验证配置，Agents以只读方式挂同一公证书。不得使用明文豁免，不复制Fusion其余环境或数据库/网关凭据。保留原镜像、reader/policy挂载及其权限；worker、graph、记忆写回和真实响应保持禁用。实施前保存容器配置/环境hash和只涉及本服务的恢复定义，若需要重建仅操作Agents。

验收输入为当前21层及旧预算批六个测试topic/group；不发布或消费旧积压。先核渲染后的新增层与实际挂载差异，再以原非root UID验证审批guard明确False、Kafka transport明确SSL、证书校验和bootstrap可用；只assign读取既有group的committed/end，不poll、join或commit。核worker与其他自动路径仍OFF、SDK retry0/45秒、reader五映射/十key保持。旧14表与预算行、六组offset、网关计数、其他35容器/18卷及134迁移前后保持。无新key、DDL、模型或业务输入。

缺失配置修复不等于常驻准入通过。A的两条unknown继续占满unsettled=2；B在当前24小时窗内calls=3/reserved_units=60000满额，均不得为方便验收改policy或标记no_request。仅在确认未启动消费者的前提下恢复旧配置；恢复不自动清理任何Run、预约或topic。若环境/源码与审计不符，先重新核差异。

随后另立p01提示词小批：明确时间、动作/对象与当次授权依据，缺失窗口结束/时区保留未知，组织习惯、职位及无匹配job不当当前授权或确认未授权。预计仅`triage.system`及其版本/lock、直接测试和来源差异；不重写风险算法、模型输出schema或评分器。先完成无模型的prompt/实际传输/持久预算检查，再单独冻结新盲测输入、判据和真实模型调用上限。旧p01结果、评分和5223 tokens不覆盖，也不把提示词文字检查当语义质量通过。
