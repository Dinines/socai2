"""Static design checks only. No database, application service, model or network calls."""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs/design"
OUT = ROOT / ("docs/operations/socai2-contract-final-20261103.json" if "--final" in sys.argv else "docs/operations/frontend-data-model-audit-20261103.json")
cat = json.loads((DESIGN / "socai2-data-contract-20261103.json").read_text(encoding="utf-8"))
schema = json.loads((DESIGN / "socai2-json-contracts-20261103.schema.json").read_text(encoding="utf-8"))
checks = []
def check(name, ok, detail=None):
    checks.append({"name":name, "passed":bool(ok), "detail":detail})
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

tables = {x["name"]:x for x in cat["tables"]}
check("table names unique and count29", len(tables)==len(cat["tables"])==29)
check("458 physical column definitions", sum(len(x["columns"])+2 for x in tables.values())==458)
check("36 enum families", len(cat["enums"])==36)
check("38 JSON contracts", len(cat["contracts"])==38)
field_errors=[]
for t in tables.values():
    names=[f["name"] for f in t["columns"]]
    if len(set(names))!=len(names):field_errors.append(t["name"]+":duplicate")
    for f in t["columns"]:
        if not f["meaning"] or not isinstance(f["nullable"],bool):field_errors.append(f["name"]+":missing definition")
        kind,sep,target=f["type"].partition(".")
        if sep:
            lookup={"ref":tables,"enum":cat["enums"],"json":cat["contracts"]}.get(kind,{})
            if target not in lookup:field_errors.append(t["name"]+"."+f["name"]+":"+f["type"])
check("all column type and reference names defined", not field_errors, field_errors)
Draft202012Validator.check_schema(schema)
check("draft2020 JSON schema meta-validation", True)
check("catalog JSON definitions equal schema", schema["$defs"]=={k:v["schema"] for k,v in cat["contracts"].items()})
def walk_refs(v):
    if isinstance(v,dict):
        if "$ref" in v:yield v["$ref"]
        for x in v.values():yield from walk_refs(x)
    elif isinstance(v,list):
        for x in v:yield from walk_refs(x)
unresolved=[r for r in walk_refs(schema) if not r.startswith("#/$defs/") or r[8:] not in schema["$defs"]]
check("all JSON references resolve locally",not unresolved,unresolved)
def valid(contract,value,expected,label):
    v=Draft202012Validator({"$ref":"#/$defs/"+contract,"$defs":schema["$defs"]},format_checker=FormatChecker())
    errors=list(v.iter_errors(value))
    check(label,(not errors)==expected, None if (not errors)==expected else [e.message for e in errors[:3]])

uid="00000000-0000-4000-8000-000000000001"
scope={"kind":"whole_case","alert_ids":[uid],"object_keys":[],"window_start":None,"window_end":None,"limitations":[]}
valid("scope",scope,True,"scope explicit identities accepted")
bad=copy.deepcopy(scope);bad["kind"]="all_guess";valid("scope",bad,False,"unknown scope enum rejected")
bad=copy.deepcopy(scope);bad["alert_ids"]=["not-a-uuid"];valid("scope",bad,False,"internal bad UUID rejected")
valid("object_attributes",{"src_port":65535,"pid":"0042"},True,"port upper bound and source PID accepted")
valid("object_attributes",{"src_port":65536},False,"invalid port rejected")
valid("object_attributes",{"invented_fact":True},False,"undeclared projected property rejected")
d={"rule_id":None,"rule_name":None,"tactics":[],"techniques":[],"labels_provided":False,"confidence_state":"not_provided","confidence_value":None,"confidence_label":None,"confidence_rationale":None,"score_source":None,"ocsf_class_uid":None}
valid("detection",d,True,"missing detection confidence stays null")
bad=copy.deepcopy(d);bad["confidence_value"]=50;valid("detection",bad,False,"default50 without computation rejected")
d.update(confidence_state="available",confidence_value=0,score_source="fixture")
valid("detection",d,True,"explicit zero detection score accepted")
bad=copy.deepcopy(d);bad["confidence_value"]=101;valid("detection",bad,False,"out of range detection score rejected")
args={"tool_name":"fixture_tool","contract_version":"test.v1","scope":scope,"limit":200,"parameters":{}}
q={"schema_version":"tool.v1","tool_name":"fixture_tool","contract_version":"test.v1","actual_args":args,"state":"completed","rows":[],"returned_rows":0,"truncated":False,"query_id":None,"error":None,"captured_at":"2026-11-03T01:00:00Z"}
valid("tool_exchange",q,True,"successful empty query accepted")
bad=copy.deepcopy(q);bad["state"]="failed";valid("tool_exchange",bad,False,"failure cannot masquerade as successful zero rows")
bad["rows"]=None;bad["returned_rows"]=None;bad["error"]={"code":"fixture_timeout","message":"synthetic","retryable":True,"occurred_at":"2026-11-03T01:00:00Z"}
valid("tool_exchange",bad,True,"query failure with unavailable rows accepted")
ref={"type":"artifact","id":uid,"external":None,"source_path":"/rows/0","row_keys":[],"role":"observation"}
valid("evidence_ref",ref,True,"typed internal evidence accepted")
bad=copy.deepcopy(ref);bad["id"]=None;valid("evidence_ref",bad,False,"missing evidence identity rejected")
valid("actor",{"type":"user","user_id":uid,"name_snapshot":"synthetic user","service_name":None,"service_version":None},True,"identified human accepted")
valid("actor",{"type":"user","user_id":None,"name_snapshot":"synthetic user","service_name":None,"service_version":None},False,"human actor without identity rejected")
usage={"input_tokens":0,"output_tokens":0,"cached_input_tokens":None,"reasoning_tokens":None,"total_tokens":0,"cost":None,"currency":None,"price_version":None,"usage_state":"reported","cost_state":"unpriced","request_id":None}
valid("usage",usage,True,"known zero tokens and unknown cost accepted")
bad=copy.deepcopy(usage);bad["cost"]=0;valid("usage",bad,False,"unpriced cost cannot become zero")
bad=copy.deepcopy(usage);bad.update(cost_state="priced",cost=0,currency="USD",price_version="fixture");valid("usage",bad,True,"explicit priced zero accepted")

dict_text=(DESIGN/"socai2-field-dictionary-20261103.md").read_text(encoding="utf-8")
dictionary_errors=[]
for name,t in tables.items():
    m=re.search(r"### 3\.\d+ socai2\."+re.escape(name)+r"\n(.*?)(?=\n### 3\.|\n## 4\.)",dict_text,re.S)
    if not m:dictionary_errors.append(name+":missing table");continue
    fields=re.findall(r"^\| ([a-z_][a-z0-9_]*) \|",m.group(1),re.M)
    if len(fields)!=len(set(fields)) or set(fields)!={f["name"] for f in t["columns"]}:dictionary_errors.append(name+":column mismatch")
check("rendered dictionary columns match catalog",not dictionary_errors,dictionary_errors)
audit=(DESIGN/"frontend-data-model-audit-20261103.md").read_text(encoding="utf-8")
old=audit.split("### 5.1")[1].split("### 5.2")[0]
new=audit.split("### 5.2")[1].split("### 5.3")[0]
check("85 old matrix rows mapped",len(re.findall(r"^\| [AIDT]\d{2} \|",old,re.M))==85)
check("36 result rows mapped",len(re.findall(r"^\| D\d{2} \|",new,re.M))==36)
docs=[DESIGN/"investigation-data-schema-plan-20261103.md",DESIGN/"frontend-data-model-audit-20261103.md",DESIGN/"socai2-field-dictionary-20261103.md",ROOT/"docs/architecture/investigation-planning-design.md",DESIGN/"investigation-design-current-gap-review-20261103.md",ROOT/"docs/investigation/README.md"]
if "--final" in sys.argv:
    docs.append(DESIGN/"socai2-schema-implementation-20261103.md")
broken=[]; formatting=[];link_count=0
for p in docs:
    text=p.read_text(encoding="utf-8")
    in_code=False; widths=[]
    for line in text.splitlines():
        if line.startswith("```"):
            in_code=not in_code
        if in_code:continue
        if line.startswith("|"):
            w=len(line.split("|"))
            if widths and widths[-1]!=w:formatting.append(str(p.name)+":table width")
            widths.append(w)
        else:widths=[]
    if in_code:formatting.append(str(p.name)+":fence")
    for href in re.findall(r"\]\(([^)]+)\)",text):
        if href.startswith(("http:","https:","#")):continue
        target=(p.parent/href.split("#")[0]).resolve()
        link_count+=1
        if not target.exists() and target!=OUT.resolve():broken.append(str(p.name)+":"+href)
check("local document links",not broken,{"count":link_count,"broken":broken})
check("Markdown tables and fences",not formatting,formatting)
prior=json.loads((ROOT/"docs/operations/investigation-design-current-gap-review-20261103.json").read_text(encoding="utf-8"))
source_files=[x for x in prior["source_manifest"] if "/services/" in x["path"] or "/prototypes/" in x["path"]]
changed=[x["path"] for x in source_files if not Path(x["path"]).is_file() or sha(x["path"])!=x["sha256"]]
check("prior backend and prototype manifest unchanged",not changed,{"files":len(source_files),"changed":changed})
receipt={"date":"2026-11-03","scope":"design audit only; no DDL or business execution","counts":{"tables":len(tables),"physical_column_definitions":458,"enum_families":36,"json_contracts":38,"mapped_old_fields":85,"mapped_result_fields":36},"checks":checks,"all_static_checks_passed":all(x["passed"] for x in checks),"not_verified":["PostgreSQL DDL/FK/unique/RLS execution","two-session transactions and freeze guards","runtime DTO or Fusion writes","model/report semantic correctness","remote branch freshness"],"pending_decisions":cat["decisions"],"actions":{"database_calls":0,"new_runs":0,"model_calls":0,"tool_business_calls":0,"deployments":0,"new_commits":0},"manifest":[{"path":str(p),"sha256":sha(p)} for p in docs+[DESIGN/"socai2-data-contract-20261103.json",DESIGN/"socai2-json-contracts-20261103.schema.json"]]}
OUT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"checks":len(checks),"passed":sum(x["passed"] for x in checks),"failed":[x for x in checks if not x["passed"]],"receipt":str(OUT)},ensure_ascii=False))
raise SystemExit(0 if receipt["all_static_checks_passed"] else 1)
