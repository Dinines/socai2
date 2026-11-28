# 已有告警选择4a：只读profile

本目录提供可审阅的候选规则，不启用A/I写入或live consumer。实现与语义见[4a设计](../../../openspec/changes/complete-socai2-investigation-chain/lake-alert-selection-20261119.md)，当前直接证据见[v2回执](../../../docs/operations/evidence/lake-alert-selection-4a-20261119-03/README.md)。首批v1及修订中间批次保留原记录。

`selection.example.json`为v2：显式配置database、tenant/source/mapping、OCSF版本、`identity_scope=global`、`alert_lifecycle=immutable`、空的额外身份范围及只读查询上限。当前规则包含2003/2004发现类和4001网络活动；其他明确告警类别进入review，普通日志仍全部保留。类名单不是落湖过滤器。

4b接收验证补充显式`initial_activity_ids=[0,1,99]`：不可变来源在明确is_alert=true、身份与类型有效时，可首次接收Unknown/Create/Other，不改写原activity_id；Update/Close及失效状态仍待核。旧v2 profile缺该配置时沿原create_activity_ids，既有4a回执保持原配置与结论。接收及读取见[4b](../lake-alert-receive-4b/README.md)。

负责人已确认`metadata.uid`全局唯一、告警没有更新，因此当前各规则的`identity_path=metadata.uid`、`identity_semantics_confirmed=true`；该字段记录业务合同，不是权限开关。租户/来源只限定存取归属，不加入全局来源告警身份；产品、设备及finding_info.uid不参与该身份。同ID同正文为重发，同ID异文为合同冲突；同次扫描发现冲突时整组候选待核。发现更新/关闭或非活动状态进入review，网络Close仍按网络活动判定。缺metadata.uid不从partial、finding_info.uid或Kafka位置补造身份。

只读程序入口为 `docs/operations/inspect_lake_alert_candidates.py`，在已有Fusion Python环境中选择以下参数：

```text
--connection /controlled/connection.json
--policy /controlled/selection.json
--private-results /controlled/new-batch/results
--execution-status /controlled/new-batch/execution-status.json
```

connection沿3e原生ClickHouse配置，库名须与policy一致。输出目录须为新批次；报告保留在原环境，不将其中的分类计数、身份、摘要和决定详情上传到Codex/GPT。终端仅输出固定执行/验证状态。程序只使用native只读SELECT，不使用Kafka组或提交位点，不连接PG，不调用模型。

64项定向合成检查及3e同批原生库只读扫描/报告保存读回已经通过。报告表示规则执行结果，不是独立业务真值、实际全局唯一性证明、分类准确率或实际A/I交付证明。现网服务/表结构未改变，候选HTTP仍为3f的82操作、正式80操作。
