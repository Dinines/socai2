# 调查流程与交接问题清单

更新于 2026-11-11。当前发布和字段合同见[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)。下列未完项独立于部署、读取和字段对应验收；登记不代表修复或取消需求。本轮[独立流程审查](investigation-flow-review-20261111.md)仅检查实现与证据，未修改业务。

按负责人 2026-11-11 的[后置决定](../../openspec/changes/archive/2026-11-11-ground-case-conclusions/scope-decision.md)，持续模型问题记录开放，允许已验证程序功能交付和后续 Case/H 正常操作推进；不再以重复模型采样作为前置。模型质量 NOT_PASSED 保持，不等于问题已修复。

## 待完成事项

| 编号 | 问题及影响 | 当前处理与验收落点 |
| --- | --- | --- |
| M01 | 模型扩大正文事实，结构合法不保证主张有据 | 质量 NOT_PASSED。程序覆盖和观察原值装配已直接验证；第五批命令结果边界改善；Deep 仍凭 synthetic 标签断言非生产环境，C6 替代解释将四项未查询也说成查空，两项已保存读回。另有时间间隔计算错误；固定 coverage 正确不代表其他正文正确；见[当前验收](../../openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md) |
| M01-A | 模型将 synthetic 等来源标签推成业务环境/良恶性事实 | **已知、后置，未修复**。第五批 Deep 原答及保存 GET 可复现；只应据对应业务材料或明确归属的人工陈述判断环境。按负责人决定不阻塞发布/后续功能，原质量结论保持 |
| M01-B | 模型自由正文将未查询写成查空 | **已知、后置，未修复**。第五批 C6 F1 替代解释与程序 coverage 的 2 查空/4 未查矛盾；原字段/原答保留，真实状态以程序回执为据。后续实际触及该输出时定向处理，不重复采样 |
| M02 | 角色引用合规与正文有据需分开持续验收 | r6 参照批次 Finding 生成／反馈缺口已按 F06 修正，该批独立真实 Run 的 6 条 observed 支持合规，0 纠正；不能由该 Run 推断所有模型场景稳定，也不能用角色合规核销 M01。当前程序原值装配及原批次拒收分别保留 |
| F01 | H 后再次调查的传递已验证，正确利用反馈及有据结论仍未通过 | 用户授权助手代拟材料核查，3 个修订和后轮 C3/Deep/C6 输入均可追溯；仅管理字段变化不造成虚假过期。模型仍重复部分已指出的错误，可见性不核销 3.7，也不代表业务授权确认 |
| F02 | 真实非空知识使用和背景取证覆盖仍待验证 | 配置排序、有效 A 配对回执覆盖及工具预留已实现；本轮真实 assets／knowledge 完成零行，其余按实际跳过／未接入保存。每 Run 4 工具、预留 2 不增额。下一适用批次核非空知识及按问题使用；graph 单列 |
| O01 | 自动消费者暂停；恢复后的实际消费、自动分诊和建案未验收 | 本批不启动消费者；按已有服务范围单独核验，健康探针不证明处理成功 |
| W01 | Case/H 的实际写入与前端操作尚需接通验证 | 当前 `SOCAI2_CASE_API_ENABLED=false`；按需作业真实建案／准备／启动及 H 服务层创建／完成／修订已验证。服务层验收适配器不等于 HTTP 写操作开放；必要接线与配置随功能处理，读写权限不作为独立前置 |
| P01 | 事件概览缺本次诊断入口 | 对应 J04；由成员主体及 Run UUID 打开实际诊断尝试，失败也可查 |
| P02 | 原页面 `severity_effective=medium` 显示错误 | 对应 F06；应显示“中”，保留来源为人工覆盖或成员最高值 |
| P03 | 原运行页把 `delivery_state=none` 与字段缺失混为一类 | 对应 F15；已记录 none 显示未交付，缺失按未知处理 |
| P04 | 无效告警 ID 缺明确未找到及返回入口 | 对应 J01；404 应终止下钻并允许返回 |
| P05 | Case 评论附件、探索保存、案件故事组合、完整管理／真实响应缺页面或服务接线 | F20/F24/F25/F27；已有表或模型建议不能宣称业务已开放。响应只以真实审批／动作／回执为据 |
| Q01 | 问答、保存回答、采用回答为预留业务 | 服务预留返回 501；生产关闭 Case 开关时先返回 503。前端标明未开放，不能把演示回答写成服务结果 |

四项 P01–P04 是已保存的产品页面核对结论；4177 内部工作台的节点详情优化不核销这些产品页面事项。[功能与跳转清单](../../deliverables/investigation-validation-20261106/frontend-feature-list.md) · [原始页面证据](investigation-test-handoff-20261106.md#下一阶段的前后端交接验收)

审计基线、各批原答、校验、采用和读回关系分别保留。第五批执行 completed/交付 partial、C6 uncertain/accepted 并采用，不等于正文已经核实：原正文独审为 REVISE；负责人后置决定后的程序交付补充审查为 ACCEPT。第四批 rejected 原件保持，不改写采用/失败历史。

## 保留模块启用前的问题

以下属于 `services/agents` 的 Hunt，不是当前 `socai2` A/I/C/H 的执行链；生产暴露和真实多租户数据未在本轮验证。按该模块启用范围处理，不单开主线权限专项。

| 编号 | 问题及影响 | 修复与验收 |
| --- | --- | --- |
| A03 | Hunt 路由只执行认证，不消费 principal 的租户，读取与手动调度落到 default | 隔离真实 ASGI 复现两租户均用 default；从认证结果显式绑定目标并传入读写/执行，不能缺失回退；验收两个租户的下游目标匹配 |
| A04 | Hunt 数据湖失败变空列表，返回 ok=true，生成 completed/零行/error=null 的落库参数 | 隔离真实 loader→scheduler→engine→store 复现；保留采集失败/错误到接口和 Run，用正常零行与超时各一例直接验收 |

详细行号、触发、证据及限制见[独立流程审查](investigation-flow-review-20261111.md)。Swarm/Debate 的确定性评分与模拟 token 未证实接入目标路径，按保留模块说明，不认定主线模拟冒充真实。

## 已修正并复验

| 编号 | 发现与修正 | 证据 |
| --- | --- | --- |
| A02 | C3 提示最多两项补查，但生成/接收曾允许 12 项 | 当前冻结配置、生成/接收/partial 均限 2，三项明确拒收且零派发，历史读取和 C6 建议兼容；直接检查通过，21 r1 实际加载上限 2，发布读回通过。[本次交付](../operations/evidence/case-grounding-20261111-01/delivery-summary.json)。原审计反例保持 |
| R01 | Case/H GET 共用关闭的写开关而 503；GET 现在接受页面读取开关，写操作仍受原开关约束 | 当前两案 365 GET、16,820 检查；读取开关／租户／权限与写入拒绝定向测试 |
| R02 | 安装核验器拒绝已经人工授权的 `aisoc_app` schema USAGE | 改为核实获准 SELECT、无调查写权限及无管理权限；实际 verify 通过，未执行 GRANT 或 DDL |
| R03 | 对账脚本只在本 Case 计算相关告警，遗漏同租户跨 Case 的合法结果 | 从同一只读快照读取匹配对象及当前材料，按类型／命名空间／对象键核对关联，复验零偏差 |
| R04 | 交接文档仍显示未部署／缺权限，OpenAPI 缺来源工件、活动及事件交付字段 | 当前入口、字段与接口导出统一更新；整理前文档归档，原失败／unknown／模型原答保持 |
| R05 | Deep/C6 生成 Schema 允许接收校验禁止的执行回执结论引用 | Deep 支持／反证及 C6 结论／比较／影响／建议的枚举排除执行回执；C6 analysis 保留查询覆盖引用。20 项边界检查、5 份原答离线复验通过；真实生成效果列 M02 |
| R06 | 核验器假定当前判断非空、Case／活动仅属于单案 | 支持空判断并拒绝伪造判断；按同租户完整主体关系核 Case、活动及 `via_member_alert`，补 H 详情和全部修订逐值核对。16,820 检查及独立活动 1,083 检查通过 |
| R07 | 4177 点击节点只能跳到下方原件，Deep 无动作时缺实际失败模型入口；展示源码变化不能刷新已有缓存 | 左侧流程／右侧详情已接通提示词、输入输出、错误和原件；Deep 每次实际调用可选，冻结输入分类经独审修正。30 项定向测试、307 条记录逐值保持及浏览器宽窄屏核验通过。见[节点详情验收](../../openspec/changes/complete-socai2-investigation-chain/workbench-node-inspector-20261110.md) |
| F03 | 分别保留查询出处与历史行主体，修正 C02 A3 查询中 A1 记录的引用范围 | C3／Deep／C6、冻结依赖恢复及案件外／冲突身份直接检查通过，原路径／角色／正文保持；[本轮验收](../../openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/validation.md) |
| F04 | 来源可见性、成员覆盖、C6 本次 finding 及 conclusion／impact 覆盖可定位错误获得一次具体反馈 | PG 已验证纠正成功与仍错时部分保留，前批真实 C6 已发生一次纠正；unknown／截断不重派。本轮补角色诊断见 F06，剩余正文问题见 M01 |
| F05 | Deep handoff 生成允许空答复、网关分支丢公共必填项，与接收合同不一致 | 每个 action／Answer 分支展开完整结构与限制；真实第三轮 handoff／answer 均完整通过，前两轮原失败保留；[69 项直接检查](../operations/evidence/case-scope-recovery-20261110-01/final-contract-tests.xml) |
| F06 | C3/C6 Finding 生成与接收的角色约束不一致，有限反馈遗漏角色错误 | 已统一部署并核来源：完整状态分支限制直接观察、v2 反馈给角色与逐成员缺口；86 项检查、两项 PG 流程和一轮真实生成通过该范围，原接收兼容性及历史原件保持。[角色验收](../../openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)；独审 ACCEPT，21 r6 生产读回通过 |

本次结果见[程序功能验收](../../openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)及[交付回执](../operations/evidence/case-grounding-20261111-01/delivery-summary.json)。r6 参照批次见[角色验收](../../openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)与[逐调用汇总](../operations/evidence/case-evidence-roles-20261110-01/execution-summary.json)。前批来源范围及纠正修复见[验收报告](../../openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/validation.md)；原[Case 流程实测](../../openspec/changes/complete-socai2-investigation-chain/case-current-flow-20261110.md)和生产原答继续保留。
