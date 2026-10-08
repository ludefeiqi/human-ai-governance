from __future__ import annotations

import copy
import hashlib

import pytest

from registry.validate_registry import (
    RegistryError,
    compare_indexes,
    load_index_bytes,
    normalized_diff,
    validate_post_merge,
    validate_pre_merge,
)
from tests.helpers import SHA_A, SHA_B, SHA_C, FakeApi, active_genesis, index
from tests.test_github_evidence import (
    COMMENTS_ENDPOINT,
    CONTENT_ENDPOINT,
    FILES_ENDPOINT,
    PR_ENDPOINT,
    REPO,
    REVIEWS_ENDPOINT,
    evidence_routes,
)


CI_ID = 9001
AI_ID = 600
OWNER_ID = 601
CI_TIME = "2026-10-08T00:45:00Z"
AI_TIME = "2026-10-08T00:55:00Z"
OWNER_TIME = "2026-10-08T01:02:03Z"
MERGE_TIME = "2026-10-08T02:00:00Z"


@pytest.fixture(scope="module")
def schema():
    from registry.validate_registry import load_schema
    from pathlib import Path
    return load_schema(Path("registry/projects.schema.json"))


def b_fixture(schema):
    routes, _, after_raw = evidence_routes(schema)
    genesis = active_genesis()
    genesis["registry_update_approval_mode"] = "SINGLE_OWNER_AI_R0_ATTESTED"
    routes[PR_ENDPOINT]["draft"] = False
    routes[REVIEWS_ENDPOINT] = []  # B does not claim a second GitHub actor
    common = {
        "candidate_head": SHA_B,
        "previous_index_commit": SHA_A,
        "index_sha256": hashlib.sha256(after_raw).hexdigest(),
        "normalized_diff_sha256": normalized_diff(
            compare_indexes(index(), load_index_bytes(after_raw, schema), SHA_A)
        )[1],
        "changed_ids": "alpha",
    }
    ai_fields = {
        **common,
        "review_scope": "DISCOVERY_METADATA_ONLY",
        "decision": "APPROVE_DESIGN",
        "assurance_level": "OWNER_POSTED_AI_R0_NOT_GITHUB_REVIEW",
        "open_blockers": "0",
        "review_engine": "codex-gpt56-sol",
        "review_session_ref": "codex-session-abc12345",
        "summary": "Independent AI read-only review of discovery metadata: no open blockers.",
        "ci_check_run_id": str(CI_ID),
    }
    def body(marker, data):
        return marker + "\n" + "\n".join(f"{k}={v}" for k, v in data.items())
    ai_body = body(genesis["ai_review_comment_marker"], ai_fields)
    owner_fields = {
        **common,
        "authorized_action": "APPROVE_DISCOVERY_REGISTRY_UPDATE",
        "approval_scope": "GOVERNANCE_REGISTRY_ONLY",
        "approval_profile": "SINGLE_OWNER_AI_R0_ATTESTED",
        "ai_review_comment_id": str(AI_ID),
        "ai_review_comment_sha256": hashlib.sha256(ai_body.encode()).hexdigest(),
        "ci_check_run_id": str(CI_ID),
        "project_authority_effect": "NONE",
    }
    routes[COMMENTS_ENDPOINT] = [
        {"id": AI_ID, "user": {"login": "owner"}, "created_at": AI_TIME, "updated_at": AI_TIME, "body": ai_body},
        {"id": OWNER_ID, "user": {"login": "owner"}, "created_at": OWNER_TIME, "updated_at": OWNER_TIME,
         "body": body(genesis["approval_comment_marker"], owner_fields)},
    ]
    routes[f"repos/{REPO}/check-runs/{CI_ID}"] = {
        "id": CI_ID,
        "name": "validate",
        "head_sha": SHA_B,
        "status": "completed",
        "conclusion": "success",
        "completed_at": CI_TIME,
        "app": {"slug": "github-actions"},
        "pull_requests": [{"number": 5, "head": {"sha": SHA_B}}],
    }
    routes[(
        f"repos/{REPO}/commits/{SHA_B}/check-runs",
        (("filter", "latest"), ("per_page", "100")),
    )] = {
        "total_count": 1,
        "check_runs": [copy.deepcopy(routes[f"repos/{REPO}/check-runs/{CI_ID}"])],
    }
    routes[PR_ENDPOINT]["merged_at"] = None
    return genesis, routes


def b_verified(schema):
    genesis, routes = b_fixture(schema)
    return validate_pre_merge(FakeApi(routes), genesis, schema, 5, SHA_B)


def test_b_exact_binding_pre_merge_passes_without_external_github_review(schema):
    result = b_verified(schema).as_dict()
    assert result["approval_profile"] == "SINGLE_OWNER_AI_R0_ATTESTED"
    assert result["assurance_level"] == "OWNER_POSTED_AI_R0_NOT_INDEPENDENT_GITHUB_REVIEW"
    assert result["independent_reviewer"].startswith("NOT_APPLICABLE_B")
    assert result["source_attribution_is_not_ai_authorship_proof"] is True
    assert result["ai_review_comment_id"] == AI_ID
    assert result["ci_check_run_id"] == CI_ID
    assert result["owner_comment_created_at"] == OWNER_TIME


def test_b_no_tag_holds_even_with_complete_ai_ci_and_owner_receipts(schema):
    genesis, routes = b_fixture(schema)
    genesis["status"] = "CANDIDATE_NOT_RELEASED"
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(FakeApi(routes), genesis, schema, 5, SHA_B)
    assert caught.value.code == "V0_2_UNPUBLISHED"


def test_b_future_merge_parent_not_confused_with_mutable_pr_base(schema):
    genesis, routes = b_fixture(schema)
    routes[PR_ENDPOINT].update({
        "merged": True, "state": "closed", "merged_at": MERGE_TIME,
        "merge_commit_sha": SHA_C, "base": {"sha": SHA_C},
    })
    result = validate_post_merge(FakeApi(routes), genesis, schema, 5, SHA_B, SHA_C)
    assert result.pre.previous_index_commit == SHA_A
    assert result.merge_commit == SHA_C


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda r: r[COMMENTS_ENDPOINT].pop(0), "AI_B_ATTESTATION_MISSING"),
        (lambda r: r[COMMENTS_ENDPOINT].pop(1), "AI_B_OWNER_APPROVAL_MISSING"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"updated_at": OWNER_TIME}), "AI_B_COMMENT_EDITED"),
        (lambda r: r[COMMENTS_ENDPOINT][1].update({"updated_at": MERGE_TIME}), "AI_B_COMMENT_EDITED"),
        (lambda r: r[COMMENTS_ENDPOINT][0]["user"].update({"login": "other"}), "AI_B_ATTESTATION_MISSING"),
        (lambda r: r[COMMENTS_ENDPOINT][1]["user"].update({"login": "other"}), "AI_B_OWNER_APPROVAL_MISSING"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"id": -1}), "AI_B_COMMENT_ID_INVALID"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"created_at": "bad"}), "AI_B_COMMENT_TIME_INVALID"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"body": r[COMMENTS_ENDPOINT][0]["body"].replace("APPROVE_DESIGN", "REQUEST_CHANGES")}), "AI_B_ATTESTATION_MISMATCH"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"body": r[COMMENTS_ENDPOINT][0]["body"].replace("open_blockers=0", "open_blockers=1")}), "AI_B_ATTESTATION_MISMATCH"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"body": r[COMMENTS_ENDPOINT][0]["body"].replace("review_scope=DISCOVERY_METADATA_ONLY", "review_scope=R3")}), "AI_B_ATTESTATION_MISMATCH"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"body": r[COMMENTS_ENDPOINT][0]["body"]+"\nadmin_grant=true"}), "AI_B_ATTESTATION_FIELDS_INVALID"),
        (lambda r: r[COMMENTS_ENDPOINT][1].update({"body": r[COMMENTS_ENDPOINT][1]["body"].replace("project_authority_effect=NONE", "project_authority_effect=WRITER")}), "AI_B_OWNER_APPROVAL_MISMATCH"),
        (lambda r: r[COMMENTS_ENDPOINT][1].update({"body": r[COMMENTS_ENDPOINT][1]["body"].replace(f"ai_review_comment_id={AI_ID}", "ai_review_comment_id=123")}), "AI_B_OWNER_APPROVAL_MISMATCH"),
        (lambda r: r[f"repos/{REPO}/check-runs/{CI_ID}"].update({"status": "in_progress"}), "AI_B_CI_NOT_VERIFIED"),
        (lambda r: r[f"repos/{REPO}/check-runs/{CI_ID}"].update({"conclusion": "failure"}), "AI_B_CI_NOT_VERIFIED"),
        (lambda r: r[f"repos/{REPO}/check-runs/{CI_ID}"].update({"head_sha": SHA_A}), "AI_B_CI_NOT_VERIFIED"),
        (lambda r: r[f"repos/{REPO}/check-runs/{CI_ID}"]["app"].update({"slug": "unknown-ci"}), "AI_B_CI_NOT_VERIFIED"),
        (lambda r: r[f"repos/{REPO}/check-runs/{CI_ID}"].update({"pull_requests": []}), "AI_B_CI_NOT_VERIFIED"),
        (lambda r: r[f"repos/{REPO}/check-runs/{CI_ID}"].update({"completed_at": OWNER_TIME}), "AI_B_ORDER_INVALID"),
        (lambda r: r[COMMENTS_ENDPOINT][0].update({"created_at": "2026-10-08T01:10:00Z", "updated_at": "2026-10-08T01:10:00Z"}), "AI_B_ORDER_INVALID"),
        (lambda r: r[FILES_ENDPOINT][0].update({"status": "renamed", "previous_filename": "bad.yml"}), "PR_FILES_FORBIDDEN"),
        (lambda r: r[PR_ENDPOINT]["head"].update({"sha": SHA_C}), "CANDIDATE_HEAD_MISMATCH"),
        (lambda r: r[PR_ENDPOINT].update({"draft": True}), "AI_B_PR_DRAFT"),
    ],
)
def test_b_fail_closed_on_missing_stale_edit_fraud_or_escalation(schema, mutation, reason):
    genesis, routes = b_fixture(schema)
    mutation(routes)
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(FakeApi(routes), genesis, schema, 5, SHA_B)
    assert caught.value.code == reason


def test_b_newest_ai_report_invalidates_older_valid_report(schema):
    genesis, routes = b_fixture(schema)
    older = copy.deepcopy(routes[COMMENTS_ENDPOINT][0])
    older["id"] = AI_ID + 1
    older["created_at"] = older["updated_at"] = "2026-10-08T01:00:00Z"
    older["body"] = older["body"].replace("open_blockers=0", "open_blockers=2")
    routes[COMMENTS_ENDPOINT].append(older)
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(FakeApi(routes), genesis, schema, 5, SHA_B)
    assert caught.value.code == "AI_B_ATTESTATION_MISMATCH"


def test_b_post_merge_approval_cannot_be_backfilled(schema):
    genesis, routes = b_fixture(schema)
    routes[PR_ENDPOINT].update({"merged": True, "state": "closed", "merged_at": OWNER_TIME, "merge_commit_sha": SHA_C})
    with pytest.raises(RegistryError) as caught:
        validate_post_merge(FakeApi(routes), genesis, schema, 5, SHA_B, SHA_C)
    assert caught.value.code == "OWNER_APPROVAL_AFTER_MERGE"


def test_a_explicit_mode_not_implicitly_changed_to_b_by_receipts(schema):
    _, routes = b_fixture(schema)
    genesis = active_genesis()
    assert genesis["registry_update_approval_mode"] == "EXTERNAL_GITHUB_REVIEW"
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(FakeApi(routes), genesis, schema, 5, SHA_B)
    assert caught.value.code == "INDEPENDENT_APPROVAL_MISSING"


def test_b_reviewer_readiness_never_announces_grant_or_automatic_downgrade():
    from registry.validate_registry import reviewer_readiness
    genesis = active_genesis()
    genesis["registry_update_approval_mode"] = "SINGLE_OWNER_AI_R0_ATTESTED"
    result = reviewer_readiness(FakeApi({
        f"repos/{REPO}/collaborators": [{"login": "owner", "permissions": {"admin": True}}]
    }), genesis)
    assert result["registry_approval_mode"] == "SINGLE_OWNER_AI_R0_ATTESTED"
    assert result["status"] == "HOLD"
    assert result["b_evidence_approved"] is False
    assert result["fallback_approved"] is False
    assert result["authorization_effect"] == "NONE"


def test_b_genesis_approval_mode_must_be_pinned_and_validated():
    from registry.validate_registry import load_genesis
    from pathlib import Path
    import json
    production = load_genesis(Path("registry/GENESIS.json"))
    assert production["registry_update_approval_mode"] == "SINGLE_OWNER_AI_R0_ATTESTED"
    assert production["ai_review_comment_marker"] == "HAGOV-AI-R0-ATTESTATION-V1"


def test_b_old_success_cannot_override_newer_failing_check(schema):
    genesis, routes = b_fixture(schema)
    key = (f"repos/{REPO}/commits/{SHA_B}/check-runs", (("filter", "latest"), ("per_page", "100")))
    routes[key]["check_runs"][0]["id"] = CI_ID + 42
    routes[key]["check_runs"][0]["conclusion"] = "failure"
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(FakeApi(routes), genesis, schema, 5, SHA_B)
    assert caught.value.code == "AI_B_CI_STALE"


def test_b_missing_latest_check_list_holds(schema):
    genesis, routes = b_fixture(schema)
    key = (f"repos/{REPO}/commits/{SHA_B}/check-runs", (("filter", "latest"), ("per_page", "100")))
    routes[key] = {"total_count": 1000, "check_runs": []}
    with pytest.raises(RegistryError) as caught:
        validate_pre_merge(FakeApi(routes), genesis, schema, 5, SHA_B)
    assert caught.value.code == "AI_B_CI_LATEST_UNAVAILABLE"
