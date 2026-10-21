"""Explicit D2 pre-Evidence contract recovery; prepare/probe/authorize only.

No import-time resource calls or legacy-batch hooks. Original five operators,
24 baselines, state and first failure remain unchanged. No provision/topic/
policy/key/model/publish/offset action is available in this helper.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
E = R / 'evidence/c03-triage-validity-quality-20261021'
P = R / 'private/completion-c03-validity-quality'
D = E / 'contract-recovery-r02'
PRIVATE = P / 'recovery-r02'
NEW_STATE = PRIVATE / 'state.json'
INSIDE = S / 'deploy/aisoc21/acceptance_triage_validity_quality_recovery_c03.py'
RUNNER = S / 'deploy/aisoc21/run_triage_validity_quality_recovery_c03.py'
FINISH = S / 'deploy/aisoc21/finish_triage_validity_quality_recovery_c03.py'
PLAN = S / 'docs/operations/c03-triage-validity-quality-recovery-plan.md'
STOP_SHA = '8c32c8eaea7ed0966b2fd212104d2343fecdf3e634ba14abf0ee8298c3ab60d7'
OBSERVATION_SHA = 'c2c8cf9abf252feaa15f69796d97fd2aa7ae6026e189275f6ac5a147278ee0a1'
LOG_SHA = 'c7f2ce89f6bd7ea1231640325647a25f7851c11f09c456debb1d40351dd52897'
HOLD_AUDIT_SHA = '4d204714ce660485c9d3ca8270c0022a51a817ffb003cf8f783ce7e6e8bdd899'
INPUT_SHA = 'e80c04a5e9d2bc18b526c197af9b6e9ab8cbc5966e2615dca274e12b3949e3c2'
IMAGE = 'sha256:9cb719ff55d772ebf047f87a06863ae7102feb5be3b9471610113dd9d85728fd'
ORIGINAL_OPS = {
 'deploy/aisoc21/prepare_triage_validity_quality_c03.py': 'b76b28ed6cb9322cfc800cf4bd9a8b3bcff19f3f862ff9159622c24258e21ee9',
 'deploy/aisoc21/run_triage_validity_quality_c03.py': '2a3832bb79fb5d76169787da9c34953704232be70d88245849b645eb6f5c3562',
 'deploy/aisoc21/acceptance_triage_validity_quality_c03.py': '243e6cea06344599eee9af032dca91d2523df6c849c730513bb08c926e14a6d6',
 'deploy/aisoc21/snapshot_triage_validity_quality_c03.py': '2ddac28e3dd98b76a2d6f2f9a5017def2364b55d9c5a55de87551bf247884fb3',
 'deploy/aisoc21/finish_triage_validity_quality_c03.py': '83a91833bcb3a91ac7386d708e12fa03e3904b2efe5deadc54ca95261bab309a'}


METADATA_CODE = "import asyncio,json,os,sys\nfrom aiokafka import AIOKafkaConsumer,TopicPartition\nfrom app.core.kafka_security import kafka_client_kwargs\ncfg=json.load(sys.stdin)\nasync def main():\n security=kafka_client_kwargs();assert security['security_protocol']=='SSL'\n if cfg['kind']=='raw':\n  from app.core.config import settings\n  selected={'raw':(settings.kafka_topic_alerts_raw,settings.kafka_consumer_group)}\n else:\n  selected={'quality':(cfg['broker']['quality_topic'],cfg['broker']['group']),\n   'dlq':(cfg['broker']['dlq_topic'],None),\n   'main':(os.getenv('KAFKA_TOPIC_ALERTS_FUSED','aisoc.alerts.fused'),os.getenv('KAFKA_CONSUMER_GROUP','aisoc-agents-triage')),\n   'old_02_quality':('socai2.c03.triage-quality.20261021','socai2-c03-triage-quality-20261021'),\n   'old_02_dlq':('socai2.c03.triage-quality.20261021.dlq',None),\n   'old_02B_quality':('socai2.c03.triage-quality-recheck.20261021','socai2-c03-triage-quality-recheck-20261021'),\n   'old_02B_dlq':('socai2.c03.triage-quality-recheck.20261021.dlq',None),\n   'old_02C02_quality':('socai2.c03.triage-authorization-quality.20261021','socai2-c03-triage-authorization-quality-20261021'),\n   'old_02C02_dlq':('socai2.c03.triage-authorization-quality.20261021.dlq',None)}\n out={}\n for alias,(topic,group) in selected.items():\n  c=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=group,enable_auto_commit=False,**security)\n  await c.start()\n  try:\n   await c._client.add_topic(topic);parts=c.partitions_for_topic(topic);assert parts\n   tps=[TopicPartition(topic,p) for p in sorted(parts)]\n   begins,ends=await c.beginning_offsets(tps),await c.end_offsets(tps)\n   out[alias]={'topic':topic,'group':group,'partitions':[{'partition':tp.partition,'begin':begins[tp],\n    'end':ends[tp],'committed':await c.committed(tp) if group else None} for tp in tps],\n    'physical_record_reads':0,'polls':0,'assigns':0,'commits':0}\n  finally:await c.stop()\n print(json.dumps(out))\nasyncio.run(main())"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value, *, readable=True):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    path.chmod(0o600)
    if readable:
        os.chown(path, 10001, 10001)
        if path.is_relative_to(D):
            parent = path.parent
            while parent != D.parent:
                os.chown(parent, 10001, 10001)
                parent = parent.parent


def copy(source, target, *, readable=False):
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(source.read_bytes())
    target.chmod(0o600)
    if readable:
        os.chown(target, 10001, 10001)


def original_bindings():
    assert all(sha(S / name) == want for name, want in ORIGINAL_OPS.items())
    if (D / 'prepared.json').is_file():
        prepared = read(D / 'prepared.json')
        for name, want in prepared['original_evidence_sha256'].items():
            assert sha(E / name) == want, 'Original evidence changed'
        for name, want in prepared['original_private_sha256'].items():
            assert sha(P / name) == want, 'Original private input changed'
        module = importlib.import_module('prepare_triage_validity_quality_c03')
        assert module.baseline_hashes() == prepared['original_baseline_sha256']
    return dict(ORIGINAL_OPS)


def zero_business_proof():
    assert sha(E / 'contract-hold-independent-audit.json') == HOLD_AUDIT_SHA
    assert read(E / 'contract-hold-independent-audit.json')['recovery_execution_accepted'] is False
    assert sha(E / 'safety-stop.json') == STOP_SHA and not (E / 'recovery-stop.json').exists()
    directory = E / 'host-phases/case01/ingress'
    assert sha(directory / 'before.json') == sha(directory / 'after.json') == OBSERVATION_SHA
    assert sha(directory / 'container.log') == LOG_SHA
    assert read(directory / 'exit.json')['exit_code'] == 1 and not read(directory / 'exit.json')['timed_out']
    assert (directory / 'failure.json').is_file() and not (directory / 'accepted.json').exists()
    assert not (E / 'cases').exists()
    assert not any((E/name).exists() for name in ('acceptance.json','finish-started.json','finish-before.json','key-lifecycle.json'))
    assert not list((E / 'record-deliveries').glob('*.json'))
    assert not list(E.glob('cases/*/ingress/http-sending.json'))
    assert not list(E.glob('cases/*/invoke/sdk-send-started.json'))
    assert not list(E.glob('cases/*/invoke/quality-sending.json'))


def originals_to_bind():
    paths = {E / 'safety-stop.json', E / 'contract-hold-independent-audit.json',
             E / 'pre-execution-independent-audit.json', E / 'provision-independent-review.json',
             E / 'execution-authorized.json', E / 'topics-ready.json'}
    paths.update(p for p in (E / 'host-phases/case01/ingress').rglob('*') if p.is_file())
    p = importlib.import_module('prepare_triage_validity_quality_c03')
    paths.update(E / name for name in p.BASELINE_FILES)
    assert all(path.is_file() and not path.is_symlink() for path in paths)
    return {str(path.relative_to(E)): sha(path) for path in sorted(paths)}


def prepare():
    assert os.geteuid() == 0 and not D.exists() and not PRIVATE.exists()
    original_bindings()
    zero_business_proof()
    original = importlib.import_module('run_triage_validity_quality_c03')
    p = original.prepare
    assert sha(p.INPUT) == INPUT_SHA and sha(p.P / 'inputs.json') == INPUT_SHA
    assert p.IMAGE == IMAGE and read(E / 'pre-execution-independent-audit.json')['accepted'] is True
    assert sha(Path(p.__file__)) == ORIGINAL_OPS['deploy/aisoc21/prepare_triage_validity_quality_c03.py']
    baseline = p.baseline_hashes()  # Original INSIDE/readability proof remains original.
    assert baseline == read(E / 'pre-execution-independent-audit.json')['baseline_sha256']
    state = read(P / 'state.json')
    provisioned = read(P / 'state-provisioned.json');provisioned['execution_authorized'] = True
    assert state == provisioned and state['execution_authorized'] is True
    assert state['operator_sha256'] == ORIGINAL_OPS['deploy/aisoc21/acceptance_triage_validity_quality_c03.py']
    assert state['image_id'] == IMAGE
    assert INSIDE.stat().st_mode & 0o777 == 0o644 and not INSIDE.is_symlink()
    D.mkdir(mode=0o700);os.chown(D,10001,10001)
    PRIVATE.mkdir(mode=0o700)
    save(D / 'started.json', {'helper_sha256': sha(Path(__file__)), 'new_business_actions': 0,
                             'automatic_retry': False})
    try:
        before = read(E / 'host-phases/case01/ingress/before.json')
        current = original.protected_output(label='contract-recovery-prepare',
            previous=before['observation'], previous_qa=before['closure_qa'])
        save(D / 'protected-before.json', current)
        metadata = p.base.container_json(METADATA_CODE, payload={'kind':'agents','broker':state['broker']})
        raw = p.base.container_json(METADATA_CODE, service='fusion', payload={'kind':'raw'})['raw']
        assert raw == read(E/'fusion-raw-metadata-before.json')
        assert metadata['main'] == read(E/'main-fused-metadata-before.json')
        assert metadata['quality']['partitions'] == [{'partition':0,'begin':0,'end':0,'committed':0}]
        assert metadata['dlq']['partitions'] == [{'partition':0,'begin':0,'end':0,'committed':None}]
        for prefix, path in (('old_02','old-quality-metadata-before.json'),
                             ('old_02B','old-recheck-quality-metadata-before.json'),
                             ('old_02C02','old-authorization-quality-metadata-before.json')):
            assert {'quality':metadata[prefix+'_quality'],'dlq':metadata[prefix+'_dlq']} == read(E/path)
        save(D / 'fresh-broker-metadata.json', {'agents':metadata,'raw':raw,'physical_record_reads_or_commits':0})

        zero_business_proof()
        old = originals_to_bind()
        for name in old:
            copy(E / name, D / 'original-evidence' / name)
        for name in ORIGINAL_OPS:
            copy(S / name, D / 'original-five-operators' / Path(name).name)
        private_names = ('state.json','state-provisioned.json','state-draft.json','inputs.json','probe.env')
        private_hashes = {name:sha(P / name) for name in private_names}
        for name in private_names:
            copy(P / name, PRIVATE / 'original' / name)
        copy(PLAN, D / 'scope-before.md')
        # The actual original stop stays at the same path with identical bytes.
        stop = E / 'safety-stop.json'
        info = stop.lstat()
        assert stat.S_ISREG(info.st_mode) and info.st_uid == 0
        assert stat.S_IMODE(info.st_mode) == 0o600 and sha(stop) == STOP_SHA
        stop_before = {'uid':info.st_uid, 'gid':info.st_gid,
                       'mode':oct(stat.S_IMODE(info.st_mode)), 'sha256':sha(stop)}
        save(D / 'original-stop-metadata-before.json', stop_before)
        os.chown(stop, 10001, 10001)
        stop.chmod(0o400)
        info = stop.lstat()
        stop_after = {'uid':info.st_uid, 'gid':info.st_gid,
                      'mode':oct(stat.S_IMODE(info.st_mode)), 'sha256':sha(stop)}
        save(D / 'original-stop-metadata-after.json', stop_after)
        assert stop_after == {'uid':10001, 'gid':10001, 'mode':'0o400', 'sha256':STOP_SHA}
        state['operator_sha256'] = sha(INSIDE)
        save(NEW_STATE, state)
        save(D / 'prepared.json', {'change':'C03-02D-02-contract-recovery-r02','original_stop_sha256':STOP_SHA,
            'original_preexec_sha256':sha(E / 'pre-execution-independent-audit.json'),
            'original_hold_audit_sha256':HOLD_AUDIT_SHA,'original_failed_before_after_sha256':OBSERVATION_SHA,
            'original_failed_log_sha256':LOG_SHA,'original_five_operators':ORIGINAL_OPS,
            'original_evidence_sha256':old,'original_private_sha256':private_hashes,
            'original_baseline_sha256':baseline,'protected_before_sha256':sha(D / 'protected-before.json'),
            'helper_sha256':sha(Path(__file__)),'new_inside_sha256':sha(INSIDE),'new_runner_sha256':sha(RUNNER),
            'new_finish_sha256':sha(FINISH),'new_state_sha256':sha(NEW_STATE),'scope_sha256':sha(PLAN),
            'cases_existed':False,'business_sends_or_model_checkpoints':0,'new_resources_or_policy':0,
            'original_state_overwritten':False,'original_readability_proof_rewritten':False,
            'original_stop_metadata_before_sha256':sha(D / 'original-stop-metadata-before.json'),
            'original_stop_metadata_after_sha256':sha(D / 'original-stop-metadata-after.json'),
            'original_stop_bytes_changed':False})
        print(json.dumps({'prepared':True,'new_business_actions':0,'prepared_sha256':sha(D / 'prepared.json')}))
    except BaseException as error:
        save(D / 'prepare-failure.json', {'error_type':type(error).__name__,'automatic_retry':False})
        raise


def review_binding():
    original_bindings()
    prepared, review = read(D / 'prepared.json'), read(D / 'independent-review.json')
    assert review['change']=='C03-02D-02-contract-recovery-r02'
    assert review['accepted'] is True and review['zero_business_sends_or_models_confirmed'] is True
    for key, want in {'prepared_sha256':sha(D / 'prepared.json'),
        'helper_sha256':sha(Path(__file__)),'new_inside_sha256':sha(INSIDE),
        'new_runner_sha256':sha(RUNNER),'new_finish_sha256':sha(FINISH),'new_state_sha256':sha(NEW_STATE),
        'original_preexec_sha256':prepared['original_preexec_sha256'],'original_stop_sha256':STOP_SHA}.items():
        assert review[key] == want
    assert prepared['new_inside_sha256'] == sha(INSIDE) and prepared['new_runner_sha256'] == sha(RUNNER)
    assert prepared['new_finish_sha256'] == sha(FINISH) and prepared['new_state_sha256'] == sha(NEW_STATE)
    assert sha(PLAN) == prepared['scope_sha256'] == sha(D / 'scope-before.md')
    info = (D / 'independent-review.json').stat()
    assert info.st_uid == 10001 and info.st_mode & 0o777 == 0o600
    return prepared, review


CONTRACT_PROBE = '''import hashlib,json,logging,os,runpy
from pathlib import Path
logging.disable(logging.CRITICAL)
import structlog
def drop(*args):raise structlog.DropEvent
structlog.configure(processors=[drop])
m=runpy.run_path('/operators/quality.py',run_name='actual_recovery_contract_probe')
state,inputs,item=m['check_contract']('ingress','case01')
assert not Path('/evidence/cases').exists()
print(json.dumps({'actual_check_contract_passed':True,'phase':'ingress','case':'case01','uid':os.geteuid(),
 'image_id':os.environ['C03_PROBE_IMAGE_ID'],'inside_sha256':m['file_sha']('/operators/quality.py'),
 'state_sha256':m['file_sha']('/private/state.json'),'inputs_sha256':m['file_sha']('/private/inputs.json'),
 'original_stop_sha256':m['file_sha']('/evidence/safety-stop.json'),
 'Evidence_created':False,'PG_HTTP_Kafka_or_model_call_functions_invoked':False}))'''


def probe():
    assert os.geteuid() == 0 and not (D / 'probe').exists() and not (D / 'authorized.json').exists()
    zero_business_proof();review_binding()
    runner = importlib.import_module('run_triage_validity_quality_recovery_c03')
    name = 'socai2-c03-validity-quality-contract-r02'
    argv = runner.command('ingress','case01',read(NEW_STATE),name,contract_only=True)
    argv[argv.index('--network')+1] = 'none'
    for index, value in enumerate(argv):
        if value.startswith('type=bind,') and ',dst=/evidence' in value:
            argv[index] = value + ',readonly'
    assert argv[-4:] == ['python','/operators/quality.py','ingress','case01']
    argv = argv[:-4] + ['python','-c',CONTRACT_PROBE]
    assert '--user' in argv and argv[argv.index('--user')+1]=='10001:10001' and '--read-only' in argv
    assert any(',dst=/evidence,readonly' in value for value in argv)
    save(D / 'probe/started.json', {'argv':argv,'network':'none','uid':10001,
        'real_original_stop_visible':True,'independent_review_sha256':sha(D / 'independent-review.json'),
        'automatic_retry':False})
    timed_out=False
    try:
        result = subprocess.run(argv,capture_output=True,timeout=60)
        stdout,stderr,code=result.stdout,result.stderr,result.returncode
    except subprocess.TimeoutExpired as error:
        stdout,stderr,code=(error.stdout or b''),(error.stderr or b''),124;timed_out=True
        cleanup=subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)
        save(D / 'probe/named-container-cleanup.json',{'exit_code':cleanup.returncode,
            'stdout_sha256':hashlib.sha256(cleanup.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(cleanup.stderr).hexdigest()})
    for name,data in (('stdout.log',stdout),('stderr.log',stderr)):
        path=D/'probe'/name
        with path.open('xb') as stream:stream.write(data)
        path.chmod(0o600)
    save(D/'probe/exit.json',{'exit_code':code,'timed_out':timed_out,'network':'none',
        'stdout_sha256':hashlib.sha256(stdout).hexdigest(),'stderr_sha256':hashlib.sha256(stderr).hexdigest(),
        'PG_HTTP_Kafka_or_model_actions':0})
    zero_business_proof();review_binding()
    assert code==0 and not timed_out
    value=json.loads(stdout.decode().splitlines()[-1])
    assert value=={'actual_check_contract_passed':True,'phase':'ingress','case':'case01','uid':10001,
        'image_id':IMAGE,'inside_sha256':sha(INSIDE),'state_sha256':sha(NEW_STATE),
        'inputs_sha256':INPUT_SHA,'original_stop_sha256':STOP_SHA,'Evidence_created':False,
        'PG_HTTP_Kafka_or_model_call_functions_invoked':False}
    save(D/'probe/accepted.json',{'actual_result':value,'exit_sha256':sha(D/'probe/exit.json'),
        'probe_started_sha256':sha(D/'probe/started.json'),'independent_review_sha256':sha(D/'independent-review.json'),
        'actual_check_contract_passed':True,'business_authorization_granted_by_probe':False})
    print(json.dumps({'contract_probe_passed':True,'new_business_actions':0}))


def authorize():
    assert os.geteuid()==0 and not (D/'authorized.json').exists()
    zero_business_proof();prepared,_=review_binding()
    assert read(D/'probe/accepted.json')['actual_check_contract_passed'] is True
    assert read(D/'probe/exit.json')['exit_code']==0
    assert read(D/'probe/accepted.json')['exit_sha256']==sha(D/'probe/exit.json')
    save(D/'authorized.json',{'change':'C03-02D-02-contract-recovery-r02','business_execution_authorized':True,
        'prepared_sha256':sha(D/'prepared.json'),'independent_review_sha256':sha(D/'independent-review.json'),
        'probe_accepted_sha256':sha(D/'probe/accepted.json'),'original_stop_sha256':STOP_SHA,
        'original_preexec_sha256':prepared['original_preexec_sha256'],
        'new_inside_sha256':sha(INSIDE),'new_runner_sha256':sha(RUNNER),'new_finish_sha256':sha(FINISH),
        'new_state_sha256':sha(NEW_STATE),'helper_sha256':sha(Path(__file__)),
        'only_original_pre_Evidence_contract_failure_exempt':True,'new_stop_path':'recovery-stop.json'})
    print(json.dumps({'recovery_authorized':True,'new_business_actions':0,'new_runner_sha256':sha(RUNNER)}))


def business_binding(*, allow_new_stop=False):
    review_binding()
    assert sha(E/'safety-stop.json')==STOP_SHA
    assert allow_new_stop or not (E/'recovery-stop.json').exists()
    auth=read(D/'authorized.json')
    for key,want in {'prepared_sha256':sha(D/'prepared.json'),
        'independent_review_sha256':sha(D/'independent-review.json'),'probe_accepted_sha256':sha(D/'probe/accepted.json'),
        'original_stop_sha256':STOP_SHA,'new_inside_sha256':sha(INSIDE),'new_runner_sha256':sha(RUNNER),
        'new_finish_sha256':sha(FINISH),'new_state_sha256':sha(NEW_STATE),'helper_sha256':sha(Path(__file__))}.items():
        assert auth[key]==want
    assert auth['business_execution_authorized'] is True
    old=read(P/'state.json');old['operator_sha256']=sha(INSIDE)
    assert old==read(NEW_STATE), 'Only the inside identity may change in the recovery state'
    return read(NEW_STATE)


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','probe','authorize'))
    args=parser.parse_args();{'prepare':prepare,'probe':probe,'authorize':authorize}[args.phase]()


if __name__=='__main__':
    try:main()
    except BaseException as error:
        if D.is_dir() and not (E/'recovery-stop.json').exists():
            try:save(E/'recovery-stop.json',{'case':'case01','phase':'contract-recovery','error_type':type(error).__name__,'automatic_retry_allowed':False})
            except BaseException:pass
        print(json.dumps({'recovery_failed':True,'error_type':type(error).__name__,
                          'message_or_locals_recorded':False,'automatic_retry':False}))
        raise SystemExit(1) from None
