# 限定发布结束审计

2026-11-12。审计者未参与本 change 的实现或发布；本次只读核对保存回执、配置与交接，写入本文。未运行测试、模型、数据库查询、网络、浏览器或部署，未改运行代码、证据或原 [audit.md](audit.md)。该原件保持发布前本地截止结论。

**结论：限定发布验收通过（RELEASE_ACCEPTED），具备本 change 的归档条件。** 范围为本地正常保存后自动同步的既有直接验收，以及生产实际加载、处理身份 SELECT／INSERT、既有租户／RLS 定义和静态原件发布读回。生产没有重新执行自动同步整链，不能将加载检查写成生产功能实跑。归档、最终 Git 推送及父项目引用仍须随后按真实回执完成。

## 真实失败、修正与一次切换

[交付汇总](../../../../docs/operations/evidence/knowledge-sync-20261112-01/delivery-summary.json)与原 `unified-*` 回执一致：

- r4 上传／构建后，[preflight](../../../../docs/operations/evidence/knowledge-sync-20261112-01/unified-preflight-20261112T032024447583Z.json)以 exit 1 失败。公开回执保留命令失败标记；[修正记录](../../../../docs/operations/evidence/knowledge-sync-20261112-01/release-plan-correction.json)说明 main／workbench Compose 基线路径漏掉 `release-` 目录前缀，并列出与 `production-before.json` 实际 labels 一致的正确路径。更正前 API／工作台 rollout 都为 0，不算已切过一次服务。
- r5 upload、build、preflight、prepare 和 [activate](../../../../docs/operations/evidence/knowledge-sync-20261112-01/unified-activate-20261112T032750251181Z.json)均保存成功回执，发布清单 hash 为 `93aa9e2cda2fcfbafedf8a3c4c21a65e9d77d8d9e17c0d867d9098a568838dd1`。修正未改变应用源码或重建处理镜像，也未重跑本地业务流程。
- 实际 rollout 回执只有 [API 一次](../../../../docs/operations/evidence/knowledge-sync-20261112-01/unified-rollout-20261112T032544490245Z.json)和[工作台一次](../../../../docs/operations/evidence/knowledge-sync-20261112-01/unified-rollout-20261112T032650857216Z.json)。逐项比对 [发布前](../../../../docs/operations/evidence/knowledge-sync-20261112-01/production-before.json)与[发布后](../../../../docs/operations/evidence/knowledge-sync-20261112-01/production-after.json)，API／工作台容器 ID 改变；fusion、agents、projection、litellm 的 ID 和镜像保持，六项均 healthy。工作台沿用原镜像并切换绑定源码。
- current 指针为 `v1.2-20261112-r5`，处理版本为 `processing-20261112-r3`／镜像 `51d94e50…`，与发布配置和构建回执对应。消费者关闭标记保持；知识同步开关启用不等于启用了 Kafka／Agents 自动处理主链。

## 写入接线和实际加载

[增量权限回执](../../../../docs/operations/evidence/knowledge-sync-20261112-01/knowledge-write-access.json)记录对 `aisoc` 中 `socai2_prod_processor` 的知识表 INSERT 授权 exit 0；脚本 hash 与仓库文件一致，增量仅为 `GRANT INSERT`，没有调查 DDL 或业务数据写入。修正记录另保留首次本地包装命令在派发前发生 Python 语法错误的事实；实际增量只执行一次，不能将未派发错误写成不明执行后盲目重试。

[loaded-sync.json](../../../../docs/operations/evidence/knowledge-sync-20261112-01/loaded-sync.json)及其[只读检查脚本](../../../../docs/operations/evidence/knowledge-sync-20261112-01/read-loaded-sync.py)表明使用原处理写会话建立只读事务，实际身份为 `aisoc/socai2_prod_processor`，租户为 `00000000-0000-0000-0000-000000000001`，KB SELECT／INSERT 均为 true。既有 `aisoc_kb_documents_tenant` 策略定义已读回；这里核的是定义及实际租户设置，没有宣称新增 RLS 规则或完成跨租户隔离测试。

实际同步开关为 true、总时限 120 秒，profile hash `0ce1a5003fd7288768d7ab8ea279a7710c6423a0856ba8e2a9155e796a005ecf` 与所选配置一致；嵌入仍为 qwen3-embedding:0.6b／1024，使用既有专用集合。五个加载源码 hash（knowledge_config、knowledge_history、knowledge_source、knowledge_sync、stage_results）均与当前工作树及本地流程 `plan.json` 冻结值一致，回执 schema 为 `socai2.history-sync.v1`。前次本地审计中的生产 INSERT=false 前置已由本次实际身份读回补齐。

## 静态原件和执行范围

[静态发布](../../../../docs/operations/evidence/knowledge-sync-20261112-01/static-publication.json)只追加本地验收批次：正式 4177 **39→40 条，2 文件／3 HTTP**，原记录、原文件和无关内容保持，没有刷新旧记录或在静态步骤重启容器。[static-manifest.json](../../../../docs/operations/evidence/knowledge-sync-20261112-01/static-manifest.json)确实列出两个文件；该清单文件本身的 SHA-256 与回执所列 manifest hash `206918da5adba671c9daa03800ee1fbb3ca2f70da53a33ac73798fb27cc48e3d` 一致。新索引 hash 为 `0a8114a3b0498d0664dca8ecca8d18d8cf80ca394f59963990618bed64d187a3`；本地 68 条和正式 40 条分别记录。

发布到 4177 的是原本地一 Run／5 工件，其中包含两份同步原件；它们不是生产新生成的分诊或同步结果。本轮没有新页面设计或浏览器视觉验收，依据为保存文件及 HTTP 内容读回。

**生产新增 A Run、Case、知识数据写入、嵌入调用和分析模型调用均为 0。** 权限增量与只读身份检查已实际执行，但没有制造第二条生产合成判断来重复验收。本地端到端依据仍为原 `finish` 提交→同步意图→卡片保存→真实嵌入／Qdrant→当前历史查询→5 GET，并已核重复 finish 不重派；[本地汇总](../../../../docs/operations/evidence/knowledge-sync-20261112-01/local-flow/summary.json)与交付汇总逐项一致。

## 保留结论与归档边界

11 项受影响检查及一次本地正常流程继续有效，没有新增测试或采样。判断来自明确标记的模板，本批质量 **NOT_EVALUATED**；前序模型质量 **NOT_PASSED**、M01／M02／F02 等问题不核销。失败／未确认状态仅由既有直接检查和实现审查支持，不冒充生产故障演练；只有意图而无结果仍是不明完成状态，不获得自动重试许可。

人工反馈自动接线、历史全库回填、持久队列／自动恢复、A/I 新检索、Deep 动态检索及自动处理主链仍未实现。原显式维护入口、旧卡及旧 Run 保留。

已复读根进度／前后端交接、OpenSpec 入口及主调查、知识交接、部署／配置与问题清单。收尾发现前后端交接曾将前批 r3 的 7 次 HTTP／3 查询／39 条记录与本次 r5 混写，实施方已原位分开；主调查当前发布号及 Case 知识交接的“前批／当时”表述也已修正，本审计再次复读确认。K01 只核销分诊保存后未接知识维护的缺口，没有核销人工反馈、消费者或模型质量范围。

本地验收、交接、独立本地审计与本次限定发布读回已满足本项收口范围，可据此归档。任务 4.1 的最终勾选及归档、服务端提交／推送、父项目 `server` gitlink 更新必须以之后实际操作为准；本文没有预报这些操作已经成功。
