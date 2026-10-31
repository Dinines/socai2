# 2026-10-31 事件阶段覆盖与关联时间线布局回执

用户要求阶段/ATT&CK覆盖上移，告警时间线与关联依据一起呈现。已将覆盖条放在事件说明后、管理字段前，阶段及告警数紧凑排列；原比例大卡移除。信息按钮说明计数来源及非检测覆盖率/攻击成功。

关联卡左侧按发生时间展示最近6条告警及每条实际共同对象，右侧展示同一共享对象投影及对应成员展开。只有至少2个不同成员共用的对象会进入两侧；对象、告警来源按钮沿用。宽屏双栏、窄屏上下堆叠，图谱继续默认展开在后，Case流程不改。

本批只改investigation-workspace.js、investigation.css、index.html缓存及既有investigations.test.cjs断言；未改模型、源数据、后台或其他控制器。改前5文件（含备用未修改alert-flow测试）及hash在.local/versions/incident-coverage-before-20261031。

## 验证

- 语法检查通过，81项既有测试全部通过；仅更新旧概览布局/顺序断言，没有新增镜像实现式测试。
- IAB Office事件覆盖为执行2告警；合并卡2条时间线均与4个共享对象对应，时间最新在前。点击时间线共同主机DEMO-FIN-11，打开原始对象详情并列2条来源告警，未改资产匹配/库存事实。
- 完整演示262144展示8个既有阶段且各告警数保留，图仍默认展开。700px单列，文档clientWidth/scrollWidth均685，合并卡列宽551，无页面横溢出；随后已恢复默认窗口。
- 截图位于.local/verification/incident-coverage-20261031：coverage-wide、timeline-wide、timeline-narrow、design-coverage、combined-final。未重置浏览器、未创建测试Case/Run或改历史样例。
- 严格OpenSpec校验和git diff --check通过；本change仅呈现，skip_specs=true，不新增业务规格。

## 审计范围

仅本地4174展示，不代表后台创建/关联/调查能力交付。原阶段分类/共享ID/时间缺值/图谱/Case合同保持，历史版本和真实13Run不改。无模型、真实服务查询/业务写入、重放、部署、Git提交推送。

## 独立结束审计

未参与实现者current_workspace_review限定ACCEPT/0必须修。18事件概览、54条时间线记录及182个共享对象标签逐项匹配，阶段计数/排序/缺时间/原数据保持。3项定向测试、36图谱/告警链视图与19旧Case概览保持、5份历史hash通过；宽窄屏无明显问题。

## 归档

已按纯呈现变更归档为2026-10-31-elevate-incident-coverage-timeline，跳过业务规格同步。归档CLI有Why文字偏短的非阻断提示；最终严格校验当前9/9、历史归档47/47通过，git diff --check通过。无Git提交推送。
