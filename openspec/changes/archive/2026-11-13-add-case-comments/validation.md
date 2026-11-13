# Case评论直接验收

本批仅F24-01，新增E58提交、E59分页读取；原57操作保持。附件、采用、自动调查和模型质量不在本批范围。

## 本机实现及候选

- 6项定向检查通过：正文原样保存、空白/伪造作者拒绝、HTTP依赖边界、原57路径及Schema保持；Ruff最初三处import排版已修正，没有业务失败或模型调用。
- [候选21次TCP](../../../../docs/operations/evidence/case-comments-20261113-01/candidate/verification.json)：新建两份独立合成Case，共享同一已有合成告警；主Case一项未完任务、两条普通评论。原文/作者/时间、幂等重放/改意图409、空白422、分页、其他Case为空、错误父Case404及活动读取通过。
- [真实SQL](../../../../docs/operations/evidence/case-comments-20261113-01/candidate/sql-after.json)核对2条评论、2条活动/4目标与HTTP一致；Case仅业务时间及行版本随评论增加，2个待启动Run、1项人工任务及修订、0结果。没有启动调查或模型。
- 已结案Case追加评论在实现中不修改处理状态，当前仅代码审查，未声称该分支完成真实HTTP验收；本批无编辑/删除或回复线程。
- 本机冻结源从已发布grouping-summary复制，只覆盖[清单8文件](../../../../docs/operations/evidence/case-comments-20261113-01/local-source-manifest.json)，不带入并行模型工作。

## 交接和发布准备

[docs11检查](../../../../docs/operations/evidence/case-comments-20261113-01/docs-check.json)：59操作、56已实现/3预留，132Schema、576固定输出字段位置；新增22=POST9+GET封套4+列表项9，原125功能和CSV104列保持。508个成功/错误响应示例符合Schema。实际作者名称沿现有认证适配保存登录邮箱，已在字段和指南说明。

## 两端实际发布及读回

本机已切换至`case-comments-20261113-r1-local`，PID69626，ARM64原生Python，库v12_upgrade_dev；6次正式只读GET与候选评论/任务/Run/Case一致，SQL快照逐值保持。21已发布`case-comments-20261113-r1`，镜像`sha256:4577b3f11125378c31e419961e68f2a5f462e7b30bc77981c4fe9ee5be3bd318`，库aisoc；新建本批两份SYNTHETIC Case、1项任务和2条评论，共22次HTTP通过，随后SQL读回核对一致，不启动Run或模型。

21首次使用docker cp传只读核验脚本，被容器只读rootfs拒绝，SQL尚未运行；保留空输出和[失败记录](../../../../docs/operations/evidence/case-comments-20261113-01/21-http/sql-read-attempt.json)。随后保持容器配置，经docker exec标准输入执行同一脚本，以只读事务核对成功；没有重派业务写入或改变服务实现。

两端Swagger docs11的9入口均200且摘要一致，8个handoff载荷与仓库字节相同。当前8文件源码与冻结包/21运行相同，其他36容器的身份/镜像/启动时间保持；API读写实际保存及读取一致。无迁移、无新表、无消费者恢复，未发布并行模型修改。[完整回执](../../../../docs/operations/evidence/case-comments-20261113-01/delivery-summary.json)与[Swagger回执](../../../../docs/operations/evidence/case-comments-20261113-01/swagger-release.json)。

结束审计见[audit](audit.md)；归档和Git动作以实际回执为准。
