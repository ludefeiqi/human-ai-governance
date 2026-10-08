#!/usr/bin/env python3
"""Fail-closed validator for the Human-AI Governance v0.2 registry.

The network-capable paths invoke only ``gh api --method GET``.  They never
write GitHub state.  Local validation is deterministic over raw bytes.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Protocol, Sequence

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.tokens import AliasToken, AnchorToken, DirectiveToken, TagToken

from registry.validate_capabilities import CapabilityError, validate_capability_directory


MAX_INDEX_BYTES = 256 * 1024
MAX_YAML_DEPTH = 24
MAX_SCALAR_CHARS = 16 * 1024
MAX_FIRST_PARENT_COMMITS = 10_000
ALLOWED_BLOB_MODES = {"100644", "100755"}
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
GLOB_CHARS = set("*?[]{}")
FIXED_MANIFEST_BASE = {
    ".github/workflows/registry-validate.yml",
    "AGENTS.md",
    "CODEX-PROTOCOL.md",
    "GOVERNANCE.md",
    "HANDOFF.md",
    "README.md",
    "REGISTRY-PROTOCOL.md",
    "REVIEW-CHECKLIST.md",
    "registry/GENESIS.json",
    "registry/__init__.py",
    "registry/projects.schema.json",
    "registry/validate_registry.py",
    "requirements-registry.lock",
}
FIXED_POLICY_TEST_FILES = {
    "tests/__init__.py",
    "tests/helpers.py",
    "tests/test_github_evidence.py",
    "tests/test_project_sources.py",
    "tests/test_single_owner_approval.py",
    "tests/test_strict_reader.py",
    "tests/test_transitions_and_manifest.py",
    "tests/test_capability_catalog.py",
}
OPTIMIZATION_POLICY_FILES = {
    'CLIENT-CONTRACT.md',
    'RULE-MAP.md',
    'clients/build_plugin_overlay.py',
    'clients/chatgpt-plugin/README.md',
    'clients/chatgpt-plugin/skills/governance-bootstrap/SKILL.md',
    'clients/chatgpt-plugin/skills/governance-bootstrap/references/acceptance-suite.md',
    'clients/chatgpt-plugin/skills/governance-bootstrap/references/discovery-protocol.md',
    'clients/chatgpt-plugin/skills/governance-bootstrap/references/execution-closure.md',
    'clients/chatgpt-plugin/skills/governance-bootstrap/references/failure-contract.md',
    'clients/chatgpt-plugin/skills/governance-bootstrap/references/ledger-adapters.md',
    'clients/chatgpt-plugin/skills/governance-bootstrap/references/recovery-protocol.md',
    'clients/chatgpt-plugin/skills/governance-bootstrap/references/role-contract.md',
    'clients/chatgpt-plugin/skills/governance-bootstrap/references/runtime-adapter.md',
    'clients/chatgpt-plugin/skills/governance-bootstrap/references/source-lock.md',
    'clients/plugin-update.json',
    'tests/test_historical_approval.py',
    'tests/test_rule_contracts.py',
    'registry/capabilities/capability-card.schema.json',
    'registry/capabilities/codex.observe.json',
    'registry/capabilities/project.restore.json',
    'registry/capabilities/tool.route.json',
    'registry/validate_capabilities.py',
}
RELEASE_POLICY_FILESET = FIXED_MANIFEST_BASE | FIXED_POLICY_TEST_FILES | OPTIMIZATION_POLICY_FILES


class RegistryError(Exception):
    """A stable fail-closed error with a machine-readable code."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        return {"status": "HOLD", "code": self.code, "message": self.message, **self.details}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")


def identity_hash(project_id: str, repository: str) -> str:
    payload = {"project_id": project_id, "repository": repository}
    return "sha256:" + _sha256(_canonical_json(payload))


def _walk_yaml_node(node: Node, depth: int = 1) -> None:
    if depth > MAX_YAML_DEPTH:
        raise RegistryError("YAML_TOO_DEEP", f"YAML nesting exceeds {MAX_YAML_DEPTH}")
    if isinstance(node, ScalarNode):
        if len(node.value) > MAX_SCALAR_CHARS:
            raise RegistryError("YAML_SCALAR_TOO_LARGE", "YAML scalar exceeds limit")
        return
    if isinstance(node, SequenceNode):
        for child in node.value:
            _walk_yaml_node(child, depth + 1)
        return
    if isinstance(node, MappingNode):
        seen: set[str] = set()
        for key_node, value_node in node.value:
            if isinstance(key_node, ScalarNode) and key_node.value == "<<":
                raise RegistryError("YAML_MERGE_KEY", "YAML merge keys are forbidden")
            if not isinstance(key_node, ScalarNode) or key_node.tag != "tag:yaml.org,2002:str":
                raise RegistryError("YAML_NON_STRING_KEY", "all YAML mapping keys must be strings")
            if key_node.value in seen:
                raise RegistryError("YAML_DUPLICATE_KEY", f"duplicate YAML key: {key_node.value}")
            seen.add(key_node.value)
            _walk_yaml_node(value_node, depth + 1)
        return
    raise RegistryError("YAML_NODE_UNSUPPORTED", f"unsupported YAML node {type(node).__name__}")


def _schema_errors(schema: Mapping[str, Any], value: Any) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(value), key=lambda e: list(e.absolute_path))
    return [
        f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
        for error in errors
    ]


def _validate_repository(value: str) -> None:
    pieces = value.split("/")
    if len(pieces) != 2:
        raise RegistryError("REPOSITORY_INVALID", "repository must be exact owner/repo")
    owner, repo = pieces
    if not OWNER_RE.fullmatch(owner) or not REPO_RE.fullmatch(repo):
        raise RegistryError("REPOSITORY_INVALID", "repository must be exact owner/repo")
    if repo in {".", ".."} or repo.lower().endswith(".git"):
        raise RegistryError("REPOSITORY_INVALID", "repository name is not canonical")


def _validate_repo_path(value: str, field: str) -> None:
    if "\\" in value or any(char in value for char in GLOB_CHARS):
        raise RegistryError("PATH_INVALID", f"{field} must be a literal POSIX path")
    if "://" in value or "?" in value or "#" in value:
        raise RegistryError("PATH_INVALID", f"{field} must not be a URL")
    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith("~"):
        raise RegistryError("PATH_INVALID", f"{field} must be repository-relative")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise RegistryError("PATH_INVALID", f"{field} contains an unsafe segment")
    lowered = {part.lower() for part in path.parts}
    forbidden = {".git", ".ssh", "secrets", "credentials", "cookies", "profiles", "cache", "logs"}
    if lowered & forbidden:
        raise RegistryError("PATH_SENSITIVE", f"{field} references a forbidden location")


def _validate_branch(value: str) -> None:
    if (
        value.startswith(("-", ".", "/"))
        or value.endswith((".", "/"))
        or ".." in value
        or "@{" in value
        or "//" in value
        or any(char in value for char in " ~^:?*[\\")
        or any(part.endswith(".lock") for part in value.split("/"))
    ):
        raise RegistryError("BRANCH_INVALID", "authority_branch is not a safe Git branch name")


def _parse_utc(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RegistryError("TIME_INVALID", f"invalid RFC3339 UTC timestamp: {value}") from exc
    if parsed.tzinfo != dt.timezone.utc or not value.endswith("Z"):
        raise RegistryError("TIME_INVALID", "timestamp must be UTC and end in Z")
    return parsed


def validate_semantics(index: Mapping[str, Any]) -> None:
    for project_id, entry in index["projects"].items():
        if not PROJECT_ID_RE.fullmatch(project_id):
            raise RegistryError("PROJECT_ID_INVALID", f"invalid project id: {project_id}")
        _validate_repository(entry["repository"])
        _validate_branch(entry["authority_branch"])
        for field in ("ledger_path", "project_rules_path"):
            _validate_repo_path(entry[field], field)
        _validate_repo_path(entry["frozen_product_baseline"]["path"], "frozen_product_baseline.path")
        identity = entry["identity"]
        if identity["canonical_id"] != project_id:
            raise RegistryError("IDENTITY_ID_MISMATCH", f"identity id mismatch for {project_id}")
        expected_hash = identity_hash(project_id, entry["repository"])
        if identity["identity_hash"] != expected_hash:
            raise RegistryError("IDENTITY_HASH_MISMATCH", f"identity hash mismatch for {project_id}")
        previous_time: dt.datetime | None = None
        for event in entry["lifecycle_history"]:
            event_time = _parse_utc(event["changed_at"])
            if previous_time is not None and event_time <= previous_time:
                raise RegistryError("HISTORY_ORDER_INVALID", f"history is not strictly ordered for {project_id}")
            previous_time = event_time
        history = entry["lifecycle_history"]
        if history and history[-1]["lifecycle"] != entry["lifecycle"]:
            raise RegistryError("HISTORY_STATE_MISMATCH", f"latest history state mismatch for {project_id}")
        if entry["lifecycle"] in {"paused", "retired"} and not history:
            raise RegistryError("TOMBSTONE_HISTORY_MISSING", f"{project_id} lacks lifecycle tombstone history")


def load_schema(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryError("SCHEMA_UNREADABLE", f"cannot read schema: {path}") from exc
    Draft202012Validator.check_schema(value)
    return value


def load_index_bytes(raw: bytes, schema: Mapping[str, Any]) -> dict[str, Any]:
    if len(raw) > MAX_INDEX_BYTES:
        raise RegistryError("INDEX_TOO_LARGE", f"index exceeds {MAX_INDEX_BYTES} bytes")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RegistryError("UTF8_BOM_FORBIDDEN", "UTF-8 BOM is forbidden")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RegistryError("UTF8_INVALID", "index is not valid UTF-8") from exc
    if CONTROL_RE.search(text):
        raise RegistryError("CONTROL_CHARACTER", "index contains a forbidden control character")
    try:
        tokens = list(yaml.scan(text, Loader=yaml.SafeLoader))
    except yaml.YAMLError as exc:
        raise RegistryError("YAML_INVALID", "index is not valid YAML") from exc
    for token in tokens:
        if isinstance(token, AnchorToken):
            raise RegistryError("YAML_ANCHOR", "YAML anchors are forbidden")
        if isinstance(token, AliasToken):
            raise RegistryError("YAML_ALIAS", "YAML aliases are forbidden")
        if isinstance(token, TagToken):
            raise RegistryError("YAML_TAG", "explicit YAML tags are forbidden")
        if isinstance(token, DirectiveToken):
            raise RegistryError("YAML_DIRECTIVE", "YAML directives are forbidden")
    try:
        root = yaml.compose(text, Loader=yaml.SafeLoader)
        if root is None:
            raise RegistryError("YAML_EMPTY", "index is empty")
        _walk_yaml_node(root)
        value = yaml.safe_load(text)
    except RegistryError:
        raise
    except yaml.YAMLError as exc:
        raise RegistryError("YAML_INVALID", "index is not valid single-document YAML") from exc
    errors = _schema_errors(schema, value)
    if errors:
        raise RegistryError("SCHEMA_INVALID", "index does not match schema", errors=errors)
    validate_semantics(value)
    return value


def load_index(path: Path, schema: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RegistryError("INDEX_UNREADABLE", f"cannot read index: {path}") from exc
    return load_index_bytes(raw, schema), raw


def compare_indexes(
    previous: Mapping[str, Any], current: Mapping[str, Any], previous_index_commit: str
) -> list[dict[str, Any]]:
    if not SHA40_RE.fullmatch(previous_index_commit):
        raise RegistryError("PREVIOUS_COMMIT_INVALID", "previous index commit must be 40 lowercase hex")
    before = previous["projects"]
    after = current["projects"]
    deleted = sorted(set(before) - set(after))
    if deleted:
        raise RegistryError("PHYSICAL_DELETE_FORBIDDEN", "project ids must remain as tombstones", ids=deleted)
    changes: list[dict[str, Any]] = []
    for project_id in sorted(after):
        new = after[project_id]
        old = before.get(project_id)
        if old is None:
            if new["lifecycle"] != "active" or new["lifecycle_history"]:
                raise RegistryError("NEW_PROJECT_STATE_INVALID", f"new project {project_id} must start active")
            provenance = new["registration_provenance"]
            if provenance.get("kind") != "reviewed_change" or provenance.get("previous_index_commit") != previous_index_commit:
                raise RegistryError("NEW_PROJECT_PROVENANCE_INVALID", f"new project {project_id} lacks base binding")
            changes.append({"id": project_id, "kind": "NEW", "before": None, "after": new})
            continue
        for field in ("canonical_id", "identity_hash"):
            if old["identity"][field] != new["identity"][field]:
                raise RegistryError("IDENTITY_REPURPOSE_FORBIDDEN", f"identity changed for {project_id}")
        if old["repository"] != new["repository"]:
            raise RegistryError("IDENTITY_REPURPOSE_FORBIDDEN", f"repository changed for {project_id}")
        old_history = old["lifecycle_history"]
        new_history = new["lifecycle_history"]
        if new_history[: len(old_history)] != old_history:
            raise RegistryError("HISTORY_REWRITE_FORBIDDEN", f"history changed for {project_id}")
        state_changed = old["lifecycle"] != new["lifecycle"]
        appended = new_history[len(old_history) :]
        if state_changed:
            if len(appended) != 1:
                raise RegistryError("LIFECYCLE_EVENT_REQUIRED", f"one lifecycle event required for {project_id}")
            event = appended[0]
            if event["lifecycle"] != new["lifecycle"] or event["previous_index_commit"] != previous_index_commit:
                raise RegistryError("LIFECYCLE_EVENT_INVALID", f"lifecycle event is not base-bound for {project_id}")
        elif appended:
            raise RegistryError("SPURIOUS_HISTORY_EVENT", f"history appended without lifecycle change for {project_id}")
        if old != new:
            kind = "RETIRED" if new["lifecycle"] == "retired" else "MODIFIED"
            if old["lifecycle"] == "retired" and new["lifecycle"] == "active":
                kind = "REACTIVATED"
            changes.append({"id": project_id, "kind": kind, "before": old, "after": new})
    return changes


def normalized_diff(changes: Sequence[Mapping[str, Any]]) -> tuple[bytes, str]:
    payload = [
        {"id": change["id"], "kind": change["kind"], "before": change["before"], "after": change["after"]}
        for change in sorted(changes, key=lambda item: item["id"])
    ]
    raw = _canonical_json(payload)
    return raw, _sha256(raw)


def load_genesis(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryError("GENESIS_UNREADABLE", f"cannot read genesis: {path}") from exc
    required = {
        "schema_version",
        "status",
        "governance_repository",
        "immutable_owner_account",
        "release_tag",
        "release_commit_source",
        "registry_branch",
        "registry_path",
        "initial_index_sha256",
        "initial_project_identity_hashes",
        "approval_comment_marker",
        "registry_update_approval_mode",
        "ai_review_comment_marker",
        "unreleased_behavior",
    }
    if set(value) != required:
        raise RegistryError("GENESIS_FIELDS_INVALID", "genesis fields are not exact")
    if value["schema_version"] != 1 or value["release_commit_source"] != "dereferenced_annotated_tag":
        raise RegistryError("GENESIS_INVALID", "genesis contract is invalid")
    if value["status"] != "ACTIVATES_ONLY_AFTER_VERIFIED_RELEASE_TAG":
        raise RegistryError("GENESIS_STATUS_INVALID", "genesis activation condition is invalid")
    _validate_repository(value["governance_repository"])
    if not OWNER_RE.fullmatch(value["immutable_owner_account"]):
        raise RegistryError("GENESIS_OWNER_INVALID", "immutable owner account is invalid")
    if value["governance_repository"].split("/", 1)[0] != value["immutable_owner_account"]:
        raise RegistryError("GENESIS_OWNER_INVALID", "immutable owner must own the governance repository")
    if value["release_tag"] not in {"v0.2.0", "v0.2.1"}:
        raise RegistryError("GENESIS_TAG_INVALID", "unsupported exact release tag")
    if value["registry_path"] != "projects.yaml" or value["registry_branch"] != "main":
        raise RegistryError("GENESIS_REGISTRY_INVALID", "genesis registry target is invalid")
    if not SHA256_RE.fullmatch(value["initial_index_sha256"]):
        raise RegistryError("GENESIS_INDEX_SHA_INVALID", "initial index SHA256 is invalid")
    if value["approval_comment_marker"] != "HAGOV-REGISTRY-OWNER-APPROVAL-V1":
        raise RegistryError("GENESIS_MARKER_INVALID", "approval comment marker is invalid")
    if value["ai_review_comment_marker"] != "HAGOV-AI-R0-ATTESTATION-V1":
        raise RegistryError("GENESIS_AI_MARKER_INVALID", "independent AI R0 attestation marker is invalid")
    if value["registry_update_approval_mode"] not in {
        "EXTERNAL_GITHUB_REVIEW", "SINGLE_OWNER_AI_R0_ATTESTED",
    }:
        raise RegistryError("GENESIS_APPROVAL_MODE_INVALID", "registry approval mode is not recognized")
    if value["unreleased_behavior"] != "HOLD_V0_1_SEMANTICS":
        raise RegistryError("GENESIS_UNRELEASED_INVALID", "unreleased behavior is invalid")
    identities = value["initial_project_identity_hashes"]
    if not isinstance(identities, dict) or not identities:
        raise RegistryError("GENESIS_IDENTITIES_INVALID", "initial identities must be a non-empty object")
    for project_id, digest in identities.items():
        if not PROJECT_ID_RE.fullmatch(project_id) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise RegistryError("GENESIS_IDENTITIES_INVALID", "initial identity entry is invalid")
    return value


def validate_genesis_index(genesis: Mapping[str, Any], index: Mapping[str, Any], raw: bytes) -> None:
    expected = genesis["initial_index_sha256"]
    if expected != _sha256(raw):
        raise RegistryError("GENESIS_INDEX_MISMATCH", "initial index raw SHA256 does not match genesis")
    identities = {pid: entry["identity"]["identity_hash"] for pid, entry in index["projects"].items()}
    if identities != genesis["initial_project_identity_hashes"]:
        raise RegistryError("GENESIS_IDENTITIES_MISMATCH", "initial identities do not match genesis")


def validate_manifest(root: Path, manifest_path: Path) -> dict[str, str]:
    try:
        lines = manifest_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise RegistryError("MANIFEST_UNREADABLE", "cannot read manifest") from exc
    entries: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)", line)
        if not match:
            raise RegistryError("MANIFEST_FORMAT_INVALID", f"invalid manifest line: {line!r}")
        digest, relative = match.groups()
        if relative in entries:
            raise RegistryError("MANIFEST_DUPLICATE", f"duplicate manifest path: {relative}")
        _validate_repo_path(relative, "manifest path")
        entries[relative] = digest
    if "projects.yaml" in entries:
        raise RegistryError("MANIFEST_DYNAMIC_INDEX", "dynamic projects.yaml must not be in policy manifest")
    expected_entries = RELEASE_POLICY_FILESET
    missing = sorted(expected_entries - set(entries))
    extra = sorted(set(entries) - expected_entries)
    if missing or extra:
        raise RegistryError(
            "MANIFEST_FILESET_MISMATCH",
            "manifest file set does not equal the fixed policy and complete test set",
            missing=missing,
            extra=extra,
        )
    for relative, expected in entries.items():
        path = root / relative
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise RegistryError("MANIFEST_FILE_UNREADABLE", f"cannot read {relative}") from exc
        actual = _sha256(raw)
        if actual != expected:
            raise RegistryError("MANIFEST_HASH_MISMATCH", f"raw-byte hash mismatch for {relative}")
    return entries


class Api(Protocol):
    def get(self, endpoint: str, fields: Mapping[str, str] | None = None) -> Any: ...


class GhApi:
    """Authenticated GitHub reads.  No other gh subcommand or HTTP method exists here."""

    def get(self, endpoint: str, fields: Mapping[str, str] | None = None) -> Any:
        command = ["gh", "api", "--method", "GET", endpoint]
        for key, value in sorted((fields or {}).items()):
            command.extend(["-f", f"{key}={value}"])
        try:
            completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise RegistryError("GITHUB_GET_TIMEOUT", f"authenticated GitHub GET timed out for {endpoint}") from exc
        if completed.returncode != 0:
            raise RegistryError(
                "GITHUB_GET_FAILED",
                f"authenticated GitHub GET failed for {endpoint}",
                exit_code=completed.returncode,
            )
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RegistryError("GITHUB_RESPONSE_INVALID", f"non-JSON response for {endpoint}") from exc


def _repo_endpoint(repository: str, suffix: str) -> str:
    return f"repos/{repository}/{suffix}"


def _pages(api: Api, endpoint: str) -> list[Any]:
    collected: list[Any] = []
    for page in range(1, 101):
        result = api.get(endpoint, {"per_page": "100", "page": str(page)})
        if not isinstance(result, list):
            raise RegistryError("GITHUB_RESPONSE_INVALID", f"expected list from {endpoint}")
        collected.extend(result)
        if len(result) < 100:
            return collected
    raise RegistryError("GITHUB_PAGINATION_LIMIT", f"too many pages from {endpoint}")


def _content_bytes(api: Api, repository: str, path: str, ref: str) -> tuple[bytes, str]:
    encoded_path = urllib.parse.quote(path, safe="/")
    response = api.get(_repo_endpoint(repository, f"contents/{encoded_path}"), {"ref": ref})
    if response.get("type") != "file" or response.get("encoding") != "base64":
        raise RegistryError("INDEX_CONTENT_INVALID", f"{path}@{ref} is not a base64 file")
    try:
        compact = "".join(response["content"].split())
        raw = base64.b64decode(compact, validate=True)
    except (KeyError, ValueError) as exc:
        raise RegistryError("INDEX_CONTENT_INVALID", "invalid base64 index content") from exc
    return raw, response.get("sha", "")


def resolve_release_commit(api: Api, genesis: Mapping[str, Any]) -> str:
    if genesis["status"] != "ACTIVATES_ONLY_AFTER_VERIFIED_RELEASE_TAG":
        raise RegistryError("V0_2_UNPUBLISHED", "genesis not active; retain previously adopted policy")
    repository = genesis["governance_repository"]
    tag_name = genesis["release_tag"]
    ref = api.get(_repo_endpoint(repository, f"git/ref/tags/{urllib.parse.quote(tag_name, safe='')}"))
    obj = ref.get("object", {})
    if obj.get("type") != "tag":
        raise RegistryError("RELEASE_TAG_NOT_ANNOTATED", "policy release must be an annotated tag")
    tag = api.get(_repo_endpoint(repository, f"git/tags/{obj.get('sha', '')}"))
    target = tag.get("object", {})
    if target.get("type") != "commit" or not SHA40_RE.fullmatch(target.get("sha", "")):
        raise RegistryError("RELEASE_TAG_TARGET_INVALID", "annotated tag does not resolve to a commit")
    return target["sha"]


def _require_release_policy_pin(
    api: Api, genesis: Mapping[str, Any], schema: Mapping[str, Any],
    expected_policy_commit: str | None,
) -> str:
    if not expected_policy_commit or not SHA40_RE.fullmatch(expected_policy_commit):
        raise RegistryError("POLICY_PIN_REQUIRED", "immutable policy commit pin is required for approval checks")
    release_commit = resolve_release_commit(api, genesis)
    if release_commit != expected_policy_commit:
        raise RegistryError("POLICY_PIN_MISMATCH", "tag resolves to a different commit than the external pin")
    verify_policy_sources_from_immutable_commit(api, genesis, schema, release_commit)
    return release_commit


def _parse_owner_comment(body: str, marker: str) -> dict[str, str] | None:
    lines = body.splitlines()
    if not lines or lines[0].strip() != marker:
        return None
    values: dict[str, str] = {}
    for line in lines[1:]:
        if not line or "=" not in line:
            return None
        key, value = line.split("=", 1)
        if key in values or not re.fullmatch(r"[a-z0-9_]+", key):
            return None
        values[key] = value
    return values


@dataclass(frozen=True)
class PreMergeEvidence:
    pr_number: int
    candidate_head: str
    previous_index_commit: str
    index_sha256: str
    normalized_diff_sha256: str
    changed_ids: tuple[str, ...]
    independent_reviewer: str
    independent_review_submitted_at: str
    owner_comment_id: int
    owner_comment_created_at: str
    approval_profile: str = "EXTERNAL_GITHUB_REVIEW"
    ai_review_comment_id: int | None = None
    ai_review_comment_sha256: str | None = None
    ci_check_run_id: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "VERIFIED",
            "phase": "PRE_MERGE",
            "pr_number": self.pr_number,
            "candidate_head": self.candidate_head,
            "previous_index_commit": self.previous_index_commit,
            "index_sha256": self.index_sha256,
            "normalized_diff_sha256": self.normalized_diff_sha256,
            "changed_ids": list(self.changed_ids),
            "independent_reviewer": self.independent_reviewer,
            "independent_review_submitted_at": self.independent_review_submitted_at,
            "owner_comment_id": self.owner_comment_id,
            "owner_comment_created_at": self.owner_comment_created_at,
            "approval_authentication": "GITHUB_ACCOUNT_ATTRIBUTION_ONLY_NOT_PASSWORD_SIGNATURE",
            "approval_profile": self.approval_profile,
            "assurance_level": (
                "OWNER_POSTED_AI_R0_NOT_INDEPENDENT_GITHUB_REVIEW"
                if self.approval_profile == "SINGLE_OWNER_AI_R0_ATTESTED"
                else "EXTERNAL_GITHUB_REVIEW"
            ),
            "ai_review_comment_id": self.ai_review_comment_id,
            "ai_review_comment_sha256": self.ai_review_comment_sha256,
            "ci_check_run_id": self.ci_check_run_id,
            "source_attribution_is_not_ai_authorship_proof": True,
        }


def _validate_pre_merge_core(
    api: Api,
    genesis: Mapping[str, Any],
    schema: Mapping[str, Any],
    pr_number: int,
    expected_head: str,
    *,
    historical_base: str | None = None,
    evidence_before: dt.datetime | None = None,
) -> PreMergeEvidence:
    repository = genesis["governance_repository"]
    if not SHA40_RE.fullmatch(expected_head):
        raise RegistryError("CANDIDATE_HEAD_INVALID", "expected candidate head must be 40 lowercase hex")
    pr = api.get(_repo_endpoint(repository, f"pulls/{pr_number}"))
    if pr.get("head", {}).get("sha") != expected_head:
        raise RegistryError("CANDIDATE_HEAD_MISMATCH", "PR head does not equal expected candidate head")
    # Once merged, GitHub may move the PR's base ref to later main HEAD.
    # The actual merge commit first parent is the historical approved base.
    base_sha = historical_base if historical_base is not None else pr.get("base", {}).get("sha", "")
    if not SHA40_RE.fullmatch(base_sha):
        raise RegistryError("PR_BASE_INVALID", "PR base SHA is missing or invalid")
    files = _pages(api, _repo_endpoint(repository, f"pulls/{pr_number}/files"))
    # A rename to projects.yaml is NOT a projects.yaml-only modification.
    if (len(files) != 1 or
            files[0].get("filename") != genesis["registry_path"] or
            files[0].get("status") != "modified" or
            "previous_filename" in files[0]):
        raise RegistryError("PR_FILES_FORBIDDEN", "registry update may only modify the existing projects.yaml")
    current_raw, _ = _content_bytes(api, repository, genesis["registry_path"], expected_head)
    previous_raw, _ = _content_bytes(api, repository, genesis["registry_path"], base_sha)
    current = load_index_bytes(current_raw, schema)
    previous = load_index_bytes(previous_raw, schema)
    changes = compare_indexes(previous, current, base_sha)
    if not changes:
        raise RegistryError("INDEX_DIFF_EMPTY", "registry PR contains no semantic registry change")
    _, diff_sha = normalized_diff(changes)
    index_sha = _sha256(current_raw)
    changed_ids = tuple(change["id"] for change in changes)
    approval_mode = genesis["registry_update_approval_mode"]
    if approval_mode == "SINGLE_OWNER_AI_R0_ATTESTED":
        return _verify_single_owner_b(
            api, genesis, pr, pr_number, expected_head, base_sha,
            index_sha, diff_sha, changed_ids, evidence_before=evidence_before,
        )
    if approval_mode != "EXTERNAL_GITHUB_REVIEW":
        raise RegistryError("APPROVAL_PROFILE_UNKNOWN", "release policy has no approved registry review mode")
    reviews = _pages(api, _repo_endpoint(repository, f"pulls/{pr_number}/reviews"))
    latest_by_user: dict[str, tuple[dt.datetime, Mapping[str, Any]]] = {}
    for review in reviews:
        login = review.get("user", {}).get("login")
        if not login or not review.get("submitted_at"):
            continue
        submitted = _parse_utc(review["submitted_at"])
        if evidence_before is not None and submitted >= evidence_before:
            continue
        if login not in latest_by_user or submitted >= latest_by_user[login][0]:
            latest_by_user[login] = (submitted, review)
    author = pr.get("user", {}).get("login")
    owner = genesis["immutable_owner_account"]
    approved = sorted(
        (
            (when, login, review)
            for login, (when, review) in latest_by_user.items()
            if review.get("state") == "APPROVED"
            and review.get("commit_id") == expected_head
            and login not in {author, owner}
        ),
        key=lambda item: (item[0], item[1]),
    )
    if not approved:
        raise RegistryError("INDEPENDENT_APPROVAL_MISSING", "no independent APPROVED review on exact head")

    comments = _pages(api, _repo_endpoint(repository, f"issues/{pr_number}/comments"))
    expected_fields = {
        "authorized_action": "APPROVE_DISCOVERY_REGISTRY_UPDATE",
        "approval_scope": "GOVERNANCE_REGISTRY_ONLY",
        "candidate_head": expected_head,
        "previous_index_commit": base_sha,
        "index_sha256": index_sha,
        "normalized_diff_sha256": diff_sha,
        "changed_ids": ",".join(changed_ids),
    }
    # Time is GitHub-owned metadata. It must NEVER be guessed and placed in the
    # user's approval body before GitHub creates the comment.
    owner_decisions: list[tuple[dt.datetime, Mapping[str, Any]]] = []
    for comment in comments:
        if comment.get("user", {}).get("login") != owner:
            continue
        if not str(comment.get("body", "")).startswith(genesis["approval_comment_marker"]):
            continue
        try:
            created = _parse_utc(comment.get("created_at", ""))
            updated = _parse_utc(comment.get("updated_at", ""))
        except (RegistryError, TypeError, AttributeError):
            raise RegistryError("OWNER_APPROVAL_TIME_INVALID", "owner comment lacks trustworthy UTC metadata")
        if evidence_before is not None and created >= evidence_before:
            continue
        if updated != created:
            raise RegistryError("OWNER_APPROVAL_EDITED", "owner approval comment was edited after creation")
        owner_decisions.append((created, comment))
    if not owner_decisions:
        raise RegistryError("OWNER_APPROVAL_MISSING", "owner comment is absent")
    owner_decisions.sort(key=lambda item: (item[0], item[1].get("id", 0)))
    created, valid_comment = owner_decisions[-1]
    parsed = _parse_owner_comment(valid_comment.get("body", ""), genesis["approval_comment_marker"])
    if parsed != expected_fields:
        raise RegistryError("OWNER_APPROVAL_MISMATCH", "latest owner approval does not bind exact reviewed evidence")
    qualifying_reviews = [(when, who) for when, who, _ in approved if when < created]
    if not qualifying_reviews:
        raise RegistryError("REVIEW_AFTER_OWNER_APPROVAL", "independent review must precede owner approval")
    review_at, reviewer = qualifying_reviews[-1]
    comment_id = valid_comment.get("id")
    if not isinstance(comment_id, int) or comment_id <= 0:
        raise RegistryError("OWNER_APPROVAL_ID_INVALID", "owner approval has no immutable GitHub comment ID")
    return PreMergeEvidence(
        pr_number=pr_number,
        candidate_head=expected_head,
        previous_index_commit=base_sha,
        index_sha256=index_sha,
        normalized_diff_sha256=diff_sha,
        changed_ids=changed_ids,
        independent_reviewer=reviewer,
        independent_review_submitted_at=review_at.isoformat().replace("+00:00", "Z"),
        owner_comment_id=comment_id,
        owner_comment_created_at=created.isoformat().replace("+00:00", "Z"),
    )



def validate_pre_merge(
    api: Api, genesis: Mapping[str, Any], schema: Mapping[str, Any],
    pr_number: int, expected_head: str, *,
    expected_policy_commit: str | None = None,
) -> PreMergeEvidence:
    """Public R0 approval audit. Caller must supply an externally pinned policy Commit."""
    immutable_genesis = json.loads(_canonical_json(genesis))
    immutable_schema = json.loads(_canonical_json(schema))
    _require_release_policy_pin(api, immutable_genesis, immutable_schema, expected_policy_commit)
    return _validate_pre_merge_core(
        api, immutable_genesis, immutable_schema, pr_number, expected_head,
    )


def _owner_github_comment(
    comments: Sequence[Mapping[str, Any]], owner: str, marker: str,
    *, missing_code: str, evidence_before: dt.datetime | None = None,
) -> tuple[dt.datetime, Mapping[str, Any]]:
    """Latest owner-authored marker comment. GitHub attribution is not a human signature."""
    options: list[tuple[dt.datetime, Mapping[str, Any]]] = []
    for comment in comments:
        if comment.get("user", {}).get("login") != owner:
            continue
        if not str(comment.get("body", "")).startswith(marker):
            continue
        try:
            created = _parse_utc(comment.get("created_at", ""))
            updated = _parse_utc(comment.get("updated_at", ""))
        except (RegistryError, TypeError, AttributeError) as exc:
            raise RegistryError("AI_B_COMMENT_TIME_INVALID", "owner comment missing valid UTC timestamps") from exc
        if evidence_before is not None and created >= evidence_before:
            continue
        if updated != created:
            raise RegistryError("AI_B_COMMENT_EDITED", "owner attestation or approval comment was edited")
        comment_id = comment.get("id")
        if type(comment_id) is not int or comment_id <= 0:
            raise RegistryError("AI_B_COMMENT_ID_INVALID", "owner comment lacks valid GitHub ID")
        options.append((created, comment))
    if not options:
        raise RegistryError(missing_code, "required GitHub owner-account attestation is missing")
    options.sort(key=lambda c: (c[0], c[1]["id"]))
    return options[-1]


def _verify_historical_ci(
    api: Api, repo: str, head: str, bound_run_id: int, cutoff: dt.datetime,
) -> None:
    """Bounded event-time proof. Missing history never becomes approval.

    Runs begun after merge are current-health evidence, not prior approval.
    A run already pending at merge, or a newer failure before merge, blocks.
    """
    result = api.get(_repo_endpoint(repo, f"commits/{head}/check-runs"),
                     {"per_page": "100", "filter": "all"})
    if (not isinstance(result, dict) or type(result.get("total_count")) is not int
            or not isinstance(result.get("check_runs"), list)
            or not 0 <= result["total_count"] <= 100
            or len(result["check_runs"]) != result["total_count"]):
        raise RegistryError("AI_B_CI_HISTORY_UNAVAILABLE", "complete bounded CI history unavailable")
    prior = []
    for run in result["check_runs"]:
        if (run.get("name") != "validate" or run.get("app", {}).get("slug") != "github-actions"
                or run.get("head_sha") != head):
            continue
        try:
            start = _parse_utc(run.get("started_at") or run.get("completed_at") or "")
        except (RegistryError, TypeError, AttributeError) as exc:
            raise RegistryError("AI_B_CI_HISTORY_TIME_UNPROVEN", "cannot place CI run in history") from exc
        if start >= cutoff:
            # A completed-only timestamp after merge cannot prove it started after merge.
            if not run.get("started_at"):
                raise RegistryError("AI_B_CI_HISTORY_TIME_UNPROVEN", "post-merge completion lacks start time")
            continue
        if type(run.get("id")) is not int or run["id"] <= 0:
            raise RegistryError("AI_B_CI_HISTORY_UNAVAILABLE", "historical run ID invalid")
        if run.get("status") != "completed" or not run.get("completed_at"):
            raise RegistryError("AI_B_CI_NOT_COMPLETE_AT_MERGE", "a validation was pending at merge")
        completed = _parse_utc(run["completed_at"])
        if completed < start:
            raise RegistryError("AI_B_CI_HISTORY_TIME_UNPROVEN", "CI times are inconsistent")
        if completed >= cutoff:
            raise RegistryError("AI_B_CI_NOT_COMPLETE_AT_MERGE", "a validation had not completed at merge")
        # GitHub latest is ordered by completion; an older-started failing run
        # that finishes after the approved run must also invalidate pre-merge approval.
        prior.append((completed, run["id"], run))
    if not prior:
        raise RegistryError("AI_B_CI_HISTORY_UNAVAILABLE", "no pre-merge validation evidence")
    _, run_id, latest = max(prior, key=lambda r: (r[0], r[1]))
    if (run_id != bound_run_id or latest.get("status") != "completed"
            or latest.get("conclusion") != "success"):
        raise RegistryError("AI_B_CI_NOT_LATEST_AT_MERGE", "approved run not the latest successful pre-merge run")
    if _parse_utc(latest.get("completed_at", "")) >= cutoff:
        raise RegistryError("AI_B_CI_NOT_COMPLETE_AT_MERGE", "validation not complete before merge")


def _verify_single_owner_b(
    api: Api, genesis: Mapping[str, Any], pr: Mapping[str, Any], pr_number: int,
    expected_head: str, base_sha: str, index_sha: str,
    diff_sha: str, changed_ids: tuple[str, ...],
    *, evidence_before: dt.datetime | None = None,
) -> PreMergeEvidence:
    """Lower-assurance B evidence, strictly distinct from a GitHub APPROVED review.

    The attestation is posted using the owner's GitHub account. We verify that
    GitHub recorded the artifact and its exact binding, NOT that another account,
    a cryptographically independent AI, or a human author created that content.
    """
    if pr.get("draft") is True:
        raise RegistryError("AI_B_PR_DRAFT", "ordinary registry change must leave Draft before approval")
    repo = genesis["governance_repository"]
    owner = genesis["immutable_owner_account"]
    comments = _pages(api, _repo_endpoint(repo, f"issues/{pr_number}/comments"))
    ai_time, ai_comment = _owner_github_comment(
        comments, owner, genesis["ai_review_comment_marker"],
        missing_code="AI_B_ATTESTATION_MISSING", evidence_before=evidence_before,
    )
    common = {
        "candidate_head": expected_head,
        "previous_index_commit": base_sha,
        "index_sha256": index_sha,
        "normalized_diff_sha256": diff_sha,
        "changed_ids": ",".join(changed_ids),
    }
    review_body = ai_comment["body"]
    reported = _parse_owner_comment(review_body, genesis["ai_review_comment_marker"])
    required_review = {
        **common,
        "review_scope": "DISCOVERY_METADATA_ONLY",
        "decision": "APPROVE_DESIGN",
        "assurance_level": "OWNER_POSTED_AI_R0_NOT_GITHUB_REVIEW",
        "open_blockers": "0",
    }
    if reported is None or any(reported.get(key) != val for key, val in required_review.items()):
        raise RegistryError("AI_B_ATTESTATION_MISMATCH", "AI R0 report not bound to exact registry diff")
    if set(reported) != set(required_review) | {
        "review_engine", "review_session_ref", "summary", "ci_check_run_id",
    }:
        raise RegistryError("AI_B_ATTESTATION_FIELDS_INVALID", "AI R0 report has unknown or missing fields")
    if (not re.fullmatch(r"[A-Za-z0-9._-]{2,64}", reported["review_engine"])
            or not re.fullmatch(r"[A-Za-z0-9._:/-]{6,180}", reported["review_session_ref"])
            or not 10 <= len(reported["summary"]) <= 500
            or any(ch in reported["summary"] for ch in "\r\n")):
        raise RegistryError("AI_B_ATTESTATION_SOURCE_INVALID", "AI review source and summary are incomplete")
    try:
        run_id = int(reported["ci_check_run_id"])
    except (ValueError, TypeError) as exc:
        raise RegistryError("AI_B_CI_ID_INVALID", "CI check run ID must be numeric") from exc
    if not 0 < run_id < 2**63 or str(run_id) != reported["ci_check_run_id"]:
        raise RegistryError("AI_B_CI_ID_INVALID", "CI check run ID is not canonical")
    check = api.get(_repo_endpoint(repo, f"check-runs/{run_id}"))
    if (check.get("id") != run_id
            or check.get("name") != "validate"
            or check.get("head_sha") != expected_head
            or check.get("status") != "completed"
            or check.get("conclusion") != "success"
            or check.get("app", {}).get("slug") != "github-actions"
            or not any(
                ref.get("number") == pr_number
                and ref.get("head", {}).get("sha") == expected_head
                for ref in check.get("pull_requests", [])
            )):
        raise RegistryError("AI_B_CI_NOT_VERIFIED", "CI check does not verify this exact PR and candidate")
    # Current pre-merge requires latest success. Historical replay instead
    # establishes the most recent run that existed *before actual merge*.
    if evidence_before is None:
        # An earlier successful run must not override a newer failed/running
        # validation on the same exact candidate commit.
        latest = api.get(
            _repo_endpoint(repo, f"commits/{expected_head}/check-runs"),
            {"per_page": "100", "filter": "latest"},
        )
        if (not isinstance(latest, dict)
                or type(latest.get("total_count")) is not int
                or not 0 <= latest["total_count"] <= 100
                or not isinstance(latest.get("check_runs"), list)):
            raise RegistryError("AI_B_CI_LATEST_UNAVAILABLE", "cannot obtain bounded latest GitHub checks")
        current_checks = [
            item for item in latest["check_runs"]
            if item.get("name") == "validate"
            and item.get("app", {}).get("slug") == "github-actions"
            and item.get("head_sha") == expected_head
        ]
        if (len(current_checks) != 1 or current_checks[0].get("id") != run_id
                or current_checks[0].get("status") != "completed"
                or current_checks[0].get("conclusion") != "success"):
            raise RegistryError("AI_B_CI_STALE", "reviewed CI run is not the latest validation on exact head")
    else:
        _verify_historical_ci(api, repo, expected_head, run_id, evidence_before)
    ci_completed = _parse_utc(check.get("completed_at", ""))
    if not ci_completed < ai_time:
        raise RegistryError("AI_B_ORDER_INVALID", "GitHub CI must finish before AI report is posted")
    approval_time, approval = _owner_github_comment(
        comments, owner, genesis["approval_comment_marker"],
        missing_code="AI_B_OWNER_APPROVAL_MISSING", evidence_before=evidence_before,
    )
    expected_owner = {
        **common,
        "authorized_action": "APPROVE_DISCOVERY_REGISTRY_UPDATE",
        "approval_scope": "GOVERNANCE_REGISTRY_ONLY",
        "approval_profile": "SINGLE_OWNER_AI_R0_ATTESTED",
        "ai_review_comment_id": str(ai_comment["id"]),
        "ai_review_comment_sha256": _sha256(review_body.encode("utf-8")),
        "ci_check_run_id": str(run_id),
        "project_authority_effect": "NONE",
    }
    decision = _parse_owner_comment(approval["body"], genesis["approval_comment_marker"])
    if decision != expected_owner:
        raise RegistryError("AI_B_OWNER_APPROVAL_MISMATCH", "owner approval does not bind the exact AI and CI evidence")
    if ai_comment["id"] == approval["id"] or not ai_time < approval_time:
        raise RegistryError("AI_B_ORDER_INVALID", "AI attestation must precede separate owner approval")
    return PreMergeEvidence(
        pr_number=pr_number,
        candidate_head=expected_head,
        previous_index_commit=base_sha,
        index_sha256=index_sha,
        normalized_diff_sha256=diff_sha,
        changed_ids=changed_ids,
        independent_reviewer="NOT_APPLICABLE_B_NO_SECOND_GITHUB_ACTOR",
        independent_review_submitted_at="NOT_APPLICABLE_B_OWNER_POSTED_AI_ATTESTATION",
        owner_comment_id=approval["id"],
        owner_comment_created_at=approval_time.isoformat().replace("+00:00", "Z"),
        approval_profile="SINGLE_OWNER_AI_R0_ATTESTED",
        ai_review_comment_id=ai_comment["id"],
        ai_review_comment_sha256=_sha256(review_body.encode("utf-8")),
        ci_check_run_id=run_id,
    )


@dataclass(frozen=True)
class PostMergeEvidence:
    pre: PreMergeEvidence
    merge_commit: str
    first_parent: str

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.pre.as_dict(),
            "phase": "POST_MERGE",
            "merge_commit": self.merge_commit,
            "first_parent": self.first_parent,
            "verification_scope": "HISTORICAL_APPROVAL_ONLY",
            "current_health": "NOT_EVALUATED",
            "current_execution_authorized": False,
        }


def _validate_post_merge_core(
    api: Api,
    genesis: Mapping[str, Any],
    schema: Mapping[str, Any],
    pr_number: int,
    expected_head: str,
    expected_merge: str,
) -> PostMergeEvidence:
    if not SHA40_RE.fullmatch(expected_merge):
        raise RegistryError("MERGE_COMMIT_INVALID", "expected merge commit must be 40 lowercase hex")
    repository = genesis["governance_repository"]
    pr = api.get(_repo_endpoint(repository, f"pulls/{pr_number}"))
    if not pr.get("merged") or pr.get("merge_commit_sha") != expected_merge:
        raise RegistryError("MERGE_COMMIT_MISMATCH", "PR is not merged at expected commit")
    commit = api.get(_repo_endpoint(repository, f"commits/{expected_merge}"))
    parents = commit.get("parents", [])
    if not parents or not SHA40_RE.fullmatch(parents[0].get("sha", "")):
        raise RegistryError("FIRST_PARENT_MISMATCH", "actual merge first parent missing")
    historical_base = parents[0]["sha"]
    merged_at = _parse_utc(pr.get("merged_at", ""))
    pre = _validate_pre_merge_core(
        api, genesis, schema, pr_number, expected_head, historical_base=historical_base,
        evidence_before=merged_at,
    )
    approved_at = _parse_utc(pre.owner_comment_created_at)
    if not approved_at < merged_at:
        raise RegistryError("OWNER_APPROVAL_AFTER_MERGE", "approval must precede the actual GitHub merge")
    if parents[0].get("sha") != pre.previous_index_commit:
        raise RegistryError("FIRST_PARENT_MISMATCH", "merge first parent is not the approved previous index commit")
    merged_raw, _ = _content_bytes(api, repository, genesis["registry_path"], expected_merge)
    candidate_raw, _ = _content_bytes(api, repository, genesis["registry_path"], expected_head)
    if merged_raw != candidate_raw or _sha256(merged_raw) != pre.index_sha256:
        raise RegistryError("MERGED_INDEX_MISMATCH", "merged index raw bytes differ from approved candidate")
    return PostMergeEvidence(pre=pre, merge_commit=expected_merge, first_parent=parents[0]["sha"])


def validate_post_merge(
    api: Api, genesis: Mapping[str, Any], schema: Mapping[str, Any],
    pr_number: int, expected_head: str, expected_merge: str, *,
    expected_policy_commit: str | None = None,
) -> PostMergeEvidence:
    """Public post-merge check, bound to immutable tag and running policy bytes."""
    immutable_genesis = json.loads(_canonical_json(genesis))
    immutable_schema = json.loads(_canonical_json(schema))
    _require_release_policy_pin(api, immutable_genesis, immutable_schema, expected_policy_commit)
    return _validate_post_merge_core(
        api, immutable_genesis, immutable_schema, pr_number, expected_head, expected_merge,
    )


def _audit_first_parent_chain_core(
    api: Api, genesis: Mapping[str, Any], schema: Mapping[str, Any], head: str,
    *, trusted_release_commit: str,
) -> dict[str, Any]:
    if not SHA40_RE.fullmatch(head):
        raise RegistryError("INDEX_HEAD_INVALID", "index head must be 40 lowercase hex")
    if not SHA40_RE.fullmatch(trusted_release_commit):
        raise RegistryError("POLICY_PIN_REQUIRED", "internal chain walk requires validated immutable release commit")
    release_commit = trusted_release_commit
    repository = genesis["governance_repository"]
    cursor = head
    visited = 0
    changes: list[dict[str, Any]] = []
    while cursor != release_commit:
        visited += 1
        if visited > MAX_FIRST_PARENT_COMMITS:
            raise RegistryError("LINEAGE_TOO_LONG", "first-parent traversal exceeded bound")
        commit = api.get(_repo_endpoint(repository, f"commits/{cursor}"))
        parents = commit.get("parents", [])
        if not parents:
            raise RegistryError("GENESIS_NOT_ANCESTOR", "release genesis not found on first-parent chain")
        parent = parents[0].get("sha", "")
        current_raw, _ = _content_bytes(api, repository, genesis["registry_path"], cursor)
        parent_raw, _ = _content_bytes(api, repository, genesis["registry_path"], parent)
        if current_raw != parent_raw:
            associated = api.get(_repo_endpoint(repository, f"commits/{cursor}/pulls"))
            candidates = [
                pr for pr in associated
                if pr.get("merged_at") and pr.get("merge_commit_sha") == cursor
            ]
            if len(candidates) != 1:
                raise RegistryError("INDEX_CHANGE_PR_UNPROVEN", f"index change {cursor} lacks one exact merged PR")
            pr = candidates[0]
            evidence = _validate_post_merge_core(
                api, genesis, schema, int(pr["number"]), pr["head"]["sha"], cursor
            )
            changes.append(evidence.as_dict())
        cursor = parent
    genesis_raw, _ = _content_bytes(api, repository, genesis["registry_path"], release_commit)
    genesis_index = load_index_bytes(genesis_raw, schema)
    validate_genesis_index(genesis, genesis_index, genesis_raw)
    return {
        "status": "VERIFIED",
        "phase": "FIRST_PARENT_CHAIN",
        "head": head,
        "genesis_commit": release_commit,
        "commits_traversed": visited,
        "registry_changes": list(reversed(changes)),
    }


def audit_first_parent_chain(
    api: Api, genesis: Mapping[str, Any], schema: Mapping[str, Any],
    head: str, *, expected_policy_commit: str | None = None,
) -> dict[str, Any]:
    """Public chain audit rejects invented approval modes and unpinned policy."""
    immutable_genesis = json.loads(_canonical_json(genesis))
    immutable_schema = json.loads(_canonical_json(schema))
    trusted = _require_release_policy_pin(
        api, immutable_genesis, immutable_schema, expected_policy_commit,
    )
    return _audit_first_parent_chain_core(
        api, immutable_genesis, immutable_schema, head, trusted_release_commit=trusted,
    )


def reviewer_readiness(api: Api, genesis: Mapping[str, Any]) -> dict[str, Any]:
    """R0-only diagnostic; never invites users or modifies repository permissions."""
    repository = genesis["governance_repository"]
    owner = genesis["immutable_owner_account"]
    members = _pages(api, _repo_endpoint(repository, "collaborators"))
    candidates = []
    for item in members:
        user = item.get("login")
        permissions = item.get("permissions", {})
        role = item.get("role_name")
        if not user or user == owner:
            continue
        # GitHub review of a private repository needs an actually distinct account.
        # Do not treat an AI session running as the same owner as another actor.
        if (permissions.get("push") or permissions.get("admin") or
                permissions.get("maintain") or role in {"write", "maintain", "admin"}):
            candidates.append(user)
    candidates.sort()
    mode = genesis["registry_update_approval_mode"]
    proposed_b = mode == "SINGLE_OWNER_AI_R0_ATTESTED"
    return {
        "status": "HOLD" if proposed_b or not candidates else "CANDIDATES_PRESENT_NOT_APPROVED",
        "reason": (
            "B_CANDIDATE_REQUIRES_TAG_REPORT_CI_OWNER_APPROVAL_AND_MERGE_PROOF"
            if proposed_b else
            (None if candidates else "INDEPENDENT_GITHUB_REVIEWER_UNAVAILABLE")
        ),
        "registry_approval_mode": mode,
        "collaborator_count": len(members),
        "eligible_other_github_reviewers": candidates,
        "b_machine_verifier_available": proposed_b,
        "b_evidence_approved": False,
        "authorization_effect": "NONE",
        "fallback_approved": False,
        "note": (
            "B is an owner-posted AI review attestation, NOT an independent GitHub account "
            "or proof of independent AI authorship. A release tag and bound evidence are "
            "required for every registry update."
        ),
    }


def _registry_branch_head(api: Api, genesis: Mapping[str, Any]) -> str:
    repository = genesis["governance_repository"]
    branch = urllib.parse.quote(genesis["registry_branch"], safe="")
    response = api.get(_repo_endpoint(repository, f"git/ref/heads/{branch}"))
    head = response.get("object", {}).get("sha", "")
    if not SHA40_RE.fullmatch(head):
        raise RegistryError("INDEX_HEAD_INVALID", "registry branch head is missing or invalid")
    return head


def verify_policy_sources_from_immutable_commit(
    api: Api, genesis: Mapping[str, Any], schema: Mapping[str, Any],
    expected_policy_commit: str,
) -> None:
    """Bind the executing validator, schema and genesis to tagged policy bytes.

    The caller must already have checked the annotated Tag against an external
    exact Commit pin. This is not a claim that the unsigned tag is signed.
    """
    repo = genesis["governance_repository"]
    manifest_raw, _ = _content_bytes(api, repo, "MANIFEST.sha256", expected_policy_commit)
    try:
        lines = manifest_raw.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise RegistryError("RELEASE_MANIFEST_INVALID", "policy manifest is not ASCII") from exc
    manifest: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)", line)
        if not match:
            raise RegistryError("RELEASE_MANIFEST_INVALID", "invalid immutable policy manifest row")
        digest, path = match.groups()
        if path in manifest or path == "projects.yaml":
            raise RegistryError("RELEASE_MANIFEST_INVALID", "duplicate or dynamic index in immutable manifest")
        manifest[path] = digest
    # A policy tag is not trustworthy merely because its three executable
    # entry points hash correctly.  Check the *entire* immutable contract.
    missing = sorted(RELEASE_POLICY_FILESET - set(manifest))
    extra = sorted(set(manifest) - RELEASE_POLICY_FILESET)
    if missing or extra:
        raise RegistryError(
            "RELEASE_MANIFEST_FILESET_MISMATCH",
            "immutable release manifest must cover the complete fixed policy",
            missing=missing, extra=extra,
        )
    actual: dict[str, bytes] = {}
    for path in sorted(RELEASE_POLICY_FILESET):
        raw, _ = _content_bytes(api, repo, path, expected_policy_commit)
        if _sha256(raw) != manifest[path]:
            raise RegistryError("RELEASE_FILE_HASH_MISMATCH", "immutable policy file has wrong hash", path=path)
        actual[path] = raw
    try:
        remote_genesis = json.loads(actual["registry/GENESIS.json"])
        remote_schema = json.loads(actual["registry/projects.schema.json"])
        running_validator = Path(__file__).read_bytes()
    except (ValueError, UnicodeDecodeError, OSError) as exc:
        raise RegistryError("RELEASE_POLICY_INPUT_INVALID", "cannot compare running policy inputs") from exc
    if remote_genesis != genesis:
        raise RegistryError("GENESIS_POLICY_MISMATCH", "local genesis differs from immutable released genesis")
    if _canonical_json(remote_schema) != _canonical_json(schema):
        raise RegistryError("SCHEMA_POLICY_MISMATCH", "runtime schema differs from immutable released schema")
    if _sha256(running_validator) != manifest["registry/validate_registry.py"]:
        raise RegistryError("VALIDATOR_POLICY_MISMATCH", "running validator differs from tagged policy file")


def _audit_verified_registry_state(
    api: Api, genesis: Mapping[str, Any], schema: Mapping[str, Any],
    expected_policy_commit: str,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Rebuild an exact, live, verified index. Never return a reusable scan token."""
    if not SHA40_RE.fullmatch(expected_policy_commit):
        raise RegistryError("POLICY_PIN_REQUIRED", "exact external policy commit pin is required")
    genesis = json.loads(_canonical_json(genesis))
    schema = json.loads(_canonical_json(schema))
    policy_commit = resolve_release_commit(api, genesis)
    if policy_commit != expected_policy_commit:
        raise RegistryError("POLICY_PIN_MISMATCH", "tag target differs from trusted external pin")
    verify_policy_sources_from_immutable_commit(api, genesis, schema, policy_commit)

    observed: list[dict[str, str]] = []
    for attempt in (1, 2):
        start = _registry_branch_head(api, genesis)
        result = _audit_first_parent_chain_core(
            api, genesis, schema, start, trusted_release_commit=policy_commit,
        )
        raw, _ = _content_bytes(api, genesis["governance_repository"], genesis["registry_path"], start)
        index = load_index_bytes(raw, schema)
        end = _registry_branch_head(api, genesis)
        observed.append({"start": start, "end": end})
        if start == end:
            report = {
                **result, "phase": "MAIN_SNAPSHOT", "policy_commit": policy_commit,
                "index_sha256": _sha256(raw), "registry": build_report(index),
                "attempts": attempt, "head_observations": observed,
            }
            return report, index, start
    raise RegistryError(
        "REGISTRY_HEAD_DRIFT", "registry main drifted during both bounded attempts",
        head_observations=observed,
    )


def audit_main_snapshot(
    api: Api, genesis: Mapping[str, Any], schema: Mapping[str, Any],
    *, expected_policy_commit: str | None = None,
) -> dict[str, Any]:
    """Return an R0 evidence report, NEVER a reusable capability to scan projects."""
    report, _, _ = _audit_verified_registry_state(
        api, genesis, schema, expected_policy_commit or "",
    )
    return report


def _commit_tree(api: Api, repository: str, ref: str) -> tuple[str, str]:
    commit = api.get(_repo_endpoint(repository, f"commits/{urllib.parse.quote(ref, safe='')}"))
    sha = commit.get("sha", "")
    tree_sha = commit.get("commit", {}).get("tree", {}).get("sha", "")
    if not SHA40_RE.fullmatch(sha) or not SHA40_RE.fullmatch(tree_sha):
        raise RegistryError("PROJECT_COMMIT_INVALID", f"cannot resolve project ref {ref}")
    return sha, tree_sha


def verify_git_mode(api: Api, repository: str, tree_sha: str, path: str) -> dict[str, str]:
    current_tree = tree_sha
    pieces = path.split("/")
    for position, piece in enumerate(pieces):
        response = api.get(_repo_endpoint(repository, f"git/trees/{current_tree}"))
        if response.get("truncated"):
            raise RegistryError("PROJECT_TREE_TRUNCATED", f"Git tree response is truncated for {path}")
        matches = [entry for entry in response.get("tree", []) if entry.get("path") == piece]
        if len(matches) != 1:
            raise RegistryError("PROJECT_PATH_MISSING", f"cannot resolve {path}")
        entry = matches[0]
        last = position == len(pieces) - 1
        if last:
            if entry.get("type") != "blob" or entry.get("mode") not in ALLOWED_BLOB_MODES:
                raise RegistryError("PROJECT_PATH_UNSAFE_MODE", f"{path} is not a regular Git blob")
            return {"path": path, "mode": entry["mode"], "blob": entry.get("sha", "")}
        if entry.get("type") != "tree" or entry.get("mode") != "040000":
            raise RegistryError("PROJECT_PATH_UNSAFE_MODE", f"parent of {path} is not a Git tree")
        current_tree = entry.get("sha", "")
    raise RegistryError("PROJECT_PATH_MISSING", f"cannot resolve {path}")


def _scan_project_entry(
    api: Api, project_id: str, entry: Mapping[str, Any],
) -> dict[str, Any]:
    """Private implementation; caller owns a just-verified index in one transaction."""
    if entry["lifecycle"] != "active":
        return {"project_id": project_id, "read": "NOT_ATTEMPTED", "reason": "LIFECYCLE_NOT_ACTIVE"}
    if entry["registration"] != "verified":
        return {"project_id": project_id, "read": "BLOCKED", "reason": "REGISTRATION_UNVERIFIED"}
    repository = entry["repository"]
    successes: list[dict[str, str]] = []
    try:
        head_sha, head_tree = _commit_tree(api, repository, entry["authority_branch"])
        for path in (entry["ledger_path"], entry["project_rules_path"]):
            successes.append(verify_git_mode(api, repository, head_tree, path))
        contract_commit = entry["frozen_product_baseline"]["commit"]
        resolved_contract, contract_tree = _commit_tree(api, repository, contract_commit)
        if resolved_contract != contract_commit:
            raise RegistryError("CONTRACT_COMMIT_MISMATCH", "fixed contract ref did not resolve exactly")
        successes.append(verify_git_mode(api, repository, contract_tree, entry["frozen_product_baseline"]["path"]))
    except RegistryError as exc:
        unsafe = {"PROJECT_PATH_UNSAFE_MODE", "CONTRACT_COMMIT_MISMATCH", "PROJECT_TREE_TRUNCATED"}
        status = "BLOCKED" if exc.code in unsafe or not successes else "PARTIAL"
        return {
            "project_id": project_id,
            "read": status,
            "reason": exc.code,
            "verified_files": successes,
            "declared_next": "UNKNOWN",
            "inferred_governance_recommendation": "READ_ONLY_HOLD",
        }
    return {
        "project_id": project_id,
        "read": "VERIFIED",
        "project_head": head_sha,
        "verified_files": successes,
        "declared_next": "UNKNOWN_NOT_PARSED_BY_REGISTRY",
        "inferred_governance_recommendation": "READ_PROJECT_AUTHORITY_BEFORE_ANY_ACTION",
    }


def scan_authorized_main(
    api: Api, genesis: Mapping[str, Any], schema: Mapping[str, Any],
    *, expected_policy_commit: str, authorized_project_ids: Sequence[str],
) -> dict[str, Any]:
    """One complete audit→R0 scan transaction. No caller-supplied YAML or scan token.

    This is an application-level fail-closed boundary, not OS sandboxing:
    a Python process with the user's GitHub credentials can always issue its
    own API calls outside this library. The caller must independently hold R0
    authorization for every requested project; indexing grants no new rights.
    """
    if isinstance(authorized_project_ids, (str, bytes)) or not isinstance(authorized_project_ids, Sequence):
        raise RegistryError("SCAN_SCOPE_INVALID", "explicit authorized project IDs are required")
    project_ids = tuple(authorized_project_ids)
    if len(set(project_ids)) != len(project_ids) or not all(isinstance(p, str) for p in project_ids):
        raise RegistryError("SCAN_SCOPE_INVALID", "scan scope has duplicate or invalid project IDs")
    result, index, pinned_head = _audit_verified_registry_state(
        api, genesis, schema, expected_policy_commit,
    )
    projects = index["projects"]
    unknown = sorted(set(project_ids) - set(projects))
    if unknown:
        raise RegistryError("PROJECT_NOT_IN_VERIFIED_REGISTRY", "unregistered project cannot be scanned", ids=unknown)
    reads: list[dict[str, Any]] = []
    for project_id in project_ids:
        # Checking before AND after each item makes a snapshot unusable after
        # retirement, pause or any subsequent registry ref update.
        if _registry_branch_head(api, genesis) != pinned_head:
            raise RegistryError("REGISTRY_HEAD_DRIFT", "registry changed before project read; no results released")
        reads.append(_scan_project_entry(api, project_id, projects[project_id]))
        if _registry_branch_head(api, genesis) != pinned_head:
            raise RegistryError("REGISTRY_HEAD_DRIFT", "registry changed during project read; no results released")
    if _registry_branch_head(api, genesis) != pinned_head:
        raise RegistryError("REGISTRY_HEAD_DRIFT", "registry changed before scan result was returned")
    return {
        **result,
        "phase": "AUDITED_PROJECT_READ",
        "project_reads": reads,
        "registry": build_report(index, reads),
        "dispatch_authorized": False,
        "writer_change_authorized": False,
    }


def build_report(index: Mapping[str, Any], project_reads: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    projects = index["projects"]
    read_by_id: dict[str, Mapping[str, Any]] = {}
    for item in project_reads:
        project_id = item.get("project_id")
        if project_id not in projects:
            raise RegistryError("READ_PROJECT_UNKNOWN", f"read result has unknown project id: {project_id}")
        if project_id in read_by_id:
            raise RegistryError("READ_PROJECT_DUPLICATE", f"duplicate read result for {project_id}")
        if item.get("read") not in {"VERIFIED", "PARTIAL", "BLOCKED", "NOT_ATTEMPTED"}:
            raise RegistryError("READ_STATUS_INVALID", f"invalid read status for {project_id}")
        read_by_id[project_id] = item
    lifecycle = {key: 0 for key in ("active", "paused", "retired")}
    registration = {key: 0 for key in ("verified", "unverified")}
    read = {key: 0 for key in ("VERIFIED", "PARTIAL", "BLOCKED", "NOT_ATTEMPTED")}
    rows: list[dict[str, Any]] = []
    for project_id, entry in projects.items():
        lifecycle[entry["lifecycle"]] += 1
        registration[entry["registration"]] += 1
        result = read_by_id.get(project_id, {"project_id": project_id, "read": "NOT_ATTEMPTED"})
        read[result["read"]] += 1
        rows.append({
            "project_id": project_id,
            "lifecycle": entry["lifecycle"],
            "registration": entry["registration"],
            **result,
        })
    total = len(projects)
    if sum(lifecycle.values()) != total or sum(registration.values()) != total or sum(read.values()) != total:
        raise RegistryError("REPORT_TOTAL_MISMATCH", "report dimensions do not each sum to registry_total")
    return {
        "registry_total": total,
        "lifecycle": lifecycle,
        "registration": registration,
        "read": read,
        "projects": rows,
        "dispatch_authorized": False,
        "writer_change_authorized": False,
    }


def candidate_schema_precheck(
    genesis: Mapping[str, Any], index: Mapping[str, Any], raw: bytes,
) -> dict[str, Any]:
    """Local validation only: a later reviewed registry can differ from genesis.

    A green CI check has NO registration, R2, or approval effect.
    """
    initial = _sha256(raw) == genesis["initial_index_sha256"]
    if initial:
        validate_genesis_index(genesis, index, raw)
    # Never echo YAML's self-reported 'verified' as an effective registration.
    report_source = json.loads(_canonical_json(index))
    for entry in report_source["projects"].values():
        entry["registration"] = "unverified"
    return {
        "status": "SCHEMA_PRECHECK_PASS",
        "phase": "GENESIS_SCHEMA_PRECHECK" if initial else "DYNAMIC_SCHEMA_PRECHECK",
        "index_sha256": _sha256(raw),
        "approval_verified": False,
        "registry_trusted": False,
        "dispatch_authorized": False,
        "writer_change_authorized": False,
        "untrusted_registry_view": build_report(report_source),
    }


def _default_paths(root: Path) -> tuple[Path, Path, Path, Path]:
    return (
        root / "projects.yaml",
        root / "registry/projects.schema.json",
        root / "registry/GENESIS.json",
        root / "MANIFEST.sha256",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-local")
    sub.add_parser("validate-candidate")
    pre = sub.add_parser("pre-merge")
    pre.add_argument("--pr", type=int, required=True)
    pre.add_argument("--expected-head", required=True)
    pre.add_argument("--expected-policy-commit", required=True)
    post = sub.add_parser("post-merge")
    post.add_argument("--pr", type=int, required=True)
    post.add_argument("--expected-head", required=True)
    post.add_argument("--expected-merge", required=True)
    post.add_argument("--expected-policy-commit", required=True)
    chain = sub.add_parser("audit-chain")
    chain.add_argument("--head", required=True)
    chain.add_argument("--expected-policy-commit", required=True)
    audited = sub.add_parser("audit-main")
    audited.add_argument("--expected-policy-commit", required=True)
    sub.add_parser("reviewer-readiness")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    index_path, schema_path, genesis_path, manifest_path = _default_paths(root)
    try:
        schema = load_schema(schema_path)
        genesis = load_genesis(genesis_path)
        if args.command in {"validate-local", "validate-candidate"}:
            index, raw = load_index(index_path, schema)
            manifest = validate_manifest(root, manifest_path)
            capability_report = validate_capability_directory(root)
            if args.command == "validate-local":
                validate_genesis_index(genesis, index, raw)
                result: Mapping[str, Any] = {
                    "status": "VERIFIED",
                    "phase": "LOCAL_GENESIS",
                    "index_sha256": _sha256(raw),
                    "manifest_entries": len(manifest),
                    "capabilities": capability_report,
                    **build_report(index),
                }
            else:
                result = {
                    **candidate_schema_precheck(genesis, index, raw),
                    "manifest_entries": len(manifest),
                    "capabilities": capability_report,
                }
        else:
            api = GhApi()
            if args.command == "pre-merge":
                result = validate_pre_merge(
                    api, genesis, schema, args.pr, args.expected_head,
                    expected_policy_commit=args.expected_policy_commit,
                ).as_dict()
            elif args.command == "post-merge":
                result = validate_post_merge(
                    api, genesis, schema, args.pr, args.expected_head, args.expected_merge,
                    expected_policy_commit=args.expected_policy_commit,
                ).as_dict()
            elif args.command == "audit-chain":
                result = audit_first_parent_chain(
                    api, genesis, schema, args.head,
                    expected_policy_commit=args.expected_policy_commit,
                )
            elif args.command == "audit-main":
                result = audit_main_snapshot(
                    api, genesis, schema, expected_policy_commit=args.expected_policy_commit
                )
            else:
                result = reviewer_readiness(api, genesis)
    except (RegistryError, CapabilityError) as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if args.command == "reviewer-readiness" and result.get("status") == "HOLD":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
