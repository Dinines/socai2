# 对外调查 HTTP 服务代码

这里仅维护供业务后端调用的告警、事件和调查HTTP接口，包括查询与完整业务操作。内部调查步骤、组件HTTP客户端、旧v2内部应用不在此挂载。

入口为 `investigation_http.main:app`；可运行目录仍为 `services/api`。本机/21分别使用[独立profile](../../../deploy/http-service/README.md)，显式选择环境，不在代码里配置地址和端口。

| 文件 | 修改责任 |
| --- | --- |
| `external_routes/` | 对外HTTP参数、返回、状态码；不得直接操作SQL、模型或消费者 |
| `ports.py` | 对外用例方法边界，不提供Session或Store |
| `dependencies.py`、`errors.py` | HTTP依赖装配、已有业务错误转换 |
| `contracts.py` | 共享业务DTO明确导出；HTTP专用请求定义 |
| `adapters/services.py` | 接入Case、任务、A/I查询和管理用例；异步提交经独立analysis_submissions适配接任务核心 |
| `adapters/identity.py` | 独立应用默认内部可信，用配置上下文；保留旧主API自己的身份依赖 |
| `adapters/runtime.py` | HTTP所需连接、健康及配置，不启动主API或后台消费者 |

调查核心留在 `app/socai2/`，不依赖本包。事件`diagnose`只持久受理并返回202，后台调度再执行；HTTP不启动消费者、不调用模型或创建Run。告警由正常入站自动分诊，对外`analyze`已移除；旧stage_execution路由为空，不保留同步旁路。Case建案登记首轮任务；外部prepare/start已移除，内部核心原语保留。当前源码已挂载`POST /api/v1/socai2/cases/{case_id}/investigations`，按`mode=check/rerun`持久受理，再沿`status_url`读取实际任务/attempt/Run。程序内部阶段仍通过业务方法调用，现场是否可执行须核同版核心、配置与共享调度器。

[完整边界及内部HTTP清单](../../../docs/design/investigation-http-boundary.md) · [交接指南](../../../FRONTEND_BACKEND_HANDOFF.md) · [独立OpenSpec](../../../openspec/changes/archive/2026-11-13-separate-investigation-http/design.md)。

独立HTTP不挂载登录路由、不验证Token或角色。启动时通过绝对路径`SOCAI2_HTTP_CONTEXT_FILE`读取JSON：`tenant_id`、`actor_id`、`actor_name`；对应本环境的租户和记录身份。该上下文仅用于业务归属/保存关系，不表示实际调用者已认证。配置缺失启动报错，不采用演示身份。

Case四个写入口通过`adapters/case_allocation.py`只做错误及URL装配，实际容量分配/关系/任务保存由核心用例完成。`case_allocation_contracts.py`在核心业务DTO上增加HTTP导航；不在路由计算接收目标。历史联验见[无鉴权保存与读取](../../../docs/integration/case-allocation-http.md)，当前源码的异步受理由`adapters/analysis_submissions.py`接任务核心。当前接通工作见[现有HTTP与真实数据](../../../openspec/changes/complete-socai2-investigation-chain/http-real-data-connection-20261120.md)；S4有限runner没有挂全部受理/执行链，不能用于证明本应用已完整接通。
