# Design

## 当前阶段：2026-11-12

1. 保留 `app.socai2_main` 为唯一当前独立应用入口，挂载现有43操作及现有认证。使用配置文件选择监听地址/端口、服务名、数据库目标、读写连接、策略和开关。以显式目标匹配代替硬编码禁止数据库名`aisoc`；认证/读取和写入目标必须相同。启动只读验证连接/已有结构，不自动迁移或创建支撑表。
2. A/I手动执行改用现有 `get_case_write_sessions()`，Case/H维持现有逻辑；关闭服务同时释放通用和调查写池。请求/响应DTO、告警字段、幂等key及状态保持。
3. 本机使用ARM64 Python和本机隔离PostgreSQL；21使用AMD64独立容器，显式指向正式`aisoc`。统一HTTP合同，环境数据彼此独立。部署配置声明新的正式服务名/端口，不覆盖原主API、旧独立容器或旧库。
4. 21镜像以实际运行主API镜像ID为基础，只复制本阶段明确文件。认证、模型、策略、CA和读写凭据沿用正式服务既有配置，只在21受控文件中派生独立配置。发布包无凭据，不同步工作树其他未发布改动。模型/知识业务仍以该已部署基础为准。
5. 验收复用上轮43操作及31项功能证据，只补启动目标校验、A/I写池接线、一条真实TCP HTTP建案→H修订→GET/SQL读回，以及两个环境的实际路由目录。模型不新采样；A/I写逻辑用已有替身验证。正式验证用独立验收Case/H，不修改原业务Case，不启动Run。
6. 回退只停止本轮新服务；旧入口/镜像/数据一直保留。交接文档只将验收后的新入口设为推荐地址；本地与21的配置及数据目标各自明确。完成限定独审后统一发布一次，再记录实际回执。

## 历史阶段：2026-10-28

Keep `application:create_app` as the standalone entry. Add `/livez` for process liveness and `/api/v2/investigation/openapi.json` for the existing route contract; neither asserts database/model readiness. Do not mount the legacy main app or start its background tasks.

Use the currently inspected API image `sha256:5a1e1fd8cf08349438e7d1346a25c9599bff7937df5d22ea94426e77b33f2aa9` as the dependency base. Copy current Python sources into an isolated work directory. Start one independently named container on existing `socai2_default`, publishing only `127.0.0.1:18010`. Reuse core API environment and read-only CA/identity mounts; add only existing Agents model connection/key settings and role `aisoc-investigation`. Store the new environment file only on 21, mode0600; do not print values or modify current containers/credentials.

The caller reads its token from an environment variable, accepts one GET/POST and optional JSON file, and never retries a POST. Relative `/api/v2/investigation` links use the investigation base; `/api/v1` links use the core base. Disable redirects so credentials are not forwarded to another endpoint. The resident smoke check covers liveness, actual route schema and the existing unauthenticated rejection; it does not repeat model workflows or claim authenticated business HTTP acceptance.
