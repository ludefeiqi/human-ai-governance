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

def test_immutable_v022_base_and_candidate_core_are_distinct():
    g=json.loads((ROOT/"registry/GENESIS.json").read_text())
    assert g["release_tag"]=="v0.2.2"
    assert "v0.2.2（Immutable Release" in (ROOT/"GOVERNANCE.md").read_text()
    assert "HAG-CORE-001" in (ROOT/"GOVERNANCE.md").read_text()

def test_governance_top_level_follows_current_public_single_owner_version():
    owner=(ROOT/"GOVERNANCE.md").read_text()
    lead=owner.split("## G0",1)[0]
    release=owner.split("### G2-RELEASE-01 发布合同",1)[1].split("### G2-SOURCE-02",1)[0]
    assert "正式公开政策为 v0.2.2" in lead
    assert "未授权、未发布、未采用" in lead
    assert "v0.2.1 整理候选" not in lead
    assert "已发布 v0.2.0 保持不变" not in lead
    for required in (
        "Public", "main.protected=true",
        "required_approving_review_count=0",
        "require_last_push_approval=false",
        "CODEOWNERS 只是归属信息",
        "用户准确发布批准",
        "HTTP 403 是历史事实",
    ):
        assert required in release,required
    assert "个人私库当前套餐的 403 必须明示" not in release
    assert "AI 独立只读复核" in release


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


# HAG-CORE-001 candidate: tests are review tripwires, not independent authorization.
def _core_charter():
    source=(ROOT/"GOVERNANCE.md").read_text(encoding="utf-8")
    begin="<!-- HAG-CORE-001:BEGIN -->"
    end="<!-- HAG-CORE-001:END -->"
    assert source.count(begin)==1 and source.count(end)==1
    assert source.index(begin)<source.index(end)<source.index("## G0 治理宪章")
    return source.split(begin,1)[1].split(end,1)[0]


def test_core_charter_12_invariants_have_exactly_one_id():
    core=_core_charter()
    found=re.findall(r"\*\*K(\d{2}) ",core)
    assert found==[f"{i:02d}" for i in range(1,13)]
    assert "五个不可变职责域" in core and "不存在独立的 Global Observation 治理层" in core


def test_core_charter_has_six_extension_admission_gates_and_five_nodes():
    core=_core_charter()
    assert re.findall(r"\*\*N(\d) ",core)==[str(i) for i in range(1,7)]
    for role in ("Human","Governance","Controller","Projects","Execution"):
        assert f"**{role}**" in core
    assert "NOT_ADMITTED" in core and "CANDIDATE / NOT_ADOPTED" in core
    assert "IMPLEMENTATION_AUTHORIZED" in core and "ACTIVATION_AUTHORIZED" in core
    assert "DOCUMENTED_NOT_ENFORCED" in core


def test_core_charter_single_normative_home_and_dev_entrypoints():
    core=_core_charter()
    for label in ("C01","C02","C03","C04","C05","C06","C07","C08","C09","C10","C11","C12"):
        assert re.search(rf"^### {label}｜",core,re.M)
    agent=(ROOT/"AGENTS.md").read_text(encoding="utf-8")
    review=(ROOT/"REVIEW-CHECKLIST.md").read_text(encoding="utf-8")
    index=(ROOT/"README.md").read_text(encoding="utf-8")
    assert "N1—N6" in agent and "CORE_CHANGE_REVIEW_REQUIRED" in agent
    assert "HAG-CORE-001" in review and "HAG-CORE-001" in index
    assert "v0.2.2 Immutable Release" in index


def test_core_charter_exact_byte_tripwire_for_normal_extensions():
    # The checksum is NOT a signature or an independent check: a changing
    # charter and its test are a core amendment requiring independent approval.
    from hashlib import sha256
    assert sha256(_core_charter().encode("utf-8")).hexdigest()=="82d2deeff661b02e3b3f0e292019d026b66a2fa789c058079d885c4bbc749263"
