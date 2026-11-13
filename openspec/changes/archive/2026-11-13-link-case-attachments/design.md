# Case附件引用

## 已确认职责与用户流程

业务后端先保存文件，获得稳定file_id，再调用调查服务登记到Case。目录/单项读取返回该file_id及元数据；业务后端据此提供下载或报告文件失效。调查服务不保存文件字节、下载URL、凭据或本机路径，不向文件服务发请求。不预建文件平台或占位下载接口。

## HTTP合同（实施目标）

- POST `/api/v1/socai2/cases/{case_id}/attachments`：operation_key UUID；非空file_id(1–512字符)、file_name(1–512)、mime_type(1–255)、size_bytes(0–9223372036854775807整数)及可选小写64位sha256。不接收作者、时间、URL或文件内容。
- GET同路径：limit默认20(1–100)、offset默认0(0–100000)，按created_at/id升序，返回items、total、next_offset、observed_at。
- GET `/api/v1/socai2/cases/{case_id}/attachments/{attachment_id}`：仅返回本案登记的单项引用。
- 单项返回id、case_id、file_id、file_name、mime_type、size_bytes、sha256、created_by、created_at，以及固定file_owner=`business_backend`和availability=`managed_by_backend`。大小/类型/哈希来自业务后端声明，本服务不独立核验文件内容或可下载性；availability不代表下载成功。
- 文字字段保留原值，拒绝空白和控制字符。file_name只用于显示。查询未知参数422；不存在Case/本案附件404；幂等意图冲突或同案同file_id重复登记409；参数不合法422。

## 保存与兼容

独立CaseAttachmentService复用Case事务/作者检查，锁Case后查本操作回执；同案同key同作者及元数据返回原结果，不再写入。不同key登记同file_id返回attachment_already_linked，先查目录获取已有记录；改变文件内容由业务后端分配新file_id。本批不实现修改/删除/版本替换。

artifacts使用kind=attachment、schema_version=socai2.case-attachment-reference.v1，blob_ref=`business-backend-file:`加原file_id；只绑定Case，run/step/alert/incident为空。它是受控逻辑引用键，不是URL。file_name/mime_type/size_bytes/sha256保存后端声明；created_by/captured_at取服务端。material_state=complete表达登记时后端声明的完整文件，文件实时可用性仍由后端判定。retention.original_*保留声明，retained_*为null、reason=business_backend_reference_only，不冒称本服务保存字节或核验哈希。

同一事务新增附件、增加Case row_version/business_updated_at、记录case_attachment_linked活动及Case目标；附件ID和完整登记值保存在该目标的operation_receipt.outcome，不新增activity_targets列。已结案案件可追加资料，状态保持。任务/Run/结果/当前判断/范围/证据目录均保持，不自动作为模型输入或已核实事实。旧Run工件读取按原合同保持；新目录仅列本schema的Case附件引用，不把报告/模型工件伪装成用户附件。

## 代码与发布来源

新增app/socai2/case_attachment_contracts.py和case_attachments.py；investigation_http/external_routes/attachments.py只接DTO、port和adapter。调查核心不导入HTTP包。原59操作/Schema保持。

本机ARM64从已发布case-comments冻结目录派生，21 AMD64从已核评论镜像派生，只叠加本change文件；运行参数放显式profile。其他服务和消费者保持，工作区并行模型修改不进入发布。回退切回前版服务/Swagger，保留已登记记录。

## 直接验收

定向输入/HTTP边界检查后，本机新合成Case：登记两份合成文件引用、目录分页、单项读取、同key重放/冲突、同file_id重复、非法大小/空白、错误Case/跨案读取；活动及独立SQL核对，任务/Run/判断保持。验证的是引用关联，不调用真实文件平台。21仅在本批明确合成Case执行同样存取，读回实际源码/配置及Swagger；未参与实现者结束审计后归档。已有评论和原59HTTP合同复用直接兼容检查。
