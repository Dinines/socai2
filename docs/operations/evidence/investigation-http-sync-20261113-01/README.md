# 调查新版的独立 HTTP 同步

本批仅同步调查聊天已发布并独审通过的`v1.2-20261113-r1`到独立HTTP。目标版本`investigation-sync-20261113-r1`，本机加`-local`；Swagger docs19。已统一发布并完成两端正式读回，发布后独立审计PASS；[最终回执](delivery-summary.json)。

## 来源与边界

[核心交接](../fixed-investigation-release-20261113-01/handoff.md)及其发布后审计是来源。固定目录`.local/unified-release/v1.2-20261113-r1`；叠加29个修改源码、4个新核心源码、1个策略，共34文件。`source-diff.json`记录源摘要；`runtime-hashes.json`共667个运行源码/策略，排除不参与执行的README。独立HTTP的路径、DTO及内部直接调用边界不变；不改业务代码、不新增表/迁移、无业务写入或新模型调用、无Git提交推送。

本机继续v12_upgrade_dev，4个可选来源开关保留false；21继续aisoc，UEBA/知识开启、图谱/产品主机查询关闭。策略固定到独立运行包内，模型协议/schema使用已发布chat_completions/vllm_grammar_v1。21知识profile挂载改为同一已发布冻结目录，私密挂载保持。不把两端架构或连接混用。

## 直接检查

- `contract-check.json`：71操作、153运行Schema保持；`preview-loaded.json`：667摘要、策略加载及核心适配器接线通过。
- `local-before.json`和`preview-readback.json`：同一10批真实Run的Case/Result/Run/当前判断历史/任务/调查历史/管理及告警/E70/E71，共10业务GET；稳定响应摘要相同，仅排除查询observed_at。既有Result保留accepted/uncertain/partial，并非质量通过。
- `21-candidate-loaded.json`：一次性容器验证667摘要与策略/来源配置，成功后退出；没有绑定端口、访问数据库或调用模型。
- `aisoc21-before.json`：21现有Case/Result/判断和告警10业务GET；生产不新建调查。
- `docs-check.json`：71操作、162文档类型、764固定字段；27请求/637JSON响应/3CSV示例；125功能分组22/15/88。
- HTTP边界定向3项测试通过；OpenSpec严格校验通过。模型流程直接验收复用核心10批证据，本批不重新采样。

## 准备过程的失败记录

准备期误用系统Python导入缺pydantic_settings，改用项目conda环境。一次配置探针把环境来源开关当settings属性读取，未运行业务；随后按实际enabled函数及环境核对并明确保留原值。首次生产登录探针误传username，返回422；按既有LoginRequest改为email后成功，之前没有业务读取或写入。上述均为检查脚本问题，不改业务代码、不追认初次成功。

## 正式发布读回

`21-release.json`核实际镜像`8dceeb0bc940…`及71路由；`21-loaded.json`和`21-runtime-config.json`核667摘要、策略及知识挂载。`local-process.json`核正式PID/目录及关闭临时候选。两端`*-after.json`各10业务GET与各自`*-before.json`完全一致（仅排除observed_at）。`docs-local.json`/`docs-21.json`各39文件14入口一致，docs19；`other-containers.json`确认36个其它运行容器身份/镜像/启动时间保持，包含新版核心。无新模型、业务写入、迁移或Git提交推送。
