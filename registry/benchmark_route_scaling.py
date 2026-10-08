"""Reproducible S5 synthetic 10/100/1000 routing & context-load benchmark.

This is intentionally offline and inert. It compares a fixed three-capability
request over varying candidate metadata catalogs; it does NOT benchmark the
released-policy remote verification, network/tool latency, actual model token
usage, or real user-facing time-to-first-valid-result.
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any, Sequence

from registry.validate_capabilities import (
    CAPABILITY_DIRECTORY,
    CAPABILITY_PROFILES,
    CapabilityError,
    _load_json_file,
    _safe_file,
    dependency_closure,
    validate_capability_directory,
)

DEFAULT_SIZES = (10, 100, 1000)
REQUIRED = ("codex.observe", "project.restore")
EXPECTED_ORDER = ("tool.route", "codex.observe", "project.restore")


def synthetic_catalog(n: int) -> dict[str, dict[str, list[str]]]:
    """Fixed three used capabilities plus n-3 unrelated metadata-only items."""
    if type(n) is not int or n not in DEFAULT_SIZES:
        raise CapabilityError("S5_SCALE_INVALID", "S5 only measures 10/100/1000 items")
    cards = {
        capability_id: {"dependencies": list(profile["dependencies"])}
        for capability_id, profile in CAPABILITY_PROFILES.items()
    }
    for i in range(n - len(cards)):
        cards[f"synthetic.extra.{i:04d}"] = {"dependencies": []}
    assert len(cards) == n
    return cards


def _synthetic_shard_index(cards: dict[str, dict[str, list[str]]]) -> tuple[int, int, int]:
    """Count *synthetic* two-level metadata, not a deployed production router.

    The chosen synthetic taxonomy has one extra-card prefix, while the three
    original R0 capabilities each form their own group. Other distributions
    can have more root groups; this does not prove arbitrary-scale O(1).
    """
    groups: dict[str, list[str]] = {}
    for capability_id in sorted(cards):
        prefix = ".".join(capability_id.split(".")[:2])
        groups.setdefault(prefix, []).append(capability_id)
    root_summary = [
        {"prefix": prefix, "count": len(items)}
        for prefix, items in sorted(groups.items())
    ]
    needed = {".".join(name.split(".")[:2]) for name in EXPECTED_ORDER}
    selected_group_ids = [
        name for prefix, items in sorted(groups.items()) if prefix in needed
        for name in items
    ]
    return (
        len(root_summary),
        len(json.dumps(root_summary, ensure_ascii=False, separators=(",", ":"))),
        len(json.dumps(selected_group_ids, ensure_ascii=False, separators=(",", ":"))),
    )


def _fixed_selected_body_chars(root: Path) -> int:
    """Read only the three genuine S2 cards after a complete fixed preflight."""
    result = validate_capability_directory(root)
    if result["capability_count"] != 3 or result["activation"] != "DISABLED":
        raise CapabilityError("CAPABILITY_SCHEMA_INVALID", "fixed catalog changed")
    chars = 0
    for capability_id in EXPECTED_ORDER:
        relative = f"{CAPABILITY_DIRECTORY}/{CAPABILITY_PROFILES[capability_id]['filename']}"
        card = _load_json_file(_safe_file(root, relative))
        chars += len(json.dumps(card, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return chars


def benchmark_synthetic_scales(
    root: Path,
    sizes: Sequence[int] = DEFAULT_SIZES,
    *,
    repeats: int = 30,
) -> dict[str, Any]:
    """Measure only local deterministic dependency selection.

    Each count uses the same original three selected S2 content bodies, the
    same request, Python process, timer and trial count. The entire N-item
    metadata catalog is *not* treated as model-loaded context.
    """
    if type(repeats) is not int or not 1 <= repeats <= 200:
        raise CapabilityError("S5_SCALE_INVALID", "trial count outside bounded S5 range")
    if type(sizes) not in (tuple, list) or len(sizes) != 3 or tuple(sizes) != DEFAULT_SIZES:
        raise CapabilityError("S5_SCALE_INVALID", "comparisons require all fixed sizes")
    selected_chars = _fixed_selected_body_chars(root)
    results = []
    for n in sizes:
        cards = synthetic_catalog(n)
        # Distinguish the bare-ID index from the complete synthetic graph
        # metadata (IDs PLUS dependency lists). Never label the ID list as
        # the full catalog cost.
        raw_id_index = json.dumps(sorted(cards), ensure_ascii=False, separators=(",", ":"))
        raw_metadata = json.dumps(cards, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        shard_count, root_shard_chars, selected_shard_chars = _synthetic_shard_index(cards)
        # Full catalog graph integrity remains a separate up-front operation;
        # a cycle in an *unselected* extra card must not silently escape.
        catalog_check_start = time.perf_counter_ns()
        all_items_order = dependency_closure(cards, sorted(cards))
        preflight_elapsed_ns = time.perf_counter_ns() - catalog_check_start
        if set(all_items_order) != set(cards):
            raise CapabilityError("S5_PREFLIGHT_INVALID", "synthetic metadata integrity incomplete")
        trials_ns: list[int] = []
        for _ in range(repeats):
            start = time.perf_counter_ns()
            order = dependency_closure(cards, REQUIRED)
            elapsed = time.perf_counter_ns() - start
            if tuple(order) != EXPECTED_ORDER:
                raise CapabilityError("S5_SELECTION_INVALID", "minimal dependency closure drifted")
            trials_ns.append(elapsed)
        loaded = list(EXPECTED_ORDER)
        results.append({
            "catalog_size": n,
            "catalog_metadata_chars": len(raw_metadata),
            "catalog_id_index_chars": len(raw_id_index),
            "synthetic_root_shard_count": shard_count,
            "synthetic_root_shard_index_chars": root_shard_chars,
            "synthetic_selected_shard_ids_chars": selected_shard_chars,
            "synthetic_all_card_preflight_count": len(all_items_order),
            "synthetic_full_catalog_preflight_ms": round(preflight_elapsed_ns / 1_000_000, 6),
            "synthetic_requested_capabilities": list(REQUIRED),
            "selected_context_ids": loaded,
            "selected_context_modules": len(loaded),
            "selected_context_chars": selected_chars,
            "irrelevant_loaded": len(set(loaded) - set(EXPECTED_ORDER)),
            "synthetic_selector_median_ms": round(statistics.median(trials_ns) / 1_000_000, 6),
            "synthetic_selector_max_ms": round(max(trials_ns) / 1_000_000, 6),
            "synthetic_trials": repeats,
            "synthetic_network_calls": 0,
            "synthetic_effect_count": 0,
        })
    return {
        "status": "S5_SYNTHETIC_MEASUREMENT_ONLY",
        "data_contract": "CANDIDATE_ONLY_NOT_RELEASED",
        "catalog_is_synthetic": True,
        "required_task_unchanged": True,
        "sharding_measured_only_in_synthetic_taxonomy": True,
        "fixed_preflight_cards": 3,
        "metrics": results,
        "real_remote_policy_verification": "NOT_PERFORMED_NOT_WAIVED",
        "real_remote_fetch_count": "NOT_MEASURED",
        "real_probe_count": "NOT_MEASURED",
        "real_time_to_first_valid_result_ms": "NOT_MEASURED",
        "model_token_count": "TOKEN_UNKNOWN",
        "tool_invocations": 0,
        "external_side_effects": 0,
        "permission_granted": False,
        "dispatch_authorized": False,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--repeats", type=int, default=30)
    args = parser.parse_args()
    result = benchmark_synthetic_scales(args.root, repeats=args.repeats)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
