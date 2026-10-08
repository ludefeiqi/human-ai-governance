"""S5 regression: scale, security, and honest measurement boundaries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from registry.benchmark_route_scaling import benchmark_synthetic_scales, synthetic_catalog
from registry.validate_capabilities import CapabilityError, dependency_closure
from tests.test_capability_catalog import candidate_root, mutate_card

ROOT = Path(__file__).resolve().parents[1]


def test_s5_10_100_1000_have_identical_relevant_context_and_no_hidden_modules():
    report = benchmark_synthetic_scales(ROOT, repeats=5)
    assert report["status"] == "S5_SYNTHETIC_MEASUREMENT_ONLY"
    rows = report["metrics"]
    assert [r["catalog_size"] for r in rows] == [10, 100, 1000]
    assert [r["synthetic_all_card_preflight_count"] for r in rows] == [10, 100, 1000]
    assert len({r["selected_context_chars"] for r in rows}) == 1
    assert rows[0]["selected_context_chars"] > 0
    assert all(r["selected_context_modules"] == 3 for r in rows)
    assert all(r["irrelevant_loaded"] == 0 for r in rows)
    assert all(r["selected_context_ids"] == ["tool.route", "codex.observe", "project.restore"] for r in rows)
    assert all(r["synthetic_trials"] == 5 for r in rows)
    assert all(r["synthetic_full_catalog_preflight_ms"] >= 0 for r in rows)
    assert all(r["synthetic_selector_median_ms"] >= 0 for r in rows)


def test_s5_metadata_cost_is_visible_and_not_misreported_as_model_context():
    rows = benchmark_synthetic_scales(ROOT, repeats=2)["metrics"]
    chars = [r["catalog_metadata_chars"] for r in rows]
    assert chars[0] < chars[1] < chars[2]
    assert chars[2] > 10 * chars[0]
    assert rows[2]["selected_context_chars"] == rows[0]["selected_context_chars"]


def test_s5_synthetic_shard_index_is_separate_from_full_integrity_preflight():
    report = benchmark_synthetic_scales(ROOT, repeats=2)
    rows = report["metrics"]
    assert report["sharding_measured_only_in_synthetic_taxonomy"] is True
    assert [r["synthetic_root_shard_count"] for r in rows] == [4, 4, 4]
    assert all(r["synthetic_root_shard_index_chars"] < 300 for r in rows)
    assert len({r["synthetic_selected_shard_ids_chars"] for r in rows}) == 1
    assert rows[2]["catalog_metadata_chars"] > 30 * rows[2]["synthetic_root_shard_index_chars"]
    assert rows[2]["synthetic_all_card_preflight_count"] == 1000


def test_s5_does_not_invent_real_network_token_or_first_result_metrics():
    result = benchmark_synthetic_scales(ROOT, repeats=2)
    assert result["catalog_is_synthetic"] is True
    assert result["real_remote_policy_verification"] == "NOT_PERFORMED_NOT_WAIVED"
    assert result["real_remote_fetch_count"] == "NOT_MEASURED"
    assert result["real_probe_count"] == "NOT_MEASURED"
    assert result["real_time_to_first_valid_result_ms"] == "NOT_MEASURED"
    assert result["model_token_count"] == "TOKEN_UNKNOWN"
    assert result["tool_invocations"] == result["external_side_effects"] == 0
    assert result["permission_granted"] is False
    assert result["dispatch_authorized"] is False


@pytest.mark.parametrize("size", [None, True, 0, 9, 11, 99, 101, 1001, 10000, 10.0])
def test_s5_unbounded_or_noncanonical_catalog_size_rejected(size):
    with pytest.raises(CapabilityError) as exc:
        synthetic_catalog(size)
    assert exc.value.code == "S5_SCALE_INVALID"


@pytest.mark.parametrize("repeats", [None, True, 0, -1, 201, 10.0])
def test_s5_invalid_trial_counts_rejected_before_probe(repeats):
    with pytest.raises(CapabilityError) as exc:
        benchmark_synthetic_scales(ROOT, repeats=repeats)
    assert exc.value.code == "S5_SCALE_INVALID"


def test_s5_unequal_or_missing_scale_points_are_not_accepted():
    with pytest.raises(CapabilityError) as exc:
        benchmark_synthetic_scales(ROOT, sizes=(10, 100), repeats=1)
    assert exc.value.code == "S5_SCALE_INVALID"


def test_s5_unselected_cycle_must_be_caught_by_full_metadata_preflight():
    cards=synthetic_catalog(1000)
    cards["synthetic.extra.0001"]["dependencies"]=["synthetic.extra.0002"]
    cards["synthetic.extra.0002"]["dependencies"]=["synthetic.extra.0001"]
    with pytest.raises(CapabilityError) as exc:
        dependency_closure(cards, sorted(cards))
    assert exc.value.code == "DEPENDENCY_CYCLE"
    # The same bad extra node is irrelevant to the task's minimal closure;
    # relying on selected-only checks would miss the danger.
    assert dependency_closure(cards, ["project.restore"]) == ["tool.route","project.restore"]


def test_s5_unselected_unknown_dependency_rejected_in_full_preflight():
    cards=synthetic_catalog(100)
    cards["synthetic.extra.0001"]["dependencies"]=["secret.run"]
    with pytest.raises(CapabilityError) as exc:
        dependency_closure(cards, sorted(cards))
    assert exc.value.code == "CAPABILITY_NOT_FOUND"


def test_s5_full_preflight_rejects_tampered_real_inert_card(tmp_path: Path):
    root=candidate_root(tmp_path)
    mutate_card(root, "codex.observe", lambda c: c["activation"].update({"invocation": "ALLOWED"}))
    with pytest.raises(CapabilityError) as exc:
        benchmark_synthetic_scales(root, repeats=1)
    assert exc.value.code == "CAPABILITY_SCHEMA_INVALID"


def test_s5_source_lock_mismatch_is_not_hidden_by_synthetic_benchmark(tmp_path: Path):
    root=candidate_root(tmp_path)
    p=root/"clients/chatgpt-plugin/skills/governance-bootstrap/references/source-lock.md"
    p.write_text("Tampered\n",encoding="utf-8")
    with pytest.raises(CapabilityError) as exc:
        benchmark_synthetic_scales(root, repeats=1)
    assert exc.value.code == "SOURCE_LOCK_MISMATCH"


def test_s5_computation_never_enters_subprocess_or_network(monkeypatch):
    import subprocess, socket

    def forbid(*args, **kwargs):
        raise AssertionError("S5 offline benchmark must not call network/process")
    monkeypatch.setattr(subprocess,"run",forbid)
    monkeypatch.setattr(subprocess,"Popen",forbid)
    monkeypatch.setattr(socket.socket,"connect",forbid)
    result=benchmark_synthetic_scales(ROOT, repeats=1)
    assert result["tool_invocations"] == 0
    assert sum(r["synthetic_network_calls"] for r in result["metrics"]) == 0


def test_s5_json_report_retains_truthful_counter_types():
    result=benchmark_synthetic_scales(ROOT, repeats=1)
    round_trip=json.loads(json.dumps(result,ensure_ascii=False))
    assert round_trip==result
    assert type(round_trip["tool_invocations"]) is int
    assert type(round_trip["dispatch_authorized"]) is bool
