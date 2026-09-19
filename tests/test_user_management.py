from datetime import datetime, timedelta, timezone

import pytest

from spectraderm.users.user_management import InMemoryUserRepository, UserManagement, UserRecord


class Clock:
    def __init__(self): self.value = datetime(2026, 1, 1, tzinfo=timezone.utc)
    def __call__(self):
        value = self.value
        self.value += timedelta(seconds=1)
        return value


def service(): return UserManagement(clock=Clock())


def test_creation_generates_unique_pseudonymous_ids():
    users = service()
    first, second = users.create_user(), users.create_user()
    assert first.user_id != second.user_id and first.user_id.startswith("usr_")


def test_user_creation_retrieval_and_timestamps():
    users = service()
    created = users.create_user()
    assert users.get_user(created.user_id) == created
    assert created.created_at.tzinfo is not None and created.updated_at == created.created_at


def test_default_consent_states_are_false_and_independent():
    record = service().create_user()
    assert record.general_consent is False and record.location_consent is False


def test_general_consent_does_not_change_location_consent():
    users = service(); record = users.create_user(location_consent=False)
    updated = users.update_consent(record.user_id, True)
    assert updated.general_consent is True and updated.location_consent is False


def test_location_consent_does_not_change_general_consent():
    users = service(); record = users.create_user(general_consent=False)
    updated = users.update_location_consent(record.user_id, True)
    assert updated.general_consent is False and updated.location_consent is True


def test_consent_update_updates_timestamp():
    users = service(); record = users.create_user()
    assert users.update_consent(record.user_id, True).updated_at > record.updated_at


def test_add_scan_associates_only_scan_ids():
    users = service(); record = users.create_user()
    updated = users.add_scan(record.user_id, "scan-synthetic-1")
    assert updated.scan_ids == ("scan-synthetic-1",)


def test_duplicate_scan_is_not_duplicated():
    users = service(); record = users.create_user()
    users.add_scan(record.user_id, "scan-1")
    assert users.add_scan(record.user_id, "scan-1").scan_ids == ("scan-1",)


def test_get_user_scans_preserves_association_order():
    users = service(); record = users.create_user()
    users.add_scan(record.user_id, "scan-1"); users.add_scan(record.user_id, "scan-2")
    assert users.get_user_scans(record.user_id) == ("scan-1", "scan-2")


def test_unknown_users_return_none_or_false():
    users = service()
    assert users.get_user("unknown") is None and users.add_scan("unknown", "scan") is None
    assert users.get_user_scans("unknown") is None and users.delete_user("unknown") is False


def test_delete_removes_user_and_scan_associations():
    users = service(); record = users.create_user(); users.add_scan(record.user_id, "scan-1")
    assert users.delete_user(record.user_id) is True and users.get_user(record.user_id) is None
    assert users.get_user_scans(record.user_id) is None


def test_record_has_no_coordinate_or_unnecessary_pii_fields():
    fields = set(UserRecord.__dataclass_fields__)
    assert fields == {"user_id", "scan_ids", "created_at", "updated_at", "general_consent", "location_consent"}
    assert not fields.intersection({"latitude", "longitude", "name", "email", "phone", "address", "password"})


def test_records_are_immutable_and_input_values_are_not_mutated():
    users = service(); record = users.create_user()
    with pytest.raises(Exception): record.user_id = "changed"
    assert users.get_user(record.user_id) == record


def test_empty_identifiers_and_non_boolean_consent_are_rejected():
    users = service(); record = users.create_user()
    with pytest.raises(ValueError): users.get_user(" ")
    with pytest.raises(ValueError): users.add_scan(record.user_id, "")
    with pytest.raises(ValueError): users.update_consent(record.user_id, 1)
    with pytest.raises(ValueError): users.create_user(location_consent="yes")


def test_injected_repository_is_supported_for_backend_replacement():
    repository = InMemoryUserRepository(); users = UserManagement(repository, Clock())
    record = users.create_user()
    assert repository.get(record.user_id) == record
