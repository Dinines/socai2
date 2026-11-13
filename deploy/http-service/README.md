# 独立调查 HTTP 服务

当前59个告警/事件/调查操作，其中56已实现、3预留501。原Case管理、告警/事件管理、三类列表查询和完整CSV已交付。前批[E57归并统计](../../openspec/changes/archive/2026-11-13-summarize-incident-grouping/validation.md)按同一告警来源/发生时间范围返回归并数量和明确比例。

| 环境 | Profile | 数据目标 | 入口 |
| --- | --- | --- | --- |
| 本机ARM64 Python | `local.json` | 本机隔离库`v12_upgrade_dev` | `http://127.0.0.1:18024` |
| 21 AMD64 Docker | `aisoc21.json` | 正式库`aisoc` | `http://192.168.1.21:18024`，本批已发布，59操作 |

两个环境共享HTTP合同，记录ID各属本环境。21原主API18000、旧独立API18020及其旧隔离库保持。新的正式入口不启动消费者、不自动执行调查；业务后端显式调用分析接口后仍会按现有业务执行模型，结果质量按响应及独立验收记录判断。

对外HTTP与内部调查调用的代码边界见[架构说明](../../docs/design/investigation-http-boundary.md)。两端18024使用独立入口 `investigation_http.main:app`；当前21发布 `case-comments-20261113-r1`，本机为同源 `case-comments-20261113-r1-local`，根profile与case-comments目录一致。新增归并统计只读、不触发调查；内部HTTP应用和组件客户端保持独立。

本机访问21使用`relay.json`的28024；验收正常登录使用`auth-relay.json`的28025转到原主服务认证入口。旧28000转发本轮返回空503，未修改；新转发与原账号正常登录已实际验证。过期旧key未续期或改权，认证token不写入公共证据。

21本轮从已发布grouping-summary镜像派生，仅叠加case-comments/aisoc21.json列出的8个文件。本机从同一已部署源码冻结后覆盖相同8文件，位于`../socai2-http-runtime/case-comments-20261113-r1`。实际源码/镜像以本批回执为准，未带入并行模型修改，无迁移。

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

本轮[归并统计验收](../../openspec/changes/archive/2026-11-13-summarize-incident-grouping/validation.md)包含新批次本机真实TCP/PG、原56操作合同保持和21既有合成范围只读复验；Swagger docs11同步，其他服务/消费者保持。18026仅作候选验收，正式入口18024。

本轮替换已有18024服务的profile显式设`replace_existing=true`，先核原镜像及端口；`expected_operations=59`用于读回。`case-comments/preview.json`的18026仅作本机验收，正式本机使用根local.json的18024。`verify_management.py`按环境专属profile新建验收Case，记录意图及响应，不自动重试写入或启动模型。

告警／事件验收使用 `verify_subject_management.py` 和 `subject-management/verify-*.json`，只操作本批明确标记的合成主体；`subject_management_fixture.py`提供受控新样本与SQL读回。`SOCAI2_MANAGEMENT_CONFIG_FILE`显式指定批量配置，默认交付`max_batch_items=100`，变更后重启本项服务。人工写入复用`SOCAI2_CASE_API_ENABLED`及既有调查写连接，关闭时新接口返回`503 socai2_subject_write_not_enabled`。

三类列表验收脚本为verify_list_query.py，配置在list-query/；seed仅允许本机隔离库，一批只建一次，verify仅GET及只读SQL，不重派分析。发布后复验脚本和回执保存在本批证据目录。

CSV导出配置为`app/socai2/list_export.json`，用`SOCAI2_EXPORT_CONFIG_FILE`显式选择；max_rows=10000、max_bytes=16777216、statement_timeout_ms=30000。启动时检查配置，错误不回落。完整只读CSV验证为`verify_list_export.py`及`list-export/verify-local.json`；发布后通过独立读取SQL核对。

归并统计直接验收使用`verify_grouping.py`和`grouping-summary/verify-*.json`；seed仅允许明确本机验证库，一批一次，verify/http只读且不调用模型。E57无新增可变运行配置，复用页面读取开关、数据库与既有只读事务。

本批普通评论E58/E59及验收见[Case评论](../../openspec/changes/archive/2026-11-13-add-case-comments/validation.md)。`case-comments/`为当前profile，`verify_comments.py`新批次只创建明确标记的Case/H/评论，不启动Run；`--read-existing`只读复验。发布SQL脚本在容器内只读事务运行；只读rootfs拒绝docker cp时，保持配置，用docker exec标准输入执行，不放宽容器。
