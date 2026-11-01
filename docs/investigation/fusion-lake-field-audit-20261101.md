# 第2段：Fusion收到事件后的入湖与调查对应

2026-11-01。**本地实现核对完成，新增6项内部问题记录；尚未修复／线上验收。** 范围遵循[主记录](field-alignment-confirmations-20261101.md)：只核Fusion已经收到的数据如何转换、保存、关联和查询。输入缺字段、错误编号、错误类别或原始日志未提供，仅标输入限制，不追查、不修复、不要求补采。

本轮没有修改业务源码、启动服务、执行新Run／模型或远端业务查询。完成13项本地行为观察，其中使用真实本地ClickHouse驱动的列绑定函数，并复核已有r13四次真实查询证据。详见[观察脚本](../operations/evidence/fusion-field-stage2-20261101/probe.py)及[结果／源码指纹](../operations/evidence/fusion-field-stage2-20261101/observations.json)。观察成立包括复现错误，不能称13项需求验收通过。

## 各入口能提供什么

| 路径 | 代码事实 | 对调查的含义 |
| --- | --- | --- |
| 规范化事件topic | consumer先调用LakeWriter，再检测／提升；未提升事件仍有写湖路径 | 不要求必须先产生告警才能查询日志；但write_event成功只代表缓冲，不能当已持久化 |
| 已有告警topic／同步`/process` | 写PG告警，不调用LakeWriter；输入告警id还可能作为来源引用追加 | source_event_ids不是自动补采指令，也不保证其中每项是湖event_id。没有单独事件输入时，不将“未自动把告警造为日志”列作待修 |
| 窗口／序列检测 | 各收到事件可先入湖；DetectionHit只带规则信息，生成告警只附当前触发事件 | 湖可能有其他参与事件，但告警未持久保存完整参与关系；沿用S1-06，不凭同主机近时间认定全部都是来源成员 |
| Case查询 | 固定租户、Case成员主机及请求起止窗口；进程限定1007且process_name非空，网络限定4001 | 在当前工具定义内查询；不能为得到非空结果改查登录3002或扩大主机／时间范围 |

来源：[consumer.py:361](../../services/fusion/app/workers/consumer.py)、[LakeWriter](../../services/fusion/app/services/lake_writer.py)、[窗口检测](../../services/fusion/app/services/windowed_detection.py)、[CaseTools](../../services/api/app/investigation_v2/case_analysis_tools.py)。

## 逐字段对应

| 字段／能力 | Fusion告警侧 | 湖侧及调查消费 | 结论 |
| --- | --- | --- | --- |
| 租户 | schema和RawAlert选择信封tenant_id，必要时取OCSF tenant_uid，解析UUID | LakeWriter采用相同优先级，Case SQL含tenant_id参数 | 已有一致路径；未扩展权限专项 |
| 事件引用 | schema优先event_id，其次id，再metadata.uid；引用保留原字符串 | LakeWriter优先id，其次event_id，仅接受UUID并规范化；不读metadata.uid。source_alignment逐字符串精确比较 | **内部规则不一致**；见S2-01、02 |
| 发生时间 | 提升读取OCSF.time；两类检测漏传的问题已记S1-01 | 湖将有效ISO带时区时间转UTC；Tool将请求窗口转UTC，左闭右开 | 有效时间转换路径已核；不重复登记S1-01。输入缺／错时间不向上追查；内部默认时刻冒充发生时间仍按S1-01处理 |
| 主机 | 提升／单事件检测读device.name；窗口检测读flat主机；Case只收已存host实体／affected_hosts | 湖src_hostname取device.name或src_endpoint.hostname；SQL精确匹配src_hostname | 同为device.name时能对齐；仅src_endpoint.hostname有值时湖能保留、告警可能无host；沿用S1-05。域名别名、大小写及源／目的主机不自动等价 |
| 事件类别 | 告警保留ocsf_class_uid，但这不是每条补查日志的类别 | 湖保留class_uid；Tool分别查1007／4001，进程结果另含activity_id/action/outcome | 合同范围正确；原有类别未知、错误或没有所需日志不列本轮上游修复 |
| 进程／账号／路径 | raw保留输入，结构化投影因入口不同 | 湖取process.name、actor.user.name、file.path；进程Tool返回这些列及hash | 对支持路径已核保存／查询；当前工具不返回PID、命令行或父子链，不把“有进程记录”写成已证明父子关系。工具扩展必要性留第5段 |
| 网络 | src_ip/dst_ip等按入口提取 | 湖取端点IP／端口及protocol；网络Tool返回源／目的IP、目标端口、协议、相关进程 | 基础路径可用；IP空值哨兵`::`不是已知地址，端口443不证明HTTPS；不得从缺字段补事实 |
| 活动、结果、会话 | SessionStore读取顶层activity；consumer也向顶层activity.session写id | LakeWriter只从ocsf_event.activity取action、outcome及session等；Case进程Tool直接消费action/outcome列 | **两个内部消费者读取位置不同**；已收到字段仍可能变空，见S2-03 |
| 文件hash | 首个fingerprint作为普通hash保存 | 湖不看算法就把首个fingerprint放hash_sha256，Tool沿此列名返回 | **字段意义可能被改变**，见S2-04 |
| raw | 形成告警时可能在PG保留OCSF；未提升日志没有该告警副本 | 湖raw_payload裁65536字符、ocsf_json裁262144字符，无截断字段；两种Tool不读raw | 湖正文并非总是完整原件；见S2-05。不假定其他存储也没有副本 |
| 查询上限／重复 | source引用按告警保存，首份材料冻结 | Tool按时间／ID排序，抓limit+1、返回最多limit（默认20／最多50），无事件去重 | 重投产生的重复物理行可能占满限额；见S2-06 |
| 来源对应 | 一个事件可被多条规则使用，对应多个告警 | source_alignment仅按返回event_id与各告警引用做对应；同主机近时间不算来源匹配 | 原则正确；ID映射先修。未匹配不等于事件与告警无关，也不证明没有告警 |
| 空结果／不可用 | 告警本身与湖数据各自成立 | available=true且rows=[]为成功空查询；失败为available=false；模型空结果标coverage/absence_reason unknown | 已有区分，不把空查询自动归因于输入、采样或数据丢失；当前报告语义问题仍在r13记录中 |

## 内部问题、影响与最小处理方向

| 编号 | 已核事实／触发条件 | 功能影响 | 最小处理方向 |
| --- | --- | --- | --- |
| S2-01 引用选择及UUID表示不一致 | 同一合法输入同时有不同的id与event_id：schema选后者，lake选前者。仅UUID大小写不同也会因湖规范化、告警引用未规范化而比较失败 | 已存在的真实对应被显示成未匹配，影响逐行证据来源和报告引用 | 在Fusion内部统一来源ID选择及有效UUID表示；保留原始值供追溯；调查比较沿同一合同。不能拿同主机／同时间替代ID对应 |
| S2-02 已有metadata.uid未映射，列绑定失败丢批 | schema接受并采用有效metadata.uid；lake不读取而置event_id=None。flush从字典删该键，但INSERT仍明确包含event_id。本地clickhouse-driver 0.2.11实际RowOrientedBlock抛KeyError；批次已从buffer移除，错误被吞，write_event仍返回True | 一个被接受的输入可导致同批其他正常事件也未入湖；告警处理可以继续而补查缺数据。laked计数及缓冲成功不能证明写入成功 | 与S2-01共用ID转换修正，保持INSERT列与行一致；向调用方区分缓冲与持久化结果，避免失败被当成功。仅围绕此正常输入触发缺陷做直接验证，不扩通用恢复框架 |
| S2-03 活动／会话读取位置不同 | 顶层activity的会话被SessionStore识别，但湖action/outcome/session_id为空；放进OCSF则湖有值、SessionStore识别不到。consumer顶层回填也不自动同步OCSF | 已收到的执行动作／结果可能在Tool中消失；会话关系跨PG／湖不一致 | 在内部统一读取与回填同一活动对象；两种已有形态明确选择，冲突不静默混配；不要求上游新增字段 |
| S2-04 首个hash被误称SHA256 | 合成输入明确给MD5在前、SHA256在后，湖hash_sha256得到前面的32字符值；完整原值仍在raw | 错误hash算法标签进入查询／调查，按SHA256检索可能漏命中或作错误归属 | 按输入明确算法选SHA256，验证值形态；未知留空，其他算法保原值。不要仅取首项或重新命名为SHA256 |
| S2-05 raw裁剪未告知 | 已收到的长raw同时超出两个字符上限后，raw_payload和ocsf_json均被裁；后者可能不是合法JSON，没有原长／截断标记。dict raw_data另被str转成Python表示，短值尚可从ocsf_json恢复 | 无告警副本时湖内正文不完整；分析人员／后续工具无法区分来源本就没有与内部裁掉；解析ocsf_json可能失败 | 明确保留合法JSON结构和截断状态；需要原文时采用现有可用原件路径，不冒称截断副本完整。仅记录到达Fusion之后的损失，不要求补采 |
| S2-06 查询未去除重投副本 | writer按收到的事件追加；仓库新表为ReplacingMergeTree，合并前仍可重复，旧表引擎本轮未核。Case SQL没有FINAL／按ID去重，替身返回两个同ID行时限额和truncated直接按物理行计算 | 同一事件可能重复作为证据，占用查询名额，排挤其他不同事件；统计不能自动等同独立活动次数 | 在证据查询按既有事件身份处理重投副本后再限额，保留不同事件；不宣称所有相似行都是重复。无需扩展新的事件处理框架 |

S2-01与02共享一处来源ID修正方向，不拆成两套机制。主机漏取、检测告警时间和窗口来源清单沿用S1-05／01／06，不重复计为新增缺陷。上述是当前实现可触发的行为，尚未证明线上发生过同类丢批或重复。

依据：[事件身份解析](../../services/fusion/app/services/event_schema.py)、[湖映射／flush](../../services/fusion/app/services/lake_writer.py)、[会话读取](../../services/fusion/app/services/sessions.py)、[消费者回填及提交顺序](../../services/fusion/app/workers/consumer.py)、[湖表定义](../../services/api/clickhouse/001_init.sql)、[Tool查询及来源对应](../../services/api/app/investigation_v2/case_analysis_tools.py)。

## 本轮验证和已有证据

- 13项不同本地行为观察已完成：有效字段／UTC／精确匹配，双ID优先级、UUID大小写、metadata.uid、活动两种位置、hash算法、长raw、dict raw、实际本地驱动列绑定、Tool实际生成SQL及重复行限额、历史证据复核。首次结果[原件](../operations/evidence/fusion-field-stage2-20261101/observations-initial.json)保留；随后发现会话夹具key_kind写成vendor，虽然块读取仍可复现，但不满足SessionStore后续枚举要求。改为vendor_session并只复核两项活动位置，11项未变观察复用；见[定向复核](../operations/evidence/fusion-field-stage2-20261101/activity-followup.json)。未执行会话DB upsert，不宣称真实会话入库已验；没有执行全量测试或重跑第1段。
- 驱动验证使用本机0.2.11的真实列绑定函数；替代连接对象只做本地绑定，不连接ClickHouse、不人为制造数据库故障。两行批次因缺event_id报错，rows_written=0、buffered=0、两个write_event均返回True。这个结果证明本地源码与驱动组合的问题，不冒称生产丢了两条日志。
- Tool核对调用真实CaseTools.execute并替换底层查询返回，验证实际SQL、参数、DTO；没有用内存模拟器冒充ClickHouse筛选语义。租户、主机、1007／4001类别和UTC起止条件保留。
- 已保存r13证据复核：A的进程／网络查询各1行，分别精确对应A1／A2；B两次均成功0行；4次QueryFinish均exception_code=0，返回数量一致。**A为专用手工fixture，证明查询与来源对应，不证明由Fusion写入；B的空结果不证明本段缺陷曾发生。** 详见[原批次](../operations/evidence/investigation-r13-20261101/review.md)。
- [原来源边界核查](source-boundaries-20261101.md)曾确认旧Office湖记录为3002登录，不能作为1007进程／4001网络证据。缺少所需输入日志按用户要求排除上游修复；原有类别过滤不能为了出结果放宽。
- 本轮没有连接21复核当前Fusion镜像、驱动、表引擎或配置；只读使用现有本地证据。线上触发情况仍未验。r13不重试，5.3仍未完成。

下一为第3段：核事件成员、归并依据、逐告警—对象关系、库存资产／标签、Case成员及旧Run范围。沿用本段已发现的来源与会话断点，继续区分已保存但没读出、内部关系没保留和输入未提供。
