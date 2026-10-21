"""Run only the organisation-memory batch and directly affected original tests."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/3a-org-memory-20261020'
SUITES={
 'agents':['test_organisation_memory_in_prompt.py','test_auto_triage_ledger_records_the_prompt.py','test_ledger_tenant.py','test_replay_leakage.py','test_replay_shadow_no_writes.py','test_replay_measures_the_real_run.py','test_auto_triage_dispositions.py','test_auto_triage_truncated_json.py'],
 'api':['test_feedback_context_statements.py','test_analyst_feedback.py','test_triage_context_routes.py'],
}
NEW={'agents':['test_org_memory_agents.py','test_org_memory_ledger.py'],'api':['test_org_memory_api.py']}
IMAGES={'agents':'socai2-agents-test:1g-20261020','api':'socai2-api-test:identity-2a-20261020'}
def main(service,attempt):
 assert service in SUITES and re.fullmatch(r'[a-z0-9-]+',attempt)
 E.mkdir(exist_ok=True,mode=0o700);E.chmod(0o700)
 log=E/f'tests-org-memory-3a-{service}-{attempt}.log';assert not log.exists(),'Retain previous attempt, use a new label'
 files=[f'/source/services/{service}/tests/'+n for n in SUITES[service]]+['/source/tests/porting/'+n for n in NEW[service]]
 cmd=['docker','run','--rm','--network','none','-e','PYTHONDONTWRITEBYTECODE=1','-e','ENVIRONMENT=production','-e','AISOC_DEV_AUTH_BYPASS=false','-e',('DATABASE_URL=postgresql+asyncpg://unit:unit@127.0.0.1:1/unit' if service=='api' else 'DATABASE_URL='),'-e','DATABASE_DSN=','-e',f'PYTHONPATH=/source/services/{service}','-v',str(R/'source')+':/source:ro','-w',f'/source/services/{service}']
 if service=='agents':cmd+=['-v',str(R/'source/tests/porting/reference/connectors')+':/source/services/connectors:ro']
 cmd += [IMAGES[service],'python','-m','pytest','-q','-p','no:cacheprovider','--asyncio-mode=auto',*files]
 result=subprocess.run(cmd,text=True,capture_output=True);log.write_text(result.stdout+result.stderr);log.chmod(0o600)
 matches=re.findall(r'(\d+) passed',result.stdout);passed=int(matches[-1]) if matches else 0
 record={'service':service,'attempt':attempt,'passed':passed,'exit_code':result.returncode,'suites':SUITES[service],'new_tests':NEW[service],'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'network':'none','auth_or_model_or_database_doubles_in_unit_tests':True}
 (E/f'tests-{service}-{attempt}.json').write_text(json.dumps(record,indent=2));print(json.dumps(record));assert result.returncode==0
if __name__=='__main__':main(*sys.argv[1:])
