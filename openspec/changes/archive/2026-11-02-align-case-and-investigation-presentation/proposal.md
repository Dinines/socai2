# Why
用户发现来源材料内切换后外层折叠，随后要求修复前述多个问题并对齐设计：案件资料双模板、案件图与Run图职责重叠、Chain/Path入口隐藏。
# What Changes
统一所有Case案件资料模板与四项统计；案件图固定当前成员与对象关联，保留圆形三栏呈现，路径/候选留单Run；Run的Chain/Path/关联范围选择前置，来源材料展开状态在重绘时保留，切换材料不跳回页顶。
# Impact
仅本地V2前端/直接测试/交接；原材料、缺项、历史、导航、模型与业务状态保持，不改服务端、执行、部署或Git提交推送。原fix-investigation-source-material-disclosure在只有元信息且尚未实施时，按用户追加范围更名为本change。
