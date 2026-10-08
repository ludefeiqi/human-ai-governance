"""Build a guarded, identity-preserving plugin overlay; never installs or changes audience."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import zipfile

MANIFESTS=("plugin.json", ".codex-plugin/plugin.json")

def build(root: Path, snapshot: dict, output: Path) -> dict:
    plan=json.loads((root/"clients/plugin-update.json").read_text())
    source=snapshot.get("result",snapshot)
    plugin=source["plugin"];contents=source["contents"]
    if plugin.get("plugin_id") != plan["plugin_id"] or plugin.get("current_release_id") != plan["expected_release_id"]:
        raise ValueError("PLUGIN_RELEASE_CONFLICT")
    if plugin.get("version") != plan["from_plugin_version"] or plugin.get("scope") != "USER" or plugin.get("discoverability") != "PRIVATE":
        raise ValueError("PLUGIN_IDENTITY_OR_AUDIENCE_MISMATCH")
    patched={}
    for path in MANIFESTS:
        data=json.loads(contents[path])
        if data.get("name") != "human-ai-governance-bootstrap" or data.get("version") != plan["from_plugin_version"]:
            raise ValueError("MANIFEST_IDENTITY_OR_VERSION_MISMATCH")
        # All original metadata, interfaces and author details survive unchanged.
        data["version"]=plan["candidate_plugin_version"]
        patched[path]=(json.dumps(data,ensure_ascii=False,indent=2)+"\n").encode()
    overlay=root/plan["overlay_root"]
    for path in overlay.rglob("*"):
        if path.is_symlink(): raise ValueError("OVERLAY_SYMLINK")
        if path.is_file(): patched[path.relative_to(overlay).as_posix()]=path.read_bytes()
    if plan["delete_paths"]: raise ValueError("DELETIONS_NOT_AUTHORIZED")
    if output.exists(): raise FileExistsError(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,"x",compression=zipfile.ZIP_DEFLATED) as archive:
        for path,raw in sorted(patched.items()):
            info=zipfile.ZipInfo(path,date_time=(2026,10,8,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,raw)
    return {"files":len(patched),"plugin_version":plan["candidate_plugin_version"],"installed":False,
            "expected_release_id":plan["expected_release_id"],"preserve_unmentioned_files":True}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source-snapshot",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(build(args.root,json.loads(args.source_snapshot.read_text()),args.output),ensure_ascii=False))
if __name__=="__main__": main()
