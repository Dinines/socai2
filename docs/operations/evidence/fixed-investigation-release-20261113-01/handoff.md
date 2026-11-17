# 新版调查核心与独立HTTP接续

核心已发布`v1.2-20261113-r1`，生产读回通过。独立18024当前仍为E71的`alert-host-20261113-r1`，本机为同源-local，Swagger docs18；本轮未替换，下一次HTTP同步由接口聊天负责，暂不提交推送Git。

| 项目 | 已发布值 |
| --- | --- |
| 核心API | `socai2-api-1`，`sha256:e12c6ca824cdfb863c31b608b1c360d47a922879f551ed9c7634caddee552c91` |
| 显式处理镜像 | `socai2-processing:processing-20261113-r1`，`sha256:4999860349fd69b047adfe60045efd470fd373e56d5dcbe573bc859c9064b7a5` |
| 冻结目录 | `/opt/sting-aisoc-socai2/releases/v1.2-20261113-r1`；本机`.local/unified-release/v1.2-20261113-r1` |
| 实际生产profile | 冻结目录下`docs/operations/evidence/fixed-investigation-release-20261113-01/production-profile.toml` |
| 模型策略 | 冻结目录下`deploy/local-investigation/investigation-policy-case-v1.toml`，SHA `a3298006f954f0a811e76a95bb26a1fbab866dd44260662a10af2bb4bc88d9d8` |
| 完整源码摘要 | [released-source-manifest.json](released-source-manifest.json)，包含app和独立investigation_http冻结来源 |
| 实际切换/保存读取 | [delivery-summary.json](delivery-summary.json)、[readback-after.json](readback-after.json) |

HTTP侧需同步调查模型核心和对应策略，保留其已有71操作、端口和profile选择。应从上述冻结目录按摘要取源，而非覆盖整个旧部署根目录；其中`app/socai2/case_context_input.py`等本轮新增文件也需带入。完整主API构建已包含分离后的`investigation_http`依赖，处理镜像直接调用核心，不要求加载独立HTTP入口。

配置用途：A/I两次上限包含首答及一次引用纠正，24000tokens；Case6次/131072tokens/1500秒。C3启用`case-input-v1.json`的`program_output.c3_coverage=true`；C3线上的模型五问不改变保存六问合同。新Run按新profile冻结，旧冻结六问和原答仍读得出；不要重派历史Run或用新profile改写旧边界。知识profile/凭据路径沿各自显式配置，不复制私密文件内容。

本次没有数据库迁移、告警字段变化或外部HTTP Schema增量，原71操作的合同沿用。核心的同一生产Case、Result、当前判断在切换前后逐值摘要一致；本轮不替代HTTP侧对其新容器的实际加载及必要读取核验，也不要求新模型采样。质量继续NOT_PASSED，流式、队列和自动反馈重算未实施，自动分析消费者继续关闭。

冻结包同时保留了上一版的根配置作为源快照；**实际加载路径以release.json的processing.profile及上表为准**。仓库`deploy/aisoc21/production-v1.2.toml`、`release-v1.2.json`及`current-rollout.json`已在发布后更新到实际版本，没有改写冻结目录。
