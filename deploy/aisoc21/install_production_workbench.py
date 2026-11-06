"""Install the production investigation workbench on 21's loopback interface."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
from pathlib import Path

BASE = Path("/opt/sting-aisoc-socai2")
PRIVATE = BASE / "private/production-workbench"
STATE = BASE / "data/production-workbench"
IMAGE = "sha256:7218b535ca88c17616f563aa1efb6935f8eedd89e5fed4140ea6c8e4949c0be7"


def catalog(sql):
    proc = subprocess.run(["docker", "exec", "-i", "spirithub-postgres-1", "psql", "-XwAtq",
                           "-v", "ON_ERROR_STOP=1", "-U", "spirithub", "-d", "aisoc"],
                          input=sql, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError("production reader configuration failed")
    return proc.stdout.strip()


def verifier(password):
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 4096)
    stored = hashlib.sha256(hmac.digest(key, b"Client Key", "sha256")).digest()
    server = hmac.digest(key, b"Server Key", "sha256")
    encoded = [base64.b64encode(v).decode() for v in (salt, stored, server)]
    return "SCRAM-SHA-256$4096:{}${}:{}".format(*encoded)


def install():
    os.umask(0o077)
    release = Path(__file__).resolve().parents[2]
    if release.parent != BASE / "releases" or not release.name.startswith("production-workbench-"):
        raise ValueError("use the installed workbench release")
    private = PRIVATE.resolve()
    if PRIVATE != private or STATE != STATE.resolve():
        raise ValueError("unexpected runtime directory")
    private.mkdir(exist_ok=True, mode=0o700)
    if private.stat().st_uid != 0 or private.stat().st_mode & 0o077:
        raise ValueError("unsafe workbench configuration directory")
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chown(STATE, 10001, 10001)
    state = catalog("""SELECT CASE WHEN rolpassword IS NULL THEN 'new' ELSE 'configured' END
        FROM pg_authid WHERE rolname='socai2_prod_reader' AND rolcanlogin AND NOT (rolsuper OR rolbypassrls)
        AND shobj_description(oid,'pg_authid')='socai2:production:v1';""")
    password_file = private / "db-password"
    if state not in {"new", "configured"} or (state == "configured" and not password_file.is_file()):
        raise ValueError("unrecognized reader identity or missing workbench private credential")
    if not password_file.exists():
        with password_file.open("x") as f:
            f.write(secrets.token_hex(32))
    password = password_file.read_text().strip()
    if state == "new":
        catalog("ALTER ROLE socai2_prod_reader PASSWORD '" + verifier(password) + "';")
    ca = BASE / "certificates/socai2-ca.crt"
    if not ca.is_file():
        raise ValueError("missing production TLS CA")
    env = private / "reader.env"
    dsn = f"postgresql://socai2_prod_reader:{password}@192.168.1.21:5432/aisoc"
    env.write_text(f"SOCAI2_AUDIT_DATABASE_URL={dsn}?sslmode=verify-full&sslrootcert=/run/certs/ca.crt\n")
    tag = "socai2-processing:processing-20261106-r3"
    pinned = subprocess.check_output(["docker", "image", "inspect", "--format", "{{.Id}}", tag], text=True).strip()
    if pinned != IMAGE:
        raise ValueError("production image identity mismatch")
    service = {
        "image": tag, "container_name": "socai2-production-workbench", "restart": "unless-stopped",
        "network_mode": "host", "user": "10001:10001", "read_only": True, "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"], "pids_limit": 86, "mem_limit": "768m",
        "env_file": [str(env)], "tmpfs": ["/tmp:rw,nosuid,nodev,size=32m,mode=1777"],
        "volumes": [f"{release}:/opt/workbench:ro", f"{STATE}:/var/lib/workbench", f"{ca}:/run/certs/ca.crt:ro"],
        "entrypoint": ["python", "-B", "/opt/workbench/docs/operations/serve_processing_workbench.py"],
        "command": ["--source", "aisoc", "--site", "/var/lib/workbench/site", "--captures", "/var/lib/workbench/captures"],
        "healthcheck": {"test": ["CMD", "python", "-c", ("import urllib.request; "
                                 "urllib.request.urlopen('http://127.0.0.1:4177/_workbench/status',timeout=4).close()")],
                        "interval": "30s", "timeout": "6s", "retries": 3, "start_period": "5s"},
    }
    config = private / "compose.json"
    temp = private / "compose.next"
    temp.write_text(json.dumps({"services": {"workbench": service}}))
    temp.replace(config)
    subprocess.run(["docker", "compose", "-p", "socai2-production-workbench", "-f", str(config),
                    "up", "-d", "--no-build", "--pull", "never"], check=True, timeout=90)


if __name__ == "__main__":
    install()
