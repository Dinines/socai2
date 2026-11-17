# F5：统一现行执行合同

2026-11-15。实现、直接检查、测试会话新PG/Redis批次及同批90次HTTP读取通过。第7步五项修复已完成本机程序联验；第11步真实Kafka整链、结束审计及正式交付尚未完成，未部署、提交或推送。

统一工厂在构造handler前要求当前alert_io、incident_io、case_io及选定政策指纹；启用调度时缺A/I/Case任一handler即拒绝。模型额度、并发和时限仍按配置，不以8192等数值判版本。A/I入口在新建Run和外部调用前核本环节合同，C1固定当前Case输入身份；完整Case、C3、Deep和C6拒绝旧冻结输入。当前A/I及C3/Deep/C6不再因缺profile切换旧模型输入或解析。历史政策、原件及只读解析保持，内部共用的事实提取/输出存储不是第二套活动版本。

修改文件与配置见[冻结摘要](source-hashes.json)，包含16个核心文件及10个相关测试/驱动/配置/发布文件。发布片段已包含这些核心变化；唯一目标运行配置仍是A/I/Case联合工厂，知识维护后置，不要求注册未实现handler。无新DDL，告警公共字段及HTTP合同不改。

## 直接检查

- [28项配置/执行入口检查](direct-tests-final.txt)：其中新增15项覆盖三类缺合同、旧嵌套合同、缺handler、选定政策指纹不符、缺合同执行前无数据库/模型调用、旧冻结Case/Deep/C6输入拒绝、历史政策仍可读取。正向把C3预算设为4096仍能构造完整工厂，证明额度不是版本门槛。
- [84项现行模型合同检查](model-contract-tests.txt)：复用A、I、C3、Deep/C6和C3输出合同测试；原已明确后置的历史重复展示测试1项deselected，不改称已修复。
- Ruff与OpenSpec strict通过；HTTP侧[6项边界检查](http-boundary-tests-01.txt)及[候选检查](http-candidate-check-01.json)确认80操作与第7步快照一致、无鉴权、Case/I异步202、E11/E13/E36退役，内部路由未混入。检查器最初未处理发布片段既有requires字符串形式的错误保留，修的是检查脚本，未另改产品合同。

## 独立测试的实际执行

测试会话以新tenant实际执行[validate_contract.py](validate_contract.py)，使用本机磁盘隔离PG `127.0.0.1:28413/v12_upgrade_dev`、Redis与独立namespace，Case容量沿默认100。输入直接构造；模型Gateway返回固定结构化回复，查询Lake返回合成记录。它们只验证程序执行、保存和读取，不是模型推理质量或真实来源的验收。

[test-pg-01](test-pg-01/result.json)四组检查通过：当前联合工厂及注册，A→I→Case保存，Case C3→补查→Deep→C6执行与结果读回，C1内当前A/I来源与profile冻结。共1 Case、3 task/attempt/Run（全部completed）、1 Case Result，5份模型替身回复、0真实模型。测试会话[包装回执](../test-f5-independent-20261115-01/pg-contract-01.json)记录30份源码/配置/驱动前后hash及4份私密配置指纹，前后保持；凭据不写入证据。

[实际快照](test-pg-01/snapshot.json)、[Case输入](test-pg-01/case-context.json)、[Case步骤模型请求/回复](test-pg-01/calls.json)、[事件请求/回复](test-pg-01/incident-calls.json)、[Run读取](test-pg-01/case-run-readback.json)与[Result读取](test-pg-01/case-result-readback.json)保留。新批不恢复或重派F1–F4旧失败/unknown。最终Kafka→真实消费/归并/事件及上下文路由→真实A/I→Case→独立TCP/4177仍另行验收。

## HTTP同源读取与保存快照查阅

[HTTP同批回执](http-read-01.json)90次无鉴权GET通过：3个完成任务及Run、25步骤、69工件和A/I/Case原结果均可读；A/I/C3/Deep/C6合同与选定profile、冻结C1一致，原A/I来源和补查的一行合成记录保持。19张相关表读取前后摘要一致；本次为ASGI与真实隔离PG只读验证，0新增执行、模型调用或业务写入，不代替21的真实TCP验收。

F1–F5已保存的13份Case快照通过项目既有`update_processing_audit.py`导入仓库查阅页；[导入核对](audit-export-receipt.json)确认原25张卡片及70个历史详情文件保持，当前共38张卡片，新增链接可读。首次核对脚本误按记录ID猜文件名的错误保留，改为核实际内容摘要链接；没有重新执行旧任务。实际4177仍未切换，本项只更新仓库内可发布的已保存快照。
