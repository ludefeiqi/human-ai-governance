"""S4 candidate-only R0 tool-route planner consuming separately collected live probes.

It never imports, calls, reconnects, authenticates, or executes the chosen
tool. The host performs permitted read-only probes independently, validates
their evidence, and retains the authorization decision. This module only
forms a scope-checked route *proposal*; tool metadata is low-trust data.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from registry.validate_capabilities import CapabilityError

# Static allowlist; tool descriptions, repository content, and plugin text cannot
# add methods or lower their risk. Codex RPC is a separate local interface, NOT
# an exposed Codex MCP or authority to resume/start any thread.
METHODS: dict[str, tuple[str, str]] = {
    "github.connector.fetch_file": ("mcp__GitHub__fetch_file", "GITHUB_READ_ONLY"),
    "github.cli.get": ("gh api --method GET", "GITHUB_READ_ONLY"),
    "codex.app_server.thread_list": ("thread/list", "CODEX_OBSERVE_ONLY"),
    "codex.app_server.thread_read": ("thread/read includeTurns=false", "CODEX_OBSERVE_ONLY"),
    "chatgpt.host.mcp_discover": ("host exposed-tool metadata", "METADATA_ONLY"),
}
TASK_ROUTES: dict[str, tuple[str, ...]] = {
    "PROJECT_RESTORE_READ_ONLY": (
        "github.connector.fetch_file",
        "github.cli.get",
    ),
    "CODEX_OBSERVE_EXISTING_READ_ONLY": ("codex.app_server.thread_list",),
    "TOOL_ROUTE_PLAN_ONLY": ("chatgpt.host.mcp_discover",),
}
SAFE_SCOPE = re.compile(r"^[A-Za-z0-9_./:@-]{1,220}$")
SAFE_EVIDENCE = re.compile(r"^[A-Za-z0-9_./:@#-]{1,300}$")
PROBE_STATUSES = frozenset({
    "TASK_VERIFIED", "PROBED", "DISCOVERED", "NOT_CONFIGURED",
    "TOOL_UNAVAILABLE", "AUTHORIZATION_BLOCKED", "RUNTIME_UNKNOWN",
    "EFFECT_UNKNOWN",
})
BLOCKING = frozenset({"AUTHORIZATION_BLOCKED", "RUNTIME_UNKNOWN", "EFFECT_UNKNOWN"})
FALLBACK_ELIGIBLE = frozenset({"NOT_CONFIGURED", "TOOL_UNAVAILABLE"})
R0_PROBE_KEYS = frozenset({
    "tool_key", "method", "state", "scope", "evidence_ref",
    "permission", "side_effects", "target_verified",
})


def _validate_probe(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != R0_PROBE_KEYS:
        raise CapabilityError("R0_PROBE_INVALID", "probe fields are not the fixed S4 shape")
    key = value["tool_key"]
    if type(key) is not str or key not in METHODS or value["method"] != METHODS[key][0]:
        raise CapabilityError("R0_PROBE_INVALID", "probe tool/method is not R0-allowlisted")
    if type(value["method"]) is not str or type(value["state"]) is not str or value["state"] not in PROBE_STATUSES:
        raise CapabilityError("R0_PROBE_INVALID", "probe state is not canonical")
    if type(value["scope"]) is not str or not SAFE_SCOPE.fullmatch(value["scope"]):
        raise CapabilityError("R0_PROBE_INVALID", "probe scope must be a bounded literal identifier")
    ref = value["evidence_ref"]
    if type(ref) is not str or (ref and not SAFE_EVIDENCE.fullmatch(ref)):
        raise CapabilityError("R0_PROBE_INVALID", "probe evidence reference is invalid")
    if type(value["side_effects"]) is not int or value["side_effects"] != 0:
        raise CapabilityError("R0_PROBE_INVALID", "R0 probe reported side effects")
    if type(value["target_verified"]) is not bool:
        raise CapabilityError("R0_PROBE_INVALID", "task verification must be boolean")
    if type(value["permission"]) is not str or value["permission"] not in {
        "READ_SCOPE_CONFIRMED", "DENIED", "UNVERIFIED",
    }:
        raise CapabilityError("R0_PROBE_INVALID", "probe permission must be explicit")
    if value["state"] in {"TASK_VERIFIED", "PROBED"}:
        if not ref or value["permission"] != "READ_SCOPE_CONFIRMED":
            raise CapabilityError("R0_PROBE_INVALID", "positive probe needs attributed R0 evidence and read scope")
    if value["target_verified"] != (value["state"] == "TASK_VERIFIED"):
        raise CapabilityError("R0_PROBE_INVALID", "task verification must match the canonical probe state")
    if value["state"] == "AUTHORIZATION_BLOCKED" and value["permission"] != "DENIED":
        raise CapabilityError("R0_PROBE_INVALID", "refusal must be represented as DENIED")
    if value["state"] in {"DISCOVERED", "NOT_CONFIGURED", "TOOL_UNAVAILABLE",
                          "RUNTIME_UNKNOWN", "EFFECT_UNKNOWN"} and value["target_verified"]:
        raise CapabilityError("R0_PROBE_INVALID", "inconclusive probe cannot verify a target")
    return value


def select_r0_tool_route(
    task_kind: str,
    scope: str,
    observations: Sequence[Mapping[str, Any]],
    *,
    allow_fallback_after_unavailable: bool = False,
) -> dict[str, Any]:
    """Return a disabled, non-authorizing plan; NEVER perform any tool call.

    Observations are caller-reported lower-trust evidence, not a grant of
    permission. An external authorized host must verify evidence/permissions
    and perform the actual read. A denial or UNKNOWN never gets a fallback.
    """
    if type(task_kind) is not str or task_kind not in TASK_ROUTES:
        raise CapabilityError("CAPABILITY_TASK_UNSUPPORTED", "task kind is not an S4 contract")
    if type(scope) is not str or not SAFE_SCOPE.fullmatch(scope):
        raise CapabilityError("RISK_SCOPE_MISMATCH", "route has no exact bounded literal target")
    if type(allow_fallback_after_unavailable) is not bool:
        raise CapabilityError("R0_PROBE_INVALID", "fallback must be explicitly boolean")
    if type(observations) not in (list, tuple) or len(observations) > len(METHODS):
        raise CapabilityError("R0_PROBE_INVALID", "S4 observations must be a bounded sequence")
    allowed = TASK_ROUTES[task_kind]
    probes: dict[str, dict[str, Any]] = {}
    for item in observations:
        obs = _validate_probe(item)
        key = obs["tool_key"]
        if key in probes or key not in allowed:
            raise CapabilityError("R0_PROBE_INVALID", "duplicate or task-unrelated tool probe")
        if obs["scope"] != scope:
            raise CapabilityError("RISK_SCOPE_MISMATCH", "probe target differs from requested scope")
        probes[key] = obs

    checked = []
    for index, key in enumerate(allowed):
        obs = probes.get(key)
        if obs is None:
            # Missing probe is UNKNOWN, not "no tool exists".
            return _hold("TOOL_PROBE_UNKNOWN", task_kind, scope, checked)
        state = obs["state"]
        checked.append({"tool_key": key, "state": state, "evidence_ref": obs["evidence_ref"]})
        if state in BLOCKING or obs["permission"] == "DENIED":
            return _hold(state if state in BLOCKING else "AUTHORIZATION_BLOCKED", task_kind, scope, checked)
        if state in {"PROBED", "TASK_VERIFIED"}:
            if index > 0 and not allow_fallback_after_unavailable:
                return _hold("FALLBACK_NOT_AUTHORIZED", task_kind, scope, checked)
            return {
                "status": "R0_ROUTE_PROPOSAL",
                "task_kind": task_kind,
                "scope": scope,
                "tool_key": key,
                "method": METHODS[key][0],
                "route_class": METHODS[key][1],
                "interface_state": state,
                "reported_task_state": state,
                "task_state": "EXTERNAL_EVIDENCE_REQUIRED" if state == "TASK_VERIFIED" else "RUNTIME_UNKNOWN",
                "fallback_used": index > 0,
                "checked": checked,
                "invocation": "FORBIDDEN_IN_CANDIDATE",
                "trusted_policy_verification": "NOT_EXECUTED",
                "runtime_permission_granted": False,
                "tools_invoked": 0,
                "side_effects": 0,
                "dispatch_authorized": False,
            }
        if state in FALLBACK_ELIGIBLE:
            if index == len(allowed) - 1:
                return _hold(state, task_kind, scope, checked)
            if not allow_fallback_after_unavailable:
                return _hold("FALLBACK_NOT_AUTHORIZED", task_kind, scope, checked)
            continue
        # DISCOVERED means metadata presence only; cannot imply a real task probe.
        return _hold("TOOL_PROBE_INCOMPLETE", task_kind, scope, checked)
    return _hold("TOOL_UNAVAILABLE", task_kind, scope, checked)


def _hold(reason: str, task_kind: str, scope: str, checked: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "HOLD",
        "reason": reason,
        "task_kind": task_kind,
        "scope": scope,
        "checked": checked,
        "invocation": "FORBIDDEN_IN_CANDIDATE",
        "runtime_permission_granted": False,
        "tools_invoked": 0,
        "side_effects": 0,
        "dispatch_authorized": False,
    }
