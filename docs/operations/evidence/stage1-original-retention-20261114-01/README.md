# 阶段一步骤6：各模块原件完整留存、关联和读取

2026-11-14，本地验收通过。实施前先更新[第六步安排](../../../../openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#第六步实施安排原件关联与读取)，并通过[OpenSpec严格校验](openspec-before.txt)。本轮止于步骤6，未推进步骤7页面展示、部署、提交、推送或change归档；主调查31/41，模型正文质量仍为NOT_PASSED。

## 实现与读取约定

- A/I、C1、C3/Deep/C6、证据索引和报告使用既有PG JSON/text保存原件，删除旧1 MiB应用级拒存；现有Case/A/I工件详情和告警材料详情取消该字节拒读，保留归属、外部引用及size/hash完整性检查。没有新增数据库迁移、对象存储或服务。真实存储失败仍走原失败/unknown处理，不承诺无限资源。
- A背景、C2、C4不再为原件字节阈值删行。`rows`、`returned_rows`保持查询数量上限；本次已经取得的额外探测行留在`overflow_rows`，`rows + overflow_rows`按原顺序还原全部有界返回。额外行不进入模型/业务投影，不扩大来源范围或追加查询。C4通过来源合同核验的返回先独立提交，再产生完整业务投影；投影失败不会回滚原件，步骤/Run仍按unknown保持，不自动重试。模型业务视图另按原有准备/上下文限额筛选。
- 四份策略删除`model.max_artifact_bytes`，将原C5派生图字节限额单列为`views.max_graph_bytes=1048576`；原件存取不使用该值。`max_prepared_bytes=262144`、各阶段模型/工具次数、行数、tokens、时间和C6预留保持。新装/升级来源及交接已同步，旧格式必须与新loader一起升级；当前运行服务和冻结发布配置未切换。
- 新A/I/Case Run另存`socai2.runtime-policy.v1`完整策略TOML及已选输入profile，输入工件通过source_refs关联该快照；策略指纹可与实际原文核对。后台配置不加入模型视图，不保存环境或凭据。已存在模块/工件的Run、步骤、父子步骤、请求/原答/处理及输出关系复用；未补造阶段输入或历史配置。

本步代码与配置差异相对开始前快照见[step6.patch](step6.patch)，包括15份核心模块、4份策略和5份既有测试；没有把前轮未提交内容计为本步实现。

## 直接验证结果

| 验证 | 结果与证据 |
| --- | --- |
| 离线合同/策略 | [30项通过](offline-tests.txt)：四份策略完整快照/哈希、配置拆分，复用C3合同和补查分流检查。首次测试文件名错误未执行任何测试，保留[原日志](initial-offline-tests.txt) |
| 定向隔离PG | [首轮6项通过](pg-checks.json)，[新增数量探测检查1项通过](pg-checks-02.json)，[C4原件先提交的2项复验通过](pg-checks-04.json)（含1项重复检查），共8个不同检查通过：C1大原件、不可变版本、历史缺失与租户边界；C2/C4大行、查空/数量上限、额外行留存；Case完整读取及校验/外部引用保护；投影失败后原件仍保留、步骤/Run为unknown |
| 新大原件实际保存读取 | [attempt03](attempt03/manifest.json)：7份工件分别为1,573,009–1,576,756字节；A/I冻结输入、A/C2实际SQL资产查询、Case原件/派生存储路径及Markdown全文均保存。25工件+1材料详情共26次ASGI GET，正文、size/hash及读取前后快照一致；三个新Run各有配置快照关联。见[校验](attempt03/readback-checks.json)、[读取回执](attempt03/api-readback.json) |
| 原件与模型视图分开 | 复用新批已保存的原始输入及约1.575MB查询原件，离线调用原生Case业务视图生成器；准备成功，完整messages为10,047字节，小于原262,144限额，原件字节未改，无模型调用。[记录](model-view-separation.json) |
| 各模块实际原件关联 | 只读复用固定C01、步骤5成功/unknown及步骤4补答，共8Run、70步骤、176工件、77个实际来源引用，覆盖A/I、C1–C6、Deep及C3初答/补答/合并。13个阶段无直接input指针，从同Run输入和子步骤还原。73次代表性ASGI GET与数据库原件一致，所有原size/hash和历史Run状态保持。[逐模块映射与读取](module-links.json) |
| 本机静态记录 | 使用既有update_processing_audit.py追加存取夹具，记录10→11，旧10条及482份文件字节不变。[更新](audit-update.txt) / [读回](audit-readback.json)。实际4177仍为SSH转发PID44022，未发布页面 |

新存取夹具Case为`dc153d2c-64a8-5a7f-ac99-549c29d19951`，Case Run为`259d44b7-0c3e-46c1-bf02-b1c260acdcae`。它专门验证存取，A/I/Case三个Run均以`cancelled / storage_validation_only_no_analysis`结束；没有模型步骤、Result或业务结论，不冒充完整调查成功。文本明确标为存取夹具，未调用模型替身；原模型证据只读复用已有真实Run。本批新增调查Run的外部湖/厂商调用0、写湖0、真实模型调用0、模型替身调用0；离线边界检查和C4组件检查中的受控来源/传输夹具不冒充真实服务调用。

## 失败及未验边界

1. 旧C2行数测试在写隔离`public.assets`夹具时，处理角色被拒绝；[原失败](pg-checks.json)保留。没有扩大处理角色权限；改用配置中既有隔离库夹具写入身份插入本批测试资产，再由处理角色执行A/C2真实SQL查询。数量探测的直接断言另用独立受控来源夹具完成，见pg-checks-02。
2. 大原件批次首轮、attempt02先后因资产夹具未填实际必填列而失败，均发生在A/I/Case Run创建之前；各自资产事务回滚，已提交的合成材料保留。[首轮](run-failure.json)、[attempt02](attempt02/run-failure.json)及写入意图保留。读取实际表结构后修正夹具，以新身份完成attempt03，没有重派旧Run。
3. 历史读取脚本首次FastAPI依赖函数写法触发深拷贝错误，发生在业务GET前；修正只读脚本后重新读取同一原Run。[原失败](links-initial-failure.log)保留。
4. 补充C4原件先提交的首轮检查触发既有`run_steps_query_rows`约束，已修正为中间阶段只提交原件指针，终态时才更新步骤行数；测试只读快照使用无锁SELECT。原检查失败保留在[pg-checks-03](pg-checks-03.json)，修正后以新夹具完成[两项复验](pg-checks-04.json)，没有改V1约束或重派旧unknown Run。
5. 历史Run未留完整运行策略原文的缺口仍标为历史未保存；旧unknown C4步骤没有原始返回，保持unknown而非查空/已保存。没有回填旧配置、虚构未收到的正文或改写原结论/引用问题。

以上HTTP为原生服务配合鉴权依赖覆盖的进程内ASGI读取，未验收生产TCP。页面预览、节点结论和长正文交互归步骤7；本轮仅确认原件存取及关联可用。现有模型质量后置项不因程序存取通过而核销。
