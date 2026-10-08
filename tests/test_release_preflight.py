"""Synthetic negative and positive tests for a pure, read-only draft gate."""

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
DIGEST=hashlib.sha256(MANIFEST).hexdigest()


def fixture_data():
    def file(raw):
        return {"type":"file","encoding":"base64","content":base64.b64encode(raw).decode()}
    p=f"repos/{REPO}"
    return {
        f"{p}/branches/main":{"commit":{"sha":COMMIT}},
        f"{p}/git/ref/tags/{TAG}":{"object":{"type":"tag","sha":TAG_SHA}},
        f"{p}/git/tags/{TAG_SHA}":{"tag":TAG,"object":{"type":"commit","sha":COMMIT}},
        f"{p}/releases/123":{"tag_name":TAG,"target_commitish":COMMIT,"draft":True,
            "immutable":False,"prerelease":False,"assets":[
                {"name":f"{TAG}-MANIFEST.sha256","size":len(MANIFEST),"digest":"sha256:"+DIGEST},
                {"name":"SHA256SUMS.txt","size":80,"digest":"sha256:"+"c"*64},
            ]},
        f"{p}/contents/registry/GENESIS.json?ref={COMMIT}":file(json.dumps({"release_tag":TAG}).encode()),
        f"{p}/contents/MANIFEST.sha256?ref={COMMIT}":file(MANIFEST),
    }


def check(routes=None,**kwargs):
    data=fixture_data() if routes is None else routes
    args={"repository":REPO,"tag":TAG,"release_id":123,"expected_tag_sha":TAG_SHA,
          "expected_commit":COMMIT,"expected_manifest_sha256":DIGEST,
          "gh_api":lambda url:data[url]}
    args.update(kwargs)
    return verify_draft(**args)


def test_valid_preflight_is_explicitly_non_authorizing():
    result=check()
    assert result["status"]=="DRAFT_RELEASE_PREFLIGHT_VERIFIED"
    assert result["manifest_entries"]==1 and result["assets_checked"]==2
    assert result["mutation_count"]==0
    assert result["policy_release_authorized"] is False
    assert result["release_published"] is False


@pytest.mark.parametrize("kwargs",[
    {"repository":"other/private"},
    {"tag":"v0.2.2;git push"},
    {"tag":"../main"},
    {"release_id":True},
    {"release_id":0},
    {"expected_tag_sha":"a"*10},
    {"expected_commit":"g"*40},
    {"expected_manifest_sha256":"f"*63},
])
def test_bad_input_denied_before_gh_api(kwargs):
    def no_calls(url):
        raise AssertionError("No network should be reached")
    data={"repository":REPO,"tag":TAG,"release_id":123,"expected_tag_sha":TAG_SHA,
          "expected_commit":COMMIT,"expected_manifest_sha256":DIGEST,
          "gh_api":no_calls}
    data.update(kwargs)
    with pytest.raises(ReleasePreflightError):
        verify_draft(**data)


@pytest.mark.parametrize("suffix,mutate",[
    ("branches/main",lambda obj:obj["commit"].update({"sha":"a"*40})),
    ("git/ref/tags/"+TAG,lambda obj:obj["object"].update({"type":"commit"})),
    ("git/ref/tags/"+TAG,lambda obj:obj["object"].update({"sha":"c"*40})),
    ("git/tags/"+TAG_SHA,lambda obj:obj["object"].update({"sha":"a"*40})),
    ("releases/123",lambda obj:obj.update({"draft":False,"immutable":True})),
    ("releases/123",lambda obj:obj.update({"target_commitish":"a"*40})),
    ("releases/123",lambda obj:obj["assets"].append(copy.deepcopy(obj["assets"][0]))),
    ("releases/123",lambda obj:obj["assets"][0].update({"digest":"sha256:"+"0"*64})),
    ("releases/123",lambda obj:obj["assets"][1].update({"digest":None})),
    ("releases/123",lambda obj:obj["assets"][1].update({"size":0})),
    ("releases/123",lambda obj:obj["assets"].pop()),
])
def test_remote_unsafe_release_and_asset_states_fail_closed(suffix,mutate):
    data=fixture_data()
    mutate(data[f"repos/{REPO}/{suffix}"])
    with pytest.raises(ReleasePreflightError):
        check(data)


def test_genesis_different_release_tag_rejected():
    data=fixture_data()
    key=f"repos/{REPO}/contents/registry/GENESIS.json?ref={COMMIT}"
    data[key]["content"]=base64.b64encode(b'{"release_tag":"v0.2.1"}').decode()
    with pytest.raises(ReleasePreflightError) as e:check(data)
    assert str(e.value)=="TAG_GENESIS_MISMATCH"


def test_manifest_source_digest_mismatch_rejected():
    data=fixture_data()
    key=f"repos/{REPO}/contents/MANIFEST.sha256?ref={COMMIT}"
    data[key]["content"]=base64.b64encode(MANIFEST+b"tampered").decode()
    with pytest.raises(ReleasePreflightError) as e:check(data)
    assert str(e.value)=="REMOTE_MANIFEST_RAW_SHA256_MISMATCH"


def test_pure_core_never_uses_process_or_shell(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError("Unexpected subprocess")
    monkeypatch.setattr(subprocess,"run",forbidden)
    assert check()["mutation_count"]==0


def test_manual_dispatch_inputs_are_env_bound_not_shell_interpolated():
    from tests.test_gh_native_version_control import workflow
    w=workflow()
    job=w["jobs"]["preflight-draft"]
    joined="\n".join(step.get("run","") for step in job["steps"])
    env=job["env"]
    assert "verify_release_preflight" in joined and "audit-main" in joined
    assert "github.token" in env["GH_TOKEN"]
    assert "inputs.tag" in env["RELEASE_TAG"]
    assert "inputs.release_id" in env["RELEASE_ID"]
    assert "inputs.expected_commit" in env["EXPECTED_COMMIT"]
    assert chr(36)+"{{" not in joined
    assert job["if"]=="github.event_name == 'workflow_dispatch'"
