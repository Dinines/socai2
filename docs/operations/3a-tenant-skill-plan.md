# 3A-05：技能读取认证与失败语义

状态：2026-10-20已限定验收，见[3A-05回执](3a-tenant-skill.md)。下文保留实施前范围及判据；当时技能、KB、近期处置、身份实际401，本批仅处理tenant skill。组织记忆见[3A-04回执](3a-org-memory.md)，下一单项为[3A-06 KB读取](3a-kb-read-plan.md)。

先核现有技能API的身份、权限与tenant交集，复用受控每租户reader配置的方式前先确认所需最小权限，不增加万能共享key或匿名路径。核既有技能版本、启停/期限、作用域及选择优先级；读取失败不能等同于确认无匹配，缓存、映射轮换与有效期必须保留来源及边界。

改运行行为前补具体文件范围和判据。以A/B合成tenant、有效/禁用/过期及无匹配样例、缺scope/越权/不可用/恢复为直接边界，沿reader port保留frozen replay。用相关原测试及一次有界真实模型调用核实际采用的skill ID/版本/文本、读取状态、prompt工件、Run/API、usage及重启回查；选择成功不外推技能内容或模型质量。

组织记忆与历史工件不改写，KB/处置/身份后续分别处理。常驻worker、自动graph、审批及真实响应继续关闭；不扩成全量知识导入或全局认证重构。

## 当前批次实施合同

2026-10-20源码核对：resolved/active接口只收共享X服务头，API未配置对应token；技能读取应使用与既有技能查询相同的`settings:read`，不能扩大组织记忆的`alerts:read` key。只改本GET为标准Bearer、tenant交集及显式RLS，复用原当前active版本解析器；其他编写/回测/激活/退休规则不改。

Agents新增专用`AISOC_TENANT_SKILLS_KEYS_FILE`受控映射，每tenant独立只含settings:read的key，复用3A-04文件权限验证。结果记录读取状态/原因、缓存与有效/过期候选数；无匹配与读取失败分开，身份/地址隔离缓存、每次核已缓存期限、不在刷新失败时采用旧材料。保留原加法选择算法（rule20/technique10/source5/每keyword2、同分按ID），记录选择输入、得分/理由及实际选中版本。API只给当前版本，重复ID/版本冲突或格式无效不伪装成无匹配。

直接阻塞修复还包括生产worker保留上游source、技能匹配使用原始MITRE技术的fallback；不改变风险/策略算法。技能指导语只清理/限长一次，保存与实际prompt相同的文本/hash；读取/选择来源与新工件在现有verdict首次写入事务保存，错误回滚，重复不追加。frozen reader沿split快照，不访问live API、不按今日期限改历史材料，保留skills_under_test回测例外。

源码范围限API tenant_skills路由、Agents技能reader/reader port/frozen reader/state/worker/prompt/ledger及受控凭据helper的兼容参数；必要原测试更新另留差异。无DDL/依赖/新评分算法，仅构建并定向重启API/Agents；Fusion/Actions及基础设施保持。复用3A-04 A/B测试tenant和既有shadow/组织记忆，不改原经验与历史Run；新增技能及版本行是合成预激活样例，不宣称完成真实编写/回测/激活流程。3短时操作key最终停用，2独立30天技能reader key保留，只绑定A/B，原组织记忆key权限与映射保持。

验收复用有效原测试，补真实Bearer/tenant/scope、active/retired/expired、空集/无匹配、source/技术/平局、当前版本变化与历史工件保持、默认缓存期限与强制刷新故障/恢复。一次真实模型调用验证确切版本/文本及usage/Run/API，失败状态另做实际读取后的prompt投影及probe-only事务故障/恢复，不作第二次模型调用。重启后查相同工件并核旧材料/其他容器/卷/迁移保持。默认120秒缓存不保证服务端退休/撤销/编辑即时生效，明确记录。

原技能生命周期测试使用SQLite，测试镜像补装固定上游poetry.lock中的dev依赖aiosqlite0.22.1及wheel hash，不装入运行镜像。合成预激活读样例必须满足原FK/CHECK：另建4条明确failed/probe-only、无分数/报告、未执行replay的FK占位记录，不能当回测完成证据；不禁用约束或改真实激活规则。
