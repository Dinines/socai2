"""Bounded, read-only checks in the final acceptance image; never calls run/append."""
import argparse
import asyncio
import hashlib
import json
import socket
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import UUID

sys.path.insert(0, '/opt/investigation-test/tools/testdata')
from acceptance_clients import Connections, require
from acceptance_materials import read_json
from acceptance_session import load_execution


def redis_reader(url_file, timeout, expected_db):
    u=urlsplit(Path(url_file).read_text().strip());db=int(u.path.lstrip('/') or '0')
    require(u.scheme in {'redis','rediss'} and db==expected_db,'redis_target_mismatch')
    raw=socket.create_connection((u.hostname,u.port or 6379),timeout=timeout)
    if u.scheme=='rediss':raw=ssl.create_default_context().wrap_socket(raw,server_hostname=u.hostname)
    stream=raw.makefile('rb')
    def receive():
        line=stream.readline();kind=line[:1];v=line[1:-2]
        if kind==b'+':return v.decode()
        if kind==b':':return int(v)
        if kind==b'$':
            size=int(v)
            if size==-1:return None
            result=stream.read(size);require(stream.read(2)==b'\r\n','redis_frame');return result.decode()
        raise ValueError('redis_read_failed_no_secret_detail')
    def command(*parts):
        require(parts[0] in {'AUTH','SELECT','PING','GET','PTTL'},'redis_readonly_command_required')
        data=[str(x).encode() for x in parts];raw.sendall(b'*'+str(len(data)).encode()+b'\r\n'+b''.join(b'$'+str(len(x)).encode()+b'\r\n'+x+b'\r\n' for x in data));return receive()
    if u.password:command('AUTH',unquote(u.username),unquote(u.password)) if u.username else command('AUTH',unquote(u.password))
    command('SELECT',db);require(command('PING')=='PONG','redis_not_ready')
    return command,lambda:(stream.close(),raw.close()),{'host':u.hostname,'port':u.port or 6379,'db':db,'tls':u.scheme=='rediss'}


async def check(args,result):
    directory=Path(args.prepared);profile,session=load_execution(directory);config=read_json(Path(args.config));out=Path(args.output).parent
    ids=session['identities'];alert_ids=[x['predicted_canonical_alert_id'] for x in ids.values() if x['kind']=='alert'];event_ids=[x['event_id'] for x in ids.values() if x['kind']=='context'];keys=sorted({x['correlation_key'] for x in ids.values() if x['kind']=='alert'})
    result.update(execution_id=session['execution']['execution_id'],session_sha256=hashlib.sha256((directory/'session.json').read_bytes()).hexdigest(),release_receipt_sha256=config['final_receipts'])
    if args.mode=='ttl':
        state=read_json(directory/'runs/part1/state.json');require(state['status'] in {'completed','completed_with_issues'},'first_part_not_complete')
        require(len(state['incidents'])==1,'ambiguous_first_incident');iid=state['incidents'][0]
        get,close,target=redis_reader(config['fusion_redis_url_file'],config['redis_timeout_seconds'],config['redis_databases']['fusion'])
        try:
            k='aisoc:fusion:correlation:'+keys[0];one=get('GET',k);index_ttl=get('PTTL',k);summary_raw=get('GET','aisoc:fusion:incident:'+iid);summary_ttl=get('PTTL','aisoc:fusion:incident:'+iid);two=get('GET',k)
            summary=json.loads(summary_raw) if summary_raw else None
            result.update(redis=target,incident_id=iid,index_before=one,index_after=two,index_pttl_ms=index_ttl,summary_pttl_ms=summary_ttl,summary=summary)
            require(one==two==iid and index_ttl>0 and summary_ttl>0,'correlation_not_current')
            first=ids['part1/alerts/001.json'];require(summary['id']==iid and summary['tenant_id']==profile.tenant_id and first['source_alert_id'] in summary['alert_ids'],'incident_summary_membership_mismatch')
        finally:close()
        return
    require(not (directory/'runs').exists(),'execution_already_started')
    clients=Connections(profile,out)
    try:
        result['connections']=await clients.open();pg=clients.pg.connection;s=clients.pg.config.schema_name;tenant=UUID(profile.tenant_id)
        alerts=[read_json(directory/'wire'/p) for p,x in ids.items() if x['kind']=='alert']
        result['source']=await clients.pg.preflight(alerts,keys)
        rows=await clients.pg.snapshot(alert_ids);require(all(not v for k,v in rows.items() if k!='readonly'),'existing_target_records')
        async with pg.transaction(readonly=True):
            await pg.execute("SELECT set_config('app.current_tenant_id',$1,true)",str(tenant))
            tables=await pg.fetch("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema=$1",s)
            result['schema']={'tables':len({x['table_name'] for x in tables}),'columns':len(tables)}
            require(result['schema']=={'tables':32,'columns':521},'schema_baseline_mismatch')
            require(await pg.fetchval('SELECT count(*) FROM public.tenants WHERE id=$1',tenant)==1,'tenant_missing')
            source_count=await pg.fetchval(f'SELECT count(*) FROM {s}.alert_source_refs WHERE tenant_id=$1 AND source_event_id::text=ANY($2::text[])',tenant,event_ids)
            counts={name:await pg.fetchval(f'SELECT count(*) FROM {s}.{name} WHERE tenant_id=$1',tenant) for name in ['analysis_tasks','analysis_attempts','runs','results','alerts','incidents','cases']}
            result['baseline_counts']=counts;result['source_refs']=source_count;require(not source_count and not any(counts.values()),'target_not_empty')
            result['execute_permissions']=[dict(x) for x in await pg.fetch("SELECT p.oid::regprocedure::text AS function,has_function_privilege(current_user,p.oid,'EXECUTE') AS executable FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=$1 ORDER BY 1",s)]
            result['transaction_read_only']=await pg.fetchval('SHOW transaction_read_only')=='on'
        hosts={read_json(directory/'wire'/p)['ocsf_event'].get('device',{}).get('name') for p,x in ids.items() if x['kind']=='context'}
        hosts|={read_json(directory/'wire'/p).get('hostname') for p,x in ids.items() if x['kind']=='alert'}
        hosts=sorted(hosts-{None})
        require(bool(hosts),'historical_host_scope_empty')
        lake_rows=await asyncio.to_thread(clients.lake.query,event_ids);history=await asyncio.to_thread(clients.lake.history_count,hosts)
        result['lake']={'events_present':len(lake_rows),'host_history':history,'hosts':hosts};require(not lake_rows and history==0,'lake_target_collision')
        http=clients.http.client.get(clients.configs['http'].base_url+'/readyz');require(http.status_code==200,'http_not_ready');result['http_ready']=http.json()
        spec=clients.http.client.get(clients.configs['http'].base_url+'/openapi.json');require(spec.status_code==200 and spec.json()['info']['version']==config['http_version'],'http_version_mismatch');result['http_version']=config['http_version']
        result['empty_http_lists']={kind:len(clients.http.pages('/api/v1/socai2/'+kind)) for kind in ['alerts','incidents','cases']};require(not any(result['empty_http_lists'].values()),'http_not_empty')
        from aiokafka.client import AIOKafkaClient
        kafka=AIOKafkaClient(**clients.transport,client_id='socai2-acceptance-readonly-admission',request_timeout_ms=clients.configs['kafka'].request_timeout_ms)
        try:
            await kafka.bootstrap();metadata=await kafka.fetch_all_metadata();brokers=[]
            for broker in metadata.brokers():
                connected=await kafka.ready(broker.nodeId);require(connected,'advertised_broker_unreachable');brokers.append({'node':broker.nodeId,'host':broker.host,'port':broker.port,'connected':connected})
            topics=clients.configs['kafka'].topics.model_dump();partitions={k:sorted(metadata.partitions_for_topic(v) or []) for k,v in topics.items()};require(all(partitions.values()),'input_topic_missing')
            result['kafka']={'brokers':brokers,'topics':topics,'partitions':partitions,'writes':0}
        finally:await kafka.close()
        result['redis']={}
        for name in ['fusion','analysis']:
            get,close,target=redis_reader(config[name+'_redis_url_file'],config['redis_timeout_seconds'],config['redis_databases'][name])
            try:
                if name=='fusion':
                    collision={key:get('GET','aisoc:fusion:correlation:'+key) for key in keys};require(all(v is None for v in collision.values()),'redis_correlation_occupied');target['correlation_indexes']=collision
                result['redis'][name]=target
            finally:close()
        require(config['policy_sha256']==config['expected']['policy_sha256'],'policy_changed')
        result['runtime_binding']=config['expected']
    finally:await clients.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['admit','ttl'],required=True);parser.add_argument('--prepared',required=True);parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=False)
    result={'status':'started','mode':args.mode,'at':datetime.now(timezone.utc).isoformat(),'business_writes':0,'model_calls':0}
    code=0
    try:asyncio.run(check(args,result));result['status']='passed'
    except Exception as exc:result.update(status='failed',error_type=type(exc).__name__,error_code=str(exc) if type(exc) in {ValueError} else 'details_not_exported');code=2
    result['ended_at']=datetime.now(timezone.utc).isoformat()
    with path.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2,default=str)
    print(json.dumps(result,ensure_ascii=False,default=str));sys.exit(code)

if __name__=='__main__':main()
