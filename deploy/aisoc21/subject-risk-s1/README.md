# 事件/Case 属性候选发布入口

本目录为统一发布入口说明，不是已部署版本。按[候选清单](../../local-investigation/subject-risk-release-fragment.json)合入同一版本；配置示例为[subject-risk.json](../../local-investigation/subject-risk.json)。三个进程显式选择同一内容的绝对路径 `SOCAI2_SUBJECT_RISK_CONFIG_FILE`，缺失不回落默认环境。

升级使用 `install_reader.py subject-risk --profile <显式配置>`，沿现有 analysis 和 analysis_ingress 节选择调查 writer、Fusion 入口及 reader；函数按调用者事务/RLS工作。新装的两个 current 入口复用同一 132，旧 V1 原件保留。增量只增加四列和创建初始化函数，不回填旧主体，不改变告警结构。

S1创建读取、S2意见应用及S3人工管理的候选代码统一列入清单；S3验收状态沿[实际回执](../../../docs/operations/evidence/subject-risk-s3-20261120-01/README.md)。S4页面新增资源列在同一清单的`page_delivery`中，4173独立静态资源和4177查看器整目录按各自发布入口打包，不混入核心API补丁；具体范围及验证见[S4页面交接](../../../docs/integration/subject-risk-pages-s4-20261120.md)与[回执](../../../docs/operations/evidence/subject-risk-s4-20261120-01/README.md)。本次无新迁移、配置键或监听，人工管理沿同一风险profile及已有显式批量上限配置。后续任务与整链验收未收口，不可单独当完整change发布。正式服务保持原版，change完成后统一发布/读回。
