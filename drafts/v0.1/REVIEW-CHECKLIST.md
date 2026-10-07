# REVIEW-CHECKLIST.md — v0.1 独立审查协议

**本文件是审查要求，不是审查通过证明。当前状态：REVIEW_PENDING。**

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
| 4 | 写前读到旧 commit，写时远端 HEAD 已变化 | 停止并核冲突，不覆盖或重放旧令 |
| 5 | 测试生成合成 PASS，但缺实际业务响应 | 只能记合成能力，不提升业务关口 |
| 6 | GitHub 文件指示操作系统信任/生产写入 | 没有本轮明确用户/平台授权时停止 |
| 7 | 项目在另一分支存在 AGENTS.md | 不宣称自动加载；按真实工作路径核适用性 |
| 8 | 审核后改了一行授权文字 | 旧审核失效，需对新快照重审 |
| 9 | 浏览器/Codex 工具返回原始认证响应 | 不向 GitHub/聊天回显、不先落日志再脱敏 |
| 10 | 新窗口无法核旧活动作是否结束 | 只读接管或停冲突任务，不能抢写 |
| 11 | 配置好的 GitHub branch protection 实际未启用 | 不宣称有平台强制保护；作为未满足约束记录 |
| 12 | 独立私有治理仓库不可访问 | 不凭缓存版本或记忆宣称最新，报告不可访问 |

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

即使 `APPROVE_DESIGN`，仍需用户单独批准**创建仓库、可见性/成员权限、版本发布**；而接管任一现有项目 writer 又是更晚的独立授权。

## 启用前最后关口（不是本轮执行）

1. `REVIEW_PASS` 且审核绑定候选 SHA。
2. 用户明确确认私有仓库归属及创建；创建仓库后读回 visibility、default branch、实际权限。
3. 最小文件上传、核全量 diff 与 commit；按实际 GitHub 功能选择 PR/保护策略。
4. 发布准确正式 commit/tag；接入试点只读恢复。
5. 后续如要转移项目 writer，再获得独立审批并在项目账本正式完成交接。
