# 独立调查服务的模型结构约束

本次仅修改新 `socai2` 执行链，不修改旧服务、共享模型网关配置、数据库表或预算。真实验收目前仍未通过；本地结构检查不能证明结论真实。

## 修复依据与边界

r2 的 I 返回字符串代替 `evidence_requirements` 数组，C3 完整返回但漏两个问题、重复成员、编造来源编号；不是输出截断。原请求的 `json_object` 仅约束 JSON 形式，字段合同只在收到答复后校验。现在将同一份 Pydantic 合同生成 `json_schema`，在请求中启用 `strict`，同时保留原有解析器和成员/来源/角色校验。

上游只读接口元数据声明支持 JSON Schema；n6/r3 四份真实回复均符合记录的请求 Schema，但语义仍未通过，不能据此单独证明上游约束的因果效果。参考 [vLLM 官方结构化输出说明](https://docs.vllm.ai/en/latest/features/structured_outputs/)。这项能力约束结构，不验证证据是否支持文字结论。

| 执行点 | 合同 | 请求约束 |
| --- | --- | --- |
| A 告警分诊 | alert_basic_contract.Answer | 判定枚举、数组、必需字段、本次可见来源编号 |
| I 事件诊断 | incident_diagnosis_contract.Answer | 完整成员数量、成员编号、来源编号、问题证据需求数组 |
| C3 初始分析及再分析 | baseline_analysis_contract.Analysis | 六个问题、四领域、成员数量及范围、可见来源、允许对象 |
| C4 Deep | baseline_deep_contract.Decision | 当前问题、实际提供的查询绑定、支持/反证来源；无绑定时只能 null |
| C6 最终交付 | baseline_delivery_contract.Delivery | 完整分析、结论、比较、影响及建议的原合同和范围 |

`structured_output.py` 复用来源/成员/问题定义，移除展示用 title/description/default，避免在模型请求中重复携带无关元数据。C3/C6 提示保留分析语义和证据边界，字段形状交由同次 Schema，不再重复大段示例。

所有新执行请求显式记录 `temperature=0`，再由网关原样透传；不是只在发送函数中偷偷追加参数。不能承诺跨版本或设备完全确定性。请求 JSON Schema 仍计入原有请求大小与 token 预留上限；没有提高模型数、工具数、输出上限、总额度或时限。上游拒绝/不支持/返回不合格时保留原件并失败，不回退弱约束、不增加自动纠错调用。

## 已做验证

最初 9 项本地检查通过：五个合同生成的 Schema 有效且不改合同；不存在的来源、错误数组、非法枚举被约束；成员数量和问题范围被约束；Deep 未提供的绑定不可选择；实际传输参数与记录 body 一致，上游拒绝仅调用一次。专门保留“形状正确但无据良性”的例子，证明 Schema 不能替代语义验收。随后新增剩余额度压缩检查，结构约束共 10 项，与阶段质量 8 项合计 18 项最新通过；不是重写原 9 项回执。

原回执：[structured-output-local/receipt.json](../operations/evidence/socai2-next-service-20261104/structured-output-local/receipt.json)。最初 Ruff 的导入顺序和测试变量重名已修。9 个相关 PG 方法最新通过，执行器两项初失败与定向复核见[投影修复记录](socai2-model-input-projection-20261104.md)；真实结果见 [r3 验收](../operations/socai2-next-r3-validation-20261104.md)，不以本地通过核销。

## 尚不能保证

结构约束不证明成员属性属于正确成员、不证明测试标签等同授权、不证明查询空结果是反证，也不证明任意文字的因果关系。原本地解析器继续检查稳定引用与归属；真实语义仍按冻结原件逐条审核。当前唯一上游服务自报 Qwen3.5-9B，五个 alias 指向同一后端，换 alias 不等于换模型；不能用模型名或服务就绪代替质量验收。
