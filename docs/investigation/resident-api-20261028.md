**最新状态（2026-10-31）：** 常驻`20261031-r8`，源码`a41ae07`，21本机18010；镜像`sha256:1f0bfe52f92b402fe2c92ed5b66c1c7250e21c27a900a2299020355b21eb337b`，472应用源码已核。开发Key与服务配置保持。协议边界修复已直接验证；唯一真实调查的纠错调用约45秒后遇网关Timeout，failed/partial，最终内容未验，见[最新回执](../operations/investigation-protocol-uncertainty-20261031.json)。下方版本为历史记录。

**2026-10-31 当前入口：** 21调查API已更新20261031-r3，监听127.0.0.1:18010；[实际批次回执](../operations/investigation-audit-live-r3-20261031.json)。后续本地纠错修复尚未部署。

开发凭据已按用户明确全权限授权保存于21的`/opt/sting-aisoc-socai2/private/investigation-dev-keys.json`，root拥有、0600，目录0700；JSON按tenant UUID映射Bearer。两个原租户分别为53824f24-d1d4-5820-8147-f6cfda8a1247（专用fixture）和f6a5c700-69b8-44fc-8238-609362fb1a9f（stingAISOC Production，含演示Case），scopes为`["*"]`，2027-10-31T05:43:45Z到期。经既有SSH在远端读取所需租户的值到AISOC_API_TOKEN，仅调用既有scripts/investigation_client.py；不打印Key，不将明文复制到本地/仓库。最初验证两租户各Case读取及调查历史GET均200；随后r4/r5/r6已使用该Key执行限定功能调查。原批次临时Key已停用，长期Key独立保留。

**2026-10-31版本说明：** 以下描述最近留存的r1部署回执，本次未重新连接21确认。当前仓库Compose/安装脚本已准备20261031-r3，包含追加修复及审计问题修复，见[实施记录](audit-fixes-implementation-20261031.md)；[任务记录](../../openspec/changes/fix-case-followup-gaps/tasks.md)仍将常驻替换和真实复验列为待做。因此下文源码链接是当前文件，不代表已运行r3。业务和审计入口见[最新指南](audit-guide-20261031.md)。

# 独立调查API与调用方接入（2026-10-28）

**状态：已按用户明确授权在21常驻启动。** 进程存活、实际接口描述、端口绑定和配置复用检查通过。既有调查与事件概况功能已通过的结果继续复用；本轮没有业务写入或模型调用。

**后续多案例更新：** [四案例逐步测试](multi-case-http-20261028.md)已通过真实API Key执行207个业务HTTP请求，未覆盖CurrentUser依赖；写入、调查、模型、报告与证据入口均实际调用。4次主调查完成，2/4例自动流程检查通过，具体失败和内容偏差保留在总报告。该批临时Key已停用，用户JWT登录仍未验证。下方“本轮未取得普通用户token”保留启动当时边界，不作为后续未测试的结论。

## 服务入口

新增容器`socai2-investigation-api`已运行，镜像`socai2-investigation-api:20261028-r1`，镜像ID为`sha256:2fde05d545c3ce9f042f180e91cc38dec30bf85e939f686b7a13dc6d04d27b98`。实际只映射21的`127.0.0.1:18010`，连接`socai2_default`，restart=unless-stopped。复用原API镜像的已验证依赖，当前源码放在独立工作目录，入口为`app.investigation_v2.application:create_app`。

- 调查入口：`http://127.0.0.1:18010/api/v2/investigation/…`
- 接口描述：`http://127.0.0.1:18010/api/v2/investigation/openapi.json`，目前18条路径。
- 进程存活：`http://127.0.0.1:18010/livez`。只证明HTTP进程响应，不证明数据库/模型就绪。
- 现有核心入口继续为`http://127.0.0.1:18000/api/v1/…`。

新服务已复用现有API的数据库/认证环境和只读CA/identity挂载；模型连接和key取自既有Agents配置，显式模型角色`aisoc-investigation`。逐项比较确认：除模型配置外，原API环境值相同，模型连接/key与Agents相同；比较过程未输出值。环境文件只在21创建为`/opt/sting-aisoc-socai2/private/investigation-v2.env`，实际mode0600。该入口不加载旧main的后台任务，也未启用首次概况worker。

## 调用脚本

[investigation_client.py](../../scripts/investigation_client.py)使用标准Python库，不需要安装SDK。Token通过`AISOC_API_TOKEN`提供，使用已有且有对应权限的普通Bearer身份；本轮不新建用户或权限。不在命令行传token。

工作站通过SSH访问21本机的两个端口：

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 18010:127.0.0.1:18010 -L 18000:127.0.0.1:18000 sting-infra21
```

在另一个终端设置好`AISOC_API_TOKEN`后，从仓库根目录调用：

```powershell
python scripts/investigation_client.py GET /api/v2/investigation/incidents/fbbe6415-3d73-5742-a91a-d1a9617d379d
python scripts/investigation_client.py GET /api/v2/investigation/cases/467dc2a9-fa33-4aba-bb87-19595ecd176e/investigations
python scripts/investigation_client.py POST /api/v2/investigation/case-links --body case-link-request.json
```

POST请求体沿用[成员转Case](case-linking-20261028.md)和[Case调查](case-first-version-20261028.md)合同，调用方自行提供operation_key。脚本不生成新key、不重试POST。超时或连接失败后，按原key或返回的result_url核对，不能把通信失败当成未执行。

把响应中的`result_url`、`steps_url`、`evidence_url`等相对路径作为下一次path参数即可。`/api/v2/investigation`发往`--base-url`，`/api/v1/cases`等核心路径发往`--core-base-url`；默认分别为本机18010、18000。HTTP正文输出到stdout，HTTP状态输出到stderr；2xx退出0、HTTP失败退出1、通信/文件失败退出2。脚本拒绝重定向，避免把认证头转交其他地址。

## 启动与验证范围

[Dockerfile](../../deploy/aisoc21/Dockerfile.investigation-v2-api)、[Compose](../../deploy/aisoc21/compose.investigation-v2-api.yml)、[安装脚本](../../deploy/aisoc21/install_investigation_api.py)已用于部署。安装脚本默认只输出计划；本次明确授权后使用`--execute`。依赖基镜像核对为当前API的`sha256:5a1e1fd8cf08349438e7d1346a25c9599bff7937df5d22ea94426e77b33f2aa9`，构建未下载依赖。原API/Agents容器ID和启动时间保持一致，未替换或重启。

本地已验证存活和OpenAPI两个GET，以及一个虚构HTTP样例中的调查POST/核心GET地址选择、原请求体保持、503不重试和302不跟随；没有业务写或模型调用。[本地直接证据](../operations/investigation-api-entry-local-20261028.json)。常驻HTTP的livez/schema均200、schema有18条路径；未带凭据的Case历史请求401。常驻服务没有身份依赖替身，但本轮未取得普通用户token，不宣称真实身份业务请求已验；之前的ASGI/注入身份功能证据仍单独记录。

代码包保存在21的`/opt/sting-aisoc-socai2/investigation-v2/20261028-r1`，仅475个明确源码/部署/调用脚本文件，不含运行环境文件。常驻启动已得到用户批准。[部署、源码清单、端口和配置比较完整记录](../operations/investigation-api-resident-20261028.json)。OpenSpec CLI不可用，未做严格CLI校验或归档。

停止该服务时在21运行下面的命令，保留原API及测试数据：

```bash
docker compose -f /opt/sting-aisoc-socai2/investigation-v2/20261028-r1/deploy/aisoc21/compose.investigation-v2-api.yml stop investigation-api
```
