"""Direct boundary checks: external routes, legacy imports, independent core."""

import ast
import importlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "services/api"
PACKAGE = API / "investigation_http"


def imports(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            yield from (item.name for item in node.names)


def test_external_routes_have_no_internal_implementation_imports():
    forbidden = ("app", "sqlalchemy", "httpx", "aiohttp", "requests")
    for path in (PACKAGE / "external_routes").glob("*.py"):
        assert not [m for m in imports(path) if m.split(".")[0] in forbidden], path.name
    # Reusing core DTOs is allowed only through the explicit contracts boundary;
    # concrete implementations and runtime wiring are restricted to adapters.
    for path in PACKAGE.rglob("*.py"):
        if "adapters" in path.parts or path.name == "contracts.py":
            continue
        assert not [m for m in imports(path) if m.startswith("app.")], path.name
    for path in (API / "app/socai2").glob("*.py"):
        assert not [
            m for m in imports(path) if m.startswith(("investigation_http", "app.api."))
        ], path.name


def test_external_contract_and_compatibility_entry_are_unchanged():
    from app import socai2_main
    from investigation_http.main import app

    before = json.loads(
        (
            ROOT
            / "docs/operations/evidence/http-boundary-20261113-01/before-openapi.json"
        ).read_text()
    )
    after = app.openapi()
    assert after["paths"] == before["paths"]
    assert after["components"] == before["components"]
    assert socai2_main.app is app
    from investigation_http.adapters.runtime import configured_database_name

    assert socai2_main.configured_database_name is configured_database_name
    assert not any(path.startswith(("/internal", "/api/v2")) for path in after["paths"])
    assert "app.investigation_v2.query_api" not in sys.modules
    assert "app.investigation_v2.program_start_api" not in sys.modules
    for name in (
        "cases",
        "case_ai",
        "analysis",
        "pages",
        "tasks",
        "stage_execution",
        "subject_management",
    ):
        legacy = importlib.import_module("app.api.v1.endpoints.socai2_" + name)
        external = importlib.import_module("investigation_http.external_routes." + name)
        assert legacy is external


def test_investigation_core_imports_without_external_http_package():
    # A separate process proves the dependency direction, independent of test
    # collection order and previously imported endpoint modules.
    script = """
import importlib.abc, sys
class NoExternalHTTP(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('investigation_http', 'app.api.')):
            raise AssertionError('core imported HTTP: ' + fullname)
sys.meta_path.insert(0, NoExternalHTTP())
from app.socai2.case_service import CaseService
from app.socai2.stage_results import StageResultService
from app.socai2.baseline_executor import BaselineExecutor
assert all((CaseService, StageResultService, BaselineExecutor))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=API,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
