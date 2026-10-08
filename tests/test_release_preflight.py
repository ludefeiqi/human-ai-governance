"""S5/S8 draft Release R0 source-integrity checks: positive and malicious cases.

Synthetic responses are never presented as real GitHub draft coverage.
"""
import base64
import copy
import hashlib
import json
import subprocess

import pytest

from registry.verify_release_preflight import ReleasePreflightError, verify_draft

REPO="ludefeiqi/human-ai-governance"
TAG="v0.2.2"
COMMIT="f"*40
TAG_SHA="b"*40
MANIFEST=b"a"*64+b"  .github/CODEOWNERS\n"
EVIDENCE=b'{"policy":"v0.2.2","authorized":false}\n'
MDIGEST=hashlib.sha256(MANIFEST).hexdigest()
EDIGEST=hashlib.sha256(EVIDENCE).hexdigest()
CHECKSUMS=(
    MDIGEST.encode()+b"  v0.2.2-MANIFEST.sha256\n"+
    EDIGEST.encode()+b"  v0.2.2-release-evidence.json\n"
)
CDIGEST=hashlib.sha256(CHECKSUMS).hexdigest()
NAME_MANIFEST=f"{TAG}-MANIFEST.sha256"
NAME_EVIDENCE=f"{TAG}-release-evidence.json"


def fixture_data():
    def file(raw):
        return {"type":"file","encoding":"base64","content":base64.b64encode(raw).decode()}
    def asset(asset_id,name,raw):
        return {
            "id":asset_id,"name":name,"size":len(raw),
            "digest":"sha256:"+hashlib.sha256(raw).hexdigest(),
            "state":"uploaded","updated_at":"2026-10-09T00:00:00Z",
        }
    root=f"repos/{REPO}"
    data={
        f"{root}/branches/main":{"commit":{"sha":COMMIT}},
        f"{root}/git/ref/tags/{TAG}":{"object":{"type":"tag","sha":TAG_SHA}},
        f"{root}/git/tags/{TAG_SHA}":{"tag":TAG,"object":{
            "type":"commit","sha":COMMIT,
            "url":f"https://api.github.com/repos/{REPO}/git/commits/{COMMIT}",
        }},
        f"{root}/releases/123":{
            "id":123,"tag_name":TAG,"target_commitish":COMMIT,
            "draft":True,"immutable":False,"prerelease":False,
            "updated_at":"2026-10-09T00:00:00Z","assets":[
                asset(101,NAME_MANIFEST,MANIFEST),
                asset(102,NAME_EVIDENCE,EVIDENCE),
                asset(103,"SHA256SUMS.txt",CHECKSUMS),
            ]},
        f"{root}/contents/registry/GENESIS.json?ref={COMMIT}":
            file(json.dumps({"release_tag":TAG}).encode()),
        f"{root}/contents/MANIFEST.sha256?ref={COMMIT}":file(MANIFEST),
    }
    bytes_by_id={101:MANIFEST,102:EVIDENCE,103:CHECKSUMS}
    return data,bytes_by_id


def check(routes=None,asset_bytes=None,fetch=None,**kwargs):
    d,b=fixture_data()
    if routes is not None:d=routes
    if asset_bytes is not None:b=asset_bytes
    args={
        "repository":REPO,"tag":TAG,"release_id":123,
        "expected_tag_sha":TAG_SHA,"expected_commit":COMMIT,
        "expected_manifest_sha256":MDIGEST,
        "expected_checksums_sha256":CDIGEST,
        "get_json":lambda url:d[url] if fetch is None else fetch(url),
        "get_binary_asset":lambda asset_id:b[asset_id],
    }
    args.update(kwargs)
    return verify_draft(**args)


def test_positive_rooted_complete_prepublish_check_has_no_permissions():
    result=check()
    assert result["status"]=="DRAFT_RELEASE_PREFLIGHT_VERIFIED_R0_ONLY"
    assert result["manifest_entries"]==1 and result["downloaded_verified_assets"]==3
    assert result["policy_release_authorized"] is False
    assert result["release_published"] is False
    assert result["mutation_count"]==0
    assert result["snapshot_is_atomic_publish_lock"] is False
    assert result["publish_requires_new_readback_and_separate_human_approval"] is True
    assert len(result["rechecked_exact_snapshot_sha256"])==64


@pytest.mark.parametrize("change",[
    {"repository":"other/private"},
    {"tag":"v0.2.2;git push"},
    {"tag":"../main"},
    {"release_id":True},
    {"release_id":0},
    {"expected_tag_sha":"a"*10},
    {"expected_commit":"g"*40},
    {"expected_manifest_sha256":"f"*63},
    {"expected_checksums_sha256":"f"*63},
])
def test_input_validation_before_network(change):
    def forbid(*args):
        raise AssertionError("MUST NOT CALL NETWORK WITH BAD ARGUMENT")
    kwargs={
        "repository":REPO,"tag":TAG,"release_id":123,
        "expected_tag_sha":TAG_SHA,"expected_commit":COMMIT,
        "expected_manifest_sha256":MDIGEST,
        "expected_checksums_sha256":CDIGEST,
        "get_json":forbid,"get_binary_asset":forbid,
    }
    kwargs.update(change)
    with pytest.raises(ReleasePreflightError):
        verify_draft(**kwargs)


@pytest.mark.parametrize("suffix,mutation",[
    ("branches/main",lambda obj:obj["commit"].update({"sha":"e"*40})),
    ("git/ref/tags/"+TAG,lambda obj:obj["object"].update({"type":"commit"})),
    ("git/ref/tags/"+TAG,lambda obj:obj["object"].update({"sha":"a"*40})),
    ("git/tags/"+TAG_SHA,lambda obj:obj["object"].update({"sha":"a"*40})),
    ("releases/123",lambda obj:obj.update({"draft":False,"immutable":True})),
    ("releases/123",lambda obj:obj.update({"target_commitish":"a"*40})),
    ("releases/123",lambda obj:obj.update({"id":999})),
    ("releases/123",lambda obj:obj.update({"prerelease":True})),
    ("releases/123",lambda obj:obj["assets"].append(copy.deepcopy(obj["assets"][0]))),
    ("releases/123",lambda obj:obj["assets"][0].update({"digest":"sha256:"+"0"*64})),
    ("releases/123",lambda obj:obj["assets"][1].update({"digest":None})),
    ("releases/123",lambda obj:obj["assets"][1].update({"state":"starter"})),
    ("releases/123",lambda obj:obj["assets"][2].update({"size":0})),
    ("releases/123",lambda obj:obj["assets"].pop()),
    ("releases/123",lambda obj:obj["assets"].append({
        "id":999,"name":"unapproved.bin","size":10,
        "digest":"sha256:"+"a"*64,"state":"uploaded"})),
    ("releases/123",lambda obj:obj["assets"][0].update({"id":False})),
])
def test_remote_unapproved_release_metadata_denied(suffix,mutation):
    data,_=fixture_data()
    mutation(data[f"repos/{REPO}/{suffix}"])
    with pytest.raises(ReleasePreflightError):
        check(routes=data)


def test_external_checksum_file_root_is_not_optional():
    with pytest.raises(ReleasePreflightError) as e:
        check(expected_checksums_sha256="0"*64)
    assert str(e.value)=="CHECKSUM_FILE_EXTERNAL_SHA_MISMATCH"


def test_modified_checksum_asset_bytes_rejected():
    data,b=fixture_data()
    b[103]=CHECKSUMS.replace(EDIGEST.encode(),b"0"*64)
    with pytest.raises(ReleasePreflightError) as e:
        check(routes=data,asset_bytes=b)
    assert str(e.value)=="CHECKSUM_FILE_EXTERNAL_SHA_MISMATCH"


def test_modified_evidence_asset_bytes_rejected():
    data,b=fixture_data()
    b[102]=b"X"*len(EVIDENCE)
    with pytest.raises(ReleasePreflightError) as e:
        check(routes=data,asset_bytes=b)
    assert str(e.value)=="ASSET_DOWNLOADED_BYTES_SHA_MISMATCH"


def test_whitelist_rejects_extra_even_if_manifest_asset_is_intact():
    data,b=fixture_data()
    data[f"repos/{REPO}/releases/123"]["assets"][1]["name"]="renamed-evidence.json"
    with pytest.raises(ReleasePreflightError) as e:check(routes=data,asset_bytes=b)
    assert str(e.value)=="RELEASE_ASSET_SET_UNEXPECTED"


def test_genesis_tag_bypass_rejected():
    data,b=fixture_data()
    key=f"repos/{REPO}/contents/registry/GENESIS.json?ref={COMMIT}"
    data[key]["content"]=base64.b64encode(b'{"release_tag":"v0.2.1"}').decode()
    with pytest.raises(ReleasePreflightError) as e:check(routes=data,asset_bytes=b)
    assert str(e.value)=="TAG_GENESIS_MISMATCH"


def test_remote_manifest_modified_but_asset_same_is_rejected():
    data,b=fixture_data()
    key=f"repos/{REPO}/contents/MANIFEST.sha256?ref={COMMIT}"
    data[key]["content"]=base64.b64encode(MANIFEST+b"tampered").decode()
    with pytest.raises(ReleasePreflightError) as e:check(routes=data,asset_bytes=b)
    assert str(e.value)=="REMOTE_MANIFEST_RAW_SHA_MISMATCH"


@pytest.mark.parametrize("component",[
    "branches/main","git/ref/tags/"+TAG,"git/tags/"+TAG_SHA,"releases/123",
])
def test_ref_or_asset_metadata_drift_on_second_read_is_blocked(component):
    data,blobs=fixture_data()
    key=f"repos/{REPO}/{component}"
    count=[0]
    def changing_get(url):
        obj=copy.deepcopy(data[url])
        if url==key:
            count[0]+=1
            if count[0]==2:
                if component=="branches/main":obj["commit"]["sha"]="e"*40
                elif component.startswith("git/ref"):obj["object"]["sha"]="a"*40
                elif component.startswith("git/tags"):obj["object"]["sha"]="a"*40
                else:
                    obj["assets"][0]["id"]=777
        return obj
    with pytest.raises(ReleasePreflightError) as e:
        check(fetch=changing_get,asset_bytes=blobs)
    assert str(e.value) in {"RELEASE_OR_REF_CHANGED_DURING_PREFLIGHT","GITHUB_READ_OBJECT_MISSING"}


def test_core_has_zero_internal_shell_invocations(monkeypatch):
    def forbid(*args,**kwargs):raise AssertionError("NO_SUBPROCESS_FROM_PURE_CORE")
    monkeypatch.setattr(subprocess,"run",forbid)
    assert check()["mutation_count"]==0


def test_user_inputs_are_env_parameters_and_never_shell_templates():
    from tests.test_gh_native_version_control import workflow
    job=workflow()["jobs"]["preflight-draft"]
    joined="\n".join(step.get("run","") for step in job["steps"])
    env=job["env"]
    assert job["if"]=="github.event_name == 'workflow_dispatch'"
    assert len({k for k in env if k!="GH_TOKEN"})==6
    assert "github.token" in env["GH_TOKEN"]
    assert "inputs.tag" in env["RELEASE_TAG"]
    assert "inputs.release_id" in env["RELEASE_ID"]
    assert "inputs.expected_checksums_sha256" in env["EXPECTED_CHECKSUMS"]
    assert "--expected-checksums-sha256" in joined
    assert "registry.verify_release_preflight" in joined and "audit-main" in joined
    assert chr(36)+"{{" not in joined
