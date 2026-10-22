# 调查候选本地镜像构建与离线核验

2026-10-22。用户在[构建准备](investigation-candidate-build-20261022.md)后要求继续，并明确授权将两个完整父镜像从21导出到本项目本地目录。本轮已完成两个本地候选镜像及镜像内离线核验，**未部署21、启用其常驻worker或调用模型**。

## 1. 实际产物

| 本地候选tag | Docker返回的镜像ID |
| --- | --- |
| `socai2-api:investigation-context-candidate-20261022` | `sha256:5a1e1fd8cf08349438e7d1346a25c9599bff7937df5d22ea94426e77b33f2aa9` |
| `socai2-agents:investigation-context-candidate-20261022` | `sha256:49643b84b8f797229d793adbc462c8c8e5428cfa585934f0345b8b3400a25ba9` |

父版本仍为API `1be37c38`、Agents `aec3c54f`，完整ID见[机器摘要](../handoff/investigation-candidate-images-20261022.json)。父镜像按精确ID只读导出，540,884,410字节压缩归档保存在`.local/aisoc21/investigation-candidate-20261022/image-build/parents-by-id.tar.gz`，归档SHA256 `684fc0d31fc639490e1facf746140c69fe1ce0d61493ccde3d6b344f405e93b1`。本地载入后核ID/amd64，补父tag时拒绝覆盖不同版本；远端未打tag、构建、启动或替换容器，未上传本地业务源码。

构建只使用已审API7/Agents12源码及固定清单，依赖层未重装。实测父RootFS层为子镜像前缀（API27→34、Agents123→135），OS/Architecture/Cmd/Entrypoint/User/WorkingDir继承一致。宿主为linux/aarch64，镜像目标及探针为linux/amd64。表中ID按当前Docker实际返回记录，不将父image ID改写成registry digest来拼FROM。

## 2. 构建环境与必要适配

初始OrbStack停止，本轮受控启动后恢复了11个既有本地容器；没有修改它们的配置或把它们的自主活动计入本轮测试。两个所需父镜像本地原先不存在，才进行上述导出。完整内部镜像导出首次被自动审批拒绝，理由为缺少对此payload和目的地的明确授权；原操作未执行，用户回复“授权”后才重试成功，没有绕过拒绝。

以下实际失败均保留在本地`image-build/`，没有改写为通过：

| 尝试 | 实际停止点 | 最小处理 |
| --- | --- | --- |
| attempt01 | API父镜像缺省Entrypoint，Docker模板直接取字段失败，未开始构建 | 助手改用Go模板index读取4个可选启动字段，缺省保持null |
| attempt02 | classic builder首次COPY报parent snapshot不存在，未生成候选镜像 | 保留classic默认，不自动fallback；显式核验并选择本地内置BuildKit |
| attempt03 | context绑定的Buildx驱动要求CLI使用`--context`，未开始实际构建 | 已核Host后显式按该context调用Buildx |

成功执行使用已有`orbstack`节点：driver=docker、单节点running，其context解析为`unix:///Users/lychee/.orbstack/run/docker.sock`，严格等于已选本地daemon。未创建/bootstrap builder，也不使用远程或docker-container builder。每个服务构建前重新核父ID/清单/端点，固定`--pull=false --network none --platform linux/amd64`，仅本地加载输出。

[构建助手](../../deploy/aisoc21/build_investigation_context_candidate.py)已包含上述必要适配；原助手及三次失败日志保版，19源码、两份Dockerfile、pyproject/lock不因这些适配改变。当前可复用命令如下；目标tag已存在时助手会拒绝覆盖，因此不需重复构建现有成功镜像。

```sh
.local/conda-envs/socai2/bin/python deploy/aisoc21/build_investigation_context_candidate.py \
  --candidate-dir .local/aisoc21/investigation-candidate-20261022 \
  --local-buildkit-builder orbstack --execute
```

## 3. 镜像内实际检查

各镜像只执行一次临时Python探针，入口覆盖为`python -B -`，不调用serve/app lifespan、实例化worker或进入调查。实际参数为`--network none --read-only --user 10001:10001 --cap-drop ALL --security-opt no-new-privileges --pids-limit 128`，只给`/tmp`32MiB tmpfs，无端口、业务卷或工作区app挂载；OTEL/追踪关闭、socket调用额外阻断，不打印环境值。两次退出码均0，stderr均空，临时容器自动删除，定向回查无候选容器残留。

| 实际检查 | API | Agents |
| --- | --- | --- |
| Python | 3.11.17 | 3.11.17 |
| 选入源码实际hash及内存编译 | 7/7 | 12/12 |
| 7个旧C2/文案文件 | 不适用 | 7/7匹配candidate05，父层继承且未被COPY |
| 实际业务模块导入 | 385，全部来自镜像`/app/app` | 129，全部来自镜像`/app/app`；12个选入模块全部导入 |
| OpenAPI路由登记 | context GET/POST、Alert链GET、Case调查POST，共4方法正确 | 不适用 |
| 执行身份 | UID10001 | UID10001 |

Deep实际hash为已审“candidate05＋仅链图摘要”变体，未带工作区其余C2修改；UEBA保持证据复用父版本/Bundle定向比较。镜像内SQLAlchemy2.1.4等实际版本随探针保存，未用Conda3.12环境结果代替镜像运行。本轮不重跑前批100项直接合同、真实模型或整链业务；以上是镜像内容/导入/路由核验，不能外推服务健康、真实调查结果或旧质量通过。

本地原始证据目录为`.local/aisoc21/investigation-candidate-20261022/image-build/`：build-result.json/build.log、probe-execution.json、api/agents-probe.json及原始stdout/stderr、父镜像归档/载入记录、execution-state.json；机器摘要保存相关hash与有限结论。

## 4. 交付边界与后续

本地候选镜像现已存在，可以进入阶段发布准备。实际21发布、服务运行及发布后验证尚未执行；本轮不扩大为常驻准入、C2质量修复或跨事件关联二开。旧失败/unknown/积压和原保护保持，完整change仍5/15，不归档或Git提交推送。21操作仅为镜像只读检查/导出；构建与探针没有新模型、业务HTTP/PG/图写、Kafka消息或Case/Run。

结束独审由未参与实现的candidate_images_end_audit完成，**限定ACCEPT，0项本轮剩余阻塞**。只读核精确父版本/19清单、本地builder、层与配置继承、19/7源码、两次受限probe及实际清理0、15份证据hash/当前helper hash、授权/失败记录与5/15；未调用Docker、网络或业务测试、未修改文件。OpenSpec strict、diff和新回执3个本地链接检查通过。结论仅覆盖本地镜像构建与离线检查，不批准21部署、真实调查结果/质量或常驻。
