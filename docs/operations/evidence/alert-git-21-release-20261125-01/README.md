# 告警功能 Git 与 21 交付

负责人于 2026-11-25 明确要求将已验告警工作推送 Git 并发布 21。范围见[本批方案](../../../../openspec/changes/complete-socai2-investigation-chain/alert-git-21-release-20261125.md)。本批只包含告警及其必要接线，保留事件页并行修改和其他未验工作。

## 功能与接口

| 功能 | 已确认行为与读取入口 |
| --- | --- |
| 列表、预览、详情 | 沿 4173 的告警布局读取 E26/E28；侧栏 AI 区仅显示结论，完整解释在详情。人工判定和 AI 分诊各保留原来源。 |
| 负责人、状态、标签和人工反馈 | Q04 查询现有人员；E48–E51 只作用于明确选择的告警，只更新显式字段。负责人修改不要求理由；关闭和反馈需要理由。单条标签可替换或清空，批量标签拒绝。旧版本不拒绝告警保存，以最后成功保存为准。失败停止且不自动补交，成功不区分“变化/无需修改”数量。 |
| 材料及固定分诊 | E31 读取同一材料，E24/E32/E33 及 Q27–Q29 读取所选 A Run 的结果、步骤与工件，保持主体、材料及轮次绑定。 |
| 规则及三类置信度 | 接收映射源规则名称和标识并保留字段来源。OCSF 源置信度枚举、Fusion 检测评分和 AI 分诊自评分别显示；源枚举不转换成百分比。 |
| 查询跳过说明 | 沿保存的原因、参数和时间显示跳过原因、计划参数及完整查看入口；未开始的查询显示“未执行”，与查询成功零行区分。 |
| 已发布分诊映射 | 同轮 ATT&CK 与已发布分诊一同展示；新鲜度、当前采用资格单独返回，不因展示而更新原分诊或运行结果。 |

## 版本与直接验证

调查核心的规则和新 A 提示已在 21，实际文件与已验指纹一致，本批不重复重启核心。其[冻结与实际加载回执](../alert-rule-source-confidence-20261125-01/core-git-deploy-handoff.json)保留 6 个提交文件、必要测试及运行配置核对。

调查 HTTP 的 E54、Q04 和管理功能按三批既有在运源码重建，原 751 文件总指纹与发布回执一致；两处已发布 ATT&CK 展示修正单独加入。现已切换 `c173-alert-attck-readback-20261125-01`，83 个操作、原配置和回退容器保留；[实际发布](http-attck-release-result.json)及配置与既有测试见[HTTP 冻结交接](http-git-freeze.md)。平台补 Q27–Q29 只读转发，两份运行文件覆盖及实际 Compose 变化见[平台 API 激活](platform-api-activation.json)。

前端从 `bb368df8cbebba85516a6fd2a47cc74e4afd75b9` 加精确 37 文件告警补丁构建，事件页保持基线。生产构建包含 TypeScript 与字体检查，详见[构建回执](frontend-build.json)。共享文件只保留告警需要的段落与可选参数，未把整个脏工作区打包。前端及平台候选已提交并推送为 `8051df5008af9e711a2c71890ad9bf111ff82301`；[21 web 镜像与入口资源](frontend-web-release.json)和[前端技术读回](frontend-21-page-readback.json)通过。

原有管理保存、同版材料、固定 Run 以及[源规则展示](../alert-rule-source-confidence-20261125-01/independent-closeout.json)、[一条首次接收](../alert-score-first-receive-20261125-01/independent-closeout.json)、[查询跳过说明](../alert-query-skipped-display-20261125-01/independent-review.json)的直接验收按原范围复用。本批另做必要构建、实际加载及静态资源核验，不增加 Kafka 投递、管理保存、模型调用或压力测试。统筹的[独立运行核对](independent-runtime-review.json)核镜像、源码、新提示、入口静态资源和 HTTP 就绪；[固定 Run 接口状态核对](platform-api-fixed-run-status-only.json)的 Q27/Q28/Q29 均为 200，响应体在 21 丢弃。

自动审核拦截了可能向 Codex 传输业务内容的正式读回；保留[拦截回执](platform-api-readback-blocked.json)，采用仅返回状态码的限定核验后可完成工程发布。正式 21 认证页面的数据内容同源性和浏览器 JavaScript 错误未在本批复验，不将接口成功当作这些业务验证通过。旧 8181 验收证据不因此扩大适用范围。

## Git 边界及未完项

服务端提交目标为 `Dinines/socai2` 的 `V1.1`、`main`，父项目 `wangjuelong26/SpiritHub` 的 `add-server-submoudle` 只更新 `server` 引用及本批 README。前端和平台代理沿当前 `codex/spirithub-4173` 分支交付。固定同步工具保存实际远端 SHA、父引用与阶段回执，不改写旧父项目工作区，也不合并无关上游代码。

本批真实新 A 的置信度仍为显式 `null`；数值正例没有取得，空值理由的语义未验，不能宣称模型评分质量已修复。原旧告警的对象漏映射和首次 Fusion 未启用保持历史状态。独立评论、历史材料目录、UID 原文、相关/相似告警非空正例、资产关联及持续接收仍按原问题清单推进；事件和 Case 的联合验收后置。整个 OpenSpec change 未完成，不归档。
