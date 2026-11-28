"""Direct policy gates and generated-schema parity; real DDL is tested in 3b evidence."""

import json
from pathlib import Path

import pytest
from app.db.lake_schema import COLUMNS, LakeStoragePolicy, create_table_sql, load_policy

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / "deploy/aisoc21/lake-storage-3b/storage.example.json"


def test_reference_init_and_contract_match_registered_schema():
    policy = load_policy(PROFILE)
    assert create_table_sql(policy).strip() in (ROOT / "services/api/clickhouse/001_init.sql").read_text()
    contract = json.loads((ROOT / "openspec/changes/complete-socai2-investigation-chain/lake-ingress-contract-v1.json").read_text())
    assert [(c[0], c[1]) for c in COLUMNS] == [(c["name"], c["type"]) for c in contract["existing_columns"] + contract["new_columns"]]


def test_policy_is_explicit_and_database_cannot_silently_change():
    with pytest.raises(ValueError, match="explicitly"):
        load_policy("")
    with pytest.raises(ValueError, match="differs"):
        load_policy(PROFILE, database="lyc_other")
    with pytest.raises(FileNotFoundError):
        load_policy(PROFILE.with_name("missing.json"))


def test_policy_requires_all_fields_and_integer_days(tmp_path):
    body = json.loads(PROFILE.read_text())
    body["retention"].pop("legacy_days")
    path = tmp_path / "storage.json"
    path.write_text(json.dumps(body))
    with pytest.raises(ValueError, match="missing"):
        load_policy(path)
    with pytest.raises(ValueError, match="integers"):
        LakeStoragePolicy("lyc_test", ("test-v1",), True, 400)


def test_profile_cannot_inject_database_or_mapping_sql():
    with pytest.raises(ValueError, match="identifier"):
        LakeStoragePolicy("test;DROP", ("test-v1",), 400, 400)
    with pytest.raises(ValueError, match="mapping"):
        LakeStoragePolicy("lyc_test", ("x'",), 400, 400)
