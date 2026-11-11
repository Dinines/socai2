"""Explicit knowledge retrieval profile; no inferred backend or model space."""
import hashlib
import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError

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
    score_threshold: float = Field(ge=-1, le=1)
    use: str


class Topics(Config):
    material_paths: list[str] = Field(min_length=1)
    label_paths: list[str]
    max_value_characters: int = Field(gt=0)
    max_query_characters: int = Field(gt=0)
    max_queries: int = Field(gt=0)


class Profile(Config):
    version: Literal["socai2.case-knowledge.v1"]
    embedding: Embedding
    vector: Vector
    purposes: dict[str, Purpose]
    topics: Topics
    max_index_chunks: int = Field(gt=0)
    max_chunk_characters: int = Field(gt=0)


def configured():
    return bool(os.environ.get("SOCAI2_KNOWLEDGE_PROFILE", "").strip())


def load():
    try:
        raw = Path(os.environ["SOCAI2_KNOWLEDGE_PROFILE"]).read_bytes()
        profile = Profile.model_validate_json(raw)
        if set(profile.purposes) != {"technical_explanation", "investigation_guidance"}:
            raise ValueError
        if any(p.template.count("{topic}") != 1 for p in profile.purposes.values()):
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
        for name, purpose in profile.purposes.items():
            query = purpose.template.replace("{topic}", "\n".join(terms))
            found.append({"object_key": f"knowledge:{aid}:{name}", "namespace": alert.alert["source_namespace"],
                "object_type": "knowledge_topic", "value": query, "ioc_type": None, "alert_ids": [aid],
                "source_paths": paths, "purpose": name, "purpose_label": purpose.label,
                "filters": {"doc_kinds": purpose.doc_kinds, "tag": purpose.tag},
                "limit": purpose.limit, "score_threshold": purpose.score_threshold, "use": purpose.use})
    return found
