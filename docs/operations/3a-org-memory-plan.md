# 3A-04：组织记忆读取与失败语义

状态：已完成限定验收，见[3A-04回执](3a-org-memory.md)；下文保留实施前范围与判据。触发证据见[3A-03回执](3a-risk-score.md)：真实模型链上的五类可选context reader仍401。本批先处理`organisation_memory`→API `GET /api/v1/feedback/context-statements`，复用既有PG编译语句与有效期逻辑。

先核上游服务token与路由认证依赖的实际关系，形成明确tenant/workload读取授权及最小scope；不借用万能管理员key、不开放匿名或任意tenant绕过。合成测试tenant和只读探针隔离；不修改历史反馈、语句或模型Run，不因组织习惯直接关闭真实严重告警。

结果需区分成功有材料、成功无匹配、禁用、认证失败、不可达/错误及缓存过期。缓存不能把失败伪装成确认没有历史，过期语句不得继续充当当前证据；若允许使用旧缓存，必须明确stale及来源/时间。模型prompt、Run工件和API记录实际采用的材料与读取状态，不能只凭HTTP200宣称知识消费。

验收用现有有效原测试和必要关键边界：A/B租户及缺scope/错误身份拒绝，真实PG语句的有效/过期/停用读取，无匹配与实际HTTP认证/服务失败区分，缓存恢复，以及一次有界真实模型调用核实际收到的语句、usage/账本/API和重启后回查。失败标记另用实际读取失败后的生产prompt投影和probe-only账本验证，不宣称失败样例也调用模型。每项写输入→调用/材料→最终状态，模型内容只作证据核对，不以单样例证明质量。

技能、KB、近期处置和身份reader后续分别迁入；不把本批扩成全量知识导入或新认证体系。常驻worker、自动graph升级、审批与真实响应保持关闭。具体实现与验收在改运行行为前补充，不提前写成已经通过。

## 当前批次实施合同

2026-10-20只读核对：API未配置Agents发送的共享token，因而真实HTTP401；旧直接函数测试模拟token成功，不能证明HTTP部署通过。只改本GET为标准Bearer身份、现有`alerts:read`权限、显式tenant交集与RLS上下文。Agents通过受控只读JSON按tenant选择各自API key；无映射明确未配置，不退回共享服务token。本接口不再接受仅共享X头授权；其他路由不在本批修改。

live读取结果增加成功有语句、成功空语句、禁用、未配置、认证失败、服务/响应失败等状态和时间、来源、缓存信息。接口读取tenant全部有效语句，空结果只代表没有有效tenant语句，不称为没有与告警匹配的历史。缓存按身份隔离，TTL内也检查语句有效期；过期缓存或请求失败不采用旧材料。模型只采用预算内的语句子集，结构化回执记录实际采用内容/hash和状态，并与prompt工件同事务保存。frozen replay仍通过reader port读取split快照，不访问live API，不按当前时间改历史材料。

源码范围为API feedback路由、Agents organisation_memory/triage_persistence/worker/state/prompt及ledger，必要时补frozen reader的只读适配；原测试按明确变化更新，新增直接影响的认证/expiry/cache/账本边界。无DDL、依赖或评分算法变化。只构建并定向重启API/Agents，保留Fusion/Actions及共享基础设施。测试tenant创建有效/过期/短时语句；表无enabled列，“停用”验证reader禁用配置。使用一次真实模型调用核实际材料和状态，其他路径复用原测试及真实HTTP/PG检查，不扩成模型质量矩阵。

部署采用两枚30天有效、分别绑定A/B测试tenant的reader API key（仅`alerts:read`），各自独立禁口令登录服务账号；JSON放受控目录、归容器UID10001，目录只读挂载，重载映射支持原子轮换。三枚3小时操作key验收后停用，reader key保留供已配置路径继续读取，仅授权所列tenant，不自动覆盖既有其他tenant。凭据与到期/轮换位置入配置索引，绝不写公开值。同步补这条ledger路径中事务内RLS设置，验证新工件失败真实PG回滚和同Run恢复，探针Run与真实模型Run分别标识。
