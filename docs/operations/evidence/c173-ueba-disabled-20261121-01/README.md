# 21 独立 UEBA 实例停用

2026-11-21，按负责人要求停用 21 的 `socai2-ueba-1`。停用前读回正式 Fusion 的 `ueba_fusion_enabled=false`，并核对 UEBA 容器的 Compose 项目和服务归属。原容器及运行配置保留供回退。

停用后，Fusion 与 HTTP 的 `/readyz` 均返回 200。告警、事件与 Case 列表返回正常 JSON 列表。Fusion、HTTP、Kafka 和 SpiritHub 转发器的容器身份及启动时间均与停用前一致。十项检查通过。完整部署快照及机器回执保存在 21 的受控批次目录。

Kafka 退役需先确定新告警入口。当前 C173 Fusion 从我方 Kafka 接收新告警，内部 `/process` 也依赖 Kafka 发布结果。[现行 C173 接口](../../../../deploy/aisoc21/c173-release-20261121-03/contract/openapi.json)
