"""Minimal, backend-ready pseudonymous user and consent state management."""

from __future__ import annotations

import json
import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class UserRecord:
    """The deliberately small AF record; it contains no PII or coordinate field."""

    user_id: str
    scan_ids: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    general_consent: bool
    location_consent: bool


class UserRepository(Protocol):
    """Persistence boundary that a future database repository can implement."""

    def get(self, user_id: str) -> UserRecord | None: ...
    def save(self, record: UserRecord) -> None: ...
    def delete(self, user_id: str) -> bool: ...


class InMemoryUserRepository:
    """Small non-persistent repository suitable for local sessions and tests."""

    def __init__(self) -> None:
        self._records: dict[str, UserRecord] = {}

    def get(self, user_id: str) -> UserRecord | None:
        return self._records.get(user_id)

    def save(self, record: UserRecord) -> None:
        self._records[record.user_id] = record

    def delete(self, user_id: str) -> bool:
        if user_id not in self._records:
            return False
        del self._records[user_id]
        return True


class FileUserRepository:
    """JSON-file repository so pseudonymous users survive API restarts.

    Scan metadata is already persisted by Module AG; keeping users only in
    memory would orphan every stored scan (and the browser's saved user id)
    whenever the server restarts.
    """

    def __init__(self, storage_root: Path | str) -> None:
        root = Path(storage_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._path = root / "users.json"
        self._lock = threading.Lock()
        self._records = self._load()

    def get(self, user_id: str) -> UserRecord | None:
        return self._records.get(user_id)

    def save(self, record: UserRecord) -> None:
        with self._lock:
            self._records[record.user_id] = record
            self._write()

    def delete(self, user_id: str) -> bool:
        with self._lock:
            if user_id not in self._records:
                return False
            del self._records[user_id]
            self._write()
            return True

    def _load(self) -> dict[str, UserRecord]:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        records = {}
        for item in data if isinstance(data, list) else ():
            try:
                records[item["user_id"]] = UserRecord(
                    user_id=item["user_id"], scan_ids=tuple(item.get("scan_ids", ())),
                    created_at=datetime.fromisoformat(item["created_at"]),
                    updated_at=datetime.fromisoformat(item["updated_at"]),
                    general_consent=bool(item["general_consent"]),
                    location_consent=bool(item["location_consent"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
        return records

    def _write(self) -> None:
        data = [
            {
                "user_id": record.user_id, "scan_ids": list(record.scan_ids),
                "created_at": record.created_at.isoformat(), "updated_at": record.updated_at.isoformat(),
                "general_consent": record.general_consent, "location_consent": record.location_consent,
            }
            for record in self._records.values()
        ]
        temporary = self._path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self._path)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _valid_identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _valid_consent(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a boolean")
    return value


class UserManagement:
    """Public AF service with cryptographic IDs and independent consent controls."""

    def __init__(self, repository: UserRepository | None = None, clock: Callable[[], datetime] = _utc_now) -> None:
        self._repository = repository or InMemoryUserRepository()
        self._clock = clock

    def create_user(self, general_consent: bool = False, location_consent: bool = False) -> UserRecord:
        general = _valid_consent(general_consent, "general_consent")
        location = _valid_consent(location_consent, "location_consent")
        user_id = self._new_user_id()
        timestamp = self._timestamp()
        record = UserRecord(user_id, (), timestamp, timestamp, general, location)
        self._repository.save(record)
        return record

    def get_user(self, user_id: str) -> UserRecord | None:
        return self._repository.get(_valid_identifier(user_id, "user_id"))

    def update_consent(self, user_id: str, general_consent: bool) -> UserRecord | None:
        consent = _valid_consent(general_consent, "general_consent")
        record = self.get_user(user_id)
        if record is None:
            return None
        updated = replace(record, general_consent=consent, updated_at=self._timestamp())
        self._repository.save(updated)
        return updated

    def update_location_consent(self, user_id: str, location_consent: bool) -> UserRecord | None:
        consent = _valid_consent(location_consent, "location_consent")
        record = self.get_user(user_id)
        if record is None:
            return None
        updated = replace(record, location_consent=consent, updated_at=self._timestamp())
        self._repository.save(updated)
        return updated

    def add_scan(self, user_id: str, scan_id: str) -> UserRecord | None:
        clean_scan_id = _valid_identifier(scan_id, "scan_id")
        record = self.get_user(user_id)
        if record is None:
            return None
        if clean_scan_id in record.scan_ids:
            return record
        scan_ids = (*record.scan_ids, clean_scan_id)
        updated = replace(record, scan_ids=scan_ids, updated_at=self._timestamp())
        self._repository.save(updated)
        return updated

    def get_user_scans(self, user_id: str) -> tuple[str, ...] | None:
        record = self.get_user(user_id)
        return None if record is None else record.scan_ids

    def delete_user(self, user_id: str) -> bool:
        return self._repository.delete(_valid_identifier(user_id, "user_id"))

    def _new_user_id(self) -> str:
        """Use a cryptographic random token, retrying only on an improbable collision."""
        while True:
            user_id = f"usr_{secrets.token_urlsafe(24)}"
            if self._repository.get(user_id) is None:
                return user_id

    def _timestamp(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime):
            raise TypeError("clock must return a datetime")
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
