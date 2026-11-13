# 独立调查 HTTP 服务

当前合同53个告警/事件/调查操作；E44–E47为Case管理/结案/重开，E19–E21仍501。新增E48–E53为告警反馈和告警/事件单条及批量管理；当前增量见[manage-alert-incident-operations](../../openspec/changes/archive/2026-11-13-manage-alert-incident-operations/tasks.md)，前批统一入口已归档。

| 环境 | Profile | 数据目标 | 入口 |
| --- | --- | --- | --- |
| 本机ARM64 Python | `local.json` | 本机隔离库`v12_upgrade_dev` | `http://127.0.0.1:18024` |
| 21 AMD64 Docker | `aisoc21.json` | 正式库`aisoc` | `http://192.168.1.21:18024`，本批已发布，53操作 |

两个环境共享HTTP合同，记录ID各属本环境。21原主API18000、旧独立API18020及其旧隔离库保持。新的正式入口不启动消费者、不自动执行调查；业务后端显式调用分析接口后仍会按现有业务执行模型，结果质量按响应及独立验收记录判断。

对外HTTP与内部调查调用的代码边界见[架构说明](../../docs/design/investigation-http-boundary.md)。两端18024已使用独立入口 `investigation_http.main:app`，旧 `app.socai2_main:app` 兼容转接到同一应用。当前21发布为 `http-boundary-20261113-r1`，本机为同源的 `http-boundary-20261113-r1-local`；根profile与 `http-boundary/local.json`、`http-boundary/aisoc21.json` 一致。该目录的preview用18026完成候选验证后已停止。新包仅挂对外业务接口，内部HTTP应用和组件客户端保持独立。

本机访问21使用`relay.json`的28024；验收正常登录使用`auth-relay.json`的28025转到原主服务认证入口。旧28000转发本轮返回空503，未修改；新转发与原账号正常登录已实际验证。过期旧key未续期或改权，认证token不写入公共证据。

21本轮从已发布subject-management服务派生受控环境及只读挂载，在其镜像上叠加26个HTTP包/兼容文件；镜像为 `sha256:b9316a414bf8bc1c388f02cf1edf7137f7ff096a9d05d22559f0acc62b045f3c`。本机使用从该实际镜像冻结的622个代码文件，位于普通项目目录 `../socai2-http-runtime/http-boundary-20261113-r1`，由profile显式配置运行路径和原有私密环境文件。这样两端均不加载工作区并行、尚未发布的模型修改；旧subject-management发布profile保留作历史记录。数据库目标不一致或已启用写入却没有写连接时，服务启动失败；没有自动建库/迁移。

本机启动：

```sh
python3 deploy/http-service/manage.py --profile deploy/http-service/local.json local
```

根local profile记录本机实际路径，换电脑时先复制为自己的profile，显式填写已准备的源码目录、Python路径、私密环境文件和目标数据库，再启动；不要直接使用原机器的绝对路径或静默切换数据库。当前本机18024已经运行，不需重复启动。

21先在本机`package --output <新目录>`生成无凭据候选，传至profile的`root/releases/<release>`；在21按`prepare`、`build`、限定独审、`start`、`verify`顺序执行。构建使用显式本地镜像标签和已核对ID，`DOCKER_BUILDKIT=0`，不拉取基础镜像。每次新发布使用独立release目录和与当前运行基底一致的profile，不重复执行已完成批次的prepare。

```sh
python3 manage.py --profile profile.json prepare
python3 manage.py --profile profile.json build
python3 manage.py --profile profile.json start
python3 manage.py --profile profile.json verify
```

私密环境只在主机`private/<release>/runtime.env`，权限0600；不进Git或文档。其他容器身份/镜像/启动时间在prepare时保存，verify逐值核对。当前18024是替换已有独立API容器；若需退回，使用上一release保留的compose、镜像和环境重新启动该API，并核对实际版本与数据目标，单纯停止新容器不会恢复旧版。18000/18020其他入口一直保留，数据库不回退或清空。

[直接验证](../../openspec/changes/archive/2026-11-12-serve-investigation-api/validation-20261112.md)区分本机TCP、受限写连接、实际SQL读回和21发布观察；历史真实模型失败不因入口通过而关闭。HTTP操作验证用`verify_flow.py`及环境专属profile，一次新Case/H，意图和响应逐步保存，不自动重试POST、不启动Run。

本轮[分离验收](../../openspec/changes/archive/2026-11-13-separate-investigation-http/validation.md)保留完整HTTP合同对比、本机真实写读、21既有记录只读复验及SQL读回。21本轮没有新增正式库测试数据；消费者、原主API和内部服务保持。两端Swagger继续使用合同相同的docs7，六个入口均200且文件摘要一致，无需因代码归属调整重建文档容器。

本轮替换已有18024服务的profile显式设`replace_existing=true`，先核原镜像及端口；`expected_operations=53`用于读回。`subject-management/preview.json`的18026仅作本机验收，正式本机使用根local.json的18024。`verify_management.py`按环境专属profile新建验收Case，记录意图及响应，不自动重试写入或启动模型。

告警／事件验收使用 `verify_subject_management.py` 和 `subject-management/verify-*.json`，只操作本批明确标记的合成主体；`subject_management_fixture.py`提供受控新样本与SQL读回。`SOCAI2_MANAGEMENT_CONFIG_FILE`显式指定批量配置，默认交付`max_batch_items=100`，变更后重启本项服务。人工写入复用`SOCAI2_CASE_API_ENABLED`及既有调查写连接，关闭时新接口返回`503 socai2_subject_write_not_enabled`。
