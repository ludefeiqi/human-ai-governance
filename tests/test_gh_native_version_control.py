"""Source-level GitHub hardening contract. Not a platform protection attestation."""

import json
import re
from pathlib import Path

import yaml

ROOT=Path(__file__).resolve().parents[1]


def workflow():
    # YAML 1.1 SafeLoader maps "on" to True; BaseLoader keeps the literal key.
    return yaml.load(
        (ROOT/".github/workflows/registry-validate.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


def test_candidate_v022_is_never_implicitly_adopted():
    g=json.loads((ROOT/"registry/GENESIS.json").read_text())
    assert g["release_tag"]=="v0.2.2"
    assert g["unreleased_behavior"]=="HOLD_V0_2_1_SEMANTICS"
    assert g["status"]=="ACTIVATES_ONLY_AFTER_VERIFIED_RELEASE_TAG"


def test_required_pr_check_is_not_filtered_and_publication_triggers_are_read_only():
    w=workflow()
    assert set(w["on"])=={"pull_request","push","release","workflow_dispatch"}
    assert w["on"]["pull_request"]["branches"]==["main"]
    assert "paths" not in w["on"]["pull_request"]
    assert "paths-ignore" not in w["on"]["pull_request"]
    assert w["on"]["push"]["branches"]==["main"]
    assert w["on"]["push"]["tags"]==["v*"]
    assert w["on"]["release"]["types"]==["published"]
    assert w["permissions"]=={"contents":"read"}
    assert w["concurrency"]["cancel-in-progress"]=="false"
    assert w["jobs"]["validate"]["name"]=="validate"
    assert w["jobs"]["audit-published"]["name"]=="audit-published"
    assert w["jobs"]["audit-published"]["needs"]=="validate"
    assert w["jobs"]["preflight-draft"]["needs"]=="validate"
    assert w["jobs"]["preflight-draft"]["if"]=="github.event_name == 'workflow_dispatch'"
    assert set(w["on"]["workflow_dispatch"]["inputs"])=={
        "tag", "release_id", "expected_tag_object_sha",
        "expected_commit", "expected_manifest_sha256",
        "expected_checksums_sha256",
    }


def test_only_github_owned_full_commit_sha_actions_are_admitted():
    w=workflow()
    refs=[
        step["uses"] for job in w["jobs"].values()
        for step in job["steps"] if "uses" in step
    ]
    assert len(refs)==6
    assert {x.split("@",1)[0] for x in refs}=={
        "actions/checkout","actions/setup-python"
    }
    assert all(re.fullmatch(r"actions/(checkout|setup-python)@[0-9a-f]{40}",x) for x in refs)
    assert {x.split("@",1)[1] for x in refs}=={
        "11d5960a326750d5838078e36cf38b85af677262",
        "a26af69be951a213d495a4c3e4e4022e16d87065",
    }
    for job in w["jobs"].values():
        for step in job["steps"]:
            if step.get("uses","").startswith("actions/checkout"):
                assert step["with"]["persist-credentials"]=="false"
                assert step["with"]["fetch-depth"]=="0"


def test_no_automatic_policy_mutation_or_credential_escalation_in_ci():
    w=workflow()
    assert "pull_request_target" not in w["on"]
    assert w["permissions"]["contents"]=="read"
    s=(ROOT/".github/workflows/registry-validate.yml").read_text()
    assert "GH_TOKEN: " + chr(36) + "{{ github.token }}" in s
    for forbidden in ("gh pr merge","gh release create","git push --force",
                      "gh auth login","GITHUB_TOKEN: write"):
        assert forbidden not in s
    assert "audit-main --expected-policy-commit" in s
    assert "TAG_GENESIS_MISMATCH" in s
    assert "PR_SOURCE_HEAD_MISMATCH" in s
    assert "Require the exact PR source HEAD" in s
    assert 'git diff --check "$PR_BASE" "$PR_HEAD"' in s
    assert 'ref: ' + chr(36) + "{{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}" in s
    assert "IMMUTABLE_RELEASE_REQUIRED" in s
    assert "RELEASE_MANIFEST_ASSET_MISMATCH" in s
    assert "registry.verify_release_preflight" in s
    assert "preflight-draft" in s


def test_codeowners_has_explicit_owner_and_self_ownership():
    s=(ROOT/".github/CODEOWNERS").read_text()
    for line in (
        "* @ludefeiqi", "/.github/CODEOWNERS @ludefeiqi",
        "/MANIFEST.sha256 @ludefeiqi",
    ):
        assert line in s
    assert "NOT independent review" in s
    assert "requires" in s


def test_official_docs_distinguish_enabled_from_missing_platform_enforcement():
    s=(ROOT/"releases/GITHUB-VERSION-MANAGEMENT.md").read_text()
    for item in (
        "immutable:true","protected=false","HTTP 403","GitHub Pro",
        "sha_pinning_required=false","v0.2.1","v0.2.2",
        "CODEOWNERS","reviewer","audit-main","v0.1.0",
        "不构成","不能阻止","不可","不自动合并",
    ):
        assert item in s,item
    assert s.count("https://docs.github.com/") >= 10


def test_solo_owner_policy_preserves_strict_github_and_separate_ai_human_gates():
    source=(ROOT/"releases/GITHUB-VERSION-MANAGEMENT.md").read_text()
    for required in (
        "main.protected=true", "required_approving_review_count=0",
        "require_last_push_approval=false", "enforce_admins=true",
        "required_conversation_resolution=true", "allow_force_pushes=false",
        "allow_deletions=false", "AI_R0_INDEPENDENT_REVIEW",
        "USER_EXPLICIT_RELEASE_APPROVAL", "HOLD_FOR_EXPLICIT_RELEASE_APPROVAL",
        "不自动发布", "不构成批准 v0.2.2 merge",
    ):
        assert required in source,required
    owners=(ROOT/".github/CODEOWNERS").read_text()
    assert "NOT independent review" in owners
    assert "ZERO GitHub reviewers" in owners


def test_current_gh_governance_narrative_not_stale_after_public_switch():
    policy=(ROOT/"GOVERNANCE.md").read_text()
    version=(ROOT/"releases/GITHUB-VERSION-MANAGEMENT.md").read_text()
    assert "正式已发布政策为 v0.2.1" in policy
    assert "尚未发布的 v0.2.2 候选" in policy
    assert "Public" in policy and "main.protected=true" in policy
    assert "HTTP 403 是历史事实" in policy
    assert "required_approving_review_count=0" in policy
    assert "用户准确发布批准" in policy
    assert "单账号" in version and "AI_R0_INDEPENDENT_REVIEW" in version
    assert "v0.2.1 整理候选" not in policy


def test_native_guard_files_are_in_next_policy_manifest():
    from registry.validate_registry import RELEASE_POLICY_FILESET
    required={
        ".github/workflows/registry-validate.yml",
        ".github/CODEOWNERS",
        "releases/GITHUB-VERSION-MANAGEMENT.md",
        "tests/test_gh_native_version_control.py",
        "tests/test_release_preflight.py",
        "registry/verify_release_preflight.py",
    }
    assert required<=RELEASE_POLICY_FILESET
    seen={line.split("  ",1)[1] for line in (ROOT/"MANIFEST.sha256").read_text().splitlines()}
    assert seen==RELEASE_POLICY_FILESET
