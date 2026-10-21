# 2B-02 处理规则版本与消费

本批范围：保留业务规则语法、原version字段与30秒tenant缓存；新增基于YAML原文和enabled的稳定内容指纹、实际采用来源/缓存状态，修复保存失败污染API缓存。原version仍仅为进程snapshot计数，内容指纹不代表持久递增序号。

验收：独立tenant经真实认证API保存规则→PG行→Agents实际applier/worker抑制分支；同输入在v1/v2/恢复v1的结果和指纹对应，缓存旧版本明确可见，另一tenant不变，依赖失败区分已知旧缓存与不可用。重启后配置/结果可回查，旧告警、规则和运行资料保持。自动Kafka worker、模型、知识与真实响应不在本批启用。

仅使用测试tenant；失败探针只修改单独探针进程的数据库目标，不停止共享PG。不重写历史结果，原回执保留。2B-02限定验收通过，下一单项为2C已有上下文/IOC来源消费；自动分诊另在3A验收。结构化结果见[JSON](2b-policy-versions.json)，[来源差异](../handoff/2b-policy-source-manifest.json)及[补丁](../../deploy/aisoc21/patches/2b-policy-versions.patch)。本批不等于所有策略入口或整个服务端基线通过。

## 实际变化

API规则响应新增`policy_revision`与`load_status`，保留原`version`。Agents结果新增实际采用的tenant指纹、updated_at、加载状态及独立file指纹/状态；worker抑制/普通返回摘要也携带`business_context_policy`。指纹为UTF-8规范JSON（键排序、保留Unicode）的`enabled`及YAML原文SHA256；格式`sha256:<hex>`，仅证明内容身份，空格变化也产生新值。未增加DDL、依赖、持久版本表或全副本同步。

API只在确认commit后发布缓存，保存失败不再把未确认新内容变成缓存；冷读失败返回503，已确认缓存失败回读标`stale_cache`。提交确认失败文本要求先回查再重试，不伪称数据库一定没变。真实共享PG未停；失败写/冷读使用测试替身，真实依赖失败仅在独立探针进程指向闭合端口，不改服务环境。

## 实际输入与结果

测试tenant A=`6282c421-71a6-5f5a-9991-38b933069a46`。3条原始low告警经真实alert-ingress→Fusion→PG→API，取API中已持久raw_event并补规范ID/tenant作为规则输入；原材料始终保留low。正常规则和维护抑制均消费真实PG行。

| 检查 | 结果 |
| --- | --- |
| 原版GET | 同一空配置连续GET，version为1/2且无稳定内容标识；不是持久版本 |
| v1实际采用 | API保存→PG YAML/enabled/updated_at→生产applier方法：high、cloud、policy-v1；API/实际采用同指纹`sha256:0734db5a74c76701ccb7b56c44a0a47b5979855a8a56173c6a95e73eb9427576` |
| v2与缓存 | 保存v2为critical/identity；同一applier缓存内仍high/cloud且明确报告v1/cache；实际等待30.5秒后采用v2 `sha256:727b3419f6ab3278997f0df86d88a150e828e963ff29e839ca4db6844a787301` |
| 恢复v1 | 再保存原v1 YAML，内容指纹恢复、updated_at为新值；新applier采用high/cloud。已记录v2输出仍critical/identity，原告警low不改写 |
| 抑制实际消费 | 直接调用生产worker.triage维护样例，匹配routing/maintenance规则、suppressed=true、携带实际v1指纹、response_dispatched=false，无模型请求 |
| 租户/权限 | 另一tenant同host/user保留low、无匹配且empty；匿名401、只读key保存403、非法规则422 |
| 依赖失败 | 热缓存刷新失败仍采用确认v1，标stale_cache；新applier无缓存标unavailable、revision=null，不能当合法无匹配 |
| 相关测试 | API42 + Agents41 = 83通过；5项新回归在旧实现均失败，原上游测试断言未改 |
| 部署/恢复 | 只更新/重启API与Agents，env/挂载/开关不变；API99、Agents142锁依赖及全部app文件匹配；重启后规则指纹、实际正常输出和3条原始告警/关联回查保持 |
| 保留/收尾 | 22条旧告警材料hash不变，新增3条总25；此前规则表无行，本批新增1行；其他34容器/18卷、134迁移保持，3key停用401，Kafka lag0，模型网关成功计数不增 |

共25项实际HTTP检查：原版GET2、更新后API检查13、告警最终回查3、重启回查4、停用密钥检查3；轮询中间404不计成功验收。独立方法调用、真实HTTP/PG、测试替身分别在JSON记录，未将preview当实际采用。

## 当前运行与限制

当前API为`sha256:f88bbcc9579727a8f81acf4e2fb2168485230d7889602943d46e13d711acde54`，Agents为`sha256:4ac381d99e4e68e588f145e51cd2e3e98f02e6d52ce9e9822344ab43edd50b90`。Fusion保持2B-01风险镜像。启动在risk层后加[policy层](../../deploy/aisoc21/compose.policy-2b.yml)，完整八层命令见[操作说明](../../deploy/aisoc21/README.md#当前apiagents2b-02处理规则)。本批有状态工具已执行，不重跑原标记/检查点；新批次另建身份和数据。

- Agents自动Kafka worker始终关闭。生产方法在独立探针容器中手动调用，未验证常驻worker订阅、完整模型分诊或真正team分派；普通severity/tag/route消费停在实际applier。
- 原抑制分支在ledger写入前返回，本批摘要只保存为运维证据，不冒充持久决策账本；3A开启前必须补验抑制记录与失败处理。
- 30秒缓存未改；故障可继续无限时长使用已知旧规则，但明确标stale_cache。冷依赖失败保留原fail-soft行为并标不可用，不把“未应用规则”解释为规则允许。
- API的DB行缺失仍可能返回旧缓存，标missing_row_cache；删除、多副本并发、CAS、全副本同步和持久单调历史版本未验。内容指纹不证明作者或原因，也不代替审计。
- 全局文件与tenant规则同时配置、tenant功能暂停、外部直接写入坏YAML的完整行为未扩验；只保留所选原测试。Fusion ML状态接口认证未配置仍503，尚未接线，不把本批通过外推到该接口。

回退前停止新配置写入和新输入，用保留的原API/Agents镜像；PG规则与历史告警保留，回退会失去新指纹/状态字段并恢复缓存污染缺陷。规则内容恢复只作用于之后的采用，不重写原记录。费用unknown，无真实厂商动作。
