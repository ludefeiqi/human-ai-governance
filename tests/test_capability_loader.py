from __future__ import annotations

import hashlib
import json
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from capabilities.router import HARD_BUDGETS, RouterError, route_capability


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _minimal_repo(tmp_path: Path, intent: str = "project_restore") -> Path:
    root = tmp_path / "candidate"
    (root / "capabilities/domains").mkdir(parents=True)
    (root / "capabilities/packs").mkdir(parents=True)
    shutil.copy2(
        SOURCE_ROOT / "capabilities/catalog.schema.json",
        root / "capabilities/catalog.schema.json",
    )
    catalog = _json(SOURCE_ROOT / "capabilities/catalog.json")
    summary = next(item for item in catalog["domains"] if intent in item["intents"])
    domain_source = SOURCE_ROOT / summary["manifest_path"]
    domain = _json(domain_source)
    shutil.copy2(domain_source, root / summary["manifest_path"])
    for capability in domain["capabilities"]:
        source = SOURCE_ROOT / capability["document_path"]
        target = root / capability["document_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    _write_json(root / "capabilities/catalog.json", {**catalog, "domains": [summary]})
    return root


def _rehash(root: Path) -> str:
    catalog_path = root / "capabilities/catalog.json"
    catalog = _json(catalog_path)
    for summary in catalog["domains"]:
        domain_path = root / summary["manifest_path"]
        domain = _json(domain_path)
        for capability in domain["capabilities"]:
            capability["sha256"] = _sha(root / capability["document_path"])
        _write_json(domain_path, domain)
        summary["sha256"] = _sha(domain_path)
    _write_json(catalog_path, catalog)
    return _sha(catalog_path)


def _assert_hold(root: Path, intent: str, pin: str, code: str) -> RouterError:
    with pytest.raises(RouterError) as caught:
        route_capability(root, intent, pin)
    assert caught.value.code == code
    assert caught.value.as_dict()["status"] == "HOLD"
    return caught.value


@pytest.mark.parametrize(
    ("intent", "domain_id", "capability_id", "pack"),
    [
        ("global_restore", "project", "project.restore", "capabilities/packs/project-restore.md"),
        ("project_restore", "project", "project.restore", "capabilities/packs/project-restore.md"),
        ("codex_observe", "codex", "codex.observe", "capabilities/packs/codex-observe.md"),
        ("tool_select", "tools", "tool.route", "capabilities/packs/tool-routing.md"),
    ],
)
def test_successful_intents_load_only_selected_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    intent: str, domain_id: str, capability_id: str, pack: str,
):
    root = _minimal_repo(tmp_path, intent)
    pin = _rehash(root)
    expected_pack_sha = _sha(root / pack)
    expected_module_text = (root / pack).read_text(encoding="utf-8")
    opened: list[str] = []
    original = Path.read_bytes

    def tracked(path: Path) -> bytes:
        opened.append(path.relative_to(root).as_posix())
        return original(path)

    def forbidden(*args, **kwargs):
        raise AssertionError("external behavior is forbidden")

    monkeypatch.setattr(Path, "read_bytes", tracked)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    result = route_capability(root, intent, pin)

    domain_path = f"capabilities/domains/{domain_id}.json"
    expected_paths = [
        "capabilities/catalog.schema.json",
        "capabilities/catalog.json",
        domain_path,
        pack,
    ]
    assert opened == expected_paths
    assert result == {
        "status": "LOADED_STATIC_CANDIDATE",
        "verification_level": "CATALOG_CHAIN_ONLY_NOT_POLICY_VERIFIED",
        "policy_verified": False,
        "authority_effect": "NONE",
        "dispatch_authorized": False,
        "writer_change_authorized": False,
        "tools_checked": False,
        "candidate_only": True,
        "intent": intent,
        "domain_id": domain_id,
        "selected_capability_id": capability_id,
        "capability_ids": [capability_id],
        "loaded_paths": expected_paths,
        "raw_bytes": sum((root / path).stat().st_size for path in expected_paths),
        "modules": [
            {
                "capability_id": capability_id,
                "path": pack,
                "sha256": expected_pack_sha,
                "module_text": expected_module_text,
                "requires": [],
                "required_tools": result["modules"][0]["required_tools"],
            }
        ],
        "required_tools": result["modules"][0]["required_tools"],
        "required_tools_status": "DECLARED_ONLY_NOT_CHECKED",
    }


def test_unknown_and_invalid_intents_hold(tmp_path: Path):
    root = _minimal_repo(tmp_path)
    pin = _rehash(root)
    _assert_hold(root, "missing_intent", pin, "INTENT_UNKNOWN")
    _assert_hold(root, "project restore", pin, "INTENT_INVALID")


@pytest.mark.parametrize("pin", ["", "a" * 63, "A" * 64])
def test_external_catalog_pin_is_required_and_canonical(tmp_path: Path, pin: str):
    root = _minimal_repo(tmp_path)
    _assert_hold(root, "project_restore", pin, "CATALOG_PIN_REQUIRED")


def test_wrong_external_catalog_pin_holds_before_domain_load(tmp_path: Path):
    root = _minimal_repo(tmp_path)
    _assert_hold(root, "project_restore", "0" * 64, "CATALOG_PIN_MISMATCH")


def test_tampered_domain_and_pack_hold(tmp_path: Path):
    domain_root = _minimal_repo(tmp_path / "domain")
    domain_pin = _rehash(domain_root)
    with (domain_root / "capabilities/domains/project.json").open("ab") as handle:
        handle.write(b" ")
    _assert_hold(domain_root, "project_restore", domain_pin, "DOMAIN_HASH_MISMATCH")

    pack_root = _minimal_repo(tmp_path / "pack")
    pack_pin = _rehash(pack_root)
    with (pack_root / "capabilities/packs/project-restore.md").open("ab") as handle:
        handle.write(b"\nchanged")
    _assert_hold(pack_root, "project_restore", pack_pin, "PACK_HASH_MISMATCH")


def test_duplicate_domain_id_and_root_intent_hold(tmp_path: Path):
    root = _minimal_repo(tmp_path)
    catalog_path = root / "capabilities/catalog.json"
    catalog = _json(catalog_path)
    duplicate = dict(catalog["domains"][0])
    catalog["domains"].append(duplicate)
    _write_json(catalog_path, catalog)
    _assert_hold(root, "project_restore", _sha(catalog_path), "DUPLICATE_DOMAIN_ID")

    duplicate["id"] = "other"
    _write_json(catalog_path, catalog)
    _assert_hold(root, "project_restore", _sha(catalog_path), "AMBIGUOUS_ROOT_INTENT")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("duplicate_id", "DUPLICATE_CAPABILITY_ID"),
        ("duplicate_intent", "AMBIGUOUS_DOMAIN_INTENT"),
    ],
)
def test_duplicate_capability_identity_or_intent_holds(tmp_path: Path, mutation: str, code: str):
    root = _minimal_repo(tmp_path)
    domain_path = root / "capabilities/domains/project.json"
    domain = _json(domain_path)
    duplicate = json.loads(json.dumps(domain["capabilities"][0]))
    if mutation == "duplicate_intent":
        duplicate["id"] = "project.other"
    domain["capabilities"].append(duplicate)
    _write_json(domain_path, domain)
    pin = _rehash(root)
    _assert_hold(root, "project_restore", pin, code)


@pytest.mark.parametrize(
    "unsafe_path",
    ["../outside.json", "/capabilities/domains/project.json", "capabilities\\domains\\project.json"],
)
def test_path_traversal_or_non_posix_path_holds(tmp_path: Path, unsafe_path: str):
    root = _minimal_repo(tmp_path)
    catalog_path = root / "capabilities/catalog.json"
    catalog = _json(catalog_path)
    catalog["domains"][0]["manifest_path"] = unsafe_path
    _write_json(catalog_path, catalog)
    with pytest.raises(RouterError) as caught:
        route_capability(root, "project_restore", _sha(catalog_path))
    assert caught.value.code in {"ROOT_SCHEMA_INVALID", "PATH_INVALID", "PATH_SCOPE_INVALID"}


def test_symlink_at_any_capability_path_level_holds(tmp_path: Path):
    root = _minimal_repo(tmp_path)
    pin = _rehash(root)
    real_domain = root / "real-project.json"
    (root / "capabilities/domains/project.json").replace(real_domain)
    (root / "capabilities/domains/project.json").symlink_to(real_domain)
    _assert_hold(root, "project_restore", pin, "SYMLINK_FORBIDDEN")


def test_symlinked_pack_holds(tmp_path: Path):
    root = _minimal_repo(tmp_path)
    pin = _rehash(root)
    pack = root / "capabilities/packs/project-restore.md"
    real_pack = root / "real-project-restore.md"
    pack.replace(real_pack)
    pack.symlink_to(real_pack)
    _assert_hold(root, "project_restore", pin, "SYMLINK_FORBIDDEN")


def test_missing_pack_holds(tmp_path: Path):
    root = _minimal_repo(tmp_path)
    pin = _rehash(root)
    (root / "capabilities/packs/project-restore.md").unlink()
    _assert_hold(root, "project_restore", pin, "FILE_MISSING")


@pytest.mark.parametrize(
    "unsafe_path",
    ["capabilities/packs/project-restore.json", "capabilities/packs/nested/project-restore.md"],
)
def test_pack_illegal_extension_or_noncanonical_depth_holds(tmp_path: Path, unsafe_path: str):
    root = _minimal_repo(tmp_path)
    domain_path = root / "capabilities/domains/project.json"
    domain = _json(domain_path)
    domain["capabilities"][0]["document_path"] = unsafe_path
    _write_json(domain_path, domain)
    catalog = _json(root / "capabilities/catalog.json")
    catalog["domains"][0]["sha256"] = _sha(domain_path)
    _write_json(root / "capabilities/catalog.json", catalog)
    _assert_hold(root, "project_restore", _sha(root / "capabilities/catalog.json"), "PATH_SCOPE_INVALID")


def test_size_and_tightened_total_budgets_hold(tmp_path: Path):
    root = _minimal_repo(tmp_path)
    pack_path = root / "capabilities/packs/project-restore.md"
    pack_path.write_bytes(b"x" * (HARD_BUDGETS["max_pack_bytes"] + 1))
    pin = _rehash(root)
    _assert_hold(root, "project_restore", pin, "FILE_TOO_LARGE")

    small = _minimal_repo(tmp_path / "small")
    small_pin = _rehash(small)
    with pytest.raises(RouterError) as caught:
        route_capability(small, "project_restore", small_pin, {"max_total_bytes": 1})
    assert caught.value.code == "TOTAL_BYTES_EXCEEDED"


@pytest.mark.parametrize(
    ("dependency", "helper_requires", "code"),
    [
        ("project.helper", ["project.restore"], "DEPENDENCY_CYCLE"),
        ("project.missing", [], "DEPENDENCY_UNKNOWN_OR_CROSS_DOMAIN"),
        ("tool.route", [], "DEPENDENCY_UNKNOWN_OR_CROSS_DOMAIN"),
    ],
)
def test_cycle_unknown_and_cross_domain_dependencies_hold(
    tmp_path: Path, dependency: str, helper_requires: list[str], code: str,
):
    root = _minimal_repo(tmp_path)
    domain_path = root / "capabilities/domains/project.json"
    domain = _json(domain_path)
    domain["capabilities"][0]["requires"] = [dependency]
    if dependency == "project.helper":
        helper_path = root / "capabilities/packs/project-helper.md"
        helper_path.write_text("candidate helper only\n", encoding="utf-8")
        domain["capabilities"].append(
            {
                "id": "project.helper",
                "intents": ["project_helper"],
                "description": "Synthetic local-only dependency.",
                "risk_class": "R0",
                "side_effects": False,
                "document_path": "capabilities/packs/project-helper.md",
                "sha256": _sha(helper_path),
                "requires": helper_requires,
                "tool_requirements": [],
            }
        )
        catalog = _json(root / "capabilities/catalog.json")
        catalog["domains"][0]["intents"].append("project_helper")
        _write_json(root / "capabilities/catalog.json", catalog)
    _write_json(domain_path, domain)
    pin = _rehash(root)
    _assert_hold(root, "project_restore", pin, code)


@pytest.mark.parametrize(("field", "value"), [("risk_class", "R2"), ("side_effects", True)])
def test_non_r0_or_side_effecting_metadata_holds(tmp_path: Path, field: str, value: object):
    root = _minimal_repo(tmp_path)
    domain_path = root / "capabilities/domains/project.json"
    domain = _json(domain_path)
    domain["capabilities"][0][field] = value
    _write_json(domain_path, domain)
    pin = _rehash(root)
    _assert_hold(root, "project_restore", pin, "DOMAIN_SCHEMA_INVALID")


def test_dependency_count_budget_is_fail_closed(tmp_path: Path):
    root = _minimal_repo(tmp_path)
    domain_path = root / "capabilities/domains/project.json"
    domain = _json(domain_path)
    dependencies = []
    catalog = _json(root / "capabilities/catalog.json")
    for number in range(2):
        capability_id = f"project.dep{number}"
        dependency_intent = f"project_dep{number}"
        document = f"capabilities/packs/project-dep{number}.md"
        (root / document).write_text("candidate dependency only\n", encoding="utf-8")
        domain["capabilities"].append(
            {
                "id": capability_id,
                "intents": [dependency_intent],
                "description": "Synthetic local-only dependency.",
                "risk_class": "R0",
                "side_effects": False,
                "document_path": document,
                "sha256": _sha(root / document),
                "requires": [],
                "tool_requirements": [],
            }
        )
        dependencies.append(capability_id)
        catalog["domains"][0]["intents"].append(dependency_intent)
    domain["capabilities"][0]["requires"] = dependencies
    _write_json(domain_path, domain)
    _write_json(root / "capabilities/catalog.json", catalog)
    pin = _rehash(root)
    with pytest.raises(RouterError) as caught:
        route_capability(root, "project_restore", pin, {"max_dependencies": 1})
    assert caught.value.code == "DEPENDENCY_COUNT_EXCEEDED"


def test_dependency_depth_budget_is_fail_closed(tmp_path: Path):
    root = _minimal_repo(tmp_path)
    domain_path = root / "capabilities/domains/project.json"
    domain = _json(domain_path)
    helper_path = root / "capabilities/packs/project-helper.md"
    helper_path.write_text("candidate helper only\n", encoding="utf-8")
    domain["capabilities"][0]["requires"] = ["project.helper"]
    domain["capabilities"].append(
        {
            "id": "project.helper",
            "intents": ["project_helper"],
            "description": "Synthetic local-only dependency.",
            "risk_class": "R0",
            "side_effects": False,
            "document_path": "capabilities/packs/project-helper.md",
            "sha256": _sha(helper_path),
            "requires": [],
            "tool_requirements": [],
        }
    )
    _write_json(domain_path, domain)
    catalog = _json(root / "capabilities/catalog.json")
    catalog["domains"][0]["intents"].append("project_helper")
    _write_json(root / "capabilities/catalog.json", catalog)
    pin = _rehash(root)
    with pytest.raises(RouterError) as caught:
        route_capability(root, "project_restore", pin, {"max_depth": 1})
    assert caught.value.code == "DEPENDENCY_DEPTH_EXCEEDED"
