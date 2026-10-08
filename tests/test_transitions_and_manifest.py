from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from registry.validate_registry import (
    RegistryError,
    build_report,
    candidate_schema_precheck,
    compare_indexes,
    normalized_diff,
    validate_genesis_index,
    validate_manifest,
)
from tests.helpers import SHA_A, SHA_B, index, project


def event(state: str, previous: str = SHA_A, when: str = "2026-10-08T00:00:00Z"):
    return {"lifecycle": state, "changed_at": when, "previous_index_commit": previous}


def test_note_change_is_modified():
    before = index()
    after = copy.deepcopy(before)
    after["projects"]["alpha"]["notes"] = "New note."
    assert compare_indexes(before, after, SHA_A)[0]["kind"] == "MODIFIED"


def test_physical_delete_is_forbidden():
    with pytest.raises(RegistryError, match="tombstones") as caught:
        compare_indexes(index(), index({"beta": project("beta", "owner/beta")}), SHA_A)
    assert caught.value.code == "PHYSICAL_DELETE_FORBIDDEN"


@pytest.mark.parametrize("field", ["canonical_id", "identity_hash"])
def test_identity_fields_cannot_change(field):
    before = index()
    after = copy.deepcopy(before)
    after["projects"]["alpha"]["identity"][field] = "changed"
    with pytest.raises(RegistryError) as caught:
        compare_indexes(before, after, SHA_A)
    assert caught.value.code == "IDENTITY_REPURPOSE_FORBIDDEN"


def test_repository_cannot_change_for_same_id():
    before = index()
    after = copy.deepcopy(before)
    after["projects"]["alpha"]["repository"] = "owner/other"
    with pytest.raises(RegistryError) as caught:
        compare_indexes(before, after, SHA_A)
    assert caught.value.code == "IDENTITY_REPURPOSE_FORBIDDEN"


def test_retirement_keeps_tombstone_and_base_binding():
    before = index()
    after = copy.deepcopy(before)
    entry = after["projects"]["alpha"]
    entry["lifecycle"] = "retired"
    entry["lifecycle_history"].append(event("retired"))
    changes = compare_indexes(before, after, SHA_A)
    assert changes[0]["kind"] == "RETIRED"
    assert changes[0]["after"]["identity"] == before["projects"]["alpha"]["identity"]


@pytest.mark.parametrize(
    "bad_event",
    [
        None,
        event("paused"),
        event("retired", SHA_B),
    ],
)
def test_retirement_requires_exact_event(bad_event):
    before = index()
    after = copy.deepcopy(before)
    after["projects"]["alpha"]["lifecycle"] = "retired"
    if bad_event:
        after["projects"]["alpha"]["lifecycle_history"].append(bad_event)
    with pytest.raises(RegistryError) as caught:
        compare_indexes(before, after, SHA_A)
    assert caught.value.code in {"LIFECYCLE_EVENT_REQUIRED", "LIFECYCLE_EVENT_INVALID"}


def test_reactivation_preserves_retirement_history():
    before = index()
    old = before["projects"]["alpha"]
    old["lifecycle"] = "retired"
    old["lifecycle_history"] = [event("retired", SHA_B, "2026-10-07T00:00:00Z")]
    after = copy.deepcopy(before)
    new = after["projects"]["alpha"]
    new["lifecycle"] = "active"
    new["lifecycle_history"].append(event("active", SHA_A, "2026-10-08T00:00:00Z"))
    changes = compare_indexes(before, after, SHA_A)
    assert changes[0]["kind"] == "REACTIVATED"
    assert changes[0]["after"]["lifecycle_history"][0]["lifecycle"] == "retired"


def test_reactivation_cannot_rewrite_history():
    before = index()
    before["projects"]["alpha"]["lifecycle"] = "retired"
    before["projects"]["alpha"]["lifecycle_history"] = [event("retired", SHA_B)]
    after = copy.deepcopy(before)
    after["projects"]["alpha"]["lifecycle"] = "active"
    after["projects"]["alpha"]["lifecycle_history"] = [event("active", SHA_A)]
    with pytest.raises(RegistryError) as caught:
        compare_indexes(before, after, SHA_A)
    assert caught.value.code == "HISTORY_REWRITE_FORBIDDEN"


def test_spurious_history_event_is_forbidden():
    before = index()
    after = copy.deepcopy(before)
    after["projects"]["alpha"]["lifecycle_history"].append(event("active"))
    with pytest.raises(RegistryError) as caught:
        compare_indexes(before, after, SHA_A)
    assert caught.value.code == "SPURIOUS_HISTORY_EVENT"


def test_new_project_requires_reviewed_base_provenance():
    before = index()
    new = project("beta", "owner/beta")
    after = index({"alpha": project(), "beta": new})
    with pytest.raises(RegistryError) as caught:
        compare_indexes(before, after, SHA_A)
    assert caught.value.code == "NEW_PROJECT_PROVENANCE_INVALID"


def test_new_project_with_base_provenance_is_allowed():
    before = index()
    new = project("beta", "owner/beta")
    new["registration"] = "unverified"
    new["registration_provenance"] = {"kind": "reviewed_change", "previous_index_commit": SHA_A}
    after = index({"alpha": project(), "beta": new})
    changes = compare_indexes(before, after, SHA_A)
    assert changes == [{"id": "beta", "kind": "NEW", "before": None, "after": new}]


@pytest.mark.parametrize("state", ["paused", "retired"])
def test_new_project_cannot_start_inactive(state):
    before = index()
    new = project("beta", "owner/beta")
    new["lifecycle"] = state
    new["registration_provenance"] = {"kind": "reviewed_change", "previous_index_commit": SHA_A}
    after = index({"alpha": project(), "beta": new})
    with pytest.raises(RegistryError) as caught:
        compare_indexes(before, after, SHA_A)
    assert caught.value.code == "NEW_PROJECT_STATE_INVALID"


def test_normalized_diff_is_order_independent():
    one = {"id": "a", "kind": "MODIFIED", "before": {"x": 1}, "after": {"x": 2}}
    two = {"id": "b", "kind": "NEW", "before": None, "after": {"x": 1}}
    assert normalized_diff([one, two]) == normalized_diff([two, one])


def test_normalized_diff_changes_when_payload_changes():
    first = {"id": "a", "kind": "MODIFIED", "before": {"x": 1}, "after": {"x": 2}}
    second = copy.deepcopy(first)
    second["after"]["x"] = 3
    assert normalized_diff([first])[1] != normalized_diff([second])[1]


def test_report_dimensions_each_sum_total():
    value = index({"alpha": project(), "beta": project("beta", "owner/beta")})
    value["projects"]["beta"]["registration"] = "unverified"
    report = build_report(value, [{"project_id": "alpha", "read": "VERIFIED"}])
    assert report["registry_total"] == 2
    for dimension in ("lifecycle", "registration", "read"):
        assert sum(report[dimension].values()) == report["registry_total"]
    assert report["dispatch_authorized"] is False
    assert report["writer_change_authorized"] is False


def test_genesis_raw_hash_is_enforced():
    raw = b"exact raw bytes"
    value = index()
    genesis = {
        "initial_index_sha256": hashlib.sha256(raw).hexdigest(),
        "initial_project_identity_hashes": {"alpha": value["projects"]["alpha"]["identity"]["identity_hash"]},
    }
    validate_genesis_index(genesis, value, raw)
    with pytest.raises(RegistryError) as caught:
        validate_genesis_index(genesis, value, raw + b"\n")
    assert caught.value.code == "GENESIS_INDEX_MISMATCH"


def test_manifest_rejects_dynamic_projects_yaml(tmp_path: Path):
    (tmp_path / "projects.yaml").write_bytes(b"x")
    manifest = tmp_path / "MANIFEST.sha256"
    manifest.write_text(f"{hashlib.sha256(b'x').hexdigest()}  projects.yaml\n", encoding="utf-8")
    with pytest.raises(RegistryError) as caught:
        validate_manifest(tmp_path, manifest)
    assert caught.value.code == "MANIFEST_DYNAMIC_INDEX"


def test_manifest_rejects_duplicate_path(tmp_path: Path):
    manifest = tmp_path / "MANIFEST.sha256"
    digest = "0" * 64
    manifest.write_text(f"{digest}  README.md\n{digest}  README.md\n", encoding="utf-8")
    with pytest.raises(RegistryError) as caught:
        validate_manifest(tmp_path, manifest)
    assert caught.value.code == "MANIFEST_DUPLICATE"

def test_genesis_candidate_precheck_does_not_grant_scan_rights():
    from tests.helpers import dump
    value = index()
    raw = dump(value)
    genesis = {
        "initial_index_sha256": hashlib.sha256(raw).hexdigest(),
        "initial_project_identity_hashes": {
            "alpha": value["projects"]["alpha"]["identity"]["identity_hash"]
        },
    }
    result = candidate_schema_precheck(genesis, value, raw)
    assert result["phase"] == "GENESIS_SCHEMA_PRECHECK"
    assert result["status"] == "SCHEMA_PRECHECK_PASS"
    assert result["registry_trusted"] is False
    assert result["approval_verified"] is False
    assert result["untrusted_registry_view"]["registration"]["verified"] == 0


def test_future_index_update_can_pass_schema_precheck_without_genesis_hash():
    from tests.helpers import dump
    initial = index()
    genesis_raw = dump(initial)
    genesis = {
        "initial_index_sha256": hashlib.sha256(genesis_raw).hexdigest(),
        "initial_project_identity_hashes": {
            "alpha": initial["projects"]["alpha"]["identity"]["identity_hash"]
        },
    }
    updated = index({
        "alpha": project(),
        "beta": project("beta", "owner/beta"),
    })
    updated_raw = dump(updated)
    result = candidate_schema_precheck(genesis, updated, updated_raw)
    assert result["phase"] == "DYNAMIC_SCHEMA_PRECHECK"
    assert result["status"] == "SCHEMA_PRECHECK_PASS"
    assert result["registry_trusted"] is False
    assert result["dispatch_authorized"] is False
    assert result["untrusted_registry_view"]["registration"] == {"verified": 0, "unverified": 2}


def test_precheck_is_not_registration_approval():
    from tests.helpers import dump
    initial = index()
    updated = index({"alpha": project(), "beta": project("beta", "owner/beta")})
    raw = dump(updated)
    genesis = {"initial_index_sha256": hashlib.sha256(dump(initial)).hexdigest()}
    report = candidate_schema_precheck(genesis, updated, raw)
    assert report["approval_verified"] is False
    assert report["writer_change_authorized"] is False


@pytest.mark.parametrize(
    ("tag", "fallback", "allowed"),
    [
        ("v0.2.0", "HOLD_V0_1_SEMANTICS", True),
        ("v0.2.1", "HOLD_V0_2_0_SEMANTICS", True),
        ("v0.2.1", "HOLD_V0_1_SEMANTICS", False),
        ("v0.2.0", "HOLD_V0_2_0_SEMANTICS", False),
        ("v0.2.1", "ENABLE_CANDIDATE_WITHOUT_TAG", False),
        ("v0.2.1", "LATEST_IS_AUTOMATIC", False),
        ("v0.2.0", "LATEST_IS_AUTOMATIC", False),
    ],
)
def test_release_specific_unreleased_behavior_is_fail_closed(tmp_path: Path, tag, fallback, allowed):
    import json
    from tests.helpers import active_genesis
    from registry.validate_registry import load_genesis
    source = active_genesis()
    # active_genesis is normally used as a pre-merge synthetic stub, with
    # empty historical identities. Populate its required immutable identity
    # shape so this test isolates only the version-specific fallback rule.
    source["initial_project_identity_hashes"] = {"alpha": "sha256:" + "0" * 64}
    source["release_tag"] = tag
    source["unreleased_behavior"] = fallback
    p = tmp_path / "GENESIS.json"
    p.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    if allowed:
        observed = load_genesis(p)
        assert observed["release_tag"] == tag
        assert observed["unreleased_behavior"] == fallback
    else:
        with pytest.raises(RegistryError) as err:
            load_genesis(p)
        assert err.value.code == "GENESIS_UNRELEASED_INVALID"


def test_candidate_genesis_requires_previous_verified_v020_not_v010():
    from registry.validate_registry import load_genesis
    source = load_genesis(Path("registry/GENESIS.json"))
    assert source["release_tag"] == "v0.2.1"
    assert source["unreleased_behavior"] == "HOLD_V0_2_0_SEMANTICS"
    # This is policy genesis metadata, not a runtime switch or user approval.
    assert source["status"] == "ACTIVATES_ONLY_AFTER_VERIFIED_RELEASE_TAG"
    assert source["registry_branch"] == "main"
    assert source["registry_path"] == "projects.yaml"
