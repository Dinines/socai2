# 1D 向量与embedding验收

2026-10-20。**结构/存取与单服务恢复验收通过。** 本批准备告警调查依赖；API/Fusion业务源码、配置及已有1F证据保持。Agents、知识自动索引和记忆写回尚未接通。

| 对象 | 实际结果 |
| --- | --- |
| 共享Qdrant | 21:6333/6334，1.7.0，原镜像ID `ff1639878418…`、卷`sting-infra21_qdrant`和API key保留；起止集合均为空 |
| 文件描述符 | 仅重建Qdrant，实际进程soft/hard从1024/524288改为65536/65536；配置已持久化到共享Compose |
| 独立embedding | `socai2-ollama-embedding-1`，Ollama0.40.6；从20复制既有镜像并核相同image ID `265409e1d931…`，21无需调用20 |
| 模型空间 | `qwen3-embedding:0.6b`，595.78M/Q8_0，原生1024维；运行digest `ac6da0dfba84…`，模型文件和符号链接均与20对应 |
| 资源/访问 | CPU16核、内存上限32GiB；应用户要求从8GiB在线提高，容器ID/启动时间保持。仅21 loopback11435及socai2项目网络可达，无GPU设备，实际`size_vram=0` |
| 探针 | 21固定API镜像Python3.11.17/httpx0.28.1中运行；复用20 embedding helper原件，无业务worker |
| 保留范围 | 新增1个embedding容器和专属bind目录，无新增Docker数据卷；其他31个已有容器元数据、18个卷名保持，API/Fusion readiness均200 |

## 输入、调用与最终关系

三条标记文本包含可疑PowerShell、授权维护及材料不足的中文测试告警，仅用于依赖验收。实际调用 `http://ollama-embedding:11434/api/embed`，同一请求得到3条有限非零1024维向量；约5.240秒，服务返回prompt_eval_count=88，费用unknown。保存输入hash、实际向量hash、模型manifest/blob hash及调用ID。

独立集合`socai2_verify_1d_20261020_qwen06b_1024`使用Cosine/1024维。三条点ID分别为`aa1f4302-5a10-523b-9633-31fc968dfc7b`、`91398a11-26c4-5b35-bf20-f14dc045997a`、`9a36bcf9-5a81-514a-9c72-7ed881d12d30`；payload含batch、文本hash、模型/manifest、维度及测试tenant标记。

写入wait=true完成→按相同ID回读payload和向量→每条原向量查询自身为首位，score约1→只重建Qdrant→同样的3个ID/payload、1024维和查询结果恢复。原数据卷和镜像未替换。无API key请求403，2维错误向量400，集合精确count仍为3。

最后只删除本批集合，确认404且集合列表回到执行前的空列表。没有为方便测试清空数据库或既有集合。3项既有MockTransport/向量合同测试另行通过，不与真实模型调用混称。

## 来源与首次失败

[来源清单](../handoff/1d-source-manifest.json)记录20 helper原件、3个固定上游适配源hash及本批部署工具。`prepare.py`生成了忽略目录中的参考副本，**未挂载到任何业务服务**；原20适配不能直接承担21共享Qdrant密钥传递。

工作站转发镜像/模型较慢，已主动中断并改为仅允许21来源IP、随机token的临时直传；镜像约3.79GB传输78秒、模型tar约639MB传输约1秒。临时监听和20的传输文件已移除，20原embedding容器ID、启动时间和镜像保持；只复制models目录，没有复制其Ollama身份私钥。

前两次启动前校验因来源`find -type f`遗漏已有`manifests-v2`符号链接而失败，未启动业务或写Qdrant。补充显式链接目标及解析后内容hash，原有5个文件均未变化；没有放松权重校验。两份失败日志及初次来源盘点继续保留。

## 限制与下一项

这是自向量匹配与持久化恢复验证，不证明语义相关性、全量ATT&CK/TI、Agent消费或调查质量。API/Agents/TI尚未接本批embedding。API当前REST路径使用httpx；未来Agents/TI锁中的qdrant-client1.19.1没有在本批安装或验收，旧search差异仍到1G/3C定向处理。

共享Qdrant仍用HTTP和共享API key，没有新增TLS或集合级ACL；集合/tenant标记仅是逻辑分配。本批未启真实厂商动作或对话模型，费用不能记零。完整服务端基线尚未冻结。**下一单项：1E角色模型网关，21受控路由到43。**

[机器回执](1d-vector-embedding.json)、[本地校验](1d-local-verification.json)及[21操作说明](../../deploy/aisoc21/README.md)可回查实际指纹和恢复方法。原始样本/向量/日志在21 `evidence/1d-20261020/`及工作站忽略目录，真实配置不入Git。
