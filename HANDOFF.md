# HANDOFF.md — ChatGPT 跨窗口接管协议（v0.1.0）

## 原则

ChatGPT 聊天窗口是可更换的**控制界面**，不是唯一数据库或天然持久的后台服务。项目事实由项目仓库和实际执行证据支持；治理协议由本仓库的**已发布且经项目采用的准确版本**支持。恢复时不得靠旧聊天记忆猜想状态。

## 1. 恢复前准备（旧窗口可用时）

只追加/更新项目**既有授权的**状态入口，不为交接新建第二套权威记录。提供：项目 ID、当前 HEAD、当前负责人、任务卡/dispatch ID、Codex thread/turn ID、已完成证据、正在运行/清理的任务、剩余许可范围和停止点。不能保存的私密上下文不进入 GitHub。

旧窗口不要求导出全部聊天；当旧窗口不可用时，仍可执行只读恢复，但不得跳过现有任务/权限核对。

## 2. 新窗口五个确定动作

1. **READ_POLICY**：获取治理仓库实际采用的版本（精确 commit），读取本仓库 `GOVERNANCE.md`、`HANDOFF.md` 和登记项目条目。未发布、未采用、版本冲突时保持只读。
2. **READ_PROJECT**：读取项目准确远端分支最新 HEAD、项目固定合同、AGENTS.md 及最新账本当前区；历史版本仅作证据，不重放旧 NEXT。
3. **RECONCILE_RUNTIME**：根据准确 `task_id` / `dispatch_id` / thread ID 只读查询 Codex CLI、App Server 或其它已批准执行工具。比对状态、实际制品、未清理资源和证据 SHA；接口不可用时标 `UNKNOWN`。
4. **DETECT_CONFLICTS**：核现任 writer、旧窗口/旧 Codex 是否仍可能活跃、共享文件与生产是否有人使用；HEAD 漂移、授权缺失、任务不明都禁止新派工。
5. **ACCEPT_OR_HOLD**：能证明授权和唯一写口、且用户同意接管时，按项目的正式单写协议提交负责人变更，读回成功后才进入执行态；否则报告只读恢复结果和唯一阻断点。

## 3. 严格区分两种接管

### A. 只读接管（默认）

可以恢复任务、报告状态、审查候选和准备执行方案；**不得自行宣布日常 writer 切换**。GitHub 全局仓库中增加项目条目不代表项目已被接管。

### B. 写入/派工负责人切换（需另行授权）

要求用户明确批准：原负责人 → 新负责人、准确项目/范围、旧任务处置、原项目账本写入口。检查当前 HEAD 和正在执行的任务；必要时让旧负责人停派工，或在旧窗口不可用时提供可核查的停止/隔离证据。未能排除两个 writer/并发动作，不得强制取得控制权。

项目账本变更按项目现有白名单、审核与提交规则进行；提交后回读 HEAD 与全文/哈希。仅在准确接管生效后，对新的授权任务下达执行命令。

## 4. 恢复回执（紧凑模板）

```yaml
handoff_result: READ_ONLY_RESTORED   # 或 BLOCKED / WRITE_TAKEOVER_ACCEPTED
project_id: example-project
governance_commit: <exact-40-hex-sha-or-UNKNOWN>
project_head: <exact-40-hex-sha-or-UNKNOWN>
existing_writer: <from-current-project-ledger>
new_window: <current-window-reference>
active_task_id: <current-project-task-or-NONE>
codex_thread_id: <verified-id-or-UNKNOWN>
executing_tasks: <verified-list-or-UNKNOWN>
accepted_evidence: <nonsecret-references>
remaining_authority: <from-actual-approval-or-NONE>
conflicts: <none-or-specific-blockers>
next_allowed_action: <READ_ONLY-or-EXPLICITLY_AUTHORIZED>
```

该模板只是一份报告格式，不是项目权威账本；不要写入未经验证的值或敏感令牌。

## 5. 异常和防双派工

- **窗口满/断线**：新窗口只读恢复；不能拿旧聊天的“可以继续”当成有效批准。
- **任务可能仍在运行**：查询现有线程/进程和运行实例；未知即暂停新同范围任务，不能重放。
- **项目账本与 GitHub Issue 冲突**：仅记录差异，返回权威负责人核对；不自己改写历史结论。
- **提交冲突、branch/文件 SHA 漂移**：停止，不自动覆盖或靠重试刷新授权。
- **旧 writer 无法联系**：由用户明确裁定转移，且先证明旧进程/生产/共享资源不在冲突状态；否则仅观测不写入。
- **用户暂停或取消**：先执行此前确切获批的安全收尾；没有批准的破坏性清理不得擅自补做。

## 6. 新窗口启动语（可复制）

> 只读恢复项目 `PROJECT_ID`。请先实际读取已采用的独立治理仓库版本、projects.yaml、项目最新权威账本/AGENTS.md/固定合同，再按准确 ID 查询 Codex 线程和运行状态。输出最新 HEAD、现任单写负责人、仍在运行任务、有效授权和唯一 NEXT；凡版本、权限、任务或资源状态有冲突均停止。未经另行明确授权，不写仓库、不发任务、不接管 writer。

## 7. 不可用状态与不重复执行（对 `2、`5 的明确例外）

- `POLICY_UNAVAILABLE`：治理私库或该项目**实际采用的准确治理版本**无法远端核实；只读报告，不凭缓存、旧窗口或记忆宣称最新，不派工、不变更 writer。
- `DISPATCH_CONFLICT`：已有 `(project_id,dispatch_id)`，但任务载荷摘要不同，停止；相同只读恢复既有状态和原线程/回执。
- `DISPATCH_UNPROVEN`：新 R2/R3/副作用任务无法在获批项目**现有唯一权威入口**原子登记 `INTENT` 并读回，禁止派发，也不增设第二账本。
- `HEAD_CONFLICT`：写入瞬间服务端拒绝旧 expected HEAD，停止；不得 force、自动 rebase 或用新工具规避。
- 旧窗口失联不证明旧进程/云任务结束；新窗口先查唯一执行键、旧 writer、共享资源和剩余批准，无法确证时仅只读，不能抢写。

## P2 Controlled Dynamic Registry · v0.2.0 (Tag-gated)

— Section 8: Cross-window dynamic discovery

每次明确的冷启动按固定顺序：解引用并验证 v0.2.0 annotated Tag/Manifest/GENESIS → 固定 `main` H1 → 严格读取 H1 的 index raw bytes → 从正式 genesis commit 沿 first-parent 核全部 index 变更和 pre/post 审批 → 只对 externally verified 且 active、并有现行读取授权的条目核项目 branch HEAD、AGENTS、ledger 与固定合同 Git mode → 再读 `main` H2。H1≠H2 时只可从头重做一次；再次漂移则整个快照 `HOLD`，不得拼接两代数据。

registration unverified 项目不深扫私库；403/404/symlink/来源缺失只阻断该项目，继续其它已授权 R0 项目。报告必须分别给出 lifecycle `active/paused/retired`、registration `verified/unverified`、read `VERIFIED/PARTIAL/BLOCKED/NOT_ATTEMPTED`，每个维度合计 `registry_total`。项目账本实际 NEXT 单列 `DECLARED`；协调者建议单列 `INFERRED governance recommendation`；未读到就是 UNKNOWN。

两个窗口即使得到相同索引也仍是 R0 observers。发现、`thread/list/read` 或 includeTurns=false 不产生 writer；`thread/resume` 会恢复执行上下文，不是本流程的只读查询。索引不得自动 adopted、dispatch 或 writer handoff；任何接管仍须项目自身权威流程与用户准确授权。

**P2.1 冷恢复补充（Tag 验证后适用）：** 外部插件需提供准确 policy Commit pin；新窗口必须从该不可变 Commit 校验运行的 validator、Schema 与 GENESIS，完成全部固定政策与完整审批链核验后，在同一次 `scan_authorized_main` 操作中针对有现行 R0 授权的项目 ID 完成读取；逐项读前读后和返回前都重核 `main` HEAD，不缓存或跨窗口重用任何扫描快照。带 `registration: verified` 的 YAML dict 没有受支持的扫描入口。未来动态索引变更的绿色 CI 仅证明 Schema precheck，不等于审批。缺不同 GitHub reviewer 标记 `REVIEWER_UNAVAILABLE/HOLD`。


**P2 审查等级：** A 要求不同 GitHub 账号的 `APPROVED`，单 owner 时不可通过 A。B 是较低保证等级（AI R0 证据 + 同 HEAD CI + owner 准确批准 + 连续链），只有已验证的正式 `v0.2.0` GENESIS 选择 B 且操作对象是发布后的普通登记 PR 才可使用；不得把新候选或 CI 成功当自动放行。


**B 级审批技术链路（仅正式政策激活后）：** 对未来普通发现登记 PR，以独立政策 GENESIS 指定的 A/B 模式为唯一开关。B 模式须在相同 HEAD 下完成 CI 最新成功、owner GitHub 评论承载 AI R0 证明、owner 不同评论明确限定用途批准，并在合并后读回实际 first-parent/原始索引。评论作者仅是 owner GitHub 账号，不能冒充另一个 GitHub reviewer 或真人独立认证。缺任一证据均 HOLD，业务项目私库读取/执行权限须另行授权。


**政策信任锚安全更新：** 当 B 级正式受用户准确批准并发布后，所有 pre/post-merge 与 first-parent 历史审计均须取得**外部已信任政策 Commit pin**，逐项读回官方 Tag 与固定文件哈希后才读取 GENESIS 中的审查模式。不可用 caller JSON、未发布候选或最近的 CI 成功结果替代政策锚。在 `v0.2.0` 正式 Tag、政策 Commit 和运行端 pin 全部确认前，旧版 v0.1.0 仍有效，新版内容只能作为候选 R0。
