# 观察字段装配与最终依据纠错

本轮修正固定06批暴露的两处程序问题：C3观察原值重复展开导致保存字段超限，C6单个影响段缺依据却重发全量目录。复用6份原答离线对照，并执行1条已有隔离库替身存取流程；**真实模型零调用**，原06批失败和Result不改写。

## 程序处理结果

| 对象 | 原问题 | 本次处理及边界 |
| --- | --- | --- |
| B01 C3两份原答 | 同一发现27个原字段展开为1822字符，超过1200字符合同 | v2按同记录/成员/业务字段/原值共享展示为984字符，27个来源号和完整路径/原值均保留；不增加上限、不删事实 |
| B01 C3第1答 | 还存在成员引用错配 | 新装配仍拒收`source_member_mismatch`，排版变化不掩盖原错误 |
| B01 C3第2答 | 剩余阻断为程序观察字段装配超限 | 显式v2离线预览通过原严格分析接收；v1边界仍保留原拒收，未回写旧Run或追认模型正文质量 |
| B01 C6两份原答 | impact声明三成员，缺登录A2依据 | 原拒收保持；局部反馈给原主张、字段原值、声明/缺失成员及相关候选，首次纠错消息15036→1202字符 |
| H02 C6两份原答 | impact声明三成员但引用为空 | 原拒收保持；同样聚焦该段缺口，首次纠错消息14722→1936字符 |

C3只使用既有配置的`$.ocsf_json.`与`$.raw_json.raw_event.ocsf_event.`等event_roots恢复业务字段含义，不根据样例IP、主机或告警标题写规则。同字段的数值/字符串、0/false、不同记录、不同成员及不同值不能混并；未知字段保留完整路径。新`case-program-output.v2`随新冻结边界保存，旧v1渲染和校验仍可复现。超长原值仍拒收，不用删字段或改成inferred绕过保护。

C6候选按缺失成员和接收允许的来源角色筛出，标明角色；它们只是回看原材料的索引，不证明正文主张。程序不补引用、不改变模型范围或结论。只有局部最终覆盖类错误才省略完整目录，混合其他错误仍保留诊断。既有最多一次纠错、严格接收和采用规则不变。两份已经用完纠正机会的末答只作离线诊断，不允许因此新增第二次纠正；预览未发送给模型。

## 可直接查看的材料

- C3：[原1822字符](offline/B01-call-02-C3-observation-before.txt) → [新版984字符](offline/B01-call-02-C3-observation-after.txt)，[完整原字段映射](offline/B01-call-02-C3-literal-map.json)、[装配预览](offline/B01-call-02-C3-assembled-preview.json)。这是程序从保存原件生成，不是手工压缩或模型改写。
- C6：[B01局部反馈](offline/B01-call-04-C6-feedback.json)、[H02局部反馈](offline/H02-call-03-C6-feedback.json)；[B01完整纠错消息预览](offline/B01-call-04-C6-correction-messages-preview.json)保留原输入与原答，只替换新增反馈。
- [六份原答离线对照回执](offline/summary.json)列原/新拒收、115份旧文件摘要及版本边界。原始请求/原答仍位于[06批](../fixed-investigation-20261113-06/comparison.md)。

## 保存读取验证

复用现有`test_case_boundary_role_correction_full_flow`，只新增本批独立合成Case。真实PostgreSQL为本机隔离`v12_upgrade_dev`；A/I、C3、Deep、C6、Token计量与外部查询均为替身。沿原角色纠错正常流程执行，新C3/C6实际请求冻结v2；C6程序装配的观察正文与来源逐项保存到Result，原HTTP处理器GET及当前判断与库一致。

Result为 **accepted / uncertain / partial**。这只证明本次程序装配和存取，不是06批原答被采用，也不证明真实模型结论通过。Case内6次替身请求（C3×2、Deep×2、C6×2），旧角色错误及各次原答完整保存；没有对真实模型重采样，没有TCP或生产环境验收。

[本次保存/GET摘要](inputs/summary.json)、[保存观察及原引用](inputs/stored-observations.json)、[Result与当前判断读回](inputs/readback.json)、[数据库快照](pg-01/database.json)。实际替身输入：[C3](inputs/01-C3-input.txt)、[C6](inputs/05-C6-input.txt)；完整请求/Schema、回答与来源映射在同目录和数据库工件中。

直接检查共5项（C3/C6两个阶段各一项、同字段合并一项、真实超长拒绝一项、最终反馈一项）。初次4通过1失败，发现新增局部反馈判别未兼容既有无code诊断；修正后仅定向复验该项通过。离线脚本最初读取错误profile属性，在生成预览前失败；按现有case_io接线修正。一次隔离库流程通过，没有新增完整流程重跑。静态检查另修正离线脚本循环闭包写法，未改业务数据。详细记录见[validation.json](validation.json)。

本机4177静态包追加本次快照，78→79，未发布在线服务。HTTP字段、数据库表和原材料保持；知识嵌入503及持续正文问题仍登记后置，新C6反馈真实效果未验。主调查31/41不变，流式未实施。

## 重放

在仓库根目录运行`.local/conda-envs/socai2/bin/python docs/operations/evidence/case-observation-input-20261113-01/replay.py`可离线复验6份原答与两个观察版本；`extract.py`只从本批快照核并导出输入、观察和读回。已有文件若不一致会拒绝覆盖，均无模型/网络/数据库调用。

`run_persistence.py`是真实隔离库替身验证入口，需要显式私密profile和全新输出目录，不可用来重派已结束Run；当时配置、源码摘要、一次执行及快照见config.json与pg-01。[源码重放基点及补丁](source-replay.json)、原答和最终源码摘要在本批保留。[独立审计](audit.md)已限定通过本轮程序修复、离线证据与一次替身存取；真实模型质量及新反馈效果仍未通过/未验。
