# 案件关系图：保存与恢复

用途：用户展开案件线索、调整画布后保存，下次继续上次的探索。保存不加入案件成员，不产生调查，不采用结论。明确加入仍调用 E08，AI 对话继续暂缓。这里提供后端 HTTP 能力，画布由调用方绘制。

| 操作 | HTTP（前缀 `/api/v1/socai2`） | 输入 | 输出与结果 |
| --- | --- | --- | --- |
| E67 读取探索底图 | GET `/cases/{case_id}/exploration-base` | 案件 ID，可选 `run_id` | `ExplorationBase`：底图来源、原图、成员材料对象和指纹；只读 |
| E68 保存探索 | PUT `/cases/{case_id}/exploration` | `ExplorationSave`，见下方 | `ExplorationSnapshot`：不可变保存 ID、底图、匹配来源、画布状态 |
| E69 恢复探索 | GET `/cases/{case_id}/exploration` | 案件 ID | `{"snapshot": ...}`；从未保存时 `{"snapshot":null}` |

## 调用步骤

1. 打开案件先 E69。已有保存时直接还原 `snapshot.base`、`expanded_links`、`expanded_sources` 和 `view_state`。没有保存再 E67。
2. E67 默认选择最近完成的基础调查。返回 `run_id`、`result_id`、`graph_artifact_id` 和原图 JSON。`delivery_state=partial` 原样保留；当次缺图返回 `graph_state=unavailable`，不借另一轮图补齐。没有已完成基础调查时 `kind=members`，用 `sources.alerts/objects` 绘制成员关系。AI 对话结果不作为底图。
3. E66 查询候选，用户展开后，将对应 `matches.seed.id` 与 `matches.candidate.id` 保存到 `expanded_links`。涉及的全部对象可先 E30 `section=objects` 回查。
4. 初次保存：`expected_snapshot_id:null`，`base_run_id` 和 `base_fingerprint` 来自 E67，成员底图的 Run ID 为 null。
5. 再次保存：`expected_snapshot_id` 填最近 E69/E68 的保存 ID；`base_snapshot_id` 填要继续的保存 ID，不传 `base_run_id/base_fingerprint`。服务端复制当时底图及已有来源快照，新调查不会替换它。
6. 撤销展开：去掉对应关系及其后续依赖分支，再 E68。重置：重新 E67，按新指纹保存空 `expanded_links` 和新的 `view_state`；仍传最近保存 ID 防覆盖他人。

## 请求示例

下列 UUID 和指纹仅说明格式，实际值从 E67/E66 取得。`operation_key` 每次新的保存生成一次，重试沿用。

```json
{
  "operation_key": "00000000-0000-4000-8000-000000000001",
  "expected_snapshot_id": null,
  "base_run_id": null,
  "base_fingerprint": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "expanded_links": [
    {
      "seed_object_id": "00000000-0000-4000-8000-000000000002",
      "candidate_object_id": "00000000-0000-4000-8000-000000000003"
    }
  ],
  "view_state": {
    "positions": {"alert:真实告警ID": {"x": 120, "y": -40}},
    "selected": ["alert:真实告警ID"],
    "zoom": 1.25,
    "filters": {"high": true}
  }
}
```

`view_state` 的键由调用方定义，是展示信息，服务端原样保存返回，不解释成事实、证据或正式成员。可保存位置、选择、隐藏、缩放和筛选。不会自动生成页面。JSON 字段及完整成功/错误示例在 Swagger E67–E69。

## 返回字段

| 字段 | 含义 |
| --- | --- |
| `snapshot.id/case_id/created_at/created_by` | 不可变保存标识、案件和实际保存人/时间 |
| `base.kind/run_id/result_id/graph_artifact_id` | 固定起点与原件来源；成员底图后三项为 null；已关联图但内容不可用时保留原件 ID，查看 graph_state |
| `base.scope_revision/delivery_state/graph_state` | 当时范围版本、原调查交付和图材料状态，缺图如实保留 |
| `base.graph` | 保存时的调查图 JSON 原文；成员底图/缺图为 null |
| `base.sources.alerts/objects` | 成员或指定 Run 成员对应的告警事实与材料对象；图原文以 `graph` 为准 |
| `base.fingerprint` | E67 内容摘要，初次保存/重置用来检测来源变化 |
| `expanded_links[].seed/candidate/basis` | 原对象、告警、材料、字段路径、值及匹配规则；只证明共有对象，不证明攻击因果 |
| `expanded_sources.alerts/objects` | 展开涉及的真实告警和所选材料全部对象；保存后冻结，不代表实时告警状态 |
| `view_state` | 调用方提交的画布 JSON 原样返回 |

展开按输入先后校验：起点必须连接底图告警或前序展开告警，双方必须同案件来源、同对象 namespace/type 和符合 E66 的值匹配规则。hash 要有明确合法算法。允许保留旧材料对象，因此“保存合法关系”不代表重新执行了一次最新 E66 时间窗口查询；实时候选重新查 E66。跨案件查看允许，但不改变原案归属。

## 错误处理

| HTTP / detail | 处理 |
| --- | --- |
| 404 `case_not_found` / `exploration_completed_run_not_found` | 检查案件、Run ID 与归属；Run 必须已完成且为基础调查 |
| 404 `exploration_snapshot_not_found` / `exploration_object_not_found` | 保存或对象不存在/不在允许来源，不伪造空成功 |
| 409 `exploration_snapshot_changed` | 他人已保存；重新 E69 后由调用方决定合并，不能自动覆盖 |
| 409 `exploration_base_changed` | 首次/重置底图指纹失效；重读 E67 或继续原保存 |
| 409 `operation_key_conflict` | 同幂等键对应的用户或请求不同，新操作使用新键 |
| 422 `exploration_objects_do_not_match` | 对象不构成支持的真实匹配关系 |
| 422 `exploration_disconnected_branch` | 展开顺序不成立或撤销后仍有悬空分支 |
| 422 `exploration_snapshot_too_large` | 请求/最终保存超过配置大小或连线数；不会静默截断 |
| 422 字段校验 / `exploration_query_parameter_not_supported` | 必填项、重复关系、混用底图来源、未知/重复查询参数不合法 |

配置在 `exploration-state.json`（可通过 `SOCAI2_EXPLORATION_STATE_CONFIG_FILE` 指定）：当前最多 1000 条展开关系、完整快照 4 MiB。复用 artifacts 的独立 `socai2.case-exploration.v1` schema；无新增表或迁移，保存不更新 Case 行版本/业务时间、Run、Result、任务或评估。每次保存仅追加快照和活动回执。旧保存保留，当前接口恢复最近一次，不提供历史版本管理页面。

本轮验收与发布状态见[证据](../operations/evidence/case-exploration-state-20261113-01/README.md)。
