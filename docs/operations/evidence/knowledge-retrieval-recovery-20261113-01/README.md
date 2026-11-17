# 固定流程知识正常检索与输入预览

2026-11-13。本批只做一次真实知识查询及离线输入装配：沿用固定05/06批的模型、1024维、集合、profile和B01九条冻结查询，没有新Run、生成模型调用、数据库/索引写入或服务发布。

## 结果

- 当前本机28135无监听；21原端点版本读取200。按[原转发配置](../../../../tools/testdata/case_knowledge/local-services.json)建立本次专用转发后，正常adapter检索成功，完成后只关闭本次SSH进程。原503只有状态回执，**不能由当前缺失转发倒推其历史根因**；也不声称永久后台转发已恢复。
- [实际查询回执](query-result.json)：一次嵌入POST200，9个输入、552个embedding prompt tokens，qwen3-embedding:0.6b、1024维；集合检查及9次向量查询均200。沿正常adapter回读真实隔离PG并核对文档/hash；未重导或重建集合。
- 两条返回均为同一份AN0846知识，分别用于技术解释和取证指导，只绑定进程成员。网络无结果，登录两个候选因适用条件冲突被排除，历史参考无结果。查询用途和适用条件独立于相似度，不能作为本案行为证明。
- 由现有程序将两条返回合为一张知识卡，845字符结构化原文投影为448字符业务正文，在C3/Deep/C6各出现一次；说明、核查说明保留原文，去除结构引用和后台字段。两个用途及全部出处保留，角色仍为`source_label`并标记`query_binding_only`，没有变成观察证据。

| 环节 | 完整输入预览 | 字符 | 知识正文 |
| --- | --- | ---: | --- |
| C3 | [首轮输入](inputs/C3-input-preview.txt) | 9818 | [程序选择的正文](inputs/C3-knowledge-content.txt) |
| Deep | [问题级输入](inputs/Deep-input-preview.txt) | 11073 | [程序选择的正文](inputs/Deep-knowledge-content.txt) |
| C6 | [综合输入](inputs/C6-input-preview.txt) | 14560 | [程序选择的正文](inputs/C6-knowledge-content.txt) |

这三份是**新检索结果配合旧冻结上下文的离线预览**，不是实际派发请求。Deep/C6承接的是旧Run保留下来的C3/Deep原答，未根据新知识重新推理；旧质量问题保持。预览wrapper使用明确的新标识，未写成数据库工件；profile仅在离线副本更新。完整提示/Schema、来源映射和摘要在`inputs/*-request-preview.json`、`*-selection.json`及[summary](inputs/summary.json)。

## 验证与复放

[query.py](query.py)使用显式[config](config.json)、正常`knowledge_source.query`及只读事务，执行意图采用独占创建；本批已有意图，不可原目录重查。未来确需新查询，应复制为新批次并按实际配置明确建转发，不能只看4177可访问就假定28135也已连接。查询结束主动关闭临时转发，因此后续真实调查仍须在整个Run期间保持其知识连接。

[rebuild.py](rebuild.py)只读本批返回及B01原快照，调用现有业务投影/去重/装配函数，检查三个环节均仅一张卡、正文一次、原说明完整、用途/范围/引用保持。可离线复放：

```bash
.local/conda-envs/socai2/bin/python docs/operations/evidence/knowledge-retrieval-recovery-20261113-01/rebuild.py
```

业务源码未修改，使用[前批源码复放包](../case-observation-input-20261113-01/source-replay.json)及本批源码摘要核对版本。三次离线导出脚本错误分别保留在`offline-attempt-01/02/03.json`，只修驱动的工件类型筛选、函数参数和角色断言；真实检索没有重试，分析模型零调用。Ruff、OpenSpec及最终离线检查见[validation](validation.json)。固定06批115份流程原件摘要不变，旧503及三例拒收未改写。

本批没有新调查或落库快照，因此不向4177新增或重标旧Run。本机静态包仍79，在线4177不变。HTTP字段、数据库表、运行预算、自动消费者和流式流程不变；没有新增业务代码缺口，不为了探针成功改产品配置。F02知识合理使用、C6新反馈真实效果及完整固定流程仍未通过，主调查31/41保持。限定独立审计见[audit](audit.md)。
