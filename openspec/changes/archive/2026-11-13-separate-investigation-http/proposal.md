# 独立 HTTP 代码与调查核心分离

## Why
18024 已独立运行，但53个调查操作仍混在原主API端点目录，路由直接装配数据库/业务实现，任务路由还依赖Case路由辅助函数。负责人明确要求整个HTTP服务从代码到设计分开，保持与调查执行和其他服务兼容。

## What Changes
- 将全部调查HTTP入口、路由、依赖和异常转换迁到 `services/api/investigation_http/` 独立Python包，与 `app/` 的调查核心和原平台HTTP分开。
- 路由只依赖公开数据合同和本包的服务端口；适配层负责接入现有调查服务、认证及数据库生命周期。共享业务合同保持单一来源。
- 旧 `app.socai2_main` 和调查路由导入路径保留兼容转接，不复制两套业务实现。
- 独立启动配置、部署候选、直接兼容验证和架构说明同步；不改变53操作的HTTP合同、数据库或调查行为。

## Capabilities
### New Capabilities
- `investigation-http-boundary`: 独立HTTP服务代码边界、单向依赖和兼容入口。

## Impact
本项是 `query-investigation-lists` 的先行重构，列表功能任务仍在原change维护；本项不新增filtered_total/next_cursor，也不移动或改写并行模型代码。先完成本地候选与独立审计；负责人继续推进后统一发布本机/21的18024，仅包含本项HTTP包和兼容转接。Swagger合同未变，保留docs7并只读核验；其他服务及消费者保持。
