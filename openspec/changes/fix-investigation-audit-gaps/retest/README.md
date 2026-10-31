# r3定向真实复验：已结束

固定最多5请求的批次已执行，3主Run中LSASS完成/partial，Office和网络因纠错预算失败；两追加按前提规则未发送。原临时Key已禁用并验证401、明文删除。完整[共享回执](../../../../docs/operations/investigation-audit-live-r3-20261031.json)和原请求/响应保持；禁止重复本批POST或换key补跑。

随后用户明确要求长期全权限开发Key，已独立创建并保存在21私有文件；见[开发凭据回执](../../../../docs/operations/evidence/investigation-audit-fixes-20261031/live-r3/dev-credentials/receipt.json)。这不改变本批固定请求、原失败或次数。新纠错修复仅本地验证，后续功能复验须使用新的具体范围。

以下为当时执行方案，身份限制已由[临时Key授权](credential-authorization.json)覆盖；历史“待执行”不代表当前状态。

## 更新前与执行顺序

1. 完成结束独审；核本地提交与source-manifest、候选包SHA相符。用户批准本次调查API更新及下面5个Run后才能执行。
2. 只读核21的调查/core/agents实际容器ID、镜像ID、启动时间、绑定端口；记录环境文件权限和配置是否保持，只比较hash/布尔值，不输出配置值。真实服务若偏离旧r1回执，先解释差异，不直接覆盖。
3. 已有调查环境文件保留。候选目录为`/opt/sting-aisoc-socai2/investigation-v2/20261031-r3`；核候选包SHA和全部文件。安装命令使用`python deploy/aisoc21/install_investigation_api.py --execute --upgrade-from <刚核实的完整镜像ID>`。仅替换调查API，原core/agents及worker不变；没有迁移或权限动作。
4. 读取livez/OpenAPI、核源码hash及鉴权拒绝，然后用对应身份读取两个租户的三个已有Case及选定Alert。核成员归属、原窗口和输入未意外变化；不新增/关联Case，不重新摄取。
5. 按plan.json的order逐个发出POST。调用脚本沿用`scripts/investigation_client.py`，凭据只用既有AISOC_API_TOKEN环境值，body使用本目录固定文件。每步保存原请求、状态、完整响应、hash、时间；发出后不自动重试。网络follow-up的前提是本批main有完成结果和可复用的同参数网络E，否则停止该追加并记录未覆盖。
6. 每Run读取result/report/steps和实际引用的evidence，比较HTTP返回与保存内容；追加后读原主报告确认未改。只沿已有相对URL，不作新查询或刷新概况。若POST回包未知，按plan中的readback_path显式GET查结果，不能换key再发。
7. 只做一次限定真实批次；结构通过与人工语义审阅分别记录。任一Run失败保留原件、原因与用量，不为凑通过重复启动。最后核core/agents未重启、调用数/账本、凭据未写入公开证据；两个change链接同一回执，各自按实际目标判断。

旧`tools/testdata/investigation_http_cases.py`会建Case、关联成员、刷新概况，超出这次定向范围，**不直接用于本批执行**。本目录不另建运行框架；5份冻结body配合现有单次客户端即可。

## 判据

| 场景 | 必须核实 | 不得冒称 |
| --- | --- | --- |
| Office main＋followup | description/PID/raw/approval来源进入冻结与实际模型请求；前报告完整；新追加在原限额内形成可读结论，若发生纠错则检查其原请求/回包 | 离线16929/17018不是真实token或真实新报告通过证明；没有发生纠错不能说真实纠错已验 |
| 网络 main＋followup | main实际网络Tool产生适用查询；追加原生调用、同参数及reused_from对应本批main；查询数/调用数分别记录 | 缺新材料版本的r1 E不得冒充新缓存；模型文字说已查不是调用 |
| LSASS main | success_empty与unavailable区分；A/T/成员UUID/主机正确；旧摘要、冻结、模型三种省略各按来源解释 | HTTP200/结构合法不代表业务语义正确、攻击成功或已授权 |

上限共5 Run、最多20模型/20工具尝试；每Run仍24000预算、单次输出3000、执行120秒。普通GET和core来源读取不增加模型调用。无F2刷新、厂商新动作、自动入口或F5测试。

## 回退

若需要回退，仅切回更新前已核的调查镜像和匹配Compose；保留新旧Run、工件和所有失败回执。不删除账本、不重置operation_key、不自动补跑。旧版本可能不理解新材料，恢复旧服务不表示新语义仍已生效。
