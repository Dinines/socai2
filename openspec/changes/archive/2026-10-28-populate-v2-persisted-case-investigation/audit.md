# 结束独审与交付

日期2026-10-28；范围仅V2历史实际Case投影及展示。来源/字段见[功能分析第15节](../../../../docs/design/incident-investigation-page-analysis.md#15-2026-10-28-已持久化-case-的联合调查样例)，直接与浏览器核验见[验证回执](../../../../docs/design/frontend-v2-verification.md)。

未参与实现者`functional_analysis_save_review`独立核16来源hash与重建一致、29条Agent audit对持久events逐序/载荷全等、4工件hash及报告一致；36测试及语法通过。发现P2：全部成员移走后真实Case历史Run消失。修复为按源Case ID/tenant/environment保留所属Run并统一目录、概览、历史及列表计数；原事件和本地Case仍沿原成员规则。

修后独审7项窄回归全部通过，结论限定ACCEPT、0剩余必须修。主代理最终36项通过，并用浏览器确认链候选/路径/可达范围/四阶段；当前页console error为空。测试输入真实执行不等于真实攻击，completed不证明完整性，dry_run建议不等于执行；保留8小时时间差异。无模型/业务请求/后端改动/部署/Git提交或推送。

已归档为2026-10-28-populate-v2-persisted-case-investigation，主规格增加1条要求；封后strict all 8/8、archived 30/30通过。git diff --check无错误，V1/冻结交接/原data与workspace-model无新增差异。
