"""Prepare a fresh release directory only; no running service changes."""
import json,subprocess
from pathlib import Path
c=CONFIG
root=Path(c['remote_root']);root.mkdir(parents=True,exist_ok=False)
(root/'incoming').mkdir();(root/'config').mkdir()
(root/'config/release.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'staged_not_switched','root':str(root),'services_changed':False}))
