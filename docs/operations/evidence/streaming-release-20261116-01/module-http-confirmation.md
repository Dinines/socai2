# HTTP后端模块发布确认

审阅日期：2026-11-16。范围仅为当前正式发布的HTTP模块确认；基于当前文件及保存证据，只写本文件。没有新增HTTP/SSH/SQL请求，没有启动服务、消费者或调度，没有投递、模型调用、业务写入、提交或推送；未修改共享文档和其他模块文件。

## 结论

**HTTP模块的已验功能和当前冻结包可发布，未发现需要新增业务代码或调整80操作合同的阻断。正式切换仍须完成下列配置装配、数据库增量和实际读回；本确认不等于正式服务已经发布或整个change已通过。**

S04预算续验已完成新I和整事件Case第二轮及上一轮读取；W5实际4177为0.6.0。这两项不能再按旧阶段文字列为未完成。第8–10步、AI对话及模型质量`NOT_PASSED`保持后置，整个change不归档。当前历史业务表和活动账本已按授权清空，旧UUID仅用于离线证据，不能要求从当前空库重新查出，也不能回灌旧批次来完成发布验收。

## 已核对内容

| 项目 | 实际结果 |
| --- | --- |
| 冻结HTTP包 | `.local/streaming-release-20261116-01/http/`，release=`streaming-http-20261116-r1`。profile列出的723份来源与包内逐字节一致；manifest的726项文件摘要全部匹配；`http.tar`摘要与`http-package-01.json`一致。723来源与726包文件是不同计数，不能混用 |
| 独立入口 | 在仓库外工作目录、禁用网络连接及字节码写入的进程中导入包内`investigation_http.main:app`，只生成OpenAPI、解析上下文及配置，不进入lifespan。没有连接数据库；离线DSN只用于配置解析，不作为正式账号连通证据 |
| 80操作/55 GET | 包内生成的业务方法/路径、全部Schema与冻结`contract/openapi.json`一致；冻结合同也与W2已读实际服务的80操作和Schema一致。没有恢复E11/E13/E36外部旧执行旁路，没有把内部阶段或调度路由加到公开Swagger |
| 无鉴权 | 加载后无顶层/操作security或securitySchemes；独立应用装配4个可信上下文依赖覆盖。`AISOC_DEV_AUTH_BYPASS=false`保持，这是独立HTTP直接使用配置身份，并非通过旧开发鉴权旁路实现。历史真实无凭据HTTP证据沿已验批次复用 |
| 异步受理 | 事件`POST /incidents/{incident_id}/diagnose`与Case`POST /cases/{case_id}/investigations`为202任务回执，保留404/409/422/503。外部适配进入核心任务用例；受理不是执行完成，HTTP启动/GET不启动调度。告警入站自动登记、Case建案登记首轮按当前统一设计，不新增手动告警旧入口 |
| 任务→Run→结果 | task真实attempt的run_id生成run_url；无Run保持null，results按source_run_id指向本轮。A/I结果链接进入原Run详情，Case进入独立Result。没有用latest_run替换选中历史轮次、没有造成功结果；这些适配源码在当前包中与已验版本一致 |
| 步骤、原件及比较 | Case Run直接提供完整目录链接，A/I经trace；目录分页和content_url保留原主体/Run/工件身份。Case前轮链接由冻结comparison_context生成，初轮/null和unavailable原因保持；不按当前历史猜上一轮或退回更早成功结果 |
| 真实后轮证据 | `streaming-budget-20261116-01/saved-validation.json`为119项保存核对通过，8新task/2新Run；`http-validation.json`为同一快照48 GET通过，24份必要正文及2条上一轮链接可读。整事件Case4成员/2轮，单案1成员/1轮；旧3000/length失败、首轮问题及后轮C3/C6问题原样保留，质量仍NOT_PASSED |
| W5能力 | `streaming-w5-4177-20261116-01/flow-02/outcome-summary.json`记录0.6.0、62包文件、10项包检查、14项JS、实际4177的10 GET及清理后空态。证明现有查阅能力和入口，不证明本次正式18024接线已经切换 |

## 正式配置对应

1. **HTTP：** `http-profile.json`明确`192.168.1.21:18024`→容器8000，数据库`aisoc`、地址`192.168.1.21:5432`、TLS `require`，新容器`socai2-production-http-20261116`。入口仍为独立HTTP应用，启动时不做schema迁移、不启内部阶段执行。
2. **reader/writer：** `release.json`和`database-install.toml`明确reader=`aisoc_app`、writer=`socai2_prod_processor`。保存的角色检查确认两者为可登录普通角色，非superuser/非bypass RLS。`manage.py`会要求两个显式DSN使用同一目标库，并补配置的sslmode；它不替代实际凭据、role和连接读回。私密运行环境指定为发布目录`private/http-runtime.json`，审阅时没有已装载该新文件的正式容器证据，不能声称正式双池已经连通。
3. **上下文：** `context.json`、release.identity及包内context一致：tenant=`00000000-0000-0000-0000-000000000001`，actor=`a5c41f91-21c8-4dfc-8f6c-cd4c71b41dc5`，记录名“业务后端（内部可信）”。`target-readonly-01.json`确认正式aisoc已有该tenant及actor。请求不需要调用方传登录、Token或角色。
4. **生命周期/策略：** 包内`analysis-tasks.json`与正式`analysis/lifecycle.json`字节一致：I4小时、Case6小时、活动7天、一次重试/60秒；分配100条及policy与发布方的对应文件一致。不是候选20秒/30秒/1天。HTTP只显示核心状态/资格，不把资格等同调度已启用。
5. **Swagger及CORS：** release.swagger明确18080，目标API为`http://192.168.1.21:18024`。离线应用实际解析的CORS为`http://192.168.1.21:18080`及`http://127.0.0.1:18081`，匹配正式文档及现有本机文档入口约定。CORS是浏览器读取配置，不是权限验证；4177通过自己的同源代理请求，无需把4177 origin额外加入业务API。
6. **4177：** release.viewer计划复用0.6.0镜像，21回环4177→容器14178，新r5容器，上游明确18024，原活动状态目录保留。此目标匹配正式HTTP；但`old_config`是现运行r4配置来源，不能只改base_url就认定已完成正式切换。新代理的tenant、environment_label、冻结OpenAPI文件及sha必须同时对应正式服务；账本服务和代理environment_label一致，不能把旧候选tenant/标签留在新入口。

## 切换前必要条件：不是新增业务需求

- **正式库增量和普通账号接线必须实际完成。** 保存证据中正式仍28表450列，候选32表521列。按本轮显式aisoc安装步骤应用128/129及必要读写接线并verify后，才能启动依赖新任务/分配结构的HTTP。不能拿候选迁移通过或现有health通过代替正式增量；不新建替代空库、不清库、不降级DDL。
- **生成并核对实际私密HTTP运行配置。** reader和writer必须分别使用上述账号、同正式库/host/port和`require`；读取实际用户名及`current_database()`，保留脱敏回执。离线配置解析、旧角色存在或旧容器凭据均不能代替这个检查。
- **完成Swagger及4177正式装配。** 当前审阅材料提供目标release配置及HTTP包，尚未提供已切换正式Swagger/4177的生成配置与读回。正式Swagger必须以新副本配置`servers[].url=18024`、告警/事件/调查三类和80操作；现冻结原合同没有servers，不能把它直接当作完整18080发布内容。4177同步正式环境、tenant、合同及摘要；当前旧18424/18480与原历史包不改写成正式证据。
- **区分合同语义和字节摘要。** 包内冻结OpenAPI的info.version为`2.0.0`，实际启动会设为`streaming-http-20261116-r1`；离线已证明80操作和Schema相同，但两者字节摘要不能直接当相等。发布方需冻结实际选定的正式合同/展示元数据，4177代理声明的contract_sha256必须对应其真实加载文件，并另核与实际HTTP的方法、参数、响应Schema一致，不复用旧r2实际服务摘要冒充新版本。
- **重新冻结最终发布清单。** 本轮只读重算时`profile-preparation-01.json`里的`fusion-support-access.sql`摘要与当前文件不同，其余所列profile一致。HTTP包及自身profile摘要均匹配；这不是HTTP代码阻断，但共同发布材料仍在收口，最终独审/部署须用更新后的准确清单，不能把较早preparation回执当最终全部文件冻结证明。本确认未改该SQL或旧回执。

这些条件未完成时，不能宣称“正式HTTP已发布且可用”；它们属于当前发布步骤，不要求负责人再确认权限，也不要求重做历史故障矩阵。

## 发布后最小必要读回

由发布/测试方统一执行一次并共享证据，HTTP模块不另起重复测试：

1. 核实际镜像/release、context、双池role/aisoc/TLS、迁移及普通账号接线、policy/lifecycle；无凭据访问18024就绪与实际OpenAPI，确认80操作/55 GET、无security及旧旁路未恢复。
2. 从18080读文档及合同，核三类、输入输出/错误、servers指向18024；对其明确origin做一次必要浏览器/CORS读回。4177 capabilities/代理实际响应核同正式tenant、环境、合同、来源；清空后的批次/业务列表空态是合法结果，不回灌旧批。
3. 使用发布方新独立批次的真实入站/执行数据，沿新身份完成最小告警分诊、事件诊断与Case首轮/更新链。受理时核202/task；沿status_url→attempt.run_url/results.url读同轮结果、步骤/原件；Case后轮核冻结前轮身份和比较链接，原件读取实际内容/摘要与范围。复用发布方同一组样本和模型调用，不另开一组为HTTP取数而重复执行。
4. 同一批次经4177读取实际task/Run/结果/原答，确认页面没有跨环境或跨轮次混用，失败/跳过/unknown/partial/新鲜度和质量仍分开。当前空态和历史非空证据不代替这次正式环境新数据的保存读取；不为后置质量或全部异常分支额外采样。

## 本轮应同步的当前交接文件

由发布负责人按实际切换结果更新，本模块只列清单，未修改这些文件：

- `FRONTEND_BACKEND_HANDOFF.md`、`README.md`、`PROGRESS.md`：正式18024/18080、4177、版本/tenant/实际能力及新批样例；将旧候选地址/UUID标为历史，明确S04/W4/W5已由后续证据承接。
- `deploy/http-service/README.md`、`CONFIGURATION.md`，`deploy/api-docs/README.md`及新正式Swagger/manifest/config副本：明确reader/writer、可信context、CORS、本机18081查看方法、实际服务器URL和配置来源。已有候选冻结目录原样保留。
- `deploy/aisoc21/workbench-display-current.json`、`deploy/investigation-test/README.md`及最终4177配置/运行清单：0.6.0读取正式HTTP，实际environment/tenant/OpenAPI摘要及状态目录；旧批次已清空，不再指引按旧ID在线查询。
- `docs/integration/analysis-submission-http.md`、`analysis-tasks-http.md`、`run-records-http.md`、`incident-analysis-http.md`、Case首轮/分配指南及实际功能清单中的当前部署状态：同步正式已可用、接口跳转与新的可用样例。请求/响应业务字段本轮不变，不借文档维护重造合同。
- 原HTTP OpenSpec配合段、stage11及发布回执：记录本次实际读回与范围；第8–10步和模型质量后置，整个change不强行勾完/归档。

不修改S01/S04原失败、预算续验、W1–W5、清理及历史冻结OpenAPI/回执来追认新环境成功。

## 关键核对锚点

| 文件/工件 | 本次核对摘要 |
| --- | --- |
| HTTP tar | `afab5689b586ed61fba5d9e98bb6c7f18a29a9c80362a8a6ad5b0f7c439594d4` |
| HTTP冻结合同 | `657a2f24a660a8c9ec5feb034e9ed0c1119fcf7dc241cdc4da2a0337fed101e3`（info.version=2.0.0的冻结文件） |
| 正式http-profile.json | `31f40aa0848a88952279061481fe54787b0d5de92a48c3563c0c7835718feb99` |
| 正式context.json | `d8af1afceea878a441781108f3bcf91be22753e97fc779f9cc446e6755fb170f` |
| 正式lifecycle.json | `2321938129828f8e768afae14ecffeaaec3f6b0788f54e8e4968ca45c0c5b181` |
| 正式investigation-policy.toml | `9ef4129c88b94be7cecfe3b0ad89ba545919554cf93b5ddb8c923f853ef90a8c` |
| S04后轮保存/HTTP共用快照 | `a2a2f45e75cd52562c281ab485f152b40a555dcba66a4b9132e9d9a74a204aa2` |

最终模块判断：**可发布已验HTTP功能；无新增HTTP实现阻断；正式数据库/运行配置/Swagger和4177装配与上述发布后读回必须完成。**

## 聚焦补核：本批Swagger取错了旧71操作来源

2026-11-16追加，只读本地文件和既有检查入口，0新增服务请求。**HTTP应用/冻结包可发布的结论保持；当前`upload-frozen.py`选择的Swagger内容有实际交接阻断，必须纠正后再放行文档发布。不能仅把相等断言放宽后继续复制这份旧合同。**

`upload-frozen.py:19`复制的`deliverables/investigation-validation-20261106/http-handoff`实际为`2026-11-14.docs20-candidate`：manifest明确71操作，文件重算为71操作/44 GET、162 Schema。它确有中文三类、x-dynamic-sections、错误/响应补充等富化信息，但底层业务合同也是旧版本，不只是展示不同。只改info.version/servers不能升级成当前80操作。

### 已确认的真实不符

| 核对项 | 旧deliverables文档 | 当前冻结HTTP合同 |
| --- | --- | --- |
| 操作数量 | 71 / 44 GET | 80 / 55 GET |
| 新读取能力 | 缺三类主体task列表/详情共6项；缺统一Run目录、steps列表/详情、artifacts共4项；缺related-cases | 上述11个GET均已提供 |
| Case再次调查 | 无`POST /cases/{case_id}/investigations` | 202 / AnalysisTaskReceipt |
| 旧外部执行入口 | 仍有`POST /alerts/{alert_id}/analyze`、`POST /cases/{case_id}/baseline/prepare`、`POST /cases/{case_id}/runs/{run_id}/start` | 已退役，不属于80操作 |
| 事件诊断 | `POST /incidents/{incident_id}/diagnose`写200 / StageEntry | 实际202 / AnalysisTaskReceipt，异步任务读取 |
| Case创建 | `POST /cases`写200 / AssociationReceipt | 实际201 / CaseAllocationReceipt，真实分配及首轮任务 |
| 主要读取结构 | 使用旧RunDetail/TraceView/ResultDetail，无新任务、完整目录和比较等Schema | 使用当前带目录/比较的结构及AnalysisTask、分配、IncidentInputSelection/AnalysisCoverage等Schema |

双方共有的68个操作，在只剥离展示注释后仍有请求/响应结构差异；不是应一概忽略的x-*扩展。缺12项、旧多3项，净差9项。这里没有把路径参数名字展开或重复分类数算成新操作。

### 现行生成器和已有验收入口的适用范围

1. `deploy/api-docs/build.py`目前仍固定读取`docs/design/socai2-independent-api-v2.openapi.json`，版本固定`2026-11-14.docs20-candidate`，通过`catalog.py`和`publish.py.enrich_contract()`生成旧71项；`publish.py`中还保留旧同步E36/E37及71操作文字。**此生成器不是当前80操作合同的生成入口，不能直接重跑它来证明本轮正确。** 本次没有运行它，也未覆盖旧资料。
2. 当前80操作三类文档已有已验工件：`docs/operations/evidence/case-update-http-20261115-01/swagger/`，其manifest记录`contract_equal_after_display_annotations=true`；对应后续候选为`deploy/api-docs/streaming-20261115-01/handoff/`。本次重新离线核后者，80操作/55 GET、路径集合、参数/请求体/响应结构和全部Schema与正式HTTP冻结合同一致，三组为告警/事件/调查，无security；注释归一后0个共有操作差异。
3. `docs/operations/evidence/streaming-http-candidate-20261115-01/validate_package.py:51–63`和包内`manage.py:verify()`中仅排除info/servers的全对象相等检查，用于**实际运行OpenAPI vs同版未富化runtime合同**，用途正确；不能原封不动用于文档富化文件。`manage.py verify`还会请求服务，本次未运行。
4. W2 HTTP合作的`streaming-w2-http-cooperation-20261115-01/result.json`已记录80操作文档的展示差异：80组tags、80项x-deployment-status、9处examples及1处POST description；全部Schema原本一致。这里不是允许任意更换请求/响应Schema的通用白名单。

### 正式内容的处理建议

- 正式Swagger以已经核对的80操作候选包/正式runtime合同为起点，在**新的正式副本**中设版本、18024服务器地址、manifest摘要及实际发布状态。不能使用旧71合同换版本号，也不能复用旧manifest的71/162统计。
- 原中文说明、125功能对应、动态字段及错误解释有保留价值，旧原件保持。继续使用时按当前路径和字段逐项移植有效说明；已变化的受理方式、200→201/202、任务/Run/比较/范围和3个退役入口必须修正。旧富化Schema、旧成功码及示例不能整块覆盖当前结构。历史审计资料可作为明确标注的历史附录，不能默认成为当前接口合同或当前执行指南。
- 4177代理使用发布方说明的独立runtime合同新version副本及实际字节SHA，做严格运行合同核对；富化Swagger另做下列结构核对，两份文件用途分开，不为了相等删除所有文档内容。

### 可复用的离线结构核对命令

在仓库根目录执行下列命令。它不请求服务、不写文件；当前80操作候选包通过，旧deliverables文件必定失败。发布方可把第二个参数替换为正式副本的`swagger/handoff/openapi.json`。Schema的properties/schema名称作为映射保留，避免误删业务字段`description`、`title`或`examples`；仅移除相应Schema/操作位置的说明和x-*注释，不删除type/required/enum/nullable/default/约束、参数、请求体、状态码、media type或引用。

```sh
PYTHONDONTWRITEBYTECODE=1 .local/conda-envs/socai2/bin/python - \
  .local/streaming-release-20261116-01/http/contract/openapi.json \
  deploy/api-docs/streaming-20261115-01/handoff/openapi.json <<'PY'
import json, sys
from pathlib import Path
runtime, swagger = [json.loads(Path(p).read_text()) for p in sys.argv[1:]]
methods = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}
maps = {'properties', 'patternProperties', '$defs', 'definitions',
        'schemas', 'mapping', 'dependentSchemas'}
annotations = {'description', 'title', 'example', 'examples', 'externalDocs'}
def clean(value, mapping=False):
    if isinstance(value, list):
        return [clean(v) for v in value]
    if not isinstance(value, dict):
        return value
    if mapping:
        return {k: clean(v) for k, v in value.items()}
    return {k: clean(v, k in maps) for k, v in value.items()
            if k not in annotations and not k.startswith('x-')}
def operations(doc):
    return {(p, m): op for p, entries in doc['paths'].items()
            for m, op in entries.items()
            if p.startswith('/api/v1/socai2/') and m in methods}
def canonical(op):
    return clean({k: v for k, v in op.items()
                  if k not in {'tags', 'summary', 'operationId'}})
a, b = operations(runtime), operations(swagger)
assert len(a) == len(b) == 80
assert sum(m == 'get' for _, m in b) == 55
assert a.keys() == b.keys(), 'missing or obsolete operations'
changed = [f'{m.upper()} {p}' for p, m in a
           if canonical(a[p, m]) != canonical(b[p, m])]
assert not changed, changed
assert clean(runtime['components']['schemas'], True) == \
       clean(swagger['components']['schemas'], True), 'Schema contract differs'
assert [v['name'] for v in swagger['tags']] == ['告警', '事件', '调查']
assert all(set(op.get('tags', [])) <= {'告警', '事件', '调查'}
           and op.get('tags') for op in b.values())
assert not swagger.get('security')
assert not swagger.get('components', {}).get('securitySchemes')
assert all(not op.get('security') for op in b.values())
print('PASS: 80 operations / 55 GET; requests, responses and Schema match')
PY
```

上述命令是本次已实际跑通的只读判据，不是声称仓库已有通用富化校验器。它对当前80候选有效；若继续移植独立动态Schema、增加未在runtime声明的错误Schema/状态码而失败，必须逐项对照当前实现及原实际回执审阅，再按明确范围接纳，不能把所有responses/components差异都忽略。对可选补充Schema也要验证引用可解析、没有覆盖或收紧当前返回字段。注释和示例不参与结构相等，因此仍须单独核它们的内容。

文档副本还需直接确认：正式`info.version`、`servers=[{'url':'http://192.168.1.21:18024'}]`；manifest的80/三类/实际文件SHA；swagger-config指向该正式文件；异步202示例有task_id/status_url，Case201为分配回执，示例UUID明确是历史样例、不能重放；公开说明不再写E11/E13/E36可执行、不再描述同步E37或候选短周期；附录与guide/endpoints当前链接不把旧71资料冒充现行。这里本次未重建或上传正式文档。

补核结论：**相等断言确实需要按用途区分，但这次还存在选错旧71来源的真正问题。先修正式Swagger来源/内容，再按80操作结构及示例、说明两层核验；不能仅放宽断言解除发布阻断。**
