# 直接验收与交付状态

2026-11-12，用户继续指令后实施。基线 `dee94ea6`，分支 `V1.1`。没有调查 DDL、告警交接合同改动、自动消费开关变更或新检索服务。

## 已完成的直接检查

- 实施前及本地修改后 strict 通过；16 项定向检查通过，见[回执](../../../../docs/operations/evidence/knowledge-selection-20261112-01/direct-tests.xml)。复用知识原有检查，补同主题合并、适用／冲突／未知、判断材料对应、历史正文修订、模型去重／范围与依赖恢复；未跑全仓回归。
- Ruff 与 inspector JavaScript 语法检查通过。新增输入测试初次缺既有 selectors、第二次误将六问题合同缩为一项，均为测试材料构造错误；修正测试材料后通过，没有修改业务合同。
- [独立批次配置](../../../../tools/testdata/knowledge_selection/local.json)使用真实本地 PostgreSQL、现有本地嵌入转发与独立 Qdrant 验收集合；Case HTTP／处理／保存采用原业务实现，仅身份与模型传输沿既有本机适配。不是生产完整调查或真实业务历史。
- [知识 HTTP](../../../../docs/operations/evidence/knowledge-selection-20261112-01/local-flow/knowledge-http.json)：显式导入、同内容重复、旧卡索引／GET、一次演练反馈修订、新卡导入、旧卡仍可读、方法资料新副本导入、新卡与方法索引／GET 均成功。反馈版本以演练 SQL 准备，不冒充生产人工操作；旧原文、旧文档和旧批次保持。

## 一次 Case 与实际模型质量

新批次一个 Case/Run 已完成保存／HTTP GET，[汇总](../../../../docs/operations/evidence/knowledge-selection-20261112-01/local-flow-summary.json)及[数据库快照](../../../../docs/operations/evidence/knowledge-selection-20261112-01/local-flow/export/database.json)保留原输入／输出。原 3 份 C02 材料逐字段保持，5 次 Case HTTP 均成功。

C2 实际 9 个目的查询：6 个候选因条件冲突排除，2 个旧卡候选因来源已修订排除，5 条命中对应 3 个唯一块（方法原文分为 2 块、历史当前卡 1 张）。5 条查询全部筛除、1 条原始查空、3 条有数据。模型只见每块一份正文；历史卡、既往分诊、人工陈述保持三种独立角色，每份请求 5 个知识来源，跨目的重复正文合并 2 次。

共 6 次模型调用、119,412 reported tokens，包含既有 C3/C6 各一次纠正，未另开 Run。C3 首次 source_member_mismatch；纠正后部分接受，保留 observed_original_fields_exceed_statement_contract。两个 Deep 自然执行，前序引用没有丢失；本轮被接受结果未结构化引用知识，因此“知识依赖优先恢复”只由定向检查及代码支持，不能称真实模型流程已经覆盖该分支。C6 首次 duplicate_source，纠正后 delivery_source_coverage_missing，Result 为 partial/rejected、conclusion=null。仅 C3 首次原答结构化引用了知识，其余未见结构化引用；正文提及与结构化引用分开。**模型质量 NOT_PASSED，未新增采样，也不把上述拒收写成已修复。**

流程后检查 V1 可空列发现判断 rationale 可为 null，补一处空值判定；仅定向复验该资格检查通过，未重跑模型。独审随后补齐配置化 Deep 可选 purpose（方法／历史；依赖仍优先），一个选择／依赖断言通过，不再调用模型。源差异见 [delta](../../../../docs/operations/evidence/knowledge-selection-20261112-01/post-flow-source-delta.json)，流程冻结 hash 和原快照不改写。

4177 已从保存快照追加本批，本地 66→67 条，保留已有记录；新页包含候选筛除、合并出处、未送入原因及原答引用，JavaScript 语法通过。21 正式静态记录从 38→39 条，79 文件及 80 HTTP 内容读回通过，原记录／文件及容器保持。浏览器经本机 SSH 转发实际查看知识节点与纠正后 C3 节点，确认筛除原因、合并出处、两次重复正文省略及“进入输入／未见结构化引用”分别显示，见 [UI 回执](../../../../docs/operations/evidence/knowledge-selection-20261112-01/ui-readback.json)。

## 发布与范围

本地限定独审 [audit.md](audit.md) 通过后，已一次实际发布 `v1.2-20261112-r3`，处理镜像 `processing-20261112-r2`。API 和工作台各切换一次，fusion／agents／projection／litellm 容器身份保持；current 指针、处理入口、源清单及实际配置已读回。模型阶段用途、12,000／8,000／8,000 字符预算、各目的 8 候选及适用字段实际加载，见 [loaded-selection](../../../../docs/operations/evidence/knowledge-selection-20261112-01/loaded-selection.json)。

首次冻结 r2 的 preflight 因预期 API 镜像及 Compose 来源仍指向前一批而失败，发生在任何 rollout 之前；核实真实 r1 基线后重新冻结 r3，保留 r2 失败回执及目录，复用已核好的处理镜像。没有因此二次切换线上服务，见 [发布计划修正](../../../../docs/operations/evidence/knowledge-selection-20261112-01/release-plan-correction.json)。

封后仅将仓库清单的描述字段 `processing.image` 对齐已部署 profile 的 `fc646d…`；实际处理入口一直读取 `production-v1.2.toml [image].id`，不是该旧描述值。已冻结 release／manifest 和回执保留，无服务或运行配置变化，见[元数据修正](../../../../docs/operations/evidence/knowledge-selection-20261112-01/release-metadata-correction.json)。

生产完成 7 次业务 HTTP：历史已有卡 3 次入库／索引／GET 保持原身份；一份带适用条件的原文方法资料分成 2 块，4 次导入／索引／GET 通过。另以保存查询做 3 个目的的只读 C2 adapter 检索，返回 5 行（历史 1 卡，两个目的各 2 个方法块）；嵌入调用真实，没有生产新 Case、Run 或分析模型。临时 key 已撤销并读到 401，账号角色保持。完整入口见[交付回执](../../../../docs/operations/evidence/knowledge-selection-20261112-01/delivery-summary.json)。发布独审与封后记录见 [release-audit.md](release-audit.md)。

本次未触及容量限制；C3 附加工具目录和实际 token 测量超限沿原显式失败，没有新增裁减能力。F02 召回正文相关性／合理采用及 M01 持续模型质量不因条件筛选测试通过而核销。未扩展 A/I 新检索、Deep 动态再检索或自动入库。归档和最终 Git／父项目引用按实际完成记录，不用发布成功代替模型质量通过。

2026-11-12 封后：本 change 已实际归档，三个既有主规格增加四项要求；strict --all 为 19 项通过，--archived 为 14 项通过。变更文档链接已核，未重跑业务／模型。见 [closeout.json](../../../../docs/operations/evidence/knowledge-selection-20261112-01/closeout.json)。最终提交和父项目 server 引用由推送后的远端读回确认。
