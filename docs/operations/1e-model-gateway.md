# 1E 角色模型网关

2026-10-20。**五角色真实路由与JSON结构验收通过。** 已在21部署独立网关，继续调用43已有服务；API/Fusion配置与源码保持，Agents/Actions仍未迁入，完整服务端基线未冻结。

| 对象 | 实际结果 |
| --- | --- |
| 网关 | `socai2-litellm-1`，LiteLLM1.106.0；从20既有镜像复制，固定image ID `2e4c0371f3a8…`，不再依赖main-stable浮动标签 |
| 访问/资源 | 仅21 `127.0.0.1:14000/v1`及socai2网络内`http://litellm:4000/v1`；独立master key；非root、只读根文件系统，4核CPU/8GiB，实际nofile65536/65536 |
| 五个发布角色 | triage、recon、investigation、summary、report；均映射43的`openai/aisoc-test-investigation` |
| 未发布角色 | copilot、nl、hunt、detection，不以参考配置存在9别名表示均已启用或通过 |
| 有界配置 | 明确45秒超时、重试0、fallback空；源配置保留，不连接外部付费模型 |
| 运行变化 | 只新增网关；其余33个已有容器元数据、18个卷名保持，API/Fusion/embedding仍健康，无新增数据卷或共享服务重启 |

## 输入、实际调用与最终关系

21固定API镜像（Python3.11.17/httpx0.28.1）内的独立探针，向每个别名各发一次带`1e-20261020`及role标记的合成请求。要求返回batch/role/status=ready/evidence_count=0，使用`response_format=json_object`，max_tokens128，temperature0、非stream。输出经严格Pydantic字段/类型/值检查，finish_reason均为stop。仅合成材料，无实际告警或厂商操作。

| 角色 | prompt/completion/total tokens | 实际秒数 | 最终值 |
| --- | --- | --- | --- |
| triage | 93/31/124 | 1.517135 | JSON校验通过 |
| recon | 93/31/124 | 0.648923 | JSON校验通过 |
| investigation | 93/31/124 | 0.632954 | JSON校验通过 |
| summary | 92/30/122 | 0.613791 | JSON校验通过 |
| report | 92/30/122 | 0.612786 | JSON校验通过 |

真实usage合计463输入、153输出、616 tokens；费用没有实际价格/账单依据，记unknown而非零。五个成功推理请求各执行一次，没有重发或隐式fallback。

网关响应`model`字段是角色别名，不能当作43底层模型身份。实际`x-litellm-model-id`和`x-litellm-model-group`已逐一关联到运行中`/model/info`的deployment ID、43地址和provider model；Prometheus另有每个角色各1次HTTP200。43模型列表从网关容器内真实读取，模型ID存在；未取得43权重/实现版本的新独立证明。请求、响应ID、调用ID、usage、route对应见[机器回执](1e-model-gateway.json)。不保存provider-specific或隐藏推理文本。

## 身份边界与首次失败

无key401；错误key被拒绝，但LiteLLM无虚拟密钥管理数据库时返回400、type=`no_db_connection`，不是标准401。未发布copilot及未知alias均400。首轮探针把错误key判据限定为401/403，因此在任何角色推理前停止；失败日志和独立400诊断保留。后续探针明确检查这个原版拒绝类型并记录限制，未加匿名绕过、改认证实现或为过测试新接数据库。

计数器包含上述鉴权/alias拒绝，不把所有失败API计数当实际provider调用或token使用。服务身份不等于tenant/BYOK隔离，虚拟密钥、租户路由及业务授权到1G/第三阶段验证。

## 来源、启动与恢复

[固定上游配置原件](../../infra/litellm/config.yaml)原样迁入；[来源清单](../handoff/1e-source-manifest.json)记录固定revision/Git blob/hash及参考factory/pins/routing。21派生配置只发布五角色，关闭原版2次重试和跨别名fallback，其余provider环境引用、Prometheus及master key行为保留；[差异](../../deploy/aisoc21/patches/1e-litellm.patch)可核对。45秒超时已实际加载，未做真实超时/断连注入，不外推失败恢复能力。

固定镜像通过临时来源IP/token受控通道从20传入，约417MB、15秒；传输监听和20临时文件已关闭/移除。20原网关ID、启动时间、镜像保持，43服务未改。独立网关密钥及provider/client运行参数保存在受控private目录；其中43沿用参数值已存在固定上游原件，不据此宣称其为保密凭据或43强制鉴权已验，见[配置入口](configuration.md#1e网关配置)。

启动/停止方法见[21操作说明](../../deploy/aisoc21/README.md)。恢复仅停止新litellm服务，保留配置/成功与失败回执，不停共享infra、清库或重发已完成/unknown调用；如未来回退路由，也只影响后续新请求。

本批仅证明真实路由及JSON对象可用，未验证工具调用、streaming、调查质量、Case/Run账本、tenant/BYOK、生产容量/高可用。43上游仍是既有HTTP路径。**下一单项为1G：迁入Agents/Actions，先构建并启动受控人工只读调查入口，保持自动分诊/升级/记忆写回与真实响应关闭。** [本地交付校验](1e-local-verification.json)单独记录来源、凭据和文档检查。
