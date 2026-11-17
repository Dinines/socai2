# HTTP PG普通密码配置与r2离线包

2026-11-15。状态：**本机配置/完整包直接验证通过，实际21运行未就绪**。按负责人最新要求去掉PG客户端CA/证书前置；只填地址、端口、库名、用户名和密码，默认require传输模式由模板提供。Kafka TLS及其他组件不在本轮修改范围。

## 本轮修改

- `manage.py prepare`从选定受控文件读取两条普通账号密码URL，核同一候选host/port/database及非空账号密码；未填SSL模式时用profile的 `postgres_sslmode=require` 补齐，保留已编码密码，不继承参考容器环境/挂载。
- 最新profile移除PGSSLROOTCERT、`runtime_mounts=[]`，无CA路径或摘要待填。私密连接仍需实际供给；[空模板](../../../../deploy/http-service/streaming-20261115-01/runtime-environment.example.json)不可直接运行。
- 调查模块提供同版 `app/db/database.py`：asyncpg require使用明确CERT_NONE/check_hostname=false的TLS上下文；HTTP读连接与Case写连接共用此归一化。HTTP没有另外复制连接实现。
- [当前HTTP配置与步骤](../../../../deploy/http-service/README.md)、[逐字段/四类配置字典](../../../../deploy/http-service/CONFIGURATION.md)、[Swagger](../../../../deploy/api-docs/README.md)已同步r2。PG证书要求不再作为部署前置；变更前文档保存在本目录before文件，r1包及原测试回执未改写。

## 验证和交付

| 项目 | 实际结果 |
| --- | --- |
| 部署入口直接检查 | [13项通过](direct-tests.txt)：普通无CA读写连接→prepare→私密env/Compose读回，缺真实文件/账号密码/目标不匹配拒绝，密码编码保持；原完整包/合同校验覆盖保留 |
| 核心同版 | 663共同app文件与processing-20261115-r2公开manifest一致；HTTP冻结43 py/json源码保持 |
| 完整候选 | 723来源/726 manifest文件，app671+HTTP44（含README）+配置/合同/元数据8；包含3个HTTP所需SQL |
| 解包实际导入 | [offline-01.json](offline-01.json)：165模块全部来自新包，80业务操作/无鉴权合同保持，9类策略和当前A/I/Case合同正常加载 |
| 读写连接参数 | 实际读引擎及实际Case写引擎均收到CERT_NONE且不校验主机名的SSLContext；故意设置无效PGSSLROOTCERT仍能装配。未连接数据库，因此不冒称实际TLS握手或业务保存通过 |
| Swagger | 同版发行号streaming-http-20261115-r2、80操作，除info/servers展示外合同保持；Compose离线解析通过，未启动文档容器 |
| 质量检查 | Ruff、OpenSpec strict及文档字段/链接检查通过；不新增全仓回归或模型测试 |

当前包：`.local/http-candidate/streaming-pg-password-20261115-01/package-01.tar`，SHA-256 `5c48c5ef2018e17da5508cc9e0e1f66d738c75aa2310c1d512785d50effcbb54`；对应公开[profile](../../../../deploy/http-service/streaming-20261115-01/profile.json)与[供给状态](../../../../deploy/http-service/streaming-20261115-01/requirements.json)。旧r1 hash只代表调整前产物，不能标成当前包。

本轮新建业务记录0、数据库连接0、模型调用0、Kafka操作0、启动/重启服务0、Git操作0。真实候选DB/迁移/tenant/actor与读写凭据、HTTP AMD64镜像及TCP流程仍待；后续按第11步统一候选验证，正式18024/18080保持。

## 后续独立连接证据（不改写本批离线计数）

测试侧随后完成[21普通reader require/TLS1.3无CA连接与本机真实HTTP两池/回滚](../pg-password-connection-20261115-01/README.md)。HTTP侧只读取回执并核三份受测源码与当前r2包摘要一致，未执行新的连接或写入。21读连接及本机disable写连接分别成立；不能拼成21候选TLS写入、真实18424端口或业务提交已验。核对记录见[connection-evidence-alignment.json](connection-evidence-alignment.json)。
