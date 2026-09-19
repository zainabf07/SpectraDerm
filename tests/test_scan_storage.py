from datetime import datetime, timedelta, timezone

import pytest

from spectraderm.storage.scan_storage import ScanRecord, ScanStorage


class Users:
    def __init__(self, ids=("usr-one",)): self.ids = set(ids)
    def get_user(self, user_id): return {"user_id": user_id} if user_id in self.ids else None


class Clock:
    def __init__(self): self.value = datetime(2026, 1, 1, tzinfo=timezone.utc)
    def __call__(self): value = self.value; self.value += timedelta(seconds=1); return value


def storage(tmp_path, users=None): return ScanStorage(tmp_path, users or Users(), clock=Clock())


def test_scan_creation_has_pseudonymous_id_user_and_timestamps(tmp_path):
    record = storage(tmp_path).create_scan("usr-one", "artifacts/image.ref")
    assert record.scan_id.startswith("scn_") and record.user_id == "usr-one"
    assert record.timestamp.tzinfo is not None and record.created_at.tzinfo is not None


def test_scan_ids_are_unique(tmp_path):
    scans = storage(tmp_path)
    assert scans.create_scan("usr-one", "a").scan_id != scans.create_scan("usr-one", "b").scan_id


def test_metadata_stores_references_only(tmp_path):
    record = storage(tmp_path).create_scan("usr-one", "images/a.bin", "features/a.json", "analysis/a.json", "change/a.json")
    assert (record.image_reference, record.feature_reference, record.analysis_reference, record.change_reference) == (
        "images/a.bin", "features/a.json", "analysis/a.json", "change/a.json")


def test_retrieval_and_unknown_scan_handling(tmp_path):
    scans = storage(tmp_path); record = scans.create_scan("usr-one", "a")
    assert scans.get_scan("usr-one", record.scan_id) == record
    assert scans.get_scan("usr-one", "scn-unknown") is None


def test_wrong_user_cannot_read_or_delete_scan(tmp_path):
    scans = storage(tmp_path, Users(("usr-one", "usr-two"))); record = scans.create_scan("usr-one", "a")
    assert scans.get_scan("usr-two", record.scan_id) is None
    assert scans.delete_scan("usr-two", record.scan_id) is False
    assert scans.get_scan("usr-one", record.scan_id) == record


def test_history_is_chronological(tmp_path):
    scans = storage(tmp_path)
    later = scans.create_scan("usr-one", "later", timestamp=datetime(2026, 2, 1, tzinfo=timezone.utc))
    earlier = scans.create_scan("usr-one", "earlier", timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert scans.list_user_scans("usr-one") == (earlier, later)


def test_delete_scan_removes_metadata_and_owned_artifact(tmp_path):
    artifact = tmp_path / "artifacts" / "image.bin"; artifact.parent.mkdir(); artifact.write_bytes(b"synthetic")
    scans = storage(tmp_path); record = scans.create_scan("usr-one", "artifacts/image.bin")
    assert scans.delete_scan("usr-one", record.scan_id) is True
    assert scans.get_scan("usr-one", record.scan_id) is None and not artifact.exists()


def test_delete_user_scans_removes_all_owned_scans_and_artifacts(tmp_path):
    for name in ("a.bin", "b.bin"):
        path = tmp_path / name; path.write_bytes(b"x")
    scans = storage(tmp_path); scans.create_scan("usr-one", "a.bin"); scans.create_scan("usr-one", "b.bin")
    assert scans.delete_user_scans("usr-one") == 2
    assert scans.list_user_scans("usr-one") == () and not (tmp_path / "a.bin").exists() and not (tmp_path / "b.bin").exists()


@pytest.mark.parametrize("reference", ["../outside", "..\\outside", "/absolute/path", "C:\\absolute\\path"])
def test_path_traversal_and_absolute_references_are_rejected(tmp_path, reference):
    with pytest.raises(ValueError): storage(tmp_path).create_scan("usr-one", reference)


def test_unknown_user_and_malformed_input_are_rejected(tmp_path):
    scans = storage(tmp_path)
    with pytest.raises(ValueError): scans.create_scan("unknown", "image")
    with pytest.raises(ValueError): scans.create_scan("usr-one", "")
    with pytest.raises(ValueError): scans.list_user_scans(" ")


def test_metadata_has_no_location_pii_or_image_bytes_fields():
    fields = set(ScanRecord.__dataclass_fields__)
    assert fields == {"scan_id", "user_id", "timestamp", "image_reference", "feature_reference", "analysis_reference", "change_reference", "created_at"}
    assert not fields.intersection({"latitude", "longitude", "name", "email", "phone", "address", "image_bytes"})


def test_reopening_file_repository_preserves_structured_metadata(tmp_path):
    first = storage(tmp_path); record = first.create_scan("usr-one", "image")
    reopened = storage(tmp_path)
    assert reopened.get_scan("usr-one", record.scan_id) == record


def test_input_objects_are_not_mutated_and_results_are_immutable(tmp_path):
    scans = storage(tmp_path); reference = "image"; record = scans.create_scan("usr-one", reference)
    assert reference == "image"
    with pytest.raises(Exception): record.user_id = "changed"
