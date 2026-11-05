# m3：告警输出格式兼容诊断已结束

**实际结果：** 用户明确允许本批后已执行2次、0重试，两次均HTTP400、0原答、usage均未知。当前anyOf引用分支报缺少type；type数组中的object也被拒。配置/容器指纹保持，原7份远端JSON见[机器回执](../operations/socai2-schema-probe-m3-20261104.json)。本批授权已解除原阻止，不能再运行run或继续等待m3授权。随后已按错误做[本地最小修复及n11候选](socai2-deepseek-union-fix-20261104.md)，修复后真实确认另属m4，不使用m3已耗尽额度。下文保留本批固定范围及准备时记录。

2026-11-04。本批用于定位m2的DeepSeek告警HTTP400，仅验证输出格式兼容性，不评价调查质量、良恶判定或待复核比例。m2结束批次保持，不重复派发旧请求。

## 固定范围

两条通用请求均使用已授权的`deepseek-flash`、`/responses`、非思考模式、temperature=0、最多512输出tokens、120秒上限，每条只发一次。请求仅含代码生成的字段Schema、局部别名`N1_S1`和通用JSON示例；没有告警/事件/Case原文、业务ID、冻结判断或Tool材料。错误留痕代码随包上传以在既有n9容器的临时Python进程内执行；不替换应用代码、不重启服务、不修改配置或凭据。

| 请求 | Schema差异 | 用途 |
| --- | --- | --- |
| canonical | 当前A合同：decision_basis使用anyOf，分支为DecisionBasis引用或null | 获取具体HTTP错误字段，核对当前格式是否被接受 |
| nullable-object-type | 仅把同一DecisionBasis对象约束内联，type设为object或null；其他请求字段全部相同 | 对照等价的可空对象表示，不移除必填字段、枚举、来源范围、长度或额外属性限制 |

官方[Responses API参数](https://api-docs.deepseek.com/api/create-response/)和[兼容说明](https://api-docs.deepseek.com/guides/responses_api/)声明支持json_schema，但没有提供足够细节确定本次400的具体关键字。nullable对象仍是假设，不称根因已确认。即使其中一种成功，也需结合另一条的错误信息判定，不把Schema实验当实际A/I/C验收。

固定包位于`docs/operations/evidence/socai2-schema-probe-20261104/m3`，远端目标为`192.168.1.21:/opt/sting-aisoc-socai2/evidence/next-schema-probe-20261104-m3`。沿用已存在容器/凭据入口，仅保存本批请求、原答、安全有界错误与配置指纹；不新增业务Run、查询或采用。原m1/m2脚本与原件不变；prepare不可重跑。

## 本地检查与准备阶段阻止记录（已解除）

`test_socai2_schema_probe.py`三项通过：除decision_basis表示外请求逐值一致；合法及非法边界的Schema结果一致；实际固定child脚本在模型替身抛出HTTP400时只调用一次、去除测试凭据、保留code/param等信息。固定runner及child编译、Ruff通过。没有新的业务代码修改，也没有真实模型调用。

首次上传命令被自动审批拒绝，原因是私有代码、Schema及错误处理逻辑属于新增m3载荷，m1/m2明确授权不覆盖本次目的和批次。当时命令未执行、0上传/预检/调用。其后用户明确答复“允许本批m3按此范围验证”，已保存user-authorization并执行完毕；原拒绝另存，不覆盖历史记录。

已按`probe_socai2_schema_m3_20261104.py upload`、`preflight`、`run`、`export`执行，run仅一次，7份JSON导出。两条intent的请求hash与固定包一致，整包CRLF→LF已按归一化hash核对；本批结束，不能重派。

线上最近核验仍n9、n10冻结未部署、r7未启。OpenSpec13/16，完整真实C/H/第二C、最终审计和归档继续待办。
