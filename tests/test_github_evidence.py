from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from types import SimpleNamespace

import pytest

from registry.validate_registry import (
    GhApi,
    RegistryError,
    audit_first_parent_chain,
    audit_main_snapshot,
    compare_indexes,
    load_index_bytes,
    normalized_diff,
    resolve_release_commit,
    reviewer_readiness,
    validate_post_merge,
    validate_pre_merge,
)
from tests.helpers import SHA_A, SHA_B, SHA_C, SHA_D, FakeApi, active_genesis, content, dump, index, mock_released_policy_routes


REPO = "owner/governance"
PR_ENDPOINT = f"repos/{REPO}/pulls/5"
FILES_ENDPOINT = f"repos/{REPO}/pulls/5/files"
REVIEWS_ENDPOINT = f"repos/{REPO}/pulls/5/reviews"
COMMENTS_ENDPOINT = f"repos/{REPO}/issues/5/comments"
CONTENT_ENDPOINT = f"repos/{REPO}/contents/projects.yaml"


@pytest.fixture(scope="module")
def schema():
    from pathlib import Path

    from registry.validate_registry import load_schema

    return load_schema(Path("registry/projects.schema.json"))


def evidence_routes(schema):
    before = index()
    after = copy.deepcopy(before)
    after["projects"]["alpha"]["notes"] = "Reviewed change."
    before_raw = dump(before)
    after_raw = dump(after)
    changes = compare_indexes(before, after, SHA_A)
    diff_sha = normalized_diff(changes)[1]
    index_sha = hashlib.sha256(after_raw).hexdigest()
    created = "2026-10-08T01:02:03Z"
    comment = "\n".join(
        [
            "HAGOV-REGISTRY-OWNER-APPROVAL-V1",
            f"candidate_head={SHA_B}",
            f"previous_index_commit={SHA_A}",
            f"index_sha256={index_sha}",
            f"normalized_diff_sha256={diff_sha}",
            "changed_ids=alpha",
            "authorized_action=APPROVE_DISCOVERY_REGISTRY_UPDATE",
            "approval_scope=GOVERNANCE_REGISTRY_ONLY",
        ]
    )
    routes = {
        f"repos/{REPO}/git/ref/tags/v0.2.0": {"object": {"type": "tag", "sha": SHA_D}},
        f"repos/{REPO}/git/tags/{SHA_D}": {"object": {"type": "commit", "sha": "e" * 40}},
        PR_ENDPOINT: {
            "number": 5,
            "state": "open",
            "merged": False,
            "merge_commit_sha": None,
            "head": {"sha": SHA_B},
            "base": {"sha": SHA_A},
            "user": {"login": "author"},
        },
        FILES_ENDPOINT: [{"filename": "projects.yaml", "status": "modified"}],
        (CONTENT_ENDPOINT, (("ref", SHA_A),)): content(before_raw),
        (CONTENT_ENDPOINT, (("ref", SHA_B),)): content(after_raw),
        (CONTENT_ENDPOINT, (("ref", SHA_C),)): content(after_raw),
        REVIEWS_ENDPOINT: [
            {
                "user": {"login": "reviewer"},
                "state": "APPROVED",
                "commit_id": SHA_B,
                "submitted_at": "2026-10-08T00:30:00Z",
            }
        ],
        COMMENTS_ENDPOINT: [{"id": 4242, "user": {"login": "owner"}, "created_at": created, "updated_at": created, "body": comment}],
        f"repos/{REPO}/commits/{SHA_C}": {"sha": SHA_C, "parents": [{"sha": SHA_A}]},
    }
    mock_released_policy_routes(routes, REPO, "e" * 40, active_genesis())
    return routes, before_raw, after_raw


def assert_hold(schema, mutate, code):
    routes, _, _ = evidence_routes(schema)
    genesis = active_genesis()
    mutate(routes, genesis)
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(FakeApi(routes), genesis, schema, 5, SHA_B, expected_policy_commit='e'*40)
    assert caught.value.code == code


def test_pre_merge_exact_evidence_passes(schema):
    routes, _, _ = evidence_routes(schema)
    evidence = validate_pre_merge(FakeApi(routes), active_genesis(), schema, 5, SHA_B, expected_policy_commit='e'*40)
    result = evidence.as_dict()
    assert result["changed_ids"] == ["alpha"]
    assert result["independent_reviewer"] == "reviewer"
    assert result["independent_review_submitted_at"] == "2026-10-08T00:30:00Z"
    assert result["owner_comment_created_at"] == "2026-10-08T01:02:03Z"
    assert result["owner_comment_id"] == 4242
    assert result["approval_authentication"] == "GITHUB_ACCOUNT_ATTRIBUTION_ONLY_NOT_PASSWORD_SIGNATURE"


def test_unpublished_genesis_holds_before_any_pr_read(schema):
    routes, _, _ = evidence_routes(schema)
    genesis = active_genesis()
    genesis["status"] = "CANDIDATE_NOT_RELEASED"
    api = FakeApi(routes)
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(api, genesis, schema, 5, SHA_B, expected_policy_commit='e'*40)
    assert caught.value.code == "V0_2_UNPUBLISHED"
    assert not any(endpoint == PR_ENDPOINT for endpoint, _ in api.calls)


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda r, g: r[PR_ENDPOINT]["head"].update({"sha": SHA_C}), "CANDIDATE_HEAD_MISMATCH"),
        (lambda r, g: r[PR_ENDPOINT]["base"].update({"sha": "bad"}), "PR_BASE_INVALID"),
        (lambda r, g: r[FILES_ENDPOINT].append({"filename": "README.md", "status": "modified"}), "PR_FILES_FORBIDDEN"),
        (lambda r, g: r[FILES_ENDPOINT][0].update({"status": "removed"}), "PR_FILES_FORBIDDEN"),
        (lambda r, g: r[FILES_ENDPOINT][0].update({"status": "renamed", "previous_filename": "UNTRUSTED.md"}), "PR_FILES_FORBIDDEN"),
        (lambda r, g: r[FILES_ENDPOINT][0].update({"previous_filename": "README.md"}), "PR_FILES_FORBIDDEN"),
        (lambda r, g: r[FILES_ENDPOINT][0].update({"status": "added"}), "PR_FILES_FORBIDDEN"),
        (lambda r, g: r[FILES_ENDPOINT][0].update({"status": "copied"}), "PR_FILES_FORBIDDEN"),
        (lambda r, g: r.update({REVIEWS_ENDPOINT: []}), "INDEPENDENT_APPROVAL_MISSING"),
        (lambda r, g: r[REVIEWS_ENDPOINT][0].update({"commit_id": SHA_A}), "INDEPENDENT_APPROVAL_MISSING"),
        (lambda r, g: r[REVIEWS_ENDPOINT][0]["user"].update({"login": "author"}), "INDEPENDENT_APPROVAL_MISSING"),
        (lambda r, g: r[REVIEWS_ENDPOINT][0]["user"].update({"login": "owner"}), "INDEPENDENT_APPROVAL_MISSING"),
        (lambda r, g: r[REVIEWS_ENDPOINT][0].update({"state": "CHANGES_REQUESTED"}), "INDEPENDENT_APPROVAL_MISSING"),
        (lambda r, g: r[COMMENTS_ENDPOINT][0]["user"].update({"login": "someone"}), "OWNER_APPROVAL_MISSING"),
        (lambda r, g: r[COMMENTS_ENDPOINT][0].update({"created_at": "not-time"}), "OWNER_APPROVAL_TIME_INVALID"),
        (lambda r, g: r[COMMENTS_ENDPOINT][0].update({"body": "wrong"}), "OWNER_APPROVAL_MISSING"),
        (lambda r, g: r[COMMENTS_ENDPOINT][0].update({"body": r[COMMENTS_ENDPOINT][0]["body"].replace("changed_ids=alpha", "changed_ids=beta")}), "OWNER_APPROVAL_MISMATCH"),
        (lambda r, g: r[f"repos/{REPO}/git/ref/tags/v0.2.0"]["object"].update({"type": "commit"}), "RELEASE_TAG_NOT_ANNOTATED"),
        (lambda r, g: r[f"repos/{REPO}/git/tags/{SHA_D}"]["object"].update({"type": "tree"}), "RELEASE_TAG_TARGET_INVALID"),
    ],
)
def test_pre_merge_fail_closed(schema, mutate, code):
    assert_hold(schema, mutate, code)


def test_latest_review_state_controls(schema):
    routes, _, _ = evidence_routes(schema)
    routes[REVIEWS_ENDPOINT].append(
        {
            "user": {"login": "reviewer"},
            "state": "CHANGES_REQUESTED",
            "commit_id": SHA_B,
            "submitted_at": "2026-10-08T00:40:00Z",
        }
    )
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(FakeApi(routes), active_genesis(), schema, 5, SHA_B, expected_policy_commit='e'*40)
    assert caught.value.code == "INDEPENDENT_APPROVAL_MISSING"


def test_empty_semantic_diff_is_rejected(schema):
    routes, before_raw, _ = evidence_routes(schema)
    routes[(CONTENT_ENDPOINT, (("ref", SHA_B),))] = content(before_raw)
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(FakeApi(routes), active_genesis(), schema, 5, SHA_B, expected_policy_commit='e'*40)
    assert caught.value.code == "INDEX_DIFF_EMPTY"


def post_routes(schema):
    routes, _, _ = evidence_routes(schema)
    routes[PR_ENDPOINT].update({"state": "closed", "merged": True, "merge_commit_sha": SHA_C, "merged_at": "2026-10-08T02:00:00Z"})
    return routes


def test_post_merge_binds_actual_merge_and_first_parent(schema):
    evidence = validate_post_merge(FakeApi(post_routes(schema)), active_genesis(), schema, 5, SHA_B, SHA_C, expected_policy_commit='e'*40)
    assert evidence.merge_commit == SHA_C
    assert evidence.first_parent == SHA_A


def change_first_parent_with_another_real_looking_commit(routes):
    # The changed first parent must itself be retrievable as a Git commit,
    # then the historical owner approval must reject the different base.
    routes[(CONTENT_ENDPOINT, (("ref", SHA_D),))] = copy.deepcopy(
        routes[(CONTENT_ENDPOINT, (("ref", SHA_A),))]
    )
    routes[f"repos/{REPO}/commits/{SHA_C}"]["parents"][0]["sha"] = SHA_D


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda r: r[PR_ENDPOINT].update({"merged": False}), "MERGE_COMMIT_MISMATCH"),
        (lambda r: r[PR_ENDPOINT].update({"merge_commit_sha": SHA_D}), "MERGE_COMMIT_MISMATCH"),
        (change_first_parent_with_another_real_looking_commit, "OWNER_APPROVAL_MISMATCH"),
        (lambda r: r.update({(CONTENT_ENDPOINT, (("ref", SHA_C),)): content(b"different")}), "MERGED_INDEX_MISMATCH"),
    ],
)
def test_post_merge_fail_closed(schema, mutate, code):
    routes = post_routes(schema)
    mutate(routes)
    with pytest.raises(RegistryError) as caught:
        validate_post_merge(FakeApi(routes), active_genesis(), schema, 5, SHA_B, SHA_C, expected_policy_commit='e'*40)
    assert caught.value.code == code


def test_chain_accepts_only_exact_release_genesis(schema):
    raw = dump(index())
    genesis = active_genesis()
    genesis["initial_index_sha256"] = hashlib.sha256(raw).hexdigest()
    genesis["initial_project_identity_hashes"] = {
        "alpha": index()["projects"]["alpha"]["identity"]["identity_hash"]
    }
    release = "e" * 40
    routes, _, _ = evidence_routes(schema)
    routes[(CONTENT_ENDPOINT, (("ref", release),))] = content(raw)
    mock_released_policy_routes(routes, REPO, release, genesis)
    result = audit_first_parent_chain(FakeApi(routes), genesis, schema, release, expected_policy_commit=release)
    assert result["genesis_commit"] == release
    assert result["commits_traversed"] == 0


def test_chain_holds_if_genesis_not_first_parent_ancestor(schema):
    genesis = active_genesis()
    routes, _, _ = evidence_routes(schema)
    routes[f"repos/{REPO}/commits/{SHA_C}"] = {"sha": SHA_C, "parents": []}
    with pytest.raises(RegistryError) as caught:
        audit_first_parent_chain(FakeApi(routes), genesis, schema, SHA_C, expected_policy_commit='e'*40)
    assert caught.value.code == "GENESIS_NOT_ANCESTOR"


def test_gh_client_constructs_get_only(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0, stdout=json.dumps({"ok": True}), stderr="")

    monkeypatch.setattr("registry.validate_registry.subprocess.run", fake_run)
    assert GhApi().get("repos/owner/repo", {"page": "1"}) == {"ok": True}
    assert captured["command"][:4] == ["gh", "api", "--method", "GET"]
    assert all(word not in captured["command"] for word in ["POST", "PUT", "PATCH", "DELETE"])


def test_gh_client_holds_on_nonzero(monkeypatch):
    monkeypatch.setattr(
        "registry.validate_registry.subprocess.run",
        lambda *a, **k: SimpleNamespace(returncode=4, stdout="", stderr="auth"),
    )
    with pytest.raises(RegistryError) as caught:
        GhApi().get("repos/owner/repo")
    assert caught.value.code == "GITHUB_GET_FAILED"


def test_gh_client_holds_on_timeout(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 30)

    monkeypatch.setattr("registry.validate_registry.subprocess.run", timeout)
    with pytest.raises(RegistryError) as caught:
        GhApi().get("repos/owner/repo")
    assert caught.value.code == "GITHUB_GET_TIMEOUT"


def test_resolve_release_rejects_candidate_without_api_calls():
    genesis = active_genesis()
    genesis["status"] = "CANDIDATE_NOT_RELEASED"
    api = FakeApi({})
    with pytest.raises(RegistryError) as caught:
        resolve_release_commit(api, genesis)
    assert caught.value.code == "V0_2_UNPUBLISHED"
    assert api.calls == []


class SequencedHeadApi(FakeApi):
    def __init__(self, routes, heads):
        super().__init__(routes)
        self.heads = iter(heads)

    def get(self, endpoint, fields=None):
        if endpoint == f"repos/{REPO}/git/ref/heads/main":
            self.calls.append((endpoint, tuple()))
            return {"object": {"sha": next(self.heads)}}
        return super().get(endpoint, fields)


def snapshot_fixture(schema):
    raw = dump(index())
    genesis = active_genesis()
    genesis["initial_index_sha256"] = hashlib.sha256(raw).hexdigest()
    genesis["initial_project_identity_hashes"] = {
        "alpha": index()["projects"]["alpha"]["identity"]["identity_hash"]
    }
    routes, _, _ = evidence_routes(schema)
    release = "e" * 40
    routes[(CONTENT_ENDPOINT, (("ref", release),))] = content(raw)
    routes[(f"repos/{REPO}/contents/registry/GENESIS.json", (("ref", release),))] = content(
        json.dumps(genesis).encode("utf-8")
    )
    mock_released_policy_routes(routes, REPO, release, genesis)
    return genesis, routes, release


def test_main_snapshot_is_stable_on_first_attempt(schema):
    genesis, routes, release = snapshot_fixture(schema)
    result = audit_main_snapshot(SequencedHeadApi(routes, [release, release]), genesis, schema, expected_policy_commit=release)
    assert result["attempts"] == 1
    assert result["head"] == release


def test_main_snapshot_retries_once_on_drift(schema):
    genesis, routes, release = snapshot_fixture(schema)
    result = audit_main_snapshot(SequencedHeadApi(routes, [release, SHA_C, release, release]), genesis, schema, expected_policy_commit=release)
    assert result["attempts"] == 2
    assert result["head_observations"][0] == {"start": release, "end": SHA_C}


def test_main_snapshot_holds_after_second_drift(schema):
    genesis, routes, release = snapshot_fixture(schema)
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(SequencedHeadApi(routes, [release, SHA_C, release, SHA_C]), genesis, schema, expected_policy_commit=release)
    assert caught.value.code == "REGISTRY_HEAD_DRIFT"


def test_owner_approval_never_pre_fills_github_created_at(schema):
    routes, _, _ = evidence_routes(schema)
    body = routes[COMMENTS_ENDPOINT][0]["body"]
    assert "approved_at_utc" not in body
    assert "authorized_action=APPROVE_DISCOVERY_REGISTRY_UPDATE" in body
    result = validate_pre_merge(FakeApi(routes), active_genesis(), schema, 5, SHA_B, expected_policy_commit='e'*40)
    assert result.owner_comment_created_at == routes[COMMENTS_ENDPOINT][0]["created_at"]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"updated_at": "2026-10-08T01:03:00Z"}), "OWNER_APPROVAL_EDITED"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"updated_at": "invalid"}), "OWNER_APPROVAL_TIME_INVALID"),
        (lambda r: r[COMMENTS_ENDPOINT][0].pop("updated_at"), "OWNER_APPROVAL_TIME_INVALID"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"id": None}), "OWNER_APPROVAL_ID_INVALID"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"created_at": "2026-10-08T00:01:00Z", "updated_at": "2026-10-08T00:01:00Z"}), "REVIEW_AFTER_OWNER_APPROVAL"),
        (lambda r: r[REVIEWS_ENDPOINT][0].update({"submitted_at": "2026-10-08T01:03:00Z"}), "REVIEW_AFTER_OWNER_APPROVAL"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"body": r[COMMENTS_ENDPOINT][0]["body"]+"\\napproved_at_utc=2026-10-08T01:02:03Z"}), "OWNER_APPROVAL_MISMATCH"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"body": r[COMMENTS_ENDPOINT][0]["body"].replace("approval_scope=GOVERNANCE_REGISTRY_ONLY", "approval_scope=BUSINESS_R3")}), "OWNER_APPROVAL_MISMATCH"),
    ],
)
def test_owner_comment_chronology_and_integrity(schema, mutate, expected):
    routes, _, _ = evidence_routes(schema)
    mutate(routes)
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(FakeApi(routes), active_genesis(), schema, 5, SHA_B, expected_policy_commit='e'*40)
    assert caught.value.code == expected


@pytest.mark.parametrize(
    ("merged_at", "expected"),
    [
        ("2026-10-08T00:59:00Z", "OWNER_APPROVAL_MISSING"),
        ("2026-10-08T01:02:03Z", "OWNER_APPROVAL_MISSING"),
        ("bad", "TIME_INVALID"),
    ],
)
def test_post_merge_requires_prior_owner_approval(schema, merged_at, expected):
    routes = post_routes(schema)
    routes[PR_ENDPOINT]["merged_at"] = merged_at
    with pytest.raises(RegistryError) as caught:
        validate_post_merge(FakeApi(routes), active_genesis(), schema, 5, SHA_B, SHA_C, expected_policy_commit='e'*40)
    assert caught.value.code == expected


def test_latest_owner_decision_invalidates_earlier_valid_approval(schema):
    routes, _, _ = evidence_routes(schema)
    later = copy.deepcopy(routes[COMMENTS_ENDPOINT][0])
    later["id"] = 4243
    later["created_at"] = later["updated_at"] = "2026-10-08T01:04:00Z"
    later["body"] = later["body"].replace("changed_ids=alpha", "changed_ids=beta")
    routes[COMMENTS_ENDPOINT].append(later)
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(FakeApi(routes), active_genesis(), schema, 5, SHA_B, expected_policy_commit='e'*40)
    assert caught.value.code == "OWNER_APPROVAL_MISMATCH"

def test_main_snapshot_requires_external_policy_commit_pin(schema):
    genesis, routes, release = snapshot_fixture(schema)
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(SequencedHeadApi(routes, []), genesis, schema)
    assert caught.value.code == "POLICY_PIN_REQUIRED"


def test_main_snapshot_rejects_tag_target_different_from_pinned_policy(schema):
    genesis, routes, release = snapshot_fixture(schema)
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(
            SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit="f" * 40
        )
    assert caught.value.code == "POLICY_PIN_MISMATCH"


def test_main_snapshot_rejects_genesis_not_present_at_immutable_release_commit(schema):
    genesis, routes, release = snapshot_fixture(schema)
    endpoint = (f"repos/{REPO}/contents/registry/GENESIS.json", (("ref", release),))
    tampered = copy.deepcopy(genesis)
    tampered["immutable_owner_account"] = "attacker"
    routes[endpoint] = content(json.dumps(tampered).encode())
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(
            SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit=release
        )
    assert caught.value.code == "RELEASE_FILE_HASH_MISMATCH"


def test_audit_main_returns_evidence_not_reusable_scan_capability(schema):
    genesis, routes, release = snapshot_fixture(schema)
    result = audit_main_snapshot(
        SequencedHeadApi(routes, [release, release]), genesis, schema,
        expected_policy_commit=release,
    )
    assert isinstance(result, dict)
    assert result["head"] == release
    assert result["policy_commit"] == release
    assert result["registry"]["projects"][0]["project_id"] == "alpha"
    assert not hasattr(result, "project_entry")


def test_reviewer_readiness_holds_for_single_owner_account():
    genesis = active_genesis()
    endpoint = f"repos/{REPO}/collaborators"
    api = FakeApi({endpoint: [{"login": "owner", "permissions": {"admin": True}}]})
    result = reviewer_readiness(api, genesis)
    assert result["status"] == "HOLD"
    assert result["reason"] == "INDEPENDENT_GITHUB_REVIEWER_UNAVAILABLE"
    assert result["eligible_other_github_reviewers"] == []
    assert result["fallback_approved"] is False


def test_reviewer_readiness_does_not_treat_same_owner_ai_as_separate_reviewer():
    genesis = active_genesis()
    endpoint = f"repos/{REPO}/collaborators"
    data = [
        {"login": "owner", "permissions": {"admin": True}},
        {"login": "observer", "permissions": {"pull": True, "push": False}},
        {"login": "reviewer", "permissions": {"push": True}},
    ]
    result = reviewer_readiness(FakeApi({endpoint: data}), genesis)
    assert result["status"] == "CANDIDATES_PRESENT_NOT_APPROVED"
    assert result["eligible_other_github_reviewers"] == ["reviewer"]
    assert result["authorization_effect"] == "NONE"


def test_remote_policy_manifest_validator_sha_mismatch_holds(schema):
    genesis, routes, release = snapshot_fixture(schema)
    endpoint = (f"repos/{REPO}/contents/registry/validate_registry.py", (("ref", release),))
    routes[endpoint] = content(b"tampered Python code")
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(
            SequencedHeadApi(routes, []), genesis, schema,
            expected_policy_commit=release
        )
    assert caught.value.code == "RELEASE_FILE_HASH_MISMATCH"


def test_remote_policy_genesis_different_but_matching_manifest_still_holds(schema):
    genesis, routes, release = snapshot_fixture(schema)
    key = (f"repos/{REPO}/contents/registry/GENESIS.json", (("ref", release),))
    changed = copy.deepcopy(genesis)
    changed["immutable_owner_account"] = "attacker"
    raw = json.dumps(changed).encode()
    routes[key] = content(raw)
    manifest_key = (f"repos/{REPO}/contents/MANIFEST.sha256", (("ref", release),))
    old_manifest = __import__("base64").b64decode(routes[manifest_key]["content"]).decode()
    old_entry = hashlib.sha256(json.dumps(genesis).encode()).hexdigest()
    routes[manifest_key] = content(old_manifest.replace(old_entry, hashlib.sha256(raw).hexdigest()).encode())
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit=release)
    assert caught.value.code == "GENESIS_POLICY_MISMATCH"


def _manifest_bytes(routes, release):
    import base64
    key = (f"repos/{REPO}/contents/MANIFEST.sha256", (("ref", release),))
    return base64.b64decode(routes[key]["content"])


def test_remote_manifest_all_nineteen_paths_are_fetched(schema):
    genesis, routes, release = snapshot_fixture(schema)
    api = SequencedHeadApi(routes, [release, release])
    audit_main_snapshot(api, genesis, schema, expected_policy_commit=release)
    refs = [
        endpoint for endpoint, fields in api.calls
        if endpoint.startswith(f"repos/{REPO}/contents/") and fields == (("ref", release),)
    ]
    fixed = [x for x in refs if not x.endswith("/projects.yaml")]
    from registry.validate_registry import RELEASE_POLICY_FILESET
    assert len(set(fixed)) == len(RELEASE_POLICY_FILESET) + 1  # all policy files plus manifest
    assert f"repos/{REPO}/contents/README.md" in fixed
    assert f"repos/{REPO}/contents/tests/test_strict_reader.py" in fixed


@pytest.mark.parametrize("deleted_path", ["README.md", "tests/test_strict_reader.py", "AGENTS.md"])
def test_remote_release_manifest_incomplete_is_rejected(schema, deleted_path):
    genesis, routes, release = snapshot_fixture(schema)
    key = (f"repos/{REPO}/contents/MANIFEST.sha256", (("ref", release),))
    lines = _manifest_bytes(routes, release).decode().splitlines()
    without = "\n".join(line for line in lines if not line.endswith("  " + deleted_path)) + "\n"
    routes[key] = content(without.encode())
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit=release)
    assert caught.value.code == "RELEASE_MANIFEST_FILESET_MISMATCH"


def test_remote_release_manifest_extra_file_is_rejected(schema):
    genesis, routes, release = snapshot_fixture(schema)
    key = (f"repos/{REPO}/contents/MANIFEST.sha256", (("ref", release),))
    malicious = _manifest_bytes(routes, release) + (("0" * 64) + "  unreviewed.py\n").encode()
    routes[key] = content(malicious)
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit=release)
    assert caught.value.code == "RELEASE_MANIFEST_FILESET_MISMATCH"


@pytest.mark.parametrize("path", ["README.md", "tests/test_strict_reader.py", "AGENTS.md"])
def test_remote_noncritical_policy_file_hash_mismatch_is_rejected(schema, path):
    genesis, routes, release = snapshot_fixture(schema)
    key = (f"repos/{REPO}/contents/{path}", (("ref", release),))
    routes[key] = content(b"REPLACED_WITH_UNREVIEWED_BYTES")
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit=release)
    assert caught.value.code == "RELEASE_FILE_HASH_MISMATCH"


def test_remote_release_manifest_with_only_three_key_files_is_rejected(schema):
    genesis, routes, release = snapshot_fixture(schema)
    key = (f"repos/{REPO}/contents/MANIFEST.sha256", (("ref", release),))
    allowed = {"registry/GENESIS.json", "registry/validate_registry.py", "registry/projects.schema.json"}
    incomplete = "\n".join(
        line for line in _manifest_bytes(routes, release).decode().splitlines()
        if line.split("  ", 1)[-1] in allowed
    ) + "\n"
    routes[key] = content(incomplete.encode())
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit=release)
    assert caught.value.code == "RELEASE_MANIFEST_FILESET_MISMATCH"


RELEASE_TREE_KEY = (
    f"repos/{REPO}/git/trees/{'9' * 40}", (("recursive", "1"),),
)


@pytest.mark.parametrize(
    ("path", "mode", "kind"),
    [
        ("registry/capabilities/tool.route.json", "100755", "blob"),
        ("registry/capabilities/project.restore.json", "120000", "blob"),
        ("registry/capabilities/codex.observe.json", "160000", "commit"),
        ("registry/capabilities/capability-card.schema.json", "100755", "blob"),
        ("registry/validate_capabilities.py", "120000", "blob"),
        ("MANIFEST.sha256", "100755", "blob"),
    ],
)
def test_remote_release_git_tree_rejects_unsafe_mode(schema, path, mode, kind):
    genesis, routes, release = snapshot_fixture(schema)
    target = next(x for x in routes[RELEASE_TREE_KEY]["tree"] if x["path"] == path)
    target.update({"mode": mode, "type": kind})
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(
            SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit=release,
        )
    assert caught.value.code == "RELEASE_POLICY_MODE_INVALID"


def test_remote_release_git_tree_must_be_complete(schema):
    genesis, routes, release = snapshot_fixture(schema)
    routes[RELEASE_TREE_KEY]["truncated"] = True
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit=release)
    assert caught.value.code == "RELEASE_POLICY_TREE_INVALID"


def test_remote_release_git_tree_missing_required_policy_fails_closed(schema):
    genesis, routes, release = snapshot_fixture(schema)
    path = "registry/capabilities/tool.route.json"
    routes[RELEASE_TREE_KEY]["tree"] = [
        x for x in routes[RELEASE_TREE_KEY]["tree"] if x["path"] != path
    ]
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit=release)
    assert caught.value.code == "RELEASE_POLICY_MODE_INVALID"
    assert path in caught.value.details["missing"]


def test_remote_release_git_tree_duplicate_policy_path_fails_closed(schema):
    genesis, routes, release = snapshot_fixture(schema)
    routes[RELEASE_TREE_KEY]["tree"].append(copy.deepcopy(routes[RELEASE_TREE_KEY]["tree"][0]))
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit=release)
    assert caught.value.code == "RELEASE_POLICY_MODE_INVALID"


def test_remote_release_git_tree_commit_must_equal_external_pin(schema):
    genesis, routes, release = snapshot_fixture(schema)
    routes[f"repos/{REPO}/commits/{release}"]["sha"] = "f" * 40
    with pytest.raises(RegistryError) as caught:
        audit_main_snapshot(SequencedHeadApi(routes, []), genesis, schema, expected_policy_commit=release)
    assert caught.value.code == "RELEASE_POLICY_TREE_INVALID"


def test_valid_release_checks_git_modes_for_all_policy_files(schema):
    genesis, routes, release = snapshot_fixture(schema)
    api = SequencedHeadApi(routes, [release, release])
    audit_main_snapshot(api, genesis, schema, expected_policy_commit=release)
    assert (RELEASE_TREE_KEY[0], RELEASE_TREE_KEY[1]) in api.calls
    from registry.validate_registry import RELEASE_POLICY_FILESET
    paths = {x["path"] for x in routes[RELEASE_TREE_KEY]["tree"]}
    assert paths == RELEASE_POLICY_FILESET | {"MANIFEST.sha256"}
