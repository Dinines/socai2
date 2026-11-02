# 参考研究回执

2026-11-02。用户明确只参考微软设计与AiSOC AI分析，不照搬/直接合并。本批追加页面分析第29节及顶部续接；第27—28节仍为讨论稿，不追认实施。

## 核对范围
在线读取微软5个官方页面，URL见第29.6节，区分Incident Case Preview、Legacy、Endpoint AIR调整，保留其适用边界。官方图片链接返回无可读图像内容，本轮依据正文和此前已确认视觉，不宣称做了新视觉复刻或像素检查。

只读核本地AiSOC HEAD 34ca18c5；CaseWorkspace.tsx与InvestigationLedger.tsx相对该HEAD无差异，核InvestigationPanel的Recon/Forensic/Response及报告入口、Ledger的Run/类型/执行者筛选。结合当前V2 overview/process/ledger和原保存数据边界，不据源码宣称20/21已接通。未读微软租户或访问20/21业务服务。

## 实际产物与验证
第29节6小节：参考取舍、六视图职责、发现回查、图谱与三种时间、下一步分类、来源与限制。保现有图谱/导航/数据，不填缺字段、证据引用或执行，不重新编排后端。实施前OpenSpec strict通过；6小节、2本地链接、5官方URL、顶部锚点核对通过；git diff --check及git diff --quiet HEAD -- prototypes/security-pages-v2 services均通过。结束独审和归档结果按实际补记。

无页面/后端/样例变更，无浏览器/业务测试、模型/调查/响应、部署、Git提交推送。

## 结束独审
未参与编写者current_workspace_review限定ACCEPT、0必须修。核第29节只作参考，未变为强制流程/后端改版；六视图、三栏图谱、历史/来源范围保持，分析限已保存结果和依据摘要，不含隐藏推理，建议/审批/执行/效果分开。AiSOC两个参考文件与34ca18c5一致，复核微软官方Incident Case和AIR说明支持适用边界。本地链接、锚点、diff-check通过，frontend/services未改；无浏览器、业务系统或模型操作。

## 归档结果
已使用`openspec archive compare-investigation-design-references --yes --skip-specs`归档到本目录，主规格未更新。封后all校核9通过、0失败，archived校核56通过、0失败；仅为文档结构核对，不表示页面或后端能力已实施。无Git提交推送。
