# 依赖项：功能与使用方式

2026-10-21。沿原设计，复用[full配套的基本运行证据](full-support-migration.md)，本页只说明如何用，不新增实现或测试专项。以下HTTP地址在21本机使用；Bearer和tenant从受控配置取得，不把凭据写进命令或文档。

## 有哪些功能

| 能力 | 入口 / 输入 | 返回 / 用法 |
| --- | --- | --- |
| UEBA学习与偏离 | Kafka `socai2.raw_events.v1`，发送normalized事件 | 建立/更新基线，达阈值才发布异常；格式、查询和参数直接见[现有UEBA说明](../architecture/ueba.md) |
| 显式实体评分 | UEBA `POST /api/v1/ueba/score`，实体和数值特征 | 更新PG并返回异常或null；HTTP不发布Kafka异常 |
| IOC精确查询 | TI `GET /api/v1/iocs/search`，`value/ioc_type/source/limit` | OpenSearch原查询；无匹配为`{"total":0,"iocs":[]}` |
| 本租户IOC管理 | API `GET /api/v1/threat-intel/iocs`，可筛`ioc_type/severity/is_active` | PG租户IOC列表，无记录为`[]`；**没有value精确筛选参数**，不能把`?value=`当匹配查询 |
| Feed情报浏览 | API `GET /api/v1/threat-intel/indicators`，可用`type/tag/q` | 现Qdrant情报浏览，与PG租户IOC及OS精确查询分别使用 |
| IOC信誉增强 | enrichment `POST /enrich`，`{"ioc_type":"ip","value":"192.0.2.77","force":false}` | 返回provider结果/来源及分数；原批量入口为`POST /enrich/bulk` |
| 知识片段检索 | API `POST /api/v1/kb/query`，问题、条数及两个false选项，见下例 | 返回`chunks`、文档ID/标题/分块/正文/相关度；只检索，不生成答案或调用embedding |
| 调查读取知识 | API `GET /api/v1/kb/runbooks/for-triage?q=T1110&limit=3` | 返回片段、来源URL/时间及可选as_of排除信息；不调用模型 |

## 两个常用调用

在21上设置服务地址变量：`API_URL=http://127.0.0.1:18000`、`TI_URL=http://127.0.0.1:18008`。enrichment为`127.0.0.1:18002`，UEBA为`127.0.0.1:18006`。需要启动/管理时沿用[现有21部署说明](../../deploy/aisoc21/README.md)，保留完整Compose叠加，不重新部署一套基础设施。

查询一个IOC：`TI_TOKEN`使用原TI服务身份，`TENANT_ID`为调用上下文。

```bash
curl -fsS --get "$TI_URL/api/v1/iocs/search" \
  -H "Authorization: Bearer $TI_TOKEN" \
  -H "X-AiSOC-Tenant-ID: $TENANT_ID" \
  --data-urlencode "value=192.0.2.88" \
  --data-urlencode "ioc_type=ip"
```

该原OS查询只按指标/类型/来源过滤，**没有tenant过滤**，当前按共享公开情报入口使用；不能用tenant头宣称私有情报已隔离。本租户私有IOC管理用上表PG路径，问题已记[现有登记](upstream-issues.md)，本轮不扩改后端。API情报接口需`threat_intel:read`。

检索知识，不调用生成模型或语义记忆：`API_TOKEN`使用本租户具有`knowledge_base:read`的身份。

```bash
curl -fsS "$API_URL/api/v1/kb/query" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"question":"T1110","top_k":3,"synthesise":false,"recall_memory":false}'
```

`chunks=[]`为该租户本次无匹配，`answer=null`；HTTP失败不是无匹配。IOC未命中不等于安全；enrichment未配置provider时的`sources:null/risk_score=0/confidence=0`表示缺少信誉来源。当前不研究数据量、覆盖率或扩Feed。

## 已有知识资料在哪里

本轮仅一次只读确认20项目`/home/lychee/beenuar`的PG表和Qdrant集合元数据，没有读取资料正文、导入、生成向量或修改服务：

| 位置 | 本次确认 |
| --- | --- |
| 20 PG `aisoc_kb_documents` | 表存在，当前没有文档；不能把它写成已有报告全文可检索 |
| 20 ATT&CK集合 | 存在`attck_techniques`、`attck_techniques_qwen06b_v1`；仅确认集合存在，未复测内容或检索 |
| 20威胁情报集合 | 存在`threatintel_iocs`、`threatintel_iocs_qwen06b_v1`及actor集合；与文档KB分别使用 |
| 20语义记忆集合 | 存在`aisoc_memory_qwen06b_v1`；历史经验相关本轮不展开 |
| 旧项目资料文件 | `/Users/lychee/Documents/project/SOCAI/knowledge`，复用[已有盘点](knowledge-data-inventory.json)，不重新采集或全量导入 |

20集合存在不等于已导入21；21当前知识读取及少量受控资料消费的有效证据直接复用。需要哪份既有资料时再做最小接入，不在依赖说明阶段重建全量索引或做引用质量复验。

源码入口：[TI查询](../../services/threatintel/app/main.py)、[OS查询](../../services/threatintel/app/storage/opensearch.py)、[API情报](../../services/api/app/api/v1/endpoints/threat_intel.py)、[信誉增强](../../services/enrichment/internal/handler/handler.go)、[KB](../../services/api/app/api/v1/endpoints/knowledge_base.py)。配置位置沿用[full回执](full-support-migration.md)，本页样例未实际发送，旧测试结果不重跑、不改写。
