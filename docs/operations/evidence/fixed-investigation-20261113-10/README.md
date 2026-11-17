# 最新固定调查保存读取闭环

2026-11-13，对应主调查字段梳理第32节。只在已有隔离Case上创建一个新Run，复用原A/I结果、三成员材料、明确事件关联、H第1版和已接受B01比较基线。没有新增Case、A/I或H，没有重派旧失败Run。

C3实际请求只要求五项业务答案，原答通过接收；程序从冻结材料和本Case的C2回执补第六项coverage。保存后按生产装配逻辑重建逐值一致，读取仍为六问。Deep不继承C3覆盖来源，C6按本步材料和回执生成覆盖。只改变模型内部输入/装配，HTTP字段、表及既有读取结构不变。

最终 **accepted / uncertain / partial**，综合结论为待复核，已成为第3版当前判断，新鲜度current。四次ASGI GET（Case、Run、Result、H）与真实隔离PostgreSQL保存一致。这是本机功能验收，不是生产/TCP部署验收，也不代表模型正文质量通过。

## 实际输入和原答

| 调用 | 程序导出的输入 | 原答及接收结果 |
| --- | --- | --- |
| 1 · C3 | [完整消息](flow/R01/review/call-01-C3-full-input.txt) · [业务材料 10302 字符](flow/R01/review/call-01-C3-input.txt) | [原答](flow/R01/review/call-01-C3-answer.txt) · 结构/引用接收 |
| 2 · C4.deep | [完整消息](flow/R01/review/call-02-C4-deep-full-input.txt) · [业务材料 11345 字符](flow/R01/review/call-02-C4-deep-input.txt) | [原答](flow/R01/review/call-02-C4-deep-answer.txt) · 结构/引用接收 |
| 3 · C4.deep | [完整消息](flow/R01/review/call-03-C4-deep-full-input.txt) · [业务材料 12197 字符](flow/R01/review/call-03-C4-deep-input.txt) | [原答](flow/R01/review/call-03-C4-deep-answer.txt) · source_not_in_model_input_or_duplicate |
| 4 · C6 | [完整消息](flow/R01/review/call-04-C6-full-input.txt) · [业务材料 17678 字符](flow/R01/review/call-04-C6-input.txt) | [原答](flow/R01/review/call-04-C6-answer.txt) · delivery_source_coverage_missing |
| 5 · C6 | [完整消息](flow/R01/review/call-05-C6-full-input.txt) · [业务材料 17678 字符](flow/R01/review/call-05-C6-input.txt) | [原答](flow/R01/review/call-05-C6-answer.txt) · 结构/引用接收 |

完整消息包括系统提示、业务正文、实际工具候选；纠错请求另含上一份原答及纠错材料。原请求及Schema在calls/和数据库快照中逐值一致，文本由程序导出，没有人工压缩或修改。C3为106来源，Deep授权/影响为106/107来源，C6为107来源；各步仍保留68条原成员事实，前序原文、H范围和指定基线可追溯。

## 接收结果与质量边界

- 授权Deep返回handoff/unresolved，没有选入无关可选知识。影响Deep重复引用N7_S8而拒收，失败及原答保留；其回答没有进入C6判断材料，C6仅消费有效授权Deep。
- C6首答影响范围列全三成员但缺A2依据；一次既有v9纠错后只将impact.alert_ids改为A1/A3，与该段进程启动/连接主张对应。其他正文及原支持引用逐值保持。没有程序替模型改答或新开Run追求接受。
- C2实际完成一次嵌入和9条检索，两个用途返回同一技术卡。程序合并后在C3、影响Deep和C6各显示一次，授权Deep不默认选入。所有原答均未结构化引用该卡，不据此宣称知识合理使用通过。
- 正文仍无充分依据断言自动化特征。M01-A/B、F01/F02保持 **NOT_PASSED**；不因接受、采用、current或程序coverage追认质量。[质量记录](quality.json)保留实际问题，不追加模型采样。

## 保存、旧件与4177

- Case：`7d3fe571-9871-5cf1-9c01-8680781573b4`。
- Run：`df15312d-e15c-4c39-bb62-97ea503132d9`；Result：`e5545ee7-f1ae-4ae0-830f-c3f2f6f9aa40`。
- 当前判断：`5cf8bf9f-c8a0-44e6-96e1-f0ae3eedbe7d`，第3版。旧12 Run、3 Result、2判断、原A/I指针/材料、任务/H、事件及成员关联逐值保持；55份09文件摘要保持。
- [4177最新批次](http://127.0.0.1:4177/index.html#180439cd6016b0a579cd9526961e226e20ca90f4f14a69683f7e23dcce478a99)已同步本机包及21静态站，两端只登记这1批；原展示完整移入备份。远端首页、详情、日志索引HTTP200，容器与服务源码保持。见workbench-local.json、workbench-remote.json；没有删除数据库/原证据或部署模型运行服务。

共5次生成、65,000tokens（51,442输入＋13,558输出），费用未知。沿用单Run6次/131,072tokens/1,500秒，无预算提高。首次SSH因沙箱禁止而在Run/模型执行前终止；原转发失败回执移入transport-attempt-01，获准网络执行后仅创建上述一个Run，结束关闭自建转发。没有unknown重派。

[review.json](review.json)核对五问→六问、事件有效I、旧行和保存读取；[实际请求验证](flow/R01/verification.json)核对材料、H、知识及前序来源。首个离线review忽略JSONB字段顺序，日志保留；改为调用同一C3字段选择器重建并先逐值比对冻结事实后通过，没有改业务源码/存储值或重跑模型。

[source-replay.json](source-replay.json)、source.patch、flow/plan.json冻结执行代码与配置摘要。重放应使用独立普通检出、新批次和明确私密profile，已结束批次不得再次执行run.py。无新增单测矩阵；程序直接检查及前后快照见[本轮修复](../case-c3-coverage-20261113-01/README.md)。主调查31/41保持，流式/队列/自动重算继续后置；本轮未提交、推送或发布模型运行服务。限定结束审计见audit.md。
