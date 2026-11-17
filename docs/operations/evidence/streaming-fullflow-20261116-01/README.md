# 新用例完整流程测试（2026-11-16）

本批 `streaming-fullflow-20261116-01` 在21正式 `aisoc` 执行。运行与保存读取已完成，部分交付；模型质量、输入边界和整个change不记通过。负责人随后明确：引用/范围、不适用领域缺少限制说明及重复引用作为问题记录，不中断后续；`tenant_uid`须过滤，并实现截断/异常时保留可用输出及页面回执。后续改动不改写本批历史。

## 已执行与实际结果

| 环节 | 实际结果 |
| --- | --- |
| 入站 | 4告警/13上下文；各单次ACK，湖原文读回一致；同一事件4成员 |
| A/I | 4次分诊、2次诊断完成；原答和引用检查保留 |
| 整案首轮 | 3成员、C1–C6；C6不适用领域limitations为空，`unapplied_domain_needs_limitations`拒收，partial/unavailable |
| 单案首轮 | 1成员、1轮；accepted/uncertain/partial；C6重复引用 |
| 整案后轮 | 4成员、2轮；accepted/uncertain/partial；C6两项发现成员引用覆盖不足 |
| 上一轮 | 指向真实首轮Run，但结论拒收，`previous_conclusion_unusable`，没有可比较Result |
| 无变化检查 | 新task实际skipped/no_changes，0attempt/Run，原Run和工件逐项不变 |
| 保存/HTTP | 33项保存检查、233GET及187份正文逐项一致；10任务/9Run/80步骤/225工件 |
| 页面 | 4177 revision1；实际切首轮/后轮，3/4冻结成员及各自201/202任务正确；两轮C6可见原答SHA与已保存字节一致；紫色测试、领域名称、跳过原因可见 |

I为4小时、Case为6小时周期，本批没有等待到时；增量通过真实HTTP `mode=check` 分别触发I与整案，任务source=user。自动周期到时和有效结论正向比较均未覆盖。背景日志先读回再投告警仅为本批投放顺序，不是业务入站前置。未接入UEBA/graph仍为未接入；威胁情报/历史告警在C2为证据补查预留工具额度而未查。

## 模型原始输入输出

16次生成均`stop`，尾部0空白，总tokens 144021；费用未知。A/I/Deep8192、C3/C616384，模型窗口65536；未更改容量。20条引用检查记录包含诊断和重复存储，不能称20个独立正文错误。全部16次实际输入都有`tenant_uid`；固定中性告警源及本次扫描的测试/答案标记未见，但输入边界仍未通过。

| 阶段 | Run | 输入tokens | 输出tokens | 原始输入 | 原始输出 |
| --- | --- | ---: | ---: | --- | --- |
| A | `7e2f68f4-393f-5dde-ab74-36ac0f866e65` | 1310 | 363 | [输入](models-final/7e2f68f4-393f-5dde-ab74-36ac0f866e65-05-A/input.txt) | [输出](models-final/7e2f68f4-393f-5dde-ab74-36ac0f866e65-05-A/output.txt) |
| A | `4a4f2e4c-2e2a-5e18-b1fc-4b9c0f98ee84` | 1583 | 325 | [输入](models-final/4a4f2e4c-2e2a-5e18-b1fc-4b9c0f98ee84-05-A/input.txt) | [输出](models-final/4a4f2e4c-2e2a-5e18-b1fc-4b9c0f98ee84-05-A/output.txt) |
| A | `dcbc8991-723b-5ae0-8af8-a21be78515a1` | 1855 | 319 | [输入](models-final/dcbc8991-723b-5ae0-8af8-a21be78515a1-05-A/input.txt) | [输出](models-final/dcbc8991-723b-5ae0-8af8-a21be78515a1-05-A/output.txt) |
| I | `015358ab-c7f4-576e-b67d-9c57b7cfb07e` | 3679 | 1513 | [输入](models-final/015358ab-c7f4-576e-b67d-9c57b7cfb07e-02-I/input.txt) | [输出](models-final/015358ab-c7f4-576e-b67d-9c57b7cfb07e-02-I/output.txt) |
| C3 | `f21248be-39eb-4832-8d87-866d7f62d40d` | 7523 | 3305 | [输入](models-final/f21248be-39eb-4832-8d87-866d7f62d40d-11-C3/input.txt) | [输出](models-final/f21248be-39eb-4832-8d87-866d7f62d40d-11-C3/output.txt) |
| C4.deep | `f21248be-39eb-4832-8d87-866d7f62d40d` | 7557 | 215 | [输入](models-final/f21248be-39eb-4832-8d87-866d7f62d40d-13-C4-deep/input.txt) | [输出](models-final/f21248be-39eb-4832-8d87-866d7f62d40d-13-C4-deep/output.txt) |
| C4.deep | `f21248be-39eb-4832-8d87-866d7f62d40d` | 8499 | 703 | [输入](models-final/f21248be-39eb-4832-8d87-866d7f62d40d-15-C4-deep/input.txt) | [输出](models-final/f21248be-39eb-4832-8d87-866d7f62d40d-15-C4-deep/output.txt) |
| C6 | `f21248be-39eb-4832-8d87-866d7f62d40d` | 9653 | 4600 | [输入](models-final/f21248be-39eb-4832-8d87-866d7f62d40d-19-C6/input.txt) | [输出](models-final/f21248be-39eb-4832-8d87-866d7f62d40d-19-C6/output.txt) |
| C3 | `ac9fcc38-69c5-49c2-9547-aa5bba5d33be` | 4633 | 3080 | [输入](models-final/ac9fcc38-69c5-49c2-9547-aa5bba5d33be-11-C3/input.txt) | [输出](models-final/ac9fcc38-69c5-49c2-9547-aa5bba5d33be-11-C3/output.txt) |
| C6 | `ac9fcc38-69c5-49c2-9547-aa5bba5d33be` | 8359 | 3678 | [输入](models-final/ac9fcc38-69c5-49c2-9547-aa5bba5d33be-17-C6/input.txt) | [输出](models-final/ac9fcc38-69c5-49c2-9547-aa5bba5d33be-17-C6/output.txt) |
| A | `fc139e35-c30e-5f93-9fdb-6a4f724b7946` | 2069 | 389 | [输入](models-final/fc139e35-c30e-5f93-9fdb-6a4f724b7946-05-A/input.txt) | [输出](models-final/fc139e35-c30e-5f93-9fdb-6a4f724b7946-05-A/output.txt) |
| I | `810a4920-65e4-5599-948e-fb314a49a4b9` | 5091 | 1805 | [输入](models-final/810a4920-65e4-5599-948e-fb314a49a4b9-02-I/input.txt) | [输出](models-final/810a4920-65e4-5599-948e-fb314a49a4b9-02-I/output.txt) |
| C3 | `873af97c-559f-46f3-a454-d8e4f92d0672` | 9168 | 5657 | [输入](models-final/873af97c-559f-46f3-a454-d8e4f92d0672-11-C3/input.txt) | [输出](models-final/873af97c-559f-46f3-a454-d8e4f92d0672-11-C3/output.txt) |
| C4.deep | `873af97c-559f-46f3-a454-d8e4f92d0672` | 12340 | 171 | [输入](models-final/873af97c-559f-46f3-a454-d8e4f92d0672-14-C4-deep/input.txt) | [输出](models-final/873af97c-559f-46f3-a454-d8e4f92d0672-14-C4-deep/output.txt) |
| C4.deep | `873af97c-559f-46f3-a454-d8e4f92d0672` | 13116 | 545 | [输入](models-final/873af97c-559f-46f3-a454-d8e4f92d0672-16-C4-deep/input.txt) | [输出](models-final/873af97c-559f-46f3-a454-d8e4f92d0672-16-C4-deep/output.txt) |
| C6 | `873af97c-559f-46f3-a454-d8e4f92d0672` | 15222 | 5696 | [输入](models-final/873af97c-559f-46f3-a454-d8e4f92d0672-20-C6/input.txt) | [输出](models-final/873af97c-559f-46f3-a454-d8e4f92d0672-20-C6/output.txt) |

## 证据入口

- [最终快照](final-pg.json)、[保存核对](saved-validation.json)、[HTTP核对](http-readback-final/validation.json)。
- [模型用量和引用记录](model-summary-final.json)、[16份实际输入残留](input-residual-review-final.json)。
- [4177发布](viewer-publish-receipt.json)、[浏览器实测](viewer-browser.json)、[可见原答比对](viewer-verification.json)。
- [本地静态导出](static-export/)，沿既有update_processing_audit导入，历史卡保留，现43卡。
- [r3必要修正独立审计](independent-audit.md)；本批结束审计另见fullflow-audit.md。

本批未提交/推送；r3 Fusion/联合调度运行，r2旧处理容器保持停止；HTTP/Swagger/4177沿现有版本，其他服务未改变。
