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
