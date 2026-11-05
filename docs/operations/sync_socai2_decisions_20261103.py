"""Synchronize confirmed product decisions and render the authoritative field dictionary."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/"docs/design"
c=json.loads((D/"socai2-data-contract-20261103.json").read_text(encoding="utf-8"))
def update(file,pairs,append=None):
 p=ROOT/file;s=p.read_text(encoding="utf-8")
 for old,new in pairs:
  if old not in s:raise ValueError(file+": missing "+old[:70])
  s=s.replace(old,new)
 if append:s+=append
 p.write_text(s,encoding="utf-8")
update("docs/design/investigation-data-schema-plan-20261103.md",[
("**当前尚未生成正式迁移或创建实际表。**","**迁移、ORM及枚举/schema已生成；已在21现有PostgreSQL的独立验证库实际建成29表，业务服务尚未切换。** 见[本轮建表与验证交接](socai2-schema-implementation-20261103.md)。"),
("AI是否同槽见D03。","AI模型/工具问答可并行，不与基础Run共用槽。"),
("采用方式D02待定。","有效基础结果自动采用；AI结果明确采用。自动采用须核范围版本及本轮期间的新判断，旧Run不覆盖较新判断。"),
("1. 先完成本轮审计的D01–D03确认，固定字段合同，之后生成socai2 schema DDL、ORM、API枚举与JSON校验。","1. D01–D03已确认，socai2 schema DDL、ORM、API枚举与JSON schema已生成，物理约束已在独立PG验证。"),
("若用户采用则另生成case_assessments/sources/members并改current指针，具体自动或手动取决D02。","若R1是有效且范围仍适用的基础结果则自动生成case_assessments/sources/members并改current指针；范围已变化或已有更新采用时只留历史。AI结果仍需用户明确采用。"),
("## 10. 尚未定稿的业务边界","## 10. 已确认决定与剩余边界"),
("- D01事件严重程度：成员最高与人工覆盖并存，还是禁止覆盖；影响4个候选override列。","- D01已确认：保留成员最高等级的自动汇总，允许人工事件覆盖，保存理由/人/时间，不修改成员。"),
("- D02当前判断：基础调查是否自动采用；AI保存不自动采用已定。","- D02已确认：有效基础调查结果自动更新当前判断；AI结果仍需明确采用，保存本身不采用。"),
("- D03基础与AI执行是否共用Case一个活跃槽；影响部分唯一索引条件。","- D03已确认：只限制基础调查单活跃；AI问答可并行，无共用槽唯一索引。"),
])
update("docs/architecture/investigation-planning-design.md",[
("结果可供案件当前认识采用，具体采用方式见第11节。","有效基础结果自动更新案件当前判断，AI结果需明确采用；发布时保留依据与覆盖，过期范围和较新判断的保护见新数据模型。"),
("AI实际补查是否共用基础Run互斥见第11节。","AI实际模型/工具执行可并行，不与基础Run共用活跃槽。"),
("分析给出有据影响；不自动改业务状态或当前采用结果","分析给出有据影响；不自动改业务状态，有效基础结果经范围/版本检查后自动采用，AI结果需明确采用"),
("采用策略待确认，历史不随新成员或任务编辑变化","有效基础结果自动采用，AI明确采用；历史不随新成员或任务编辑变化"),
("当前并未创建新表；需要先固定审计中仍有歧义的业务定义，再生成DDL并验证实际PostgreSQL约束。","新表已在21独立验证库创建并验证；迁移/ORM/枚举已生成，服务写入和完整C1–C6接线仍待实施，见[交接](../design/socai2-schema-implementation-20261103.md)。"),
])
# The last section is decisions-to-make, retain only genuinely unsettled policy.
p=ROOT/"docs/architecture/investigation-planning-design.md";s=p.read_text(encoding="utf-8")
s=re.sub(r"^.*AI.*是否.*共用.*活跃.*$", "AI执行已确认可并行；单活跃约束仅用于基础调查。",s,flags=re.M)
s=re.sub(r"^.*当前.*(?:认识|判断).*采用.*待(?:定|明确).*$", "采用已确认：有效基础结果自动更新，AI明确采用；旧范围/较新采用保护见数据模型。",s,flags=re.M)
p.write_text(s,encoding="utf-8")
update("docs/design/alert-incident-case-product-requirements.md",[
("AI需要实际补查时是否共用基础Run互斥仍需明确。","AI需要实际模型或工具执行时可并行，不与基础Run共用活跃槽。"),
("事件按成员最高等级呈现；不能用分诊置信度替代","保留成员最高等级自动汇总，允许人工事件覆盖并记录理由/人/时间；不修改成员，不用分诊置信度替代"),
("| 调查结果 → 案件当前判断 | 需要有明确采用依据与覆盖范围；最新一轮或最后一句回复不能直接覆盖全案判断 |","| 调查结果 → 案件当前判断 | 有效基础调查结果自动更新，AI结果需明确采用；保留依据与实际覆盖，过期范围和较新采用不能被旧Run覆盖 |"),
("发送涉及新的执行时遵守单活跃约束。","同Case只限制基础调查单活跃；AI问答的实际执行可以并行。"),
("待更新/领取本地代码的真实PG验收；AI补查是否共用执行互斥，以及取消/超时/未知处理","新schema的单活跃与关键竞争已在独立PG验证；服务端接线、取消/超时/未知处理仍须接入"),
("| 案件当前判断采用 | 有明确依据与覆盖范围，不能取最后一轮自动代替 | 谁可确认采用、如何处理新旧判断冲突、哪些变化要求重新确认 |","| 案件当前判断采用 | 有效基础结果自动采用，AI明确采用；当前范围匹配且不覆盖本轮期间的较新采用 | 人工采用权限、交互和冲突提示接入；自动采用函数需接入结果发布事务 |"),
])
# Explain current implementation without rewriting old backend facts.
update("docs/design/investigation-design-current-gap-review-20261103.md",[
("采用策略要在实现前明确，不能把保存AI答案直接变成采用","采用已确认：有效基础结果自动采用，AI明确采用；不能把保存AI答案直接变成采用"),
("当前下一步按用户最新要求，先完成[新库表建表前审计](frontend-data-model-audit-20261103.md)，固定字段类型/枚举/约束后生成迁移；C1–C6接线仍按工作包1继续。","第一轮审计与三项业务确认已完成；新表迁移/ORM/枚举/schema已生成并在独立PG验证。下一接新存储入口及结果发布，C1–C6接线仍按工作包1继续，见[实现交接](socai2-schema-implementation-20261103.md)。"),
("尚需产品决定的少量事项：哪类结果可以更新Case当前认识及如何采用；AI实际补查是否与基础Run共用单活跃约束。用户已定的基础Run手动启动和单活跃不重问；上述选择在相应实现工作包前确认，不阻止先定义完整基础流程。","已确认：有效基础结果自动更新当前判断，AI结果明确采用；AI执行可并行，单活跃仅限基础调查。剩余空/已解决Case策略按D04保留；既定口径不重复询问。"),
])
# Audit findings remain historical findings, current disposition is updated explicitly.
update("docs/design/frontend-data-model-audit-20261103.md",[
("**结论：先完成字段合同；尚不进入正式建表。**","**首轮审计完成，三项业务口径已确认，随后已生成迁移并在独立PG验证。**"),
("D01–D03已向用户集中询问、仍待答复","D01–D03已获得用户明确答复"),
("**未向自动迁移目录添加DDL，未访问或修改实际数据库。**","审计当时尚未建表；确认后的迁移和独立验证库事实见[后续实现交接](socai2-schema-implementation-20261103.md)，原静态审计回执保持。"),
("D02采用方式待确认；旧Case.summary不能自动回填为已采用","D02已确认有效基础自动采用、AI明确采用；旧Case.summary不能自动回填为已采用"),
("D01集中确认；保派生值，人工覆盖四列列为候选。","D01已确认；保派生值，人工覆盖四列已纳入迁移。"),
("D01回答后固定DDL；旧分类交页面团队明确去留","D01已落实物理约束；旧分类交页面团队明确去留"),
("D03集中确认；baseline唯一约束已确定，AI是否同槽单列","D03已确认：baseline单活跃，AI并行，无共用槽索引"),
("成员severity最大值；人工覆盖列等待D01，暂不开放写入","成员severity最大值保留；人工覆盖值/理由/人/时间已定义并验证"),
("## 6. 集中待确认项","## 6. 已确认决定与剩余边界"),
("保汇总且允许事件人工覆盖；决定incidents四个override列是否保留，不能修改成员等级","已确认保汇总且允许事件人工覆盖；四个override列保留，不能修改成员等级"),
("两类结果均明确采用；若自动采用基础结果，仍须范围/有效性/版本检查。表结构已支持两种","已确认有效基础结果自动采用、AI明确采用；范围/有效性/较新采用保护已实现数据库函数"),
("共用一活跃槽；直接决定runs的部分唯一索引条件","已确认只限制baseline单活跃，AI可并行；索引明确不含AI"),
("D01–D03已发出一组问题。","D01–D03已答复并同步到合同、DDL和主设计。"),
("1. 根据D01–D03答复一次固定合同；","1. 已根据D01–D03答复固定合同；"),
])
# Render the entire dictionary from the same source, including confirmed decisions.
def esc(v):return str(v if v is not None else "—").replace("|","／").replace("\n"," ")
md="# 新库表字段字典\n\n2026-11-03。D01–D03已确认，29表/458列/36枚举/38JSON合同已生成迁移并在独立验证库核对。字段合同不等于业务服务已接入，见[实现交接](socai2-schema-implementation-20261103.md)。来源：[结构化字典](socai2-data-contract-20261103.json)、[JSON schema](socai2-json-contracts-20261103.schema.json)。\n\n## 1. 全表规则\n\n"
for k,v in c["common"].items():md+="- **"+k+"**："+(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False))+"\n"
md+="\n## 2. 枚举定义\n\n| 名称 | 允许值 | 语义 |\n| --- | --- | --- |\n"
for k,v in c["enums"].items():md+=f"| {k} | {'、'.join(v['values'])} | {v['meaning']} |\n"
md+="\n## 3. 每表字段\n\n每表另有id UUID NOT NULL与tenant_id UUID NOT NULL；UUID由应用分配，tenant来自服务端。PRIMARY KEY(id)、UNIQUE(tenant_id,id)，tenant引用public.tenants。\n"
for i,t in enumerate(c["tables"],1):
 md+=f"\n### 3.{i} socai2.{t['name']}\n\n写入者：{t['owner']}。可变性：{t['mutability']}。\n\n| 字段 | PostgreSQL类型／合同 | 可空 | 默认 | 语义 |\n| --- | --- | --- | --- | --- |\n"
 for f in t["columns"]:
  ty=f["type"]
  if ty.startswith("ref."):ty="UUID → "+ty[4:]
  elif ty.startswith("enum."):ty="TEXT / "+ty[5:]
  elif ty.startswith("json."):ty="JSONB / "+ty[5:]
  md+=f"| {f['name']} | {esc(ty)} | {'是' if f['nullable'] else '否'} | {esc(f['default'])} | {esc(f['meaning'])} |\n"
 md+="\n"+"\n".join("- "+v for v in t["constraints"])+"\n"
md+="\n## 4. JSON内部字段和类型\n\n对象默认拒绝未定义字段；原始payload、工具注册参数、活动白名单是明确例外。JSON引用仍须服务端做来源/租户/范围验证，数据库JSON类型检查不代替语义校验。\n"
for k,v in c["contracts"].items():md+=f"\n### {k}\n\n{v['meaning']}\n\n```json\n{json.dumps(v['schema'],ensure_ascii=False,indent=2)}\n```\n"
md+="\n## 5. 关系、索引及写入规则\n\n"
for k in ["composite_unique_keys","deferred_constraints","application_invariants","index_plan","artifact_contracts","auto_adoption_policy"]:
 md+=f"### {k}\n\n```json\n{json.dumps(c[k],ensure_ascii=False,indent=2)}\n```\n\n"
md+="## 6. 已确认决定与剩余边界\n\n| ID | 项目 | 状态 | 决定/建议 |\n| --- | --- | --- | --- |\n"
for d in c["decisions"]:md+=f"| {d['id']} | {d['topic']} | {d['status']} | {d.get('decision',d.get('proposed'))} |\n"
md+="\nD04特殊流程尚未开放，不能据建表完成推断相关API已实现。旧表历史不自动回填或迁移，当前业务写入尚未切换。\n"
(D/"socai2-field-dictionary-20261103.md").write_text(md,encoding="utf-8")
schema=json.loads((D/"socai2-json-contracts-20261103.schema.json").read_text(encoding="utf-8"));schema["title"]="socai2 confirmed page data contracts"
(D/"socai2-json-contracts-20261103.schema.json").write_text(json.dumps(schema,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("confirmed design, PRD and field dictionary synchronized")
