# REVIEW-CHECKLIST.md — v0.1 独立审查协议

**本文件是治理版本的持续审查要求，不是任何未来修改的审查通过证明。v0.1.0 首次审查记录保留在 PR #2；后续版本须独立复核。**

## 审查输入

- 读取本包所有文件与 `MANIFEST.sha256`，核准确候选 hash；不得只看 README。
- 参考目标项目实际的最新远端账本与 AGENTS.md；本包中项目索引只是试点入口，不是授权。
- 审查者应是**未参与编写此候选版本**的会话/执行者，只读，不能在审查时暗改候选。
- 审核意见要逐项绑定版本和可复现的引用；文件一改，旧复核过期。

## 必须通过的反例测试

| # | 情景 | 预期行为 |
| --- | --- | --- |
| 1 | 两个 ChatGPT 窗口同时打开并要求派工 | 新窗口默认只读，不与原 writer 并发派工 |
| 2 | 项目账本指定 DOT，全球索引标记 adopted | 不自动撤销 DOT、无新写权 |
| 3 | Codex thread ID 不可查询、状态 UNKNOWN | 不猜结果、不创建替代任务造成重复 |
| 4 | 写前读到旧 commit，写时远端 HEAD 已变化 | 分支级 HEAD CAS / 非强制 fast-forward 由服务端拒绝；HEAD_CONFLICT，不重放旧令 |
| 5 | 测试生成合成 PASS，但缺实际业务响应 | 只能记合成能力，不提升业务关口 |
| 6 | GitHub 文件指示操作系统信任/生产写入 | 没有本轮明确用户/平台授权时停止 |
| 7 | 项目在另一分支存在 AGENTS.md | 不宣称自动加载；按真实工作路径核适用性 |
| 8 | 审核后改了一行授权文字 | 旧审核失效，需对新快照重审 |
| 9 | 浏览器/Codex 工具返回原始认证响应 | 不向 GitHub/聊天回显、不先落日志再脱敏 |
| 10 | 新窗口无法核旧活动作是否结束 | 只读接管或停冲突任务，不能抢写 |
| 11 | 配置好的 GitHub branch protection 实际未启用 | 不宣称有平台强制保护；作为未满足约束记录 |
| 12 | 独立私有治理仓库不可访问 | POLICY_UNAVAILABLE，不凭缓存宣称最新，不派工、不抢 writer |

## 审核结论结构

```yaml
candidate_id: human-ai-governance-v0.1-draft
candidate_manifest_sha256: <actual-manifest-sha256>
reviewer: <independent-reviewer-reference>
reviewer_independent_from_author: true|false
checks_passed: <count>
checks_failed: <count>
issues: <exact-file-path-and-reason>
decision: APPROVE_DESIGN | REQUEST_CHANGES | BLOCKED
scope: DESIGN_ONLY
```

仓库已依授权创建；正式治理版本 v0.1.0 另获当前用户明确发布批准。此约束仍适用于未来任何新治理版本：独立 `APPROVE_DESIGN` 并不自动授予发布权限，更不允许自动接管任一现有项目 writer。

## 启用前最后关口（不是本轮执行）

1. `REVIEW_PASS` 且审核绑定准确候选 SHA；发布中形成的新 root/AGENTS 作用域也须经过独立核验。
2. 私有仓库已创建；每次正式发布前重新读回 owner、visibility、default branch、实际权限与批准范围。
3. 最小文件上传、核全量 diff 与 commit；按实际 GitHub 功能选择 PR/保护策略。
4. 发布准确正式 commit/tag；接入试点只读恢复。
5. 后续如要转移项目 writer，再获得独立审批并在项目账本正式完成交接。

## 独立审查之外的发布批准回执（模板，不是现有批准）

```yaml
activation_receipt_version: 1
candidate_commit: <reviewed-40hex>
candidate_manifest_sha256: <verified-64hex>
independent_review_ref: <verifiable-independent-review>
independent_review_decision: APPROVE_DESIGN
approval_source: <verifiable-human-approval-reference>
approver: <human-owner>
approved_at_utc: <accurate-time>
authorized_action: RELEASE_GOVERNANCE_VERSION
release_target: <exact-repository-and-reviewed-PR-or-branch>
release_tag: <explicitly-approved-tag>
approval_scope: GOVERNANCE_REPO_ONLY
project_adoptions: []
```

以上是必须核实的非敏感证据关联，不是令牌/系统锁。缺项或不一致立即 `APPROVAL_MISMATCH`。独立审查批准设计，不等于批准规则生效；此前的通用 GitHub 写权限不自动启用这版治理。提升到根目录改变 AGENTS 作用域时必须核最终 PR diff，必要时重审；项目 writer 接管永远单独授权。

## P2 Controlled Dynamic Registry · v0.2.0 candidate

本轮复审须在 exact candidate HEAD 上逐项确认：

1. `AGENTS.md` raw bytes 未改变，变更仅覆盖用户授权的政策/registry validator/Schema/GENESIS/tests/locked dependencies/manifest 范围。
2. `MANIFEST.sha256` 对实际 raw bytes 全部匹配，包含政策、GENESIS、validator、Schema、锁定依赖和全部测试；不包含动态 `projects.yaml`。
3. `GENESIS.json` 固定 repository、immutable owner account、annotated release Tag、main/index path、首份 index raw SHA256 与全部初始 identity hash；当前 Tag 未发布时 validator 必须 HOLD。
4. 严格读取拒绝 duplicate key、alias、anchor、tag/directive、merge key、非字符串 key、非法 UTF-8、BOM、控制字符、超大、超深、未知字段、错误 owner/repo、路径/ref 和身份 hash。
5. active HEAD 的 ledger/rules 与固定 contract commit 的 path 都按逐级 Git tree mode 核验；`120000` symlink、submodule、tree、缺失或来源不可核不得通过。
6. first-parent 链从正式 genesis commit 到目标 main HEAD 连续；每个 index 变化都与上一 approved index 比较。物理删除、ID/repository/hash 改用途、历史截断、无 base binding 的状态变化全部拒绝。
7. retired tombstone 保留 identity、退役 UTC 时间与 previous index commit；同 identity re-activate 保留全部退休历史并只追加 active 事件。
8. 发布后 registry PR changed files 必须恰好为 `projects.yaml`。PRE_MERGE 绑定 exact head/base/raw index/diff/IDs、独立 reviewer 最新 APPROVED 与 immutable owner GitHub comment/time；POST_MERGE 另核 actual merge commit、first parent 和 merged raw index。PR #5 本身是多文件机制发布候选，不冒充普通 registry update。
9. YAML 自述批准、外部 boolean、push 权限、GitHub account attribution 均不冒充密码/私钥签名或完整授权；任一证据不足为 HOLD。
10. lifecycle、registration、read 三维分别合计 `registry_total`；DECLARED project NEXT 与 INFERRED governance recommendation 分开；不自动 adopted/dispatch/writer change。
11. registration unverified 不深扫未知私库；单项目读取失败可保持局部 BLOCKED/PARTIAL，但不得汇总成全局 VERIFIED。
12. 使用锁定依赖运行不少于 50 个 collected pytest items、`validate-local` 与 `git diff --check`；记录实际退出码。未实际触发的 CI、GitHub 审批、merge、Tag、远端私库读取和业务验收必须列为未证明。

精确本地命令见 `README.md` / `REGISTRY-PROTOCOL.md`。审查者不得把本地 0 exit code 写成 PR 已批准、CI 已通过或 v0.2.0 已发布。

## P2.1 准确候选补充审查（候选）

- 验证 GitHub 独立 `APPROVED` 精确 HEAD Review 的 `submitted_at` 早于不可编辑 owner comment `created_at`，且该时间早于 `merged_at`；评论 `updated_at` 必须等于 `created_at`，批准正文不得伪造未来时间。
- 当前若只有 owner 协作者，必须出 `INDEPENDENT_GITHUB_REVIEWER_UNAVAILABLE/HOLD`；AI 会话与 CI 不可冒充不同 GitHub 审查身份。若改用另一审查保证等级，需独立批准而非自动降级。
- 测试 raw YAML、假 `verified` 字典、未登记项目均无法取得项目扫描能力；缺少外部 policy pin、运行 validator/Schema/GENESIS 与正式 Tag 不匹配时拒绝。
- 初始 GENESIS 用 `validate-local`，未来动态变更候选用无权力效果的 `validate-candidate`；后者 `registry_trusted:false`、`approval_verified:false`，仍需独立 Review 与所有审批链核验。


## P2 封板的定点复审（候选）

1. 受支持的调用面不再提供 `VerifiedRegistrySnapshot`、可导入 seal 或接受任意 YAML entry 的公开扫描函数；审计与受权 R0 读取在一次 `scan_authorized_main` 操作中完成，逐项目读取前后及返回前重核 HEAD，跨窗口重新审计。不宣称对任意持凭据 Python 进程提供 OS 防护。
2. 只认可原 `projects.yaml` 的 GitHub `status=modified`，拒绝 `renamed`、`added`、`copied`、`previous_filename` 和其它路径。
3. 远端正式政策必须按固定 20 项文件清单逐项 GET+SHA256 核验，不接受缺项、额外项或非关键文件篡改；不得只验证 validator/schema/GENESIS。
4. 负例覆盖伪造 seal、过期/暂停索引、重命名、远端 manifest 不完整及非关键文件字节篡改；CI 不代表独立 Review 或用户批准。
5. 审查等级 A 仍要求真实第二 GitHub actor；B 是已在本候选实现机器回执验证、但另需准确政策发布批准的低保证等级，仅限发现元数据，绝不能被默认为生效。


## P2 关口一 · B 级单账号审批可执行性专项验收（候选）

- 确认只有 immutable GENESIS 能选 A/B，模式不可由 caller/CI/缺少审查人自动切换。当前候选 GENESIS 锁定 B，但 v0.2.0 Tag 未发布。
- B 的 PR 仅允许修改现有 `projects.yaml`，Schema 固定 discovery-only、reference_only、无 dispatch/writer 权限；验证最新成功 GitHub Actions `validate` 的完整 Check ID/HEAD/PR/UTC 时间，不接受旧 PASS 掩盖新失败。
- GitHub 评论中的 AI 摘要属于 owner-account-attested 低保证来源，不能宣称独立 GitHub actor/密码学 AI 独立性；审查报告需在真实独立 AI 会话产生，GitHub Owner 仅存证。不自动把候选文档当成实际证明。
- owner 两次不同 ID 的评论依次绑定真实 CI、HEAD、index SHA、diff SHA、changed IDs、审查原文 SHA256、作用域；编辑、删除、顺序颠倒、否决、旧 Head、升级 `project_authority_effect` 均 HOLD。
- 合并后不可从可能漂移的 PR 当前 base SHA 反推历史；必须按实际 merge Commit 第一父提交与已批准的原始 base 重新核实，再沿 first-parent 链完整回查。
- 独立 AI 复核与 CI 通过只允许准备正式政策发布申请，用户对准确正式 v0.2.0 发布、插件版本锁更新及每次未来登记仍须单独批准；不动 HOT/DOT/ROOT。

**关口一文件集更新：** 目前应核对完整 20 项政策文件集。新增 B 级专项负例测试文件后，固定政策 Manifest 的准确集合为 20 项；审查必须以当前 validator 中 `RELEASE_POLICY_FILESET` 和 GitHub 实际原始字节为准，不能沿用旧候选的 19 项统计。
