# Human–AI Governance v0.1.0

**Status: RELEASED_GOVERNANCE / PROJECT_ADOPTION_NOT_AUTOMATIC**

This private repository holds the shared protocol for coordinating people, ChatGPT work windows and Codex. The **governance protocol is published** here; it is **not** an authorization token, a production control plane, or a substitute for project-specific rules and user permissions.

## Published policies

- [GOVERNANCE.md](GOVERNANCE.md) — authority, risk boundaries, single writer, HEAD-level checks and evidence
- [CODEX-PROTOCOL.md](CODEX-PROTOCOL.md) — task cards, idempotent dispatch, Codex CLI/App Server receipts
- [HANDOFF.md](HANDOFF.md) — safe cross-window recovery, conflict detection and failure stop
- [projects.yaml](projects.yaml) — **entry index only**, no business task/NEXT replication
- [AGENTS.md](AGENTS.md) — instructions for Codex *inside this governance repository*, not other projects
- [REVIEW-CHECKLIST.md](REVIEW-CHECKLIST.md) — review scenarios and versioned change gates
- [MANIFEST.sha256](MANIFEST.sha256) — raw-byte SHA256 list for the immutable policy candidate (policy, GENESIS, validator, Schema, locked dependencies and tests); dynamic `projects.yaml` is deliberately excluded

The exact first-reviewed candidate is preserved under [drafts/v0.1/](drafts/v0.1/), with the separate manifest and historical draft wording. Independent first review and corrected design approval: [PR #2](https://github.com/ludefeiqi/human-ai-governance/pull/2). The final root promotion requires an independent review of its own accurate diff. Release authorization is recorded separately under `releases/v0.1.0/`.

## No automatic adoption or execution

HOT/AUTH/BBS remains managed in **ludefeiqi/dabing.lol** under its existing project authority and DOT/ROOT ledger writer. The entry in `projects.yaml` is `reference_only` and `dispatch_enabled: false`. No project code, frozen v3.2 contract, project AGENTS, Issue, ledger, browser/identity/production setting or credentials changed as part of this governance release.

**Policy on GitHub != loaded agent instructions != a current user operation grant.** Each work window must read the effective policy version, live project authority and execution state before it may request a task. A new governance version never automatically overwrites existing project rules.

## Updating this version

Exact candidate + manifest -> independent read-only review -> explicit user approval bound to scope -> release-PR root diff review -> non-force merge/readback -> immutable Git tag. Later project adoption and any writer handoff require separate authority and evidence.

## P2 Controlled Dynamic Registry · v0.2.0 candidate

This branch is a re-review candidate, not an active release. It adds:

- deterministic strict YAML + JSON Schema validation in `registry/`;
- immutable `registry/GENESIS.json` binding owner, release route, initial identities and the initial index raw SHA256;
- a first-parent, no-delete tombstone chain with exact pre/post GitHub GET evidence;
- separate lifecycle, registration and read-result accounting;
- synthetic positive/negative pytest coverage and pinned dependencies.

The immutable policy Manifest excludes the future dynamic `main/projects.yaml`; genesis binds the first index, while every later index is approved against its immediately preceding approved commit. Post-release registry PRs may change only `projects.yaml`. This PR #5 is the multi-file bootstrap policy candidate and remains governed by the release review gate.

Exact local commands:

```bash
python3 -m venv /private/tmp/hagov-registry-venv
/private/tmp/hagov-registry-venv/bin/python -m pip install --disable-pip-version-check -r requirements-registry.lock
/private/tmp/hagov-registry-venv/bin/python -m pytest -q
/private/tmp/hagov-registry-venv/bin/python registry/validate_registry.py validate-local
git diff --check
```

Local success is not CI, GitHub review, owner approval, merge, Tag publication, project adoption or business acceptance. Until the annotated `v0.2.0` Tag and all bound evidence exist, retain v0.1.0 semantics and HOLD dynamic discovery.
