# Why

F24-01要求同案协作评论的提交和阅读，目前仅有表和告警／事件只读入口。结果采用及任务调度由调查模块继续推进，本change独立完成Case评论，避免重复实现调查流程。

# What Changes

- 新增Case评论POST与GET列表；保存作者、原文、时间，支持幂等重试和分页。
- 复用comments、Case更新时间及活动记录，不建表，不改告警/事件HTTP合同。
- 对齐功能清单、Swagger及交接，直接验证后独审，统一发布本机和21。
- 不实现编辑/删除、附件上传或引用、模型输入、任务调度及结果采用；附件继续按业务后端保存文件的方向另行对接。

# Capabilities

## New Capabilities
- `case-comments`: 同案普通评论提交及读取。

## Modified Capabilities
无。

# Impact

关联主调查任务3.12及HTTP实施计划批次3。本文件为目标合同，尚非交付事实。对外HTTP适配与核心评论用例分开；基于已发布grouping-summary版本叠加本批文件，保留并行模型工作。
