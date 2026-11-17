# 本机实际服务状态核对

2026-11-15 15:18（北京时间）只读观察，见 [runtime.json](runtime.json)。此前“本机停用”的概括不准确：旧服务仍在运行，当前候选没有部署到这些常驻端口。

| 本机入口 | 实际运行情况 | 对接含义 |
| --- | --- | --- |
| 127.0.0.1:18024 | PID 77189，独立 uvicorn；目录 `/Users/lychee/Documents/project/socai2-http-runtime/investigation-sync-20261113-r1`；OpenAPI版本 `investigation-sync-20261113-r1-local`，71个业务操作，仍声明 HTTPBearer；无凭据 Case 列表 GET 返回401 | 是旧版独立 API，不是当前80操作、无鉴权的候选。没有用它验证新的异步任务流程 |
| 127.0.0.1:18080 | Docker `socai2-api-docs-swagger-1`，只读挂载 `.local/api-docs/releases/20261113-docs19/handoff`；实际 docs19、71操作、旧鉴权合同 | 是旧静态 Swagger。页面同时列21、28024转发及本机18024地址，不代表这些地址均已更新或可用 |
| 127.0.0.1:4177 | PID 44022 为 SSH `sting-infra21-tunnel`，首页返回200；[隧道配置](../../../operations/mac-ssh-relay-20261107.md)将本机4177转到21的4177 | 是21工作台的本机入口，不是重新启动了本机工作台；首页200不代表调查流程或新HTTP已验收 |
| 本轮 F1–F4 的 HTTP 读取测试 | 当前源码独立应用经 ASGI，显式连接本机隔离 `v12_upgrade_dev`，强制只读，无鉴权；测试进程结束即退出 | 与上述旧常驻18024不同，不冒充实际 TCP 或21验收 |

本次没有启停服务、变更监听或读取进程环境变量。最初 `/health` 探针404保留在原回执，它不是本项目实际健康路径，不能据此判断服务故障。当前目标版本仍按同一 change 完整验收后统一发布；21已知64操作/静态71及401差异沿[原21预检](../http-test-alignment-20261115-01/README.md)保留，本次未重新连接21执行业务验证。
