# 调查流程与交接问题清单

更新于 2026-11-10。当前发布和字段合同见[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)。下列未完项独立于本批的部署、读取和字段对应验收；登记不代表修复或取消需求。

## 待完成事项

| 编号 | 问题及影响 | 当前处理与验收落点 |
| --- | --- | --- |
| M01 | 模型扩大正文事实，结构合法不保证主张有据 | 质量 NOT_PASSED。本轮仍有进程启动被写作命令效果、未查与查空笼统并列、未提供环境属性被推断等问题；保留原答和局部结果，不报准确率。按 A/I/C 目标单列事实依据验收，见[本轮报告](../../openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/validation.md) |
| M02 | 模型的成员／发现关联可有限纠正，标签或描述冒充 observed 仍造成拒收 | 本地 3 轮、14 调用；第二轮 C6 重复引用纠正后采用，第三轮悬空 finding 经一次反馈处理后仍因 non_observation_promoted_to_observed 拒收。Deep 完整分支已复验通过。F03 程序主体映射已修；模型角色选择及正文质量不随程序修复核销 |
| F01 | H 后再次调查的传递已验证，正确利用反馈及有据结论仍未通过 | 用户授权助手代拟材料核查，3 个修订和后轮 C3/Deep/C6 输入均可追溯；仅管理字段变化不造成虚假过期。模型仍重复部分已指出的错误，可见性不核销 3.7，也不代表业务授权确认 |
| F02 | 真实非空知识使用和背景取证覆盖仍待验证 | 配置排序、有效 A 配对回执覆盖降序及工具预留已实现；本地三轮真实查询 assets／knowledge 均完成零行，未把查空当使用成功。每 Run 4 工具、预留 2 不增额。下一适用批次验证非空知识及按问题使用；graph 接入仍单列 |
| O01 | 自动消费者暂停；恢复后的实际消费、自动分诊和建案未验收 | 本批不启动消费者；按已有服务范围单独核验，健康探针不证明处理成功 |
| W01 | Case/H 的实际写入与前端操作尚需接通验证 | 当前 `SOCAI2_CASE_API_ENABLED=false`；按需作业真实建案／准备／启动及 H 服务层创建／完成／修订已验证。服务层验收适配器不等于 HTTP 写操作开放；必要接线与配置随功能处理，读写权限不作为独立前置 |
| P01 | 事件概览缺本次诊断入口 | 对应 J04；由成员主体及 Run UUID 打开实际诊断尝试，失败也可查 |
| P02 | 原页面 `severity_effective=medium` 显示错误 | 对应 F06；应显示“中”，保留来源为人工覆盖或成员最高值 |
| P03 | 原运行页把 `delivery_state=none` 与字段缺失混为一类 | 对应 F15；已记录 none 显示未交付，缺失按未知处理 |
| P04 | 无效告警 ID 缺明确未找到及返回入口 | 对应 J01；404 应终止下钻并允许返回 |
| P05 | Case 评论附件、探索保存、案件故事组合、完整管理／真实响应缺页面或服务接线 | F20/F24/F25/F27；已有表或模型建议不能宣称业务已开放。响应只以真实审批／动作／回执为据 |
| Q01 | 问答、保存回答、采用回答为预留业务 | 服务预留返回 501；生产关闭 Case 开关时先返回 503。前端标明未开放，不能把演示回答写成服务结果 |

四项 P01–P04 是已保存的产品页面核对结论；4177 内部工作台的节点详情优化不核销这些产品页面事项。[功能与跳转清单](../../deliverables/investigation-validation-20261106/frontend-feature-list.md) · [原始页面证据](investigation-test-handoff-20261106.md#下一阶段的前后端交接验收)

## 已修正并复验

| 编号 | 发现与修正 | 证据 |
| --- | --- | --- |
| R01 | Case/H GET 共用关闭的写开关而 503；GET 现在接受页面读取开关，写操作仍受原开关约束 | 当前两案 365 GET、16,820 检查；读取开关／租户／权限与写入拒绝定向测试 |
| R02 | 安装核验器拒绝已经人工授权的 `aisoc_app` schema USAGE | 改为核实获准 SELECT、无调查写权限及无管理权限；实际 verify 通过，未执行 GRANT 或 DDL |
| R03 | 对账脚本只在本 Case 计算相关告警，遗漏同租户跨 Case 的合法结果 | 从同一只读快照读取匹配对象及当前材料，按类型／命名空间／对象键核对关联，复验零偏差 |
| R04 | 交接文档仍显示未部署／缺权限，OpenAPI 缺来源工件、活动及事件交付字段 | 当前入口、字段与接口导出统一更新；整理前文档归档，原失败／unknown／模型原答保持 |
| R05 | Deep/C6 生成 Schema 允许接收校验禁止的执行回执结论引用 | Deep 支持／反证及 C6 结论／比较／影响／建议的枚举排除执行回执；C6 analysis 保留查询覆盖引用。20 项边界检查、5 份原答离线复验通过；真实生成效果列 M02 |
| R06 | 核验器假定当前判断非空、Case／活动仅属于单案 | 支持空判断并拒绝伪造判断；按同租户完整主体关系核 Case、活动及 `via_member_alert`，补 H 详情和全部修订逐值核对。16,820 检查及独立活动 1,083 检查通过 |
| R07 | 4177 点击节点只能跳到下方原件，Deep 无动作时缺实际失败模型入口；展示源码变化不能刷新已有缓存 | 左侧流程／右侧详情已接通提示词、输入输出、错误和原件；Deep 每次实际调用可选，冻结输入分类经独审修正。30 项定向测试、307 条记录逐值保持及浏览器宽窄屏核验通过。见[节点详情验收](../../openspec/changes/complete-socai2-investigation-chain/workbench-node-inspector-20261110.md) |
| F03 | 分别保留查询出处与历史行主体，修正 C02 A3 查询中 A1 记录的引用范围 | C3／Deep／C6、冻结依赖恢复及案件外／冲突身份直接检查通过，原路径／角色／正文保持；[本轮验收](../../openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/validation.md) |
| F04 | 来源可见性、成员覆盖、C6 本次 finding 及 conclusion／impact 覆盖可定位错误获得一次具体反馈 | PG 验证纠正成功与仍错时部分保留；真实 C6 已发生一次纠正，unknown／截断不重派。该反馈不承诺纠正全部模型角色或正文问题，剩余见 M01／M02 |
| F05 | Deep handoff 生成允许空答复、网关分支丢公共必填项，与接收合同不一致 | 每个 action／Answer 分支展开完整结构与限制；真实第三轮 handoff／answer 均完整通过，前两轮原失败保留；[69 项直接检查](../operations/evidence/case-scope-recovery-20261110-01/final-contract-tests.xml) |

本轮结果见[修复验收](../../openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/validation.md)与[逐轮汇总](../operations/evidence/case-scope-recovery-20261110-01/execution-summary.json)。此前结果见[Case 流程实测](../../openspec/changes/complete-socai2-investigation-chain/case-current-flow-20261110.md)与[读回证据](../operations/evidence/case-current-flow-20261110-01/readback-03/summary.json)。前批回执与过程见[发布核验报告](../../openspec/changes/complete-socai2-investigation-chain/release-current-20261110.md)及[证据目录](../operations/evidence/current-release-20261110-01/readback-03/summary.json)。
