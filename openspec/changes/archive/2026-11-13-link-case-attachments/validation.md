# Case附件引用验收

2026-11-13，限定F24-02/03中调查服务负责的文件关联及元数据，不验业务后端文件上传/下载，不触发模型、采用或任务调度。

## 实际实现与来源

E60 POST附件登记、E61 GET分页目录、E62 GET单项信息；文件所有权固定为business_backend，availability=managed_by_backend不表示文件被探测为存在。原59操作及Schema保持；新3DTO、8个源文件，零迁移/新表。外部路由经port/adapter接独立核心用例，未改并行模型源码。

6项定向检查及Ruff通过；OpenSpec首次delta标题层级错误已修正，strict在实施前通过。初始两个导入格式问题已修正。逐项回执见[批次目录](../../../../docs/operations/evidence/case-attachments-20261113-01/README.md)。

## 直接HTTP与保存

- 本机修后candidate-03：25次真实TCP，新建明确合成的两个Case、一项未完任务及两份文件引用。保存后原file_id/文件元数据、登记人/时间均保持；同key重放、意图冲突、同file_id重复、负字节数/空白、分页、单项、跨案404和未知参数均按合同返回。
- 独立SQL读取2附件、2活动/2 Case目标，回执outcome与HTTP全部字段一致；两案有2个pending_update Run、一项not_started任务/修订、0结果。主Case只增加两次行版本和业务更新时间，范围/判断/其他业务字段保持。
- 本机正式18024发布后8次GET读取同一批次，不重复登记；正式SQL与候选SQL相同。
- 21正式发布后26次真实HTTP，独立新Case为`c1c9c7bb-2da6-5d17-aa7f-e83761063c66`；同样2附件/2活动/2目标，HTTP与SQL一致，任务/Run/判断保持。通过容器标准输入执行只读SQL脚本，保持容器只读根文件系统。

全部file_id均标为SYNTHETIC，只证明引用关联存取。没有调用文件平台或核验实际文件字节，不能把本批写成上传/下载通过。已结案补充资料由实现审查覆盖，没有另走该分支TCP验收。

## 失败与修复

首次candidate在登记活动时使用了activity_targets不存在的artifact_id列，事务失败。旧驱动随后解析非JSON响应失败，原HTTP错误正文未完整捕获；保留请求意图、此前响应、实际CompileError及独立rollback-check：0附件/0登记活动、Case原值不变。修复为只记录Case活动目标，附件ID和元数据保存在既有operation_receipt.outcome，不新增迁移。首批不重派、不追认通过。

候选重启第一次因旧进程退出期间端口尚未释放而启动失败；再次启动后candidate-02过早GET OpenAPI得到非JSON错误，驱动取info失败，未发业务写请求。原输出与失败说明保留，随后明确检查readyz及实际版本成功后才用新candidate-03验收。驱动已支持保存非JSON错误，正式两端未发生此问题。

## 两端发布与交接

两端独立API为case-attachments-20261113-r1（本机带-local），62操作。本机ARM64原生Python，数据库v12_upgrade_dev，PID80726，冻结源码从前版评论目录派生；21 AMD64、aisoc，镜像sha256:d0bb509983c04ba1e322f374f0d31dc23c8cd443a5193671097a8f0ff4fd8566，只叠加本批8文件。实际加载摘要/配置已读回，其他36容器身份/镜像/启动时间保持。

Swagger docs12两端9入口200、8个handoff载荷与仓库/已审候选逐字节相同；62操作/59已实现/3预留、135Schema、613固定输出字段位置、28动态结构、125功能和CSV104列。新增输出位置37=登记11+分页封套4/items11+单项11。532响应示例通过，新DTO/参数/请求体与实际OpenAPI一致，摘要`1a05526f7daf24b11fcb09ff2b97d8a48cf25cac21c8dd9cee2eeb60a693e735`。

原README、功能清单、交接/联调、表职责和HTTP实施计划同步；本服务关联已完成，文件平台归业务后端，采用/助手/故事/探索等范围保持各自状态。[汇总回执](../../../../docs/operations/evidence/case-attachments-20261113-01/delivery-summary.json)，独立审计见[audit](audit.md)。归档/Git及父项目同步按实际后续回执，不在此提前声明完成。
