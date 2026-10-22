# 调查候选组合核验与构建准备

2026-10-22。沿[阶段收口](investigation-stage-closeout-20261022.md)选定的19个文件继续准备，沿用restore B5→B6及原2.1/3.1/3.4/4.1，不新增产品任务树。本轮完成父版本核对、隔离组合直接验证和最小构建输入；**尚未构建镜像或部署**。

## 1. 父版本和UEBA基线

只读查询21上API/Agents容器的镜像ID及对应本地tag，均匹配最近full回执：

| 服务 | 父tag | Docker image ID |
| --- | --- | --- |
| API | `socai2-api:integrity-20261021` | `sha256:1be37c3893f782b84ea5bfe3d1af20f20700f7e88fa9c79fee1202f3a15a3b1d` |
| Agents | `socai2-agents:full-ueba-context-20261021` | `sha256:aec3c54f6f07c219f55922b0209e2a8edf3303e084441bb7651a27f7845a2c82` |

二者均为linux/amd64，应用路径无覆盖挂载。本次只核上述定向事实，不称为完整运行健康或全量配置无漂移验收。ID是Docker镜像/config ID，**不是registry manifest digest**，不能写成`FROM name@sha256:<该ID>`。

从匹配上述父ID的Agents容器定向读取`/app/app/context/bundle.py`，同时确认该文件没有容器可写层修改。取得42,259字节，SHA256为`0e2c7a05e9c3ecfa4f500bec2586db0c9d94ef07b44e91096c898a5951a10025`。与候选比较：UEBA `_fetch_baselines` AST相同，原五来源的获取/采用不变；差异限定于链图字段/摘要、GET读取、可信准备回执及链图独立22秒超时，原来源超时保持。

前一轮“纯full bundle本地缺证”是当时事实，本轮已补该定向证据；不改写旧回执。原始净化记录、源文件及差异保存在本批本地目录的`baseline/`，没有记录环境变量或凭据。首次普通sandbox SSH被拒，受控只读重试成功；未创建/重启远端容器或上传本地业务源码。

## 2. 隔离组合与直接验证

本批目录：`.local/aisoc21/investigation-candidate-20261022/`。

以candidate05来源manifest核过的API439、Agents188份运行输入建立独立源码树，再覆盖前一轮审查副本中的19文件。候选bundle覆盖full唯一源码增量，并按第1节核保已发布UEBA接线；这不等于复原完整full镜像。Deep使用candidate05原件仅追加链图摘要的审查变体，7个旧C2/关闭文案文件仍为父版本，未从当前工作区整包复制。

复用相关已有测试，连同测试文件一起放入独立树，分别以API/Agents进程运行。这样避免测试按自身位置修改sys.path后误导入工作区。数据库环境变量清除、OTEL关闭、socket连接以BaseException阻断，未启动服务lifespan。

| 检查 | 结果 | 可证明范围 |
| --- | --- | --- |
| Agents直接合同 | **55 passed** | Kafka写图入口、链图Bundle与编排交接、AttackPath、单IOC请求字段 |
| API直接合同 | **45 passed** | 定向图准备/租户保护、PG链、历史查询列类型合同 |
| 已加载业务模块来源 | Agents129、API62，树外0 | 上述测试使用本次隔离组合，未混用工作区app |
| API完整router导入/OpenAPI登记 | 385个app模块均来自隔离树；以下4个方法登记正确 | GET/POST `/api/v1/graph/investigation-context`，GET `/api/v1/alerts/{alert_id}/attack-chain`，POST `/api/v1/cases/{case_id}/investigate` |

本轮组合共100项通过，不与前批85项/Deep单用例累加；不是镜像内运行、真实模型或新整链业务验收。Agents保留33条已有`datetime.utcnow`弃用警告。路由检查脚本前两次分别因FastAPI嵌套路由无path属性、检查地址漏`/api/v1`前缀失败；原日志保留，改用公开OpenAPI结果和实际前缀后通过，未改业务源码。

## 3. 最小构建输入与用法

本批`build-context/manifest.json`列出19个文件及hash，内容从审查副本复制，清单字节SHA256 `827f54b729925a9110bc21d9b0254ab3eb09aa68eea430891d0f4fe68b24f193`固定在助手中；两服务context只含各自API7/Agents12份源码，不含凭据、测试、锁文件或其他工作区差异。

- [API Dockerfile](../../deploy/aisoc21/Dockerfile.investigation-context-api)和[Agents Dockerfile](../../deploy/aisoc21/Dockerfile.investigation-context-agents)逐文件COPY至原`/app/app/`，权限为10001:10001；继承各自父镜像依赖和启动配置。
- [本地构建助手](../../deploy/aisoc21/build_investigation_context_candidate.py)默认只输出计划并校验输入。实际构建前核本地Docker endpoint、父tag对应ID及架构；不下载父镜像，不回退candidate05。构建仅生成新的本地候选tag，不执行run/compose/push或部署。

从仓库根运行默认只读计划：

```sh
.local/conda-envs/socai2/bin/python deploy/aisoc21/build_investigation_context_candidate.py \
  --candidate-dir .local/aisoc21/investigation-candidate-20261022
```

后续可用`--check-parents`定向检查本地父镜像；实际需要本地构建时用`--execute`，固定`--pull=false --network=none --platform=linux/amd64`，显式使用本地classic daemon builder（`DOCKER_BUILDKIT=0`），不自动回退远程Buildx。助手拒绝远程Docker endpoint和已有候选tag，构建后核父层前缀及Cmd/Entrypoint/User/WorkingDir继承；默认计划、帮助和静态编译通过；Docker检查/实际构建执行路径本轮未实跑。

## 4. 当前结果及剩余工作

本地Docker socket不存在，因此本轮没有启动Docker或构建镜像，也没有改用21远程构建。**源码组合及构建输入已准备；实际镜像构建、镜像内检查和阶段发布仍未完成。** 后续先在本地具备指定父镜像的Docker上构建，核实际镜像结果，再按阶段处理发布；本轮不将配方的存在当成镜像通过。

本轮0真实模型、业务HTTP/PG/图写、Kafka消息/位点提交、Case/Run创建、部署或常驻启用；21访问仅为定向父版本/文件只读取证。7项后置工作及旧Deep工作区源码保留，原C2质量失败、预算/unknown及常驻worker OFF保持，原任务仍5/15，不归档、Git提交或推送。机器记录见[本批摘要](../handoff/investigation-candidate-build-20261022.json)。

结束独审由未参与实现的candidate_preparation_audit完成，**限定ACCEPT，0项本轮剩余阻塞**。独立核19份源码/隔离树/context一致、7排除项保持父版本、Deep变体、父版本/UEBA证据、100合同/路由日志及文档边界。提出清单身份固定、构建后父层/配置检查两点，已在助手补齐并只读复核；未重跑业务测试、联网或调用Docker。该结论只覆盖源码组合证据与构建准备，不批准尚未构建镜像、运行质量、部署或常驻。OpenSpec strict、diff、新回执5个本地文件链接检查通过，任务仍5/15。

## 5. 后续实际本地构建

用户继续并明确授权完整父镜像导出后，已另完成[本地镜像与离线检查](investigation-candidate-images-20261022.md)。前文Docker未运行/镜像未构建为准备时事实；后续helper因实际环境补缺省字段、显式本地BuildKit及context必要适配，原helper按原hash另存。实际镜像通过不改变本回执的原准备/静态审查范围，不追认21部署或质量。
