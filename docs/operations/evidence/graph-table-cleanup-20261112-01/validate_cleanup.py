import json, pathlib, subprocess, sys, hashlib
root=pathlib.Path.cwd(); evidence=root/'docs/operations/evidence/graph-table-cleanup-20261112-01'
cfg=json.loads((evidence/'profile.json').read_text()); target=cfg['targets']['local-current']; base=target['command']; db=target['database']
migration=(root/'services/api/migrations/127_socai2_remove_unused_graph_table.sql').read_text()
def pg(sql, argv=base, success=True, error=None):
 p=subprocess.run(argv,input=sql,text=True,capture_output=True,timeout=cfg['timeout_seconds'])
 assert (p.returncode==0)==success,p.stderr
 if error: assert error in p.stderr,p.stderr
 return p.stdout.strip()
def begin(database=db):
 return "BEGIN; SELECT set_config('socai2.cleanup.expected_database','"+database+"',true); SET LOCAL lock_timeout='"+str(cfg['lock_timeout_seconds'])+"s'; SET LOCAL statement_timeout='"+str(cfg['statement_timeout_seconds'])+"s';\n"
checks={}
pg(begin('wrong_target')+migration,success=False,error='cleanup_target_or_baseline_mismatch');checks['wrong_target']='rejected'
seed="INSERT INTO socai2.graph_explorations(id,tenant_id,case_id,base_input_artifact_id,graph_state,created_by,updated_by) SELECT gen_random_uuid(),a.tenant_id,a.case_id,a.id,'{}',c.created_by,c.created_by FROM socai2.artifacts a JOIN socai2.cases c ON c.tenant_id=a.tenant_id AND c.id=a.case_id LIMIT 1; DO $$ BEGIN IF NOT EXISTS(SELECT FROM socai2.graph_explorations) THEN RAISE EXCEPTION 'probe_not_seeded'; END IF; END $$;\n"
pg(begin()+seed+migration,success=False,error='cleanup_table_contains_data');checks['nonempty']='rejected_and_rolled_back'
pg(begin()+"CREATE VIEW socai2.graph_cleanup_dependency_probe AS SELECT id FROM socai2.graph_explorations;\n"+migration,success=False,error='depend on it');checks['dependent_view']='rejected_and_rolled_back'
rls="CREATE ROLE socai2_graph_cleanup_probe NOLOGIN NOSUPERUSER NOBYPASSRLS; GRANT USAGE,CREATE ON SCHEMA socai2 TO socai2_graph_cleanup_probe; GRANT SELECT ON public.aisoc_schema_migrations TO socai2_graph_cleanup_probe; ALTER TABLE socai2.graph_explorations OWNER TO socai2_graph_cleanup_probe; SET LOCAL ROLE socai2_graph_cleanup_probe;\n"
pg(begin()+rls.replace('socai2_graph_cleanup_probe',cfg['validation']['role'])+migration,success=False,error='row-level security');checks['rls_restricted_role']='rejected_and_rolled_back'
probe="""CREATE TEMP TABLE cleanup_artifact_probe(id uuid);
WITH saved AS (INSERT INTO socai2.artifacts SELECT (jsonb_populate_record(NULL::socai2.artifacts,to_jsonb(a)||jsonb_build_object('id',gen_random_uuid()))).* FROM socai2.artifacts a WHERE a.case_id IS NOT NULL LIMIT 1 RETURNING id) INSERT INTO cleanup_artifact_probe SELECT id FROM saved;
SELECT json_build_object('saved_readable',count(*)=1) FROM socai2.artifacts a JOIN cleanup_artifact_probe p ON p.id=a.id;
ROLLBACK;"""
out=pg(begin()+migration+probe);assert '"saved_readable" : true' in out,out;checks['existing_upgrade_artifact_save_read']='passed_and_rolled_back'
sys.path.insert(0,str(root/'deploy/database'));import install_reader
scratch=cfg['validation']['database'];scratch_args=base[:-1]+[scratch]
pg('CREATE DATABASE '+scratch+';',base[:-1]+['postgres'])
try:
 sql=install_reader.render('init_socai2_current.sql')
 args=scratch_args+['-v','expected_database='+scratch,'-v','cleanup_lock_timeout='+str(cfg['lock_timeout_seconds'])+'s','-v','cleanup_statement_timeout='+str(cfg['statement_timeout_seconds'])+'s']
 pg(sql,args)
 result=json.loads(pg((evidence/'inspect.sql').read_text(),scratch_args))
 assert result['socai2_tables']==28 and result['socai2_columns']==450 and result['cleanup_recorded'] and not result['graph_exists'],result
 checks['fresh_current_install']={'tables':28,'columns':450,'graph_absent':True,'migration_recorded':True}
 pg(begin(scratch)+migration+'COMMIT;',scratch_args);checks['idempotent_increment']='passed'
finally:
 pg('DROP DATABASE '+scratch+';',base[:-1]+['postgres'])
checks['scratch_database']='created_for_this_validation_then_removed'
report={'status':'passed','checks':checks,'model_calls':0,'persistent_business_writes':0,'migration_sha256':hashlib.sha256(migration.encode()).hexdigest()}
(evidence/'direct-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
