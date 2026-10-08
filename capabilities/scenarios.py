"""Pure, local-only S4 scenario planning over the pinned capability router.

The public entry point reads only through :func:`route_capability` and returns
an inert data plan.  It never probes tools, performs dispatch, or restores
business state.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, TypedDict

from capabilities.router import RouterError, route_capability


PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
TARGET_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
CAPABILITY_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$")
TOOL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")

SUPPORTED_INTENTS = {
    "global_restore",
    "project_restore",
    "codex_observe",
    "tool_select",
}
BASE_FIELDS = {"requested_effect", "untrusted_text"}
INTENT_FIELDS = {
    "global_restore": BASE_FIELDS,
    "project_restore": BASE_FIELDS | {"project_id"},
    "codex_observe": BASE_FIELDS | {"identifier_type", "identifier"},
    "tool_select": BASE_FIELDS
    | {
        "target_ref",
        "target_semantics",
        "target_capability_id",
        "session_ref",
        "candidates",
        "replacement_for",
    },
}
TARGET_SEMANTICS = {
    "RESTORE_GOVERNANCE_VIEW": {"project.restore"},
    "OBSERVE_EXISTING_CODEX_STATE": {"codex.observe"},
    "SELECT_READ_ONLY_TOOL": {"tool.route"},
}
CANDIDATE_FIELDS = {
    "tool_id",
    "target_ref",
    "session_ref",
    "capability_ids",
    "permission_fit",
    "scope_fit",
    "effect",
    "tool_kind",
    "continuity",
    "verifiability",
}
REPLACEMENT_FIELDS = {"tool_id", "target_ref", "side_effect_status"}


class ScenarioError(Exception):
    """Fail-closed context error whose receipt remains non-executing."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        return _base_receipt("HOLD", code=self.code, message=self.message, **self.details)


class ScenarioPlan(TypedDict, total=False):
    status: str
    decision: str
    authority_effect: str
    dispatch: bool
    writer: bool
    policy_verified: bool
    business_state_restored: bool
    runtime_tool_permission_required: bool
    candidate_only: bool
    intent: str
    selected_capability_id: str
    catalog_verification_level: str
    context: dict[str, Any]
    steps: list[dict[str, Any]]
    tool_observation_trust: str
    recommendation: dict[str, Any]
    excluded_candidates: list[dict[str, str]]
    code: str
    message: str


def _base_receipt(decision: str, **extra: Any) -> dict[str, Any]:
    return {
        "status": "PLAN_ONLY",
        "decision": decision,
        "authority_effect": "NONE",
        "dispatch": False,
        "writer": False,
        "policy_verified": False,
        "business_state_restored": False,
        "runtime_tool_permission_required": True,
        "candidate_only": True,
        **extra,
    }


def _exact_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ScenarioError("CONTEXT_TYPE_INVALID", f"{label} must be a plain object")
    if any(type(key) is not str for key in value):
        raise ScenarioError("CONTEXT_KEY_INVALID", f"{label} keys must be plain strings")
    return value


def _fields(value: dict[str, Any], allowed: set[str], required: set[str], label: str) -> None:
    unknown = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if unknown:
        raise ScenarioError("CONTEXT_UNKNOWN_FIELD", f"{label} contains unknown fields", fields=unknown)
    if missing:
        raise ScenarioError("CONTEXT_REQUIRED_FIELD", f"{label} is missing required fields", fields=missing)


def _string(value: Any, label: str, pattern: re.Pattern[str], *, max_length: int) -> str:
    if type(value) is not str or not value or len(value) > max_length or not pattern.fullmatch(value):
        raise ScenarioError("CONTEXT_VALUE_INVALID", f"{label} is not a canonical identifier")
    return value


def _enum(value: Any, allowed: set[str], label: str) -> str:
    if type(value) is not str or value not in allowed:
        raise ScenarioError("CONTEXT_VALUE_INVALID", f"{label} is not an allowed value")
    return value


def _nullable_ref(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _string(value, label, TARGET_REF_RE, max_length=256)


def _normalize_base(context: dict[str, Any]) -> dict[str, Any]:
    effect = _enum(context.get("requested_effect"), {"READ_ONLY", "WRITE", "EXECUTE"}, "requested_effect")
    if effect != "READ_ONLY":
        raise ScenarioError(
            "R0_EFFECT_FORBIDDEN",
            "write, deployment, execution, and other side effects cannot map to an R0 scenario",
        )
    note = context.get("untrusted_text")
    if note is not None and (type(note) is not str or len(note) > 4096):
        raise ScenarioError("CONTEXT_VALUE_INVALID", "untrusted_text must be a bounded plain string")
    return {"requested_effect": effect, "untrusted_text_ignored_for_control": note is not None}


def _plan_steps(intent: str, context: dict[str, Any]) -> list[dict[str, Any]]:
    if intent == "global_restore":
        # Global discovery requires explicit full authorized registry coverage.
        return [
            {"operation": "read_policy_source", "source_layer": "POLICY", "mode": "READ_ONLY"},
            {"operation": "read_project_index", "source_layer": "REGISTRY", "mode": "READ_ONLY"},
            {"operation": "enumerate_all_registered_and_authorized_projects", "source_layer": "REGISTRY",
             "coverage": "COMPLETE_OR_EXPLICIT_PARTIAL", "mode": "READ_ONLY"},
            {"operation": "read_each_authorized_project_head", "source_layer": "PROJECT_SOURCE", "mode": "READ_ONLY"},
            {"operation": "read_each_authorized_ledger_at_same_head", "source_layer": "PROJECT_STATE", "mode": "READ_ONLY"},
            {"operation": "reconcile_existing_runtime_only_if_needed", "source_layer": "RUNTIME", "mode": "READ_ONLY"},
            {"operation": "report_source_state_runtime_and_coverage_separately", "source_layer": "REPORT",
             "mode": "READ_ONLY"},
        ]
    if intent == "project_restore":
        project_id = context["project_id"]
        return [
            {"operation": "read_policy_source", "source_layer": "POLICY", "mode": "READ_ONLY"},
            {"operation": "read_project_index_entry", "source_layer": "REGISTRY", "project_id": project_id, "mode": "READ_ONLY"},
            {"operation": "read_project_head", "source_layer": "PROJECT_SOURCE", "project_id": project_id, "mode": "READ_ONLY"},
            {"operation": "read_project_ledger_at_same_head", "source_layer": "PROJECT_STATE", "project_id": project_id, "mode": "READ_ONLY"},
            {"operation": "report_source_state_runtime_separately", "source_layer": "REPORT", "mode": "READ_ONLY"},
        ]
    return [
        {
            "operation": "thread/list",
            "identifier_type": context["identifier_type"],
            "identifier": context["identifier"],
            "mode": "READ_ONLY_IF_RUNTIME_PERMISSION_VERIFIED",
        },
        {
            "operation": "thread/read",
            "identifier_type": context["identifier_type"],
            "identifier": context["identifier"],
            "mode": "READ_ONLY_IF_RUNTIME_PERMISSION_VERIFIED",
        },
    ]


def _normalize_candidate(value: Any, index: int) -> dict[str, Any]:
    candidate = _exact_dict(value, f"candidates[{index}]")
    _fields(candidate, CANDIDATE_FIELDS, CANDIDATE_FIELDS, f"candidates[{index}]")
    capability_ids = candidate["capability_ids"]
    if type(capability_ids) is not list or not capability_ids or len(capability_ids) > 16:
        raise ScenarioError("CONTEXT_VALUE_INVALID", "capability_ids must be a bounded non-empty plain list")
    normalized_ids: list[str] = []
    for item in capability_ids:
        normalized_ids.append(_string(item, "capability_id", CAPABILITY_ID_RE, max_length=128))
    if len(set(normalized_ids)) != len(normalized_ids):
        raise ScenarioError("CONTEXT_VALUE_INVALID", "capability_ids must be unique")
    return {
        "tool_id": _string(candidate["tool_id"], "tool_id", TOOL_ID_RE, max_length=128),
        "target_ref": _string(candidate["target_ref"], "candidate target_ref", TARGET_REF_RE, max_length=256),
        "session_ref": _nullable_ref(candidate["session_ref"], "candidate session_ref"),
        "capability_ids": normalized_ids,
        "permission_fit": _enum(candidate["permission_fit"], {"WITHIN_STATED_R0", "OUT_OF_SCOPE", "UNKNOWN"}, "permission_fit"),
        "scope_fit": _enum(candidate["scope_fit"], {"EXACT", "BROADER", "MISMATCH"}, "scope_fit"),
        "effect": _enum(candidate["effect"], {"READ_ONLY", "SIDE_EFFECTING", "UNKNOWN"}, "effect"),
        "tool_kind": _enum(candidate["tool_kind"], {"MCP", "LOCAL", "OTHER", "UNKNOWN"}, "tool_kind"),
        "continuity": _enum(candidate["continuity"], {"SAME_TARGET", "DIFFERENT_TARGET", "UNKNOWN"}, "continuity"),
        "verifiability": _enum(candidate["verifiability"], {"VERIFIABLE", "UNVERIFIABLE", "UNKNOWN"}, "verifiability"),
    }


def _tool_plan(context: dict[str, Any]) -> tuple[str, dict[str, Any], list[dict[str, str]]]:
    target_ref = context["target_ref"]
    session_ref = context["session_ref"]
    target_capability_id = context["target_capability_id"]
    replacement = context.get("replacement_for")
    if replacement is not None:
        replacement = _exact_dict(replacement, "replacement_for")
        _fields(replacement, REPLACEMENT_FIELDS, REPLACEMENT_FIELDS, "replacement_for")
        _string(replacement["tool_id"], "replacement tool_id", TOOL_ID_RE, max_length=128)
        prior_target = _string(replacement["target_ref"], "replacement target_ref", TARGET_REF_RE, max_length=256)
        side_effect_status = _enum(
            replacement["side_effect_status"],
            {"NONE_VERIFIED", "PRESENT", "UNKNOWN"},
            "replacement side_effect_status",
        )
        if prior_target != target_ref or side_effect_status != "NONE_VERIFIED":
            return (
                "HOLD",
                {"state": "HOLD", "reason": "REPLACEMENT_GATE_UNSATISFIED", "candidate_tool_ids": []},
                [],
            )

    qualified: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for candidate in context["candidates"]:
        reason = None
        if candidate["target_ref"] != target_ref:
            reason = "TARGET_MISMATCH"
        elif session_ref is not None and candidate["session_ref"] != session_ref:
            reason = "SESSION_MISMATCH"
        elif target_capability_id not in candidate["capability_ids"]:
            reason = "CAPABILITY_MISMATCH"
        elif candidate["permission_fit"] != "WITHIN_STATED_R0":
            reason = "PERMISSION_NOT_QUALIFIED"
        elif candidate["scope_fit"] == "MISMATCH":
            reason = "SCOPE_MISMATCH"
        elif candidate["effect"] != "READ_ONLY":
            reason = "SIDE_EFFECT_OR_UNKNOWN"
        elif candidate["tool_kind"] == "UNKNOWN":
            reason = "TOOL_KIND_UNKNOWN"
        elif candidate["continuity"] != "SAME_TARGET":
            reason = "TARGET_CONTINUITY_UNPROVEN"
        elif candidate["verifiability"] != "VERIFIABLE":
            reason = "RESULT_UNVERIFIABLE"
        if reason:
            excluded.append({"tool_id": candidate["tool_id"], "reason": reason})
        else:
            qualified.append(candidate)

    if not qualified:
        return "HOLD", {"state": "HOLD", "reason": "NO_QUALIFIED_CANDIDATE", "candidate_tool_ids": []}, excluded

    best_scope = "EXACT" if any(item["scope_fit"] == "EXACT" for item in qualified) else "BROADER"
    finalists = sorted(
        (item for item in qualified if item["scope_fit"] == best_scope),
        key=lambda item: item["tool_id"],
    )
    ids = [item["tool_id"] for item in finalists]
    if len(ids) != 1:
        return "AMBIGUOUS", {"state": "AMBIGUOUS", "reason": "EQUALLY_QUALIFIED", "candidate_tool_ids": ids}, excluded
    return (
        "READY_FOR_RUNTIME_GATE",
        {
            "state": "SUGGESTED",
            "reason": "UNIQUE_QUALIFIED_CURRENT_TARGET_CANDIDATE",
            "primary_tool_id": ids[0],
            "candidate_tool_ids": ids,
            "execution_authorized": False,
        },
        excluded,
    )


def plan_scenario(
    root: Path,
    intent: str,
    expected_catalog_sha256: str,
    context: Mapping[str, Any],
) -> ScenarioPlan:
    """Validate one scenario and return a plan with no execution capability."""
    if type(intent) is not str or intent not in SUPPORTED_INTENTS:
        raise ScenarioError("INTENT_UNSUPPORTED", "only the four S4 intents are supported")
    value = _exact_dict(context, "context")
    required = {"requested_effect"}
    if intent == "project_restore":
        required |= {"project_id"}
    elif intent == "codex_observe":
        required |= {"identifier_type", "identifier"}
    elif intent == "tool_select":
        required |= {"target_ref", "target_semantics", "target_capability_id", "session_ref", "candidates"}
    _fields(value, INTENT_FIELDS[intent], required, "context")
    normalized = _normalize_base(value)

    if intent == "project_restore":
        normalized["project_id"] = _string(value["project_id"], "project_id", PROJECT_ID_RE, max_length=128)
    elif intent == "codex_observe":
        normalized["identifier_type"] = _enum(value["identifier_type"], {"task", "thread"}, "identifier_type")
        normalized["identifier"] = _string(value["identifier"], "identifier", IDENTIFIER_RE, max_length=128)
    elif intent == "tool_select":
        normalized["target_ref"] = _string(value["target_ref"], "target_ref", TARGET_REF_RE, max_length=256)
        normalized["session_ref"] = _nullable_ref(value["session_ref"], "session_ref")
        semantics = _enum(value["target_semantics"], set(TARGET_SEMANTICS), "target_semantics")
        capability_id = _string(value["target_capability_id"], "target_capability_id", CAPABILITY_ID_RE, max_length=128)
        if capability_id not in TARGET_SEMANTICS[semantics]:
            raise ScenarioError("TARGET_CAPABILITY_MISMATCH", "target semantics and capability are not compatible")
        normalized["target_semantics"] = semantics
        normalized["target_capability_id"] = capability_id
        candidates = value["candidates"]
        if type(candidates) is not list or len(candidates) > 32:
            raise ScenarioError("CONTEXT_VALUE_INVALID", "candidates must be a bounded plain list")
        normalized["candidates"] = [_normalize_candidate(item, index) for index, item in enumerate(candidates)]
        if len({item["tool_id"] for item in normalized["candidates"]}) != len(normalized["candidates"]):
            raise ScenarioError("CONTEXT_VALUE_INVALID", "candidate tool_id values must be unique")
        if "replacement_for" in value:
            normalized["replacement_for"] = value["replacement_for"]

    try:
        routed = route_capability(root, intent, expected_catalog_sha256)
    except RouterError as exc:
        raise ScenarioError("CAPABILITY_ROUTE_HOLD", "pinned capability route did not verify", route_error=exc.as_dict()) from exc

    common = {
        "intent": intent,
        "selected_capability_id": routed["selected_capability_id"],
        "catalog_verification_level": routed["verification_level"],
        "context": {key: item for key, item in normalized.items() if key != "candidates" and key != "replacement_for"},
    }
    if intent != "tool_select":
        return _base_receipt("READY_FOR_RUNTIME_GATE", **common, steps=_plan_steps(intent, normalized))  # type: ignore[return-value]

    decision, recommendation, excluded = _tool_plan(normalized)
    return _base_receipt(
        decision,
        **common,
        steps=[
            {"operation": "bounded_current_tool_discovery", "mode": "PLAN_ONLY"},
            {"operation": "verify_runtime_permission_before_any_call", "mode": "PLAN_ONLY"},
        ],
        tool_observation_trust="CALLER_SUPPLIED_UNVERIFIED",
        recommendation=recommendation,
        excluded_candidates=excluded,
    )  # type: ignore[return-value]
