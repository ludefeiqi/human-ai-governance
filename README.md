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
/private/tmp/hagov-registry-venv/bin/python -m registry.validate_registry --root . validate-local
/private/tmp/hagov-registry-venv/bin/python -m registry.validate_registry --root . validate-candidate
/private/tmp/hagov-registry-venv/bin/python -m registry.validate_registry --root . reviewer-readiness
git diff --check
```

Local success is not CI, GitHub review, owner approval, merge, Tag publication, project adoption or business acceptance. Until the annotated `v0.2.0` Tag and all bound evidence exist, retain v0.1.0 semantics and HOLD dynamic discovery.

### P2.1 trust-chain boundary (candidate only)

Owner comments never prefill GitHub's future `created_at`. Exact-head independent GitHub `APPROVED` Review must precede the unedited owner approval comment and GitHub merge. The current repo only has its owner as a collaborator; `reviewer-readiness` reports `HOLD` until an actually distinct authorized GitHub account is available or a separately approved governance change establishes a different, honestly labelled assurance level. A second AI chat using the owner account is not a second GitHub actor.

Cold-start project reads require an externally pinned immutable policy commit, all 20 policy files checked by SHA256, a complete first-parent approval chain, and an atomic audit-plus-read `scan_authorized_main` transaction with a fresh `main` HEAD check before and after each authorized project. No reusable scan token exists; raw YAML status is never scan authority. `validate-candidate` allows future updated index bytes as a schema-only CI preflight, not registration approval. `audit-main` requires an external `--expected-policy-commit`.


### P2 final-seal candidate and assurance grades

The targeted fixes address forged reusable scan tokens, stale registry snapshots, PR rename loopholes and incomplete remote manifest validation. They confer no new project authority. A remains an actual distinct GitHub account APPROVED Review and is currently unavailable in the single-owner private repo. The lower-assurance B proposal (independent AI R0 report + exact-HEAD CI + owner approval + verified merge lineage) is only for discovery-only metadata. Its machine verifier is now staged in this Draft PR, but it still requires an independently reviewed exact policy release, explicit owner approval and official Tag before use; this draft does NOT automatically activate B.


### P2 Gate 1: single-owner B machine verifier staged, **not released**

This Draft PR now includes an immutable GENESIS selection of `SINGLE_OWNER_AI_R0_ATTESTED` for future discovery-only registry updates and a tested read-only `pre-merge/post-merge/audit-chain` verifier. B checks the latest exact-HEAD GitHub Actions `validate` run, owner-posted AI R0 attestation and a *separate* owner approval comment, immutable comment IDs/body hashes, chronological order and merged bytes/first parent. The owner account posting an AI summary is **not** proof of a second GitHub reviewer or independent AI identity. The original A-mode verified GitHub reviewer path remains available for a differently released GENESIS. This code is not a bootstrap release approval: v0.1.0 remains effective, and future R0 project access still needs authorization independent from discovery metadata.
