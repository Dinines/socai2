# 对外调查 HTTP 服务代码

这里仅维护供业务后端调用的告警、事件和调查HTTP接口，包括查询与完整业务操作。内部调查步骤、组件HTTP客户端、旧v2内部应用不在此挂载。

入口为 `investigation_http.main:app`；可运行目录仍为 `services/api`。本机/21分别使用[独立profile](../../../deploy/http-service/README.md)，显式选择环境，不在代码里配置地址和端口。

| 文件 | 修改责任 |
| --- | --- |
| `external_routes/` | 对外HTTP参数、返回、状态码；不得直接操作SQL、模型或消费者 |
| `ports.py` | 对外用例方法边界，不提供Session或Store |
| `dependencies.py`、`errors.py` | HTTP依赖装配、已有业务错误转换 |
| `contracts.py` | 共享业务DTO明确导出；HTTP专用请求定义 |
| `adapters/services.py` | 接入现有Case、任务、A/I查询/执行/管理服务 |
| `adapters/identity.py` | 复用现有身份/登录，不另建认证体系 |
| `adapters/runtime.py` | HTTP所需连接、健康及配置，不启动主API或后台消费者 |

调查核心留在 `app/socai2/`，不依赖本包。旧入口/路由文件只转接到这里，依赖覆盖对象身份保持一致。业务后端的 `analyze/diagnose/start` 属于对外操作；程序内部阶段通过业务方法调用。

[完整边界及内部HTTP清单](../../../docs/design/investigation-http-boundary.md) · [交接指南](../../../FRONTEND_BACKEND_HANDOFF.md) · [独立OpenSpec](../../../openspec/changes/archive/2026-11-13-separate-investigation-http/design.md)。
