from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from registry.validate_registry import RegistryError, VerifiedRegistrySnapshot, audit_main_snapshot, build_report, load_schema, verify_git_mode, verify_project_sources
from tests.helpers import SHA_B, SHA_C, TREE_A, TREE_B, FakeApi, active_genesis, content, dump, index, mock_released_policy_routes, project


REPO = "owner/repo"


def audited_project_snapshot(entry):
    """Independent synthetic GitHub audit, not a forged YAML 'verified' flag."""
    registry = index({"alpha": entry})
    raw = dump(registry)
    genesis = active_genesis()
    genesis["initial_index_sha256"] = hashlib.sha256(raw).hexdigest()
    genesis["initial_project_identity_hashes"] = {"alpha": entry["identity"]["identity_hash"]}
    release = "e" * 40
    governance = "owner/governance"
    routes = {
        f"repos/{governance}/git/ref/tags/v0.2.0": {"object": {"type": "tag", "sha": "d" * 40}},
        f"repos/{governance}/git/tags/{'d' * 40}": {"object": {"type": "commit", "sha": release}},
        f"repos/{governance}/git/ref/heads/main": {"object": {"sha": release}},
        (f"repos/{governance}/contents/registry/GENESIS.json", (("ref", release),)):
            content(json.dumps(genesis).encode("utf-8")),
        (f"repos/{governance}/contents/projects.yaml", (("ref", release),)): content(raw),
    }
    mock_released_policy_routes(routes, governance, release, genesis)
    return audit_main_snapshot(
        FakeApi(routes), genesis, load_schema(Path("registry/projects.schema.json")),
        expected_policy_commit=release, mint_scan_snapshot=True,
    )


def source_routes(ledger_mode: str = "100644", rules_mode: str = "100644", baseline_mode: str = "100644"):
    return {
        f"repos/{REPO}/commits/main": {
            "sha": SHA_B,
            "commit": {"tree": {"sha": TREE_A}},
        },
        f"repos/{REPO}/commits/{SHA_C}": {
            "sha": SHA_C,
            "commit": {"tree": {"sha": TREE_A}},
        },
        f"repos/{REPO}/git/trees/{TREE_A}": {
            "tree": [
                {"path": "docs", "type": "tree", "mode": "040000", "sha": TREE_B},
                {"path": "AGENTS.md", "type": "blob", "mode": rules_mode, "sha": "3" * 40},
            ]
        },
        f"repos/{REPO}/git/trees/{TREE_B}": {
            "tree": [
                {"path": "LEDGER.md", "type": "blob", "mode": ledger_mode, "sha": "4" * 40},
                {"path": "BASELINE.md", "type": "blob", "mode": baseline_mode, "sha": "5" * 40},
            ]
        },
    }


@pytest.mark.parametrize("mode", ["100644", "100755"])
def test_regular_blob_modes_are_allowed(mode):
    api = FakeApi(source_routes(ledger_mode=mode))
    result = verify_git_mode(api, REPO, TREE_A, "docs/LEDGER.md")
    assert result["mode"] == mode


@pytest.mark.parametrize("mode", ["120000", "160000", "040000", "100664"])
def test_symlink_submodule_tree_and_noncanonical_modes_are_rejected(mode):
    api = FakeApi(source_routes(ledger_mode=mode))
    with pytest.raises(RegistryError) as caught:
        verify_git_mode(api, REPO, TREE_A, "docs/LEDGER.md")
    assert caught.value.code == "PROJECT_PATH_UNSAFE_MODE"


def test_missing_file_is_rejected():
    routes = source_routes()
    routes[f"repos/{REPO}/git/trees/{TREE_B}"]["tree"] = []
    with pytest.raises(RegistryError) as caught:
        verify_git_mode(FakeApi(routes), REPO, TREE_A, "docs/LEDGER.md")
    assert caught.value.code == "PROJECT_PATH_MISSING"


def test_symlink_parent_is_rejected():
    routes = source_routes()
    routes[f"repos/{REPO}/git/trees/{TREE_A}"]["tree"][0].update({"type": "blob", "mode": "120000"})
    with pytest.raises(RegistryError) as caught:
        verify_git_mode(FakeApi(routes), REPO, TREE_A, "docs/LEDGER.md")
    assert caught.value.code == "PROJECT_PATH_UNSAFE_MODE"


def test_verified_active_project_checks_head_and_fixed_contract():
    result = verify_project_sources(FakeApi(source_routes()), "alpha", audited_project_snapshot(project()))
    assert result["read"] == "VERIFIED"
    assert result["project_head"] == SHA_B
    assert len(result["verified_files"]) == 3
    assert result["declared_next"] == "UNKNOWN_NOT_PARSED_BY_REGISTRY"
    assert result["inferred_governance_recommendation"] != result["declared_next"]


def test_unverified_registration_is_not_deep_scanned():
    entry = project()
    entry["registration"] = "unverified"
    api = FakeApi({})
    result = verify_project_sources(api, "alpha", audited_project_snapshot(entry))
    assert result == {"project_id": "alpha", "read": "BLOCKED", "reason": "REGISTRATION_UNVERIFIED"}
    assert api.calls == []


@pytest.mark.parametrize("state", ["paused", "retired"])
def test_inactive_project_is_not_scanned(state):
    entry = project()
    entry["lifecycle"] = state
    entry["lifecycle_history"] = [{
        "lifecycle": state, "changed_at": "2026-10-08T00:00:00Z",
        "previous_index_commit": "a" * 40,
    }]
    api = FakeApi({})
    result = verify_project_sources(api, "alpha", audited_project_snapshot(entry))
    assert result["read"] == "NOT_ATTEMPTED"
    assert api.calls == []


def test_unsafe_ledger_mode_blocks_before_other_files():
    result = verify_project_sources(FakeApi(source_routes(ledger_mode="120000")), "alpha", audited_project_snapshot(project()))
    assert result["read"] == "BLOCKED"
    assert result["reason"] == "PROJECT_PATH_UNSAFE_MODE"


def test_unsafe_fixed_contract_mode_blocks_project():
    result = verify_project_sources(FakeApi(source_routes(baseline_mode="120000")), "alpha", audited_project_snapshot(project()))
    assert result["read"] == "BLOCKED"
    assert len(result["verified_files"]) == 2


def test_missing_fixed_contract_after_partial_read_is_partial():
    routes = source_routes()
    routes[f"repos/{REPO}/git/trees/{TREE_B}"]["tree"] = [
        entry for entry in routes[f"repos/{REPO}/git/trees/{TREE_B}"]["tree"] if entry["path"] != "BASELINE.md"
    ]
    result = verify_project_sources(FakeApi(routes), "alpha", audited_project_snapshot(project()))
    assert result["read"] == "PARTIAL"
    assert result["reason"] == "PROJECT_PATH_MISSING"


def test_truncated_tree_blocks_source_verification():
    routes = source_routes()
    routes[f"repos/{REPO}/git/trees/{TREE_A}"]["truncated"] = True
    result = verify_project_sources(FakeApi(routes), "alpha", audited_project_snapshot(project()))
    assert result["read"] == "BLOCKED"
    assert result["reason"] == "PROJECT_TREE_TRUNCATED"


def test_report_has_independent_dimensions():
    alpha = project()
    beta = project("beta", "owner/beta")
    beta["lifecycle"] = "paused"
    beta["lifecycle_history"] = [
        {"lifecycle": "paused", "changed_at": "2026-10-08T00:00:00Z", "previous_index_commit": "a" * 40}
    ]
    beta["registration"] = "unverified"
    value = index({"alpha": alpha, "beta": beta})
    report = build_report(
        value,
        [
            {"project_id": "alpha", "read": "PARTIAL", "declared_next": "D1", "inferred_governance_recommendation": "HOLD"},
            {"project_id": "beta", "read": "NOT_ATTEMPTED"},
        ],
    )
    assert report["lifecycle"] == {"active": 1, "paused": 1, "retired": 0}
    assert report["registration"] == {"verified": 1, "unverified": 1}
    assert report["read"] == {"VERIFIED": 0, "PARTIAL": 1, "BLOCKED": 0, "NOT_ATTEMPTED": 1}
    assert report["registry_total"] == 2


def test_unknown_read_status_cannot_be_counted():
    with pytest.raises(RegistryError) as caught:
        build_report(index(), [{"project_id": "alpha", "read": "UNKNOWN"}])
    assert caught.value.code == "READ_STATUS_INVALID"


def test_extra_read_result_cannot_change_registry_total():
    with pytest.raises(RegistryError) as caught:
        build_report(index(), [{"project_id": "ghost", "read": "VERIFIED"}])
    assert caught.value.code == "READ_PROJECT_UNKNOWN"


def test_duplicate_read_result_is_rejected():
    with pytest.raises(RegistryError) as caught:
        build_report(
            index(),
            [
                {"project_id": "alpha", "read": "VERIFIED"},
                {"project_id": "alpha", "read": "BLOCKED"},
            ],
        )
    assert caught.value.code == "READ_PROJECT_DUPLICATE"

def test_raw_yaml_verified_flag_cannot_enable_private_repository_scan():
    api = FakeApi({})
    result = verify_project_sources(api, "alpha", project())
    assert result == {"project_id": "alpha", "read": "BLOCKED", "reason": "REGISTRY_CHAIN_UNVERIFIED"}
    assert api.calls == []


def test_fake_plain_dict_receipt_does_not_mint_scan_authority():
    api = FakeApi({})
    raw = {"status": "VERIFIED", "project_id": "alpha", "registration": "verified"}
    result = verify_project_sources(api, "alpha", raw)
    assert result["reason"] == "REGISTRY_CHAIN_UNVERIFIED"
    assert api.calls == []


def test_snapshot_cannot_be_constructed_with_fake_seal():
    with pytest.raises(RegistryError) as caught:
        VerifiedRegistrySnapshot(index(), dump(index()), "e" * 40, "e" * 40, object())
    assert caught.value.code == "REGISTRY_CHAIN_UNVERIFIED"


def test_verified_snapshot_does_not_allow_unknown_repo_scan():
    api = FakeApi({})
    snapshot = audited_project_snapshot(project())
    result = verify_project_sources(api, "unregistered-private-repo", snapshot)
    assert result["reason"] == "PROJECT_NOT_IN_VERIFIED_REGISTRY"
    assert api.calls == []


def test_snapshot_entry_is_copy_not_mutable_shared_state():
    snapshot = audited_project_snapshot(project())
    item = snapshot.project_entry("alpha")
    item["repository"] = "attacker/private-repo"
    item["registration"] = "verified"
    assert snapshot.project_entry("alpha")["repository"] == "owner/repo"
