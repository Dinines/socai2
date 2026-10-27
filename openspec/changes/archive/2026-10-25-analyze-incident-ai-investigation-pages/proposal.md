# 事件与AI调查页面功能划分分析

## Why
用户明确事件页汇聚智能体调查启动前的信息，调查模块展示AI分析工作和进展，要求逐项形成文档，先不改前端。用户后续允许只读访问20，并强调不能遗漏Attack Chain和Attack Path等已有服务能力。

## What Changes
- 整理事件保留项、调查新增/调整项、每项展示与操作、当前数据来源、空态及能力状态。
- 单列Attack Chain、Attack Path、Alert Graph、Blast Radius及调查中路径分析的差别。
- 用socai2发布回执、本地源码及20只读参考验证边界，区分v1、本地未发布小修和v2设计。
- 仅保存文档及阅读索引，不改原型、交接包、业务源码或运行状态。

## Capabilities
纯文档分析，skip_specs；不新增已交付产品需求，不替代独立调查设计。

## Impact
docs/design、文档索引、PROGRESS及本change。只读20已有样例/部署源码，无新调查、模型、写库、部署或Git提交推送。
