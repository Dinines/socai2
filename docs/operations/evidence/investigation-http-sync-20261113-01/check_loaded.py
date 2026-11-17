"""Run under the explicit HTTP environment. Hashes/config only, no I/O to models/DB."""
import json,os,hashlib,sys
from pathlib import Path
root=Path(sys.argv[1]);expected=json.loads(Path(sys.argv[2]).read_text())
if len(sys.argv)>3:
 cfg=json.loads(Path(sys.argv[3]).read_text());os.environ.update(json.loads(Path(cfg['private_environment']).read_text()));os.environ.update(cfg['environment'])
actual={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in expected};assert actual==expected
sys.path.insert(0,str(root))
from app.socai2.runtime_policy import active_policy
from app.socai2.baseline_optional_sources import enabled
from investigation_http.adapters.services import CaseBackend,ExecutionBackend
from app.socai2.case_service import CaseService
assert issubclass(CaseBackend,CaseService)
p=active_policy();assert p is not None
assert os.environ['SOCAI2_MODEL_PROTOCOL']=='chat_completions' and os.environ['SOCAI2_MODEL_SCHEMA_PROFILE']=='vllm_grammar_v1'
assert hashlib.sha256(Path(os.environ['SOCAI2_INVESTIGATION_POLICY']).read_bytes()).hexdigest()==expected['config/investigation-policy.toml']
print(json.dumps({'matched_files':len(actual),'policy_loaded':True,'policy_sha256':expected['config/investigation-policy.toml'],'protocol':os.environ['SOCAI2_MODEL_PROTOCOL'],'schema_profile':os.environ['SOCAI2_MODEL_SCHEMA_PROFILE'],'optional_sources':{n:enabled(n) for n in ['ueba','knowledge','graph','product_host']},'external_adapter_core_binding':True,'new_model_calls':0},indent=2))
