# 新版独立服务部署与验收方案

依据用户2026-11-04最新要求：“持续推进到完成，做好验收”“不替代原版，单开服务即可”。本方案用于新增服务，既有API、r13调查、Fusion、agents和旧数据保持运行。

## 隔离安排

| 项 | 新版 | 原版保持 |
| --- | --- | --- |
| Compose项目/容器 | socai2-next / socai2-next-api | socai2-api-1、socai2-investigation-api、socai2-fusion-1、socai2-agents-1 |
| HTTP端口 | 127.0.0.1:18020 | 18000、18010 |
| 应用入口 | app.socai2_main，仅新表接口、必要auth和health | 不运行app.main及旧scheduler/consumer |
| PostgreSQL | 现有spirithub-postgres-1上的新库socai2_next_20261104，socai2 schema；独立受限角色 | aisoc/public不写；原schema_review验证库不改 |
| 公共支持表 | 依据现ORM创建空的完整身份/RBAC、资产、TI、UEBA及KB表；仅新增合成租户/用户/API key | 不复制旧业务记录/用户/凭据行，不扩旧fixture身份表 |
| ClickHouse | 同实例新库socai2_next_validation/raw_events，独立SELECT用户 | aisoc.raw_events及旧查询不改 |
| Redis | 同实例逻辑库13 | 当前已核8/9/10/11/12保持 |
| Kafka | 新API无消费者，broker配置不可连接；本次无需新topic | 旧topics、offset、consumer group保持 |
| AI问答 | 继续3条501预留入口 | 不新增Q执行 |

2026-11-04只读确认：旧主API镜像`sha256:5a1e1fd8...`，r13镜像`sha256:7ca0572275260ee96a677665e20d513b0ced6a58fcfdba1b13ca2c6922ac5093`；18020空闲。review库public.tenants只有id，users/connectors只有id和tenant_id，不能冒充可用身份系统，故另建独立库而不扩改测试夹具。

## 鉴权与配置

通过原 `get_current_user` 的真实API key路径校验数据库哈希、有效状态、所属用户及显式scopes。新增key绑定新合成用户，使用正常cases/alerts权限，不启用dev bypass，不以手造CurrentUser替代网络验收身份。写key和只读key仅在21的`/opt/sting-aisoc-socai2/private/next-20261104/identity.json`保留，目录0700、文件0600；脚本只输出租户/用户ID及统计，不导出凭据。

同库建全量users/tenants/api_keys，以及正常JWT权限读取需要的RBAC/条件/临时授权表，避免缺表异常导致事务abort。合成账户为key-only，密码登录不作为本批交付或验收承诺。API key路径会实际更新自己的last_used_at；数据库角色仅对该公共列有UPDATE权限，其他public表只读，socai2 schema按服务需要授DML。

模型仅在21进程内从现r13容器已配置环境白名单复用OPENAI/LLM连接配置；不改原容器、不导出Key、不读取旧租户BYOK行。新库tenant_llm_credentials为空，正常resolver使用环境基线。Secret/JWT/vault/realtime值为新随机值。PG沿用原机验证完整证书的端点和CA，只更换数据库与专用角色；CH使用新库专用只读身份。外部graph和产品host默认关闭，避免读旧业务图或厂商；本次只用新合成PG/CH材料验真实模型和查询链。

## 可执行步骤

1. 所有H/来源修改完成后，运行 [prepare_next_service.py](../../deploy/aisoc21/prepare_next_service.py) `--output .local/releases/next-20261104-<批次>`。脚本只本地打包，记录逐文件hash/大小/0644及基底镜像ID；新入口不存在则拒绝。包内无env/凭据。
2. 将固定tar和manifest上传至21独立release目录，核archive SHA256后安全解包。`next_service_remote.py inspect`核每个manifest文件及原基底镜像身份。任何当前源码变化须重建新候选，不覆盖原候选和失败回执。
3. `next_service_remote.py bootstrap`只创建新PG库/受限角色/必需空表/合成身份、新CH库及只读用户、私有env文件。原版容器ID/镜像/启动时间留基线；脚本拒绝非指定库操作。
4. `... build`使用已核r13依赖镜像，不从网络重新解析依赖，完全替换新镜像的/app/app。`... start`只启动socai2-next项目api，`... verify`核health、OpenAPI无旧业务路径及原版容器未变。Compose定义在[独立配置](../../deploy/aisoc21/compose.next-service.yml)。
5. 新服务真实HTTP验收：无鉴权401、只读key写403、读/写key正常；Fusion收到的合成材料持久化→A→I→Case→完整C→H反馈/后续C，核字段/来源引用、请求与原回复、真实查询、用量、范围变更和冻结历史。模型调用沿原Run限额；真实质量按明确预期判定，失败保留，不用放宽来源规则冒充通过。

本文件是部署方案与脚本说明，不是已部署/已通过真实验收的回执。实际创建/启动、候选与原版不变证明及真实验收由根任务另存固定批次；本次不提交、推送或替换原版。

## 本批已观察结果

根任务核具体方案后，已授权仅执行bootstrap。固定候选`next-20261104-bootstrap-a1`共551个清单文件（544个app文件，另有manifest），tar SHA256 `2235d5b06d3da6b5c64ddd710cda184fde3154402f5ea8b7e19c7ae59648e2ad`。上传后按SHA及逐文件清单验证、安全解包；首次bootstrap全部成功，见[原始回执](evidence/socai2-next-service-20261104/20261104T045208/receipt.json)。

新PG库17张public支持表和29张socai2表/459列已建；新CH库/raw_events及只读用户已建；独立私有身份/env已保存。合成tenant为`deefcfa8-dc3c-512d-849b-508d911f307c`，user为`22155cc9-c340-59ba-99ff-b4d811837626`。旧四容器ID/镜像/启动时间保持。未运行build/start、未触发模型或CH业务查询；这不是服务上线或真实质量通过。

H/来源仍在并行实现，bootstrap候选不能直接作为最终应用候选。最终应另建release目录和manifest，重核当前代码后构建/启动；已建立的空间和身份可复用，不复制旧数据。三个发布辅助脚本Ruff通过，初prepare脚本导入格式检查已修正，不影响所建DDL。
