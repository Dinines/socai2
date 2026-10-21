# 3A-10-03-01：分诊请求界限与开始游标

状态：本小批已限定验收，实际结果见[回执](3a-triage-request.md)；下述为执行范围，操作前原件另存受控scope-plan-before.md。批次 `3a-triage-request-20261020`。承接[可靠性总计划](3a-worker-reliability-plan.md)与[重投保护回执](3a-triage-recovery.md)。用户继续推进本计划；本批不扩大常驻worker或质量准入。

生产只读重现：`make_chat_model("triage", max_tokens=512, json_output=True)`的模型max_retries/request_timeout均None，底层async client为retry2、timeout None。网关retry0/45秒不约束SDK自动重发。上批真实start-only Run的next_seq=-1而since=-1返回422。

本批仅修改三份运行文件：factory为triage角色显式默认SDK retry0、timeout45秒；auto_triage_agent为safe_ainvoke增加45秒整次调用截止时间（保留512输出上限、原prompt、异常回退及调用账本）；API investigations的since下界改为-1，使原开始事件的cursor可直接往后读取。其他角色/原始HTTP/stream入口不外推；显式factory参数仍可覆盖默认值，当前生产auto-triage没有此覆盖。外层截止是客户端停止等待，不证明服务端中止或usage为零，取消不自动重发。保留普通Kafka claim/unknown合同。

先以原实现跑新增回归，固定失败，再做修改。沿用固定生产依赖及缓存test镜像，实际ChatOpenAI SDK+httpx替身验证500单请求、超时/取消不重试、成功usage、BYOK和底层配置；通过真实agent方法验证整次超时后原回退及外部取消不吞。API以有效上游timeline fixture验证-1、分页、不重叠、权限及原非负边界。保留直接相关原测试，不默认全仓回归。

真实环境仅只读查询既有Run，通过新三枚短期操作key验证HTTP身份/tenant/scope及cursor；不新建告警、Run、事件或模型成本，不发布broker消息、不重放原输入。先保存14表旧材料hash、36容器/18卷/134迁移、十枚reader与网关计数。仅构建/更新API和Agents两个最小顶层，保留旧镜像、全部env/挂载和关闭开关，真实HTTP及常驻SDK配置通过后各单服务重启回查。操作key最后停用；读者key和旧证据保持。未知停止前先回查检查点，不盲重复部署。

本批不实现单tenant持久调用/tokens额度、跨进程并发/积压、完整停机恢复或worker准入，继续列为3A-10-03-02；生产SDK有限制不等于有持久预算。真实模型0次，费用unknown。回退撤本批Compose顶层恢复原镜像，保留全部账本和消息；常驻worker继续关闭，回退后-1 cursor可能再次422。
