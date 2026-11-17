# 当前功能版正式发布收尾

2026-11-16。正式aisoc的128/129增量、普通账号和HTTP双池验证已完成；正式HTTP18024、Swagger18080与4177正式上游已切换。新v2批次1告警/3上下文单次投递，A完成但单字、I在8192/length处失败；确认0在途后停止本批Fusion/调度，只读入口和新数据保留，Case未启动。当前不是整链验收成功，模型质量NOT_PASSED及第8–10步后置，不归档整个change。

用户允许核查重试后，[空白输出兼容核查](../model-output-compatibility-20261116-01/说明.txt)以实际43语法编译和一次同输入诊断确认生成约束问题：修正约束后1166/stop、原合同通过。本地提供端适配24项检查通过，尚未部署修正版；这不是业务I重跑。下一步处理嵌套后台信息排除，再冻结必要修正/复审和发布读回。以下准备与冻结记录保留其原阶段，当前实际状态以[PROGRESS](../../../../PROGRESS.md)和revision-02回执为准。

负责人要求的三个模块均已确认已验功能可纳入发布：[HTTP后端](module-http-confirmation.md)、[测试](module-test-confirmation.md)、[调查执行](module-investigation-confirmation.md)。最终独审见[independent-audit](independent-audit-01.md)，按其实际最后结论办理。

## 准备及发现

- `source-comparison-01.json`：初始735处理文件/723 HTTP来源与已验候选只差policy。既有S01/Case首轮、S04预算续验、F1–F5、W4/W5复用；初始处理r1和HTTP r1已构建，无正式服务切换。
- `connection-probe-02.json`：新普通processor/ingress实际连通正式aisoc（TLS1.3）、Redis DB8/9和湖aisoc；业务行保持0。新任务表和public支撑表授权仍待增量，不能由连接成功推断可写。
- `session-rls-before-01.json`：正式sessions要求实际tenant上下文，原实现缺失；临时GRANT和失败写入在同事务完全回滚。修正后`session-tests-01.txt`为19通过，`session-rls-after-01.json`用真实方法/普通角色证明父子保存、按tenant关闭、厂商会话保持；最终0行0授权提交。`session-lint-comparison.json`记录5项原有lint问题无新增，不冒称全lint通过。
- `viewer-preparation-01.json`与HTTP模块补核：第一版选错旧71操作Swagger，缺12项/多3项退役接口、E37旧同步200。第一版目录/镜像未上线且保持原样；不能只改版本号或放宽断言通过。
- 第一轮包探针字段名、连接探针嵌套引号的脚本错误均保留01回执；修正后的02通过，无业务源码/数据库写入由探针错误引起。

## 第二版冻结目标

[显式profile](../../../../deploy/aisoc21/streaming-release-20261116-02/release.json)，21新目录`/opt/sting-aisoc-socai2/deployments/streaming-release-20261116-02`。`revision-02/`保存上传、manifest、构建及配置验证；processing-20261116-r2包含唯一新增业务修正SessionStore，HTTP业务源码/预算保持。Swagger来自[已核80操作正式副本](../../../../deploy/api-docs/streaming-release-20261116-02/handoff/openapi.json)，其参数、请求、响应Schema、55 GET、三类及无鉴权经`verify-swagger.py`直接验证。

正式使用aisoc/已有正式tenant与actor；I4小时、Case6小时、活动7天、poll60秒、N1。A/I/Deep8192、C3/C616384、服务窗口65536。4177 r5按同正式18024/tenant/环境与runtime合同摘要准备后已完成切换。原r1准备和旧业务容器、清理备份保留，不恢复旧消费者或旧数据。

上述发布准备已推进到实际新批最小读回。正式1+3发送入口独立冻结，ACK及湖原文核对已保存；真实A/I共2次生成，另有1次独立兼容诊断，当前仍无Case调用。实际模型视图嵌套来源字段尚未完全排除，不宣称已全面满足模型透明要求。本轮没有Git提交或推送。
