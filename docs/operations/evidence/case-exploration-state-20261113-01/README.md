# 案件探索保存恢复验收

本机真实 PostgreSQL `v12_upgrade_dev`，冻结候选服务18026；独立合成Case `c107b9a2-3634-5ef9-a0de-9a5fae31f7aa`。0模型调用、0生产业务写入。完整输入/输出保留在 seed、verify、continuation 回执。

27次功能HTTP通过，另2次新建合成Case。保存/恢复、继续、撤销、幂等、并发冲突、底图指纹冲突、错误对象/来源/悬空分支/重复输入、缺记录均验证。`sql-before.json` 与 `sql-after-save.json` 中7张业务表相同；只新增探索快照和活动。两次程序构造调查证明：新调查完成不改变旧保存；新调查缺图明确unavailable；显式旧Run仍能读取原图，继续保存固定旧图。

初次测试中，前20次HTTP已成功，随后合成图准备误在发布后尝试修改只追加Results，数据库拒绝并回滚该图事务。原Result、Run和失败均保留，未禁用约束或删除记录。修改验收脚本为发布前登记图、Publication显式关联后，仅继续7次历史底图HTTP，见continuation-http.json。此失败属于测试材料构造，不是业务保存接口成功的替代证据。CLI首次边界检查缺少新JsonValue schema白名单导致1失败2通过，补新schema白名单后3通过；旧66操作及138schema实际保持。

最终冻结、独立审计与两端发布读回尚待补齐；本地功能完成不代表已发布21。AI对话和模型质量仍未完成。
