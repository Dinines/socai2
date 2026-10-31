**2026-10-31 r9补充：** 源码`bf2bd9c`完成调查剩余时限传递，6项必要直接用例首次通过；已安装网关选择函数验证请求timeout优先于45秒默认。仅本地/替身通过，r9构建部署被自动审批拒绝并请求确认，0真实Run；线上仍r8，5.3未完成。见[回执](../../../docs/operations/investigation-model-wait-20261031.json)。

**r8当前验证：** 10项必要直接用例首次全通过，含2新增；r7原始回复进入一次替身纠错，明确不确定协议句式可保存，无据肯定/否定仍拒；原预算保持。源码a41ae07已上线且472文件hash核。唯一真实Run因纠错HTTP错误failed/partial，3模型尝试、2回复、7540已知tokens，第三次usage未知；约45.25秒与同期网关Timeout/45秒配置相符。21HTTP/44原件hash核、父报告保持；新内容未取得真实完整验收。见[回执](../../../docs/operations/investigation-protocol-uncertainty-20261031.json)，16/17、不归档。OpenSpec严格校验已通过。

**r7当前验证：** source_alignment/query_sources和来源段已实现并上线；30项受影响直接用例首轮29过1额度失败，压缩重复提示后只复核3项全过，其他27项通过复用。唯一真实Run failed/partial，3模型/1复用/0新湖查询/11341 tokens；两次校验错误为json_invalid及unobserved_application_protocol_use_gaps。23HTTP/48原件hash核，原报告不变，失败原答未被采纳。见[回执](../../../docs/operations/investigation-source-alignment-20261031.json)；16/17，不归档。

**r6当前验证：** 29项受影响直接用例通过，包含r5实际错误内容与r4缓存行的选定重放、一次纠错及不可修正遗漏停止；不是完整r5调用重演。源码7330a7c，21部署及472源码核对完成。真实网络追加1 Run完成partial，3模型、1复用、0新湖查询、12780 tokens，22HTTP/46原件hash核，原报告字节保持。两项修复已验证，完整语义仍有历史复用、H1和行归属错误；见[回执](../../../docs/operations/investigation-network-report-fix-20261031.json)。当前16/17，不归档。r6更新后OpenSpec严格校验exit0；新增/修改Markdown行的链接与候选479文件hash均核对，见[静态记录](../../../docs/operations/evidence/investigation-audit-fixes-20261031/live-r6/static-checks.json)。

**后续实际功能验证：** r4/r5的[同一汇总回执](../../../docs/operations/investigation-functional-followup-20261031.json)覆盖6 Run、16模型、2新湖查询和4复用；均completed/partial，历史原件不改。r5源码3324fea，提示词修正后6项受影响直接测试通过。语义质量仍部分失败，当前16/17，不归档。

**实际执行补充：** [r3共享回执](../../../docs/operations/investigation-audit-live-r3-20261031.json)记录部署、3主Run/2未发追加、原失败及临时Key清理。随后纠错材料修复6项直接验证通过，真实模型调用0；不将以下原本地通过或独审解释为最新真实完整验收。任务15/17，不归档。

# 实施阶段校验（2026-10-31）

用户“推进执行”后，本地实现与必要直接验证已执行，不能再沿规划阶段validation.md的“未测试/未实现”解释当前工作区。完整范围、失败、当前版本和未完成事项见[实施记录](../../../docs/investigation/audit-fixes-implementation-20261031.md)及[机器回执](../../../docs/operations/investigation-audit-fixes-20261031.json)。

- Case API/synthesis/product/navigation 26项通过；H1缺口保留修正后只重查受影响6项并通过。Incident受影响5项最终通过，其中模式失败用例初次2个subtest为时间格式断言失败，改datetime等值后通过；原失败日志保留。去重31项，不累加阶段运行数。
- Office原冻结错误响应及usage进入当前执行器＋HTTP模型替身，实际纠错16929≤17018，余89；新增来源与完整历史gaps保留。不是新真实模型结果。
- 本地OpenSpec1.13.0：`openspec validate fix-investigation-audit-gaps --strict --no-interactive` → exit0，`Change 'fix-investigation-audit-gaps' is valid`。
- 同工具：`openspec validate fix-case-followup-gaps --strict --no-interactive` → exit0，`Change 'fix-case-followup-gaps' is valid`。
- 安装脚本仅无参数准备分支：tag=20261031-r3，472个app Python文件，executed=false；未访问Docker/SSH/实际服务。
- git diff --check退出0；39份入口/调查/OpenSpec文档的1112个本地链接核对后，本轮调查目标均存在。PROGRESS原有另一任务的模型预检压缩包及SHA文件两项缺失单列保留，不归为本轮通过或擅自改动。首次链接脚本还将两项URL编码空格误报，解码后目标存在；见[静态记录](../../../docs/operations/evidence/investigation-audit-fixes-20261031/static-checks.json)。476份候选源码hash与当前工作区一致。

任务按实绩完成14/17。4.2源码提交 `bb8dbc3`、候选提交对应清单、5份定向body/方案已完成；5.2[未参与实现者结束独审](audit.md)0必须修，无业务重跑。21只读SSH预检连接超时，4.3/4.4真实部署、同批复验回执待实际条件与授权满足；5.3严格校验已通过，但全部任务和归档前完成检查未满足。因此不归档、不同步主spec、不关闭旧追加真实任务或上层2.2/2.3。

已保存本地源码提交；无新的真实PG/模型/ClickHouse/厂商调用、迁移、权限变更、worker启用、镜像构建、部署、远端推送或合并。只读SSH尝试未建立连接；原安装dry-run记录不回填为在线检查。
