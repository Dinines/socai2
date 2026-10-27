# 告警主表列适配回执

2026-10-24；分支 codex/security-pages-replica。仅主告警表局部改动，无后端/真实服务/模型/部署/Git提交。

## 直接验证

- npm run check 通过。
- 浏览器10项观察：9列主表与列设置、时间升降序、08:40–09:00为5条、叠加进行中为2条、实际下载CSV为9列2行且UTC时间一致、事件及Case内嵌告警表仍12列、无浏览器错误。
- 直接材料：.local/verification/security-pages-replica/alert-table-columns.json 和同名 png；公开摘要见 docs/design/security-pages-replica-verification.md。
- 时间演示由旧 Mock first 投影至 event_time；未定义或接入真实后端回退。

## 未参与实现者窄审

prototype_end_review 只读审查并做本地 Node VM 核验，结论 **限定 ACCEPT，0项必须修**。特意构造 event_time 与 first 不同的输入，确认主表排序、日期筛选和CSV均采用 event_time；原数据未被投影改写，内嵌表仍用 first，详情保持。

仅覆盖本次列适配；不重新认定完整原型或生产能力。归档前 OpenSpec strict 与 diff 空白检查通过。

## 归档

已归档为 2026-10-24-adapt-alert-table-columns，主规格同步1项修改；封后 security-reference-ui-prototype strict 通过。
