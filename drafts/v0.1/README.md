# Human–AI Governance · v0.1 设计草案

> **状态：DRAFT / REVIEW_REQUIRED / NOT_ACTIVE**  
> 本仓库尚未创建；本包仅为待独立审查的初稿，不是有效授权、执行令或自动加载的全局指令。

## 目的

为不同 ChatGPT 协调窗口与 Codex 任务建立跨项目、可迁移的**最小治理协议**。ChatGPT 负责与人沟通、解释目标与汇报；Codex CLI / App Server 负责经批准的工程执行；GitHub 承载规范版本、项目索引和项目自身的权威状态。聊天记录、模型记忆、工具返回值均不单独充当权威授权。

## 边界

- **治理仓库**：跨项目的协作方法、派工/回执格式、跨窗口接管协议、项目入口索引。不得放项目实际 NEXT、逐项 PASS、生产秘密或全量业务历史。
- **项目仓库**：各自固定目标与验收合同、项目 AGENTS.md、Issues/PR、唯一执行账本、证据和受控写入负责人。
- **运行时**：Codex 的线程/任务 ID、实际进程状态与本地原生证据，由对应任务环境核对；GitHub 文档不能替代运行时观察。
- **授权**：必须来自用户当次明确许可、适用平台权限和项目现行执行令；本仓库不能产生、继承或扩大授权。

## 草案目录

| 文件 | 职责 |
| --- | --- |
| `GOVERNANCE.md` | 稳定的治理边界、权责、冲突处理、版本与接入规则 |
| `CODEX-PROTOCOL.md` | CLI/App Server 派工与结构化回执、单写及失败停止 |
| `HANDOFF.md` | 新窗口恢复、避免双派工和离线/失败接管 |
| `projects.yaml` | **仅项目索引**，不复制任何项目当前任务或权限 |
| `AGENTS.md` | 仅指导 Codex 修改**本治理仓库本身**，并非自动全局生效 |
| `REVIEW-CHECKLIST.md` | 独立只读复核、反例与启用关口 |

## 建议启用流程

1. 本草案独立只读审查，绑定审核的完整文件哈希；修订时作废旧审核。
2. 用户确认仓库归属、私有可见性、版本号及启用范围；再创建**独立私有仓库**，不迁移旧工程树。
3. 在 `main` 建立可读文档；是否使用受保护分支 / PR 审查，按 GitHub 实际计划与权限逐项核实，未核实时不可声称强制生效。
4. 固定提交 SHA 并在启用后发布版本标签（例如 `v0.1.0`）；各项目**主动引用**确定版本，不能因全局仓库变化自动被覆盖。
5. 先用 HOT/AUTH/BBS 做**只读跨窗口发现试点**；只有经用户授权、项目原负责人安全交接且项目账本写回后，才考虑切换日常单写负责人。

## 文档依据（供审查）

- [OpenAI: Codex app-server 调用概述](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server)
- [OpenAI: AGENTS.md 及上下文精简](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
- [GitHub: Contents API 更新所需 SHA](https://docs.github.com/en/rest/repos/contents)
- [GitHub: 分支保护与规则集](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)

**非目标**：新 MCP、数据库、常驻代理群、跨项目统一业务账本、无人工授权的自动生产调度。
