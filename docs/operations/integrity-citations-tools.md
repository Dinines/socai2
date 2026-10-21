# 调查引用格式与原只读工具身份接入

2026-10-21，沿当前OpenSpec的B2/B3接缝修复。candidate04已完成源码、部署及运行独立审计。此处解决来源记录和认证接入，不重新判定旧模型结论，也不代表自动调查已验。

## 问题、修改与验证

人工调查R01实际输出裸`KB1`和`(KB1)`，原parser只识别`[KB1]`，造成持久引用计数为0。仅扩展一个正则及说明：支持独立完整标记，拒绝`fooKB1`、`KB1_extra`、`KB1000`等部分匹配；未知编号仍不能映射到未供给来源。采用R01原可见句及对应来源作纯函数验证，未回填或重发旧Run。7项新增与既有知识测试共32项通过（1.80秒，断网、只读源码、0模型），日志SHA `94702e010bda8ba3f5acfecabbd403a7ead993263438042e64517ee753135150`。不把解析出引用当作相邻结论得到语义支持。

正常deep工具另缺API服务身份，原API→Agents专用身份不能替用。按固定源码已有的可信服务主体配置独立`AISOC_API_SERVICE_TOKEN`，同时供API和Agents；权限固定为七项只读权限，请求必须明确存在的tenant，工具闭包取Run的tenant。没有新增API、工具或授权模型参数，也没有借用操作key。私有位置见[配置索引](configuration.md#2026-10-21调查工具原只读服务身份)，值不入文档/Git/日志；原专用身份与十枚A/B reader保持。

部署后实际六项HTTP：合法C读取告警200（0条）、缺tenant403、不存在tenant403、错token401、缺执行权限的dry-run请求403、只读工具backend入口200。后者registry可达，但vendor/siem均0，不能写成日志/厂商资料已有；缺源继续unknown/unavailable。没有模型、消息或业务写。

## 运行来源与边界

- [candidate03运行审计](../handoff/integrity-candidate03-runtime.json)保留原B4/B5/报告/技能pin修复及原生PDF依赖，去重组合383项；candidate04的32项属于此单处差异验证，不与383简单相加宣称唯一用例数。
- [candidate04源码](../handoff/integrity-candidate04-source-manifest.json)及[运行审计](../handoff/integrity-candidate04-runtime.json)：772运行Python和1个lock全部匹配；相对candidate03仅`knowledge_base.py`一处变化、0删除。Agents为`c311a94b…`，完整保留`9ac2bb3e…`父层；API镜像`1be37c38…`保持，仅API/Agents容器替换，Fusion/Actions及其他容器保持。
- 两服务环境唯一新增上述只读身份；原七只读挂载、60秒停止宽限、2048 completion配置和关闭开关保持。运行仍原28层加integrity共29层，Compose SHA `9ee7731b2fe3c53592b03908d48c6e798a133cce876f6f89058814e072560121`。
- [六项HTTP摘要](../handoff/integrity-candidate04-http.json)与部署前脚本/部署后审计均由未参与实现者核对。构建及部署各一次，0模型/新业务消息；常驻worker OFF、review_only、自动graph及审批关闭。

另建的新C隔离租户五类reader已通过11项HTTP（5成功空结果、5跨tenant403、1错scope403）。六枚短期key供下一有限自动验收使用，结束须撤销并核401；不更改A/B额度、unknown或积压。本回执该批结束时尚无C告警/模型。下一沿原worker和原关闭策略分别验自动关闭与自动升级调查；此回执不勾最终迁移完成。
