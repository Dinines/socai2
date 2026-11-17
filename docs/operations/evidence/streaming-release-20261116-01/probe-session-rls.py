"""Bounded rollback-only proof of the formal session RLS precondition."""
import json,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);c=json.loads((root/'config/release.json').read_text());db=c['database'];tenant=c['identity']['tenant_id']
# GRANT is local to the transaction and rolls back together with the attempted row.
sql=f'''BEGIN;
SET LOCAL lock_timeout='3s'; SET LOCAL statement_timeout='15s';
GRANT SELECT,INSERT,UPDATE ON public.sessions TO "{db['ingress']}";
SET LOCAL ROLE "{db['ingress']}";
SELECT json_build_object('role',current_user,'tenant_setting',current_setting('app.current_tenant_id',true),'resolved_tenant',public.current_tenant_id());
INSERT INTO public.sessions(id,tenant_id,session_key,key_kind,key_source,source,first_seen_at,last_seen_at)
VALUES (gen_random_uuid(),'{tenant}','release-readiness','vendor_session','release-check','runtime-check',now(),now());
ROLLBACK;
'''
argv=['docker','exec','-i',db['container'],'psql','-wXAtq','-U',db['admin'],'-d',db['name'],'-v','ON_ERROR_STOP=1']
r=subprocess.run(argv,input=sql,text=True,capture_output=True,timeout=c['command_timeout_seconds'])
expected='new row violates row-level security policy for table "sessions"' in r.stderr
assert expected and r.returncode!=0
post=subprocess.check_output([*argv,'-c',f"SELECT json_build_object('support_insert_grant',has_table_privilege('{db['ingress']}','public.sessions','INSERT'),'rows',(SELECT count(*) FROM public.sessions));"],text=True,timeout=c['command_timeout_seconds'])
print(json.dumps({'status':'confirmed_runtime_blocker','expected_rejection':expected,'exit':r.returncode,'ordinary_role_context':json.loads(r.stdout),'post_rollback':json.loads(post),'grants_committed':False,'rows_committed':0,'error':'session_write_requires_tenant_context','models_called':0},indent=2))
