"""Read-only inventory of the authorized SOCAI knowledge corpus; no import/indexing."""
from pathlib import Path
import argparse, collections, hashlib, json

def inventory(root):
    entries=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file() or any(part.startswith('.') for part in p.relative_to(root).parts):
            continue
        # Do not follow an unexpected symlink outside the authorized corpus.
        p.resolve().relative_to(root.resolve())
        h=hashlib.sha256();lines=0
        with p.open('rb') as stream:
            for chunk in iter(lambda:stream.read(4*1024*1024),b''):
                h.update(chunk)
                if p.suffix=='.jsonl':lines+=chunk.count(b'\n')
        row={'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
        if p.suffix=='.jsonl':row['newline_count']=lines
        entries.append(row)
    bypath={e['path']:e for e in entries};metadata=[]
    for p in sorted((root/'raw').glob('*.meta.json')):
        d=json.loads(p.read_text());name=str(p.relative_to(root)).removesuffix('.meta.json')
        assert name in bypath,name
        item=bypath[name]
        assert d['sha256']==item['sha256'] and d['bytes']==item['bytes'],name
        metadata.append({'path':name,'source_url':d['url'],'fetched_at':d['fetched_at'],'sha256_matches':True,'bytes_match':True})
    audit=json.loads((root/'parse-audit.json').read_text())
    assert bypath['records.jsonl']['newline_count']==audit['record_count']
    sections=collections.Counter();entities=set()
    with (root/'attack-sections.v1.jsonl').open() as f:
        for line in f:
            d=json.loads(line);sections[d['section_type']]+=1;entities.add(d['entity_id'])
    return {'date':'2026-10-20','authorization':'User permits reuse of existing data and ../SOCAI data','source_root':str(root.resolve()),'operation':'read-only file hashing, raw sidecar hash checks and JSONL line inventory','imported':False,'indexed':False,'consumed_by_investigation':False,'files':entries,'file_count':len(entries),'bytes':sum(e['bytes'] for e in entries),'extension_counts':dict(sorted(collections.Counter(Path(e['path']).suffix for e in entries).items())),'raw_source_sidecars_checked':metadata,'parser_version':audit['parser_version'],'reported_entity_type_counts':audit['entity_type_counts'],'record_count_verified_by_newlines':audit['record_count'],'attack_section_types':dict(sorted(sections.items())),'attack_section_entity_count':len(entities),'limits':['Line counts and hashes do not establish semantic parsing or retrieval quality','Existing parser audits are historical evidence, not newly reproduced parser tests','No old vectors, databases, model weights, private investigations or old task trees imported']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=Path('../SOCAI/knowledge'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=inventory(a.source)
    with a.output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ['file_count','bytes','extension_counts','record_count_verified_by_newlines','attack_section_entity_count','attack_section_types']}))
