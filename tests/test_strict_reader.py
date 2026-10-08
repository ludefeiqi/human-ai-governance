from __future__ import annotations

import copy
import json

import pytest

from registry.validate_registry import (
    MAX_INDEX_BYTES,
    RegistryError,
    identity_hash,
    load_index_bytes,
    load_schema,
)
from tests.helpers import SHA_A, dump, index, project


@pytest.fixture(scope="module")
def schema():
    from pathlib import Path

    return load_schema(Path("registry/projects.schema.json"))


def assert_code(schema, raw: bytes, code: str) -> None:
    with pytest.raises(RegistryError) as caught:
        load_index_bytes(raw, schema)
    assert caught.value.code == code


def test_valid_minimal_index(schema):
    parsed = load_index_bytes(dump(index()), schema)
    assert parsed["projects"]["alpha"]["registration"] == "verified"


def test_valid_retired_tombstone(schema):
    value = index()
    value["projects"]["alpha"]["lifecycle"] = "retired"
    value["projects"]["alpha"]["lifecycle_history"] = [
        {"lifecycle": "retired", "changed_at": "2026-10-08T00:00:00Z", "previous_index_commit": SHA_A}
    ]
    assert load_index_bytes(dump(value), schema)["projects"]["alpha"]["lifecycle"] == "retired"


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b"schema_version: '0.2'\nschema_version: '0.2'\n", "YAML_DUPLICATE_KEY"),
        (b"a: &x 1\nb: 2\n", "YAML_ANCHOR"),
        (b"a: 1\nb: *x\n", "YAML_ALIAS"),
        (b"a: !thing value\n", "YAML_TAG"),
        (b"%YAML 1.2\n---\na: b\n", "YAML_DIRECTIVE"),
        (b"1: value\n", "YAML_NON_STRING_KEY"),
        (b"true: value\n", "YAML_NON_STRING_KEY"),
        (b"base: &base\n  x: y\nitem:\n  <<: *base\n", "YAML_ANCHOR"),
        (b"item:\n  <<: value\n", "YAML_MERGE_KEY"),
        (b"\xff\xfe", "UTF8_INVALID"),
        (b"\xef\xbb\xbfschema_version: x\n", "UTF8_BOM_FORBIDDEN"),
        (b"schema_version: \x00\n", "CONTROL_CHARACTER"),
        (b"schema_version: \x1b\n", "CONTROL_CHARACTER"),
        (b"", "YAML_EMPTY"),
        (b"---\na: b\n---\nc: d\n", "YAML_INVALID"),
        (b"x: [unterminated\n", "YAML_INVALID"),
        (b"a: \"" + b"x" * (16 * 1024 + 1) + b"\"\n", "YAML_SCALAR_TOO_LARGE"),
        (b"x" * (MAX_INDEX_BYTES + 1), "INDEX_TOO_LARGE"),
    ],
)
def test_rejects_hostile_yaml(schema, raw, code):
    assert_code(schema, raw, code)


def test_rejects_too_deep(schema):
    lines = ["  " * depth + "a:" for depth in range(30)]
    lines.append("  " * 30 + "z: value")
    raw = ("\n".join(lines) + "\n").encode()
    assert_code(schema, raw, "YAML_TOO_DEEP")


@pytest.mark.parametrize(
    ("repository", "valid"),
    [
        ("owner/repo", True),
        ("o/r", True),
        ("owner", False),
        ("owner/repo/extra", False),
        ("-owner/repo", False),
        ("owner-/repo", False),
        ("owner/repo.git", False),
        ("owner/..", False),
        ("https://github.com/owner/repo", False),
        ("owner/re po", False),
    ],
)
def test_repository_validation(schema, repository, valid):
    value = index()
    value["projects"]["alpha"]["repository"] = repository
    value["projects"]["alpha"]["identity"]["identity_hash"] = identity_hash("alpha", repository)
    if valid:
        load_index_bytes(dump(value), schema)
    else:
        assert_code(schema, dump(value), "REPOSITORY_INVALID")


@pytest.mark.parametrize(
    "path",
    [
        "/etc/passwd",
        "../LEDGER.md",
        "docs/../LEDGER.md",
        "docs//LEDGER.md",
        "./LEDGER.md",
        "~/LEDGER.md",
        "docs\\LEDGER.md",
        "docs/*.md",
        "docs/file?.md",
        "file://docs/LEDGER.md",
        "docs/LEDGER.md?token=x",
        "docs/secrets/value.md",
        ".git/config",
        "logs/output.txt",
    ],
)
def test_rejects_unsafe_paths(schema, path):
    value = index()
    value["projects"]["alpha"]["ledger_path"] = path
    assert_code(schema, dump(value), "PATH_INVALID" if path not in {"docs/secrets/value.md", ".git/config", "logs/output.txt"} else "PATH_SENSITIVE")


@pytest.mark.parametrize(
    "branch",
    ["-main", ".main", "/main", "main/", "main..next", "main@{1}", "a//b", "a b", "a~b", "a^b", "a:b", "a?b", "a*b", "a[b", "a\\b", "a.lock"],
)
def test_rejects_unsafe_branches(schema, branch):
    value = index()
    value["projects"]["alpha"]["authority_branch"] = branch
    assert_code(schema, dump(value), "BRANCH_INVALID")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda v: v.update({"unknown": True}), "SCHEMA_INVALID"),
        (lambda v: v["projects"]["alpha"].update({"unknown": True}), "SCHEMA_INVALID"),
        (lambda v: v.update({"schema_version": 0.2}), "SCHEMA_INVALID"),
        (lambda v: v.update({"registry_state": "published"}), "SCHEMA_INVALID"),
        (lambda v: v["projects"]["alpha"].update({"dispatch_enabled": True}), "SCHEMA_INVALID"),
        (lambda v: v["projects"]["alpha"].update({"governance_adoption": "adopted"}), "SCHEMA_INVALID"),
        (lambda v: v["projects"]["alpha"].update({"writer_source": "registry"}), "SCHEMA_INVALID"),
        (lambda v: v["projects"]["alpha"].update({"issue_root": "1"}), "SCHEMA_INVALID"),
        (lambda v: v["projects"]["alpha"]["identity"].update({"canonical_id": "beta"}), "IDENTITY_ID_MISMATCH"),
        (lambda v: v["projects"]["alpha"]["identity"].update({"identity_hash": "sha256:" + "0" * 64}), "IDENTITY_HASH_MISMATCH"),
        (lambda v: v["projects"]["alpha"].update({"lifecycle": "retired"}), "TOMBSTONE_HISTORY_MISSING"),
        (lambda v: v["projects"]["alpha"].update({"registration": "maybe"}), "SCHEMA_INVALID"),
    ],
)
def test_rejects_schema_and_semantic_drift(schema, mutation, code):
    value = index()
    mutation(value)
    assert_code(schema, dump(value), code)


def test_rejects_duplicate_nested_key(schema):
    raw = dump(index()).replace(b"    display_name: Alpha\n", b"    display_name: Alpha\n    display_name: Again\n")
    assert_code(schema, raw, "YAML_DUPLICATE_KEY")


def test_rejects_history_reversal(schema):
    value = index()
    entry = value["projects"]["alpha"]
    entry["lifecycle"] = "active"
    entry["lifecycle_history"] = [
        {"lifecycle": "paused", "changed_at": "2026-10-09T00:00:00Z", "previous_index_commit": SHA_A},
        {"lifecycle": "active", "changed_at": "2026-10-08T00:00:00Z", "previous_index_commit": "b" * 40},
    ]
    assert_code(schema, dump(value), "HISTORY_ORDER_INVALID")


def test_rejects_latest_history_state_mismatch(schema):
    value = index()
    value["projects"]["alpha"]["lifecycle_history"] = [
        {"lifecycle": "paused", "changed_at": "2026-10-08T00:00:00Z", "previous_index_commit": SHA_A}
    ]
    assert_code(schema, dump(value), "HISTORY_STATE_MISMATCH")


def test_identity_hash_is_canonical():
    assert identity_hash("alpha", "owner/repo") == identity_hash("alpha", "owner/repo")
    assert identity_hash("alpha", "owner/repo") != identity_hash("beta", "owner/repo")
