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
- [MANIFEST.sha256](MANIFEST.sha256) — SHA256 of the seven published root source files, including this README

The exact first-reviewed candidate is preserved under [drafts/v0.1/](drafts/v0.1/), with the separate manifest and historical draft wording. Independent first review and corrected design approval: [PR #2](https://github.com/ludefeiqi/human-ai-governance/pull/2). The final root promotion requires an independent review of its own accurate diff. Release authorization is recorded separately under `releases/v0.1.0/`.

## No automatic adoption or execution

HOT/AUTH/BBS remains managed in **ludefeiqi/dabing.lol** under its existing project authority and DOT/ROOT ledger writer. The entry in `projects.yaml` is `reference_only` and `dispatch_enabled: false`. No project code, frozen v3.2 contract, project AGENTS, Issue, ledger, browser/identity/production setting or credentials changed as part of this governance release.

**Policy on GitHub != loaded agent instructions != a current user operation grant.** Each work window must read the effective policy version, live project authority and execution state before it may request a task. A new governance version never automatically overwrites existing project rules.

## Updating this version

Exact candidate + manifest -> independent read-only review -> explicit user approval bound to scope -> release-PR root diff review -> non-force merge/readback -> immutable Git tag. Later project adoption and any writer handoff require separate authority and evidence.
