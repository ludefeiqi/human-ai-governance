from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
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
        "registry_update_approval_mode": "EXTERNAL_GITHUB_REVIEW",
        "ai_review_comment_marker": "HAGOV-AI-R0-ATTESTATION-V1",
        "unreleased_behavior": "HOLD_V0_1_SEMANTICS",
    }


def mock_released_policy_routes(routes: dict, repository: str, release: str, genesis: dict) -> None:
    """Synthetic tagged policy blobs; all expected hashes use actual test checkout bytes."""
    from registry.validate_registry import RELEASE_POLICY_FILESET
    source = {
        path: (json.dumps(genesis).encode("utf-8") if path == "registry/GENESIS.json"
               else Path(path).read_bytes())
        for path in sorted(RELEASE_POLICY_FILESET)
    }
    for path, payload in source.items():
        routes[(f"repos/{repository}/contents/{path}", (("ref", release),))] = content(payload)
    manifest = "".join(
        f"{hashlib.sha256(raw).hexdigest()}  {path}\\n"
        for path, raw in sorted(source.items())
    ).replace("\\n", "\n")
    routes[(f"repos/{repository}/contents/MANIFEST.sha256", (("ref", release),))] = content(
        manifest.encode("ascii")
    )
    # Immutable release Git tree is a separate source of file mode evidence.
    tree_sha = "9" * 40
    routes[f"repos/{repository}/commits/{release}"] = {
        "sha": release, "commit": {"tree": {"sha": tree_sha}}, "parents": [],
    }
    routes[(f"repos/{repository}/git/trees/{tree_sha}", (("recursive", "1"),))] = {
        "truncated": False,
        "tree": [
            {"path": path, "type": "blob", "mode": "100644", "sha": "d" * 40}
            for path in sorted(set(source) | {"MANIFEST.sha256"})
        ],
    }
