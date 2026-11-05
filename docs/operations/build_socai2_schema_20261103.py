"""Generate reviewed, explicit SQL/ORM/contracts. Never connects to a database."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/"docs/design/socai2-data-contract-20261103.json"
C=json.loads(CAT.read_text(encoding="utf-8"))
if C.get("incremental_migrations"):
    raise SystemExit("Migration 123 is frozen. Apply the catalogue's incremental migrations; do not regenerate the baseline.")
TABLES={t["name"]:t for t in C["tables"]}
MIGRATION="123_socai2_page_data_model.sql"
def quote(v): return "'"+str(v).replace("'","''")+"'"
def ident(v):
    assert v.replace("_","").isalnum() and v==v.lower(),v
    return '"'+v+'"'
def table(v): return "socai2."+ident(v)
def cname(t,tag):
    value=t+"_"+tag
    return value if len(value)<=60 else value[:47]+"_"+hashlib.sha256(value.encode()).hexdigest()[:10]
def sqltype(v):
    if v.startswith("enum."):return "text"
    if v.startswith("ref."):return "uuid"
    if v.startswith("json."):return "jsonb"
    return v
SQL=["-- Generated from socai2-data-contract-20261103.json; do not edit by hand.",
     "-- D01: incident override; D02: valid baseline auto-adoption; D03: AI may run concurrently.",
     "-- New namespace only. No legacy backfill or runtime writer switch. Requires migrations 002/061.",
     "BEGIN;","CREATE SCHEMA IF NOT EXISTS socai2;","REVOKE ALL ON SCHEMA socai2 FROM PUBLIC;"]
CHECKS={};UQS={};FKS={};INDEXES=[]
def ck(t,tag,expr):CHECKS.setdefault(t,[]).append((cname(t,tag),expr))
def uq(t,tag,cols):UQS.setdefault(t,[]).append((cname(t,tag),cols))
def fk(t,tag,cols,dest,dcols,schema="socai2"):
    FKS.setdefault(t,[]).append((cname(t,tag),cols,schema,dest,dcols))
def ix(t,tag,cols,where=None,unique=False):
    name=cname(t,tag)
    INDEXES.append("CREATE "+("UNIQUE " if unique else "")+"INDEX IF NOT EXISTS "+ident(name)+" ON "+table(t)+" ("+cols+")"+(" WHERE "+where if where else "")+";")
for t in C["tables"]:
    n=t["name"]
    cols=['"id" uuid NOT NULL','"tenant_id" uuid NOT NULL']
    for f in t["columns"]:
        v=ident(f["name"])+" "+sqltype(f["type"])
        if not f["nullable"]:v+=" NOT NULL"
        d=f["default"]
        if d is not None:
            if d=="transaction_timestamp()":v+=" DEFAULT transaction_timestamp()"
            elif d=="{}":v+=" DEFAULT '{}'::text[]"
            elif d=="[]":v+=" DEFAULT '[]'::jsonb"
            elif d in ["1","0","false","true"]:v+=" DEFAULT "+d
            else:v+=" DEFAULT "+quote(d)
        cols.append(v)
        fn=ident(f["name"])
        if f["type"].startswith("enum."):
            ck(n,f["name"]+"_enum",fn+" IN ("+",".join(map(quote,C["enums"][f["type"][5:]]["values"]))+")")
        if f["type"].startswith("ref."):fk(n,f["name"]+"_fk",["tenant_id",f["name"]],f["type"][4:],["tenant_id","id"])
        if f["type"]=="uuid" and f["name"] in ["owner_id","assigned_by","closed_by","reopened_by","severity_override_by","resolved_by","created_by","adopted_by","added_by","linked_by","requested_by","saved_by","assignee_id","completed_by","changed_by","updated_by","author_id","edited_by"]:
            fk(n,f["name"]+"_user_fk",[f["name"]],"users",["id"],"public")
        if f["type"]=="uuid" and f["name"]=="connector_id":fk(n,"connector_fk",["connector_id"],"connectors",["id"],"public")
        if f["type"]=="bigint":ck(n,f["name"]+"_range",fn+(" > 0" if f["name"] in ["revision","row_version","seq","sequence"] else " >= 0"))
        if f["type"]=="char(64)":ck(n,f["name"]+"_sha",fn+" ~ '^[0-9a-f]{64}$'")
        if f["name"] in ["title","purpose","body","source_namespace","source_identity_key","source_incident_id","object_key","namespace","normalized_value","raw_value","operation_key","client_request_key"]:
            ck(n,f["name"]+"_nonblank","length(btrim("+fn+")) > 0")
        if f["type"].startswith("json."):
            key=f["type"][5:];kind=C["contracts"][key]["schema"].get("type")
            if kind in ["object","array"]:ck(n,f["name"]+"_json_type","jsonb_typeof("+fn+") = "+quote(kind))
    cols+=['PRIMARY KEY ("id")','UNIQUE ("tenant_id","id")','FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT']
    SQL.append("CREATE TABLE IF NOT EXISTS "+table(n)+" (\n    "+",\n    ".join(cols)+"\n);")
    for f in t["columns"]:SQL.append("COMMENT ON COLUMN "+table(n)+"."+ident(f["name"])+" IS "+quote(f["meaning"])+";")
for t,groups in C["composite_unique_keys"].items():
    for i,g in enumerate(groups):uq(t,"scope_key_"+str(i),g.split(","))
for t in ["alerts","incidents","cases"]:
    ck(t,"assignment","(assignment_state='assigned') = (owner_id IS NOT NULL)")
    ck(t,"unresolved_owner","assignment_state <> 'unresolved' OR nullif(btrim(owner_source_value),'') IS NOT NULL")
    ck(t,"priority","(priority_state='available' AND priority_value IS NOT NULL AND priority_value BETWEEN 0 AND 100 AND nullif(btrim(priority_source),'') IS NOT NULL) OR (priority_state<>'available' AND priority_value IS NULL)")
ck("alerts","event_time","(event_time_source='unknown') = (event_time IS NULL)")
ck("alerts","time_order","first_seen_at IS NULL OR last_seen_at IS NULL OR first_seen_at<=last_seen_at")
ck("incidents","severity_override","(severity_override IS NULL AND severity_override_reason IS NULL AND severity_override_at IS NULL AND severity_override_by IS NULL) OR (severity_override IS NOT NULL AND nullif(btrim(severity_override_reason),'') IS NOT NULL AND severity_override_at IS NOT NULL AND severity_override_by IS NOT NULL)")
ck("alert_assessments","confidence","(score_state='available' AND confidence IS NOT NULL AND confidence BETWEEN 0 AND 1) OR (score_state<>'available' AND confidence IS NULL)")
ck("alert_assessments","human_no_score","kind<>'human_feedback' OR confidence IS NULL")
ck("alert_objects","other_type","object_type<>'other' OR nullif(btrim(source_type),'') IS NOT NULL")
ck("alert_objects","asset_match","asset_match_state<>'matched' OR (asset_ref IS NOT NULL AND match_basis IS NOT NULL)")
uq("alerts","source_identity",["tenant_id","source_namespace","source_identity_key"])
uq("incidents","source_identity",["tenant_id","source_namespace","source_incident_id"])
for t,cols in {
"alert_materials":["tenant_id","alert_id","revision"],
"alert_source_refs":["tenant_id","material_id","source_namespace","source_event_id","relation_kind"],
"alert_objects":["tenant_id","material_id","object_key","source_path"],
"alert_assessments":["tenant_id","operation_key"],
"incident_alerts":["tenant_id","alert_id"],
"incident_diagnoses":["tenant_id","incident_id","revision"],
"case_alerts":["tenant_id","case_id","alert_id"],
"case_incidents":["tenant_id","case_id","incident_id"],
"case_assessments":["tenant_id","case_id","revision"],
"case_assessment_members":["tenant_id","assessment_id","alert_id"],
"run_members":["tenant_id","run_id","alert_id"],
"run_steps":["tenant_id","run_id","seq"],
"results":["tenant_id","operation_key"],
"result_members":["tenant_id","result_id","alert_id"],
"task_revisions":["tenant_id","task_id","revision"],
"messages":["tenant_id","conversation_id","sequence"],
}.items():uq(t,"business_key",cols)
uq("case_assessments","operation_key",["tenant_id","operation_key"])
uq("incident_diagnoses","run_key",["tenant_id","source_run_id"])
uq("messages","request_key",["tenant_id","conversation_id","client_request_key"])
for t in ["runs","artifacts","comments","response_links"]:
    ck(t,"one_parent","num_nonnulls(alert_id,incident_id,case_id)=1")
ck("activities","one_subject","num_nonnulls(subject_alert_id,subject_incident_id,subject_case_id)=1")
target_cols=["alert_id","incident_id","case_id","task_id","run_id","result_id","comment_id"]
ck("activity_targets","one_target","num_nonnulls("+",".join(target_cols)+")=1")
for col in target_cols:ix("activity_targets",col+"_once","tenant_id,activity_id,"+col,col+" IS NOT NULL",True)
for col in ["result_id","task_revision_id","artifact_id"]:
    ix("case_assessment_sources",col+"_once","tenant_id,assessment_id,"+col,col+" IS NOT NULL",True)
ck("case_assessment_sources","one_source","num_nonnulls(result_id,task_revision_id,artifact_id)=1")
ck("runs","kind_parent","(kind='alert_basic' AND alert_id IS NOT NULL) OR (kind='incident_diagnosis' AND incident_id IS NOT NULL) OR (kind IN ('baseline','ai_question') AND case_id IS NOT NULL)")
ck("runs","case_scope","(case_id IS NULL AND scope_revision IS NULL AND scope_kind IS NULL) OR (case_id IS NOT NULL AND scope_revision IS NOT NULL AND scope_kind IS NOT NULL)")
ck("runs","baseline_whole","kind<>'baseline' OR scope_kind='whole_case'")
ck("runs","pending_baseline","state<>'pending_update' OR (kind='baseline' AND started_at IS NULL AND ended_at IS NULL AND input_artifact_id IS NULL AND operation_key IS NULL AND request_hash IS NULL)")
ck("runs","start_fields","state NOT IN ('running','unknown','completed','failed') OR (started_at IS NOT NULL AND input_artifact_id IS NOT NULL AND executor_version IS NOT NULL AND operation_key IS NOT NULL AND request_hash IS NOT NULL)")
ck("runs","end_fields","(state IN ('completed','failed','cancelled')) = (ended_at IS NOT NULL)")
ck("runs","time_order","ended_at IS NULL OR started_at IS NULL OR ended_at>=started_at")
ck("runs","window","(window_start IS NULL AND window_end IS NULL) OR (window_start IS NOT NULL AND window_end IS NOT NULL AND window_start<=window_end)")
ck("runs","request_pair","(operation_key IS NULL)=(request_hash IS NULL)")
ck("runs","retry_self","retry_of_run_id IS DISTINCT FROM id")
ix("runs","request_once","tenant_id,kind,operation_key","operation_key IS NOT NULL",True)
ix("runs","one_pending_baseline","tenant_id,case_id","kind='baseline' AND state='pending_update'",True)
ix("runs","one_active_baseline","tenant_id,case_id","kind='baseline' AND state IN ('running','unknown')",True)
ck("run_members","read_material","read_state<>'read' OR material_id IS NOT NULL")
ck("run_steps","not_self","parent_step_id IS DISTINCT FROM id AND retry_of_step_id IS DISTINCT FROM id")
ck("run_steps","time_order","ended_at IS NULL OR started_at IS NULL OR ended_at>=started_at")
ck("run_steps","query_rows","returned_rows IS NULL OR (kind='tool' AND state='completed' AND returned_rows>=0)")
ck("run_steps","no_parent_cost","kind<>'stage' OR usage IS NULL")
ck("artifacts","content","num_nonnulls(content_json,content_text,blob_ref)=1 OR (material_state='unavailable' AND num_nonnulls(content_json,content_text,blob_ref)=0 AND nullif(retention->>'reason','') IS NOT NULL)")
ck("artifacts","step_has_run","step_id IS NULL OR run_id IS NOT NULL")
ck("results","answer_kind","(kind='ai_saved')=(source_answer_id IS NOT NULL)")
ck("results","conclusion","(conclusion_state='unavailable' AND conclusion IS NULL) OR (conclusion_state<>'unavailable' AND nullif(btrim(conclusion),'') IS NOT NULL)")
ck("results","comparison_self","comparison_result_id IS DISTINCT FROM id AND supersedes_result_id IS DISTINCT FROM id")
ck("results","initial_comparison","change_kind<>'initial' OR comparison_result_id IS NULL")
ck("results","human_edit","NOT ('conclusion'=ANY(edited_fields)) OR conclusion_origin='human'")
ck("result_members","coverage","NOT conclusion_covered OR assessment_state IN ('analyzed','unresolved')")
ix("results","baseline_root","tenant_id,source_run_id","kind='baseline' AND supersedes_result_id IS NULL",True)
ix("results","answer_root","tenant_id,source_answer_id","kind='ai_saved' AND supersedes_result_id IS NULL",True)
ix("results","single_revision","tenant_id,supersedes_result_id","supersedes_result_id IS NOT NULL",True)
ck("task_revisions","completed_feedback","state<>'completed' OR (nullif(btrim(result_text),'') IS NOT NULL AND result_scope IS NOT NULL AND completed_at IS NOT NULL AND completed_by IS NOT NULL)")
ck("task_revisions","completion_pair","(completed_at IS NULL)=(completed_by IS NULL)")
ck("tasks","finding_source","origin_finding_id IS NULL OR origin_result_id IS NOT NULL")
ck("messages","not_self","in_reply_to IS DISTINCT FROM id")
ck("messages","user_text","role<>'user' OR nullif(btrim(content),'') IS NOT NULL")
ck("messages","answer_fields","role<>'assistant' OR state<>'completed' OR (nullif(btrim(content),'') IS NOT NULL AND source_run_id IS NOT NULL AND input_artifact_id IS NOT NULL AND answered_at IS NOT NULL)")
ck("response_links","source","(result_id IS NOT NULL AND proposal_id IS NOT NULL AND legacy_proposal_ref IS NULL) OR (result_id IS NULL AND proposal_id IS NULL AND legacy_proposal_ref IS NOT NULL)")
ck("response_links","has_target","approval_id IS NOT NULL OR action_id IS NOT NULL")
for col in ["approval_id","action_id"]:
    ix("response_links",col+"_proposal_once","tenant_id,result_id,proposal_id,external_namespace,"+col,"result_id IS NOT NULL AND "+col+" IS NOT NULL",True)

# Strong parent-scoped references supplement basic tenant+id FK.
def scoped(t,col,dest,parents,target_parents=None):
    fk(t,col+"_scope_fk",["tenant_id"]+parents+[col],dest,["tenant_id"]+(target_parents or parents)+["id"])
for col,dst in [("latest_material_id","alert_materials"),("latest_triage_id","alert_assessments"),("latest_feedback_id","alert_assessments")]:
    scoped("alerts",col,dst,["id"],["alert_id"])
scoped("alerts","latest_explanation_id","artifacts",["id"],["alert_id"])
scoped("incidents","latest_diagnosis_id","incident_diagnoses",["id"],["incident_id"])
scoped("cases","current_assessment_id","case_assessments",["id"],["case_id"])
for t in ["alert_source_refs","alert_objects"]:scoped(t,"material_id","alert_materials",["alert_id"])
scoped("alert_assessments","input_material_id","alert_materials",["alert_id"])
scoped("alert_assessments","source_run_id","runs",["alert_id"])
scoped("incident_diagnoses","source_run_id","runs",["incident_id"])
scoped("incident_diagnoses","input_artifact_id","artifacts",["incident_id"])
for t in ["case_assessment_sources","case_assessment_members"]:
    scoped(t,"assessment_id","case_assessments",["case_id"])
for col,dst in [("result_id","results"),("task_revision_id","task_revisions"),("artifact_id","artifacts")]:
    scoped("case_assessment_sources",col,dst,["case_id"])
for t in ["results","run_members"]:
    scoped(t,"source_run_id" if t=="results" else "run_id","runs",["case_id"])
for col in ["comparison_result_id"]:scoped("runs",col,"results",["case_id"])
scoped("runs","input_artifact_id","artifacts",["id"],["run_id"])
for col in ["material_id","triage_id","feedback_id"]:
    scoped("run_members",col,"alert_materials" if col=="material_id" else "alert_assessments",["alert_id"])
for col in ["parent_step_id","retry_of_step_id"]:scoped("run_steps",col,"run_steps",["run_id"])
for col in ["input_artifact_id","output_artifact_id"]:scoped("run_steps",col,"artifacts",["run_id"])
scoped("artifacts","step_id","run_steps",["run_id"])
for parent in ["case_id","alert_id","incident_id"]:scoped("artifacts","run_id","runs",[parent])
for col in ["comparison_result_id","supersedes_result_id"]:scoped("results",col,"results",["case_id"])
scoped("results","source_answer_id","messages",["case_id"])
for col in ["input_artifact_id","graph_artifact_id","report_artifact_id"]:
    scoped("results",col,"artifacts",["case_id"])
fk("result_members","result_run_fk",["tenant_id","case_id","run_id","result_id"],"results",["tenant_id","case_id","source_run_id","id"])
fk("result_members","run_member_fk",["tenant_id","case_id","run_id","alert_id"],"run_members",["tenant_id","case_id","run_id","alert_id"])
scoped("tasks","current_revision_id","task_revisions",["case_id","id"],["case_id","task_id"])
scoped("tasks","origin_result_id","results",["case_id"])
scoped("task_revisions","task_id","tasks",["case_id"])
scoped("messages","conversation_id","conversations",["case_id"])
scoped("messages","in_reply_to","messages",["case_id","conversation_id"])
scoped("messages","source_run_id","runs",["case_id"])
scoped("messages","input_artifact_id","artifacts",["case_id"])
scoped("graph_explorations","base_result_id","results",["case_id"])
for col in ["base_graph_artifact_id","base_input_artifact_id"]:scoped("graph_explorations",col,"artifacts",["case_id"])
scoped("response_links","result_id","results",["case_id"])
for parent in ["case_id","alert_id","incident_id"]:scoped("response_links","receipt_artifact_id","artifacts",[parent])

def add_constraint(t,n,body):
    SQL.append("DO $migration$ BEGIN\n IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid="+quote("socai2."+t)+"::regclass AND conname="+quote(n)+") THEN\n ALTER TABLE "+table(t)+" ADD CONSTRAINT "+ident(n)+" "+body+";\n END IF;\nEND $migration$;")
for t,items in UQS.items():
    for n,cols in items:add_constraint(t,n,"UNIQUE ("+",".join(map(ident,cols))+")")
for t,items in CHECKS.items():
    for n,expr in items:add_constraint(t,n,"CHECK ("+expr+")")
for t,items in FKS.items():
    for n,cols,sch,dst,dcols in items:add_constraint(t,n,"FOREIGN KEY ("+",".join(map(ident,cols))+") REFERENCES "+sch+"."+ident(dst)+" ("+",".join(map(ident,dcols))+") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED")
# B-tree listing, reverse relation and history access; no blanket JSON GIN.
for t,groups in {
"alerts":["tenant_id,event_time DESC,id","tenant_id,handling_status,event_time DESC,id","tenant_id,severity,event_time DESC,id","tenant_id,owner_id,event_time DESC,id"],
"incidents":["tenant_id,business_updated_at DESC,id","tenant_id,handling_status,business_updated_at DESC,id"],
"case_alerts":["tenant_id,alert_id,case_id"],"case_incidents":["tenant_id,incident_id,case_id"],
"runs":["tenant_id,case_id,requested_at DESC,id","tenant_id,alert_id,requested_at DESC,id","tenant_id,incident_id,requested_at DESC,id"],
"results":["tenant_id,case_id,saved_at DESC,id"],"task_revisions":["tenant_id,case_id,state,due_at"],
"artifacts":["tenant_id,run_id,kind,captured_at,id","tenant_id,case_id,kind,captured_at,id"],
"alert_objects":["tenant_id,object_type,normalized_value,alert_id","tenant_id,material_id"],
"incident_alerts":["tenant_id,incident_id,alert_id"],
"activities":["tenant_id,subject_case_id,occurred_at DESC,id","tenant_id,subject_incident_id,occurred_at DESC,id","tenant_id,subject_alert_id,occurred_at DESC,id"],
}.items():
    for i,g in enumerate(groups):ix(t,"read_"+str(i),g)
for col in target_cols:ix("activity_targets",col+"_lookup","tenant_id,"+col+",activity_id",col+" IS NOT NULL")
for col in ["alert_id","incident_id","case_id"]:ix("comments",col+"_lookup","tenant_id,"+col+",created_at,id",col+" IS NOT NULL")
SQL+=INDEXES
# Physical guards maintained separately for review, included in this atomic migration.
SQL.append((ROOT/"docs/design/socai2-schema-guards-20261103.sql").read_text(encoding="utf-8"))
for t in TABLES:
    SQL+=["ALTER TABLE "+table(t)+" ENABLE ROW LEVEL SECURITY;","ALTER TABLE "+table(t)+" FORCE ROW LEVEL SECURITY;",
          "DROP POLICY IF EXISTS tenant_scope ON "+table(t)+";",
          "CREATE POLICY tenant_scope ON "+table(t)+" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());"]
SQL.append("DO $grants$ BEGIN\n IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN\n GRANT USAGE ON SCHEMA socai2 TO aisoc_app;\n GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA socai2 TO aisoc_app;\n REVOKE TRUNCATE,REFERENCES,TRIGGER ON ALL TABLES IN SCHEMA socai2 FROM aisoc_app;\n END IF;\nEND $grants$;")
for t in C["tables"]:
    if t["mutability"]=="append_only":
        SQL.append("DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON "+table(t["name"])+" FROM aisoc_app; END IF; END $grants$;")
# Record within the same transaction too; runner's follow-up ON CONFLICT remains harmless.
SQL+=["INSERT INTO public.aisoc_schema_migrations(name) VALUES ("+quote(MIGRATION)+") ON CONFLICT DO NOTHING;","COMMIT;"]
out=ROOT/"services/api/migrations"/MIGRATION
out.write_text("\n\n".join(SQL)+"\n",encoding="utf-8")
# Explicit ORM columns. No autoload or automatic create_all at application import.
orm=['"""Generated socai2 ORM. Explicit opt-in; does not switch existing writers."""',
"from datetime import datetime","from decimal import Decimal","from uuid import UUID as PyUUID",
"from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKeyConstraint, Numeric, Text, UniqueConstraint, text",
"from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID, CHAR",
"from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column","",
"class Socai2Base(DeclarativeBase):","    pass",""]
def cls(n):return "".join(x.title() for x in n.split("_"))
def pytype(f):
    t=f["type"]; nullable=f["nullable"]
    if t=="uuid" or t.startswith("ref."):a,b="PyUUID","UUID(as_uuid=True)"
    elif t=="bigint":a,b="int","BigInteger"
    elif t=="boolean":a,b="bool","Boolean"
    elif t=="timestamptz":a,b="datetime","TIMESTAMP(timezone=True)"
    elif t=="text[]":a,b="list[str]","ARRAY(Text)"
    elif t.startswith("numeric"):a,b="Decimal","Numeric"+t[len("numeric"):]
    elif t.startswith("char"):a,b="str","CHAR"+t[len("char"):]
    elif t.startswith("json."):a,b="object","JSONB"
    else:a,b="str","Text"
    return a+(" | None" if nullable else ""),b
for t in C["tables"]:
    n=t["name"]
    orm+=["class "+cls(n)+"(Socai2Base):","    __tablename__ = "+repr(n),
          "    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)",
          "    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)"]
    for f in t["columns"]:
        pt,st=pytype(f);kw=", nullable="+str(f["nullable"])
        d=f["default"]
        if d is not None:
            sd=d if d in ["transaction_timestamp()","0","1","true","false"] else "'{}'::text[]" if d=="{}" else "'[]'::jsonb" if d=="[]" else quote(d)
            kw+=", server_default=text("+repr(sd)+")"
        orm.append("    "+f["name"]+": Mapped["+pt+"] = mapped_column("+st+kw+")")
    orm.append("    __table_args__ = (")
    orm.append("        UniqueConstraint('tenant_id', 'id'),")
    for name,cols in UQS.get(n,[]):orm.append("        UniqueConstraint("+", ".join(map(repr,cols))+", name="+repr(name)+"),")
    for name,expr in CHECKS.get(n,[]):orm.append("        CheckConstraint("+repr(expr)+", name="+repr(name)+"),")
    for name,cols,sch,dst,dcols in FKS.get(n,[]):
        if sch=="public":continue # cross-metadata legacy FKs owned by migration
        orm.append("        ForeignKeyConstraint("+repr(cols)+", "+repr(["socai2."+dst+"."+x for x in dcols])+", name="+repr(name)+", ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),")
    orm+=["        {'schema': 'socai2'},","    )",""]
(ROOT/"services/api/app/models/socai2.py").write_text("\n".join(orm)+"\n",encoding="utf-8")
package=ROOT/"services/api/app/socai2"
package.mkdir(exist_ok=True)
(package/"__init__.py").write_text('"""Explicit new data contracts; existing API paths remain unchanged."""\n',encoding="utf-8")
enums=["# Generated from the reviewed data contract.","from enum import StrEnum",""]
for name,e in C["enums"].items():
    enums+=["class "+cls(name)+"(StrEnum):"]+["    "+v.upper()+" = "+repr(v) for v in e["values"]]+[""]
enums+=["ENUM_VALUES = {"]+["    "+repr(k)+": tuple(v.value for v in "+cls(k)+")," for k in C["enums"]]+["}"]
(package/"enums.py").write_text("\n".join(enums)+"\n",encoding="utf-8")
schemas={"$schema":"https://json-schema.org/draft/2020-12/schema","$defs":{k:v["schema"] for k,v in C["contracts"].items()}}
(package/"contracts.schema.json").write_text(json.dumps(schemas,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
manifest={"migration":str(out),"tables":len(TABLES),"columns":sum(len(t["columns"])+2 for t in C["tables"]),"checks":sum(map(len,CHECKS.values())),"unique_constraints":sum(map(len,UQS.values())),"foreign_keys":sum(map(len,FKS.values())),"indexes":len(INDEXES),"catalog_sha256":hashlib.sha256(CAT.read_bytes()).hexdigest(),"migration_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"not_database_validated":True}
(ROOT/"docs/operations/socai2-schema-generated-20261103.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(manifest,ensure_ascii=False))
