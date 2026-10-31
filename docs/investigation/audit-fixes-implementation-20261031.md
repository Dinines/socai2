**2026-10-31 r10当前交付：** 源码`51086a4`已部署r10；首份正式报告使用JSON Schema，模型A引用映射公共UUID，具体校验反馈和原一次纠错/预算保持。唯一完整raw演示告警主Run `4f094ed4-b4f9-5db9-8cc2-b5f8c781858e` 为completed/partial：3模型、2真实湖查询、0复用、10292 tokens；首次报告格式/成员通过、纠错0。两次成功空查询经ClickHouse QueryFinish核实，报告却把空结果当矛盾并猜测采样/丢日志等原因，语义仍未过。 42个受影响方法的最新结果通过；完整输入、查询日志和具体语义问题见[r10回执](../operations/investigation-structured-report-20261031.json)。下方均为历史阶段。

**2026-10-31 r9：** 用户明确确认后已部署`bf2bd9c`，模型等待采用原120秒剩余时间，6项直接验证复用。唯一真实追加3回复均取得，最长26.50秒；首答JSON无效，纠错后重复成员引用被拒，failed/partial。11740 tokens、1复用/0新湖查询、父报告保持，完整报告语义仍待。见[r9实际回执](../operations/investigation-model-wait-20261031.json)。

**当前交付（r8）：** 源码`a41ae07`上线，明确不确定协议表述可通过；无据肯定/否定仍拒。纠错提示要求完整中文和未证实/非攻击区分，10项必要直接测试通过。唯一真实Run failed/partial，首次结论UUID错误触发一次纠错，随后45.25秒HTTP错误，同期网关Timeout与45秒配置相符；未取得最终模型回复，第三次用量未知。见[最新回执](../operations/investigation-protocol-uncertainty-20261031.json)。当前16/17，不归档，下文为先前阶段。

**当前交付（r7）：** 源码`f19cc70`已上线，模型source_alignment及程序生成的query_sources把复用、历史Run和精确行—告警对应显式化，旧来源/报告保持。30项直接用例首轮29过1额度失败，精简重复指令后3项定向复核通过，其余27项复用。唯一真实网络追加failed/partial，未取得合格结论；原回答与两次校验失败保留。见[最新回执](../operations/investigation-source-alignment-20261031.json)，当前16/17，不归档。下文r6及以前均为阶段记录。

**当前交付（r6）：** 源码`7330a7c`已上线；窄协议名校验、可读成员完整性和HTTPX紧凑JSON额度核算完成，29项受影响直接验证通过。一次网络追加真实完成partial，两个成员均有判断，无HTTPS/TLS/SSL结论；一次历史复用、父报告字节保持，见[最新回执](../operations/investigation-network-report-fix-20261031.json)。新报告仍误述复用、历史与行归属；当前16/17、不归档。以下各阶段数字只适用于当时版本。

**r5阶段交付：** r5已部署，源码`3324fea`；[后续功能回执](../operations/investigation-functional-followup-20261031.json)记录r4四Run及r5两追加均完成partial。原预算内真实纠错、指定Tool和复用、父报告字节保持已验；新来源提示词6项直接测试通过。网络报告仍有HTTPS推断和遗漏成员判断，保留为报告质量未过，不能把完成状态当作语义正确。下方为原阶段记录。

**r3阶段结果：** r3已部署；[共享回执](../operations/investigation-audit-live-r3-20261031.json)记录3主Run为1完成/partial、2纠错预算失败，2追加未发送。针对本轮失败仅本地增加超预算纠错材料精简，完整原件和strict schema不变；6项受影响直接验证通过，Office14007/15074、网络12237/12296。保留原真实失败，当前新修复未部署，不能将模拟纠错回包记为真实业务通过。旧31项为r3的原证据，新用例1个含2个冻结场景。

# 调查审计问题：本地实施与交付记录

日期：2026-10-31。用户在完成OpenSpec规划后要求“推进执行”。本轮基于 `5b9513860c566ea9c7f17917ddb71cc199a1988e` 的工作区实现，处理A01/A02/D01及追加组合回归。**31个不同的受影响直接用例最终通过；实际服务仍只确认已有r1回执，未部署或调用真实PG/ClickHouse/模型/厂商。** 未参与实现者已完成[结束独审](../../openspec/changes/fix-investigation-audit-gaps/audit.md)，必须修项0；源码已提交为 `bb8dbc3`。独审复用既有31项结果，未重跑业务测试。

任务状态见[OpenSpec](../../openspec/changes/fix-investigation-audit-gaps/tasks.md)，原始发现见[审计报告](design-implementation-audit-20261031.md)，精确源码/测试/交付hash见[实施回执](../operations/investigation-audit-fixes-20261031.json)。静态审计清单仍保留修复前基线，不重写旧失败或原207响应。

## 1. 实际修复

| 问题 | 当前行为 | 必要证据与边界 |
| --- | --- | --- |
| A01 进程查询混入其他事件 | SQL固定1007类及非空进程名；保存class_uid/activity_id/action/outcome；进程证据增加case.process_activity.v2，旧查询合同不复用 | T1执行实际SELECT，SQLite只替换参数与时间函数，混合1007/4001/1001只选进程类；不是实际CH验证 |
| A02 失败概况模式/权限 | 同一summary行锁内先核请求和旧正文的Case权限；基础/Case视图各保自己的时间；失败按保留正文来源模式返回stale，已准入尝试/usage沿原事务提交 | T2双向失败、GET一致、已知usage；T3前置403零模型/尝试/成本和基础成功对照；仅ASGI/DB/model替身 |
| D01 取材缺口 | Case.description和选定Alert.description/raw_event进入有界冻结、结果、A证据及模型视图；完整字段canonical hash进入新材料版本，尾部变化也使复用失效 | T4 Office原件、UTF-8/字段/总量限制、输入合同；T5旧Run/H1/同key兼容及来源变化 |
| 组合预算回归 | 保留新原始来源；H1模型只保留summary/findings/counterevidence/gaps，结构化明细和A旧摘要逐项注明省略，完整历史工件不变 | T6冻结Office沿原usage6982进入纠错，当前请求16929≤17018，余89；另验追加＋required_tools＋当前查询复用＋一次纠错及读回 |

### 1.1 模型与原件的边界

进程证据读回包含原class_uid/activity_id；现有LLM合同禁止直接传原始OCSF编号，因此模型行使用event_kind=process_activity和原action/outcome，并带model_omitted_fields及raw_ocsf_codes_retained_in_evidence。未知活动不猜启动，空outcome不表示成功。没有修改或关闭已有LLM guard。

新来源版本为case.source-material.v1。Case描述最多4KiB，每Alert描述4KiB/raw_event16KiB，全Run新增正文合计128KiB；先Case，再按已有成员顺序取描述和raw。完整字段先计算canonical指纹和长度，然后按UTF-8边界截断；超限全文未被Run保留。raw JSON截断后只作文本，hash不是厂商网络包hash。

模型新增正文最多8KiB：Case最多1KiB，其余按可读成员均分，每成员描述最多1KiB/raw最多2KiB。完整来源在嵌套/裁剪前单独经已有输入合同检查，被拒字段留冻结原文，模型以llm_input_contract说明省略。普通模型裁剪以model_limit说明，源冻结省略以field_limit/run_limit说明；不得把未送模型说成来源没有。

新result保存source_material_schema和case_material；A.data.source_material可通过原evidence读取。每字段冻结形状见[设计](../../openspec/changes/fix-investigation-audit-gaps/design.md)。模型只带status/text及model_retained_bytes/model_truncated/model_omission_reason，完整hash/原字节/来源路径留在冻结视图。

H1完整报告保持原样；模型视图逐项省略timeline、member_coverage、member_assessments、relationships、open_questions、recommendations。它们不是被删除的历史事实，也不都属于完全重复内容；选择保留历史摘要/发现/反证/完整缺口，为当前原始来源和纠错预留额度。A旧saved_analysis省略不依赖缓存可用性。all/read/selected三份成员列表完全相同时，模型仅保留selected_member_ids，并以member_sets_equal=true说明三者相同；完整scope不变。旧Run可作H1，但无新材料schema不能复用查询；同key重读仍返回原工件和报告。

### 1.2 权限顺序

POST overview/refresh保留alerts:write/read。include_investigations=true需要cases:read；即使请求基础模式，只要锁内存在非空Case来源旧文，也在模型前要求cases:read。已有基础旧文或无旧文的基础刷新不新增此要求。此收紧只保证可能的失败回退已获授权，不修改角色或JWT系统。成功返回新模式，失败返回旧文模式；生成失败且无旧文仍未生成。

## 2. 直接验证与失败记录

| 输出 | 实际运行与最终状态 |
| --- | --- |
| [b1-direct.txt](../operations/evidence/investigation-audit-fixes-20261031/b1-direct.txt) | 3项进程类型/旧合同/当前复用通过；之后材料改动后并入最终受影响集合 |
| [b2-direct.txt](../operations/evidence/investigation-audit-fixes-20261031/b2-direct.txt) | 5项中4项通过；模式用例的两个subtest仅因Z和+00:00文本比较失败，原日志保留 |
| [b2-mode-recheck.txt](../operations/evidence/investigation-audit-fixes-20261031/b2-mode-recheck.txt) | 改为datetime等值断言后原模式用例两方向通过；其余4项未重复运行 |
| [b3-direct.txt](../operations/evidence/investigation-audit-fixes-20261031/b3-direct.txt) | 3项来源/guard/版本兼容通过 |
| [b4-combined.txt](../operations/evidence/investigation-audit-fixes-20261031/b4-combined.txt) | 2项Office及required/reuse/correction组合通过 |
| [case-final.txt](../operations/evidence/investigation-audit-fixes-20261031/case-final.txt) | 材料初次组合Case API17＋synthesis4＋product2＋navigation3，共26项通过，包含上述Case新用例 |

H1自查发现省略明细后必须保留完整历史gaps；修正并压缩完全相同的成员列表后，[6项受影响追加复核](../operations/evidence/investigation-audit-fixes-20261031/followup-gaps-recheck.txt)通过。当前Office为16929/17018、余89；之前日志中的16486/532是修正前的阶段结果，不覆写。

去重最终结果为26＋5＝31，不将阶段重跑累计成更多通过用例。B2用例包括首次worker只尝试一次、失败保旧/首次失败、Case概况关联，以及新增双向模式和前置权限。新用例共9个（Case7、概况2）。测试通过仅说明相应替身合同，既有真实模型语义缺口仍未关闭。

最初B1混合类别例实际被已有模型输入guard拦截，后续断言表现为缺rows；当时另两项通过。本轮修为语义模型视图后原3项通过，未将其归为单纯测试断言错误。首轮完整控制台未另存文件，本处保留原因，成功日志在上表。B4初次静态组合测得19650/18496均超过17018，未冒称通过；修改历史模型视图后，当前执行器实际到达第二次模型HTTP替身并保存结论。

## 3. 可审阅更新候选（尚未安装）

目标tag：`socai2-investigation-api:20261031-r3`。Compose与安装脚本均使用此独立标识；本地仅执行安装脚本无--execute分支，executed=false。镜像未构建，因此没有新image digest，也不把tag当作已部署版本证明。业务源码已保存为 `bb8dbc321dca574ce19b37ec524051f5ed16b421`。[提交绑定回执](../operations/evidence/investigation-audit-fixes-20261031/source-commit-attestation.json)核476个候选文件与commit内容一致：36个逐字节一致，440个仅Git CRLF/LF差异。冻结tar/manifest保持提交前快照元数据，不改写原哈希；绑定回执补充实际提交归属。

[候选源码包](../operations/evidence/investigation-audit-fixes-20261031/investigation-api-20261031-r3.tar.gz)为1,653,951字节，SHA256 `21bebe063a482201577b61cc146804dd2cc2d2e76a0ea67039720cae534c677a`。包内476份源码/部署文件加SOURCE-MANIFEST.json共477项，已逐项从归档读出重算hash核对；[独立manifest](../operations/evidence/investigation-audit-fixes-20261031/source-manifest.json)记录全部路径及来源。相对r1原475份文件，7份不同、新增1份材料helper；不包含凭据、虚拟环境、缓存或未授权的其他工作区资料。

服务差异仅调查API镜像源码/标签。沿现有loopback18010、原受限容器、现有private环境文件、CA挂载和network；迁移0，权限变更0，core/agents不重建，不启worker。候选安装沿原--upgrade-from精确image ID防误覆盖；真正更新前必须重新只读核当前镜像，不能用旧回执冒充当前状态。回退切回经核实的原镜像/Compose tag，保留全部新旧Run与工件，不删除或重置key。

[定向执行材料](../../openspec/changes/fix-investigation-audit-gaps/retest/README.md)已固定5份实际请求body及派发顺序，当前请求模型静态校验通过、0派发。最近一次[只读交付预检](../operations/evidence/investigation-audit-fixes-20261031/delivery-preflight.json)在SSH连接21:22时超时，未执行远端inspect，不能确认当前在线镜像；不是自动审批拒绝。

获准后的唯一真实批次使用新operation_key，复用原测试材料，不重新摄取：

1. Office：新主Run及一次追加，核描述/PID/raw/审批字段到模型，追加纠错与报告；最多2个Run。
2. 网络：当前版本新主Run形成适用E，再以required_tools追加核复用；最多2个Run，旧r1不能要求缓存命中。
3. LSASS：新Run核成功空结果、成员UUID、来源/旧摘要截断三类语义；最多1个Run。

共最多5个新Run，沿每Run4模型/4Tool/24000 tokens/3000输出/120秒上限；不因内容不理想无限重试。真实成功/失败、用量、输入输出和语义判定留同一回执，两个OpenSpec change引用；A01/A02关闭证据以本轮直接用例为准，不另造生产数据/故障场景。该计划不是实际调用授权。

## 4. r3交付前阶段待办（历史）

- 本地提交及独立结束复审已完成；候选包尚未构建为新镜像，不能称已安装。
- 用户已确认仅更新调查API至r3并使用既有有效身份执行固定5个Run；[新前提检查](../operations/evidence/investigation-audit-fixes-20261031/authorized-preflight-20261031.json)仍在SSH连接阶段超时。实际21连通、在线版本/现有有效身份仍需核实，不重复请求同一授权。
- r3真实部署、Office/网络/LSASS复验和语义判定未做；旧fix-case-followup-gaps的真实任务仍未关闭。
- 本change不归档、不同步主规格，不核销旧2.2/2.3；F5、自动Case、权限专项、恢复/压力及远端推送/合并不在本次执行范围。
