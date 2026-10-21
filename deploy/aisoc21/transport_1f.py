#!/usr/bin/env python3
"""Add a verified TLS path for this batch while retaining old LAN listeners.

Host21 infrastructure operator only. PostgreSQL reloads TLS settings without
restart. Kafka is recreated alone with its original image/data volume and an
additional SECURE listener. Private keys/config backups stay outside source.
"""
import hashlib
import json
from pathlib import Path
import ssl
import socket
import subprocess
import sys
import time

from shared_1b import SharedBatch, PG_CONTAINER

ROOT = Path('/opt/sting-aisoc-socai2')
KAFKA = 'sting-infra21-kafka-1'


def main():
    batch = SharedBatch(ROOT)
    evidence = ROOT / 'evidence/1f-20261020'
    private = ROOT / 'private/transport-1f'
    private.mkdir(mode=0o700)
    kafka_certs = private / 'kafka'
    kafka_certs.mkdir(mode=0o755)
    clients = ROOT / 'certificates'
    clients.mkdir(mode=0o755, exist_ok=True)
    compose = Path('/opt/sting-aisoc-infra/compose.yml')
    original = compose.read_bytes()
    (private / 'compose-before.yml').write_bytes(original)
    (private / 'compose-before.yml').chmod(0o600)
    pg_before = json.loads(batch.pg("SELECT json_object_agg(name,setting) FROM pg_settings "
                                   "WHERE name IN ('ssl','ssl_cert_file','ssl_key_file');").stdout)
    (private / 'pg-settings-before.json').write_text(json.dumps(pg_before))
    before = batch.inspect(KAFKA)
    groups = batch.run(['docker','exec',KAFKA,'kafka-consumer-groups','--bootstrap-server',
                        '192.168.1.21:9092','--describe','--all-groups','--state']).stdout
    states = [line.split() for line in groups.splitlines() if line.split() and line.split()[-1].isdigit()]
    if not states or any(int(row[-1]) for row in states):
        raise RuntimeError('Inspect active shared consumers before Kafka recreation')
    def openssl(*args):
        batch.run(['openssl', *args])
    ca_key, ca = private / 'ca.key', clients / 'socai2-ca.crt'
    key, csr, crt = private / 'server.key', private / 'server.csr', private / 'server.crt'
    openssl('req','-x509','-newkey','rsa:3072','-nodes','-keyout',str(ca_key),'-out',str(ca),
            '-days','365','-subj','/CN=socai2 host21 test baseline CA')
    openssl('req','-new','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(csr),
            '-subj','/CN=192.168.1.21')
    extensions = private / 'server.ext'
    extensions.write_text('subjectAltName=IP:192.168.1.21,DNS:kafka\nextendedKeyUsage=serverAuth\n')
    openssl('x509','-req','-in',str(csr),'-CA',str(ca),'-CAkey',str(ca_key),'-CAcreateserial',
            '-out',str(crt),'-days','90','-extfile',str(extensions))
    for f in private.iterdir():
        if f.is_file(): f.chmod(0o600)
    # PEM keystore accepts unencrypted PKCS8 plus certificate chain. Keeping the
    # listener name SECURE avoids Confluent's JKS-specific SSL:// wrapper.
    pem = kafka_certs / 'server.pem'
    pem.write_bytes(key.read_bytes() + crt.read_bytes() + ca.read_bytes())
    pem.chmod(0o400)
    batch.run(['chown','1000:1000',str(pem)])
    pg_dir = '/var/lib/postgresql/data/socai2-tls'
    batch.run(['docker','exec','-u','root',PG_CONTAINER,'sh','-c',
               f'mkdir -m 700 {pg_dir} && chown postgres:postgres {pg_dir}'])
    for name, source in [('server.key',key),('server.crt',crt)]:
        batch.run(['docker','exec','-u','root','-i',PG_CONTAINER,'sh','-c',
                   f'umask 077; cat > {pg_dir}/{name}; chown postgres:postgres {pg_dir}/{name}'],
                  source.read_text())
    batch.pg(f"ALTER SYSTEM SET ssl_cert_file='{pg_dir}/server.crt';\n"
             f"ALTER SYSTEM SET ssl_key_file='{pg_dir}/server.key';\n"
             "ALTER SYSTEM SET ssl='on';\nSELECT pg_reload_conf();")
    for _ in range(15):
        if batch.pg('SHOW ssl;').stdout.strip() == 'on': break
        time.sleep(1)
    else: raise RuntimeError('PG TLS reload failed; private settings backup retained')
    text = original.decode()
    start, end = text.index('  kafka:\n'), text.index('\n  kafka-ui:')
    section = text[start:end]
    section = section.replace('CONTROLLER://0.0.0.0:29093\n', 'CONTROLLER://0.0.0.0:29093,SECURE://0.0.0.0:19093\n')
    section = section.replace('EXTERNAL://${LAN_IP}:9092\n', 'EXTERNAL://${LAN_IP}:9092,SECURE://${LAN_IP}:19093\n')
    section = section.replace('CONTROLLER:PLAINTEXT\n', 'CONTROLLER:PLAINTEXT,SECURE:SSL\n'
                              '      KAFKA_SSL_KEYSTORE_TYPE: PEM\n'
                              '      KAFKA_SSL_KEYSTORE_LOCATION: /etc/kafka/socai2/server.pem\n'
                              '      KAFKA_SSL_CLIENT_AUTH: none\n')
    section = section.replace('ports: ["${LAN_IP}:9092:9092"]',
                              'ports: ["${LAN_IP}:9092:9092", "${LAN_IP}:19093:19093"]')
    section = section.replace('volumes: ["kafka:/var/lib/kafka/data"]',
                              f'volumes: ["kafka:/var/lib/kafka/data", "{kafka_certs}:/etc/kafka/socai2:ro"]')
    if 'SECURE:SSL' not in section or section == text[start:end]:
        raise RuntimeError('Unexpected shared Kafka section; original retained')
    compose.write_text(text[:start] + section + text[end:])
    command = ['docker','compose','--project-directory',str(compose.parent),'-f',str(compose)]
    if batch.run(command+['config','--quiet'],allow_error=True).returncode:
        compose.write_bytes(original)
        raise RuntimeError('Compose validation failed; original restored')
    batch.run(command+['up','-d','--no-deps','--pull','never','kafka'])
    context = ssl.create_default_context(cafile=str(ca))
    started = time.monotonic()
    for _ in range(40):
        try:
            with socket.create_connection(('192.168.1.21',19093),timeout=2) as connection:
                with context.wrap_socket(connection,server_hostname='192.168.1.21') as connection:
                    tls_version = connection.version()
            break
        except OSError: time.sleep(1)
    else: raise RuntimeError('Kafka TLS not ready; backups retained')
    plain = batch.run(['docker','exec',KAFKA,'kafka-topics','--bootstrap-server',
                       '192.168.1.21:9092','--list']).stdout
    after = batch.inspect(KAFKA)
    if before['Image'] != after['Image']:
        raise RuntimeError('Unexpected Kafka image change')
    result = {'batch':'1F','postgres_ssl_reloaded_without_restart':True,
              'postgres_previous_tls_settings':pg_before,'kafka_tls_endpoint':'192.168.1.21:19093',
              'kafka_ca_and_ip_verified_tls_version':tls_version,
              'old_plaintext_listener_still_works':bool(plain.strip()),
              'kafka_image_unchanged':True,'kafka_before_id':before['Id'],'kafka_after_id':after['Id'],
              'kafka_before_mounts':before['Mounts'],'kafka_after_mounts':after['Mounts'],
              'certificate_sha256':hashlib.sha256(crt.read_bytes()).hexdigest(),
              'ca_sha256':hashlib.sha256(ca.read_bytes()).hexdigest(),
              'compose_before_sha256':hashlib.sha256(original).hexdigest(),
              'compose_after_sha256':hashlib.sha256(compose.read_bytes()).hexdigest(),
              'private_backup':str(private),'server_certificate_days':90,'ca_days':365,
              'limitations':['TLS authenticates server; existing Kafka broker has no topic ACL or client authentication',
                            'Old plaintext listeners retained for existing users; no production security certification']}
    (evidence/'transport.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'success':False,'error_type':type(exc).__name__,
                          'action':'Inspect private transport-1f backups and host21 state before retry'}))
        sys.exit(1)
