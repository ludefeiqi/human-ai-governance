from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from registry.validate_registry import RegistryError, build_report, load_schema, scan_authorized_main, verify_git_mode
from tests.helpers import SHA_B, SHA_C, TREE_A, TREE_B, FakeApi, active_genesis, content, dump, index, mock_released_policy_routes, project


REPO = "owner/repo"


def audited_source_api(entry, project_routes=None):
    """Synthetic complete GitHub policy/registry evidence for one R0 transaction."""
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
        (f"repos/{governance}/contents/projects.yaml", (("ref", release),)): content(raw),
    }
    mock_released_policy_routes(routes, governance, release, genesis)
    routes.update(project_routes or {})
    return FakeApi(routes), genesis, release


def run_project(entry, project_routes):
    api, genesis, release = audited_source_api(entry, project_routes)
    audited = scan_authorized_main(
        api, genesis, load_schema(Path("registry/projects.schema.json")),
        expected_policy_commit=release, authorized_project_ids=("alpha",),
    )
    return audited["project_reads"][0], api


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
    result, _ = run_project(project(), source_routes())
    assert result["read"] == "VERIFIED"
    assert result["project_head"] == SHA_B
    assert len(result["verified_files"]) == 3
    assert result["declared_next"] == "UNKNOWN_NOT_PARSED_BY_REGISTRY"
    assert result["inferred_governance_recommendation"] != result["declared_next"]


def test_unverified_registration_is_not_deep_scanned():
    entry = project()
    entry["registration"] = "unverified"
    result, api = run_project(entry, {})
    assert result == {"project_id": "alpha", "read": "BLOCKED", "reason": "REGISTRATION_UNVERIFIED"}
    assert not [endpoint for endpoint, _ in api.calls if endpoint.startswith("repos/owner/repo/")]


@pytest.mark.parametrize("state", ["paused", "retired"])
def test_inactive_project_is_not_scanned(state):
    entry = project()
    entry["lifecycle"] = state
    entry["lifecycle_history"] = [{
        "lifecycle": state, "changed_at": "2026-10-08T00:00:00Z",
        "previous_index_commit": "a" * 40,
    }]
    result, api = run_project(entry, {})
    assert result["read"] == "NOT_ATTEMPTED"
    assert not [endpoint for endpoint, _ in api.calls if endpoint.startswith("repos/owner/repo/")]


def test_unsafe_ledger_mode_blocks_before_other_files():
    result, _ = run_project(project(), source_routes(ledger_mode="120000"))
    assert result["read"] == "BLOCKED"
    assert result["reason"] == "PROJECT_PATH_UNSAFE_MODE"


def test_unsafe_fixed_contract_mode_blocks_project():
    result, _ = run_project(project(), source_routes(baseline_mode="120000"))
    assert result["read"] == "BLOCKED"
    assert len(result["verified_files"]) == 2


def test_missing_fixed_contract_after_partial_read_is_partial():
    routes = source_routes()
    routes[f"repos/{REPO}/git/trees/{TREE_B}"]["tree"] = [
        entry for entry in routes[f"repos/{REPO}/git/trees/{TREE_B}"]["tree"] if entry["path"] != "BASELINE.md"
    ]
    result, _ = run_project(project(), routes)
    assert result["read"] == "PARTIAL"
    assert result["reason"] == "PROJECT_PATH_MISSING"


def test_truncated_tree_blocks_source_verification():
    routes = source_routes()
    routes[f"repos/{REPO}/git/trees/{TREE_A}"]["truncated"] = True
    result, _ = run_project(project(), routes)
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

def test_raw_yaml_verified_flag_is_not_a_scan_api_argument():
    import registry.validate_registry as module
    assert not hasattr(module, "verify_project_sources")
    assert not hasattr(module, "VerifiedRegistrySnapshot")
    assert not hasattr(module, "_VERIFIED_SNAPSHOT_SEAL")


def test_no_external_commit_pin_prevents_any_private_repository_scan():
    api = FakeApi({})
    with pytest.raises(RegistryError) as caught:
        scan_authorized_main(
            api, active_genesis(), load_schema(Path("registry/projects.schema.json")),
            expected_policy_commit="", authorized_project_ids=("alpha",),
        )
    assert caught.value.code == "POLICY_PIN_REQUIRED"
    assert api.calls == []


def test_unknown_project_id_does_not_trigger_private_repository_scan():
    api, genesis, release = audited_source_api(project(), {})
    with pytest.raises(RegistryError) as caught:
        scan_authorized_main(
            api, genesis, load_schema(Path("registry/projects.schema.json")),
            expected_policy_commit=release, authorized_project_ids=("attacker-secret",),
        )
    assert caught.value.code == "PROJECT_NOT_IN_VERIFIED_REGISTRY"
    assert not [endpoint for endpoint, _ in api.calls if endpoint.startswith("repos/owner/repo/")]


def test_duplicate_or_malformed_scan_scope_is_rejected():
    for scope in ("alpha", ("alpha", "alpha"), ("alpha", 0)):
        api, genesis, release = audited_source_api(project(), {})
        with pytest.raises(RegistryError) as caught:
            scan_authorized_main(
                api, genesis, load_schema(Path("registry/projects.schema.json")),
                expected_policy_commit=release, authorized_project_ids=scope,
            )
        assert caught.value.code == "SCAN_SCOPE_INVALID"


class SequencedRegistryHeads(FakeApi):
    def __init__(self, routes, heads):
        super().__init__(routes)
        self.heads = iter(heads)

    def get(self, endpoint, fields=None):
        if endpoint == "repos/owner/governance/git/ref/heads/main":
            self.calls.append((endpoint, ()))
            return {"object": {"sha": next(self.heads)}}
        return super().get(endpoint, fields)


def test_registry_paused_after_audit_blocks_before_scanning():
    api, genesis, release = audited_source_api(project(), source_routes())
    api = SequencedRegistryHeads(api.routes, [release, release, "f" * 40])
    with pytest.raises(RegistryError) as caught:
        scan_authorized_main(
            api, genesis, load_schema(Path("registry/projects.schema.json")),
            expected_policy_commit=release, authorized_project_ids=("alpha",),
        )
    assert caught.value.code == "REGISTRY_HEAD_DRIFT"
    assert not [endpoint for endpoint, _ in api.calls if endpoint.startswith("repos/owner/repo/")]


def test_registry_retired_during_project_read_rejects_entire_transaction():
    api, genesis, release = audited_source_api(project(), source_routes())
    api = SequencedRegistryHeads(api.routes, [release, release, release, "f" * 40])
    with pytest.raises(RegistryError) as caught:
        scan_authorized_main(
            api, genesis, load_schema(Path("registry/projects.schema.json")),
            expected_policy_commit=release, authorized_project_ids=("alpha",),
        )
    assert caught.value.code == "REGISTRY_HEAD_DRIFT"


def test_every_scan_reaudits_policy_and_main_not_a_reusable_snapshot():
    api, genesis, release = audited_source_api(project(), source_routes())
    schema = load_schema(Path("registry/projects.schema.json"))
    first = scan_authorized_main(
        api, genesis, schema, expected_policy_commit=release, authorized_project_ids=("alpha",),
    )
    assert first["project_reads"][0]["read"] == "VERIFIED"
    initial_calls = len(api.calls)
    api.routes["repos/owner/governance/git/ref/heads/main"] = {"object": {"sha": "f" * 40}}
    with pytest.raises(AssertionError):  # synthetic API lacks an ancestry proof for changed HEAD
        scan_authorized_main(
            api, genesis, schema, expected_policy_commit=release, authorized_project_ids=("alpha",),
        )
    assert len(api.calls) > initial_calls


def test_scanner_does_not_claim_business_authorization():
    api, genesis, release = audited_source_api(project(), source_routes())
    result = scan_authorized_main(
        api, genesis, load_schema(Path("registry/projects.schema.json")),
        expected_policy_commit=release, authorized_project_ids=("alpha",),
    )
    assert result["dispatch_authorized"] is False
    assert result["writer_change_authorized"] is False
    assert result["registry"]["dispatch_authorized"] is False
