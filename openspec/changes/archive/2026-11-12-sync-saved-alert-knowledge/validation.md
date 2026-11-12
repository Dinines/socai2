# 实施、直接验收与发布读回

2026-11-12。基线 `f993e630`；实际分支 V1.1，无关 `tools/model-preflight/` 保持。前序交付已完成并归档，本项完成本地实施、独审及一次生产切换，最终状态见任务与发布审计。

## 已完成

- 实施前 strict 通过。提交后接线、配置开关、独立会话与意图／结果工件已实现；原 outcome、告警 DTO、V1 表结构保持。处理账号增加知识表 INSERT，沿现有身份和 RLS；新装与增量脚本同步。
- [11 项直接检查](../../../../docs/operations/evidence/knowledge-sync-20261112-01/direct-tests.xml)通过，覆盖原卡片资格／稳定身份、配置关闭、未采用／I 不触发、成功及索引失败／未确认的分离、源版本改变；Ruff 通过。未跑全仓回归、故障恢复矩阵或模型比较。
- [一次真实本地流程](../../../../docs/operations/evidence/knowledge-sync-20261112-01/local-flow/summary.json)：新告警 `33e34ce6-6419-5505-a9ac-f0e63f03813a`，Run `13bc7764-3ce8-597a-9b3c-fa91e49a9c14`，判断 `6150ca41-2e3a-5359-b178-f803b214fefd`，历史卡 `a3c8e5ce-6005-53a5-9343-220bd6c9d297`。通过原 finish 保存、采用、触发；真实 `v12_upgrade_dev/v12_developer`、现有嵌入和独立 Qdrant 集合成功。不是直接调用同步 helper 冒充正常接线。
- [同步结果](../../../../docs/operations/evidence/knowledge-sync-20261112-01/local-flow/sync-result.json)为 `completed/stored/completed/source_current=true`；新卡实际入库、向量写入完成；只读历史查询返回该当前卡。重复 finish 返回原 outcome，仍只有两份同步工件。Run completed、原 rationale 和采用指针保持。
- [原 HTTP GET](../../../../docs/operations/evidence/knowledge-sync-20261112-01/local-flow/http) 5 次成功：trace、publication、同步 intent/result、历史卡。仅认证使用本地适配，路由／服务／数据库为原实现。工件 captured_at、源身份及独立状态均可读。
- 复用 update_processing_audit.py 追加本地 4177：67→68 份，旧批保留。原始工件沿现有查看入口，没有增加状态页面。

## 边界与剩余

本批使用明确标记的模板判断作为保存输入，分析模型调用为 0，没有新增模型质量证据。原 M01／F02 及模型质量 NOT_PASSED 保留。SQLAlchemy 对原循环外键给出排序警告，数据读取成功，未扩展 DDL 或重跑流程。

实际知识表 INSERT 增量已执行，回执见 [knowledge-write-access.json](../../../../docs/operations/evidence/knowledge-sync-20261112-01/knowledge-write-access.json)。r4 的 Compose 基线路径在 preflight 被拒，未 rollout；按实际路径修正后冻结 r5，原失败和[修正说明](../../../../docs/operations/evidence/knowledge-sync-20261112-01/release-plan-correction.json)保留。

21 已发布 `v1.2-20261112-r5`／`processing-20261112-r3`。[实际加载](../../../../docs/operations/evidence/knowledge-sync-20261112-01/loaded-sync.json)核 5 个运行源码与本地一致，profile hash `0ce1a5003fd7288768d7ab8ea279a7710c6423a0856ba8e2a9155e796a005ecf`，同步开启／120 秒。真实处理连接为 `aisoc/socai2_prod_processor`，租户设置及 KB SELECT/INSERT=true；既有 RLS 规则读回。该检查只读，不等于生产重新执行了同步。

[发布后读回](../../../../docs/operations/evidence/knowledge-sync-20261112-01/production-after.json)确认当前指针 r5，API／工作台各切换一次，fusion／agents／projection／litellm 原容器身份保持、消费者仍关闭。[4177 静态发布](../../../../docs/operations/evidence/knowledge-sync-20261112-01/static-publication.json)只追加本批：39→40 份，2 文件／3 HTTP 读回，旧记录／文件保持，静态发布没有重启服务。复用现有原件入口，未做新页面设计或浏览器视觉验收。

自动触发端到端证据仅来自上述本地流程；生产没有新增 A／Case Run、知识写入、嵌入或分析模型调用。独审与发布边界见 [audit.md](audit.md)及 release-audit.md，汇总见[交付回执](../../../../docs/operations/evidence/knowledge-sync-20261112-01/delivery-summary.json)。没有人工反馈自动接线、全库回填、新队列、定时任务、A/I 新检索或 Deep 动态检索。

## 归档后检查

2026-11-12 已归档并合并主规格 2 项新增／1 项修改。`--all --strict` 为 19/19，`--archived --strict` 为 15/15；21 个相关 Markdown 的 338 个本地文件目标均存在。见[封后回执](../../../../docs/operations/evidence/knowledge-sync-20261112-01/archive-closeout.json)。未重跑业务、嵌入或模型，最终 Git 与父项目引用随后一次同步，具体提交由远端读回确认。
