# 2026-11-14 三案固定调查展示

状态：三案已执行、保存、读回并同步本机/21的4177及前端4173。1案 accepted/uncertain/partial 并采用，2案 rejected/unavailable/partial 未采用；模型质量 **NOT_PASSED**，不因展示完成追认质量通过。

[4177三案记录](http://127.0.0.1:4177/index.html) · [前端demo](http://127.0.0.1:4173/#/cases) · [范围及直接验收](../../../../openspec/changes/complete-socai2-investigation-chain/showcase-validation-20261114.md) · [程序汇总](comparison.json) · [配置](config.json)。前端保留原有样例，三案为最新创建记录；搜索 `fixed-investigation-20261114-01` 可只看本批。只读快照不冒充实时API或21生产数据。

## 实际结果与对照

| 案例 | 输入差异 | 实际结果 | 查阅 |
| --- | --- | --- | --- |
| C01 基础调查 | 登录、外联、进程启动3成员；本批新A/I | C3、两次Deep、C6均通过接收；结论待复核、部分交付，已自动采用为当前判断 | [4177](http://127.0.0.1:4177/index.html#689d783554c3b8cb92d5416899594e241cdeba23e93adde125b6bf2a98d3bf11) · [demo](http://127.0.0.1:4173/#/cases/socai2!isolated_local_pg_real_model_new_AI!fixed-investigation-20261114-01!00000000-0000-0000-0000-000000000001!case!06480fc3-706a-5a00-b687-4754a693d0b4/case-info) · [汇总](flow/C01/summary.json) |
| C02 限定人工反馈 | 共用C01事实和A/I，仅进程启动增加授权H；不确认命令完成，也不覆盖登录、外联 | C3达到4096输出token上限截断；C6一次纠正后仍缺依据及范围匹配，综合结论拒收/null，未采用 | [4177](http://127.0.0.1:4177/index.html#bde7d9690af79510c581181af64d819d826240e039567c7d7326923b0b7f2152) · [demo](http://127.0.0.1:4173/#/cases/socai2!isolated_local_pg_real_model_new_AI!fixed-investigation-20261114-01!00000000-0000-0000-0000-000000000001!case!04e4dca8-edca-5623-8e31-5fc0c58180d9/case-info) · [汇总](flow/C02/summary.json) |
| C03 材料不足 | 单条网络连接，独立新A/I，无进程/登录/H | C3、两次Deep有结果；C6两答建议均重复引用，一次纠正后仍拒收/null，未采用 | [4177](http://127.0.0.1:4177/index.html#a36ea8cf7ced19a5e6171b846cdce0c75e31c6fbefb0ddb11dd02609388b7bde) · [demo](http://127.0.0.1:4173/#/cases/socai2!isolated_local_pg_real_model_new_AI!fixed-investigation-20261114-01!00000000-0000-0000-0000-000000000001!case!3215fde7-d21a-5797-9be7-414d8ea0f48a/case-info) · [汇总](flow/C03/summary.json) |

共4个新A、2个新I、3个新Case Run，19次真实生成，usage为105,413输入+35,108输出=140,521 tokens，费用未知/unpriced。每个Run只执行一次，沿现有有界纠正，未追加质量采样、扩预算或重跑全仓测试。

E01登录A两答引用重复，最终failed/alert_answer_source_invalid；另外3个A和2个I保存完成。I及Case继续使用原始登录事实，不伪造有效A判断。各次实际请求/原答与185份保存工件逐一匹配，三案共20次ASGI GET读回与真实隔离PG快照一致；鉴权/依赖覆盖明确存在，不能据此称正式TCP或鉴权验收。

C01/C02共享同一批事实与A/I，但检索背景可能随前案保存变化，仅为功能对照，不是受控A/B。材料复制自既有合成原件，H为明确标注的模拟陈述，没有独立真值，不报准确率。

## 模型实际输入和已知质量

输入均由当前任务模板/字段选择程序生成，再从网关请求和落库工件核对导出；没有手工压缩或改写原答。每个review目录含输入、完整messages+Schema和原答；纠正请求也单独保留。

| 环节 | 实际输入示例 |
| --- | --- |
| 告警A（登录，首次失败） | [输入](flow/E01/A1/review/call-01-input.txt) · [完整请求](flow/E01/A1/review/call-01-full-input.txt) · [原答](flow/E01/A1/review/call-01-answer.txt) |
| 事件I（3成员） | [输入](flow/E01/I/review/call-01-input.txt) · [原答](flow/E01/I/review/call-01-answer.txt) |
| C01 C3 / Deep / C6 | [C3](flow/C01/review/call-01-C3-input.txt) · [Deep](flow/C01/review/call-03-C4-deep-input.txt) · [C6](flow/C01/review/call-04-C6-input.txt) |
| C02 H进入C3/C6及纠正 | [C3](flow/C02/review/call-01-C3-input.txt) · [C6](flow/C02/review/call-02-C6-input.txt) · [纠正完整请求](flow/C02/review/call-03-C6-full-input.txt) |
| C03 C3/C6及纠正 | [C3](flow/C03/review/call-01-C3-input.txt) · [C6](flow/C03/review/call-04-C6-input.txt) · [纠正完整请求](flow/C03/review/call-05-C6-full-input.txt) |

C01/C02实际请求含选入知识，C03未选入知识；进入请求不代表模型合理使用。C02 H原文、版本和限定范围与保存/GET一致，原答也区分进程与登录/外联，但整案拒收，不能报H流程质量通过。

仍见凭主机/用户名推自动化、把synthetic标签当性质依据、把进程启动扩大为完成动作等问题。C03最后一答的第二项建议重复同一引用32次；C02除缺依据还出现成员覆盖和来源错配。保留在原答/校验/局部交付中，按负责人决定后置，不修改原件追认成功。C3截断列为后续输出预算/结构评估项，本批不重派。

## 页面同步与保留范围

- 4177先备份旧静态目录，再清空列表；逐案导入后最终仅3条。本机与21相同，最终211份文件、首页/3详情/3日志索引共7项HTTP读回通过；容器、运行源码和数据库保持。[最终回执](site-after-C03-remote.json)。旧展示位于配置指定的本机 `.local/workbench-archive/…/before-cases/site-before` 和21私密目录，数据库与历史批次未删除。
- 4173复用既有适配器从三案真实快照生成[数据文件](../../../../prototypes/security-pages-v2/socai2-recorded-fixed-investigation-20261114-01.js)，共享A/I按原tenant/id和整行相等合并；4告警、2事件、3Case、9Run。只增加数据及index引用，原有样例和浏览器编辑保留。[导出来源](demo-export/source-snapshots.json) · [生成回执](demo-export/publication.json)。
- 浏览器已核三类列表、C01采用判断、C02/C03空判断、C02已完成H原文及版本、A/I和部分交付显示。4177已见三案及C03两次C6失败节点。[页面核对](demo-export/ui-review.json)。这是直接查阅验证，不是产品页面全量验收。

首次C01静态同步遗漏嵌套logs/index.html，原404[失败回执](site-after-C01-failure.json)保留。定位为本批打包器误跳过所有index.html，改为只跳根首页后以新发布标签补齐，后续两案正常；没有重跑模型。

## 保留与重放

每案flow目录保留执行intent、网关calls、tokenizer、模型原答、执行回执、真实PG快照、ASGI读回和逐调用review。源码/策略/工具与配置通过归档和SHA保留，私密凭据文件不打包。

准备阶段路径修正的旧plan及源码在preparation-v1归档中。C02的模拟反馈时间笔误在H保存/派发前按原始材料修正，见[修正记录](C02-fixture-time-correction.json)；原材料、已结束A/I/C01都未改。C01使用[当时plan引用](flow/C01/plan-reference.json)及replay-source-through-C01.tar.gz，C02/C03使用各自plan-reference及replay-source.tar.gz。

离线核对可运行 `summarize.py --scenario C01|C02|C03` 和 `finalize.py`，只读取已结束证据并要求已有输出完全相同。需要新的真实重放时复制驱动/配置到**新批次**，改batch/output/remote_evidence_dir和明确环境后依次prepare、preflight、seed、stages，再逐case/export；不能对本批已结束Run重派。不要为离线回看执行site clear或覆盖既有demo文件。

本批未改HTTP合同/数据库表、未发布调查核心、未恢复自动消费者、未实施流式或H-only C6、未提交推送Git。主调查31/41、质量NOT_PASSED保持。
