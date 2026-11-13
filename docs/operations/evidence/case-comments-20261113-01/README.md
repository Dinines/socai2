# Case评论验收证据

本批只交付普通评论提交及分页读取，不调用模型、不改变任务/调查/采用。实施状态见[本批验收](../../../../openspec/changes/archive/2026-11-13-add-case-comments/validation.md)。

- `before-openapi.json`：原57操作；`candidate-openapi.json`：新增两评论操作，原合同保持。
- `offline-check.json`、`docs-check.json`：离线范围与合成示例校验。
- `candidate/`：本机新合成Case的真实HTTP输入输出、记录身份及SQL；不覆盖前批。
- `local-source-manifest.json`：本批冻结8文件及已发布基底。

`local-http/`为正式本机只读复验，`21-http/`为本批生产合成Case的HTTP/SQL。`21-runtime.json`与两端Swagger回执核对真实源码/版本/其他服务；`delivery-summary.json`汇总已通过范围。初次docker cp拒绝的原空输出和失败说明保留。凭据及可执行私密配置不在本目录。
