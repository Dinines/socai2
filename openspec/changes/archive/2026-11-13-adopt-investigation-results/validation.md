# 采用接口交付验收

本项已完成本机/21 API与Swagger发布，发布后独立复核见audit.md。

- 调查聊天完成核心及HTTP接线：[原本机HTTP批次](../../../../docs/operations/evidence/case-result-adoption-http-20261113-01/http-01/verification.json)，20次请求、真实PG、0模型调用。
- 本聊天从已发布附件基底只叠加7文件，冻结源码与未修改基底见[清单](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/local-source-manifest.json)。候选18026再次用新合成Case验证20HTTP及SQL，结果见[回执](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/local-candidate/verification.json)。新判断/来源/覆盖/活动保存；原Result、任务、Run与处理状态保持；旧预览409、未完确认、幂等、历史分页及旧DTO422直接通过。
- [Swagger候选检查](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/docs-check.json)：64操作，原其他61合同保持；E19/E20仍501。139类型、655固定输出字段位置、35动态结构、562 JSON响应示例及26请求示例校验通过，另3CSV示例。最初文档示例误写finished_at已按实际ended_at修正，失败记录保留。
- 模型结果均为程序构造，只证明接口存取，不证明模型质量。核心自动采用时序复用已通过核心PG审计，未追加模型或复杂矩阵。
- 自动审批拒绝导出21数据库凭据与正式库新合成数据写入，理由是授权不明确；未执行这两项。21改做只读API/源码/运行版本核验，生产采用写入不另宣称实测。

发布为case-result-adoption-20261113-r1（本机-local），21镜像sha256:056c29bf8714018df5543cecad4a371b38c2ada3f0d510bfce8fc885eb35a42a；正式本机7GET、21已有Case 6GET均通过，21业务写入为0。两端docs13各9入口200、摘要与仓库/冻结包一致；7文件实际加载及36其他容器保持见[交付回执](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/delivery-summary.json)。只读脚本最初错从列表封套取Case字段，已修正为item.case；原失败保留。复制的驱动聚合日志中第6次请求对象被后续修改，逐次原始06-intent及409响应完整；保留原汇总与[差异说明](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/request-reconciliation.json)，未来驱动已改为深拷贝，没有重跑业务。主调查31/41及模型NOT_PASSED保持。
