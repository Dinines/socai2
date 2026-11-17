import json,shlex,subprocess
from pathlib import Path
E=Path(__file__).resolve().parent
data={name:{'response_format':json.loads((E/file).read_text())['response_format']} for name,file in [('original','original-request.json'),('candidate','candidate-request.json')]}
cmd=['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12','-J','sting-infra21','sting-llm',shlex.join(['/home/lychee/anaconda3/envs/vllm-new/bin/python','-c',(E/'grammar-probe.py').read_text()])]
r=subprocess.run(cmd,input=json.dumps(data),capture_output=True,text=True,timeout=55)
with (E/'grammar-invocation.json').open('x') as f:json.dump({'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},f,ensure_ascii=False,indent=2)
assert r.returncode==0
receipt=json.loads(r.stdout)
with (E/'grammar-checks.json').open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
assert receipt['checks']['current']['single_character'] and not receipt['checks']['current']['sentence']
assert all(receipt['checks']['candidate'][key] for key in ['sentence','line_break','escaped_quote'])
print(json.dumps(receipt,ensure_ascii=False,indent=2))
