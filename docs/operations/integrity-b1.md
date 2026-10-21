# B1 告警融合入口合同限定验收

2026-10-21。对应`restore-alert-investigation-integrity`任务2.4/I3。实现fusion_review，源码/部署准备/运行结束独审api_auth_review，定向部署及真实验收root。结论：**Fusion HTTP/Kafka入口一致性在本批范围通过**；不等于整体迁移完成。

## 实际改变

`POST /process`与Kafka共用原C01完整处理接缝：canonical身份→首次快照恢复→PG确认→消息确认，保持FusedAlert响应。HTTP在写任何处理状态前校验主体与body tenant，持久/交付未确认显式503；不再让旧HTTP只写共享dedup而没有完整持久结果。重复HTTP返回冻结的首次结果，保留incident及材料。

Agents Fusion工具已补服务凭据需要的tenant声明头，原Bearer/JSON合同保持；其源码探针通过，运行发布随组合Agents候选，不伪称本次已更新Agents。

## 输入、调用与最终事实

- 119项断网直接测试通过（新5、原HTTP7、C01保护107），0失败/跳过；使用实际模块和明确PG/Redis/Kafka边界替身，涵盖两种身份版本、两入口顺序和跨tenant写前拒绝。
- 21真实HTTP共10次。两条新source-v1测试告警分别为`f8f905ff-e75f-5e07-ad8e-4ee0927c3f5c`、`0c3942b6-99de-556a-ad0f-0ade3842e839`，只用既有A/B测试tenant。
- 第一条HTTP→API raw发布→Fusion/Kafka；再次HTTP提交变化的正文，完整响应仍逐字等于第一次冻结结果。第二条API raw→Fusion/PG→HTTP，canonical ID一致，API所读正文/分数/时间保持。
- 两次真实raw发布位于`socai2.alerts.raw`分区2、offset41/42；跨tenant403，无效凭据401。模型调用0，Agents worker仍OFF，未重调旧unknown或积压。

## 部署与来源

只构建并替换Fusion一次：父`a8825d41…`（C01）→`c52b9aacf4099a2ace30673c7d7b3ca9bcd933c1a22af5e20a38000494441018`，保持C01父层，只覆盖router/consumer两文件。使用完整28层加`compose.integrity.yml`，其他托管容器ID保持，未重启基础设施。

原Fusion没有HTTP身份材料，本批在私有`completion-integrity-20261021/fusion-auth.env`复用API JWT验证secret并配置独立Fusion service token，恢复原支持的两种身份形状；值不入源码/镜像/公开回执。其他原env与挂载保持。仅核本批`/process`认证，旧ML等接口未据此补写实测结论。

机器结果与源码摘要见[JSON](integrity-b1.json)。私有原始请求/构建/回退快照在21`private/completion-integrity-20261021/b1-*`，断网测试在`b1-test/test-01*`；原C01回执不改写。原操作key仍按本批后续验收使用，完成收尾后撤销；旧十reader凭据保持。

## 限制与下一项

真实legacy版本不重复验；两版本直接合同测试已复用。可用性/停止恢复专项、原playbook/反馈额外改测继续后置。下一项是B2/B3/I2组合候选的实际Case调查、知识消费和报告验收，尚未据本回执认定自动调查或质量通过。
