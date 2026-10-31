# Design
事件关系图使用显式incident范围，renderer强制associated/blast=false，旧UI状态不能扩范围或带入潜在路径；Case调用仍沿原控制器。保留关联分析主导航，仅在其中展示关系图；移除概览“有哪些关系”重复图，取消graph/chain子切换，旧/chain及view=chain兼容单一关系图。移除已无入口的事件候选链renderer/seed事件处理，保Case/Run调查图和模型原件。
无Case的incident-case按钮默认new，事件名称预填、全部成员并集加入；复用已有创建/关联、来源限制、重复创建检查和本地保存跳转，不创建Run。已有Case直接进入或多项选择，保留原成员关系。
保存改前文件，更新必要直接测试，核宽窄屏/无Case表单/Case历史图；结束独审后归档。

资产仅改名称，保留主机/对象取值与计数。首卡复用incidentHandlingStatus归一结果，只统计In progress；默认新建/已解决/未知不计入，不受Run完成度影响。追加校验状态计数与文案，不重跑已通过的图谱独审矩阵。
