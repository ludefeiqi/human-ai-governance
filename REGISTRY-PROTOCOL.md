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
- immutable owner 必须在独立审查者 exact-head `APPROVED` Review 之后发布 GitHub comment。评论正文绑定 head、base、index SHA、diff SHA、IDs、动作和范围；以 API `created_at` 为唯一批准时间，不得要求预填尚未生成的服务器时间；`updated_at` 必须等于 `created_at`，编辑评论一律拒绝，comment ID 必须读回。

Owner comment 固定格式：

```text
HAGOV-REGISTRY-OWNER-APPROVAL-V1
candidate_head=<40hex>
previous_index_commit=<40hex>
index_sha256=<64hex>
normalized_diff_sha256=<64hex>
changed_ids=<sorted-comma-separated-ids>
authorized_action=APPROVE_DISCOVERY_REGISTRY_UPDATE
approval_scope=GOVERNANCE_REGISTRY_ONLY
```

PRE_MERGE 必须核实独立 Review 的服务器 `submitted_at` 早于 owner comment 的 `created_at`，且 reviewer 最新审查状态仍为 `APPROVED`；最后一条同标记的 owner 决议优先，不能重用被取代的旧批准。PRE_MERGE 不得声称已知未来 merge SHA，也不构成生效。

### POST_MERGE

合并后重新 GET 同一 PR 和实际 commit，验证：`merged=true`、actual `merge_commit_sha`、服务器 `merged_at` 必须晚于 owner `created_at`、merge commit first parent 等于 PRE_MERGE base、merge commit 的 `projects.yaml` raw bytes 等于已批准 candidate，并且该 commit 在 genesis→current main 的 first-parent 连续链上。只有 POST_MERGE 与完整链都通过，该变更才是 approved index；否则 `HOLD`，不降低分支保护或绕过核验。

## 5. 项目读取与统一报告

报告的三个维度彼此独立，且每一维合计都必须等于 `registry_total`：

- lifecycle：`active / paused / retired`；
- registration：`verified / unverified`；
- read：`VERIFIED / PARTIAL / BLOCKED / NOT_ATTEMPTED`。

`VERIFIED` 只表示本轮列明来源全部核真；`PARTIAL` 表示部分来源已核但仍有缺口；`BLOCKED` 表示安全或来源门禁失败；`NOT_ATTEMPTED` 表示未尝试。单项目失败可继续其它已授权、安全的 R0 项目，但不能把 `PARTIAL` 汇总成全局通过。

项目账本中实际读取到的 NEXT 标为 `DECLARED`；治理层基于证据提出的动作只能标为 `INFERRED governance recommendation`。两者不得合并，UNKNOWN 不得补写。Registry 报告固定 `dispatch_authorized:false`、`writer_change_authorized:false`。

## 6. 漂移、冷恢复与停止

冷恢复顺序：从插件取得**独立于 YAML 的精确政策 Commit pin** → Tag 解引用匹配 pin → 从固定 Commit 读取、核验**全部 19 项固定政策文件**的原始 SHA256，比较正在运行的 validator/Schema/GENESIS → pin main H1 → 严格读取 H1 的索引并验证 first-parent/每次审批 → 仅在同一次 `scan_authorized_main(...)` 操作中读取调用方另有 R0 授权的项目 ID → 每个项目读取前后复核 `main` HEAD → 返回结果前再复核。不得返回可重用的扫描令牌或快照。YAML 即使写着 `registration: verified` 也不是扫描能力；漂移即 `REGISTRY_HEAD_DRIFT/HOLD`，不返回本轮部分结果。不同窗口必须重新审计。

若 v0.2.0 Tag 未发布或无法解引用、Manifest/GENESIS/index 不匹配、GitHub GET 失败、项目 403/404、Git mode 不安全或审批不足，只报告准确缺口。不得自动采用项目、派工、恢复 thread、变更 writer、改保护设置或创建第二账本/服务。

## 7. 可复现本地验证

```bash
python3 -m venv /private/tmp/hagov-registry-venv
/private/tmp/hagov-registry-venv/bin/python -m pip install --disable-pip-version-check -r requirements-registry.lock
/private/tmp/hagov-registry-venv/bin/python -m pytest -q
/private/tmp/hagov-registry-venv/bin/python -m registry.validate_registry --root . validate-local
/private/tmp/hagov-registry-venv/bin/python -m registry.validate_registry --root . validate-candidate
/private/tmp/hagov-registry-venv/bin/python -m registry.validate_registry --root . reviewer-readiness
git diff --check
```

`validate-local` 仅校验首次政策发布时的原始 GENESIS，不可作为未来每次动态索引变更的 CI 门禁。`validate-candidate` 只做 Schema 和固定文件预检，必须输出 `registry_trusted:false`、`approval_verified:false`，不可深扫。`reviewer-readiness` 仅读 GitHub 实际协作者；只有一个 owner 时 `INDEPENDENT_GITHUB_REVIEWER_UNAVAILABLE/HOLD`，不能用另一个 AI 会话冒充不同 GitHub 审查账号，CI 替代审查属于另需批准的策略。正式 `audit-main` 必须提供插件单独锁定的 `--expected-policy-commit`。`pre-merge`、`post-merge`、`audit-main` 需要正式 Tag 和认证 GitHub GET；未发布期间必须 HOLD。


## 8. 单人多 AI 的分级审查候选（**待准确政策裁定，尚未生效**）

### A：EXTERNAL_GITHUB_REVIEW（现行可执行门禁）

由不同于仓库 owner/PR author 的真实 GitHub 账号对同一准确 HEAD 提交 `APPROVED` Review；服务端 Review 时间须早于 owner 对相同对象的批准，批准又必须早于 merge。当前私有仓库仅有 `ludefeiqi` 协作者，且 `main.protected=false`，分支保护和 rulesets API 返回套餐限制。**没有真实第二账号时 A 必须 HOLD**；其它 AI 窗口或 CI 不能冒充 GitHub Review。

### B：SINGLE_OWNER_AI_R0_ATTESTED（较低保证等级的拟议方案）

仅考虑发现元数据的登记变更，且持续 `reference_only`、`dispatch_enabled:false`、`writer_source:current_project_ledger_only`。不得增加项目实际读取权限、采用、业务派工、INTENT、writer、生产、身份权限或 R3 操作。

拟议必要证据为：独立 AI R0 审查绑定准确 PR HEAD、base、索引原始 SHA256、规范化差分摘要、changed IDs、审查结论与风险，保存可再读回的报告引用/摘要；同 HEAD 的 GitHub CI 明确 success；人类 owner 以可核验评论明确批准准确版本、用途范围与报告/CI 引用，服务器时间晚于审查和 CI 且早于 merge；合并后严格检查 parent、原始索引字节和连续历史。没有证明独立 AI 的不同 GitHub 账号身份，保证等级**严格低于 A**。单账号也没有平台分支保护，须保留读取端 fail-closed，不得伪称平台阻止恶意直接 push。

**执行边界：** B 目前只是候选政策。当前验证器依然执行 A 的不同 GitHub Reviewer 要求；只有用户另行对准确政策变更正式批准、独立复核，并将 B 的证据验证实现和测试加入受控版本，才可能启用。此处不得自动降级、也不得将 AI 评审回执当成 GitHub APPROVED Review。
