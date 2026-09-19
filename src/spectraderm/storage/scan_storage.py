"""Filesystem-backed, pseudonymous scan metadata storage for Module AG."""

from __future__ import annotations

import json
import secrets
from io import BytesIO
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Protocol

from PIL import Image, UnidentifiedImageError


MAX_IMAGE_ARTIFACT_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
_IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


@dataclass(frozen=True)
class ScanRecord:
    """Reference-only scan metadata; no bytes, coordinates, or PII belong here."""

    scan_id: str
    user_id: str
    timestamp: datetime
    image_reference: str
    feature_reference: str | None
    analysis_reference: str | None
    change_reference: str | None
    created_at: datetime


class UserLookup(Protocol):
    def get_user(self, user_id: str) -> object | None: ...


class ScanRepository(Protocol):
    def get(self, scan_id: str) -> ScanRecord | None: ...
    def save(self, record: ScanRecord) -> None: ...
    def delete(self, scan_id: str) -> bool: ...
    def list_by_user(self, user_id: str) -> Sequence[ScanRecord]: ...


class FileScanRepository:
    """Small JSON metadata repository under the private storage root."""

    def __init__(self, storage_root: Path | str) -> None:
        self.root = Path(storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._metadata_path = self.root / "scan_metadata.json"
        self._records = self._load()

    def get(self, scan_id: str) -> ScanRecord | None:
        return self._records.get(scan_id)

    def save(self, record: ScanRecord) -> None:
        self._records[record.scan_id] = record
        self._write()

    def delete(self, scan_id: str) -> bool:
        if scan_id not in self._records:
            return False
        del self._records[scan_id]
        self._write()
        return True

    def list_by_user(self, user_id: str) -> Sequence[ScanRecord]:
        return tuple(record for record in self._records.values() if record.user_id == user_id)

    def _load(self) -> dict[str, ScanRecord]:
        if not self._metadata_path.exists():
            return {}
        data = json.loads(self._metadata_path.read_text(encoding="utf-8"))
        return {
            item["scan_id"]: ScanRecord(
                scan_id=item["scan_id"], user_id=item["user_id"],
                timestamp=datetime.fromisoformat(item["timestamp"]), image_reference=item["image_reference"],
                feature_reference=item["feature_reference"], analysis_reference=item["analysis_reference"],
                change_reference=item["change_reference"], created_at=datetime.fromisoformat(item["created_at"]),
            ) for item in data
        }

    def _write(self) -> None:
        data = []
        for record in self._records.values():
            item = asdict(record)
            item["timestamp"] = record.timestamp.isoformat()
            item["created_at"] = record.created_at.isoformat()
            data.append(item)
        self._metadata_path.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _reference(value: object, label: str, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    text = _identifier(value, label)
    paths = (PurePath(text), PurePosixPath(text), PureWindowsPath(text))
    if any(path.is_absolute() or ".." in path.parts for path in paths):
        raise ValueError(f"{label} must be a relative reference without path traversal")
    if text.replace("\\", "/") == "scan_metadata.json":
        raise ValueError(f"{label} cannot reference internal metadata")
    return text


class ScanStorage:
    """Public AG service; storage and user lookup are injected backend boundaries."""

    def __init__(
        self, storage_root: Path | str, user_lookup: UserLookup,
        repository: ScanRepository | None = None, clock: Callable[[], datetime] = _now,
    ) -> None:
        self._root = Path(storage_root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._users = user_lookup
        self._repository = repository or FileScanRepository(self._root)
        self._clock = clock

    def create_scan(
        self, user_id: str, image_reference: str, feature_reference: str | None = None,
        analysis_reference: str | None = None, change_reference: str | None = None,
        timestamp: datetime | None = None,
    ) -> ScanRecord:
        clean_user_id = _identifier(user_id, "user_id")
        if self._users.get_user(clean_user_id) is None:
            raise ValueError("user_id does not identify an existing user")
        image = _reference(image_reference, "image_reference", required=True)
        feature = _reference(feature_reference, "feature_reference")
        analysis = _reference(analysis_reference, "analysis_reference")
        change = _reference(change_reference, "change_reference")
        scan_time = self._timestamp(timestamp) if timestamp is not None else self._timestamp()
        created = self._timestamp()
        record = ScanRecord(self._new_scan_id(), clean_user_id, scan_time, image, feature, analysis, change, created)
        self._repository.save(record)
        add_scan = getattr(self._users, "add_scan", None)
        if callable(add_scan):
            add_scan(clean_user_id, record.scan_id)
        return record

    def get_scan(self, user_id: str, scan_id: str) -> ScanRecord | None:
        record = self._repository.get(_identifier(scan_id, "scan_id"))
        return record if record is not None and record.user_id == _identifier(user_id, "user_id") else None

    def list_user_scans(self, user_id: str) -> tuple[ScanRecord, ...]:
        clean_user_id = _identifier(user_id, "user_id")
        return tuple(sorted(self._repository.list_by_user(clean_user_id), key=lambda record: (record.timestamp, record.scan_id)))

    def resolve_image_artifact(self, record: ScanRecord) -> Path:
        """Resolve an AG-managed image reference without accepting arbitrary paths.

        This intentionally returns only an existing regular file inside the
        configured AG storage root. It does not upload, copy, or otherwise
        alter the scan record or its referenced artifact.
        """
        if not isinstance(record, ScanRecord):
            raise TypeError("record must be a ScanRecord")
        path = (self._root / record.image_reference).resolve()
        if not path.is_relative_to(self._root) or not path.is_file():
            raise FileNotFoundError("The scan image artifact was not found in managed storage.")
        return path

    def store_image_artifact(self, user_id: str, content: bytes) -> str:
        """Validate and store one browser-uploaded image under the AG root."""
        clean_user_id = _identifier(user_id, "user_id")
        if self._users.get_user(clean_user_id) is None:
            raise ValueError("user_id does not identify an existing user")
        if not isinstance(content, bytes):
            raise ValueError("image upload must contain bytes")
        if not content:
            raise ValueError("image upload is empty")
        if len(content) > MAX_IMAGE_ARTIFACT_BYTES:
            raise ValueError("image upload exceeds the maximum allowed size")
        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
            with Image.open(BytesIO(content)) as image:
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError("image dimensions exceed the maximum allowed size")
                extension = _IMAGE_FORMATS.get(image.format or "")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise ValueError("image upload is not a supported image") from error
        if extension is None:
            raise ValueError("image upload is not a supported image")

        while True:
            reference = f"images/{clean_user_id}/img_{secrets.token_urlsafe(24)}{extension}"
            destination = self._root / reference
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                with destination.open("xb") as artifact:
                    artifact.write(content)
                return reference
            except FileExistsError:
                continue

    def save_feature_snapshot(self, record: ScanRecord, current_features: dict[str, float]) -> ScanRecord:
        """Persist Module N ``current_features`` so future scans can use this one as history.

        Without this, longitudinal comparison, personal baseline, and change/
        anomaly scoring only ever see scans processed since the last server
        restart, since they would otherwise rely purely on an in-memory cache.
        """
        if not isinstance(record, ScanRecord):
            raise TypeError("record must be a ScanRecord")
        if not isinstance(current_features, dict):
            raise TypeError("current_features must be a dictionary")
        reference = f"features/{record.user_id}/{record.scan_id}.json"
        path = self._root / reference
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            str(name): float(value)
            for name, value in current_features.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        updated = replace(self._repository.get(record.scan_id) or record, feature_reference=reference)
        self._repository.save(updated)
        return updated

    def save_change_record(
        self, record: ScanRecord, change_score: float | None, category: str | None,
        extra: dict[str, object] | None = None,
    ) -> ScanRecord:
        """Persist this scan's Module Q output so later scans can form a trend."""
        if not isinstance(record, ScanRecord):
            raise TypeError("record must be a ScanRecord")
        reference = f"changes/{record.user_id}/{record.scan_id}.json"
        path = self._root / reference
        path.parent.mkdir(parents=True, exist_ok=True)
        score = float(change_score) if isinstance(change_score, (int, float)) and not isinstance(change_score, bool) else None
        payload = {
            **{str(key): value for key, value in (extra or {}).items() if value is None or isinstance(value, (str, int, float))},
            "change_score": score, "category": category if isinstance(category, str) else None,
        }
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        updated = replace(self._repository.get(record.scan_id) or record, change_reference=reference)
        self._repository.save(updated)
        return updated

    def load_change_record(self, record: ScanRecord) -> dict[str, object] | None:
        """Load a persisted Module Q change record, if one exists."""
        if not isinstance(record, ScanRecord):
            raise TypeError("record must be a ScanRecord")
        if record.change_reference is None:
            return None
        path = (self._root / record.change_reference).resolve()
        if not path.is_relative_to(self._root) or not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def load_feature_snapshot(self, record: ScanRecord) -> dict[str, float] | None:
        """Load a previously persisted Module N ``current_features`` snapshot, if any."""
        if not isinstance(record, ScanRecord):
            raise TypeError("record must be a ScanRecord")
        if record.feature_reference is None:
            return None
        path = (self._root / record.feature_reference).resolve()
        if not path.is_relative_to(self._root) or not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        return {
            str(name): float(value)
            for name, value in data.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }

    def delete_scan(self, user_id: str, scan_id: str) -> bool:
        record = self.get_scan(user_id, scan_id)
        if record is None:
            return False
        self._remove_owned_artifacts(record)
        return self._repository.delete(record.scan_id)

    def delete_user_scans(self, user_id: str) -> int:
        records = self.list_user_scans(user_id)
        for record in records:
            self._remove_owned_artifacts(record)
            self._repository.delete(record.scan_id)
        return len(records)

    def _new_scan_id(self) -> str:
        while True:
            scan_id = f"scn_{secrets.token_urlsafe(24)}"
            if self._repository.get(scan_id) is None:
                return scan_id

    def _timestamp(self, value: datetime | None = None) -> datetime:
        timestamp = self._clock() if value is None else value
        if not isinstance(timestamp, datetime):
            raise ValueError("timestamp must be a datetime")
        return timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=timezone.utc)

    def _remove_owned_artifacts(self, record: ScanRecord) -> None:
        for reference in (record.image_reference, record.feature_reference, record.analysis_reference, record.change_reference):
            if reference is None:
                continue
            path = (self._root / reference).resolve()
            if path.is_relative_to(self._root) and path.is_file():
                path.unlink()
