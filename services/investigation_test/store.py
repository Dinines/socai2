"""Immutable revisions with one atomic current pointer; no business connections."""
import base64
import fcntl
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from .models import TERMINAL, Document, Evidence, Ledger, PublishedDocument

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
REVISION = re.compile(r"rev-([1-9][0-9]*)-[a-f0-9]{32}\Z")


class LedgerError(Exception):
    def __init__(self, code, status=503):
        self.code, self.status = code, status
        super().__init__(code)


def now():
    return datetime.now(timezone.utc)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def identifier(value):
    if not ID.fullmatch(value):
        raise LedgerError("invalid_identifier", 422)
    return value


def read_bytes(path, limit):
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise LedgerError("file_size_limit")
    return data


def safe_path(root, *parts):
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise LedgerError("ledger_unavailable")
    return path


def synced_write(path, data):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Store:
    def __init__(self, config):
        self.config = config
        self.root = Path(config.ledger_root)

    def load(self, batch_id):
        batch_id = identifier(batch_id)
        try:
            directory = safe_path(self.root, batch_id)
            pointer = safe_path(directory, "current.json")
            if not pointer.exists():
                raise LedgerError("batch_not_found", 404)
            target = json.loads(read_bytes(pointer, self.config.max_document_bytes))
            if set(target) != {"directory", "sha256"} or not isinstance(target["directory"], str):
                raise ValueError("invalid pointer")
            match = REVISION.fullmatch(target["directory"])
            if not match:
                raise ValueError("invalid revision")
            revision_dir = safe_path(directory, target["directory"])
            raw = read_bytes(safe_path(revision_dir, "ledger.json"), self.config.max_document_bytes)
            if digest(raw) != target["sha256"]:
                raise ValueError("ledger digest mismatch")
            ledger = Ledger.model_validate_json(raw)
            if ledger.revision != int(match[1]) or ledger.document.batch.id != batch_id:
                raise ValueError("ledger identity mismatch")
            return ledger, revision_dir, target["sha256"]
        except LedgerError:
            raise
        except (OSError, ValueError, TypeError, KeyError, ValidationError):
            raise LedgerError("ledger_unavailable") from None

    def all(self):
        try:
            if not self.root.exists():
                return []
            result = []
            for entry in self.root.iterdir():
                if (ID.fullmatch(entry.name) and (entry.is_symlink() or entry.is_dir())
                        and safe_path(self.root, entry.name, "current.json").exists()):
                    result.append(self.load(entry.name))
            return result
        except OSError:
            raise LedgerError("ledger_unavailable") from None

    def evidence(self, batch_id, evidence_id):
        evidence_id = identifier(evidence_id)
        ledger, directory, _ = self.load(batch_id)
        item = next((e for e in ledger.document.evidence if e.id == evidence_id), None)
        if item is None:
            raise LedgerError("evidence_not_found", 404)
        try:
            body = read_bytes(safe_path(directory, "evidence", item.id), self.config.max_evidence_bytes)
            if len(body) != item.size or digest(body) != item.sha256:
                raise ValueError("invalid evidence")
            return item, body
        except (OSError, ValueError, LedgerError):
            raise LedgerError("evidence_unavailable") from None

    def publish(self, document_path, expected_revision):
        if type(expected_revision) is not int or expected_revision < 0:
            raise LedgerError("invalid_revision", 422)
        source = Path(document_path).absolute()
        try:
            document = Document.model_validate_json(read_bytes(source, self.config.max_document_bytes))
            evidence, bodies = [], {}
            for item in document.evidence:
                relative = Path(item.path)
                if relative.is_absolute() or not relative.parts or any(p.startswith(".") for p in relative.parts):
                    raise LedgerError("invalid_evidence_path", 422)
                path = safe_path(source.parent, *relative.parts)
                if not path.is_file():
                    raise LedgerError("evidence_source_unavailable", 422)
                body = read_bytes(path, self.config.max_evidence_bytes)
                bodies[item.id] = body
                evidence.append(Evidence(id=item.id, label=item.label, mime_type=item.mime_type,
                    size=len(body), sha256=digest(body), source_ref=item.source_ref))
            data = document.model_dump(mode="json")
            data["evidence"] = [e.model_dump(mode="json") for e in evidence]
            published = PublishedDocument.model_validate_json(encoded(data))
            self.root.mkdir(parents=True, exist_ok=True)
            lock_path = safe_path(self.root, ".publish.lock")
            with lock_path.open("a+b") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                return self._publish_locked(published, bodies, expected_revision)
        except LedgerError:
            raise
        except ValidationError:
            raise LedgerError("invalid_document", 422) from None
        except (OSError, ValueError, TypeError):
            raise LedgerError("publication_failed") from None

    def _publish_locked(self, document, bodies, expected_revision):
        try:
            old, _, _ = self.load(document.batch.id)
        except LedgerError as exc:
            if exc.code != "batch_not_found":
                raise
            old = None
        revision = old.revision if old else 0
        if revision != expected_revision:
            raise LedgerError("revision_conflict", 409)
        if old and old.document.batch.execution_state in TERMINAL:
            raise LedgerError("batch_terminal", 409)
        if old:
            for key in ("id", "environment", "scenario_version", "mode", "provenance"):
                if getattr(old.document.batch, key) != getattr(document.batch, key):
                    raise LedgerError("batch_identity_changed", 409)
            if old.document.batch.started_at is not None and document.batch.started_at != old.document.batch.started_at:
                raise LedgerError("batch_identity_changed", 409)
            if document.batch.updated_at < old.document.batch.updated_at:
                raise LedgerError("batch_time_regressed", 409)
        ledger = Ledger(revision=revision + 1, published_at=now(), document=document)
        raw = ledger.model_dump_json().encode()
        if len(raw) > self.config.max_document_bytes:
            raise LedgerError("document_size_limit", 422)
        directory = safe_path(self.root, document.batch.id)
        directory.mkdir(exist_ok=True)
        token = uuid4().hex
        temporary = directory / (".pending-" + token)
        temporary.mkdir()
        (temporary / "evidence").mkdir()
        for key, body in bodies.items():
            synced_write(temporary / "evidence" / key, body)
        sync_dir(temporary / "evidence")
        synced_write(temporary / "ledger.json", raw)
        sync_dir(temporary)
        name = f"rev-{ledger.revision}-{token}"
        os.rename(temporary, directory / name)
        pointer = directory / (".current-" + token)
        synced_write(pointer, encoded({"directory": name, "sha256": digest(raw)}))
        os.replace(pointer, safe_path(directory, "current.json"))
        sync_dir(directory)
        sync_dir(self.root)
        return ledger


def paginate(items, *, scope, snapshot, limit, cursor, config):
    limit = config.default_limit if limit is None else limit
    if not 1 <= limit <= config.max_limit:
        raise LedgerError("invalid_limit", 422)
    binding = digest(encoded({"scope": scope, "limit": limit}))
    offset = 0
    if cursor is not None:
        try:
            if len(cursor.encode()) > config.max_cursor_bytes:
                raise ValueError("cursor too long")
            value = json.loads(base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True))
            if set(value) != {"scope", "snapshot", "offset"} or value["scope"] != binding:
                raise ValueError("cursor scope mismatch")
            if type(value["offset"]) is not int or value["offset"] < 0:
                raise ValueError("invalid offset")
            if value["snapshot"] != snapshot:
                raise LedgerError("cursor_stale", 409)
            if value["offset"] > len(items):
                raise ValueError("invalid offset")
            offset = value["offset"]
        except LedgerError:
            raise
        except (ValueError, TypeError, KeyError):
            raise LedgerError("invalid_cursor", 422) from None
    selected = items[offset:offset + limit]
    following = offset + len(selected)
    next_cursor = None
    if following < len(items):
        next_cursor = base64.urlsafe_b64encode(encoded({"scope": binding, "snapshot": snapshot, "offset": following})).decode().rstrip("=")
    return {"items": selected, "total": len(items), "next_cursor": next_cursor, "observed_at": now()}
