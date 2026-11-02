# 案件探索入口与历史材料分离回执

2026-11-02。仅本地V2呈现、原标签刷新和交接；不改关系生成/扩展算法、成员、草案或Run持久逻辑，不调用真实服务/模型、部署或Git提交推送。其他未提交工作及用户aaa。txt保持。

## 发现及修正

用户两张截图分别为AiSOC20-3和socai2财务Case，均显示旧“查看当前成员告警与对象”成员图。主代理最初只验证新开的socai2页，误以为遗漏来源分支；随后直接读用户原标签5确认旧版，与新开同地址不同，原URLreload后探索出现。无当前源码来源分支缺陷，不重复改路由或另造探索器。

案件图确实仍有历史来源折叠及当时未关联Case提示，本批caseSnapshot模式撤这组材料和Path状态，保来源Run/时间/完整性、节点关联证据、上下文身份及对应Run链接；Run原材料/状态保留。Case技术缺归属提示不再指向已移除的下方材料。index资源版本r3。

改前investigation-workspace.js、investigation-graph.js、index.html、tests/case-reading.test.cjs、tests/case-exploration.test.cjs共5文件在.local/versions/case-graph-entry-before-20261102/。

## 验证

- 实施前strict规格校验通过；npm run check通过；探索/Case阅读/调查3文件46项相关检查全通过，日志/tmp/case-graph-entry-tests.log。新增2项核23Case移除材料且Run可查，两反馈Case实体扩展/草案表单无写入。旧缺图断言改核准确的上下文说明。
- CUA原用户标签5刷新后，选择demo.finance显示以此节点扩展/选入调查草案，扩展找到Office隐藏PowerShell，保留此阅读状态；未保存探索/草案、未启动Run或重置。截图.local/versions/case-graph-entry-current-tab-20261102.png显示原标签窄屏详情及候选。
- 背景标签26核local-aisoc20-3，demo.export显示扩展入口并找到归档上传字节候选，点击查看本次调查进入原c142792a-b1a0-5d5c-9a64-4a89db4d6b67，历史跳过状态/来源材料保持且无探索按钮。
- git diff --check通过，10源/模型文件、后端和V1无diff；原真实数据/历史/用户本地编辑保持。

## 未参与实现者结束审阅

current_workspace_review代码结论限定ACCEPT/0必须修；独立3/3定向通过，另以改前renderer双VM比较全部21个全局Run图谱HTML逐字一致。最终第41节/交接及原标签截图补核同为限定ACCEPT、0必须修，可按流程归档。未重复全量测试。

## 归档及封后

已归档为2026-11-02-align-case-graph-exploration-entry，主规格修改1项；all9/9、archived68/68严格校验通过。无提交推送或服务重启。
