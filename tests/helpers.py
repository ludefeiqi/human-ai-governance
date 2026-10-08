from __future__ import annotations

import base64
import copy
from typing import Any, Mapping

import yaml

from registry.validate_registry import identity_hash


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40
TREE_A = "1" * 40
TREE_B = "2" * 40


def project(project_id: str = "alpha", repository: str = "owner/repo") -> dict[str, Any]:
    return {
        "display_name": "Alpha",
        "repository": repository,
        "authority_branch": "main",
        "ledger_path": "docs/LEDGER.md",
        "project_rules_path": "AGENTS.md",
        "issue_root": 1,
        "frozen_product_baseline": {"path": "docs/BASELINE.md", "commit": SHA_C},
        "governance_adoption": "reference_only",
        "dispatch_enabled": False,
        "writer_source": "current_project_ledger_only",
        "latest_project_head": "read_remote_at_use_time",
        "lifecycle": "active",
        "registration": "verified",
        "identity": {
            "canonical_id": project_id,
            "identity_hash": identity_hash(project_id, repository),
        },
        "lifecycle_history": [],
        "registration_provenance": {
            "kind": "carried_from_v0.1.0",
            "policy_commit": SHA_A,
        },
        "notes": "Discovery only.",
    }


def index(projects: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "0.2",
        "registry_state": "controlled_dynamic_index",
        "registry_policy": "v0.2.0",
        "registry_mode": "discovery_only",
        "projects": copy.deepcopy(dict(projects or {"alpha": project()})),
    }


def dump(value: Any) -> bytes:
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True).encode("utf-8")


def content(raw: bytes, blob: str = SHA_D) -> dict[str, Any]:
    return {
        "type": "file",
        "encoding": "base64",
        "content": base64.encodebytes(raw).decode("ascii"),
        "sha": blob,
    }


class FakeApi:
    def __init__(self, routes: Mapping[Any, Any]) -> None:
        self.routes = dict(routes)
        self.calls: list[tuple[str, tuple[tuple[str, str], ...]]] = []

    def get(self, endpoint: str, fields: Mapping[str, str] | None = None) -> Any:
        field_tuple = tuple(sorted((fields or {}).items()))
        self.calls.append((endpoint, field_tuple))
        key = (endpoint, field_tuple)
        if key in self.routes:
            return copy.deepcopy(self.routes[key])
        if endpoint in self.routes:
            return copy.deepcopy(self.routes[endpoint])
        raise AssertionError(f"unexpected GET {endpoint} {dict(field_tuple)}")


def active_genesis() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "ACTIVATES_ONLY_AFTER_VERIFIED_RELEASE_TAG",
        "governance_repository": "owner/governance",
        "immutable_owner_account": "owner",
        "release_tag": "v0.2.0",
        "release_commit_source": "dereferenced_annotated_tag",
        "registry_branch": "main",
        "registry_path": "projects.yaml",
        "initial_index_sha256": "0" * 64,
        "initial_project_identity_hashes": {},
        "approval_comment_marker": "HAGOV-REGISTRY-OWNER-APPROVAL-V1",
        "unreleased_behavior": "HOLD_V0_1_SEMANTICS",
    }
