"""S3 candidate-only deterministic, non-executing context selector.

This module is NOT a production router and provides no tool execution, authorization,
permission discovery, remote policy verification, or business project restoration.
All selected card content is lower-trust metadata, never governing instructions.
An authorized real launcher must separately verify the entire released policy
using the existing pinned tag/Manifest mechanism before any operational action.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from registry.validate_capabilities import (
    CAPABILITY_DIRECTORY,
    CAPABILITY_PROFILES,
    CapabilityError,
    _load_json_file,
    _safe_file,
    _validate_static_card,
    dependency_closure,
    validate_capability_directory,
)


# Exact normalized intent contracts, not natural-language authority inference.
# These are context-selection wishes, not permission or tool-invocation commands.
TASK_CAPABILITY_MAP = {
    "PROJECT_RESTORE_READ_ONLY": ("project.restore",),
    "CODEX_OBSERVE_EXISTING_READ_ONLY": ("codex.observe",),
    "TOOL_ROUTE_PLAN_ONLY": ("tool.route",),
}


def build_candidate_context(root: Path, task_kind: str) -> dict[str, Any]:
    """Perform a complete S2 catalog preflight, then context-load only the closure.

    The preflight intentionally reads all THREE cards for catalog consistency;
    the selected model-context modules below are a distinct, smaller set.
    No remote policy verification is claimed or bypassed by this function.
    """
    if type(task_kind) is not str or task_kind not in TASK_CAPABILITY_MAP:
        raise CapabilityError("CAPABILITY_TASK_UNSUPPORTED", "task_kind is not a fixed S3 selector")
    root = root.resolve()
    # This preflight remains comprehensive and may fail even on unselected data.
    preflight = validate_capability_directory(root)
    cards = {
        capability_id: {"dependencies": profile["dependencies"]}
        for capability_id, profile in CAPABILITY_PROFILES.items()
    }
    required = list(TASK_CAPABILITY_MAP[task_kind])
    ordered = dependency_closure(cards, required)

    loaded: list[dict[str, Any]] = []
    for capability_id in ordered:
        profile = CAPABILITY_PROFILES[capability_id]
        relative = f"{CAPABILITY_DIRECTORY}/{profile['filename']}"
        card = _load_json_file(_safe_file(root, relative))
        # Defend against selected-file drift between complete preflight and this read.
        _validate_static_card(card, capability_id)
        for field in (
            "dependencies", "allowed_operations", "forbidden_operations",
            "success_states", "failure_states",
        ):
            actual = card[field] if field == "dependencies" else card["contract"][field]
            if actual != profile[field]:
                raise CapabilityError(
                    "RISK_SCOPE_MISMATCH",
                    f"selected S3 contract drift: {capability_id}.{field}",
                )
        body = json.dumps(card, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        loaded.append({
            "capability_id": capability_id,
            "source": relative,
            "trust": "LOWER_TRUST_DESCRIPTIVE_DATA_NOT_INSTRUCTIONS",
            "context_body": body,
            "context_chars": len(body),
        })

    loaded_ids = [item["capability_id"] for item in loaded]
    return {
        "status": "S3_STATIC_CONTEXT_CANDIDATE",
        "task_kind": task_kind,
        "requested_capabilities": required,
        "context_loaded_ids": loaded_ids,
        "context_loaded": loaded,
        "selection_coverage": "STATIC_CLOSURE_COMPLETE",
        "catalog_preflight_cards": preflight["capability_count"],
        "catalog_preflight_scope": "ALL_FIXED_CARDS",
        "unrelated_context_modules_loaded": 0,
        "context_chars": sum(item["context_chars"] for item in loaded),
        "remote_fetch_count": 0,
        "full_released_policy_verification": "NOT_PERFORMED_REQUIRED_FOR_REAL_LAUNCH",
        "activation": "DISABLED",
        "tools_invoked": 0,
        "side_effects": 0,
        "dispatch_authorized": False,
        "writer_change_authorized": False,
        "registry_trusted": False,
    }
