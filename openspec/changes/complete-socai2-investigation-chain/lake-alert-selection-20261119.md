# 步骤4：已有告警选择、身份及A/I接线

2026-11-19，承接湖3a–3f，属于主change的3.7/3.21及IA03；不另立change或重复任务树。4a v2、4b限定接收/存取及4c持久交付已完成：[4c当前回执](../../../docs/operations/evidence/lake-alert-delivery-4c-20261119-01/README.md)验证同批湖的持久登记、接收后确认、同文幂等、失败/unknown不越过及HTTP读回；[4b回执](../../../docs/operations/evidence/lake-alert-receive-4b-20261119-03/README.md)保留长正文及首次接收证据。使用3e已入湖数据在独立PG验证，初诊只登记未执行。后续按依赖推进必要工具及一条Case；正式发布和Git同步未执行。

## 4c实施安排（2026-11-19）

本轮已获准完成湖到告警接收的持久交付。业务效果：已落湖的候选先成为可读回的PG待处理项，再调用4b；只有确认首次告警/材料/初诊事务已提交，才确认交付。重复扫描或同文重试不重复创建；失败、hold、结果未知不越过，已有unknown尝试保留原结果。范围限此接线，不执行初诊模型、不创建Case、不重放Kafka、不发布正式服务或Git。

实现顺序为本规划/strict→131内部增量及交付器→配置文件驱动的独立worker入口→定向检查→21新隔离PG及专用缓存的合成/实际湖验证→HTTP读回/交接。复用4a选择、4b接收及130回执。4c不修改公开告警HTTP字段或V1原件，不建通用恢复框架。

| 部分 | 实现与必要验收 |
| --- | --- |
| 湖发现与登记 | 只读显式tenant/source/mapping范围；先校验完整有界扫描、复算选择和同ID版本冲突，再在一个PG事务登记本次全部逻辑版本的去向。新增131的交付项和尝试表。只保存决定及精确湖引用，正文仍按4b从湖读取。无移动时间水位：重复有界扫描通过稳定delivery_key幂等，旧时间/迟到记录不会因游标被跳过；超范围上限或扫描不完整直接停止，不截断后推进 |
| 接收及确认 | 同来源用PG会话锁串行交付，按待处理项固定顺序取头部；先持久登记receiving尝试，再调用4b。PG确认交付同时检查130回执、来源版本和告警/材料关联，不能只信任函数成功返回或Kafka已commit。完成确认事务后才返回已交付 |
| 失败与未知 | 接收failed/held/unknown或确认提交未知时停止本轮，后项不执行。receiving遗留视为未知；重启先只读查询4b持久回执，证明存在则补确认并记录recovered尝试，不重跑Fusion。未知且无已证明回执时保持unknown，不自动重新执行副作用。已知失败可在下一次显式运行重试同项；不删除/重写旧失败或unknown尝试 |
| 配置与运行 | 独立worker显式选择selection/receive/delivery/连接文件；同库/同scope/规则绑定不一致拒绝，地址、开关、轮询、每轮数量及超时均在配置中。可单轮验收或持续轮询；遇未解决交付停止退出，正式启用另按整个change交付。新装/升级/verify同步131 |
| 直接验证 | 合成用真实PG/Redis/CH与Fusion：登记保存后新实例继续、只读扫描重复、同文不增告警/材料/初诊、提交失败后项未执行、接收提交后丢失回执先unknown再只读恢复、无提交证据的unknown保持阻断、确认写入拒绝后不越过。只补这些直接边界，不铺故障矩阵。实际只读复用3e湖，新PG按显式上限交付，保存并HTTP读取材料/湖原文/accepted任务，全部未交付去向保留私有报告 |

证据入口`docs/operations/evidence/lake-alert-delivery-4c-20261119-01/`；真实记录、统计、ID、摘要及HTTP正文仍留21，仅回传结构和固定执行状态。通过需同时有持久登记/尝试/确认的数据库读回、受控失败与unknown不越过、真实数据HTTP读回；不以CLI成功或合成代替实际验证。初诊执行、工具/Case和统一发布不在本步核销。

### 4c限定结果

[01批回执](../../../docs/operations/evidence/lake-alert-delivery-4c-20261119-01/README.md)已通过：真实worker CLI先持久登记、另进程单轮交付，再重复扫描及同文接收；聚合、关联和任务唯一性在21程序核对，完整材料及湖引用经实际TCP HTTP读回。每轮显式上限20，其余待处理项继续保存，不称整批告警全部处理完成。合成使用真实PG/CH/Redis/Fusion验证新实例接续、旧时间记录发现、接收提交失败、已提交但回执丢失、无证明unknown及确认写入拒绝；各未确认项均阻断后项，恢复另记尝试，不改写旧失败或unknown。

65项Fusion及11项安装入口检查通过；3项依赖旧本机数据库的检查未选，本批另验真实新装、131重复增量及reader verify。HTTP首版脚本沿用4b的大正文样例要求，与4c交付状态合成输入不符，保留原失败；移除该不适用断言后，合成与实际均只读复验通过，未重派接收。4b的大正文证据保持。最终封包与本机源码一致，正式Fusion/HTTP及48列表保持，临时HTTP和专用缓存已停止。仅关闭4c，不核销主change整体任务。

## 4b实施安排（2026-11-19）

目标：4a选出的、身份及必要投影明确的告警，经现有RawAlert/source-v1、Fusion处理和socai2接收事务，保存告警、完整材料、来源引用、事件成员及一次A/I initial任务；HTTP能读回对应材料，并按冻结湖版本引用取回完整OCSF（收到的Kafka正文）及可选raw_data。初诊“登记”指analysis_tasks accepted，不表示模型已执行。

本轮为一个完整的接收/存取步骤：设计与strict→内部适配及接收事务→必要合成检查→21独立PG数据库与临时验证进程→HTTP读回与幂等复验→记录结果。3e湖只读复用，测试PG独立于正式调度器；不重放Kafka、不启动持续消费者，不改原湖数据或正式服务。

| 部分 | 实现与验收条件 |
| --- | --- |
| 适配 | 复算4a v2判定及正文版本；metadata.uid生成来源告警ID，保留原ID、完整OCSF、来源角色、可靠事件时间及湖引用。标题/严重度等必要投影无依据时明确hold，不使用RawAlert默认中危掩盖缺失；partial只按既有规则读取。配置文件明确来源、字段路径、严重度映射、时限和大小预算 |
| 全局身份及持久回执 | 新增内部增量表lake_alert_receipts，以全局source_subject_id唯一，记录原ID、租户/来源归属、正文版本、告警/材料和湖引用；不修改V1原件或告警HTTP字段。在同一事务先争取该身份、再调用现有Fusion及接收写入；跨归属、同ID异文或原有记录缺证据保持hold。提交后才返回created/duplicate；失败和结果未知不等于接收成功 |
| Fusion与初诊 | 复用真实FusionEngine、去重/关联和Socai2AlertSink写入；保留首次结果及恢复语义。新增来源回执和既有告警/材料/成员/初诊任务同事务提交。同文重试读取首次保存的材料、任务及事件，不再Fusion、不增加revision或初诊、不覆盖人工字段；4b不发布Kafka或消费初诊任务 |
| 1MiB及完整材料 | 对本接入通过显式profile分别给出正文与快照预算，替代固定1MiB；检查正文接收、快照生成/恢复/Redis及PG读回，超预算明确hold。完整OCSF的长整数/小数和原始JSON字符串保持，页面原文可从既有材料HTTP及湖引用读回；不截断、不只调大一处。旧非湖接收路径的默认预算保持兼容 |
| 验证 | 合成：首接收、同文重试、同ID异文/跨归属、缺字段/partial、超过1MiB正文和完整快照、小数与长整数、超预算不入库及直接事务失败。实际：3e固定范围只读判定，全部去向保留私有报告；有可交付候选才核实际落库与读回，未选中/hold不算成功。用SQL聚合数、稳定ID集合及程序摘要核材料关联/任务唯一；HTTP读告警、材料、首次快照及湖完整原文，不要求人工逐条正文比对 |

4b证据位于`docs/operations/evidence/lake-alert-receive-4b-20261119-03/`，01/02失败及中间回执保留。实际记录/统计/摘要/HTTP正文仅保存在21受控目录；Codex只接收结构和固定执行状态。合成和真实DB/HTTP保存读回均已通过，关闭4b限定步骤；实际类或大小未覆盖如实留在私有报告，不以合成代称真实覆盖。后续4c已有本页独立回执，主change任务和结束审计不提前核销。

直接验证配置限定最多20个候选接收尝试，按已冻结来源与稳定排序选择；其余候选记为not_attempted_validation_limit，不冒称整批均已变成告警。数字/正文读回也属于本步完整性：新湖首次结果采用fusion.first-result.v2的数字规范化摘要，避免JSONB改变数值写法导致完整快照被误判损坏；旧v1摘要/回执保留原算法。材料和新快照HTTP读取用精确小数解析及数字原样输出，冻结ContentView字段、类型和路径保持不变。

### 4b直接验证阻断修正

02批合成接收及HTTP复验通过；实际批停在`actual_delivery_present`，选择程序给出`finding_activity_semantics_unmapped`，不能认定实际落库通过。先保留该失败，再解决本步入口的具体阻断：v2发现类增加可选`initial_activity_ids`，旧profile缺该项仍按`create_activity_ids`处理；当前接入显式选择0/1/99。依据是负责人已确认的不可变告警合同及明确boolean告警标记，不是把Unknown/Other改写为Create。类/类型一致、ID、标记、状态和冲突校验继续执行；初始活动配置不能包括Update/Close。没有标记不接收，false只落湖，同ID异文和跨归属仍hold。

必要验证：合成覆盖Unknown/Other的true/false/缺标记、partial、未确认ID、显式生命周期拒绝与旧profile兼容；修正增量130的新装/升级验证对新增表列和reader读取的识别。随后新03批重新执行合成与实际接收/HTTP，保留01/02原件，不重用失败批任务、不改3e湖。只有实际接收及读回通过才能标记4b完成；若仍无候选则保留未通过并报告具体入口条件，不制造告警。

03结果：真实Fusion/PG首次接收及同文重试通过；合成超过1MiB、精确数字、跨归属/异文拒绝、人工字段保护及提交失败回滚通过。实际HTTP首次因验收脚本要求可选raw_data非空而失败；按既有合同修正为与输入字段对应后，仅只读复验通过，不重发告警。完整Kafka OCSF在ocsf_json，raw_payload为可选raw_data，二者不混同。106项定向检查、增量130新装/重复应用及strict通过。新湖v2快照保持精确数字，旧v1恢复沿原float摘要语义。正式服务及48列表保持，专用缓存及HTTP已停止；此为4b结束时点，后续4c结果见本页上方。

## 当前合同与本轮出口：全局ID、一次性告警

负责人已在本会话明确：告警身份使用`metadata.uid`，全局唯一，不以租户、来源、产品或设备作为唯一性前提；本接入认定告警没有更新。该明确答复替代首批v1的finding_info.uid候选及待确认生命周期假设，不再重复请求同一确认。

采用显式v2 profile：`identity_scope=global`、`alert_lifecycle=immutable`、`identity_scope_paths=[]`；已配置类别均使用metadata.uid且identity_semantics_confirmed=true。租户/来源继续约束湖查询与存储归属，不加入来源告警身份的生成。finding_info.uid仍保留在原文，不用于合并告警；相同finding_info.uid但不同metadata.uid是独立输入。

| 情况 | 当前处理方式 |
| --- | --- |
| 已配置类别、明确告警标记、有效metadata.uid，首次接收 | 生成稳定的全局来源告警身份候选；4b按现有source-v1接收并登记一次初诊 |
| metadata.uid及规范化OCSF内容版本均相同 | 按同一条重发处理；Kafka位置、入湖时间及规则版本变化不造成新告警 |
| metadata.uid相同，OCSF正文版本不同 | 违反一次性告警合同；湖保留各版本，候选进入review，不追加告警材料或覆盖原告警。同一次扫描发现冲突时整组候选待核，不按查询顺序选“第一条” |
| 发现类明确Update/Close或非活动状态 | 当前不建立更新/关闭分支，记录合同不符并待核；网络连接的Close仍是网络活动，不当作告警关闭 |
| 缺ID、字段冲突或未配置类别 | 保留湖材料及原因，不用内容指纹、finding_info.uid或Kafka坐标补造告警身份 |

全局唯一是已确认的来源合同，程序仍需检查违例。只读扫描只能核所选湖范围，不能证明所有租户/来源的实际全局唯一；4b必须核已保存来源ID、归属与正文版本，不能把“告警已存在”直接当成允许追加材料。租户隔离不因此取消。

本轮依赖已满足：来源身份答复及3e既有隔离湖数据均已有。本轮步骤为规格修订与strict校验→v2规则及同ID冲突判定→直接合成检查→同3e库只读判定/私有保存/读回→当前交接同步。v1仅保留复核旧批次所需兼容，不再作为当前部署示例。

必要检查限于本次受影响行为：无产品/设备字段仍可生成身份；跨来源/租户/产品身份稳定但查询仍隔离；不同metadata.uid不因finding_info.uid相同被合并；重发、同ID异文、未知旧正文、更新/关闭标记、partial和网络Close；同批冲突不依赖行顺序；报告保存及读回。复用首批v1语义检查，避免改写历史证据。实际报告及统计留21，只回传固定执行状态；不调用PG、Kafka消费者或模型。

4a历史批次从`docs/operations/evidence/lake-alert-selection-4a-20261119-02/`开始；修正partial冲突分组后的回执为[03](../../../docs/operations/evidence/lake-alert-selection-4a-20261119-03/README.md)。这些4a证据仅证明规则与只读验证。后续4b已有独立PG/HTTP直接证据，见本页开头；不能将4a历史通过解释成当时已接收或执行初诊。

## 当前依据与新增发现

依据21当前SpiritHub源码及本仓库未发布候选代码，不以旧说明代替实现。21 SpiritHub源码HEAD为`bb368df8cbebba85516a6fd2a47cc74e4afd75b9`；三个相关Go解析文件及OCSF1.9合同与本机只读参考指纹一致、目标源码无修改。实际normalizer镜像仍为`15b8ff0e617d0a1c389dfa6ca04e643d855fbf5d790cd0ec7c7b06d84e4eeb64`；源码一致不等于已证明该二进制逐文件构建来源，保留此界限。

- 通用promotion仍按发现类或严重度提升，不判断is_alert；不能用于本次筛选。
- `ocsf.go`的finding分支把`activity_id`固定为Create，`finding_info.uid`优先用厂商`alert_id/finding_id`，缺失时用`event_fingerprint`。`metadata.uid`来自清洗记录event_id。这些字段不能互相当作已确认的告警长期ID。
- 普通解析partial会降为class0，原分类进入`unmapped.spirithub.classification`，被移走的字段进入`partial_fields`；网络解析partial可能保留根is_alert。筛选必须阅读原JSON，不能仅看湖中的class0或UInt8化is_alert列。
- 现有PG接收器可在同一告警下追加材料，但只在主体首次插入时登记A/I initial任务。收到更新不等于已自动复分诊；更新/关闭也不能伪装成新告警绕过此行为。
- 正式旧接收路径默认仍为1MiB；4b候选通过显式profile配置正文和快照预算，已完成超过1MiB合成正文的PG/HTTP读回，未据此宣称正式服务已更新。

OCSF1.9的[Detection Finding](https://raw.githubusercontent.com/ocsf/ocsf-schema/1.9.0/events/findings/detection_finding.json)把可更新发现与活动型告警分开；[finding_info.uid](https://raw.githubusercontent.com/ocsf/ocsf-schema/1.9.0/objects/finding_info.json)标识发现；[security_control](https://raw.githubusercontent.com/ocsf/ocsf-schema/1.9.0/profiles/security_control.json)中的is_alert表示可告警信号。上述Schema说明不证明某个生产者生成的ID已具有相同生命周期语义。

## 整体步骤与出口

| 步骤 | 本步效果、依赖与必要验证 |
| --- | --- |
| 4a / 本轮修订 | 将已确认的metadata.uid全局身份及一次性告警合同落入v2规则，复验重发/冲突和同批只读报告；首批v1证据保留 |
| 4b / 已完成限定存取 | v2候选经现有RawAlert/source-v1与真实Fusion写入独立PG；完整材料、来源回执及首任务登记同事务保存，真实HTTP读回。明确初始活动配置、同文幂等、异文hold、超1MiB正文/快照及精确数字已验证，冻结告警HTTP字段不变；持续派发未启用 |
| 4c / 已完成限定交付 | 有界湖扫描→PG持久登记→4b接收→数据库证明后确认；同文幂等，failed/held/unknown阻断后项，未知先只读回执恢复。同批湖与合成直接验证、131新装/重复升级、HTTP完整读回通过；正式持续进程未启用 |
| 后续工具/Case | 依据实际类和字段覆盖逐项实现必要工具及一条Case链；普通日志仍全部落湖，不因告警名单丢弃日志 |

## 4a v1筛选合同（首批历史；当前使用上方v2）

所有材料已在湖内，筛选不会删除、改类或重新入湖。profile显式绑定database、tenant、source_namespace、mapping_version、OCSF版本、候选规则和只读上限。参数/来源错配直接失败，不回落默认库。

1. 读取完整ocsf_json；非法/非对象/tombstone等为`review`，保留原文引用。metadata.version必须匹配来源合同。
2. 保留根class。仅在根class0且上游明确partial时，允许以结构完整且相互一致的classification作为筛选目标；该目标只用于判定，不覆盖湖列或原JSON。目标class/category/activity/type必须匹配。
3. is_alert仅接受JSON boolean。数字0/1、字符串、null均不得自动当成已确认标记。根字段明确存在时不能用partial字段掩盖；根与partial同字段冲突进入review。partial回填仅在本合同明确允许且根路径缺失时使用；缺父节点与显式null父节点不同。
4. 首版支持已核语义的2003/2004发现类和4001网络活动类；其余明确true但未配置的类别进入review，待受控覆盖盘点后扩展。未标记的普通非发现类可以保留为lake_only/unmarked，不能把unknown标记为false或自动提升高严重度日志。

| 输入语义 | 动作 | 后续约束 |
| --- | --- | --- |
| 明确is_alert=false，且不是已配置发现类的更新/关闭/非活动状态 | lake_only | 全量保留，不生成新告警 |
| 发现类Create、is_alert=true，且状态非Suppressed/Resolved/Archived/Deleted | new_alert_candidate | 仍需确认身份及4b材料可交付条件 |
| 发现类Update，或Create携带非活动状态 | update_candidate | 只关联已有主体；找不到原主体则hold，不新建告警，不覆盖人工处理状态 |
| 发现类Close | close_candidate | 只保存来源关闭观察；不等于关闭我方告警/事件/Case，也不自动触发新的A初诊 |
| 已配置网络类is_alert=true | new_alert_candidate | 网络Open/Close/Traffic等都是网络活动语义，不能套用发现类Update/Close语义 |
| 发现类缺标记/未知活动、身份/类型冲突、明确告警但类别未配置 | review | 给出明确原因及原文关联；不能静默丢弃或硬拼合法OCSF |

partial只影响材料质量，不自动排除明确告警；关键判定字段缺失/冲突才阻止相应候选。普通日志、未分类和review材料仍可用3f接口查询。

## v1身份与版本合同（首批历史）

分别保留三个层级：

- 湖版本引用：tenant/source/mapping + event_id/source_version/event_time/class_uid，可精确读取完整材料。
- 来源日志身份：metadata.uid；缺失时只有Kafka位置可用于同记录追溯，不能以正文相同推断跨Topic重复。缺日志ID的告警候选保持待确认，不用临时时间或随机ID造业务身份。
- 告警主体身份候选：发现类使用finding_info.uid；网络活动型告警使用metadata.uid。均置于tenant、配置source_namespace及明确产品范围字段之内，并生成候选source_subject_id。它不是现有alerts.id，不修改既有告警ID算法；后续按已有source-v1接线。产品范围缺失、ID无效或生产者未确认稳定性时，候选不可自动交付。

重复的同一湖版本使用稳定delivery_key；同主体不同内容版本是追加材料，不能新建主体。delivery_key不包含规则profile摘要，规则升级不能让同一版本重复产生业务写入；decision_id另包含profile摘要以追踪当次判定。同ID不同来源或产品范围必须分开。field路径只允许合同白名单，不能从标题、严重度、主机或规则名称拼长期身份。

4a只输出候选身份和判定，不声称已经验证生产ID的长期稳定性或厂商状态更新。固定范围内能核对重复/新版本的形状；缺少真实更新样本时保持未覆盖，不把程序自洽当作来源语义确认。

## 首批提出的来源问题及当前答复

1. **已答复**：使用metadata.uid作为全局唯一告警ID，不再依赖finding_info.uid及产品/设备范围。直写与转发重叠时须原样保留该ID和正文，作为同文重发处理。
2. **已答复**：本接入告警没有更新，不开发来源更新/关闭归并。明确的发现更新/关闭或同ID异文作为合同不符保留待核。
3. is_alert=true是否确实代表对方希望进入调查的已有告警；合规通过/失败、抑制/已解决及partial如何表示。直写继续遵守既定Topic、OCSF1.9、原时间和完整JSON要求。

is_alert仍沿明确boolean及类别校验处理，不将高严重度自动当成告警；第三项实际映射覆盖不能由ID答复推断为全面通过，但不再阻止已确认身份合同的实现。对外发送及正式直写切换另行记录，不声称已完成沟通。

## 4a直接验证与证据

实施前strict校验；只新增纯判定及只读验收入口，不接live consumer。合成用中性lyc来源，覆盖true/false/missing/invalid、发现/网络活动语义、partial恢复与null/冲突、同版本/新版本/跨来源、无父主体更新以及未确认身份保持hold。只使用既有3e库、明确profile及只读native SELECT；去除同湖版本物理重复，不扫描其他客户库、不重投Kafka。真实逐项判定、统计、身份、摘要及覆盖保留21的700目录/600文件，报告保存后原地读回核验，只输出固定执行/验证状态。无独立业务真值时不报分类准确率。

证据目录`docs/operations/evidence/lake-alert-selection-4a-20261119-01/`。通过仅关闭4a限定步骤；4b接线、来源语义答复、主change结束审计和统一交付继续保留。

## 4a首批v1结果（历史，2026-11-19）

[限定交付回执](../../../docs/operations/evidence/lake-alert-selection-4a-20261119-01/README.md)：纯判定、显式profile及只读报告入口已实现，36项合成直接检查、Ruff和OpenSpec strict通过。3e既有湖批次完成原生只读判定、私有保存和原地读回；只回传执行/验证状态。生产者身份确认均保持false，实际覆盖/分布留21，不报准确率。正式表和服务未变，4a范围没有业务写入或模型调用。未答复的来源语义、4b/4c及主change整体任务均未核销。

## 4a当前v2结果（2026-11-19）

负责人身份答复已落实到v2示例及实际profile，旧v1只用于历史复核。64项定向检查、Ruff通过；02只读批次通过后，复核补了partial根ID冲突分组边界，独立03批次同库只读判定、私有保存及读回再次通过。两批回执和首批v1均保留。实际来源分布和判定未进入Codex/GPT；正式Fusion/HTTP镜像及启动时间、正式48列表保持。这是4a结束时点的证据；4b后续实现及读回见本页当前回执，不再等待ID和更新语义答复。
