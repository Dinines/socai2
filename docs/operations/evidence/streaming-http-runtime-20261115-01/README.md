# 21候选HTTP与Swagger空态接入

2026-11-15。本批承接第11步候选资源供给，在21启动两个独立候选容器。默认内部可信，无登录、Token或角色校验。实际业务成功写入、非空记录、Kafka/真实模型整链及结束审计仍待，不计本change最终验收通过。

| 项目 | 实际结果 |
| --- | --- |
| API | `http://192.168.1.21:18424`，`streaming-http-20261115-r2`，80个业务操作 |
| Swagger | `http://192.168.1.21:18480/`，告警/事件/调查三类；Schema及HTTP输入输出合同与实际API一致，说明和隔离样例单独保留 |
| HTTP镜像 | `sha256:35d4021c6a1b31a57161e8cadd6a5bc004152648cbcb12e7aa1b0c140b3842f8`，linux/amd64 |
| 数据库 | `socai2_streaming_20261115`，调查方完成123–129、32表521列及tenant/actor，见[供给回执](../streaming-candidate-20261115-01/database-prepare-01.json) |
| 连接 | 普通reader/writer使用同一库，实际TLSv1.3；无superuser/bypass/角色或数据库创建权限，真实应用连接池未覆盖依赖 |
| 业务空态 | 无Authorization对告警、事件、Case列表的3次TCP GET均200，items为空、total为0、next_cursor为空 |
| 写边界 | writer执行零行UPDATE后ROLLBACK，5张相关表前后均0；没有提交业务数据，不称成功业务HTTP写入 |
| 其他服务 | 旧9个业务容器仍主动停止；其余29个运行容器的ID、镜像、启动时间保持 |

## 执行与读回

1. [preflight-02](preflight-02.json)：核两端口空闲、固定基镜像/架构和网络、受控文件0600、同库普通密码连接及9个旧容器仍停止。凭据不入证据。
2. [prepare](prepare-01.json)：传输并核r2原tar摘要`5c48c5ef2018e17da5508cc9e0e1f66d738c75aa2310c1d512785d50effcbb54`、manifest摘要`2f7bcf811fc1e19472f044366a0d13667e80517fc44a03cca1d40d0c93c9330c`；只使用显式私密文件及当前配置，不继承旧环境。完整来源723文件与工作树一致。
3. [build](build-01.json)、[start](start-01.json)：使用已核AMD64依赖镜像离线构建，只新增候选HTTP；实际ready及完整OpenAPI通过，80操作、无security、版本一致。
4. [双池连接](connection-01.json)：在候选容器中运行[直接检查](connection_readback.py)，使用实际应用lifespan/reader engine/writer session，不添加测试替身。探针为同容器独立进程，不冒充服务主进程的某条已借出连接。核普通身份、TLS、上下文、零行更新回滚及前后5表空态。
5. [TCP空列表](empty-reads-01.json)：21主机经真实192.168.1.21:18424访问三类列表，无Authorization；响应正文完整保留。
6. [Swagger](swagger-01.json)：独立18480启动，首页及manifest/swagger-config/OpenAPI全部200、文件摘要一致；展示说明明确已接入、成功写入待验及旧18024/18080主动停止。
7. [最终读回](final-readback-01.json)：实际API完整合同与冻结源一致，Swagger的Schema、请求/响应合同一致（只增加展示分类/说明和已标明的历史隔离样例），80操作/三类/目标地址一致；核旧9容器仍停止及其余29运行容器保持。随后向调查释放容器变更窗口，向测试提供W2实际目标。

本批没有投放Kafka、调用模型、创建Case/task/Run/Result，没有操作本机旧服务、恢复21旧容器或提交/推送Git。Swagger示例ID来自此前隔离保存记录，不是候选库对象。

文档收口时OpenSpec strict及受影响文件的diff空白检查通过；[文档核对](documentation-check.json)确认723个冻结来源摘要保持、42个本地链接有效、仓库三份Swagger文件与21实际返回摘要一致。本轮没有修改业务代码或重跑原本机业务批次。

## 原失败与后续

`preflight-01.stderr.txt`保留最初只读检查脚本误把暂停回执中的布尔值`selected_stopped`当作名字列表的TypeError；此前端口/镜像/受控文件检查已运行，没有服务或业务变更。改为读取`groups[].names`后，新preflight-02通过；不把原失败覆盖为成功。

成功写读并入测试S01正常Kafka→真实A/I→首次整事件建案；调查统一安排受理读回和Case调度开始的观察点。HTTP沿同一真实Case核initial task、同key重放、一次管理修改/保存读回，再让原task进入同批整链。当前空库连接和GET成功不代替这一步，也不计W2非空流程全部通过。
