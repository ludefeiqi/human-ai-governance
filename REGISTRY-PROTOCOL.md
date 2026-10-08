# REGISTRY-PROTOCOL.md — Human–AI Governance v0.2.0 P2 候选规范

> **CANDIDATE / NOT RELEASED / LOCAL TESTED ONLY**  本候选不改变 v0.1.0，也不授予项目读取、采用、派工、writer 变更或生产权限。只有 `v0.2.0` annotated tag、其底层 Commit、固定政策清单、GENESIS、独立审查和用户发布批准全部按本节核真后，动态索引机制才可使用；Tag 缺失、轻量 Tag、证据不足或 API 不可用均为 `HOLD`，继续 v0.1.0 语义。

## 1. 三轨分离与不可推导

1. **Immutable policy**：`v0.2.0` annotated tag 解引用后的 Commit 是正式 genesis commit。`MANIFEST.sha256` 固定政策文档、`registry/GENESIS.json`、validator、JSON Schema、锁定依赖和测试的 raw-byte SHA256；它明确不包含之后随 `main` 变化的 `projects.yaml`。
2. **Dynamic registry**：唯一位置是同一治理仓库 `main/projects.yaml`。它只保存项目入口、采用事实引用和墓碑，不保存当前 NEXT、业务 PASS、线程、dispatch、writer 令牌或第二套运行账本。
3. **Project authority**：项目实时 HEAD、同 HEAD 的 `AGENTS.md`、权威账本和固定合同仍决定项目事实。索引不能自动把项目变为 `adopted`，不能开启 dispatch，不能转移 writer，也不能生成业务 INTENT。

`registry/GENESIS.json` 固定治理仓库、owner GitHub account、Tag、registry 分支/路径、首份 `projects.yaml` raw-byte SHA256 与初始 identity hash。owner 是 GitHub 账户归属校验基准；GitHub `user.login` 与 `created_at` 只能证明平台账户归属和平台记录时间，不是密码签名、私钥签名或真人身份学证明。

PR #5 是发布这套机制的多文件政策候选，仍按旧版发布门禁审查。只有 v0.2.0 正式发布后的普通 registry 变更 PR，才适用“PR 只许改 `projects.yaml`”的机械规则。

## 2. 严格读取与 Schema

`registry/validate_registry.py` 必须对 raw bytes 执行以下顺序，任一失败即 `HOLD`：

1. 最大 262144 bytes；UTF-8 strict；拒绝 BOM 和除 TAB/LF/CR 外的 C0/DEL 控制字符。
2. YAML 单文档、最大深度 24、单 scalar 最大 16384 字符；拒绝 duplicate key、alias、anchor、显式/custom tag、directive、merge key 和非字符串 mapping key。
3. 使用 `registry/projects.schema.json` Draft 2020-12 校验；所有对象 `additionalProperties:false`，拒绝未知字段、错误类型和超限集合。
4. `repository` 必须是 canonical `owner/repo`；路径必须是无 `..`、绝对路径、反斜线、URL、query/fragment、glob 和敏感目录的仓库相对 POSIX 路径；branch 通过严格 ref 语义检查。
5. `identity_hash = sha256(canonical-json({project_id,repository}))`，ID、repository 与 identity hash 不可改用途。
6. 只有 `lifecycle=active` 且外部证据使 `registration=verified` 的条目才可做项目来源核验。`unverified` 不深扫未知私库。
7. 读取 active 项目的 branch HEAD 后，以逐级 Git tree GET 精确核 `ledger_path`、`project_rules_path`；再在 `frozen_product_baseline.commit` 核固定合同 path。目标必须是 mode `100644`/`100755` 的 blob；symlink `120000`、submodule、tree、缺失或不确定全部拒绝。

YAML 中的 `registration: verified` 不是自证。有效状态仍取决于本节的 genesis、连续历史和 GitHub 审批证据；任何来源无法核真时，effective registration 必须降为 `unverified/HOLD`。

## 3. 连续索引链与墓碑

正式链以 `v0.2.0` annotated tag 解引用的 genesis commit 为根，只沿 `main` 的 first-parent 前进。扫描固定一个 `main` HEAD，向 genesis 有界遍历；每个改变 `projects.yaml` raw bytes 的 first-parent commit 必须对应恰好一个经验证的 merged PR。到不了 genesis、历史过深、关联 PR 不唯一、父提交不符或中途漂移都不得拼接状态。

每份候选索引必须与**上一份已批准索引**比较：

- 项目 ID 禁止物理删除；退役必须保留完整 tombstone、`identity_hash`、repository 与历史。
- ID、repository、identity hash 不得改用途。需要不同 repository 时使用新 ID，旧 ID 退役保留。
- `lifecycle` 只有 `active|paused|retired`。每次状态改变只追加一个事件，含 UTC `changed_at`、新 lifecycle 和上一份索引 commit；不得重写或截断历史。
- `retired` 的最后事件必须保留退役时间与 `previous_index_commit`。re-activate 只能在 identity 完全相同且原退休事件原样保留时追加 active 事件。
- 新项目初始为 active，provenance 绑定已知上一份索引 commit；审批证据仍须从 GitHub 独立核验。
- Schema 固定 `governance_adoption: reference_only`、`dispatch_enabled:false`、`writer_source:current_project_ledger_only`，索引本身没有升级采用、派工或 writer 的表达能力。

## 4. 审批证据与 pre/post 两阶段

validator 的网络面只可调用认证的 `gh api --method GET`。不接受 YAML 内的 `approved:true`、外部 boolean、Issue 标签、宽泛仓库权限或人工转述。

### PRE_MERGE

在合并前验证：

- PR 的 `head.sha` 等于指定 exact candidate HEAD，base SHA 有效；
- changed files 恰好只有 `projects.yaml`，且不是删除；
- 从 exact head/base 读取 raw index，严格解析并与上一份索引比较；
- 计算 candidate index raw SHA256、canonical JSON semantic diff SHA256 和排序后的 changed IDs；
- 至少一个不等于 PR author、也不等于 immutable owner 的 reviewer，其**最新** review 在 exact head 上为 `APPROVED`；
- immutable owner 发布 GitHub comment，API `user.login` 精确匹配，comment `created_at` 是 UTC，正文逐项绑定 head、base、index SHA、diff SHA、IDs 和同一 API 时间。

Owner comment 固定格式：

```text
HAGOV-REGISTRY-OWNER-APPROVAL-V1
candidate_head=<40hex>
previous_index_commit=<40hex>
index_sha256=<64hex>
normalized_diff_sha256=<64hex>
changed_ids=<sorted-comma-separated-ids>
approved_at_utc=<GitHub-comment-created_at>
```

PRE_MERGE 不得声称已知未来 merge SHA，也不构成生效。

### POST_MERGE

合并后重新 GET 同一 PR 和实际 commit，验证：`merged=true`、actual `merge_commit_sha`、merge commit first parent 等于 PRE_MERGE base、merge commit 的 `projects.yaml` raw bytes 等于已批准 candidate，并且该 commit 在 genesis→current main 的 first-parent 连续链上。只有 POST_MERGE 与完整链都通过，该变更才是 approved index；否则 `HOLD`，不降低分支保护或绕过核验。

## 5. 项目读取与统一报告

报告的三个维度彼此独立，且每一维合计都必须等于 `registry_total`：

- lifecycle：`active / paused / retired`；
- registration：`verified / unverified`；
- read：`VERIFIED / PARTIAL / BLOCKED / NOT_ATTEMPTED`。

`VERIFIED` 只表示本轮列明来源全部核真；`PARTIAL` 表示部分来源已核但仍有缺口；`BLOCKED` 表示安全或来源门禁失败；`NOT_ATTEMPTED` 表示未尝试。单项目失败可继续其它已授权、安全的 R0 项目，但不能把 `PARTIAL` 汇总成全局通过。

项目账本中实际读取到的 NEXT 标为 `DECLARED`；治理层基于证据提出的动作只能标为 `INFERRED governance recommendation`。两者不得合并，UNKNOWN 不得补写。Registry 报告固定 `dispatch_authorized:false`、`writer_change_authorized:false`。

## 6. 漂移、冷恢复与停止

冷恢复顺序：verify policy tag/manifest/genesis → pin main H1 → read strict index at H1 → verify first-parent/approvals → 仅核 verified active 项目的目标文件 → re-read main H2。若 H1≠H2，只允许从头重做一次独立快照；再次漂移则 `REGISTRY_HEAD_DRIFT/HOLD`，绝不拼接两次结果。

若 v0.2.0 Tag 未发布或无法解引用、Manifest/GENESIS/index 不匹配、GitHub GET 失败、项目 403/404、Git mode 不安全或审批不足，只报告准确缺口。不得自动采用项目、派工、恢复 thread、变更 writer、改保护设置或创建第二账本/服务。

## 7. 可复现本地验证

```bash
python3 -m venv /private/tmp/hagov-registry-venv
/private/tmp/hagov-registry-venv/bin/python -m pip install --disable-pip-version-check -r requirements-registry.lock
/private/tmp/hagov-registry-venv/bin/python -m pytest -q
/private/tmp/hagov-registry-venv/bin/python registry/validate_registry.py validate-local
git diff --check
```

`validate-local` 只证明当前 raw files、Schema、GENESIS binding 与 Manifest 一致。`pre-merge`、`post-merge`、`audit-chain` 需要正式 Tag 和认证 GitHub GET；本候选在 Tag 未发布期间必须 HOLD，不能把本地测试冒充 CI、GitHub 审批或发布通过。
