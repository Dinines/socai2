# W2 HTTP离线配合：真实来源路径与读取边界

2026-11-15。本步只核已有源码、OpenAPI及S01/S04实际HTTP回执，新增HTTP/业务操作均为0，不改服务或镜像。测试模块独占临时代理及实际GET，调查模块维护第11步及运行状态；此记录不是W2 TCP验收结果。

- [离线核对结果](result.json)：实际80操作、55 GET、无鉴权；来源文件摘要及文档差异。
- [少量真实路径](path-map.json)：两Case C1到原I输入的来源链，可选I到A01查询原件链，S04五个真实task及两Case原Run的保存字段。这里只提供已有回执定位；测试仍以原保存快照作独立对照。

## 最小跨Run读取

1. 读取整事件Case原C1：`/api/v1/socai2/cases/58194401-03ca-5383-83b4-ac82886a5acd/runs/d1b17106-0ee7-4265-ac84-beb9ebf048eb/artifacts/bf3a8ed9-eedf-4bae-8f50-ebbf51eeba53`。
2. 从`content_json.incidents["263a1c58-e9c6-4ba4-9204-3b0568970551"].diagnosis_scope`取得实际`source_run_id`、`input_artifact_id`、`source_fingerprint`。这里保存的是来源身份，没有内嵌URL。
3. GET `/api/v1/socai2/analysis-runs/b5410c29-8134-544d-94e0-f8d59ee82958/artifacts`，按`items[].id=1b43bb64-f8cb-473f-b57c-21e0995bec7b`匹配，并跟随该行返回的`content_url`；若分页，以返回游标继续。
4. 实际返回链接属于原I的`/incidents/{id}/analysis/runs/{source_run_id}/artifacts/{id}`，不能改成Case路径。原件`metadata.sha256`及目录摘要均与C1冻结`source_fingerprint`相同。Case原件的元数据键为`artifact`，A/I为`metadata`，代理原样保留。

单告警Case原C1也指向同一I原件：原I分析3条，本案交集仅A01的1条，保持`diagnosis_scope_extends_beyond_case`。可选第二级来源取I输入`triage_queries[A01][0]`的真实Run/工件身份，再沿A Run目录返回链接读取；无需为证明第一级来源额外扩大测试。

## 合同和边界

保存的实际服务OpenAPI与当前Swagger具有相同80个方法/路径和全部Schema；实际55 GET与原候选GET定义完全一致。Swagger额外整理80项tags、80项部署状态、9处示例及1处POST描述，字节摘要不同，不是字段或执行合同变化。代理继续使用测试已冻结的实际服务OpenAPI，不替换该文件或摘要。

本批8份实际步骤目录中没有跨Run的`artifact_refs`。上述真实业务来源链可以验收，但不能写成“步骤直接返回跨Run引用”已真实覆盖。S04没有Case R2；两Case原Run的`previous_run_url/comparison_result_url`仍为空，不能用上一轮比较冒充跨来源读取。

S04 A04任务completed，I新任务failed/model_response_not_complete，3条后续check为skipped/automatic_attempts_stopped且无attempt/Run。旧I结果指针保留，当前为stale/valid_for_current_input=false；两Case原结果可读但当前新鲜度stale。冻结旧I输入中的3条范围和当时覆盖仍是历史事实，不等于已覆盖当前第4条。失败后没有新Case任务或Run。原模型质量NOT_PASSED、S04正向后轮未通过均保持。

本步未发现新增HTTP接口或字段缺口。以下补记测试实际结果，原离线result.json/path-map.json保持不变。W3/W4不在本步实施范围。

## 收到实际TCP结果后的离线复核

测试模块[本批34次GET](../test-http-proxy-w2-live-20261115-01/tcp-02/result.json)全部200：9次账本、24次业务代理、1次实际OpenAPI，107项直接断言通过。已读取整事件C1→原I目录→返回content_url→原输入，未追加可选A01链。S04失败/3条skip、两案原partial及首轮空比较保持。首次临时隧道回环目标误选失败原件保留，没有成功业务GET；修正为当前21地址后本批34次一次通过。临时代理/SSH已停止、端口关闭，0业务写/模型/测试直接SQL；业务GET仍经过服务正常数据库读取。

HTTP[离线复核记录](tcp-readback-review-01.json)核34份保存响应摘要、5个S04任务、两Case原Run/Result身份及partial/initial、当前stale、原I输入来源摘要和3条范围与原map一致。本次复核0新HTTP，不改服务、源码或合同。代理读取通过不改变S04正向后轮未通过、steps直接跨Run引用未覆盖及模型质量NOT_PASSED。
