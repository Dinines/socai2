## ADDED Requirements

### Requirement: 21 Kafka internal client transport

21 上的 Fusion 和 UEBA 使用指定的同机 Kafka 内部监听和原有消费组。启用此 profile 时，客户端 MUST 通过配置的明文协议收发，Kafka Topic 与已提交位点 MUST 保持原业务身份。

#### Scenario: Transition the two deployed Kafka clients

- **GIVEN** 同机监听已经通过合成记录的投递与读回，业务依赖解析与当前实例一致
- **WHEN** 依次替换 21 的 Fusion 和 UEBA 并读取实际 Kafka 配置
- **THEN** 两个实例达到就绪状态，沿原消费组和位点继续工作，Kafka 和转发器保持原在役实例
