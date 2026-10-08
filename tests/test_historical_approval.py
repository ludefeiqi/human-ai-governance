from pathlib import Path
import copy
import pytest
from registry.validate_registry import load_schema, validate_post_merge, validate_pre_merge, RegistryError
from tests.test_single_owner_approval import b_fixture, REPO, CI_ID, AI_ID, OWNER_ID, OWNER_TIME, MERGE_TIME, PR_ENDPOINT, COMMENTS_ENDPOINT
from tests.helpers import FakeApi, SHA_B, SHA_C

@pytest.fixture
def case():
    schema=load_schema(Path("registry/projects.schema.json"))
    gen,routes=b_fixture(schema)
    routes[PR_ENDPOINT].update(merged=True,state="closed",merged_at=MERGE_TIME,merge_commit_sha=SHA_C)
    return schema,gen,routes

def post(case):
    schema,gen,routes=case
    return validate_post_merge(FakeApi(routes),gen,schema,5,SHA_B,SHA_C,expected_policy_commit="e"*40)

def allkey():
    return (f"repos/{REPO}/commits/{SHA_B}/check-runs", (("filter","all"),("per_page","100")))

def later_run(routes, started="2026-10-08T03:00:00Z", completed="2026-10-08T03:01:00Z", conclusion="failure"):
    run=copy.deepcopy(routes[f"repos/{REPO}/check-runs/{CI_ID}"])
    run.update(id=CI_ID+1, started_at=started, completed_at=completed, conclusion=conclusion)
    routes[allkey()]["check_runs"].append(run);routes[allkey()]["total_count"]+=1
    routes[(f"repos/{REPO}/commits/{SHA_B}/check-runs",(("filter","latest"),("per_page","100")))]["check_runs"]=[run]

@pytest.mark.parametrize("conclusion",["failure","success","cancelled"])
def test_later_run_does_not_revoke_valid_historical_approval(case,conclusion):
    later_run(case[2],conclusion=conclusion)
    result=post(case).as_dict()
    assert result["verification_scope"]=="HISTORICAL_APPROVAL_ONLY"
    assert result["current_health"]=="NOT_EVALUATED"
    assert result["current_execution_authorized"] is False

def test_pre_merge_still_rejects_newer_check(case):
    later_run(case[2]);schema,gen,routes=case
    routes[PR_ENDPOINT].update(merged=False,state="open",merged_at=None)
    with pytest.raises(RegistryError) as e:
        validate_pre_merge(FakeApi(routes),gen,schema,5,SHA_B,expected_policy_commit="e"*40)
    assert e.value.code=="AI_B_CI_STALE"

@pytest.mark.parametrize("completed,conclusion",[("2026-10-08T01:30:00Z","failure"),("2026-10-08T02:30:00Z","success")])
def test_run_started_before_merge_not_ignored(case,completed,conclusion):
    later_run(case[2],started="2026-10-08T01:20:00Z",completed=completed,conclusion=conclusion)
    with pytest.raises(RegistryError) as e: post(case)
    assert e.value.code==("AI_B_CI_NOT_COMPLETE_AT_MERGE" if completed >= MERGE_TIME else "AI_B_CI_NOT_LATEST_AT_MERGE")

def test_edited_original_comment_still_holds(case):
    case[2][COMMENTS_ENDPOINT][0]["updated_at"]="2026-10-08T03:00:00Z"
    with pytest.raises(RegistryError) as e: post(case)
    assert e.value.code=="AI_B_COMMENT_EDITED"

def test_original_ci_revocation_still_holds(case):
    case[2][f"repos/{REPO}/check-runs/{CI_ID}"]["conclusion"]="failure"
    with pytest.raises(RegistryError) as e: post(case)
    assert e.value.code=="AI_B_CI_NOT_VERIFIED"

def test_later_owner_comment_cannot_rewrite_past_but_pre_merge_rejects(case):
    schema,gen,routes=case
    late=copy.deepcopy(routes[COMMENTS_ENDPOINT][-1]);late.update(id=OWNER_ID+22,created_at="2026-10-08T03:00:00Z",updated_at="2026-10-08T03:00:00Z")
    late["body"]=late["body"].replace("project_authority_effect=NONE","project_authority_effect=WRITER")
    routes[COMMENTS_ENDPOINT].append(late)
    assert post(case).as_dict()["current_execution_authorized"] is False
    with pytest.raises(RegistryError) as e:
        validate_pre_merge(FakeApi(routes),gen,schema,5,SHA_B,expected_policy_commit="e"*40)
    assert e.value.code=="AI_B_OWNER_APPROVAL_MISMATCH"

def test_deleted_original_owner_cannot_use_later_approval(case):
    routes=case[2];late=copy.deepcopy(routes[COMMENTS_ENDPOINT][-1]);late.update(id=OWNER_ID+22,created_at="2026-10-08T03:00:00Z",updated_at="2026-10-08T03:00:00Z")
    routes[COMMENTS_ENDPOINT]=[routes[COMMENTS_ENDPOINT][0],late]
    with pytest.raises(RegistryError) as e: post(case)
    assert e.value.code=="AI_B_OWNER_APPROVAL_MISSING"

@pytest.mark.parametrize("count",[101,0])
def test_incomplete_ci_history_holds(case,count):
    case[2][allkey()]["total_count"]=count
    with pytest.raises(RegistryError) as e: post(case)
    assert e.value.code=="AI_B_CI_HISTORY_UNAVAILABLE"

def test_unknown_later_run_start_time_holds(case):
    later_run(case[2]);del case[2][allkey()]["check_runs"][-1]["started_at"]
    with pytest.raises(RegistryError) as e: post(case)
    assert e.value.code=="AI_B_CI_HISTORY_TIME_UNPROVEN"


def test_older_start_but_later_failure_before_merge_blocks(case):
    later_run(case[2],started="2026-10-08T00:01:00Z",completed="2026-10-08T01:55:00Z")
    with pytest.raises(RegistryError) as e: post(case)
    assert e.value.code=="AI_B_CI_NOT_LATEST_AT_MERGE"
