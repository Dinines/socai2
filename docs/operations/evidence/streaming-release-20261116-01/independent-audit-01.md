# 当前功能版独立结束审计

审阅日期：2026-11-16。审阅者：独立子代理 `release_audit`，未参与本轮实现；只读代码、配置和已保存回执，没有运行模型、投递消息、修改业务数据或部署服务。除本审计文件外未修改仓库。

**最终复审结论：`streaming-release-20261116-02` 的本期实现、冻结工件及发布安排通过切换前独立审计，可进入明确计划内的正式增量、接线验证和统一切换。** 这不是正式环境已发布或新批业务验收已完成的声明；增量后与启用/投递前的必要验证见末节。第8–10步和模型正文质量按负责人决定后置，整个含后置项的 change 不在本审计中归档或声称全部完成。

下文至“最终发布前复审”之前保留首轮审计时点的核对和待收件记录；末节承接最终r2、SessionStore修正及新版Swagger，不能继续把首轮待收件当作当前未解决的软件阻断。

## 审计范围与证据

| 范围 | 独立核对结果 |
| --- | --- |
| 任务/尝试生命周期与唯一调度 | 复核 `analysis-lifecycle-20261114-01`、`analysis-dispatch-20261114-01` 的实际PG/Redis证据说明；受理无假Run、实际执行后绑定、失败/unknown原件保留、有限重试、N和同主体串行有直接证据。第2步早期普通请求合并口径已被F4独立请求规则替代，不能沿旧阶段文档部署 |
| 真实入站→A/I | `test-streaming-ai-20261115-01/acceptance-01.json`：4真实生成、4 task/attempt/Run、9查询、62同源GET；独立重算其11份JSON原件SHA256全部一致。正文质量仍NOT_PASSED |
| Case首轮 | `test-streaming-case-initial-20261115-01/acceptance-01.json`：同一S01的两案首轮、4真实生成、277保存检查、58GET；独立重算9份JSON原件SHA256全部一致。accepted/uncertain/partial与10项引用问题保留，不改记正文正确 |
| S04更新与比较身份 | `streaming-budget-20261116-01/outcome-summary.json`、`saved-validation.json`、`http-validation.json`：新I正常保存4成员，整事件活跃Case扩到4成员并有第二轮，上一实际Run/Result身份可读；单A01案保持1成员/1轮。119保存检查与48GET通过。原3000/length失败不是此成功回执；C3/C6问题与正文未验保持 |
| F1–F5 | 复核事件诊断实际覆盖进入Case、管理字段不剔除有效A、确定未发送故障可有限重试、不同请求独立排队/事件驱动Case、联合现行合同执行等README及对应原件入口。明确PG/Redis/HTTP是真实依赖，模型/故障为替身；HTTP同源读取分别有22/24/52/89/90请求证据。不把这些替身结果冒充真实模型质量 |
| 可信HTTP与保存读取 | 第7步的受理、实际消费后状态、上一失败轮不可比而不回退早期成功轮、task/Run/Result及工件链接已有隔离PG/ASGI证据；21候选实际TCP链由同批A/I、Case及S04补齐。现行80操作，旧E11/E13/E36外部旁路已退役；第8–10步缺失能力不声称已发布 |
| W5 4177 | `streaming-w5-4177-20261116-01/flow-02/outcome-summary.json`及实际部署/HTTP/浏览器原件：0.6.0、62文件、10包/页面检查、14JS、10GET及清理后的真实空态。旧非空样本的具体领域/原答/轮次证据保留各自预览版本；不能用当前空态证明新增非空业务批次已经执行 |
| v2测试材料 | `model-blind-data-20261116-01`：4告警/13上下文/55模板，61业务文件递归检查及实际A/I/C3/Deep/C6构造视图；测试身份/固定来源/答案留控制侧，作者镜像名中性化保留相同对象关系及实际命令/权限/结果。该证据是离线输入检查，非真实模型采样，也不是无限范围的信息安全保证 |

原始证据均位于本目录的同级批次目录，历史 `not_completed` 数组描述该批当时范围；后续完成项用各自新回执承接，不修改原件追认。

## 源码与预算核对

独立重算了 `.local/processing-release/processing-20261115-r3/manifest.json` 的735个文件，与当前映射源文件比较无缺失，唯一变化为 `investigation-policy.toml`。独立重算候选HTTP profile的723个来源文件，无缺失，唯一变化同样是 `deploy/local-investigation/investigation-policy-case-v1.toml`。结果与根侧 `source-comparison-01.json` 一致。

预算变化已有11-16真实I/Case后轮、38项容量检查及同镜像loader/1MiB字符保护回执，当前代码无新增差异要求重跑历史功能矩阵。64K指当前服务输入+输出共同窗口；C3/C6输出16384会占用输入空间，不能以模型理论262K或准备字节额度宣称实际窗口扩大。新正式包仍需冻结该policy及所有运行profile，避免使用旧镜像内policy或候选覆盖配置。

## 正式切换前仍需审阅的最少材料

1. 新处理包/独立HTTP包的冻结清单、摘要、实际入口、选定基础镜像与包外导入核对；当前源码只差policy的结论须与最终包保持一致。
2. 正式目标aisoc的128/129增量、普通reader/writer/ingress接线及verify步骤。正式当前28表450列，候选32表521列不能替代正式升级；保留schema/配置备份，不运行空库初始化、不降级DDL。
3. 正式租户/actor、Topic/group、Redis namespace、湖/知识来源和路径的显式profile；敏感内容只留受控引用。HTTP、执行器、4177代理必须使用同一正式目标，不能仍读清空的候选库。
4. 正式生命周期明确采用已确认的I4小时、Case6小时、7天窗口与默认60秒一次重试，或有本轮明确替代配置依据。候选20秒/30秒/1天不能静默成为正式值。旧production profile的UEBA=true不能当作来源已接入证据；按实际可用源明确冻结。
5. 仅一个Fusion入站消费者和一个A/I/Case调度器的服务清单及旧服务停止/保留规则；准备后统一切换，失败读取实际状态后回退本轮应用，不自动复活旧消费者、不重派旧批次/回灌清理备份。
6. 发布后最小正常业务读回计划：新独立批次使用v2业务材料，经实际入站/受理、执行、保存和HTTP/4177确认同身份；不需要追加质量比较或故障矩阵。预先区分真实模型、来源未接入、旧可复用证据和本次新增证据。

上列是发布工件尚在准备时的审计待收件，不是新权限审批或额外功能需求。材料齐备后在本文件追加最终审阅结论；发布后事实仍须由实际回执证明。

## 文档与未验边界

部分历史README/完整测试规划仍写“W4/W5待”“S04成功分支未通过”等原阶段描述，当前PROGRESS已说明后续完成与清理。正式交接需要让当前发布入口明确指向新冻结版本和新回执，避免直接复用这些旧段落的运行命令；不要求改写历史原件。

模型质量NOT_PASSED、知识/反馈合理使用质量、未接入UEBA/graph/产品来源，以及后置第8–10步，均保持各自状态。新版本可发布范围是已验第1–7步及读取/展示，不扩大为整个产品或所有OpenSpec复选已完成。

## 最终发布前复审（2026-11-16，revision-02）

已阅读负责人要求的[调查执行模块确认](module-investigation-confirmation.md)、[HTTP后端确认及71操作问题补核](module-http-confirmation.md)、[测试模块确认](module-test-confirmation.md)，并与最终profile、源码和直接回执交叉核对。三份确认早于r2，仍保留其原时点的r1摘要与待补项；本节按新证据逐项承接，不改写旧原件。当前分支为`V1.1`，已有大量前轮未提交内容，本次没有暂存、提交、切分支或改动他人文件。

### 本轮两个实际阻断已定向解决

1. **SessionStore租户上下文。** [正式策略](support-rls-readonly-01.json)及[修正前回滚探针](session-rls-before-01.json)确认普通ingress默认没有租户，sessions的`WITH CHECK`会拒绝旧写法。这是实际问题，不能由授权脚本或连接成功替代。最终源文件`services/fusion/app/services/sessions.py`的变化仅在`record_event`和`close_idle`：取连接后进入事务，使用`set_config('app.current_tenant_id', tenant, true)`；父子保存同事务，关闭按指定/查得的tenant逐一事务执行并保持SQL租户谓词。没有改RLS、角色默认值或字段合同。事务本地设置随正常事务结束/回滚释放；既有异常降级行为仍保留。
2. [真实方法回滚验证](session-rls-after-01.json)从无租户普通ingress上下文执行该源码，父子关联、不同租户关闭0条、派生关闭1条、厂商会话保留全部通过，结束后0行/0授权提交。已检查探针代码确实调用SessionStore，而非仅手写等价SQL；探针中的外层事务用于统一回滚，不能冒称已持久授予正式权限。现有[sessions测试](session-tests-01.txt)为19通过。[Ruff比较](session-lint-comparison.json)的5项是修改前后同一旧发现，不是全lint通过，也不要求本期扩大修复范围。最终包内该文件摘要与回滚探针的`c1d658e408cf40279135c86c1ba0d64e426d038e1847328ae0eeab0daa34fd11`一致。
3. **Swagger旧71操作来源。** 第一版未上线工件和失败保留，最终正式副本来自已验80操作候选，发布版本为`streaming-http-20261116-r2`。本审计独立运行只读`verify-swagger.py`通过：80操作/55 GET、路径集合、参数、请求体、响应状态及Schema一致，三类为告警/事件/调查且无security。另读实际说明和示例，建案201为分配/首轮任务回执，事件诊断和再次调查202为task/status_url；退役的3个外部入口没有恢复。示例标明历史结构样本、不能重放旧ID。`servers`指向18024，manifest及Swagger配置指向这份新文件。部分操作的“21待发布”是准备时点描述，正式成功后由实际交接承接，不视为业务实现缺陷。

上述是对实际阻断的直接修复和复审，不新增模型质量采样或全仓测试门槛。

### 独立重算的冻结范围

本审计使用本机Python只读读取tar、manifest和来源文件，未执行包内业务入口、连接数据库/服务或调用模型。

| 冻结对象 | 独立核对结果 |
| --- | --- |
| `processing-20261116-r2` | tar内735份文件的长度/摘要全部匹配manifest，无多余/缺失来源；与已验`processing-20261115-r3`相比没有新增/删除，仅`investigation-policy.toml`与`smoke-fusion/app/services/sessions.py`变化。前者有已有预算续验，后者有上述定向真实RLS验证 |
| `streaming-http-20261116-r2` | 723份profile来源均匹配工作树及包内目标；726份manifest文件及tar全部匹配。SessionStore属于Fusion，不引起HTTP业务源码扩张；完整独立HTTP及核心仍在包内 |
| 统一发布清单 | [revision-02/frozen-manifest-01.json](revision-02/frozen-manifest-01.json)的755份文件全部重算匹配，含16份正式配置、HTTP包、128/129与增量入口、Swagger及运行环境文件；无缺失/摘要差异。远端上传回执确认新目录创建且全部文件核对，不代表服务已切换 |
| 镜像与包外导入 | [processing构建](revision-02/processing-build-20261116T054009652881Z.json)为amd64、冻结base、network=none，源码校验与既有自检通过；[HTTP构建](revision-02/http-build.json)有独立r2镜像。[无网络包probe](revision-02/package-probe.json)装配现行A/I/Case工厂及80操作HTTP，读取新policy、N1/poll60秒；0模型/业务写入 |
| 4177准备 | [viewer-preparation](revision-02/viewer-preparation.json)仍是`prepared_not_switched`，复用已验0.6.0镜像。独立由r2 runtime合同加实际version重算，SHA与代理配置一致；service/upstream环境均`streaming-release-20261116-02`，正式tenant及18024一致。富化Swagger合同另核语义，不与runtime合同混用字节摘要 |

| 关键身份 | SHA256 |
| --- | --- |
| processing tar | `bd81ac554300b5e015cf3ddcb5816541ccea9978892daed6c1925a7e2d03ad26` |
| processing manifest | `7c0a032913be8270a916ef3027539fb4068169fce9a1c90dc241c13891dcfcf6` |
| processing image | `e95a878b8d1bed6a6639666d5e46215bd38f478a5bd46c9bee5e30992cc7669d` |
| HTTP tar | `cb4aaae161e78fec01876e59cb3d834d0490ba001e4c825ab0729c836fff7a6a` |
| HTTP manifest | `0199df1949a8617d660eddde428f70094d3122d779332de7927488092dc76ee6` |
| HTTP image | `f3f43ebaeedf2438498dcc13bd7e2b99934d0ae599e528b0b8e7a06c264439e4` |
| 755文件发布清单 | `883dd853c6be7046d06532cfb238a6d05d42d4804781fe0482a8a49e2234f075` |
| 正式Swagger文件 | `c5850934aad0d8a3dd4f38133b1e99998375d9f248a3eb58a669ca0bc36b866a` |
| 4177 runtime合同 | `3f4f1be3fb1be69fb8be0be98af9ad17915338174e23b29ff7e63c375a4b72ad` |

### 正式配置与发布安排

最终[release profile](../../../../deploy/aisoc21/streaming-release-20261116-02/release.json)明确21的`aisoc`、既有正式tenant/actor和普通reader=`aisoc_app`、processor=`socai2_prod_processor`、ingress=`socai2_prod_ingress`，PG要求TLS。HTTP18024/Swagger18080与4177正式代理同目标，服务私密运行文件保存0o600，仅引用受控文件而未将凭据放入公开配置。已保存[连接probe](connection-probe-02.json)证明processor/ingress实际连到正式aisoc/TLS1.3、Redis DB8/9和湖aisoc，但它发生于增量前，不证明新表及缺失权限已安装。

生命周期统一为I14400秒、Case21600秒、活动604800秒、重试1次/60秒；N1/poll60秒。A/I/Deep输出8192、C3/C6输出16384，总tokens分别131072/131072/393216，服务共同窗口65536和1MiB准备保护与已验policy相符。UEBA/graph/product为false，knowledge为true且禁用分诊后同步；清空后的知识零命中必须如实记录。正式Kafka两个输入Topic、固定consumer group、Redis独立范围和实际湖reader/writer已显式配置，没有沿用候选短周期或候选tenant。

128/129通过已有增量入口应用，`analysis-ingress`补初始任务权限；`fusion-support-access.sql`仅向已有公共支撑表及connectors所需列增量GRANT，不重建公共表、不改变RLS、不运行空库初始化或清库。部署层停止清单已补齐五个旧API/投影/Agents入口；运行期的文件锁不能替代跨目录旧实例检查。回退安排为停本批新执行入口并核在途/unknown，保留业务与失败原件，可恢复旧只读viewer；不降级DDL、不恢复清理备份、不重放请求、不自动复活旧消费者。该回退意味着业务暂停，不能写成业务已恢复。

### 按执行时点区分的出口

**切换前当前结论：本期实现与冻结工件没有未解决的实际软件阻断，独立审计通过。** 可按stage11已授权的步骤进入正式增量和切换；不要求在DDL尚未执行时声称新表普通账号连通已验。

1. **正式增量执行后、依赖服务启用前必须核实：** 保留正式结构/配置备份，逐项安装128/129、ingress与support权限并执行正式verify。用实际普通运行连接核库/role/TLS、必要读写与真实租户上下文；补HTTP双池及知识/模型实际路由的必要依赖读回。现有SessionStore回滚验证可复用代码行为，持久权限及新表是否到位仍取本次实际回执。若此步出现具体失败，停止相依启用并仅修该阻断。
2. **统一启动和端口切换后必须核实：** 实际镜像/config/release一致；仅一个Fusion和一个联合调度；停止清单中的旧入口未恢复。HTTP无凭据读80操作/55 GET及同正式context；18080当前合同/服务器和必要CORS读回一致；4177为0.6.0、正式环境/tenant/合同。原候选HTTP/Swagger在新就绪后停止、原r4在r5可用后替换，不以空态或health宣布完整业务通过。
3. **新批投递前必须补齐：** 本次1告警+3上下文的v2生成器、material-source、实际依赖及显式正式Topic发送入口另行冻结并完成直接离线检查；不冒称0.6.0页面包已经包含该驱动，不绕过旧候选发送器限制。保存本批新run_id/UTC时间/tenant/实际payload字节和起始offset；确认真实订阅就绪。先上下文ACK及湖读回通过，再发送告警，unknown按原身份读回，不换key重发。本复审尚未收到该独立驱动冻结件，因此不声明投递步骤已经就绪；这是新批执行前接线，非上述服务包发布阻断。
4. **新批业务读回完成后才能声明本次发布验收完成：** 与测试模块共用一次“1条v2告警+3上下文→正式Kafka→A/I→HTTP建1案→Case首轮→实际4177”。取实际主体/task/attempt/Run/result，冻结实际请求、工具回执、模型原答及保存/读取证据；Case POST201及前轮null保持真实，账本新增live_execution和http-exchanges才能让4177发现新对象。展示至少读一份实际请求/原答及当轮已有领域/跳过原因，未命中不额外造调用。补查按实际前后1小时/主机/类型条件核，不套用fixture狭窄窗口或目的IP排除预期；直接来源仍单独核1条。测试颜色/来源识别/答案只在控制侧，不进入业务分析材料。

这个最小正常路径足够补正式接线与v2材料影响，Case后轮和上一轮比较复用S04预算续验，不要求新建第二轮、等待正式4/6小时周期或重复历史功能矩阵。HTTP模块较宽的读取清单据此用已有后轮证据承接；不会由本审计追加生成次数。

模型结构/执行/保存可用性与正文质量分开记录。若新批截断导致无可用I/Case结果、解析/保存/读取失败，正常流程仍未通过，不能用“质量后置”核销程序阻断；已明确后置的引用/正文缺陷则保留原答和`NOT_PASSED`，不反复采样、不改记已修复。第8–10步和产品页面全接线继续后置，整个change不归档。本文件是本期发布前独立结论；正式发布事实及新批验收须由后续实际回执承接。
