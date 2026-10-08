"""Strict local validator for the S2 candidate capability definitions.

This module only reads the supplied local repository directory.  It has no
network, subprocess, tool-routing, import-discovery, or capability-execution
path.  A valid card remains disabled candidate data.
"""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker


CAPABILITY_DIRECTORY = "registry/capabilities"
SCHEMA_NAME = "capability-card.schema.json"
RELEASED_POLICY_COMMIT = "7aced01a8c12e1bba5e810ce91ab425f4615d4a7"
SOURCE_LOCK_PATH = "clients/chatgpt-plugin/skills/governance-bootstrap/references/source-lock.md"
MAX_CARD_BYTES = 32 * 1024
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SAFE_RELATIVE_RE = re.compile(r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$")


CAPABILITY_PROFILES: dict[str, dict[str, Any]] = {
    "codex.observe": {
        "filename": "codex.observe.json",
        "dependencies": ["tool.route"],
        "allowed_operations": [
            "read_existing_thread",
            "list_existing_threads",
            "report_runtime_unknown",
            "query_original_effect",
        ],
        "forbidden_operations": [
            "resume_thread",
            "start_thread",
            "start_turn",
            "retry_task",
            "dispatch_agent",
        ],
        "success_states": ["RUNTIME_VERIFIED", "RUNTIME_UNKNOWN"],
        "failure_states": [
            "AUTHORIZATION_BLOCKED",
            "EFFECT_UNKNOWN",
            "RISK_SCOPE_MISMATCH",
            "TOOL_UNAVAILABLE",
        ],
    },
    "project.restore": {
        "filename": "project.restore.json",
        "dependencies": ["tool.route"],
        "allowed_operations": [
            "read_authorized_project_sources",
            "read_same_head_ledger_and_rules",
            "separate_source_state_runtime",
            "report_declared_next_from_ledger_only",
        ],
        "forbidden_operations": [
            "adopt_project",
            "change_writer",
            "write_project",
            "invoke_runtime",
            "infer_declared_next",
        ],
        "success_states": ["SOURCE_VERIFIED", "STATE_RESTORED", "STATE_PARTIAL"],
        "failure_states": [
            "AUTHORIZATION_BLOCKED",
            "CAPABILITY_NOT_FOUND",
            "GLOBAL_R0_PARTIAL",
            "HASH_MISMATCH",
            "PATH_INVALID",
            "PROJECT_HEAD_DRIFT",
            "STATE_UNKNOWN",
        ],
    },
    "tool.route": {
        "filename": "tool.route.json",
        "dependencies": [],
        "allowed_operations": [
            "inspect_exposed_tool_metadata",
            "select_approved_adapter",
            "report_tool_unavailable",
            "select_read_only_effect_query",
        ],
        "forbidden_operations": [
            "connect_new_tool",
            "grant_permission",
            "bypass_refusal",
            "invoke_selected_tool",
            "dispatch_agent",
            "scan_unrelated_tools",
        ],
        "success_states": ["ROUTE_R0_READY"],
        "failure_states": [
            "AUTHORIZATION_BLOCKED",
            "CAPABILITY_UNAVAILABLE",
            "EFFECT_UNKNOWN",
            "TOOL_UNAVAILABLE",
        ],
    },
}


# These constraints are enforced by Python independently of the candidate
# JSON Schema. A modified schema may never grant a capability execution rights.
STATIC_CARD_FIELDS = frozenset({
    "schema_version", "capability_id", "capability_version", "status",
    "activation", "risk", "policy_lock", "dependencies", "contract",
})
STATIC_ACTIVATION = {
    "enabled": False, "invocation": "FORBIDDEN", "implementation": "NONE",
}
STATIC_RISK = {
    "class": "R0", "read_only": True,
    "state_change": "NONE", "side_effects": "FORBIDDEN",
}
STATIC_POLICY_LOCK = {
    "released_policy_version": "v0.2.0",
    "released_policy_commit": RELEASED_POLICY_COMMIT,
    "candidate_policy_version": "v0.2.1",
    "design_stage": "S2",
    "source_lock_path": SOURCE_LOCK_PATH,
}
STATIC_CONTRACT_FIELDS = frozenset({
    "purpose", "allowed_operations", "forbidden_operations",
    "success_states", "failure_states",
})


class CapabilityError(Exception):
    """Fail-closed validation error with a stable machine code."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        return {"status": "HOLD", "code": self.code, "message": self.message, **self.details}


def _exact_static_object(value: Any, expected: Mapping[str, Any], field: str) -> None:
    """Reject missing/extra fields and bool/int equivalence, even with a loose schema."""
    if type(value) is not dict or set(value) != set(expected):
        raise CapabilityError("CAPABILITY_SCHEMA_INVALID", f"{field} has unexpected fields")
    for key, required in expected.items():
        observed = value[key]
        if type(observed) is not type(required) or observed != required:
            raise CapabilityError("CAPABILITY_SCHEMA_INVALID", f"{field}.{key} violates immutable S2 contract")


def _validate_static_card(card: Mapping[str, Any], capability_id: str) -> None:
    """Out-of-schema, fail-closed immutable candidate contract."""
    if type(card) is not dict or set(card) != STATIC_CARD_FIELDS:
        raise CapabilityError("CAPABILITY_SCHEMA_INVALID", "card top-level keys are not fixed")
    for field, required in (
        ("schema_version", "1.0"),
        ("capability_version", "1.0.0"),
        ("status", "CANDIDATE_DEFINITION_ONLY"),
    ):
        if type(card[field]) is not str or card[field] != required:
            raise CapabilityError("CAPABILITY_SCHEMA_INVALID", f"{field} must remain fixed")
    if type(card["capability_id"]) is not str or card["capability_id"] != capability_id:
        raise CapabilityError("CAPABILITY_ID_MISMATCH", f"card identity mismatch: {capability_id}")
    _exact_static_object(card["activation"], STATIC_ACTIVATION, "activation")
    _exact_static_object(card["risk"], STATIC_RISK, "risk")
    _exact_static_object(card["policy_lock"], STATIC_POLICY_LOCK, "policy_lock")
    contract = card["contract"]
    if type(contract) is not dict or set(contract) != STATIC_CONTRACT_FIELDS:
        raise CapabilityError("CAPABILITY_SCHEMA_INVALID", "contract keys must remain fixed")
    purpose = contract["purpose"]
    if type(purpose) is not str or not 1 <= len(purpose) <= 240:
        raise CapabilityError("CAPABILITY_SCHEMA_INVALID", "contract purpose must be bounded text")
    for field in ("allowed_operations", "forbidden_operations", "success_states", "failure_states"):
        values = contract[field]
        if type(values) is not list or any(type(item) is not str for item in values):
            raise CapabilityError("CAPABILITY_SCHEMA_INVALID", f"contract.{field} must be string array")
    dependencies = card["dependencies"]
    if type(dependencies) is not list or any(type(item) is not str for item in dependencies):
        raise CapabilityError("CAPABILITY_SCHEMA_INVALID", "dependencies must be a string array")


def _reject_symlink_parents(root: Path, relative: str) -> None:
    """Check every intermediate component, not merely the final file/dir."""
    _validate_relative_path(relative, "capability path")
    current = root
    for part in PurePosixPath(relative).parts[:-1]:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise CapabilityError("PATH_INVALID", f"missing unsafe parent in {relative}") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise CapabilityError("PATH_INVALID", f"unsafe parent component in {relative}")


def _validate_relative_path(value: str, field: str) -> None:
    if not SAFE_RELATIVE_RE.fullmatch(value):
        raise CapabilityError("PATH_INVALID", f"{field} is not a literal repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CapabilityError("PATH_INVALID", f"{field} contains an unsafe segment")


def _safe_file(root: Path, relative: str) -> Path:
    _validate_relative_path(relative, "capability path")
    root = root.resolve()
    _reject_symlink_parents(root, relative)
    path = root.joinpath(*PurePosixPath(relative).parts)
    try:
        info = path.lstat()
    except OSError as exc:
        raise CapabilityError("CAPABILITY_FILE_MISSING", f"missing required file: {relative}") from exc
    if stat.S_ISLNK(info.st_mode):
        raise CapabilityError("PATH_INVALID", f"symbolic links are forbidden: {relative}")
    if not stat.S_ISREG(info.st_mode):
        raise CapabilityError("PATH_INVALID", f"required path is not a regular file: {relative}")
    if info.st_mode & 0o111:
        raise CapabilityError("EXECUTABLE_FILE_FORBIDDEN", f"capability data must not be executable: {relative}")
    try:
        path.resolve().relative_to(root)
    except (OSError, ValueError) as exc:
        raise CapabilityError("PATH_INVALID", f"path escapes repository root: {relative}") from exc
    return path


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CapabilityError("JSON_DUPLICATE_KEY", f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json_file(path: Path, *, max_bytes: int = MAX_CARD_BYTES) -> Mapping[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CapabilityError("CAPABILITY_FILE_UNREADABLE", f"cannot read {path.name}") from exc
    if len(raw) > max_bytes:
        raise CapabilityError("CAPABILITY_FILE_TOO_LARGE", f"{path.name} exceeds {max_bytes} bytes")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise CapabilityError("UTF8_BOM_FORBIDDEN", f"UTF-8 BOM is forbidden: {path.name}")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CapabilityError("UTF8_INVALID", f"invalid UTF-8: {path.name}") from exc
    if CONTROL_RE.search(text):
        raise CapabilityError("CONTROL_CHARACTER", f"forbidden control character: {path.name}")
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
    except CapabilityError:
        raise
    except json.JSONDecodeError as exc:
        raise CapabilityError("JSON_INVALID", f"invalid JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise CapabilityError("JSON_ROOT_INVALID", f"JSON root must be an object: {path.name}")
    return value


def _load_schema(path: Path) -> Mapping[str, Any]:
    schema = _load_json_file(path, max_bytes=64 * 1024)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise CapabilityError("CAPABILITY_SCHEMA_INVALID", "capability schema is invalid") from exc
    return schema


def _schema_errors(schema: Mapping[str, Any], value: Mapping[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path))
    return [
        f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
        for error in errors
    ]


def _validate_source_lock(root: Path, cards: Mapping[str, Mapping[str, Any]]) -> None:
    source_path = _safe_file(root, SOURCE_LOCK_PATH)
    try:
        text = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CapabilityError("SOURCE_LOCK_UNREADABLE", "cannot read the preserved source lock") from exc
    expected_line = f"- policy_commit: {RELEASED_POLICY_COMMIT}"
    if text.count(expected_line) != 1:
        raise CapabilityError("SOURCE_LOCK_MISMATCH", "source lock does not contain the exact released policy commit")
    for capability_id, card in cards.items():
        lock = card["policy_lock"]
        if lock["source_lock_path"] != SOURCE_LOCK_PATH or lock["released_policy_commit"] != RELEASED_POLICY_COMMIT:
            raise CapabilityError("VERSION_LOCK_MISMATCH", f"version lock mismatch: {capability_id}")


def dependency_closure(cards: Mapping[str, Mapping[str, Any]], requested: Sequence[str]) -> list[str]:
    """Return a deterministic dependency-first closure or fail closed."""

    if len(set(requested)) != len(requested):
        raise CapabilityError("DUPLICATE_CAPABILITY_REQUEST", "requested capabilities contain duplicates")
    visiting: set[str] = set()
    visited: set[str] = set()
    ordered: list[str] = []

    def visit(capability_id: str) -> None:
        if capability_id not in cards:
            raise CapabilityError("CAPABILITY_NOT_FOUND", f"unknown capability: {capability_id}")
        if capability_id in visiting:
            raise CapabilityError("DEPENDENCY_CYCLE", f"dependency cycle includes {capability_id}")
        if capability_id in visited:
            return
        visiting.add(capability_id)
        dependencies = cards[capability_id].get("dependencies")
        if not isinstance(dependencies, list):
            raise CapabilityError("CAPABILITY_SCHEMA_INVALID", f"dependencies are invalid: {capability_id}")
        for dependency in sorted(dependencies):
            visit(dependency)
        visiting.remove(capability_id)
        visited.add(capability_id)
        ordered.append(capability_id)

    for capability_id in sorted(requested):
        visit(capability_id)
    return ordered


def validate_capability_directory(root: Path) -> dict[str, Any]:
    """Validate only the fixed local S2 directory and return inert metadata."""

    root = root.resolve()
    _reject_symlink_parents(root, CAPABILITY_DIRECTORY)
    directory = root / CAPABILITY_DIRECTORY
    try:
        directory_info = directory.lstat()
    except OSError as exc:
        raise CapabilityError("CAPABILITY_DIRECTORY_MISSING", "capability directory is missing") from exc
    if stat.S_ISLNK(directory_info.st_mode) or not stat.S_ISDIR(directory_info.st_mode):
        raise CapabilityError("PATH_INVALID", "capability directory must be a real local directory")

    expected_names = {SCHEMA_NAME} | {profile["filename"] for profile in CAPABILITY_PROFILES.values()}
    try:
        actual_names = {entry.name for entry in os.scandir(directory)}
    except OSError as exc:
        raise CapabilityError("CAPABILITY_DIRECTORY_UNREADABLE", "cannot list capability directory") from exc
    if actual_names != expected_names:
        raise CapabilityError(
            "CAPABILITY_DIRECTORY_INVALID",
            "capability directory must contain only the fixed schema and three cards",
            missing=sorted(expected_names - actual_names),
            extra=sorted(actual_names - expected_names),
        )

    schema_path = _safe_file(root, f"{CAPABILITY_DIRECTORY}/{SCHEMA_NAME}")
    schema = _load_schema(schema_path)
    cards: dict[str, Mapping[str, Any]] = {}
    for capability_id, profile in sorted(CAPABILITY_PROFILES.items()):
        relative = f"{CAPABILITY_DIRECTORY}/{profile['filename']}"
        card = _load_json_file(_safe_file(root, relative))
        _validate_static_card(card, capability_id)
        errors = _schema_errors(schema, card)
        if errors:
            raise CapabilityError(
                "CAPABILITY_SCHEMA_INVALID",
                f"card does not match schema: {profile['filename']}",
                errors=errors,
            )
        if card["capability_id"] != capability_id:
            raise CapabilityError("CAPABILITY_ID_MISMATCH", f"card identity mismatch: {profile['filename']}")
        cards[capability_id] = card

    _validate_source_lock(root, cards)
    closure = dependency_closure(cards, sorted(cards))
    if set(closure) != set(CAPABILITY_PROFILES):
        raise CapabilityError("DEPENDENCY_CLOSURE_INVALID", "capability closure is incomplete")

    for capability_id, profile in sorted(CAPABILITY_PROFILES.items()):
        card = cards[capability_id]
        for field in (
            "dependencies",
            "allowed_operations",
            "forbidden_operations",
            "success_states",
            "failure_states",
        ):
            actual = card[field] if field == "dependencies" else card["contract"][field]
            if actual != profile[field]:
                code = "DEPENDENCY_CONTRACT_MISMATCH" if field == "dependencies" else "RISK_SCOPE_MISMATCH"
                raise CapabilityError(code, f"fixed capability contract mismatch: {capability_id}.{field}")
    return {
        "status": "CAPABILITY_CANDIDATE_VALID",
        "activation": "DISABLED",
        "capability_count": len(cards),
        "capability_ids": sorted(cards),
        "dependency_order": closure,
        "policy_commit": RELEASED_POLICY_COMMIT,
        "tool_calls": 0,
        "side_effects": 0,
    }
