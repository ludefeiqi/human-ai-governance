"""Read-only GitHub draft Release preflight, never publishing or mutating refs.

This verifies existing staged assets BEFORE GitHub locks them on publication.
Its result is only an integrity gate, not a substitute for a human release
approval, an authorized PR merge, or post-publication native audit-main.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
from typing import Any, Callable

REPO = "ludefeiqi/human-ai-governance"
TAG = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReleasePreflightError(ValueError):
    """Fail-closed reason without containing a private API response body."""


def _must(condition: bool, reason: str) -> None:
    if not condition:
        raise ReleasePreflightError(reason)


def _get(gh_api: Callable[[str], Any], url: str) -> dict[str, Any]:
    obj = gh_api(url)
    _must(type(obj) is dict, "GITHUB_OBJECT_INVALID")
    return obj


def verify_draft(
    repository: str,
    tag: str,
    release_id: int,
    expected_tag_sha: str,
    expected_commit: str,
    expected_manifest_sha256: str,
    gh_api: Callable[[str], Any],
) -> dict[str, Any]:
    """A PURE validation pass over read-only GET data from a caller.

    No mutation, GitHub auth changes or tag creation is performed.
    """
    _must(repository == REPO, "REPOSITORY_NOT_ALLOWLISTED")
    _must(type(tag) is str and bool(TAG.fullmatch(tag)), "TAG_INVALID")
    _must(type(release_id) is int and release_id > 0, "RELEASE_ID_INVALID")
    _must(type(expected_tag_sha) is str and bool(SHA40.fullmatch(expected_tag_sha)), "TAG_OBJECT_SHA_INVALID")
    _must(type(expected_commit) is str and bool(SHA40.fullmatch(expected_commit)), "COMMIT_SHA_INVALID")
    _must(type(expected_manifest_sha256) is str and bool(SHA256.fullmatch(expected_manifest_sha256)), "MANIFEST_SHA_INVALID")
    prefix=f"repos/{repository}"

    main=_get(gh_api,f"{prefix}/branches/main")
    _must(main.get("commit",{}).get("sha")==expected_commit, "MAIN_COMMIT_DRIFT")
    ref=_get(gh_api,f"{prefix}/git/ref/tags/{tag}")
    obj=ref.get("object",{})
    _must(obj.get("type")=="tag" and obj.get("sha")==expected_tag_sha, "ANNOTATED_TAG_OBJECT_MISMATCH")
    tag_object=_get(gh_api,f"{prefix}/git/tags/{expected_tag_sha}")
    dereferenced=tag_object.get("object",{})
    _must(tag_object.get("tag")==tag and dereferenced.get("type")=="commit" and dereferenced.get("sha")==expected_commit,
          "TAG_TARGET_MISMATCH")

    release=_get(gh_api,f"{prefix}/releases/{release_id}")
    _must(release.get("tag_name")==tag, "RELEASE_TAG_MISMATCH")
    _must(release.get("target_commitish")==expected_commit, "RELEASE_TARGET_MISMATCH")
    _must(release.get("draft") is True and release.get("immutable") is False, "RELEASE_ALREADY_PUBLISHED_OR_IMMUTABLE")
    _must(release.get("prerelease") is False, "PRERELEASE_NOT_ALLOWED_FOR_POLICY")
    assets=release.get("assets")
    _must(type(assets) is list and len(assets)>=2, "RELEASE_ASSETS_MISSING")
    names=[a.get("name") for a in assets if isinstance(a,dict)]
    _must(len(names)==len(assets) and len(names)==len(set(names)), "RELEASE_ASSETS_DUPLICATE")
    for item in assets:
        d=item.get("digest")
        _must(isinstance(d,str) and d.startswith("sha256:") and bool(SHA256.fullmatch(d.removeprefix("sha256:"))),
              "ASSET_DIGEST_UNAVAILABLE")
        _must(type(item.get("size")) is int and item["size"]>0, "RELEASE_ASSET_EMPTY")
    expected_name=f"{tag}-MANIFEST.sha256"
    by_name={a["name"]:a for a in assets}
    _must(expected_name in by_name and "SHA256SUMS.txt" in by_name, "REQUIRED_RELEASE_ASSET_MISSING")
    _must(by_name[expected_name]["digest"]=="sha256:"+expected_manifest_sha256, "RELEASE_MANIFEST_ASSET_MISMATCH")

    genesis_file=_get(gh_api,f"{prefix}/contents/registry/GENESIS.json?ref={expected_commit}")
    manifest_file=_get(gh_api,f"{prefix}/contents/MANIFEST.sha256?ref={expected_commit}")
    _must(genesis_file.get("type")=="file" and manifest_file.get("type")=="file", "SOURCE_FILES_NOT_REGULAR")
    _must(genesis_file.get("encoding")=="base64" and manifest_file.get("encoding")=="base64", "SOURCE_BYTES_UNAVAILABLE")
    try:
        genesis_raw=base64.b64decode("".join(genesis_file["content"].split()),validate=True)
        manifest_raw=base64.b64decode("".join(manifest_file["content"].split()),validate=True)
        genesis=json.loads(genesis_raw.decode("utf-8"))
    except (ValueError, KeyError, UnicodeError, AttributeError) as exc:
        raise ReleasePreflightError("SOURCE_BYTES_INVALID") from exc
    _must(type(genesis) is dict and genesis.get("release_tag")==tag, "TAG_GENESIS_MISMATCH")
    _must(hashlib.sha256(manifest_raw).hexdigest()==expected_manifest_sha256, "REMOTE_MANIFEST_RAW_SHA256_MISMATCH")
    try:
        entries=[line.split("  ",1) for line in manifest_raw.decode("ascii").splitlines()]
        _must(len(entries)>0 and len(entries)<256 and all(len(pair)==2 for pair in entries),"MANIFEST_ENTRIES_INVALID")
        paths=[pair[1] for pair in entries]
        _must(len(paths)==len(set(paths)) and all(bool(SHA256.fullmatch(pair[0])) for pair in entries),"MANIFEST_ENTRIES_INVALID")
    except (UnicodeError, ValueError) as exc:
        raise ReleasePreflightError("MANIFEST_ENTRIES_INVALID") from exc

    return {
        "status":"DRAFT_RELEASE_PREFLIGHT_VERIFIED",
        "repository":repository,"tag":tag,
        "release_id":release_id,"policy_commit":expected_commit,
        "annotated_tag_object":expected_tag_sha,
        "manifest_sha256":expected_manifest_sha256,"manifest_entries":len(entries),
        "assets_checked":len(assets),"mutation_count":0,
        "policy_release_authorized":False,"release_published":False,
    }


def _github_api(url: str) -> Any:
    process=subprocess.run(
        ["gh","api","--method","GET",url],
        capture_output=True,text=True,timeout=50,check=False,
    )
    _must(process.returncode==0, "GITHUB_API_READ_FAILED")
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise ReleasePreflightError("GITHUB_API_JSON_INVALID") from exc


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag",required=True)
    parser.add_argument("--release-id",required=True,type=int)
    parser.add_argument("--expected-tag-object-sha",required=True)
    parser.add_argument("--expected-commit",required=True)
    parser.add_argument("--expected-manifest-sha256",required=True)
    args=parser.parse_args()
    try:
        result=verify_draft(
            os.environ.get("GITHUB_REPOSITORY",""),
            args.tag,args.release_id,args.expected_tag_object_sha,
            args.expected_commit,args.expected_manifest_sha256,_github_api,
        )
    except ReleasePreflightError as exc:
        print(json.dumps({"status":"HOLD","reason":str(exc),"published":False}))
        raise SystemExit(1) from None
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
