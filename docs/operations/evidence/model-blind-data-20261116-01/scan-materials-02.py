"""Bounded recursive payload audit, including JSON encoded telemetry."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
DATA=OUT/'revision-02'
files=sorted(DATA.glob('template-data-*/payloads/*.json'))+sorted((DATA/'clean-data-01').glob('S*/*.jsonl'))+[DATA/'clean-data-01/background.json',DATA/'clean-data-01/knowledge.json']
key=re.compile(r'^(synthetic|is_test|scenario_id|run_id|batch_id|expected.*|decisive_evidence|ground_truth|program_classification|api_key|access_token|private_key|password)$',re.I)
text=re.compile(r'\b(synthetic|fixture|ground.?truth|benign|malicious|attacker|evil)\b|测试|预期|授权未知|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',re.I)
rows=[]
def visit(value,path,hits):
    if isinstance(value,dict):
        for k,v in value.items():
            if key.search(k):hits.append({'path':path+'.'+k,'kind':'control_or_secret_field'})
            visit(v,path+'.'+k,hits)
    elif isinstance(value,list):
        for n,v in enumerate(value):visit(v,path+'.'+str(n),hits)
    elif isinstance(value,str):
        if text.search(value):hits.append({'path':path,'kind':'answer_hint_or_secret_text'})
        if value.lstrip().startswith(('{','[')):
            try: decoded=json.loads(value)
            except json.JSONDecodeError:return
            visit(decoded,path+'[json]',hits)
for path in files:
    raw=path.read_bytes();objects=[json.loads(line) for line in raw.splitlines()] if path.suffix=='.jsonl' else [json.loads(raw)]
    hits=[]
    for n,value in enumerate(objects):visit(value,str(n),hits)
    rows.append({'path':path.relative_to(DATA).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'hits':hits})
result={'files':len(rows),'findings':sum(len(r['hits']) for r in rows),'records':rows,'scope':'business payloads only; control sidecars excluded by design; recursive encoded JSON scanned','model_calls':0}
with (OUT/'material-scan-02.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='records'}))
assert result['findings']==0,[r for r in rows if r['hits']]
