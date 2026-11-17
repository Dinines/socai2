import json,subprocess,sys
from pathlib import Path
from urllib.request import Request,urlopen
c=json.load(sys.stdin)
key=Path(c['key_file']).read_text().strip() if c.get('key_file') else ''
def get(path):
    with urlopen(Request(c['url']+path,headers={'api-key':key} if key else {}),timeout=10) as r:
        return json.load(r)
collections=get('/collections')['result']['collections']
result=[]
for row in collections:
    d=get('/collections/'+row['name'])['result']
    result.append({'name':row['name'],'points':d.get('points_count'),'status':d.get('status')})
print(json.dumps(result,indent=2))
