# Why

F24-02/03的Case补充资料目前没有文件关联和目录接口。2026-11-13负责人确认：业务后端负责上传、保存和下载文件，调查服务只保存案件与文件的关联和元数据。本change承接HTTP实施计划第三批，不接管调查采用、模型或自动调度。

# What Changes

- 新增Case附件登记、分页目录和单项信息读取；输入是业务后端已保存文件的ID、名称、类型、字节数及可选哈希。
- 复用artifacts的attachment类别和blob_ref，不新增表或迁移；记录登记人、时间及活动，保持任务、Run、案件判断和证据目录。
- 对外路由通过独立用例端口调用，不调用文件平台或调查内部HTTP；返回file_id，由业务后端执行下载。
- 完成直接存取、独立审计、两端服务/Swagger和交接。上传/下载的实际业务后端实现不在本仓库验收范围。

# Capabilities

## New Capabilities
- `case-attachment-references`: Case附件引用的登记、目录和按ID读取。

## Modified Capabilities

无。原59操作和告警交接字段保持。

# Impact

新增独立核心用例/DTO及HTTP适配；仅写artifacts、Case管理时间/版本和活动。直接验收使用明确标记的合成文件ID，不将引用保存冒称文件上传或下载通过。范围属于主调查3.12的独立HTTP交付，不核销主调查整体任务。
