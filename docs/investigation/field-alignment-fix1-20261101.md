# 字段对齐第1批：事件ID与湖列绑定修复

2026-11-01。用户要求先提交当前版本，再修改代码、同步文件并比对确认。已在当前分支保存基线提交 **`b400fd0`**（r13实现、验证记录及六段核对，共339文件）；未推送。随后仅实施[修复顺序](field-alignment-impact-and-repair-plan-20261101.md)第1批 **S2-01/02**，本地代码及必要验证完成，尚未部署/真实ClickHouse验收。其余批次仍待办，不称全部字段已对齐。

## 改动与功能结果

| 位置 | 修前 | 修后 |
| --- | --- | --- |
| Fusion事件ID读取 | schema选event_id优先，lake选id优先且不取metadata.uid | 共用`resolve_source_event_id`，顺序为event_id→id→OCSF metadata.uid；有效UUID统一表示，原始输入不改写 |
| 告警来源引用 | 大写/其他合法UUID写法与湖规范化后的字符串可能不匹配 | 新处理的source_event_ids规范化、按同一身份去重后追加；未知/非UUID编号保原值，不跳到另一个不同的UUID |
| 湖批次INSERT | event_id为空时仅删行中的键，SQL仍声明该列，真实驱动绑定KeyError可丢整批 | 有有效ID的行按完整列写；使用既有数据库默认ID的行，其SQL与行同时省略event_id。两组分别绑定，避免一条缺键影响正常行 |
| 写入回执和指标 | write_event在自动flush失败后仍True；laked按缓冲接受计数 | 自动flush失败返回False；未触发flush的True只代表接受缓冲。`laked`从当前writer.rows_written取得，另列缓冲/失败等指标 |
| 未提升日志 | 不论实际写湖状态，都称archived to lake，ID只读id | 使用同一来源ID；说明入湖独立并引导核写入指标，不声称已持久化 |
| Case来源对应 | 返回event_id与保存source_event_ids按字面比较 | 兼容历史有效UUID的大小写/其他合法表示；非UUID仍精确比较，不按同主机/时间猜匹配，不修改旧冻结材料或报告 |

主要代码：[事件身份](../../services/fusion/app/services/event_schema.py)、[湖写入](../../services/fusion/app/services/lake_writer.py)、[消费/指标](../../services/fusion/app/workers/consumer.py)、[指标接口](../../services/fusion/app/api/router.py)、[未提升日志](../../services/fusion/app/services/promoter.py)、[Case来源匹配](../../services/api/app/investigation_v2/case_analysis_tools.py)。

## 保留的语义与接口说明

- ID的字段优先级沿原schema合同，不为了得到UUID而绕过优先字段。例如event_id为厂商字符串、id为另一UUID时仍保留前者作为来源编号；不擅自断言二者同义。
- 没有可用UUID的湖行继续走数据库原有默认ID路径，只修正列声明与参数不一致；不新增上游校验、随机来源身份或补数要求。原有非UUID来源引用不能因此被称为已精确对应湖行。
- `write_event=True`：仍在缓冲，或本次触发的flush成功；**不作为每行持久化凭据**。`False`：未接受，或本次自动flush未全部成功。批次中已确认的组仍计入rows_written。
- `/metrics.metrics.laked`现在是本进程当前writer已确认INSERT成功的行数，空闲定时flush后也会实时反映。新增`lake_accepted`仅计write_event返回True的处理次数；`lake`对象包括rows_written、buffered、flush_failures、rows_dropped。
- `rows_dropped`指未得到成功确认而从本地缓冲放弃的行数，不能证明服务器没有存入任何行；没有新增自动重试或恢复框架。持续不可用仍沿原best-effort策略，未把此批改为可靠消息投递项目。
- 新代码只影响后续处理/匹配；旧告警身份、旧Run冻结原文、旧报告、租户/主机/时间窗口及查询列保持。完整hash/复制原件不由这次修复重算。

## 直接验证与提交前后比对

最新39个相关测试用例（含参数场景）通过：Fusion 37，API来源匹配2。首次Fusion为34通过、3失败，API2通过；失败的3个实际驱动绑定测试是在绑定成功后，对驱动原地转成列表的记录再作字典检查而失败。修正**测试记录保留方式**为将副本交给真实驱动后，仅定向重跑这3个通过，没有重跑未变的34+2。首轮和复核日志全部保留，不能说首次39全通过。

覆盖：三种ID入口/优先级/UUID表示；schema与lake一致且不修改输入；metadata.uid和正常行混合批次；默认ID与正常ID列绑定；原有缓冲/年龄/停止flush；flush失败返回及指标；事件经实际consumer到湖行与告警snapshot；非提升日志不误报；历史Case UUID兼容及非UUID精确匹配。DB/Kafka/Redis使用替身，ClickHouse仅调用本机0.2.11真实行绑定，不联网。

[前后比对脚本](../operations/evidence/fusion-field-fix1-20261101/compare_baseline.py)直接从基线提交读取原schema/lake_writer，与当前代码用相同合成输入对照，见[结果](../operations/evidence/fusion-field-fix1-20261101/before-after.json)：

| 对照场景 | 基线b400fd0 | 当前代码 |
| --- | --- | --- |
| event_id/id同时有不同UUID | 告警引用取event_id，湖取另一id | 二者都取event_id并规范化 |
| UUID大写 | 告警引用大写，湖小写 | 二者同一规范表示 |
| 只有有效metadata.uid | 告警有引用，湖event_id=None | 二者取同一有效UUID |
| metadata.uid事件+正常事件，两行入同批 | 实际驱动KeyError；rows_written=0，write_event两次True | 绑定2行成功；rows_written=2，无绑定错误 |

最后一项是**本地驱动绑定/计数比对，不是向真实ClickHouse插入了两行**。本轮没有启动调查、模型、湖业务查询、厂商动作或部署。旧r13批次不重跑，报告问题及OpenSpec 5.3保持未完成。

测试日志、源码指纹与对照范围见[本批回执](../operations/fusion-field-fix1-20261101.json)。Ruff的语法/未定义引用检查及git diff空白检查通过；只检查本批文件，不格式化整仓库。

## 同步和下一步

已同步字段主记录、六段修复顺序、湖审计的最新状态、README、审阅入口、PROGRESS与AGENTS。旧审计内容作为修前事实保留，通过顶部更新链接区分当前代码；旧观察/HTTP/模型原件不改写。

S2-01/02状态为“本地修复并直接验证；线上未验”。下一第2批处理已有身份被旧指纹忽略、归并键缺对象类型及实际归并依据等；第3—8批仍按原计划，用户16项业务决定继续有效。修复工作区与基线提交的差异可直接审阅，本轮未自动做第二次提交、推送或合并。
