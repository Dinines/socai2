# 192.168.1.20：参考 AiSOC 部署

> 历史参考环境记录。socai2当前只负责[告警处理服务端](../../docs/operations/alert-processing-scope.md)，不交付前端；本页CORE、控制台及维护命令只描述20参考部署，不能作为21新服务方案或已通过验收的证明。

2026-10-20 实测。这是独立的上游参考环境，不是 stingAISOC 的运行组成部分，也不构成 stingAISOC 功能验收。

## 位置与访问

| 项目 | 当前值 |
| --- | --- |
| SSH | `ssh sting-host20`，账号 `lychee`，可免密 sudo |
| 源码目录 | `/home/lychee/beenuar`，由本地参考仓库的 Git archive 传输，不含 `.git` |
| 来源 | <https://github.com/beenuar/AiSOC> |
| 源码及官方应用镜像 revision | `34ca18c57dd4175539e5c6dd3d04a72dc057306b` |
| 控制台 | <http://192.168.1.20:3000>，版本 `19.0.0`，非 demo 模式 |
| 管理员 | `admin@aisoc.internal` |
| 密码 | 仅保存在服务器 `/home/lychee/beenuar/deployment/admin-credentials.json`，权限 `0600` |
| 对话模型 | `http://192.168.1.43:8000/v1`，`aisoc-test-investigation` |
| 嵌入模型 | 20 本地 Ollama `0.40.6`，`qwen3-embedding:0.6b`，原生 1024 维、CPU |

43 上当前是兼容 OpenAI 接口的模型服务，Ollama 未启动。按用户要求复用该服务，LiteLLM 的七个对话角色别名均使用它。20 另运行一个只用于嵌入的 Ollama，不在 20 部署对话模型。

## 部署配置与维护

按上游默认 CORE 部署，以 43 替代 bundled 对话模型，加上独立嵌入 Ollama，共 16 个运行服务。未启用 `full`、`extras`、`monitoring` 等可选 profile。

配置保存在服务器 `.env` 和 `docker-compose.override.yml`：生成独立凭据，保持生产认证；仅控制台绑定 `192.168.1.20:3000`，数据服务和后端端口保持 loopback。AiSOC PostgreSQL 使用 `127.0.0.1:15432`，宿主机原有 PostgreSQL `5432` 保持原样。所有运行服务启用 `unless-stopped`。

服务器上执行：

```bash
cd /home/lychee/beenuar
docker compose ps -a
docker compose up -d --pull never --no-build
docker compose logs --tail 100 api agents litellm
```

使用以上 Compose 命令维护这次部署。上游 `make up` 的端口自动映射会另生成 overlay，并可能忽略这里的默认 override；本次没有使用它。部署 override 的副本见本目录 [docker-compose.override.yml](docker-compose.override.yml)。

Docker Hub 直连仍不可用。基础镜像通过 [DaoCloud 公共缓存](https://github.com/DaoCloud/public-image-mirror) 获取并保留原始标签；应用镜像从官方 GHCR 获取，revision 已与源码核对。各镜像摘要记录在服务器 `deployment/image-inventory.json`，后续升级需显式获取新镜像，不以重启代替升级。

## 已测证据与边界

- 初次 CORE 部署的 15 个服务均 running、重启次数为 0；带健康检查的服务全部 healthy。初次快照见服务器 `deployment/service-status.json`；嵌入接线后的状态另见 `deployment/embedding/service-status.json`。
- 控制台 `/api/health` 为 200；`/api/runtime-config` 返回 `demoMode=false`、`consoleVersion=19.0.0`。
- 管理员经控制台同源代理登录 200，读取 `/api/v1/auth/me` 确认为 admin；记录见 `deployment/login-check.json`，无 token/密码。
- 一次 `aisoc-triage` 网关调用经 43 返回 `READY`，约 1.409 秒，usage 19 输入 / 2 输出 / 21 总 token，费用 unknown；受控记录见 `deployment/model-smoke.json`，未保留隐藏推理。
- 上游 golden pipeline 合成事件 `5c3757a85756`：10/10 项通过，接入 accepted=1/rejected=0，经 Kafka/Fusion 生成告警 `b6f8d542-a461-5b03-b515-6da94297b205`，API 可读，severity=`high`，来源=`CrowdStrike Falcon`。记录见 `deployment/golden-pipeline.log`。

上述仅为部署 smoke。合成事件不是生产观测；没有验收完整调查质量、真实厂商连接、响应执行或 full profile。本轮未修改或重启 43 的模型服务，也未修改 stingAISOC 业务代码及 OpenSpec 任务状态。

## 嵌入与数据来源（2026-10-20）

20 的 Ollama 内部地址为 `http://ollama-embedding:11434`，宿主机仅发布 `127.0.0.1:11434`。模型为 Q8_0 的 `qwen3-embedding:0.6b`，模型文件 639,150,858 字节，manifest digest `ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d`。实际 `size_vram=0`，按 CPU 运行；模型文件大小不等于运行内存。

| 路径 | 实际数据来源 | 新集合与实测数量 |
| --- | --- | --- |
| ATT&CK | 上游内置精简技术集，本地没有完整 MITRE STIX 文件，CDN 下载未开启 | `attck_techniques_qwen06b_v1`，14 项 |
| 威胁情报 | 原有 1,748 条均为 `source=cisa-kev`、`tenant_id=shared`，来自 [CISA KEV 公开目录](https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json) 的采集路径 | `threatintel_iocs_qwen06b_v1`，1,748 条；actors 为 0 |
| 语义记忆 | 分析员录入、处置手册或案件关闭后产生的 `case/runbook/memory`；当前租户原本没有记录 | `aisoc_memory_qwen06b_v1`，合成验证后已清理，仍为 0 |

模型只对已有文本生成向量，不生成这些来源数据。没有自动导入全量 ATT&CK、私有知识或业务案件。ATT&CK 此次验证到入库及函数检索，不证明调查 Agent 已实际消费这些检索结果。

### 部署接线

[embedding/prepare.py](embedding/prepare.py) 校验三个上游文件的固定 SHA-256，再生成部署专用副本：API 语义记忆、Agents ATT&CK、Threatintel 存储。容器只读挂载这些副本及共享的 [本地嵌入调用模块](embedding/aisoc_local_embeddings.py)。`opensource/AiSOC` 与服务器原始源码均未覆盖；实际运行代码因此包含本部署的接线补丁，不能只用官方镜像 revision 描述。

三条路径都直接调用本地 `/api/embed`，使用原生 1024 维；拒绝零向量、非有限数值、维度或数量错误，失败不伪造结果。新模型使用新集合；旧集合保留。ATT&CK point ID 改为稳定 UUID。每次实际嵌入批次的输入/输出 hash、模型、token/耗时或错误记录在服务器 `deployment/embedding/calls/<service>/`；费用 unknown，不写为零。

首次真实检查发现两处阻塞，已定向修正：Qdrant 默认 1024 文件上限导致记忆集合创建失败，现为 65536；SDK 1.19.1 已移除上游调用的 `search`，两处检索改用现有 Qdrant HTTP `/points/search`。保留上游 Qdrant 1.7.0，当前实际使用的写入/读取/检索已测，不代表完整版本兼容验收。

### 证据与验证范围

- 三条文本的首次本地嵌入约 4.412 秒，均为 1024 维非零向量；中英文同主题余弦 0.914、无关主题 0.187。仅一个连通性样本，非检索质量评测。
- 旧情报向量抽查一条为全零。1,748 条公开记录全部重新向量化；新旧 point ID 相同、原集合所有 payload 核对不变。`original-iocs.json`、`data-sources.json`、`calls/threatintel/reindex-progress.json` 保存来源及完成证据。
- ATT&CK 函数检索返回 T1059 等技术条目；情报函数经 tenant/shared 过滤返回 CISA 记录。未宣称 CVE 编号精确命中或调查 RAG 质量通过。
- 经实际 HTTP `/memory/items` → `/memory/recall` 检索到标记为 `deployment-smoke` 的中文合成条目，再删除并清理唯一测试行/向量；PostgreSQL 记忆和新 memory 集合均回到 0。
- 首次失败证据保留在 `memory-smoke.first-failed.json`、`agents-retrieval.first-failed.log`；修复后的定向复验见 `memory-smoke.json`、`agents-retrieval.json`、`threatintel-retrieval.json`、`final-state.json`。以上路径均相对服务器 `deployment/embedding/`。
- 本地三项 MockTransport/数值边界合同检查通过；部署代码和生成模块 Ruff、语法检查通过。没有扩大为全仓回归或模型质量评测。

后续如更换模型或源版本，先审查固定 hash 和补丁，再重建新的模型集合；不要把不同模型的向量写入当前集合。下一项实际数据扩充需单独决定：获取完整 MITRE STIX，或导入真实手册/案件记忆；当前未开展。
