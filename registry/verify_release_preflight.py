"""Strict read-only audit of a GitHub DRAFT before irreversible publication.

The expected checksum-file SHA256 is an independent human-approved release
input. It roots every other asset digest, unlike comparing only GitHub-returned
metadata against itself. A second metadata read detects drift during this R0
window; it is NOT an atomic publish lock or authorization to publish later.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime
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
ASSET_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
MAX_ASSET_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
GH_ISO_UTC = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


class ReleasePreflightError(ValueError):
    """Untrusted remote content never becomes a privileged instruction."""


def _must(ok: bool, reason: str) -> None:
    if not ok:
        raise ReleasePreflightError(reason)


def _github_utc_timestamp(value: Any) -> str:
    # GitHub REST release/asset updated_at must be a valid canonical
    # UTC timestamp. Two missing values are NOT evidence of stable state.
    _must(type(value) is str and GH_ISO_UTC.fullmatch(value) is not None,
          "GITHUB_UPDATED_AT_MISSING_OR_INVALID")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ReleasePreflightError("GITHUB_UPDATED_AT_MISSING_OR_INVALID") from exc
    return value


def _get(get_json: Callable[[str], Any], path: str) -> dict[str, Any]:
    try:
        obj = get_json(path)
    except KeyError as exc:
        # Missing/changed GitHub objects are a HOLD, not a recovery hint.
        raise ReleasePreflightError("GITHUB_READ_OBJECT_MISSING") from exc
    _must(type(obj) is dict, "GITHUB_READ_OBJECT_INVALID")
    return obj


def _asset_map(release: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets=release.get("assets")
    _must(type(assets) is list and 3 <= len(assets) <= 16, "RELEASE_ASSET_COUNT_INVALID")
    mapping: dict[str, dict[str, Any]] = {}
    total=0
    for value in assets:
        _must(type(value) is dict, "RELEASE_ASSET_INVALID")
        name=value.get("name")
        _must(type(name) is str and ASSET_NAME.fullmatch(name) is not None,"RELEASE_ASSET_NAME_INVALID")
        _must(name not in mapping,"RELEASE_ASSET_DUPLICATE")
        asset_id=value.get("id")
        size=value.get("size")
        digest=value.get("digest")
        _must(type(asset_id) is int and asset_id>0,"RELEASE_ASSET_ID_INVALID")
        _must(type(size) is int and 0<size<=MAX_ASSET_BYTES,"RELEASE_ASSET_SIZE_INVALID")
        _must(type(digest) is str and digest.startswith("sha256:") and SHA256.fullmatch(digest[7:]) is not None,
              "RELEASE_ASSET_DIGEST_UNAVAILABLE")
        _must(value.get("state")=="uploaded","RELEASE_ASSET_NOT_FULLY_UPLOADED")
        total+=size
        _must(total<=MAX_TOTAL_BYTES,"RELEASE_ASSET_TOTAL_TOO_LARGE")
        mapping[name]={
            "id":asset_id,"name":name,"size":size,"digest":digest,
            "state":value["state"],"updated_at":_github_utc_timestamp(value.get("updated_at")),
        }
    return mapping


def _observed_snapshot(
    repo: str, tag: str, release_id: int, get_json: Callable[[str], Any],
) -> tuple[dict[str, Any],dict[str, dict[str, Any]]]:
    prefix=f"repos/{repo}"
    main=_get(get_json,f"{prefix}/branches/main")
    ref=_get(get_json,f"{prefix}/git/ref/tags/{tag}")
    obj=ref.get("object") or {}
    sha=obj.get("sha")
    if obj.get("type")!="tag" or type(sha) is not str or SHA40.fullmatch(sha) is None:
        raise ReleasePreflightError("ANNOTATED_TAG_REQUIRED")
    tag_object=_get(get_json,f"{prefix}/git/tags/{sha}")
    release=_get(get_json,f"{prefix}/releases/{release_id}")
    assets=_asset_map(release)
    # Real GitHub tag target includes an additional URL. Pin its type/SHA
    # fields, not the entire non-security metadata object.
    target=tag_object.get("object") or {}
    _must(type(target) is dict,"TAG_TARGET_OBJECT_INVALID")
    snapshot={
        "main":main.get("commit",{}).get("sha"),
        "tag_ref":{"type":obj.get("type"),"sha":sha},
        "tag_object":{
            "tag":tag_object.get("tag"),
            "target":{"type":target.get("type"),"sha":target.get("sha")},
        },
        "release":{
            "id":release.get("id"),"tag":release.get("tag_name"),
            "target":release.get("target_commitish"),
            "draft":release.get("draft"),"immutable":release.get("immutable"),
            "prerelease":release.get("prerelease"),
            "updated_at":_github_utc_timestamp(release.get("updated_at")),
        },
        "assets":[assets[name] for name in sorted(assets)],
    }
    return snapshot,assets


def _remote_source_bytes(get_json: Callable[[str], Any], path: str) -> bytes:
    source=_get(get_json,path)
    _must(source.get("type")=="file" and source.get("encoding")=="base64","SOURCE_BYTES_UNAVAILABLE")
    try:
        decoded=base64.b64decode("".join(source["content"].split()),validate=True)
    except (KeyError,AttributeError,ValueError) as exc:
        raise ReleasePreflightError("SOURCE_BYTES_INVALID") from exc
    _must(0<len(decoded)<=MAX_ASSET_BYTES,"SOURCE_BYTES_TOO_LARGE")
    return decoded


def _checksums(contents: bytes) -> dict[str,str]:
    try:
        lines=contents.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise ReleasePreflightError("CHECKSUMS_FILE_NOT_ASCII") from exc
    _must(len(lines)==2,"CHECKSUM_FILE_LINE_COUNT_INVALID")
    mapping:dict[str,str]={}
    for line in lines:
        _must(len(line)<250 and "  " in line,"CHECKSUM_LINE_INVALID")
        digest,name=line.split("  ",1)
        _must(SHA256.fullmatch(digest) is not None and ASSET_NAME.fullmatch(name) is not None,
              "CHECKSUM_LINE_INVALID")
        _must(name not in mapping and name!="SHA256SUMS.txt","CHECKSUM_DUPLICATE_OR_SELF_REFERENCE")
        mapping[name]=digest
    return mapping


def verify_draft(
    repository: str,tag: str,release_id: int,
    expected_tag_sha: str,expected_commit: str,
    expected_manifest_sha256: str,expected_checksums_sha256: str,
    get_json: Callable[[str], Any],get_binary_asset: Callable[[int],bytes],
) -> dict[str,Any]:
    """Verify exact approved assets via GitHub GETs; NEVER mutate/publish."""
    _must(repository==REPO,"REPOSITORY_NOT_ALLOWLISTED")
    _must(type(tag) is str and TAG.fullmatch(tag) is not None,"TAG_INVALID")
    _must(type(release_id) is int and release_id>0,"RELEASE_ID_INVALID")
    for val,error,regex in (
        (expected_tag_sha,"TAG_OBJECT_SHA_INVALID",SHA40),
        (expected_commit,"COMMIT_SHA_INVALID",SHA40),
        (expected_manifest_sha256,"MANIFEST_SHA_INVALID",SHA256),
        (expected_checksums_sha256,"CHECKSUM_FILE_SHA_INVALID",SHA256),
    ):
        _must(type(val) is str and regex.fullmatch(val) is not None,error)
    first,assets=_observed_snapshot(repository,tag,release_id,get_json)
    _must(first["main"]==expected_commit,"MAIN_COMMIT_DRIFT")
    _must(first["tag_ref"]=={"type":"tag","sha":expected_tag_sha},"TAG_OBJECT_MISMATCH")
    _must(first["tag_object"]=={"tag":tag,"target":{"type":"commit","sha":expected_commit}},
          "TAG_TARGET_MISMATCH")
    release=first["release"]
    _must(release["id"]==release_id and release["tag"]==tag and release["target"]==expected_commit,
          "DRAFT_RELEASE_IDENTITY_MISMATCH")
    _must(release["draft"] is True and release["immutable"] is False and release["prerelease"] is False,
          "RELEASE_ALREADY_PUBLISHED_OR_INCOMPATIBLE")

    required={f"{tag}-MANIFEST.sha256",f"{tag}-release-evidence.json","SHA256SUMS.txt"}
    # Exactly three immutable archive pieces are admitted: the current
    # manifest, evidence JSON, and a separately pinned checksum root. More
    # assets require a new audited contract rather than implicit extension.
    _must(set(assets)==required,"RELEASE_ASSET_SET_UNEXPECTED")
    checksum_asset=assets["SHA256SUMS.txt"]
    raw=get_binary_asset(checksum_asset["id"])
    _must(type(raw) is bytes and len(raw)==checksum_asset["size"],"CHECKSUM_FILE_BYTES_INVALID")
    _must(hashlib.sha256(raw).hexdigest()==expected_checksums_sha256,"CHECKSUM_FILE_EXTERNAL_SHA_MISMATCH")
    _must(checksum_asset["digest"]=="sha256:"+expected_checksums_sha256,"CHECKSUM_FILE_GITHUB_DIGEST_MISMATCH")
    checksums=_checksums(raw)
    _must(set(checksums)==set(assets)-{"SHA256SUMS.txt"},"ASSET_SET_NOT_WHITELISTED_IN_CHECKSUMS")
    downloaded={}
    for name in sorted(checksums):
        asset=assets[name]
        expected=checksums[name]
        _must(asset["digest"]=="sha256:"+expected,"ASSET_GITHUB_DIGEST_MISMATCH")
        data=get_binary_asset(asset["id"])
        _must(type(data) is bytes and len(data)==asset["size"],"ASSET_BYTES_OR_SIZE_MISMATCH")
        _must(hashlib.sha256(data).hexdigest()==expected,"ASSET_DOWNLOADED_BYTES_SHA_MISMATCH")
        downloaded[name]=data
    _must(hashlib.sha256(downloaded[f"{tag}-MANIFEST.sha256"]).hexdigest()==expected_manifest_sha256,
          "MANIFEST_RELEASE_ASSET_EXTERNAL_MISMATCH")
    prefix=f"repos/{repository}"
    genesis_raw=_remote_source_bytes(get_json,f"{prefix}/contents/registry/GENESIS.json?ref={expected_commit}")
    manifest_raw=_remote_source_bytes(get_json,f"{prefix}/contents/MANIFEST.sha256?ref={expected_commit}")
    try:
        genesis=json.loads(genesis_raw.decode("utf-8"))
        lines=manifest_raw.decode("ascii").splitlines()
    except (UnicodeError,ValueError) as exc:
        raise ReleasePreflightError("SOURCE_SCHEMA_INVALID") from exc
    _must(type(genesis) is dict and genesis.get("release_tag")==tag,"TAG_GENESIS_MISMATCH")
    _must(hashlib.sha256(manifest_raw).hexdigest()==expected_manifest_sha256,"REMOTE_MANIFEST_RAW_SHA_MISMATCH")
    _must(downloaded[f"{tag}-MANIFEST.sha256"]==manifest_raw,"RELEASE_SOURCE_MANIFEST_MISMATCH")
    _must(0<len(lines)<256,"MANIFEST_ENTRIES_INVALID")
    paths=set()
    for line in lines:
        _must("  " in line,"MANIFEST_ENTRIES_INVALID")
        digest,path=line.split("  ",1)
        _must(SHA256.fullmatch(digest) is not None and path not in paths and path,"MANIFEST_ENTRIES_INVALID")
        paths.add(path)

    # A second GET window detects mutation during this R0 review, but the
    # caller must re-check the snapshot immediately before any later publish.
    second,_=_observed_snapshot(repository,tag,release_id,get_json)
    _must(second==first,"RELEASE_OR_REF_CHANGED_DURING_PREFLIGHT")
    serialized=json.dumps(first,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return {
        "status":"DRAFT_RELEASE_PREFLIGHT_VERIFIED_R0_ONLY",
        "repository":repository,"tag":tag,"release_id":release_id,
        "policy_commit":expected_commit,"annotated_tag_object":expected_tag_sha,
        "manifest_sha256":expected_manifest_sha256,
        "checksums_sha256":expected_checksums_sha256,
        "manifest_entries":len(lines),"downloaded_verified_assets":len(downloaded)+1,
        "rechecked_exact_snapshot_sha256":hashlib.sha256(serialized).hexdigest(),
        "snapshot_is_atomic_publish_lock":False,
        "publish_requires_new_readback_and_separate_human_approval":True,
        "mutation_count":0,"policy_release_authorized":False,"release_published":False,
    }


def _json_api(path:str)->Any:
    r=subprocess.run(["gh","api","--method","GET",path],capture_output=True,text=True,timeout=50)
    _must(r.returncode==0,"GITHUB_API_READ_FAILED")
    try:return json.loads(r.stdout)
    except ValueError as exc:raise ReleasePreflightError("GITHUB_API_JSON_INVALID") from exc


def _asset_api(asset_id:int)->bytes:
    _must(type(asset_id) is int and asset_id>0,"ASSET_ID_INVALID")
    r=subprocess.run([
        "gh","api","-H","Accept: application/octet-stream","--method","GET",
        f"repos/{REPO}/releases/assets/{asset_id}",
    ],capture_output=True,timeout=60)
    _must(r.returncode==0,"GITHUB_ASSET_DOWNLOAD_FAILED")
    _must(0<len(r.stdout)<=MAX_ASSET_BYTES,"ASSET_DOWNLOAD_TOO_LARGE")
    return r.stdout


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("tag","expected-tag-object-sha","expected-commit","expected-manifest-sha256",
                "expected-checksums-sha256"):
        parser.add_argument("--"+key,required=True)
    parser.add_argument("--release-id",required=True,type=int)
    a=parser.parse_args()
    try:
        result=verify_draft(
            os.environ.get("GITHUB_REPOSITORY",""),a.tag,a.release_id,
            a.expected_tag_object_sha,a.expected_commit,
            a.expected_manifest_sha256,a.expected_checksums_sha256,
            _json_api,_asset_api,
        )
    except ReleasePreflightError as exc:
        print(json.dumps({"status":"HOLD","reason":str(exc),"published":False}))
        raise SystemExit(1) from None
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
