# 3A-01：规则抑制持久回执

2026-10-20，批次`3a-suppression-20261020`。**本批限定验收通过**：规则抑制不再只有临时摘要，已有账本记录和经认证API回查已接通；真实Kafka验证了持久完成后才提交offset。常驻worker仍关闭，完整3A、真实模型分诊及调查质量未验。

## 输入 → 持久产品 → 回查

两个独立测试tenant接收同名主机/账号的合成告警，经真实认证ingress→Kafka→Fusion→PG保存两行；仅A由规则API保存`authorized-maintenance`抑制规则。旧Agents镜像直接调用生产方法返回suppressed，但该tenant的ledger为0行，复现缺口。

新版本经生产applier读取实际PG规则指纹，生产worker/sink在同一事务中写既有`investigation_runs`与`investigation_events`：

- 事件为`policy_decision`，payload为`policy-suppression-v1`，保存tenant、告警ID、输入SHA256、实际规则来源/指纹/加载状态、命中规则、shadow和无模型/无响应标记。
- Run使用`policy:business_context:suppression-v1`标识。completed表示规则处理完成，不能当作模型已调查或告警已解决；无verdict、无outcome prior、无审批或动作，也不改原告警状态/分数/严重度。
- 唯一键由tenant UUID、告警UUID、租户/文件规则revision、命中规则集合和shadow模式生成。相同键重复/8次并发返回首份冻结记录；同键输入变更拒绝覆盖。新revision/模式可产生独立记录，不是每条告警终身只能有一个决策。
- 在事务内设置RLS，先核告警属于该tenant；数据库缺失、写入失败、未知告警或冲突均抛持久化错误。运行时不回退到默认tenant。

现有认证API`GET /api/v1/investigations/{run_id}`及`/events`实际返回记录，B查询A为404、缺scope403、匿名401。A取消/更改规则及全面分诊重做语义仍须后续验证，本批没有把不同政策下的历史记录覆盖成最新值。

## 真实故障与broker提交

| 输入/故障 | 实际路径 | 最终结果 |
| --- | --- | --- |
| 同输入重复/并发 | 生产worker→PG相同键 | 首份live Run/事件各1，首次规则来源冻结；无模型调用 |
| PG写入故障 | 独立探针连接代理在run插入后、event插入前执行真实`SELECT 1/0` | 事务回滚，无半条Run；恢复同一pool后可写。共享PG未停，探针使用的独立合成f-revision恢复记录保留为**probe-only**，不冒充实际采用规则 |
| B同实体但无抑制规则 | 实际applier/worker | 到达正常模型配置分支；探针在该边界显式停止，不调用模型，不宣称B分诊成功 |
| replay / live shadow | 原有writer接口 | replay只计数且无DB写；live shadow独立观察回执，不填模型agreement/autonomy表、不写原告警 |
| Kafka offset0 | 独立SSL测试topic/group→真实`worker.start()`→已有冻结回执 | 确认提交位置1 |
| offset1，探针同时使pool和DLQ producer不可用 | 生产重试→无持久结果→提交保护 | 订阅停止，提交位置仍1；恢复同group从offset1续读，无重新发送，随后提交2 |
| offset2，同键材料冲突 | 生产持久冲突→`send_and_wait` | 测试DLQ经broker确认保存1条，再提交3；已有规则记录不变 |

原DLQ的`send`只等待入队，发送失败也返回；外层handler异常被吞后仍可能提交。本批改为`send_and_wait`并传播失败，窗口内出现无持久结果时停止订阅，保留未提交位置。此处验证单分区和已建立提交位置的测试group；**新group默认latest、积压起点、多分区、rebalance及常驻进程健康/重启策略未验，不能直接打开自动worker。**

## 验证与部署

83项相关测试通过，其中11项新增边界；两处原测试只适配显式replay sink/确认式producer，之前项目policy-loader测试也显式使用replay sink，没有移除原断言。首轮56通过/1失败的无DB fixture记录保留。27项明确对应的HTTP验收检查包含失败请求、回查与停用检查，不计轮询中的中间404。

只更新并重启Agents，镜像`socai2-agents:suppression-3a-20261020`，ID`sha256:127036ae1776f95c0bfcf820a33e9d2c151795a4e696c935bca5f42f9754ffc4`；配置/挂载、142项锁依赖及全部运行源码hash已核，无新增依赖/DDL。重启后原3份回执经API可查，再次处理同输入返回首份记录。

旧36条告警材料、2个Run/36事件及1条规则集完整保留；新增2条告警、3个Run/事件（live、shadow、probe-only恢复记录）和1条测试规则集。其他35容器、18卷、134迁移保持；3key停用401。两个测试topic保留7天retention，3输入/1DLQ及group位置可追溯。旧模型网关13次成功计数不增，无真实厂商操作；费用unknown，账本数值0默认不表示一次免费的模型调用。

探针初次导入路径、HTTP方法/必填字段、最终events/items字段及Kafka配置假设失败均保留。前置guard曾拒绝不完整baseline；最终API读校验失败时3条新账本行已存在，使用complete只读取并核对现有行，不重新受理告警或重跑故障候选写入。失败及限制详见[机器回执](3a-policy-suppression.json)。

## 后续与恢复

下一项3A-02：在独立测试topic/group明确起始offset和恢复策略，恶意/有授权背景/材料不足三样例及模型失败分别核实际模型输入、verdict、usage、ledger；自动graph升级/响应继续关闭。2C事件/UEBA真实来源和Agents API工作负载凭据仍缺，不能把缺源当已核实安全；知识质量后续另验。

当前使用[十一层部署命令](../../deploy/aisoc21/README.md)。恢复时先停本项目输入/相关消费者，再撤suppression层回到policy版Agents；保留新账本/消息/卷。撤层会失去本批持久性保护，因此旧版自动worker仍须关闭，不重发unknown动作或改旧事实。

来源见[差异清单](../handoff/3a-suppression-source-manifest.json)。受控证据在工作站`.local/aisoc21/evidence/3a-suppression-20261020/`及21对应evidence目录，秘密只保存在private目录。
