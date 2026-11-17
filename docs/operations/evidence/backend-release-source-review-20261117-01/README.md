# 后端发布来源限定审阅

2026-11-17。**建议发布与3c.2真实正常链一致的当前完整后端，明确保留D5a异常验收未完边界。** 发布协调已接受该范围；不临时拼接r4+C1、不回退活动工作树。本轮只读核来源并写审阅回执，0模型、0业务执行、0部署；没有重新核21活动容器，r4依据其已保存的发布来源清单及就绪回执。

[机器回执](review.json) · [复核脚本](review.py) · [当前processing来源摘要](current-processing-manifest.json) · [当前HTTP来源摘要](current-http-manifest.json) · [HTTP完整路径映射](current-http-targets.json)。这些是打包核对输入，不是新发布包或部署成功证据。本审阅参与过D5a实现，不替代change结束时未参与实现者的独立审计。

## 范围结论

3c.2实际运行的[source-freeze-02](../acceptance-append-20261117-02/source-freeze-02.json)列453文件，其中286个API/Fusion文件与当前逐项一致，**后端新增差异为0**。其余未列入该专项冻结的既有运行源，沿完整r4包逐文件比较，确认只有下表4个修改、1个新增。调度、Fusion、预算policy、模型输入profile及公开HTTP代码相对r4无额外运行改动。

| 相对r4的文件 | 改动及实际验证边界 |
| --- | --- |
| `services/api/app/socai2/case_incident_material.py` | C1嵌套SQL改用唯一外层task别名定位事件，避免同租户多事件时标量子查询扩成多行。SHA与3b core-fix-scope及3c.2完全相同；3b已核另一个无关事件存在时冻结范围不串读，3c.2两案各两轮通过 |
| `services/api/app/socai2/baseline_deep.py` | D5a统一接收/保存Deep阶段回执，控制不完整时可独立保留答案；3c.2真实正常Deep→C6→Result已走当前版本 |
| `services/api/app/socai2/baseline_deep_contract.py` | 抽取独立答案校验，保留原引用/说明诊断及控制约束；同当前3c.2冻结 |
| `services/api/app/socai2/baseline_reasoning.py` | Deep允许stop/length进入接收并定位真实正文；C6自身接收未改，同当前3c.2冻结 |
| `services/api/app/socai2/case_deep_delivery.py`（新增） | Deep单元接收和严格回执。旧r4哈希列表不存在此项；新HTTP清单必须重新生成，不能仅补4个变化文件 |

当前processing应为742个包输入文件，HTTP为730个源文件。两包共享的调查核心必须使用相同SHA；`current-http-targets.json`含新增接收器，仍须由发布方重新生成新release标识及完整配置，不能复用旧r4版本名。

D5a原先68直接检查、独立10切点及“无可用答案仍继续C6”的同Run读取仍有效；[3c.2](../acceptance-append-20261117-02/README.md)进一步证明当前组合的正常Deep及完整两段链，13模型请求均stop、109995tokens、限定独审通过。**它没有验证D5a“有效截断答案经PG进入C6”的目标，也没有验证D5b/c的C6自身截断、网络异常和比较接线；这些仍未完成。** 不能因当前组合正常链通过勾掉D5/D6，不能把3c.2正常样本包装为异常测试。

## 可用存档及其他差异

- 完整r4 processing存档：`.local/processing-release/processing-20261116-r4/release.tar.gz`，SHA `cddffb21820db54628911c980fd55571cf7dadc5ac966c4034c07087cb299f05`。741个manifest条目均验证，tar内manifest与外部原件相同，SHA256SUMS匹配。
- 完整r4 HTTP存档：`.local/http-release/streaming-http-20261116-r4/`。732个manifest条目均验证，729个源文件与已发布http-profile预期SHA逐项一致。
- 3c.2的freeze02是摘要清单，不是独立全源码压缩包。当前源与其运行后端条目一致、其余旧源与上述r4存档一致，可据此冻结新完整候选。r4+C1虽能重建，但它是新的组合，不能称为3c.2当时执行的完整来源；本次不采用。
- 当前相对freeze02的6个其他差异均属于测试工具：build.py/package-build.json/test_build.py/acceptance.py/acceptance_append.py与3d runtime-freeze-02一致；test_acceptance_append.py与3c.2最终AP02 guard冻结一致。具体哈希见机器回执，不把测试工具后续修改算成调查后端未验改动。

## 最小发布定向验证建议

1. 打包时核742/730条完整来源与本回执，两个镜像的共享core SHA一致；额外/缺失文件均明确处理。新release、配置及实际policy单独冻结，保持原模型额度、N=1及既定4h/6h/7天规则，环境地址按21配置。
2. 候选镜像只做必要加载/入口检查和80操作OpenAPI合同核对。代码SHA未变时复用3b C1及3c.2正常链证据，不重跑全仓回归或为质量再采样。若打包发现新的运行代码差异，先停止该候选并定向审查新差异。
3. 发布后的实际源码/配置读回由根协调执行，再按已定的新Kafka两段材料验A→I→Case、同Case更新/上一轮链接、HTTP冻结范围读取；不能用旧数据成功记录或HTTP200代替本次业务验收。测试等待可使用已明确的check流程，不声称自然4h/6h已测。

本审阅没有执行上述候选/发布验证或历史清理；根协调在用户已确认范围内负责对应动作与实际回执。
