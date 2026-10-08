"""Deterministic, local-only loader for the candidate capability catalog.

This module verifies only the externally pinned catalog -> selected domain ->
selected capability dependency closure.  It is not a policy verifier and it
never grants dispatch, writer, tool, or other authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, TypedDict

from jsonschema import Draft202012Validator


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
INTENT_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")

HARD_BUDGETS = {
    "max_schema_bytes": 16 * 1024,
    "max_root_bytes": 16 * 1024,
    "max_domain_bytes": 32 * 1024,
    "max_pack_bytes": 24 * 1024,
    "max_total_bytes": 80 * 1024,
    "max_dependencies": 8,
    "max_depth": 8,
}


class RouterError(Exception):
    """Fail-closed routing error with a stable machine-readable code."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        return {"status": "HOLD", "code": self.code, "message": self.message, **self.details}


class LoadedModule(TypedDict):
    capability_id: str
    path: str
    sha256: str
    module_text: str
    requires: list[str]
    required_tools: list[str]


class RouteResult(TypedDict):
    status: str
    verification_level: str
    policy_verified: bool
    authority_effect: str
    dispatch_authorized: bool
    writer_change_authorized: bool
    tools_checked: bool
    candidate_only: bool
    intent: str
    domain_id: str
    selected_capability_id: str
    capability_ids: list[str]
    loaded_paths: list[str]
    raw_bytes: int
    modules: list[LoadedModule]
    required_tools: list[str]
    required_tools_status: str


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise RouterError("JSON_DUPLICATE_KEY", f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _parse_json(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_duplicate_rejecting_object)
    except RouterError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RouterError("JSON_INVALID", f"{label} is not strict UTF-8 JSON") from exc


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _budgets(overrides: Mapping[str, int] | None) -> dict[str, int]:
    result = dict(HARD_BUDGETS)
    if overrides is None:
        return result
    if not isinstance(overrides, Mapping):
        raise RouterError("BUDGET_INVALID", "budgets must be a mapping")
    unknown = set(overrides) - set(HARD_BUDGETS)
    if unknown:
        raise RouterError("BUDGET_UNKNOWN", "unknown budget keys", keys=sorted(unknown))
    for key, value in overrides.items():
        if type(value) is not int or value <= 0 or value > HARD_BUDGETS[key]:
            raise RouterError(
                "BUDGET_INVALID",
                f"{key} must be a positive integer no greater than the hard limit",
            )
        result[key] = value
    return result


def _safe_file(root: Path, relative: str, *, area: str, suffix: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise RouterError("PATH_INVALID", "path must be a non-empty literal POSIX path")
    pure = PurePosixPath(relative)
    parts = relative.split("/")
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise RouterError("PATH_INVALID", "path must be canonical and repository-relative")
    if tuple(pure.parts[:2]) != ("capabilities", area) or pure.suffix != suffix:
        raise RouterError("PATH_SCOPE_INVALID", f"path must be under capabilities/{area} with {suffix} suffix")
    if len(pure.parts) != 3:
        raise RouterError("PATH_SCOPE_INVALID", "capability paths must have exactly three components")

    current = root
    for part in pure.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise RouterError("FILE_MISSING", f"required file is unavailable: {relative}") from exc
        if stat.S_ISLNK(mode):
            raise RouterError("SYMLINK_FORBIDDEN", f"symlink component is forbidden: {relative}")
    if not stat.S_ISREG(current.lstat().st_mode):
        raise RouterError("FILE_TYPE_INVALID", f"required path is not a regular file: {relative}")
    return current


def _fixed_file(root: Path, relative: str) -> Path:
    """Resolve a fixed loader input while rejecting symlinks below root."""
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise RouterError("FILE_MISSING", f"required file is unavailable: {relative}") from exc
        if stat.S_ISLNK(mode):
            raise RouterError("SYMLINK_FORBIDDEN", f"symlink component is forbidden: {relative}")
    if not stat.S_ISREG(current.lstat().st_mode):
        raise RouterError("FILE_TYPE_INVALID", f"required path is not a regular file: {relative}")
    return current


def _read_bounded(path: Path, relative: str, limit: int) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise RouterError("FILE_UNREADABLE", f"cannot stat required file: {relative}") from exc
    if size > limit:
        raise RouterError("FILE_TOO_LARGE", f"{relative} exceeds its byte budget", limit=limit)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RouterError("FILE_UNREADABLE", f"cannot read required file: {relative}") from exc
    if len(raw) > limit:
        raise RouterError("FILE_TOO_LARGE", f"{relative} exceeds its byte budget", limit=limit)
    return raw


def _validate(schema: Mapping[str, Any], definition: str, value: Any) -> None:
    try:
        validator_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{definition}",
        }
        errors = sorted(
            Draft202012Validator(validator_schema).iter_errors(value),
            key=lambda error: list(error.absolute_path),
        )
    except (KeyError, TypeError) as exc:
        raise RouterError("SCHEMA_INVALID", "catalog schema does not expose required definitions") from exc
    if errors:
        error = errors[0]
        path = "/".join(str(part) for part in error.absolute_path)
        code = "DOMAIN_SCHEMA_INVALID" if definition == "Domain" else "ROOT_SCHEMA_INVALID"
        raise RouterError(code, f"{definition} schema validation failed at /{path}: {error.message}")


def _unique(items: list[Mapping[str, Any]], key: str, code: str) -> None:
    seen: set[str] = set()
    for item in items:
        value = item[key]
        if value in seen:
            raise RouterError(code, f"duplicate {key}: {value}")
        seen.add(value)


def route_capability(
    root: Path,
    intent: str,
    expected_catalog_sha256: str,
    budgets: Mapping[str, int] | None = None,
) -> RouteResult:
    """Load one exact intent and its same-domain R0 dependency closure.

    The returned structure is static evidence only.  ``required_tools`` is a
    declaration copied from the selected metadata and is never probed.
    """
    limits = _budgets(budgets)
    if not isinstance(root, Path):
        raise RouterError("ROOT_INVALID", "root must be pathlib.Path")
    try:
        root_mode = root.lstat().st_mode
    except OSError as exc:
        raise RouterError("ROOT_INVALID", "root directory is unavailable") from exc
    if stat.S_ISLNK(root_mode) or not stat.S_ISDIR(root_mode):
        raise RouterError("ROOT_INVALID", "root must be a real directory, not a symlink")
    if not isinstance(intent, str) or not INTENT_RE.fullmatch(intent):
        raise RouterError("INTENT_INVALID", "intent must be an exact declared identifier")
    if not isinstance(expected_catalog_sha256, str) or not SHA256_RE.fullmatch(expected_catalog_sha256):
        raise RouterError("CATALOG_PIN_REQUIRED", "an external lowercase 64-hex catalog SHA256 pin is required")

    loaded_paths: list[str] = []
    raw_total = 0

    def account(relative: str, raw: bytes) -> None:
        nonlocal raw_total
        raw_total += len(raw)
        if raw_total > limits["max_total_bytes"]:
            raise RouterError("TOTAL_BYTES_EXCEEDED", "loaded raw bytes exceed the total budget")
        loaded_paths.append(relative)

    schema_relative = "capabilities/catalog.schema.json"
    schema_raw = _read_bounded(
        _fixed_file(root, schema_relative), schema_relative, limits["max_schema_bytes"]
    )
    account(schema_relative, schema_raw)
    schema = _parse_json(schema_raw, "catalog schema")
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise RouterError("SCHEMA_INVALID", "catalog schema is not valid Draft 2020-12") from exc

    catalog_relative = "capabilities/catalog.json"
    catalog_raw = _read_bounded(
        _fixed_file(root, catalog_relative), catalog_relative, limits["max_root_bytes"]
    )
    account(catalog_relative, catalog_raw)
    if _sha256(catalog_raw) != expected_catalog_sha256:
        raise RouterError("CATALOG_PIN_MISMATCH", "catalog raw-byte SHA256 does not match external pin")
    catalog = _parse_json(catalog_raw, "catalog")
    _validate(schema, "Root", catalog)

    domains = catalog["domains"]
    _unique(domains, "id", "DUPLICATE_DOMAIN_ID")
    root_intents: dict[str, list[Mapping[str, Any]]] = {}
    for summary in domains:
        for declared in summary["intents"]:
            root_intents.setdefault(declared, []).append(summary)
    duplicate_root_intents = sorted(key for key, values in root_intents.items() if len(values) != 1)
    if duplicate_root_intents:
        raise RouterError("AMBIGUOUS_ROOT_INTENT", "root intent is declared by multiple domains", intents=duplicate_root_intents)
    matches = root_intents.get(intent, [])
    if not matches:
        raise RouterError("INTENT_UNKNOWN", "intent is not declared by the pinned catalog")
    summary = matches[0]

    domain_relative = summary["manifest_path"]
    domain_raw = _read_bounded(
        _safe_file(root, domain_relative, area="domains", suffix=".json"),
        domain_relative,
        limits["max_domain_bytes"],
    )
    account(domain_relative, domain_raw)
    if _sha256(domain_raw) != summary["sha256"]:
        raise RouterError("DOMAIN_HASH_MISMATCH", "domain raw-byte SHA256 does not match catalog")
    domain = _parse_json(domain_raw, "domain")
    _validate(schema, "Domain", domain)
    if domain["domain_id"] != summary["id"]:
        raise RouterError("DOMAIN_ID_MISMATCH", "domain identity does not match root summary")

    capabilities = domain["capabilities"]
    _unique(capabilities, "id", "DUPLICATE_CAPABILITY_ID")
    domain_intents: dict[str, list[Mapping[str, Any]]] = {}
    by_id: dict[str, Mapping[str, Any]] = {}
    for capability in capabilities:
        by_id[capability["id"]] = capability
        if capability["risk_class"] != "R0":
            raise RouterError("RISK_CLASS_FORBIDDEN", "only R0 capability metadata may be loaded")
        if capability["side_effects"] is not False:
            raise RouterError("SIDE_EFFECTS_FORBIDDEN", "capabilities with side effects are forbidden")
        for declared in capability["intents"]:
            domain_intents.setdefault(declared, []).append(capability)
    duplicate_domain_intents = sorted(key for key, values in domain_intents.items() if len(values) != 1)
    if duplicate_domain_intents:
        raise RouterError("AMBIGUOUS_DOMAIN_INTENT", "domain intent maps to multiple capabilities", intents=duplicate_domain_intents)
    if set(domain_intents) != set(summary["intents"]):
        raise RouterError("DOMAIN_INTENTS_MISMATCH", "domain intents do not exactly match the root summary")
    selected_matches = domain_intents.get(intent, [])
    if len(selected_matches) != 1:
        raise RouterError("INTENT_NOT_UNIQUE", "intent does not select exactly one capability")
    selected = selected_matches[0]

    ordered: list[Mapping[str, Any]] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(capability_id: str, depth: int) -> None:
        if depth > limits["max_depth"]:
            raise RouterError("DEPENDENCY_DEPTH_EXCEEDED", "capability dependency depth exceeds budget")
        if capability_id in visiting:
            raise RouterError("DEPENDENCY_CYCLE", "capability dependency cycle detected")
        if capability_id in visited:
            return
        capability = by_id.get(capability_id)
        if capability is None:
            raise RouterError("DEPENDENCY_UNKNOWN_OR_CROSS_DOMAIN", f"dependency is not in selected domain: {capability_id}")
        visiting.add(capability_id)
        for dependency in capability["requires"]:
            visit(dependency, depth + 1)
        visiting.remove(capability_id)
        visited.add(capability_id)
        ordered.append(capability)

    visit(selected["id"], 1)
    dependency_count = len(ordered) - 1
    if dependency_count > limits["max_dependencies"]:
        raise RouterError("DEPENDENCY_COUNT_EXCEEDED", "capability dependency count exceeds budget")

    modules: list[LoadedModule] = []
    required_tools: list[str] = []
    seen_tools: set[str] = set()
    for capability in ordered:
        pack_relative = capability["document_path"]
        pack_raw = _read_bounded(
            _safe_file(root, pack_relative, area="packs", suffix=".md"),
            pack_relative,
            limits["max_pack_bytes"],
        )
        account(pack_relative, pack_raw)
        pack_sha = _sha256(pack_raw)
        if pack_sha != capability["sha256"]:
            raise RouterError("PACK_HASH_MISMATCH", "capability pack raw-byte SHA256 does not match domain")
        try:
            module_text = pack_raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RouterError("PACK_ENCODING_INVALID", "capability pack must be UTF-8") from exc
        declared_tools = list(capability["tool_requirements"])
        for tool in declared_tools:
            if tool not in seen_tools:
                required_tools.append(tool)
                seen_tools.add(tool)
        modules.append(
            {
                "capability_id": capability["id"],
                "path": pack_relative,
                "sha256": pack_sha,
                "module_text": module_text,
                "requires": list(capability["requires"]),
                "required_tools": declared_tools,
            }
        )

    return {
        "status": "LOADED_STATIC_CANDIDATE",
        "verification_level": "CATALOG_CHAIN_ONLY_NOT_POLICY_VERIFIED",
        "policy_verified": False,
        "authority_effect": "NONE",
        "dispatch_authorized": False,
        "writer_change_authorized": False,
        "tools_checked": False,
        "candidate_only": True,
        "intent": intent,
        "domain_id": summary["id"],
        "selected_capability_id": selected["id"],
        "capability_ids": [capability["id"] for capability in ordered],
        "loaded_paths": loaded_paths,
        "raw_bytes": raw_total,
        "modules": modules,
        "required_tools": required_tools,
        "required_tools_status": "DECLARED_ONLY_NOT_CHECKED",
    }
