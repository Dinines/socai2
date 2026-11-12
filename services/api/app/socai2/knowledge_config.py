"""Explicit knowledge retrieval profile; no inferred backend or model space."""
import hashlib
import json
import os
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    ValidationError,
    model_validator,
)

from .baseline_optional_sources import SourceUnavailable


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Embedding(Config):
    url: HttpUrl
    model: str = Field(min_length=1)
    dimension: int = Field(gt=0)
    timeout_seconds: int = Field(gt=0)
    options: dict


class Vector(Config):
    url: HttpUrl
    collection: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    api_key_file: str | None
    timeout_seconds: int = Field(gt=0)


class Purpose(Config):
    label: str
    template: str
    doc_kinds: list[str] = Field(min_length=1)
    tag: str
    limit: int = Field(gt=0)
    candidate_limit: int = Field(gt=0)
    score_threshold: float = Field(ge=-1, le=1)
    use: str


class Topics(Config):
    material_paths: list[str] = Field(min_length=1)
    label_paths: list[str]
    max_value_characters: int = Field(gt=0)
    max_query_characters: int = Field(gt=0)
    max_queries: int = Field(gt=0)


class History(Config):
    lookback_days: int = Field(gt=0)
    max_import_alerts: int = Field(gt=0)
    max_card_characters: int = Field(gt=0)
    observation_paths: list[str] = Field(min_length=1)
    sync_after_adopted_triage: bool = False
    sync_timeout_seconds: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def synchronization_limit(self):
        if self.sync_after_adopted_triage and self.sync_timeout_seconds is None:
            raise ValueError("history_sync_timeout_required")
        return self


class Facet(Config):
    paths: list[str] = Field(min_length=1)
    normalization: Literal["exact", "casefold", "basename_casefold"]
    topic: bool


class Applicability(Config):
    tag_prefix: str = Field(min_length=1)
    generic_tag: str = Field(min_length=1)
    facets: dict[str, Facet] = Field(min_length=1)


class Profile(Config):
    version: Literal["socai2.case-knowledge.v1"]
    embedding: Embedding
    vector: Vector
    purposes: dict[str, Purpose]
    topics: Topics
    max_index_chunks: int = Field(gt=0)
    max_chunk_characters: int = Field(gt=0)
    history: History | None = None
    applicability: Applicability


def configured():
    return bool(os.environ.get("SOCAI2_KNOWLEDGE_PROFILE", "").strip())


def load():
    try:
        raw = Path(os.environ["SOCAI2_KNOWLEDGE_PROFILE"]).read_bytes()
        profile = Profile.model_validate_json(raw)
        required = {"technical_explanation", "investigation_guidance"}
        if not required <= set(profile.purposes) <= required | {"historical_case_reference"}:
            raise ValueError
        if ("historical_case_reference" in profile.purposes) != (profile.history is not None):
            raise ValueError
        if any(p.template.count("{topic}") != 1 for p in profile.purposes.values()):
            raise ValueError
        if any(p.candidate_limit < p.limit for p in profile.purposes.values()):
            raise ValueError
        return profile, hashlib.sha256(raw).hexdigest()
    except (KeyError, OSError, ValueError, ValidationError):
        raise SourceUnavailable("knowledge_profile_missing_or_invalid") from None


def content_hash(row):
    # Metadata participates too: changed purpose tags or source URLs invalidate an index hit.
    fields = {key: row[key] for key in (
        "id", "tenant_id", "title", "doc_kind", "source_url", "tags", "chunk_index", "chunk_total", "content")}
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def at(value, path):
    for part in path.removeprefix("$.").split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def selectors(context, materials, profile):
    from .knowledge_applicability import material_facets
    found = []
    for aid, alert in sorted(context.alerts.items()):
        material = materials.get(aid) or {}
        terms, paths = [], []
        for role, data, configured_paths in (
            ("observation", material, profile.topics.material_paths),
            ("source_label", {"alert": alert.alert, "material": material}, profile.topics.label_paths),
        ):
            for path in configured_paths:
                value = at(data, path)
                if not isinstance(value, str) or not value.strip():
                    continue
                original = value.strip()
                term = original[:profile.topics.max_value_characters]
                terms.append(f"{role} {path}={term}")
                paths.append({"alert_id": aid, "material_id": str(material["id"]) if material.get("id") else None, "source_path": path,
                    "role": role, "original_characters": len(original), "query_text_truncated": term != original})
        if not terms:
            continue
        facets = material_facets(material, profile)
        for name, purpose in profile.purposes.items():
            history_filter = {}
            if name == "historical_case_reference":
                from datetime import datetime, timedelta
                start = getattr(getattr(context, "scope", None), "window_start", None)
                if start is None or not any(facets.get(k) for k, f in profile.applicability.facets.items() if f.topic):
                    continue
                start = datetime.fromisoformat(start) if isinstance(start, str) else start
                history_filter = {"event_start": (start - timedelta(days=profile.history.lookback_days)).isoformat(),
                    "event_before": start.isoformat(), "exclude_alert_ids": sorted(context.alerts)}
            query = purpose.template.replace("{topic}", "\n".join(terms))
            found.append({"object_key": f"knowledge:{aid}:{name}", "namespace": alert.alert["source_namespace"],
                "object_type": "knowledge_topic", "value": query, "ioc_type": None, "alert_ids": [aid],
                "source_paths": list(paths), "purpose": name, "purpose_label": purpose.label,
                "filters": {"doc_kinds": purpose.doc_kinds, "tag": purpose.tag, **history_filter},
                "facets": facets, "candidate_limit": purpose.candidate_limit,
                "limit": purpose.limit, "score_threshold": purpose.score_threshold, "use": purpose.use})
    merged = {}
    for key in found:
        signature = json.dumps({k: key[k] for k in ("purpose", "value", "namespace", "filters", "facets")}, sort_keys=True)
        if signature not in merged:
            merged[signature] = key
        else:
            merged[signature]["alert_ids"].extend(key["alert_ids"])
            merged[signature]["source_paths"].extend(key["source_paths"])
    return list(merged.values())
