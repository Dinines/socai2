# DeepSeek可空对象兼容修复与n11候选

2026-11-04。用户授权m3后，两次请求均已执行并以HTTP400结束，未重试，未产生模型答复；用量均未报告，不能记作零tokens或零费用。原服务、独立新容器、共享网关和凭据配置指纹前后保持，0业务Run/Tool/采用/部署。[m3固定回执](../operations/socai2-schema-probe-m3-20261104.json)保留7份远端JSON及原始安全错误字段。

## 已确认的兼容问题

| 请求 | 供应商错误 | 能确认的事实 |
| --- | --- | --- |
| 当前A格式：`anyOf: [$ref DecisionBasis, null]` | `field anyOf: missing field type` | 当前可空对象的引用分支被拒，发生在生成模型答案之前 |
| 等价表示：`type: [object, null]` | object不是该type数组支持的选项；仅列string/number/integer/boolean/null | 可空对象不能用这一种类型数组表示 |

本批只改变输出Schema，不包含告警材料；不能据此评价大小模型推理能力。m2原错误正文未保留，m3现在以同一A合同类型结构取得具体错误证据；已定位发送Schema兼容问题，但修复后实际接收仍需再验证。

## 最小修改

`model_protocol.prepare_request`在DeepSeek协议下、计量和保存请求之前，将anyOf分支中的本地引用展开为带明确type的完整定义，仍保留anyOf和null分支。例如decision_basis的对象分支保留kind枚举、claim长度、source_ids范围及长度、所有required和additionalProperties=false。普通属性/数组元素的引用继续共享，避免整份Schema重复展开。

本地规范合同、解析器与依据检查不变；小模型和普通Chat协议不受此改动影响。缺失、非本地、循环或带兄弟约束的引用明确报错，不静默删除约束，不降为宽松JSON，不增加重试或输出预算。无DDL、页面或模型配置修改。此修复同样处理Deep决定中的可空Answer/BindingId等引用分支，不局限于告警字段名。

## 验证及候选

- 33个既有相关纯检查、11个新检查通过。新增覆盖A/I/C3/Deep/C6全部Schema的分支type、空值/合法/非法对象边界等价、来源和长度限制、循环/丢失引用，以及只改变DeepSeek发送层。新测试首次Ruff有一处导入格式问题，已修；无业务测试失败。
- 2个新的真实隔离PG方法通过：A保存发送的完整转换后请求和原回复；完整C3→Deep→Deep→C6的请求逐值一致、结果被本地解析接受，仍为4模型/4Tool/24000tokens原上限。**模型和湖返回是替身，不能当真实模型验收。** 临时受限角色和隧道均清理。
- n11已本地固定：620文件/549应用文件；与n10相比仅8个应用路径及镜像标签变化，包含前轮I优先级/错误留痕和本轮协议修复。tar逐文件hash、0644权限、应用字节及敏感文件名检查通过；n10原包保持。

候选：`.local/releases/next-20261104-n11`。tar SHA256 `7f0dfd8f6d0943badb6191e12455a86c903bd755f9f2b74f9186c579004dfd0a`，manifest SHA256 `8329b0505cc23f53b2474ffc80eb6585cac1e22a66d35ff29393b674abf4f29a`。[修复回执](../operations/socai2-deepseek-union-fix-20261104.json)列代码和测试指纹、2份PG原回执。

## 下一项：m4单次兼容确认

本批m3授权的2次已用完，不派发第三次。新m4仅准备1条修复后请求：沿用m3通用JSON，实际调用当前prepare_request生成明确type的anyOf分支；其他字段逐值相同，512输出tokens/120秒、一次且不重试。仅Schema/通用JSON/错误留痕代码，无告警/事件/Case材料，不写业务判断，不部署。

本地目录`docs/operations/evidence/socai2-schema-probe-20261104/m4`，目标`192.168.1.21:/opt/sting-aisoc-socai2/evidence/next-schema-probe-20261104-m4`。需要额外一次调用授权后，沿`probe_socai2_schema_m4_20261104.py upload→preflight→run→export`执行；prepare已固定不可重跑。此次授权需求来自用户对m3明确最多2次的限制，不把前次自动审批已解除的拒绝误称为仍有效。

2026-11-05接续：原n11包保持，后续范围/计划关联与C6预算修复已形成n13，[明细与PG验证](socai2-m2-followup-fix-20261104.md)末节。协议代码未变，m4固定包仍等待新增1次授权，不重做prepare。真实兼容确认通过后，再部署届时核验的最新独立候选并按新批验证A/I/C/H/第二C；不再部署已被接续的n11。无据定性不等于有真值的误判，needs_review可接受并单列。线上最近核验仍n9，n13未上传/部署、r7未启，OpenSpec13/16、真实质量/最终审计/归档仍未完成。
