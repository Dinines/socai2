# 调查结果人工采用 HTTP

## Why
调查核心已经实现固定结果的预览、人工采用和判断历史；E21仍为501，业务后端无法使用。将已有核心通过独立HTTP边界交付，供用户选择调查当前判断。

## What Changes
- 实现E21，增加E63采用预览和E64判断历史读取。
- 复用核心资格、Case锁、预览摘要、未完工作确认和幂等回执；不复制另一套规则。
- E21旧预留体只有operation_key/expected_scope_revision，未曾成功执行。本次改为operation_key/expected_review_token/reason/acknowledge_pending_work，须先预览再提交。
- 同步本机/21服务、Swagger、功能清单及后端调用说明。其他61操作合同、告警字段及数据库结构保持。

## Capabilities
### New Capabilities
- `case-result-adoption-http`: 指定调查结果的预览、显式采用及判断历史。

## Impact
对外HTTP路由/合同入口/用例端口、已有CaseService采用核心、交接和发布配置。无模型调用、调度、消费者或文件上传变更。主调查质量和未完范围不由本项核销。
