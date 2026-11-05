"""Explicit isolated database on the existing PG instance; synthetic data only."""
import argparse
import hashlib
import json
import shlex
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID

ROOT=Path(__file__).resolve().parents[2]
DATABASE="socai2_schema_review_20261103_a1"
CONTAINER="spirithub-postgres-1"
READER="socai2_schema_review_20261103_a1_reader"
SSH=["ssh","-F","C:/Users/lychee/.ssh/config","-i","C:/Users/lychee/.ssh/id_ed25519_socai2",
     "-o","UserKnownHostsFile=C:/Users/lychee/.ssh/known_hosts","-o","StrictHostKeyChecking=yes",
     "-o","BatchMode=yes","-o","ConnectTimeout=10","root@192.168.1.21"]
MIGRATION=ROOT/"services/api/migrations/123_socai2_page_data_model.sql"
EVIDENCE=ROOT/"docs/operations/evidence/socai2-schema-20261103"
def remote(args,data=None):
    return subprocess.run(SSH+[shlex.join(args)],input=data,capture_output=True,timeout=45)
def query(sql,db=DATABASE):
    assert db in [DATABASE,"postgres"]
    args=["docker","exec","-i",CONTAINER,"psql","-X","-v","ON_ERROR_STOP=1","-v","VERBOSITY=verbose",
          "-U","spirithub","-d",db,"-A","-t","-q"]
    p=remote(args,sql.encode("utf-8"))
    return p.returncode,p.stdout.decode("utf-8","replace").strip(),p.stderr.decode("utf-8","replace").strip()
def run(sql):
    code,out,err=query(sql)
    if code: raise RuntimeError(err)
    return out
def save(name,detail):
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    (EVIDENCE/name).write_text(json.dumps(detail,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def setup():
    code,out,err=query("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname='"+DATABASE+"');","postgres")
    if code or out!="f":raise RuntimeError("database not provably new; refusing overwrite: "+out+err)
    code,out,err=query("CREATE DATABASE "+DATABASE+" TEMPLATE template0; COMMENT ON DATABASE "+DATABASE+" IS 'socai2 schema review 20261103 a1; synthetic data only; no business writer switch';","postgres")
    save("database-create.json",{"code":code,"stdout":out,"stderr":err,"database":DATABASE})
    if code:raise RuntimeError(err)
    bootstrap="""
CREATE TABLE public.tenants(id uuid PRIMARY KEY);
CREATE TABLE public.users(id uuid PRIMARY KEY,tenant_id uuid NOT NULL REFERENCES public.tenants(id));
CREATE TABLE public.connectors(id uuid PRIMARY KEY,tenant_id uuid NOT NULL REFERENCES public.tenants(id));
CREATE TABLE public.aisoc_schema_migrations(name text PRIMARY KEY,applied_at timestamptz NOT NULL DEFAULT now());
CREATE FUNCTION public.current_tenant_id() RETURNS uuid LANGUAGE sql STABLE
 AS $$ SELECT nullif(current_setting('app.current_tenant_id',true),'')::uuid $$;
"""
    code,out,err=query(bootstrap)
    save("bootstrap.json",{"code":code,"stdout":out,"stderr":err})
    if code:raise RuntimeError(err)
def apply():
    payload=MIGRATION.read_bytes()
    code,out,err=query(payload.decode("utf-8"))
    save("apply-"+hashlib.sha256(payload).hexdigest()[:12]+".json",{"code":code,"stdout":out,"stderr":err,"sha256":hashlib.sha256(payload).hexdigest()})
    if code:raise RuntimeError(err)
    print(json.dumps({"applied_to":DATABASE,"postgres":run("SHOW server_version;"),"tables":run("SELECT count(*) FROM pg_tables WHERE schemaname='socai2';")}))
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("action",choices=["setup","apply","test","test_tail","extra","finish_extra"])
    action=ap.parse_args().action
    if action=="setup":setup()
    elif action=="apply":apply()
    elif action=="extra":extra_tests()
    elif action=="finish_extra":finish_extra()
    else:tests(resume=action=="test_tail")

def uid(n):return str(UUID(int=n))
def lit(s):return "'"+str(s).replace("'","''")+"'"
def j(v):return lit(json.dumps(v,ensure_ascii=False))+"::jsonb"
T=uid(1);T2=uid(2);USER=uid(3)
def scope(alerts):
    return {"kind":"whole_case","alert_ids":alerts,"object_keys":[],"window_start":None,"window_end":None,"limitations":[]}
def artifact_sql(aid,case,rid,alerts,run_kind="baseline"):
    payload={"schema_version":"input.v1","run_kind":"baseline","scope_revision":1,"scope":scope(alerts),"source_materials":[],"prior_results":[],"task_revisions":[],"comparison_result_id":None,"projection_version":"fixture.v1","omissions":[],"captured_at":"2026-11-03T00:00:00Z"}
    payload["run_kind"]=run_kind
    if run_kind=="ai_question":payload["scope"]["kind"]="selected_alerts"
    retention={"original_size_bytes":None,"retained_size_bytes":None,"original_sha256":None,"retained_sha256":None,"truncated":False,"reason":None,"omitted_paths":[]}
    return f"""INSERT INTO socai2.artifacts(id,tenant_id,case_id,run_id,kind,schema_version,content_json,mime_type,captured_at,material_state,source_refs,retention)
VALUES('{aid}','{T}','{case}','{rid}','input_snapshot','input.v1',{j(payload)},'application/json',clock_timestamp(),'complete','[]',{j(retention)});"""
def pending_sql(rid,case,revision=1):
    return f"""INSERT INTO socai2.runs(id,tenant_id,case_id,kind,title,purpose,trigger,scope_revision,scope_kind,state)
VALUES('{rid}','{T}','{case}','baseline','synthetic baseline','schema test','manual',{revision},'whole_case','pending_update');"""
def member_sql(mid,rid,case,alert):
    return f"INSERT INTO socai2.run_members(id,tenant_id,run_id,case_id,alert_id) VALUES('{mid}','{T}','{rid}','{case}','{alert}');"
def add_alert_sql(aid):
    return f"INSERT INTO socai2.alerts(id,tenant_id,source_namespace,source_identity_key,title) VALUES('{aid}','{T}','synthetic',{lit(aid)},'synthetic alert');"
def add_case_member(mid,case,alert):
    return f"INSERT INTO socai2.case_alerts(id,tenant_id,case_id,alert_id,membership_source,source_operation_id) VALUES('{mid}','{T}','{case}','{alert}','manual','{mid}');"
def fixture(base,count=1):
    f={"case":uid(base+1),"run":uid(base+30),"input":uid(base+50),"alerts":[uid(base+10+i) for i in range(count)]}
    sql=f"BEGIN; INSERT INTO socai2.cases(id,tenant_id,title,scope_revision) VALUES('{f['case']}','{T}','synthetic case',1);"
    for i,a in enumerate(f["alerts"]):sql+=add_alert_sql(a)+add_case_member(uid(base+20+i),f["case"],a)
    sql+=pending_sql(f["run"],f["case"])
    for i,a in enumerate(f["alerts"]):sql+=member_sql(uid(base+40+i),f["run"],f["case"],a)
    sql+=artifact_sql(f["input"],f["case"],f["run"],f["alerts"])+"COMMIT;"
    run(sql);return f
def claim(f,expected=1):
    return f"""UPDATE socai2.runs SET state='running',input_artifact_id='{f["input"]}',executor_version='fixture.v1',
operation_key='claim:{f["run"]}',request_hash=repeat('a',64),started_at=clock_timestamp(),row_version=row_version+1
WHERE tenant_id='{T}' AND id='{f["run"]}' AND state='pending_update' AND scope_revision={expected} RETURNING 'CLAIMED';"""
def result_sql(f,base,validation="accepted",origin="model",kind="baseline",answer=None,input_id=None):
    rid=uid(base+60); f["result"]=rid
    impact={"summary":"synthetic","supported_changes":[],"cannot_generalize":[],"affected_scope":scope(f["alerts"]),"next_steps":[]}
    valid=validation=="accepted"
    sql=f"""INSERT INTO socai2.results(id,tenant_id,case_id,kind,source_run_id,source_answer_id,title,purpose,conclusion,conclusion_state,
conclusion_origin,validation_state,closing_note,findings,questions,recommendations,change_kind,case_impact,input_artifact_id,delivery_state,created_at,operation_key)
VALUES('{rid}','{T}','{f["case"]}',{lit(kind)},'{f["run"]}',{lit(answer) if answer else "NULL"},'synthetic result','schema verification',
{lit("synthetic conclusion") if valid else "NULL"},{lit("supported" if valid else "unavailable")},{lit(origin)},{lit(validation)},'synthetic handoff',
'[]','[]','[]','initial',{j(impact)},'{input_id or f["input"]}','partial',clock_timestamp(),'save:{rid}');"""
    for i,a in enumerate(f["alerts"]):
        sql+=f"""INSERT INTO socai2.result_members(id,tenant_id,case_id,result_id,run_id,alert_id,assessment_state,conclusion_covered,evidence_refs)
VALUES('{uid(base+70+i)}','{T}','{f["case"]}','{rid}','{f["run"]}','{a}','unresolved',{'true' if i==0 and valid else 'false'},'[]');"""
    return sql
def finish(f,base,**kw):
    run("BEGIN;"+claim(f)+f"UPDATE socai2.runs SET state='completed',ended_at=clock_timestamp(),delivery_state='partial' WHERE id='{f['run']}';"+result_sql(f,base,**kw)+"COMMIT;")
def adopt(f):
    out=run(f"SET app.current_tenant_id='{T}';SELECT socai2.auto_adopt_baseline_result('{T}','{f['result']}');")
    return json.loads(out.splitlines()[-1])
def tests(resume=False):
    observations=[]
    if resume:
        prior=json.loads((EVIDENCE/"postgres-tests.initial.json").read_text(encoding="utf-8"))
        observations=[dict(x,reused_from="postgres-tests.initial.json") for x in prior["observations"] if x["passed"]]
    def record(name,ok,detail=None):
        observations.append({"name":name,"passed":bool(ok),"detail":detail})
    def reject(name,sql,state):
        code,out,err=query("BEGIN;"+sql+"COMMIT;")
        record(name,code!=0 and state in err,{"exit":code,"stdout":out,"stderr":err})
    def race(s1,s2):
        with ThreadPoolExecutor(max_workers=2) as ex:
            a=ex.submit(query,s1);time.sleep(.3);b=ex.submit(query,s2)
            return a.result(),b.result()
    try:
        if not resume:
            run(f"INSERT INTO public.tenants VALUES('{T}'),('{T2}'); INSERT INTO public.users VALUES('{USER}','{T}');")
            record("29 real PG tables",run("SELECT count(*) FROM pg_tables WHERE schemaname='socai2';")=="29")
            record("458 actual columns",run("SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2';")=="458")
            record("all tables force strict RLS",run("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='socai2' AND c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity;")=="29")
            f=fixture(1000)
            reject("one pending baseline",pending_sql(uid(1090),f["case"]),"23505")
            run("BEGIN;"+claim(f)+"COMMIT;")
            reject("claimed Run input frozen",f"UPDATE socai2.runs SET purpose='changed' WHERE id='{f['run']}';","23514")
            reject("claimed member source frozen",f"UPDATE socai2.run_members SET material_id='{uid(999)}' WHERE run_id='{f['run']}';","23514")
            r2=uid(1091);a2=uid(1092)
            run("BEGIN;"+pending_sql(r2,f["case"])+member_sql(uid(1093),r2,f["case"],f["alerts"][0])+artifact_sql(a2,f["case"],r2,f["alerts"])+"COMMIT;")
            reject("second active baseline rejected",claim({"run":r2,"input":a2}),"23505")
            record("failed competing claim preserves pending",run(f"SELECT state FROM socai2.runs WHERE id='{r2}';")=="pending_update")
            for i in [1100,1200]:
                rid=uid(i);art=uid(i+1)
                run(f"""BEGIN; INSERT INTO socai2.runs(id,tenant_id,case_id,kind,title,purpose,trigger,scope_revision,scope_kind,state,operation_key,request_hash,input_artifact_id,executor_version,started_at)
    VALUES('{rid}','{T}','{f["case"]}','ai_question','synthetic AI','schema test','question',1,'whole_case','running','ai:{rid}',repeat('b',64),'{art}','fixture.v1',clock_timestamp());"""
                    +artifact_sql(art,f["case"],rid,f["alerts"])+"COMMIT;")
            record("two AI executions parallel with baseline",run(f"SELECT count(*) FROM socai2.runs WHERE case_id='{f['case']}' AND state='running';")=="3")
            reject("immutable original artifact",f"UPDATE socai2.artifacts SET content_json='{{}}' WHERE id='{f['input']}';","23514")
            reject("unknown business status",f"UPDATE socai2.alerts SET handling_status='magical' WHERE id='{f['alerts'][0]}';","23514")
            reject("score cannot default50 without calculation",f"UPDATE socai2.alerts SET priority_value=50 WHERE id='{f['alerts'][0]}';","23514")
            inc=uid(1300)
            run(f"INSERT INTO socai2.incidents(id,tenant_id,source_namespace,source_incident_id,title) VALUES('{inc}','{T}','synthetic','I1','test');")
            reject("incident override requires audit fields",f"UPDATE socai2.incidents SET severity_override='high' WHERE id='{inc}';","23514")
            run(f"UPDATE socai2.incidents SET severity_override='high',severity_override_reason='synthetic review',severity_override_by='{USER}',severity_override_at=clock_timestamp() WHERE id='{inc}';")
            record("incident override accepted independently",run(f"SELECT severity_override FROM socai2.incidents WHERE id='{inc}';")=="high")
            other=uid(1310)
            run(f"INSERT INTO socai2.alerts(id,tenant_id,source_namespace,source_identity_key,title) VALUES('{other}','{T2}','synthetic','foreign','other tenant');")
            reject("cross tenant member FK",add_case_member(uid(1311),f["case"],other),"23503")
            task=uid(1400);rev=uid(1401)
            run(f"""BEGIN; INSERT INTO socai2.tasks(id,tenant_id,case_id,current_revision_id) VALUES('{task}','{T}','{f["case"]}','{rev}');
    INSERT INTO socai2.task_revisions(id,tenant_id,case_id,task_id,revision,title,state,result_text,result_scope,source_refs,completed_at,completed_by,changed_by)
    VALUES('{rev}','{T}','{f["case"]}','{task}',1,'synthetic human task','completed','confirmed synthetic',{j(scope(f["alerts"]))},'[]',clock_timestamp(),'{USER}','{USER}'); COMMIT;""")
            record("task current pointer deferred cycle commits",run(f"SELECT current_revision_id='{rev}' FROM socai2.tasks WHERE id='{task}';")=="t")
            reject("completed feedback version immutable",f"UPDATE socai2.task_revisions SET result_text='changed' WHERE id='{rev}';","23514")
        g=({"case":uid(2001),"run":uid(2030),"input":uid(2050),"alerts":[uid(2010),uid(2011)]} if resume else fixture(2000,2));finish(g,2000)
        a=adopt(g);b=adopt(g)
        record("valid partial baseline auto adopted",a.get("state")=="adopted",a)
        record("auto adoption idempotent",b.get("state")=="already_adopted" and a.get("assessment_id")==b.get("assessment_id"),b)
        record("adoption only covers explicitly covered member",run(f"SELECT count(*) FROM socai2.case_assessment_members WHERE assessment_id='{a['assessment_id']}';")=="1")
        record("adoption does not resolve Case",run(f"SELECT handling_status FROM socai2.cases WHERE id='{g['case']}';")=="new")
        reject("published result immutable",f"UPDATE socai2.results SET conclusion='changed' WHERE id='{g['result']}';","23514")
        h=fixture(3000);finish(h,3000);run(f"UPDATE socai2.cases SET scope_revision=2 WHERE id='{h['case']}';")
        record("old scope result cannot overwrite current judgment",adopt(h)["state"]=="stale_scope")
        k=fixture(4000);finish(k,4000,validation="system_only",origin="system")
        record("system handoff not auto adopted",adopt(k)["state"]=="not_eligible")
        m=fixture(5000);finish(m,5000)
        aid=uid(5080)
        actor={"type":"user","user_id":USER,"name_snapshot":"synthetic user","service_name":None,"service_version":None}
        run(f"""BEGIN; INSERT INTO socai2.case_assessments(id,tenant_id,case_id,revision,conclusion,origin,validity,scope_revision,formed_at,adopted_at,adopted_by,actor,operation_key)
VALUES('{aid}','{T}','{m["case"]}',1,'newer human assessment','human','accepted',1,clock_timestamp(),clock_timestamp(),'{USER}',{j(actor)},'human:{aid}');
UPDATE socai2.cases SET current_assessment_id='{aid}' WHERE id='{m["case"]}'; COMMIT;""")
        record("newer human adoption preserved",adopt(m)["state"]=="newer_assessment")
        # Real two-session claim race: only one conditional UPDATE claims the pending row.
        n=fixture(6000)
        sql="BEGIN;"+f"SELECT id FROM socai2.cases WHERE id='{n['case']}' FOR UPDATE;"+claim(n)
        x,y=race(sql+"SELECT pg_sleep(2);COMMIT;",sql+"COMMIT;")
        record("concurrent duplicate claim only one succeeds",x[0]==y[0]==0 and (x[1]+y[1]).count("CLAIMED")==1,{"first":x,"second":y})
        # Claim committed before executor's first step; second member writer must create next pending.
        z=fixture(7000);extra=uid(7090);next_run=uid(7091)
        run(add_alert_sql(extra))
        mutate="BEGIN;"+add_case_member(uid(7092),z["case"],extra)+f"UPDATE socai2.cases SET scope_revision=2 WHERE id='{z['case']}';"+pending_sql(next_run,z["case"],2)+member_sql(uid(7093),next_run,z["case"],z["alerts"][0])+member_sql(uid(7094),next_run,z["case"],extra)+"COMMIT;"
        x,y=race("BEGIN;"+f"SELECT id FROM socai2.cases WHERE id='{z['case']}' FOR UPDATE;"+claim(z)+"SELECT pg_sleep(2);COMMIT;",mutate)
        old_count=run(f"SELECT count(*) FROM socai2.run_members WHERE run_id='{z['run']}';")
        next_count=run(f"SELECT count(*) FROM socai2.run_members WHERE run_id='{next_run}';")
        record("claim-before-first-step then added alert uses next pending",x[0]==y[0]==0 and old_count=="1" and next_count=="2",{"first":x,"second":y,"old_members":old_count,"next_members":next_count})
        # Reversed ordering: updated pending range rejects the stale revision claim.
        v=fixture(8000);extra=uid(8090);run(add_alert_sql(extra))
        mutate="BEGIN;"+add_case_member(uid(8091),v["case"],extra)+f"UPDATE socai2.cases SET scope_revision=2 WHERE id='{v['case']}';UPDATE socai2.runs SET scope_revision=2 WHERE id='{v['run']}';"+member_sql(uid(8092),v["run"],v["case"],extra)+"SELECT pg_sleep(2);COMMIT;"
        x,y=race(mutate,"BEGIN;"+f"SELECT id FROM socai2.cases WHERE id='{v['case']}' FOR UPDATE;"+claim(v,1)+"COMMIT;")
        record("member-update first rejects stale scope claim",x[0]==y[0]==0 and "CLAIMED" not in y[1] and run(f"SELECT state FROM socai2.runs WHERE id='{v['run']}';")=="pending_update",{"first":x,"second":y})
        # Dedicated non-login test role; grants are confined to this review database.
        run(f"CREATE ROLE {READER} NOLOGIN NOSUPERUSER NOBYPASSRLS; GRANT USAGE ON SCHEMA public,socai2 TO {READER}; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA socai2 TO {READER};")
        out=run(f"SET ROLE {READER}; SELECT count(*) FROM socai2.alerts;")
        record("RLS missing tenant returns no rows",out=="0",out)
        out=run(f"SET ROLE {READER};SET app.current_tenant_id='{T}'; SELECT count(DISTINCT tenant_id)=1 AND min(tenant_id::text)='{T}' FROM socai2.alerts;")
        record("RLS filters tenant",out=="t",out)
        reject("RLS cross tenant write denied",f"SET LOCAL ROLE {READER};SET LOCAL app.current_tenant_id='{T}';INSERT INTO socai2.alerts(id,tenant_id,source_namespace,source_identity_key,title) VALUES('{uid(99990)}','{T2}','synthetic','rls_write','forbidden');","42501")
    except Exception as e:
        record("test harness stopped on unexpected error",False,str(e))
    finally:
        # Preserve fixtures for review, remove only this newly-created NOLOGIN verification role.
        code,out,err=query(f"SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='{READER}');")
        if code==0 and out=="t":
            code,out,err=query(f"DROP OWNED BY {READER};DROP ROLE {READER};")
            record("test-only role removed",code==0,err or None)
        save("postgres-tests.json",{"database":DATABASE,"migration_sha256":hashlib.sha256(MIGRATION.read_bytes()).hexdigest(),"observations":observations,"passed":sum(x["passed"] for x in observations),"total":len(observations),"all_passed":all(x["passed"] for x in observations),"business_databases_read_or_written":False,"test_database_retained":True})
        print(json.dumps({"passed":sum(x["passed"] for x in observations),"total":len(observations),"failed":[x for x in observations if not x["passed"]]},ensure_ascii=False))
    if not all(x["passed"] for x in observations):raise SystemExit(1)


def extra_tests():
    previous=json.loads((EVIDENCE/"postgres-tests.json").read_text(encoding="utf-8"))
    obs=[]
    def record(name,ok,detail=None):obs.append({"name":name,"passed":bool(ok),"detail":detail})
    try:
        f={"case":uid(2001),"run":uid(9000),"input":uid(9001),"alerts":[uid(2010)]}
        prior=run(f"SELECT current_assessment_id FROM socai2.cases WHERE id='{f['case']}';")
        conversation=uid(9003);question=uid(9004);answer=uid(9005)
        sql="BEGIN;"+member_sql(uid(9002),f["run"],f["case"],f["alerts"][0])
        sql+=f"""INSERT INTO socai2.runs(id,tenant_id,case_id,kind,title,purpose,trigger,scope_revision,scope_kind,state,operation_key,request_hash,input_artifact_id,executor_version,started_at)
VALUES('{f["run"]}','{T}','{f["case"]}','ai_question','synthetic question','selected alert question','question',1,'selected_alerts','running','ai:{f["run"]}',repeat('c',64),'{f["input"]}','fixture.v1',clock_timestamp());"""
        sql+=artifact_sql(f["input"],f["case"],f["run"],f["alerts"],run_kind="ai_question")
        sql+=f"""INSERT INTO socai2.conversations(id,tenant_id,case_id,created_by) VALUES('{conversation}','{T}','{f["case"]}','{USER}');
INSERT INTO socai2.messages(id,tenant_id,case_id,conversation_id,sequence,role,content,state,client_request_key)
VALUES('{question}','{T}','{f["case"]}','{conversation}',1,'user','synthetic question','accepted','question:9004');
INSERT INTO socai2.messages(id,tenant_id,case_id,conversation_id,sequence,role,content,state,in_reply_to,source_run_id,input_artifact_id,client_request_key,answered_at)
VALUES('{answer}','{T}','{f["case"]}','{conversation}',2,'assistant','synthetic answer','completed','{question}','{f["run"]}','{f["input"]}','answer:9005',clock_timestamp());
UPDATE socai2.runs SET state='completed',ended_at=clock_timestamp(),delivery_state='partial' WHERE id='{f["run"]}';"""
        sql+=result_sql(f,9400,kind="ai_saved",answer=answer)+"COMMIT;"
        run(sql)
        record("AI Run input and members publish atomically",run(f"SELECT count(*) FROM socai2.run_members WHERE run_id='{f['run']}';")=="1")
        result=adopt(f)
        record("saved AI result never auto adopted",result["state"]=="not_eligible" and run(f"SELECT current_assessment_id FROM socai2.cases WHERE id='{f['case']}';")==prior,result)
        code,out,err=query("BEGIN;"+member_sql(uid(9006),f["run"],f["case"],uid(2011))+"COMMIT;")
        record("late AI member append rejected",code!=0 and "23514" in err,err)
        # New parent is invisible to the other writer until commit. Child must not slip through deferred FK.
        newrun=uid(11000);newinput=uid(11001)
        s1=f"""BEGIN; INSERT INTO socai2.runs(id,tenant_id,case_id,kind,title,purpose,trigger,scope_revision,scope_kind,state,operation_key,request_hash,input_artifact_id,executor_version,started_at)
VALUES('{newrun}','{T}','{f["case"]}','ai_question','synthetic concurrent AI','empty scope question','question',1,'selected_alerts','running','ai:{newrun}',repeat('d',64),'{newinput}','fixture.v1',clock_timestamp());"""
        s1+=artifact_sql(newinput,f["case"],newrun,[],run_kind="ai_question")+"SELECT pg_sleep(2);COMMIT;"
        s2="BEGIN;"+member_sql(uid(11002),newrun,f["case"],uid(2010))+"COMMIT;"
        with ThreadPoolExecutor(max_workers=2) as ex:
            x=ex.submit(query,s1);time.sleep(.3);y=ex.submit(query,s2);a,b=x.result(),y.result()
        record("concurrent foreign transaction cannot append to newly frozen AI Run",a[0]==0 and b[0]!=0 and any(code in b[2] for code in ["23503","23514"]),{"parent":a,"child":b})
        z=fixture(12000);run("BEGIN;"+claim(z)+"COMMIT;")
        record("baseline creation and claim still valid with deferred member guard",run(f"SELECT state FROM socai2.runs WHERE id='{z['run']}';")=="running")
        # Introspection is schema metadata only, from the dedicated validation database.
        catalog=json.loads(run("""SELECT json_agg(json_build_object('table',table_name,'column',column_name,'type',data_type,'nullable',is_nullable,'default',column_default) ORDER BY table_name,ordinal_position)
FROM information_schema.columns WHERE table_schema='socai2';"""))
        save("actual-column-catalog.json",catalog)
        declared=json.loads((ROOT/"docs/design/socai2-data-contract-20261103.json").read_text(encoding="utf-8"))
        expected={}
        for t in declared["tables"]:
            expected[(t["name"],"id")]=("uuid",False);expected[(t["name"],"tenant_id")]=("uuid",False)
            for col in t["columns"]:
                ty=col["type"]
                actual="uuid" if ty.startswith("ref.") or ty=="uuid" else "text" if ty.startswith("enum.") or ty=="text" else "jsonb" if ty.startswith("json.") else "numeric" if ty.startswith("numeric") else "character" if ty.startswith("char") else "timestamp with time zone" if ty=="timestamptz" else "ARRAY" if ty=="text[]" else ty
                expected[(t["name"],col["name"])]=(actual,col["nullable"])
        mismatch=[]
        for row in catalog:
            key=(row["table"],row["column"])
            if expected.get(key)!=(row["type"],row["nullable"]=="YES"):mismatch.append(row)
        record("458 actual PostgreSQL column types and nullability match contract",len(catalog)==len(expected)==458 and not mismatch,mismatch)
    except Exception as e:
        record("additional harness stopped",False,str(e))
    combined=previous["observations"]+obs
    save("postgres-tests.final.json",{"database":DATABASE,"postgres":"16.15","migration_sha256":hashlib.sha256(MIGRATION.read_bytes()).hexdigest(),"observations":combined,"passed":sum(x["passed"] for x in combined),"total":len(combined),"all_passed":all(x["passed"] for x in combined),"first_batch_reused":17,"second_batch_reused":15,"current_changed_guard_verified_by":obs,"business_databases_read_or_written":False,"test_database_retained":True})
    print(json.dumps({"passed":sum(x["passed"] for x in combined),"total":len(combined),"failed":[x for x in combined if not x["passed"]]},ensure_ascii=False))
    if not all(x["passed"] for x in combined):raise SystemExit(1)


def finish_extra():
    prior=json.loads((EVIDENCE/"postgres-tests.final.json").read_text(encoding="utf-8"))
    save("postgres-tests.final.initial.json",prior)
    obs=prior["observations"]
    for entry in obs:
        if entry["name"]=="concurrent foreign transaction cannot append to newly frozen AI Run":
            a,b=entry["detail"]["parent"],entry["detail"]["child"]
            count=run(f"SELECT count(*) FROM socai2.run_members WHERE run_id='{uid(11000)}';")
            entry["passed"]=a[0]==0 and b[0]!=0 and any(x in b[2] for x in ["23503","23514"]) and count=="0"
            entry["detail"]["committed_member_count"]=count
            entry["detail"]["expectation_correction"]="Either the FK rejects before parent commit or the freeze guard rejects afterwards; both are correct. Original narrow SQLSTATE expectation retained separately."
    rid=uid(13000);art=uid(13001);case=uid(2001)
    s1=f"""BEGIN; INSERT INTO socai2.runs(id,tenant_id,case_id,kind,title,purpose,trigger,scope_revision,scope_kind,state,operation_key,request_hash,input_artifact_id,executor_version,started_at)
VALUES('{rid}','{T}','{case}','ai_question','delayed synthetic AI','empty scope question','question',1,'selected_alerts','running','ai:{rid}',repeat('e',64),'{art}','fixture.v1',clock_timestamp());"""
    s1+=artifact_sql(art,case,rid,[],run_kind="ai_question")+"SELECT pg_sleep(4);COMMIT;"
    s2="BEGIN;"+member_sql(uid(13002),rid,case,uid(2010))+"SELECT pg_sleep(6);COMMIT;"
    with ThreadPoolExecutor(max_workers=2) as ex:
        a=ex.submit(query,s1);time.sleep(.3);b=ex.submit(query,s2);x,y=a.result(),b.result()
    count=run(f"SELECT count(*) FROM socai2.run_members WHERE run_id='{rid}';")
    obs.append({"name":"late commit after concurrent parent committed still cannot append frozen AI member","passed":x[0]==0 and y[0]!=0 and "23514" in y[2] and count=="0","detail":{"parent":x,"child":y,"committed_members":count}})
    prior.update(observations=obs,total=len(obs),passed=sum(x["passed"] for x in obs),all_passed=all(x["passed"] for x in obs),migration_sha256=hashlib.sha256(MIGRATION.read_bytes()).hexdigest())
    save("postgres-tests.final.json",prior)
    print(json.dumps({"passed":prior["passed"],"total":prior["total"],"failed":[x for x in obs if not x["passed"]]},ensure_ascii=False))
    if not prior["all_passed"]:raise SystemExit(1)

if __name__=="__main__":main()
