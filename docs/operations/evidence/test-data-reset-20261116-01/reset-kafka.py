"""Delete records up to exact frozen ends; preserve Topics and other namespaces."""
import json,subprocess,sys
from pathlib import Path
c=json.load(sys.stdin);root=Path(c['backup_root']);root.mkdir(parents=True,exist_ok=True,mode=0o700)
def call(args,timeout=50):
    p=subprocess.run(['docker','exec',c['container'],*args],capture_output=True,timeout=timeout)
    if p.returncode:raise RuntimeError(p.stderr.decode()[-700:])
    return p.stdout.decode()
def offsets(when):
    text=call(['kafka-run-class','kafka.tools.GetOffsetShell','--broker-list',c['bootstrap'],
               '--topic',c['topic_regex'],'--time',str(when)])
    return {':'.join(parts[:2]):int(parts[2]) for row in text.splitlines() if (parts:=row.rsplit(':',2))}
ends=offsets(-1);starts=offsets(-2)
assert ends==c['expected_ends'],'message_offsets_changed'
assert all(k.rsplit(':',1)[0] in c['topics'] for k in ends)
pending=[{'topic':k.rsplit(':',1)[0],'partition':int(k.rsplit(':',1)[1]),'offset':v}
         for k,v in ends.items() if starts[k]<v]
plan={'partitions':pending,'version':1}
(root/'offsets-before.json').write_text(json.dumps({'start':starts,'end':ends,'delete':plan},indent=2))
if pending:
    # Bounded original messages retained outside the serving paths.
    for part in pending:
        count=part['offset']-starts[part['topic']+':'+str(part['partition'])]
        args=['kafka-console-consumer','--bootstrap-server',c['bootstrap'],'--topic',part['topic'],
              '--partition',str(part['partition']),'--offset',str(starts[part['topic']+':'+str(part['partition'])]),
              '--max-messages',str(count),'--timeout-ms','10000']
        data=call(args)
        with (root/(part['topic']+'.'+str(part['partition'])+'.jsonl')).open('x') as f:f.write(data)
    remote='/tmp/socai2-record-reset-20261116-01.json'
    p=subprocess.run(['docker','exec','-i',c['container'],'sh','-c','cat > '+remote],input=json.dumps(plan).encode(),capture_output=True,timeout=10)
    assert p.returncode==0
    result=call(['kafka-delete-records','--bootstrap-server',c['bootstrap'],'--offset-json-file',remote])
    (root/'delete-receipt.txt').write_text(result)
    assert 'error:' not in result.lower(),result
after=offsets(-2);final=offsets(-1)
assert final==ends and after==ends,'old_messages_still_consumable'
print(json.dumps({'topics':len(c['topics']),'partitions':len(ends),'records_removed':sum(ends[k]-starts[k] for k in ends),
                  'all_start_equals_end':True,'topics_preserved':True,'other_namespaces_untouched':True}))
