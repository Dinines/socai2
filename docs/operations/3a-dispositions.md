# 3A-07近期分析员处置读取与采用来源回执

2026-10-20，批次`3a-dispositions-20261020`。**本批限定验收通过**：最终396项相关测试（API91、Agents305）、60项显式HTTP检查，真实API/PG读取、实际采用文本/账本、一次真实模型及重启回查已核。完整历史、结案反馈流程、因果采用与调查质量未通过，常驻worker、graph、审批与真实响应保持关闭。

字段、hash和逐项检查见[机器回执](3a-dispositions.json)，来源见[差异清单](../handoff/3a-dispositions-source-manifest.json)，交付核验见[本地核验](3a-dispositions-local-verification.json)。[原计划](3a-dispositions-plan.md)保留为输入；21 `evidence/3a-dispositions-20261020/`原始材料已受控同步88文件，完整模型输入/输出和凭据不放公开回执。

## 输入 → API/PG读取

复用A/B测试tenant，真实PG直接种入五条带batch/probe-only标记的短个人意见；alert_id为空符合真实约束，无DDL/约束放宽。它们不是实际分析员结案、纠正、第二人佐证或编译组织记忆。

| 样例 | 匹配及相对准备时刻的创建时间 | 实际结果 |
| --- | --- | --- |
| A a_after_split | 同rule/host，前12小时 | A第1条 |
| A a_rule_old | 同rule/host，前2天 | A第2条 |
| A a_entity_newer | 其他rule/同host，前3小时 | A第3条 |
| A a_unmatched | 其他rule/host，前2天 | 不返回 |
| B b_same_rule | 同rule，前2天 | 只在B返回 |

部署前Bearer和旧共享X头实际401。部署后`GET /api/v1/feedback/recent-dispositions`使用Bearer/alerts:read、认证tenant交集与显式RLS；A3/B1互相隔离，无scope/跨tenant/reader写ingress与反馈被拒绝。同rule仍优先于更新的仅entity，再按created_at及ID排序；原prompt的newest first不是跨优先组全局最新。

split=`2026-10-19T09:43:22.888022Z`时只采用A旧rule行、排除2条，更早split为空/排除3条；after_split相对测试split，所种创建时间均在准备时刻之前。表created_at非空、没有updated_at/历史或禁止UPDATE约束，故创建cutoff不能还原后来编辑的旧note。缺时间/坏echo等是单元或投影证据，没有改表强种NULL。feedback_id是来源身份，row_source_sha256是含tenant和请求匹配标记的当前API投影hash，不是DB行历史版本或认证签名。

AST提取生产SQL常量/formatter并记录hash，真实PG同连接执行原SQL→SAVEPOINT内SELECT1/0→回滚→原SQL恢复；不是HTTP、共享PG outage或API503传播验收。

## 读取状态 → 实际采用 → 模型

`recent_dispositions_read`分别记录success/no_match/disabled/unavailable/not_requested、参数、时间/cache/HTTP状态、数量、实际行/文本/hash及prompt块/hash。真实无配置、错误身份、闭合地址失败与恢复已核；空匹配不发请求。专用映射先于按tenant/URL/凭据hash/rule/entities/limit/cutoff隔离的缓存。默认120秒内服务端撤销后仍cache success；强制TTL0刷新实际401、采用0且生产prompt无旧意见，恢复后网络读取成功，不能称默认即时撤销/编辑生效。

一条`Account access review`告警（R-DISP-A、DISP-HOST-A、svc-review、critical、无MITRE，明确缺当前认证/进程/作业证据）经真实HTTP→SSL Kafka→Fusion→无group/无commit有界捕获→生产worker→21网关→43。fused为partition1/offset19，hash见JSON；只受理一次输入、只启动一次模型，未验常驻提交/rebalance/调用中崩溃。

最多5条、note240字符及含原heading/advisory的3000字符块预算保持。本次3条意见形成1336字符块；采用行/清理文本/rendered/hash与JSON解码后的实际safe-call message、Run payload和工件一致，完整prompt7355字符≤8000、无截断。safe-call入口捕获不当作传输线抓包。org读取success，技能读取success但selection no_match、KB no_match为新rule/entity的自然结果；旧查询另验原三能力保持。

| 实际产物 | 值与关系 |
| --- | --- |
| 告警 / 模型Run | `e2983f80-845e-5c66-a43c-2aab73779ff2` / `f2bfeb75-4c98-56c7-8a35-9f4da9b3ac7c` |
| 回复 / usage | needs_review，自报0.65；1779输入+130输出=1909 tokens，Run/成本一致，unpriced1/费用unknown |
| 意见观察 | 3条已提供，note和反馈ID精确提及均0；rationale概括参考过往意见，不证明因果采用、分类或引用质量；没有追加call索取结果 |
| 模型账本 | shadow/no actions，2事件/6工件（org/skill/KB/dispositions读取及prompt/response） |

独立probe-only Run `7f072075-1665-5668-986d-93d43550fd3b`把真实401回执经生产prompt投影，在读取工件INSERT处真实SELECT1/0：Run/事件/工件0/0/0→同Run恢复1/1/1→重复仍1/1/1且材料不变。该Run无模型/告警修改/成本行，不作模型成绩。首次读取事件/工件与verdict同事务，不冻结通用Run/alert更新。个人意见不覆盖当前直接证据，也不构成当前授权。

## 重启、失败恢复与当前运行

初394项（API91/Agents303）通过，实际模型、verify和原定向重启工件核对成功；收尾独立进程读取却经app.agents包初始化触发ImportError，日志保留。移除新reader对该包初始化依赖、用固定的闭合词表并补两种新进程导入顺序核对，最终396项通过。只额外构建镜像并重建Agents容器，env/mount/依赖/DDL不变；最终非root读取处置A3/B1、org success、skill A v3/B v1、KB旧查询各1条。**模型及原重启材料来自首48407679镜像，最终90126c76镜像模型未重测。** 后半只读resume无新restart/key mutation/输入/模型；另一次观察文件名单复数误拼只读失败亦保留，不写成全首次通过。

当前API=`sha256:41bae3dde2fdccb230622f30af99b6ef807469c930cb7b6aed1baf860eb7cd3d`，Agents=`sha256:90126c76cd8714fafef80c853fec595b0a6c7b702999bd7118e2cab564eae865`，tag=`dispositions-3a-20261020`，Fusion/Actions保持。7个运行文件、3个原测试差异、14个新输入见来源清单；完整[十六层命令](../../deploy/aisoc21/README.md)保留旧层并新增末层dispositions。

新映射`AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE=/run/secrets/dispositions/keys.json`只读挂载宿主`private/dispositions-3a`，UID/GID10001、目录0700/文件0600。A/B两枚alerts:read reader保留，到期2026-11-19T09:43:22.888022Z、最终200，三操作key撤销401；原六枚org/skill/KB key及文件hash/scope/env/mount保持。八枚reader分别映射，alerts:read不是本接口专属scope。原件只在[受控位置](configuration.md)，轮换保持权限并核映射/读取状态。

旧52告警/19Run/63事件/31工件/16成本行及既有规则/记忆/技能/KB全保持；新增1告警、2Run、3事件、7工件、1成本行、1 shadow决策和5反馈，当前总53/21/66/38/17，shadow决策12。其他34容器/18卷/134迁移保持，无基础设施重启；网关triage11→12、其他角色不增。60项显式HTTP的分段计数见JSON，typed reader内部调用及中间poll另计。

有状态prepare/deploy/acceptance/finish不盲重跑已受理输入、model-call-started或成功key生命周期。回退先停相关输入/消费者、核队列并保留PG/工件，仅撤最上层dispositions恢复3A-06 API/Agents及移除专用env/mount，保留原三读取层/身份；不清库/卷或重发模型，旧镜像不当同等能力，保留null消息与旧float-only消费者兼容限制。

下一单项[3A-08身份读取计划](3a-identity-read-plan.md)，**目前仅规划**。身份reader401、旧增强/工具身份、实际事件/UEBA、deep investigation版本pin、完整知识/调查质量与整个3A仍未通过；imported_at不等于HR有效期或历史版本。本批不开放常驻worker、graph、审批或真实响应，不冻结整个服务端基线。
