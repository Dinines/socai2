# 比较引用修复的一次真实核验

2026-11-13。按[09批OpenSpec计划](../../../../openspec/changes/complete-socai2-investigation-chain/fixed-flow-plan.md#比较引用修复的一次真实核验2026-11-13)，在08同一隔离Case上执行一个新固定Run。原A/I、三成员材料及H第1版保持，指定已接受的08 B01 Result作比较。没有重派08失败Run，也没有新增Case、H或A/I。

C6首答已引用指定基线；一次v9纠错后通过结构与引用接收，得到 **accepted / uncertain / partial**，已保存并成为当前判断，输入新鲜度为 **current**。正文质量仍 **NOT_PASSED**：比较说明无依据地宣称本轮材料更充分，名称推自动化等旧问题保持。两者分别记录，不核销主调查31/41。

## 实际输入与原答

| 环节 | 程序生成的实际输入 | 原答与结果 |
| --- | --- | --- |
| C3 初步解释及必要补查 | [10,182字符](flow/R01/review/call-01-C3-input.txt) | [原答](flow/R01/review/call-01-C3-answer.txt)通过结构/引用校验；仅提出授权补查 |
| Deep 授权问题 | [11,921字符](flow/R01/review/call-02-C4-deep-input.txt) | [原答](flow/R01/review/call-02-C4-deep-answer.txt)为handoff/unresolved，没有执行新的现场工具查询 |
| C6 综合结论 | [13,526字符](flow/R01/review/call-03-C6-input.txt) | [首答](flow/R01/review/call-03-C6-answer.txt)因结论依据重复N5_S7拒收；[纠正答](flow/R01/review/call-04-C6-answer.txt)通过 |

C3/C6保留68条成员事实；进入C6的C3概要、发现、业务问题及矛盾均来自本Run，原文、成员及映射后的依据逐项相符。H原文、版本、范围及附件保持。文本由程序从实际保存请求导出，没有手工压缩或改写。

C6明确标注`指定比较基线引用=[N5_S93]`，首答及纠正答均引用它。本次C6没有同一Result的背景别名，所以没有实际覆盖“同文背景＋指定基线并存”分支，也没有触发缺基线/当前依据诊断；这些分支仍以[08批离线核验](../fixed-investigation-20261113-08/README.md)为证。不能把这一Run写成v9所有分支均已真实通过。

v9只反馈实际存在的重复引用，未增加纠错轮数。原答差异仅在`conclusion.support_ids`：删除一份重复N5_S7，同时删除N5_S73检测概要引用；其他正文和比较完全不变。没有由程序替模型改答。原始完整请求包含提示/Schema，纠正请求还包含首答及反馈，均保存在`flow/R01/calls/`及数据库快照中。

## H、知识与正文质量

C3/C6结构化引用H，保留不同来源IP、启动不等于完成和人工核查不等于授权的边界；最终结论与所选B01逐字相同。新的采用状态和current只证明本轮消费、保存与新鲜度计算，不能证明H已得到充分合理利用。

C2实际一次嵌入、9条检索，技术解释和取证指导返回同一AN0846卡。程序合并为448字符正文，每份实际输入仅出现一次；C6两答引用知识，C3/授权Deep未引用。卡可以解释Get-LocalUser，但不能证明授权或旧、新结论的材料差异；合理使用F02仍未通过。下一步先离线核查授权Deep是否需要这张卡，并区分必要前序依赖与仅因成员重合选入的知识。

完整评审见[quality.json](quality.json)。持续问题记录后置，不再追加模型采样。与08相比，本次前序回答、查询时点和输入选择依赖均可能不同，不是受控A/B，不能由本例报告稳定成功率或准确率。

## 保存、读取与重放

- Case：`7d3fe571-9871-5cf1-9c01-8680781573b4`。
- Run：`6c18ba08-7d88-4b34-b301-84e8e8757af5`；Result：`8d7ef196-a3eb-4af8-b0eb-748d5a8bbecf`。
- 新当前判断：`d83b6c37-cbc5-4c8a-b734-1c9114b41c96`，第2版；此前B01判断为stale/human_feedback_changed，本次为current。
- 比较基线：08 B01 `24d81409-c5ce-47a4-9740-bd7666195337`；H：`a560b884-441d-4b84-9970-60352f40a723`，第1版。

真实隔离库`v12_upgrade_dev`。4次模型请求/原答与数据库一致；原ASGI Case、Run、Result、H共4次GET均200且与保存结果相符，这不是生产或TCP发布验收。前两Run、Result、旧评估及任务/H行逐值保持，A/I当前指针未变；137份08批文件摘要未变。本机4177静态包83→84，在线4177和模型服务未发布。

共4次生成、50,394tokens（37,771输入＋12,623输出），另有嵌入552输入tokens；费用未知。沿用单Run6次/131,072tokens/1,500秒，无预算提高、额外Run或单元测试。自建知识转发在Run结束后关闭。

[review.json](review.json)记录纠正差异、旧行保留和新鲜度；[verification.json](flow/R01/verification.json)记录材料、知识及新C3来源。`summarize.py`、`verify.py`、`review.py`只处理已保存文件；[source-replay.json](source-replay.json)及`source.patch`冻结实际执行源码，重放应使用独立普通检出和新的批次配置。`run.py`是有副作用的入口，已结束批次不得重派。私密配置不打包，原失败保留。

[限定结束审计](audit.md)与[验证回执](validation.json)记录本批边界。本批未修改业务实现、HTTP字段、数据库表或部署配置；不提交、推送、发布或推进流式更新。
