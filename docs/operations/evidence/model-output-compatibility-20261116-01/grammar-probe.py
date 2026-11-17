"""Zero inference checks in the actual vLLM environment; input contains two schemas."""
import importlib.metadata,json,sys
import xgrammar as xgr
from xgrammar.testing import _is_grammar_accept_string
data=json.loads(sys.stdin.read())
current=data['original']['response_format']['json_schema']['schema']['$defs']['CompactString0']
candidate=data['candidate']['response_format']['json_schema']['schema']['$defs']['CompactString0']
schemas={'current':current,'pattern_omitted_only':{k:v for k,v in current.items() if k!='pattern'},'candidate':candidate}
values={'single_character':'告','sentence':'告警需要结合原始记录复核','spaces_only':'   ','line_break':'网络\n连接','escaped_quote':'存在"连接"记录','too_long':'a'*3001}
out={'versions':{n:importlib.metadata.version(n) for n in ['vllm','xgrammar']},'schemas':schemas,'checks':{},'model_calls':0}
for name,schema in schemas.items():
 grammar=xgr.Grammar.from_json_schema(json.dumps(schema))
 out['checks'][name]={key:bool(_is_grammar_accept_string(grammar,json.dumps(value,ensure_ascii=False))) for key,value in values.items()}
out['full_schemas_compile']={}
for name in ['original','candidate']:
 xgr.Grammar.from_json_schema(json.dumps(data[name]['response_format']['json_schema']['schema']))
 out['full_schemas_compile'][name]=True
print(json.dumps(out,ensure_ascii=False,indent=2))
