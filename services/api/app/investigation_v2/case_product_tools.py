"""One source-bound product read, using the existing Actions HTTP adapter."""
import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.models.connector import Connector
from app.security.credential_vault import CredentialVaultError, get_vault
from app.services import actions_client

TOOL_NAME = "product_host_details"
HOST_FIELDS = ("device_id", "hostname", "platform", "os_version", "agent_version",
               "local_ip", "external_ip", "last_seen", "first_seen", "containment_status", "tags")
LIMITATION = "产品返回查询时的主机快照，不覆盖Case历史时间窗口，不包含进程树；未找到主机不证明安全。"


class HostArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_alert_id: str
    hostname: str


def supported(connector):
    return (connector is not None and connector.is_enabled and connector.connector_type == "crowdstrike"
            and (connector.allowed_capabilities is None or "get_host" in connector.allowed_capabilities))


class ProductHostTool:
    def __init__(self, db, tenant_id, bindings, case_id):
        self.db, self.tenant_id, self.bindings = db, tenant_id, bindings
        self.case_id = case_id

    @classmethod
    async def from_context(cls, db, tenant_id, context):
        alerts = [item["data"] for item in context["evidence"] if item.get("kind") == "alert"
                  and item.get("data", {}).get("source_connector_id") and item["data"].get("hosts")]
        ids = {UUID(item["source_connector_id"]) for item in alerts}
        connectors = []
        if ids:
            connectors = (await db.execute(select(Connector).where(
                Connector.tenant_id == tenant_id, Connector.id.in_(ids),
                Connector.is_enabled.is_(True), Connector.connector_type == "crowdstrike",
            ))).scalars().all()
        by_id = {str(item.id): item for item in connectors if supported(item)}
        bindings = {}
        for item in alerts:
            connector = by_id.get(item["source_connector_id"])
            hosts = [host for host in item["hosts"] if re.fullmatch(r"[a-zA-Z0-9_.-]{1,253}", host)]
            if connector is not None and hosts:
                bindings[item["alert_id"]] = {"connector_id": str(connector.id), "hosts": hosts}
        return cls(db, tenant_id, bindings, context["case_id"])

    def schemas(self):
        if not self.bindings:
            return []
        parameters = HostArguments.model_json_schema()
        parameters["properties"]["source_alert_id"]["enum"] = sorted(self.bindings)
        parameters["properties"]["hostname"]["enum"] = sorted({
            host for binding in self.bindings.values() for host in binding["hosts"]})
        return [{"type": "function", "function": {"name": TOOL_NAME,
            "description": "从来源告警的CrowdStrike连接器读取该告警主机的当前设备信息、最近在线时间和隔离状态。"
                           "source_alert_id与hostname须属于同一告警。" + LIMITATION,
            "parameters": parameters}}]

    async def execute(self, arguments):
        try:
            args = HostArguments.model_validate(arguments)
            binding = self.bindings.get(args.source_alert_id)
            if binding is None or args.hostname not in binding["hosts"]:
                raise ValueError("host_outside_source_alert")
        except ValueError:
            return {"available": False, "reason": "invalid_or_out_of_scope_arguments", "rows": []}
        result = {"available": False, "rows": [], "query_id": str(uuid4()),
                  "observed_at": datetime.now(UTC).isoformat(),
                  "source": {"source_alert_id": args.source_alert_id, "connector_id": binding["connector_id"],
                             "vendor_id": "crowdstrike", "capability": "get_host"},
                  "query_scope": {"hostname": args.hostname, "time_semantics": "current_snapshot"},
                  "limitation": LIMITATION}
        # Resolve the exact instance again at dispatch, never the first connector of its type.
        connector = (await self.db.execute(select(Connector).where(
            Connector.tenant_id == self.tenant_id, Connector.id == UUID(binding["connector_id"]),
        ))).scalar_one_or_none()
        if not supported(connector):
            return {**result, "reason": "source_connector_unavailable"}
        try:
            credentials = get_vault().decrypt_dict(connector.auth_config or {})
        except CredentialVaultError:
            return {**result, "reason": "source_credentials_unavailable"}
        auth = {key: credentials[key] for key in ("client_id", "client_secret", "base_url") if credentials.get(key)}
        if (connector.connector_config or {}).get("base_url"):
            auth["base_url"] = connector.connector_config["base_url"]
        if not auth.get("client_id") or not auth.get("client_secret"):
            return {**result, "reason": "source_credentials_missing"}
        try:
            body = await actions_client.dispatch_live_action(
                capability="get_host", vendor_id="crowdstrike", target=args.hostname,
                tenant_id=str(self.tenant_id), case_id=self.case_id, auth_config=auth, dry_run=False,
                requested_by="aisoc-case-analysis",
            )
        except actions_client.ActionsServiceError:
            return {**result, "reason": "product_query_failed"}
        upstream = body.get("result")
        if not isinstance(upstream, dict):
            return {**result, "reason": "invalid_product_response"}
        result["upstream_request_id"] = upstream.get("request_id")
        if upstream.get("status") != "succeeded":
            return {**result, "reason": "product_query_not_succeeded", "upstream_status": upstream.get("status")}
        details = upstream.get("details")
        if (not upstream.get("request_id") or upstream.get("vendor_id") != "crowdstrike" or upstream.get("capability") != "get_host"
                or not isinstance(details, dict) or not isinstance(details.get("found"), bool)):
            return {**result, "reason": "invalid_product_response"}
        if details["found"]:
            if (not details.get("device_id") or not isinstance(details.get("hostname"), str)
                    or details["hostname"].casefold() != args.hostname.casefold()):
                return {**result, "reason": "product_host_mismatch"}
            result["rows"] = [{key: details.get(key) for key in HOST_FIELDS}]
        return {**result, "available": True, "returned_count": len(result["rows"]), "truncated": False}
