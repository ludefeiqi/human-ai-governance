from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

import pytest
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES = ROOT / "capabilities"
SCHEMA_PATH = CAPABILITIES / "catalog.schema.json"
CATALOG_PATH = CAPABILITIES / "catalog.json"

EXPECTED_DOMAINS = {
    "project": {
        "intents": ("global_restore", "project_restore"),
        "capability": "project.restore",
        "manifest": "capabilities/domains/project.json",
        "document": "capabilities/packs/project-restore.md",
    },
    "codex": {
        "intents": ("codex_observe",),
        "capability": "codex.observe",
        "manifest": "capabilities/domains/codex.json",
        "document": "capabilities/packs/codex-observe.md",
    },
    "tools": {
        "intents": ("tool_select",),
        "capability": "tool.route",
        "manifest": "capabilities/domains/tools.json",
        "document": "capabilities/packs/tool-routing.md",
    },
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repository_file(relative: str) -> Path:
    pure = PurePosixPath(relative)
    assert not pure.is_absolute()
    assert ".." not in pure.parts
    assert pure.parts and pure.parts[0] == "capabilities"
    path = ROOT.joinpath(*pure.parts)
    assert path.resolve().is_relative_to(CAPABILITIES.resolve())
    assert path.is_file() and not path.is_symlink()
    return path


@pytest.fixture(scope="module")
def schema() -> dict:
    value = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(value)
    assert value["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(value["$defs"]) == {"Root", "Domain"}
    return value


def test_schema_is_closed_and_rejects_dangerous_or_unknown_structure(schema):
    validator = Draft202012Validator(schema)
    catalog = load_json(CATALOG_PATH)
    validator.validate(catalog)

    extra = {**catalog, "authorization": "granted"}
    with pytest.raises(ValidationError):
        validator.validate(extra)

    traversal = json.loads(json.dumps(catalog))
    traversal["domains"][0]["manifest_path"] = "../outside.json"
    with pytest.raises(ValidationError):
        validator.validate(traversal)


def test_catalog_identity_and_exact_domain_summary(schema):
    catalog = load_json(CATALOG_PATH)
    Draft202012Validator(schema).validate(catalog)
    assert catalog["format"] == "hagov.capability-root.v1"
    assert catalog["version"] == 1
    assert catalog["candidate_only"] is True
    assert [item["id"] for item in catalog["domains"]] == ["project", "codex", "tools"]
    assert set(catalog["domains"][0]) == {
        "id", "description", "intents", "manifest_path", "sha256"
    }
    for item in catalog["domains"]:
        expected = EXPECTED_DOMAINS[item["id"]]
        assert tuple(item["intents"]) == expected["intents"]
        assert item["manifest_path"] == expected["manifest"]


def test_each_domain_and_pack_has_exact_raw_sha256(schema):
    validator = Draft202012Validator(schema)
    catalog = load_json(CATALOG_PATH)
    seen_capabilities = set()
    seen_intents = set()

    for summary in catalog["domains"]:
        domain_path = repository_file(summary["manifest_path"])
        assert raw_sha256(domain_path) == summary["sha256"]
        domain = load_json(domain_path)
        validator.validate(domain)
        assert domain["domain_id"] == summary["id"]
        assert len(domain["capabilities"]) == 1

        capability = domain["capabilities"][0]
        expected = EXPECTED_DOMAINS[summary["id"]]
        assert capability["id"] == expected["capability"]
        assert tuple(capability["intents"]) == expected["intents"]
        assert capability["risk_class"] == "R0"
        assert capability["side_effects"] is False
        assert capability["requires"] == []
        assert capability["document_path"] == expected["document"]
        pack_path = repository_file(capability["document_path"])
        assert raw_sha256(pack_path) == capability["sha256"]

        assert not (seen_capabilities & {capability["id"]})
        assert not (seen_intents & set(capability["intents"]))
        seen_capabilities.add(capability["id"])
        seen_intents.update(capability["intents"])

    assert seen_capabilities == {"project.restore", "codex.observe", "tool.route"}
    assert seen_intents == {"global_restore", "project_restore", "codex_observe", "tool_select"}


def test_references_stay_inside_the_static_capability_file_set():
    expected_files = {
        "capabilities/catalog.schema.json",
        "capabilities/catalog.json",
        *(value["manifest"] for value in EXPECTED_DOMAINS.values()),
        *(value["document"] for value in EXPECTED_DOMAINS.values()),
    }
    actual_files = {
        path.relative_to(ROOT).as_posix()
        for path in CAPABILITIES.rglob("*")
        if path.is_file()
    }
    assert actual_files == expected_files


def test_one_intent_static_load_contract_needs_only_one_domain_and_one_pack():
    catalog = load_json(CATALOG_PATH)
    for intent in {intent for value in EXPECTED_DOMAINS.values() for intent in value["intents"]}:
        matching_summaries = [item for item in catalog["domains"] if intent in item["intents"]]
        assert len(matching_summaries) == 1
        summary = matching_summaries[0]
        domain = load_json(repository_file(summary["manifest_path"]))
        matching_capabilities = [
            capability for capability in domain["capabilities"] if intent in capability["intents"]
        ]
        assert len(matching_capabilities) == 1
        capability = matching_capabilities[0]
        assert capability["requires"] == []
        assert repository_file(capability["document_path"]).is_file()

        static_load_set = {
            "capabilities/catalog.schema.json",
            "capabilities/catalog.json",
            summary["manifest_path"],
            capability["document_path"],
        }
        assert len(static_load_set) == 4
        assert not any(
            other["manifest_path"] in static_load_set
            for other in catalog["domains"]
            if other["id"] != summary["id"]
        )
