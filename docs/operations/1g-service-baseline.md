# 1G 调查/响应服务基线

2026-10-20。固定上游Agents/Actions共591个原版构建输入及测试已迁入（426/165），6个原文件作必要启动/授权/真实缺陷修复，8个服务文件新增。原锁、Dockerfile保留；来源及差异见[清单](../handoff/1g-source-manifest.json)、[补丁](../../deploy/aisoc21/patches/1g-baseline.patch)。**本批人工调查与Actions dry-run基线通过；完整服务端尚未冻结。** 机器回执见[JSON](1g-service-baseline.json)。

## 实际部署与边界

21从源码按原锁hash构建，Python3.11.17；Agents核142项、Actions核37项运行依赖（实际计数以JSON为准），runtime无Poetry。Agents仅21 loopback18004→8084、4核/8GiB；Actions18005→8085、2核/2GiB。均非root、只读、nofile65536；连接1B PG TLS/Redis与1E网关。34个此前已有容器元数据、18个卷名保持，API/Fusion/embedding/gateway未重建。

开放人工Case调查、选定结果/Markdown/HTML查询，及Actions discovery/dry-run；其余HTTP入口404，WebSocket不开放。原路由过滤第一次因FastAPI延迟挂载失效，保留失败测试后改为ASGI入口限制，未删除原业务代码。关闭Kafka自动分诊/升级、记忆抑制/写回、调度/reaper、默认剧本seed和ATT&CK自动下载/索引；未连接Qdrant/embedding或真实厂商。无Realtime仍完成以下持久结果验收。

## 输入、调用与最终结果

标记已有告警经1F真实受理→Kafka/Fusion→API取得canonical ID，再关联测试tenant A的Case；B tenant作为拒绝对照。正向调查使用原默认编排、21网关→43真实模型，实际调用Recon、Forensic、Responder、Report四节点。只读`enrich_ioc`尝试因增强依赖未连接而失败，账本正确记录`success=false`和错误；结果属于上下文不足的部分调查，不作为调查质量或真实厂商查询通过。

| 结果 | 首次原版成本缺陷记录 | 独立修复复验 |
| --- | --- | --- |
| Case | `724a7d5d-77b4-5037-9bf2-c9a459d7f7d0` | `5c8cd297-8560-54cc-9586-0205d2e04def`，复用同一已有告警，无重投受理 |
| Run | `f5c3512d-c4a2-4fcc-a8d4-4dbf049c4bfb` | `3675fc0b-14b6-47cc-b3d6-489d32f9b4bf` |
| 实际模型调用/事件 | 4次；18个连续序号事件 | 4次；18个连续序号事件 |
| 实际tokens总和→PG账本 | 5731→11462，重复累计 | 5718→5718，一次计入 |
| 定价 | 原版把网关零值当8次measured；保留错误事实 | measured0、unpriced4，四个调用cost_usd=null；费用unknown |
| Markdown SHA-256 | `039d4b56123b0ad41131d211f8334a7afed8b9cc364d43fa713e9a90197b84e6` | `3f5d0f946011dcf611e0aa322c684bfdeb80da4855b1560f1219cddc764bc108` |
| Agents定向重启后 | API账本与报告hash保持 | API账本与报告hash保持 |

成功网关计数按label series汇总相对1E增加8次，与两Run各4个llm_response对应；中途窄探针因状态label选择错误得到空数组，保留该采集限制，不宣称获得逐Run指标差分。

身份验证包含无身份401、body tenant与身份不符403、外租户Case404，以及B tenant读取A Run/报告/API产物404。Case归属在发起前真实查PG；缓存结果读路由增加tenant绑定。Agents自身结果缓存易失，重启后的持久交付通过API的investigation/artifact路由，不能声称原Agents GET可恢复。两Case仍为`new`，Run完成不等于Case结案。

Actions真实HTTP共7检查：无/错误token401，禁用入口404，discovery可读，dry-run即使body传false也强制模拟，结果simulated。使用保留测试凭据哨兵及无效目标，不连接真实厂商；凭据剥离和服务token直接边界另由单元测试验证。审批、dispatch和真实响应未验。

## 修复、测试与限制

原`safe_ainvoke`与节点各记录同一响应，成本按响应/网关call ID在单Run内去重。43自托管路由缺可信价格，部署显式`AISOC_GATEWAY_COST_TRUST=0`，不把零成本header当免费。API/PG既有聚合numeric字段仍有零默认值，必须结合measured0/unpriced4解释为unknown；不追改首次错误账本、事件或报告。工具错误dict原来被当作truthy成功，现按错误字段判断失败；回归先复现失败再通过。

98项Agents、25项Actions直接相关测试通过，共123项，包含替身测试；真实HTTP/PG/模型证据另存，不能相互替代。首次测试路径、路由过滤、JWT缺type、工具成功标记、成本重复及采集器失败日志保留。两个标记API key已停用，实际401；JWT自然到期，未轮换共享签名密钥。样本/Case/Run不清理覆盖。

报告节点达1024 completion token上限，报告质量、知识消费、自动分诊、其他编排入口、真实厂商、审批执行与结案反馈仍未验。自动写回关闭。旧知识与较大模型按[复用计划](knowledge-data-reuse-plan.md)进入3C，允许20/21分担模型负载。

启动/停止见[运行说明](../../deploy/aisoc21/README.md)；仅操作本项目指定服务、保留原数据及失败证据，不重发unknown工作。下一单项为**2A告警不同发生/去重关系核对**，之后按既定路线接上下文和知识消费。
