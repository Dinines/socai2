# H反馈后固定调查的保存与读取

本批补核上一批[H/指定比较/原计划输入选择](../case-human-input-20261113-01/README.md)的保存读取接线。复用既有一条正常H后调查场景，真实连接本机隔离PostgreSQL `v12_upgrade_dev`，全部告警/事件/Case模型、Token计量及外部查询均为替身。没有真实模型调用、生产服务发布、HTTP/表合同修改或流式更新。本轮没有发现新的业务代码缺口，只扩充已有场景和修正验证脚本。

## 已完成的链路

先在独立合成Case形成首轮结果，再保存H第1、2版。保存H没有创建或启动Run；显式prepare/start后，下一轮冻结第2版，并指定首轮结果比较。C3、两次Deep请求和C6各保留一次第2版原文、原范围和材料附件；第1版仍可读取，没有混进本轮输入。1份材料附件对应2个可见字段，不是2份独立证明。

C3把H引用带入待核问题和原补查计划；C6原计划仍绑定实际初始C3，目标、所需材料和3个依据逐一对应原引用。指定基线为accepted旧Result，同一结果的冻结副本和比较来源共用展示，两种原引用仍保留。替身C6输出uncertain结论，引用H及指定基线；人工作为`human_statement`保存，没有升级为原始观察或授权证明。

最终Result为 **accepted / uncertain / partial**，变化类型`unchanged`，当前判断已采用同一结论。`accepted`表示接收校验通过，`partial`保留待核及交付限制；这些均不是实际模型判断质量通过。H版本、结果详情和当前判断均经原ASGI HTTP处理器与真实库读取；没有网络TCP/部署验收。

| 对象 | 本批已完成记录 |
| --- | --- |
| Case | `94f1021a-70e4-46ce-a56d-780527ec9e48` |
| H后的Run | `36d2d7b7-9303-4427-9b9a-c506c55342a2` |
| 新Result | `781c249e-d114-4054-9cf2-a09a04465d23` |
| 指定旧Result | `31fcd182-d58e-43b8-95d9-f671c893941b` |

## 从保存请求逐字导出的输入

以下是本批合成材料实际送到替身的请求正文，不是重建预览或真实模型调用；与上一批C01的材料不同，不比较压缩率。

| 环节 | 完整正文 | 字符数 |
| --- | --- | ---: |
| C3 | [完整输入](inputs/C3-model-input.txt) · [H/比较片段](inputs/C3-H-comparison-plan.txt) | 4,080 |
| Deep查询前 | [完整输入](inputs/Deep-01-model-input.txt) | 3,894 |
| Deep查询后 | [完整输入](inputs/Deep-02-model-input.txt) | 4,928 |
| C6 | [完整输入](inputs/C6-model-input.txt) · [H/比较/计划片段](inputs/C6-H-comparison-plan.txt) | 7,935 |

完整请求、Schema和来源映射随输入保存；[输入摘要](inputs/summary.json)、[数据库快照](pg-02/database.json)、[结果GET](pg-02-readback/result-get.json)、[当前Case GET](pg-02-readback/case-get.json)、[H原引用及两版GET](pg-02-readback/H-reference-readback.json)可相互追溯。

## 必要复验与原失败

只扩充一个既有场景，没有回归矩阵。实际有两次数据库尝试和一次只读尾段补核，失败不改写：

- [pg-01](pg-01/checks.json)：测试替身误从`source_map`读取只在记录上存在的`context_kind`，在第二轮C3生成答案前中断。首轮结果、H版本、请求及unknown Run均保留，没有重派。
- [pg-02](pg-02/checks.json)：两轮固定调查完成，结果及当前判断GET通过；最后验证脚本误把简版报告当成包含比较/引用的完整交付工件，报`KeyError: comparison`。原检查仍记failed，不伪造整项通过。
- 修正读件位置后，直接对pg-02已有记录运行[只读尾段检查](pg-02-readback/validation.json)：完整交付的H/比较引用、两版H GET、新Result GET和当前判断GET通过。连接强制只读，没有第三次完整流程、没有新增Run或模型派发。

离线导出最初两次读错上下文和阶段位置，均在写出输入前失败，见`extract-01-error.json`、`extract-02-error.json`；修正后按冻结C1 Schema及RunStep取数，程序导出和原计划映射核对通过，不访问数据库。

本机4177静态包追加两份Case快照，73→75，保留unknown与成功记录；没有发布21或声称在线入口已复验。脚本/配置/源码指纹与限定审计见[validation.json](validation.json)、[audit.md](audit.md)。主调查仍31/41，3.16真实模型效果、M01/F02及完整固定流程质量不由替身存取闭环核销。
