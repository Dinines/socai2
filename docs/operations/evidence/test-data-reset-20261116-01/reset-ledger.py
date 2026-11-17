"""Remove the exact authorized old test batches from the active viewer ledger."""
import hashlib,io,json,os,shutil,sys,tarfile
from pathlib import Path
c=json.load(sys.stdin);root=Path(c['root'])
actual={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
assert actual==c['expected_files'],'ledger_changed_since_inventory'
backup=Path(c['backup']);backup.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
with tarfile.open(backup,'x:gz') as tar:
    for name in actual:tar.add(root/name,arcname=name,recursive=False)
os.chmod(backup,0o600)
for name in c['batches']:
    assert '/' not in name and name not in {'','.','..'}
    path=root/name
    assert path.is_dir() and not path.is_symlink()
    shutil.rmtree(path)
remaining=[str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.name!='.publish.lock']
assert not remaining,remaining
print(json.dumps({'batches_removed':c['batches'],'files_removed':len(actual),'remaining_files':0,
                  'backup':str(backup),'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest()}))
