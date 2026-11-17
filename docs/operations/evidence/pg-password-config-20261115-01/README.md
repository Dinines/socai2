# PostgreSQL普通密码连接配置修复

2026-11-15，负责人明确应用部署仅需数据库地址/端口/库名/用户名/密码，取消CA、客户端证书和私钥配置要求。已更新同一OpenSpec设计及规格，当前目标统一使用require保留服务器TLS，不做客户端证书身份校验；Kafka TLS保持。

## 修改与直接验证

- 处理profile删除ca_file/ca_mount，生成runtime/ingress环境、处理容器挂载及入站子进程不再要求PGSSLROOTCERT/SSL_CERT_FILE。当前模板、候选identity和A/I/Case调度统一require。
- PG安装模板使用密码文件与require，安装器不接受旧PGSSLROOTCERT且不继承父环境的PG证书变量；新装/增量SQL不变，无DDL变化。
- HTTP和Case写池共用app/db/database.py：asyncpg require使用明确SSLContext，CERT_NONE/check_hostname=false，不读取旧CA配置；psycopg沿显式require。HTTP prepare只需普通连接身份和密码，见[HTTPr2回执](../streaming-http-pg-password-20261115-01/README.md)。
- [根直接检查](direct-03.txt)36 passed、3 skipped。跳过的是既有数据库新装/授权测试，未提供其专用profile，本次未修改SQL。首次命令缺PYTHONPATH在收集前失败；[第二次](direct-02.txt)34通过、2失败、3跳过，定位到旧测试仍找已退役路由变量，随后改用现行HTTP adapter，原失败保留，没有修改业务实现掩盖断言。
- HTTP13项配置/完整包检查、80操作合同、实际读写引擎参数装配通过；未启21候选HTTP。Ruff与OpenSpec strict通过。

## 独立真实连接证据

[测试会话回执](../pg-password-connection-20261115-01/README.md)验证两种明确环境：

1. 21现有普通socai2_prod_reader通过真实TCP require连接，0CA、无客户端证书/私钥，TLS1.3；旧PGSSLROOTCERT指向不存在文件仍不依赖它。正确密码成功，错误密码28P01拒绝；只读、非superuser、无业务写入，临时SSH转发已停止。
2. 本机28413原隔离PG不支持TLS。已提供[新普通LOGIN writer](local-writer-preparation.json)，不修改旧角色/HBA。该账号真实HTTP两池以密码登录，无SET ROLE；对已存在F5 Case在事务内写/读后回滚，前后完整行及两次ASGI管理GET摘要一致，错误密码被拒绝。此段为disable传输，不能外推为require写入验收。

无新Case、Run、模型调用或Kafka投递；没有修改21数据库认证或正式服务。真实候选同库的require写入及18424 TCP仍随第11步实际资源供给验证。

## 候选与文档

[处理r2](../streaming-candidate-20261115-01/README.md)已重新冻结并构建21独立镜像，733运行文件核验/无网络自检通过；HTTPr2完整包与663共享app文件一致，尚未构建或启动21 HTTP候选。r1原件保持为调整前证据。

[部署总入口](../../../../deploy/README.md)及[数据库说明](../../deployment-datastores.md)已区分部署必填、保留默认、启用时必填、程序生成；当前应用无PG证书要求。旧正式profile仍按历史实际记录，不改写成已发布新配置。
