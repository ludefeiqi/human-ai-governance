# GitHub 原生版本安全控制（v0.2.2 候选）

这份文件是候选政策的一部分，不是平台已启用 Branch Protection 的证据。v0.2.2 未经独立审查、真实 CI、本人精确批准和新 Tag 发布前不能替代现行 v0.2.1，也不自动更新已安装插件。

## 固定事实：当前已实际开启的 GitHub 原生保护

- GitHub 仓库 immutable-releases.enabled=true：历史 v0.2.0 和最新 v0.2.1 GitHub Releases 均已发布并返回 immutable:true。Tag 和三份 Release 附件受平台约束。旧 v0.1.0 Release 早于功能启用，所以仍 mutable；不得删除重建以掩盖历史。
- v0.2.1 源：Tag 对象 bf80e4af9b088f65f6f47c7d60313239023d7093，指向 8284952acf2ddf817b6fe4a0b7d6ef4fea4e5e18；原始 MANIFEST SHA256 为 a7de7d1b8f0ed694fa0e05b047d3af1d2316d5055bd57ae29b83de0a2130180d，49 文件。禁止改写此已冻结 Tag。Latest 显示是 UI 属性而非可信政策来源。
- Actions allowed_actions=selected，只允许 GitHub-owned Actions；其他 Marketplace verified/unverified 均不被默认授予，patterns_allowed=[]。GITHUB_TOKEN 默认 read，Actions 无 PR 审批权。
- SHA pinning repo setting sha_pinning_required=false 目前仍 false，因为已发布 v0.2.1 工作流使用 @v4/@v5，直接强制会使旧工作流无法运行。v0.2.2 候选改为已按 GitHub 官方 Tag 查得的完整 Action Commit SHA；必须在新工作流受控发布、CI 读回之后，才能另行启用 sha_pinning_required=true。
- Repo 只允许 merge commits；Squash 和 Rebase PR merge 已禁用。这支持保存两父提交和 first-parent 历史，却不阻止 direct push。
- 历史事实（2026-10-09 从 Private 变为 Public 之前）：旧 main.protected=false，Branch Protection 和 Rulesets API 曾返回 HTTP 403，提示需要 GitHub Pro 或改 Public，当时无法强制拦截 direct main push。用户之后明确选择 Public 并自行操作成功，不再维持早期“继续保持私有”策略。现行规则见下节。

## Public 单账号硬保护与 AI 独立自审核（GitHub 真实读回）

本节是新 v0.2.2 候选记录的现状事实；不代表该候选已合并、生效或取得用户发布批准。

1. 仓库现为 Public，main.protected=true。GitHub 官方支持 required_approving_review_count=0，且 require_last_push_approval=false：单账号不会因自我审核要求被锁死；required_pull_request_reviews 对象依然存在，所以 0 人不代表不用 PR。
2. GitHub 强制项未削弱：必须 PR、准确且严格的 validate 检查（GitHub Actions App 15368）；enforce_admins=true、required_conversation_resolution=true、dismiss_stale_reviews=true，allow_force_pushes=false、allow_deletions=false；允许 Merge Commit 保留完整父提交。发布前每次按当时 API 重新核权限、HEAD、CI。
3. Tag Ruleset 24772923 已经 Active，作用于 refs/tags/v*，禁止更新/删除、没有 bypass；v0.2.0 和 v0.2.1 immutable Releases 保持不变。CODEOWNERS 只负责标明 owner；require_code_owner_reviews=false，不能把同账号审核模拟成另一真人。
4. AI_R0_INDEPENDENT_REVIEW 是制度层只读门：与施工会话隔离的 AI 复核者在最新精确 PR HEAD 上读真实源差分、固定 Manifest、有效政策与适用 GitHub Actions check，记录 HEAD/Manifest SHA256/check id、发现的问题和 REQUEST_CHANGES 或 APPROVE_DESIGN_CANDIDATE_ONLY。任何新提交、CI 失败或来源变动，先暂停并重审，旧 PASS 不可重复使用。
5. USER_EXPLICIT_RELEASE_APPROVAL 单独取得：用户需要针对精确 HEAD、Manifest、发布范围及仍有效的 GitHub 强制保护明确批准；只批准审核规则从 1 改 0，不构成批准 v0.2.2 merge、Tag、Release、插件切换或业务 writer 转移。AI 复核结果、owner 账号代发的评论都不等同人类数字签名。
6. 需要区分强制等级：平台强制 PR、CI、管理员/Tag 保护；AI 复核和用户最终批准仍是治理协议与人为停止点，尚未由独立可靠的 GitHub required status check 强制，因此不能宣称 GitHub 原生实施了双账号或密码学独立审查。单账号自身具有修改仓库管理规则的能力，无法抵御 owner 凭据泄露。
7. 没有 AI 合格复核或没有用户精确批准，即便 GitHub UI 显示可合并，仍保持 HOLD_FOR_EXPLICIT_RELEASE_APPROVAL，不自动发布。今后若需要把 AI 证据提升为平台 required check，应另立正确的受信验证源，并阻止 PR 修改自身检查逻辑来给自己发 PASS。

官方机制：
- https://docs.github.com/en/rest/branches/branch-protection#update-pull-request-review-protection
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets

## 候选工作流的可执行边界

- workflow registry-validate.yml 对任何目标为 main 的 pull_request 均触发，无路径过滤，确保未来 required validate 不被 paths 过滤误跳过。
- push main、push v* Tag、release published 和手动 workflow_dispatch 也触发，全部 jobs 仅有 contents:read；checkout 无 persisted credentials；Actions 都固定完整 SHA。
- 主检查 validate 跑 pytest、validate-local、validate-candidate 与适用完整差分检查。candidate/schema PASS 不产生 Tag、项目 writer、业务动作权限。
- audit-published 仅 Tag push / Release published 触发：读取真实 annotated Tag 对象、解引用至 checked out Commit、校对 GENESIS.release_tag、真实运行 audit-main；在 Release published 时再要求 immutable=true 和带 SHA256 digest 的对应 MANIFEST Release 附件。整个流程只读，不修改 Source、Release、Tag、Repo 或插件。
- pull_request 的 validate 必须按 GitHub 官方 head.sha checkout PR 真实源 Commit（默认 refs/pull/N/merge 是合成合并树）；运行时和差分检查都对 PR_HEAD 严格 fail-closed。来源验证与模拟合并集成测试分别命名，不以 check API 的 head_sha 代替真实 checkout 证明。
- 正式发布前支持手动 workflow_dispatch 的 preflight-draft：准确 tag、numeric draft Release ID、Tag 对象 SHA、Commit、原始 MANIFEST SHA256、由用户独立核定的 SHA256SUMS.txt 原始 SHA256 **六项**。只允许真实已有 draft，核 main/GENESIS/Tag/Commit/原始清单；只接受 Manifest、Release evidence、SHA256SUMS 三个附件，下载每个附件原始字节，核全部 SHA256、由可信外部 checksum 根绑定的白名单及 GitHub asset 元数据。结束前重复 GET main/Tag/Release ID/asset ID/size/digest/updated_at，Release 与每个 asset 的 updated_at 必须实际存在且是有效 GitHub UTC 时间戳（缺失/无效值直接 HOLD），任何漂移即 HOLD；输出整个读回快照 SHA256 供发布时再次对照。纯 R0 预检不是原子锁，检查后仍可能被他人修改；发布前必须重复精确读回并需要人类批准，绝不能因为预检结果自动发布。随后在准确已核 Commit 运行 audit-main；无 write token。
- workflow_dispatch 根据 GitHub 官方平台要求，须在 default branch 的正式工作流中存在才可被触发。因此该 v0.2.2 草稿仅能独立测试其静态规则及 PR validate；首次 v0.2.2 发布前无法实际调用草稿里的新 Dispatch，必须沿现有人工精确 Tag/Manifest/草稿资产读回机制；不得冒称已部署的 preflight。
- Tag push 与 Release published 可能各触发一次只读审计；这是分离来源与不可变发布的有意双验证。
- 之前 private/main.protected=false 时，绿色 CI 仍不能阻止已发生的 direct main push；现在 Public/main.protected=true，平台确实强制 PR 和 CI。但 AI 独立只读复核和本人明确批准尚不是 GitHub 平台强制第二审核人；候选仍不自动合并发布。

## 版本与发布的不可越权顺序

候选分支 -> 全 PR 差分与固定 Manifest 哈希 -> GitHub Actions -> 独立 AI R0 只读审查（非第二 GitHub reviewer）-> 用户针对精确 HEAD/Manifest 明确批准 -> 非强制双父 Merge Commit -> GitHub main/tree 读回 -> 新 annotated Tag -> 严格 audit-main -> Release draft + 校验 -> Immutable Release -> 明确授权客户端采用。

旧 v0.2.1 及已安装的 Bootstrap 0.3.0 继续锁定既有 Tag。v0.2.2 正式发布和插件未来采用是分开的治理决定，不因更新工作流自动改变业务权限。

## 异常恢复

- HEAD/Tag/Manifest/CI/Reviewer/时间顺序任一冲突或未知，HOLD；禁止强推、删除重建 immutable Release、旧审批重放、换工具绕过拒绝。
- 回滚只使用经过审查的新 Commit / 新 Tag / 新 Release，保留旧版本、失败回执、精确文件 hash 和审查来源。
- GitHub Releases 不能代替原业务项目权威账本；注册项目只有 hot-auth-bbs 为 reference_only，dispatch_enabled=false，任何 writer 交接均为单独的项目级批准。
- 目前远端主分支强制保护已生效；更高的单账号风险是用户审批尚不能被 GH 平台当独立真人 Review 强制验证，不能用 AI、CODEOWNERS、Git Hook 或 owner 评论冒充。

## GitHub 官方文档（政策硬依据）

- Branch Protection: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- Rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
- CODEOWNERS: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- Immutable Releases: https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases
- Release REST API: https://docs.github.com/en/rest/releases/releases
- Repository immutable setting REST API: https://docs.github.com/en/rest/repos/repos
- Actions workflow syntax: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- Actions permission settings: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository
- Actions secure use: https://docs.github.com/en/actions/reference/security/secure-use
- Status checks: https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks
- Merge methods: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-merging-for-pull-requests
