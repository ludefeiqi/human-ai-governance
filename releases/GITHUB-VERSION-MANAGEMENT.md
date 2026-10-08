# GitHub 原生版本安全控制（v0.2.2 候选）

这份文件是候选政策的一部分，不是平台已启用 Branch Protection 的证据。v0.2.2 未经独立审查、真实 CI、本人精确批准和新 Tag 发布前不能替代现行 v0.2.1，也不自动更新已安装插件。

## 固定事实：当前已实际开启的 GitHub 原生保护

- GitHub 仓库 immutable-releases.enabled=true：历史 v0.2.0 和最新 v0.2.1 GitHub Releases 均已发布并返回 immutable:true。Tag 和三份 Release 附件受平台约束。旧 v0.1.0 Release 早于功能启用，所以仍 mutable；不得删除重建以掩盖历史。
- v0.2.1 源：Tag 对象 bf80e4af9b088f65f6f47c7d60313239023d7093，指向 8284952acf2ddf817b6fe4a0b7d6ef4fea4e5e18；原始 MANIFEST SHA256 为 a7de7d1b8f0ed694fa0e05b047d3af1d2316d5055bd57ae29b83de0a2130180d，49 文件。禁止改写此已冻结 Tag。Latest 显示是 UI 属性而非可信政策来源。
- Actions allowed_actions=selected，只允许 GitHub-owned Actions；其他 Marketplace verified/unverified 均不被默认授予，patterns_allowed=[]。GITHUB_TOKEN 默认 read，Actions 无 PR 审批权。
- SHA pinning repo setting sha_pinning_required=false 目前仍 false，因为已发布 v0.2.1 工作流使用 @v4/@v5，直接强制会使旧工作流无法运行。v0.2.2 候选改为已按 GitHub 官方 Tag 查得的完整 Action Commit SHA；必须在新工作流受控发布、CI 读回之后，才能另行启用 sha_pinning_required=true。
- Repo 只允许 merge commits；Squash 和 Rebase PR merge 已禁用。这支持保存两父提交和 first-parent 历史，却不阻止 direct push。
- 现有 private personal repository main.protected=false。Branch Protection 和 Rulesets GET 均 HTTP 403，明确提示需要 GitHub Pro 或转公开。继续保持私有，不为节省费用转公开。当前仍无 GitHub 平台级强制 PR/Review/CI 防污染锁。 在套餐门禁生效前，以上设置不构成对远端 main 的强制保护。

## 必须建立的强制门禁（套餐/真实独立审核人尚缺）

1. 用户自行为私有个人仓库启用官方支持的 GitHub Pro，或使用同等支持的正式计划；涉及账单，需本人操作，此候选不替用户购买。
2. 在 Settings / Rules / Rulesets 或 Branch protection 对 main 实施 ACTIVE 规则：Require PR before merging；至少 1 名不同 GitHub 身份且具有相应权限的真人 reviewer；Dismiss stale approvals；Require approval for most recent reviewable push；Require conversation resolution；Require status check 名称唯一且确切为 validate（来源 GitHub Actions）；Do not allow bypassing；拒绝 force push 和删除主分支。不能假装机器人同账号评论是独立 GitHub Review。
3. 仓库所有权文件 .github/CODEOWNERS 只是通知/归属。必须在 base branch 生效且平台支持 required code owner approvals 时才强制；只有仓库所有者一个 GitHub 账号时，要求自己批准自己发起的 PR 会死锁。先落实真实可审查的独立 reviewer，不制造虚假身份。
4. 对 refs/tags/v* 配置官方 Tag Ruleset，禁止修改/删除已有 Tag，而保留经过人类批准的新 Tag 创建路线。将不可变 Release 和 Tag Ruleset 分开，不把前者误说成 main 的保护。
5. 所有设置写后必须以 GitHub 真实 API 读回，确认 main.protected、active rulesets、required status checks、Review/No-bypass 及 tag rules 实际生效。不接受 403 或 YAML 声明充当验收结果。

## 候选工作流的可执行边界

- workflow registry-validate.yml 对任何目标为 main 的 pull_request 均触发，无路径过滤，确保未来 required validate 不被 paths 过滤误跳过。
- push main、push v* Tag、release published 和手动 workflow_dispatch 也触发，全部 jobs 仅有 contents:read；checkout 无 persisted credentials；Actions 都固定完整 SHA。
- 主检查 validate 跑 pytest、validate-local、validate-candidate 与适用完整差分检查。candidate/schema PASS 不产生 Tag、项目 writer、业务动作权限。
- audit-published 仅 Tag push / Release published 触发：读取真实 annotated Tag 对象、解引用至 checked out Commit、校对 GENESIS.release_tag、真实运行 audit-main；在 Release published 时再要求 immutable=true 和带 SHA256 digest 的对应 MANIFEST Release 附件。整个流程只读，不修改 Source、Release、Tag、Repo 或插件。
- pull_request 的 validate 必须按 GitHub 官方 head.sha checkout PR 真实源 Commit（默认 refs/pull/N/merge 是合成合并树）；运行时和差分检查都对 PR_HEAD 严格 fail-closed。来源验证与模拟合并集成测试分别命名，不以 check API 的 head_sha 代替真实 checkout 证明。
- 正式发布前支持手动 workflow_dispatch 的 preflight-draft：准确 tag、numeric draft Release ID、Tag 对象 SHA、Commit、原始 MANIFEST SHA256 共五项。只允许真实已有 draft，核 main/GENESIS/Tag/Commit/原始清单/每个资产 digest 和必需的 MANIFEST、SHA256SUMS；再在准确已核 Commit 运行 audit-main。preflight 不发布、不更新 Tag、无 write token，预检通过仍非用户发布批准。
- workflow_dispatch 根据 GitHub 官方平台要求，须在 default branch 的正式工作流中存在才可被触发。因此该 v0.2.2 草稿仅能独立测试其静态规则及 PR validate；首次 v0.2.2 发布前无法实际调用草稿里的新 Dispatch，必须沿现有人工精确 Tag/Manifest/草稿资产读回机制；不得冒称已部署的 preflight。
- Tag push 与 Release published 可能各触发一次只读审计；这是分离来源与不可变发布的有意双验证。
- 在 Pro 强制规则配置完成前：即使 CI 失败，也只能给出报警/停止建议，**不能阻止已发生的 direct main push**；因此本候选不自动合并发布、不伪报强制保护到位。

## 版本与发布的不可越权顺序

候选分支 -> 全 PR 差分与固定 Manifest 哈希 -> GitHub Actions -> 真实独立人审 -> 用户针对精确 HEAD/Manifest 明确批准 -> 不允许 force 的 two-parent merge -> 实际 main/tree 读回 -> 创建新的 annotated Tag（Tag 不得复用或移动）-> 严格 audit-main -> Create GitHub Release draft + 添加 MANIFEST/来源证据 + 核资产摘要 -> Publish immutable Release -> 确认 Latest -> 另行授权插件更新/冷启动。

旧 v0.2.1 及已安装的 Bootstrap 0.3.0 继续锁定既有 Tag。v0.2.2 正式发布和插件未来采用是分开的治理决定，不因更新工作流自动改变业务权限。

## 异常恢复

- HEAD/Tag/Manifest/CI/Reviewer/时间顺序任一冲突或未知，HOLD；禁止强推、删除重建 immutable Release、旧审批重放、换工具绕过拒绝。
- 回滚只使用经过审查的新 Commit / 新 Tag / 新 Release，保留旧版本、失败回执、精确文件 hash 和审查来源。
- GitHub Releases 不能代替原业务项目权威账本；注册项目只有 hot-auth-bbs 为 reference_only，dispatch_enabled=false，任何 writer 交接均为单独的项目级批准。
- 平台分支保护缺失被明确保留为最高剩余风险，不以模型审查、CODEOWNERS、Git Hook 或 Owner 评论替代远端规则。

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
