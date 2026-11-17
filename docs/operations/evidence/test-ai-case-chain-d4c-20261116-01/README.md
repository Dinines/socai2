# D4c 独立测试复核

2026-11-16，状态：本步保存流程复核通过，正文质量 **NOT_PASSED**。唯一执行包为[调查 real-01](../ai-case-chain-d4c-20261116-01/real-01/result.json)；测试模块只读该包，不运行第二批PG/Redis/HTTP/模型。最终[复核回执](saved-review-05.json)覆盖C01–C09共414项断言，这不是414个独立业务用例。原证据、227个运行源码/profile文件未改变。

| 实际验证 | 结果 |
| --- | --- |
| 原材料及任务 | 4条原告警/对象复制到新身份，起点无旧task/Run/Result；8任务、6Run、46步骤、134工件、2Result |
| 模型与注入 | 9次真实模型，69015 reported tokens；A1/I1/I2各一次本次响应前缀注入，完整原答另存同Run/step；严格回执只引用实际收到的片段，注入不是自然故障 |
| A/I→Case | A1缺evidence_ids不可用但I继续；I1仅首成员可用，Case先保存4成员和initial task、之后执行R1；A2真实有效分诊改变I输入，I2 none推动R2，不借旧I1替代 |
| 冻结与比较 | I选入4/实际保留1/Case4范围分开；C3保留prior_analysis角色；R1在后轮后不变；R2比较固定R1实际Result |
| 去重 | 两次新operation_key的显式check均skipped/no_changes，无Run；受控next_check_at周期扫描无多余Case；运行槽全部释放 |
| 完整业务执行 | 两轮C1–C6及Result真实完成；R1实际Deep一次，R2按条件无Deep；两次C6原答与保存结论、实际Result URL读回逐字一致，断言确实执行 |
| HTTP | 同包196 ASGI GET，全目录分页读取46步骤/134工件；metadata/artifact封套、availability、SHA、大小、正文及冻结源I五原件一致；25表只读前后摘要一致 |
| 当前配置与输入 | 各Run保存的policy仅tokenizer转发地址区别于当前发布配置；三个输入profile逐字匹配当前文件。实际messages不含批次/后台tenant_uid/执行身份，业务0、false、[]保留 |

模型原答全部来自本批真实调用。A1/I1/I2的截断/空答是明确的响应注入；Case日志依赖明确未配置，UEBA/knowledge/graph跳过且不是查空。此边界不能称为厂商或数据湖查询已验。费用未知，未记为0；测试侧新增业务连接及生成均为0。

## 独立质量记录

最终回执的`automatic_quality`逐项定位4条程序诊断：两轮C3各一次支持/反证同源；R1 C6影响范围缺依据；R2 C6支持/反证同源。来源是实际C3 stage-delivery的`$.quality.issues`及C6 delivery-detail的`$.citation_review.issues`，避免把多个封套重复计数。

`quality`另存3条人工观察，未计入程序自动诊断：

- R1、R2实际C6 member_aliases均把A2映射到05:46:12的process_start，A4映射到05:50:12的network_flow。原材料、实际输入、来源编号一致，A4实际晚4分钟；两轮原答及Result却均写成“早于”，属于明确正文错误。保存成功及accepted不证明该判断正确。
- I1完整原答member[1]写登录后8分钟启动进程，实际05:40:12→05:46:12为6分钟。真实I别名映射已核；该单元不在member[0]交付前缀内，未进入下游作为I材料。

两轮Result均accepted/uncertain/partial。原答、原Result及质量诊断保持；不重采样，不改成通过。

## 覆盖边界与复验

本步未部署21、未验TCP/浏览器、未重投Kafka、未执行ASGI POST或D5网络故障。I2运行中没有额外调用checker，不能声称该时点完成整链扫描；运行/待重试门控沿D4b直接证据。周期时钟是实际next_check_at的显式受控扫描，未实际等待4/6小时。

协调方负责静态追加46→47及后续根进展，测试未重复导入。本步不推动D5/D6，不提交推送。

[review_saved.py](review_saved.py)仅用标准库读保存文件，任何失败以新文件保存，禁止覆盖旧回执。命令：

```sh
.local/conda-envs/socai2/bin/python docs/operations/evidence/test-ai-case-chain-d4c-20261116-01/review_saved.py --bundle docs/operations/evidence/ai-case-chain-d4c-20261116-01/real-01 --output /tmp/d4c-new-review.json
```

历史复核保留：[01](saved-review-01.json)为相对CLI路径未resolve的启动错误；[02](saved-review-02.json)完成374项流程断言，当时`quality=[]`表示尚未附单独质量记录，不能理解为零质量问题；[03](saved-review-03.json)补配置/正文人工核对至412项；[04](saved-review-04.json)补自动诊断后因把原模型`alert_ref`误当标准化`alert_id`而失败，已有413项检查不丢弃；[05](saved-review-05.json)按真实原答字段修正，414项通过。所有复核均0新模型/数据库/HTTP执行，未改调查原包。
