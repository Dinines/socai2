# W2只读代理组件及真实候选TCP回执

2026-11-15。依据[W2当前子步](../../../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#7-w2当前子步单环境只读代理)，已实现单环境只读代理并完成组件与真实TCP空态/错误检查。**W2部分完成**：非空A/I/Case、实际任务/Run/跨Run原件仍待S01；W3页面、W4部署包和21测试服务发布未实施。

## 实现和输入

- 当前独立组件版本`0.2.0`。保留W1账本9字段配置，新增`serve --upstream-config`及10字段显式代理配置，配置及运行命令见[部署入口](../../../../deploy/investigation-test/README.md#w2显式只读代理配置)。未提供代理配置时只运行账本。
- [实际OpenAPI读取回执](contract-read-01.json)与[live原件](live-openapi.json)来自21候选18424，路径和components与HTTP交付包一致；允许55个业务GET，涵盖统一Run目录。摘要为`9bce09317ad13c411f2a299e4fbf34c89f41e2a48eb58020d8e5900fa5a67b83`。旧71操作/44GET包及部署前文案快照均未用作本次代理合同。
- 只允许当前GET路径和查询参数，不自动重试或跟随重定向，不接受调用方URL/SQL或转发其凭据/租户头。业务正文/状态及分页游标保持，原件逐块传输不套用账本证据大小限制；来源环境及合同摘要独立返回。代理错误明确502/504，不包装成空列表。

## 直接验证

[组件检查](component-01.json)共24项通过：W1既有16项和W2新增8项。W2明确使用`httpx.MockTransport`受控上游，覆盖无启动请求、实际合同GET数、分页/错误/参数保真、2,400,000字节原件完整传输和关闭、只读/禁止任意目标、连接失败/超时/重定向不重试、环境及合同不回退。首次组件执行曾出现capabilities严格UUID类型错误（1失败/23通过），已修正为返回UUID对象后完整复验；未涉及真实业务失败或改写历史结果。

[真实TCP结果](tcp-01/result.json)通过：临时本机代理`127.0.0.1:58333`→本次SSH转发`127.0.0.1:58334`→21候选`192.168.1.21:18424`。8项带断言代理GET为A/I/Case/统一Run目录四个空列表200、三项真实不存在主体/Run返回404，以及非法limit返回422；另将两项错误与直接上游逐字节/状态比较一致。启动探测只读取capabilities及实际OpenAPI，合同摘要相同。

本次真实请求都为GET，没有业务提交、Kafka发送或模型调用。服务启动/读取未创建账本目录，账本前后保持；`result.json`记录两个临时进程均已停止。未改21容器，未恢复旧服务。仅本机临时代理处理此批请求，不能声称测试服务已部署到21。

## 来源和剩余边界

组件中的分页及大原件是合成字节/模拟HTTP，不算真实跨Run读取。TCP为空候选的真实读请求，没有制造对象ID作为已存在主体；不存在对象使用明确无对应记录的UUID验证404，实际业务映射仍由后续S01真实响应提供。没有成功建案、A/I/Case结果或非空全分页验收。

`capabilities.investigation_http.runtime_verified=false`表示启动元数据不自动认证上游验收，实际读取结论以本回执为准。tenant是已供给的候选绑定身份，代理不提供租户切换；后续页面须核批次environment与代理标签一致，archive样本不自动转为live。

私密运行profile在`.local/test-http-proxy-w2-20261115-01/`，未登记为公开证据。公开[源码/配置摘要](sources-01.json)、[Ruff](ruff-01.json)、[OpenSpec及链接检查](docs-01.json)供复核。下一步由调查供给隔离Fusion/Kafka/Redis/上下文，S01正常来源→Kafka→A/I后接同批HTTP建案，再补W2非空/跨Run，W3和W4分别推进。
