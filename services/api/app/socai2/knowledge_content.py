"""Select known structured knowledge fields; original documents stay frozen."""
import copy

from app.services.kb_chunking import structured_document

from .baseline_store import digest
from .case_input_hierarchy import project, render


def project_content(value, config, ledger, origin):
    """Called only for knowledge cards, after the original input guard."""
    if not isinstance(value, dict) or not isinstance(value.get("record"), dict):
        return value
    content = value["record"].get("content")
    if not isinstance(content, str):
        return value
    document = structured_document(content)
    policy = config["knowledge_selection"]["content_projection"]
    profile = next((p for p in policy["profiles"] if isinstance(document, dict)
                    and all(type(document.get(k)).__name__ == kind for k, kind in p["required_fields"].items())), None)
    if profile is None:
        return value  # Plain text and unsupported/partial structures are not guessed.
    selected = project(document, "content", {"hierarchy": {"content": profile["rules"]}}, ledger, origin)
    # Keep the same field view across C3 and follow-up stages; local stage
    # labels must not change a shared knowledge source's projected value.
    display = {"presentation": {"labels": policy["labels"], "equal_fields": [], "map_containers": []}}
    result = copy.deepcopy(value)
    result["record"]["content"] = render(selected, display)
    ledger.append({"origin": origin, "reason": "structured_knowledge_business_fields",
                   "profile": profile["name"], "original_content_sha256": digest(content),
                   "selected_value_sha256": digest(selected)})
    return result
