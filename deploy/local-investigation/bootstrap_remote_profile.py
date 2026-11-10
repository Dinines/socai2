"""Copy an existing reader password/public CA to local private configuration.

No remote installation, credential rotation, SQL, or production login keys.
"""

import argparse
import base64
import json
import os
import secrets
import shlex
import subprocess
from pathlib import Path

import tomllib
from config import minimal_process_environment
from remote_profile import SECRET_ENV_KEYS, load_profile, local_path, need


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile")
    args = parser.parse_args()
    path = Path(args.profile).resolve(strict=True)
    cfg = tomllib.loads(path.read_text())
    ssh = cfg["ssh"]
    secret_path = local_path(cfg["secrets_file"])
    ca_path = local_path(cfg["database"]["sslrootcert"])
    need(secret_path.parent == ca_path.parent, "private_config_and_ca_must_share_directory")
    need(not secret_path.exists() and not ca_path.exists(), "existing_profile_credentials_are_not_overwritten")
    secret_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    need(not secret_path.parent.is_symlink() and secret_path.parent.stat().st_mode & 0o077 == 0,
         "private_directory_requires_owner_only_access")
    code = (
        "import json,pathlib,sys; "
        "print(json.dumps({'password':pathlib.Path(sys.argv[1]).read_text().strip(),"
        "'ca':pathlib.Path(sys.argv[2]).read_text()}))"
    )
    remote_command = shlex.join(["python3", "-c", code, ssh["database_password_file"], ssh["ca_file"]])
    result = subprocess.run(
        [ssh["binary"], "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "UpdateHostKeys=no",
         "-o", "ConnectionAttempts=1", "-o", f"ConnectTimeout={ssh['connect_timeout_seconds']}",
         ssh["target"], remote_command],
        env=minimal_process_environment(), capture_output=True, check=True,
        timeout=ssh["startup_timeout_seconds"], text=True,
    )
    remote = json.loads(result.stdout)
    need(bool(remote["password"]) and "BEGIN CERTIFICATE" in remote["ca"], "remote_reader_configuration_incomplete")
    environment = {key: secrets.token_hex(32) for key in SECRET_ENV_KEYS}
    environment["AISOC_CREDENTIAL_KEY"] = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    values = {"database_password": remote["password"], "access_token": secrets.token_urlsafe(48), "environment": environment}
    for target, content in ((secret_path, json.dumps(values, indent=2) + "\n"), (ca_path, remote["ca"])):
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as output:
            output.write(content)
    profile = load_profile(path)
    print(json.dumps({"profile": profile.config["name"], "local_private_configuration_created": True,
                      "production_changes": False}))


if __name__ == "__main__":
    main()
