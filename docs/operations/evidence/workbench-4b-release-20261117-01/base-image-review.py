"""Read immutable base references and platform identity across Docker engines."""
import json,subprocess
from pathlib import Path
c=CONFIG;root=Path(c['remote_root']);package=root/'package'/c['package_release']
p=json.loads((package/'build-profile.json').read_text());a=json.loads((package/p['acceptance_image']).read_text())
rows=[]
for kind,ref,expected in [('viewer',p['image']['base_tag'],p['image']['base_id']),('acceptance',a['base_ref'],a['base_id'])]:
 d=json.loads(subprocess.run(['docker','image','inspect',ref],text=True,capture_output=True,check=True).stdout)[0]
 rows.append({'kind':kind,'reference':ref,'expected_id':expected,'image_id':d['Id'],'repo_digests':d['RepoDigests'],'architecture':d['Architecture'],'os':d['Os']})
print(json.dumps({'status':'observed','bases':rows}))
