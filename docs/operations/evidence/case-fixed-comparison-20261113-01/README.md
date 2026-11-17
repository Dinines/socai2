# 不可用历史比较由程序固定装配

2026-11-13。[07批真实C6](../fixed-investigation-20261113-07/README.md)已经输出not_comparable，却仍在说明中声称与历史一致。程序在请求前已知道指定Result不可用，无需再让模型生成这一固定事实。本批只收好该职责边界，不追加真实生成调用。

## 处理规则

- 新C6没有可用的指定历史综合结论：程序在冻结边界保存版本、原选择及完整比较值，输入给简短说明，输出Schema去掉comparison；适配器恢复冻结值。初次调查仍为initial/null；其余不可比情况为not_comparable、配置的固定说明及空引用。
- 有可用指定Result时：比较字段仍由模型结合历史结论与本轮材料生成，保持原引用和范围校验。
- 模型擅自输出程序固定字段时拒收，不静默改掉模型原答。旧冻结边界没有新标记，按旧规则解析，历史已保存说明不改写。

这属于内部模型边界和配置变化，HTTP的change_kind/change_summary字段、含义与数据库表均保持。没有新增自动重算、调度或语义判断器。

## 输入与保存读取

| 材料 | 性质与结果 |
| --- | --- |
| [新C6输入](after/C6-model-input.txt) / [完整请求预览](after/C6-request-preview.json) | 从07原件用当前程序重建，17,116字符；仅离线预览，未派发模型 |
| [C3输入](after/C3-model-input.txt) | 与07实际C3业务输入逐字一致，10,894字符 |
| [实际替身C6请求](pg-C6-request.json) / [原答](pg-C6-raw-answer.json) | 一条隔离库验证，模型原答没有comparison，程序填入冻结值 |
| [Result及GET对照](pg-comparison-readback.json) | not_comparable及固定说明保存/GET一致，当前判断结论与Result一致；旧拒收Result保持 |
| [旧真实末答回放](legacy-answer-check.json) | 07无标记原答仍按旧规则接受，原错误比较说明保持；质量仍NOT_PASSED |

直接检查4项通过：initial、not_selected、unavailable三个状态的新旧边界，以及可用历史继续比较。仅补一条真实隔离PostgreSQL替身场景，先保存一个拒收基线，再显式创建新Run选择它；C3/Deep/C6和查询均为替身，未新增真实模型调用。

隔离Case `77226457-aed2-49a3-8895-022dc4e7433a`；第二Run `06b0c14c-1072-4db7-80ef-5dc53158c60a`；新Result `0fd2354c-c6f2-4721-97c0-1e4eded34318`为 **accepted / uncertain / partial**。旧拒收Result `0af49228-bdac-4988-8f23-36b43f0e1156`未修改。使用原ASGI GET处理器与真实数据库核对，不代表TCP、生产或真实模型质量验收；本替身Case只关联告警，未用它证明事件关联链路。

## 证据边界与重放

[verification.json](verification.json)核07批33份原流程文件不变、旧答兼容、新输入Schema和保存读取。前批06的115份文件由07批review另核，未重写旧失败、采用或未知状态。4项检查及一次PG流程回执见[validation.json](validation.json)、[pg-01/checks.json](pg-01/checks.json)。

首次4177导入严格拒绝全测试快照中未关联本Case的合成I；保留[原错误](processing-audit-update.json)和[完整测试快照](pg-01/database.json)。随后只读按实际Case关联范围另捕获展示快照，不改数据库关联。采集脚本首轮JSON字面量被SQLAlchemy误识别为绑定参数，在查询前失败，保存在[capture-attempt-01.json](capture-attempt-01.json)；修正驱动参数后仅补只读捕获。新[workbench-export](workbench-export/manifest.json)严格导入通过，本机静态包80→81，在线4177未发布。

可离线运行，不连接模型或数据库：

```bash
.local/conda-envs/socai2/bin/python docs/operations/evidence/case-fixed-comparison-20261113-01/verify.py
```

`rebuild.py`按preview-config生成明确的新配置预览，已有工件不一致会拒绝覆盖。`run_persistence.py`仅用于新的独立隔离库验证，需要显式私密profile和新输出目录，不能重派既有批次。[源码包](source-replay.json)记录基点及全部相关未提交模型文件，在独立普通检出中复放，不覆盖当前工作区。

[限定独立审计](audit.md)只覆盖本次程序职责、旧答兼容、07真实运行和一次替身保存读取，不替代主调查结束审计。比较字段的程序修复不意味着其他模型正文正确；知识合理使用、名称推自动化、未查写查空仍未通过。本地修改未部署，主调查31/41、流式后置保持。
