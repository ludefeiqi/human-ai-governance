from pathlib import Path
import json,re,zipfile
import pytest
from clients.build_plugin_overlay import build
ROOT=Path(__file__).resolve().parents[1]

def test_all_g0_g6_have_unique_stable_rule_ids():
    text=(ROOT/"GOVERNANCE.md").read_text()
    ids=re.findall(r"^### (G[0-6]-[A-Z]+-\d+)",text,re.M)
    assert len(ids)==len(set(ids))>=18
    assert {i[:2] for i in ids}=={f"G{i}" for i in range(7)}

def test_all_rule_references_resolve_to_one_normative_location():
    owner=(ROOT/"GOVERNANCE.md").read_text()
    ids=set(re.findall(r"^### (G[0-6]-[A-Z]+-\d+)",owner,re.M))
    for name in ("CLIENT-CONTRACT.md","CODEX-PROTOCOL.md","HANDOFF.md","RULE-MAP.md","REVIEW-CHECKLIST.md"):
        refs=set(re.findall(r"G[0-6]-[A-Z]+-\d+",(ROOT/name).read_text()))
        assert refs<=ids,(name,refs-ids)

def test_one_governance_authority_not_seven_agents():
    t=(ROOT/"GOVERNANCE.md").read_text()
    assert "不是 Agent 数量" in t and "不是第二个治理权威" in t
    assert "领域" in t and "不自动" in t

def test_candidate_tag_v022_does_not_alter_published_v021():
    g=json.loads((ROOT/"registry/GENESIS.json").read_text())
    assert g["release_tag"]=="v0.2.2"
    assert "v0.2.2 候选" in (ROOT/"GOVERNANCE.md").read_text()

def test_plugin_overlay_pins_only_the_released_v020():
    plan=json.loads((ROOT/"clients/plugin-update.json").read_text())
    lock=(ROOT/plan["overlay_root"]/"skills/governance-bootstrap/references/source-lock.md").read_text()
    assert plan["installed"] is False and plan["published"] is False
    assert plan["policy_commit"]=="7aced01a8c12e1bba5e810ce91ab425f4615d4a7"
    assert plan["policy_commit"] in lock and "manifest_files: 20" in lock
    assert "7aced01" not in (ROOT/plan["overlay_root"]/"skills/governance-bootstrap/references/role-contract.md").read_text()

def test_overlay_has_no_hardcoded_project_or_new_execution_rights():
    base=ROOT/"clients/chatgpt-plugin/skills/governance-bootstrap"
    skill=(base/"SKILL.md").read_text()
    assert "hot-auth-bbs" not in skill
    assert "VALIDATOR_UNAVAILABLE" in skill and "STATE_RESTORED" in skill
    assert "不预设项目ID" in skill and "不因此开启任何副作用" in skill
    for file in base.rglob("*.md"):
        text=file.read_text()
        for ref in re.findall(r"references/[a-z-]+\.md",text):
            assert (base/ref).exists() or ref=="references/decision-engine.md",ref

def source_snapshot():
    plan=json.loads((ROOT/"clients/plugin-update.json").read_text())
    data={"name":"human-ai-governance-bootstrap","version":"0.2.0","author":{"name":"Synthetic owner"},"keep_this":{"capability":"unchanged"}}
    return {"plugin":{"plugin_id":plan["plugin_id"],"current_release_id":plan["expected_release_id"],"version":"0.2.0","scope":"USER","discoverability":"PRIVATE"},
            "contents":{p:json.dumps(data) for p in ("plugin.json",".codex-plugin/plugin.json")}}

def test_plugin_builder_preserves_original_metadata_and_never_installs(tmp_path):
    snap=source_snapshot();out=tmp_path/"overlay.zip"
    result=build(ROOT,snap,out)
    assert result["installed"] is False
    with zipfile.ZipFile(out) as z:
        for path in ("plugin.json",".codex-plugin/plugin.json"):
            updated=json.loads(z.read(path));before=json.loads(snap["contents"][path])
            assert updated.pop("version")=="0.3.0-rc.1"
            before.pop("version");assert updated==before
        assert "skills/governance-bootstrap/references/decision-engine.md" not in z.namelist()

@pytest.mark.parametrize("field,value",[("current_release_id","drift"),("plugin_id","unrelated"),("scope","WORKSPACE"),("discoverability","PUBLIC")])
def test_plugin_builder_rejects_release_or_identity_drift(tmp_path,field,value):
    snap=source_snapshot();snap["plugin"][field]=value
    with pytest.raises(ValueError): build(ROOT,snap,tmp_path/"overlay.zip")
    assert not (tmp_path/"overlay.zip").exists()

def test_rule_map_marks_semantic_changes_not_cosmetic_only():
    text=(ROOT/"RULE-MAP.md").read_text()
    assert "真实语义变更" in text and "post-merge" in text
    assert "不是另一个治理规则来源" in text
