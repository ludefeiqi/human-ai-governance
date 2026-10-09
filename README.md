# Human–AI Governance

## 规范来源与版本查验

本 README 仅提供仓库导航，不以固定文字宣称“永远当前的最新版本”。**发布 ≠ 采用 ≠ 派工授权**，分别查证：

- **正式政策发布**：从 [GitHub Releases](https://github.com/ludefeiqi/human-ai-governance/releases) 取得实际正式版本；按 `Tag → Commit → 原始 MANIFEST.sha256 → Immutable Release` 核对政策来源、固定文件及发布证据。`main`、README、绿色 CI 或合并记录均不能单独证明发布或人类准确批准。
- **客户端实际采用**：通过当前安装插件的版本、`source-lock`、当次资源加载和必要独立冷启动验证；GitHub 发布不等于所有客户端已更新。
- **项目实际执行**：按项目当前冻结合同、权威账本、现任 writer、有效授权和唯一 INTENT 判断；治理登记可读或测试通过不产生业务派工权。

历史正式 Tag、Commit、Release 和审查回执均保持原状；旧版事实可以作为历史来源，不得冒称当次最新版本。

## 核心架构开发边界

**总章程唯一正本：根目录 [GOVERNANCE.md](GOVERNANCE.md) 的 HAG-CORE-001 章。** 五职责域及 K01—K12 保持固定；**新增独立能力、权限或常驻依赖**必须先完成 N1—N6 准入，普通局部修复按照现有 G4／G6 进行比例审查；开发指导见 [AGENTS.md](AGENTS.md)，独立验收见 [REVIEW-CHECKLIST.md](REVIEW-CHECKLIST.md)。PR 应记录具体必要性、owner_node、准确差分、证据、权限、停用及待批准项。

本节仅用于定位现有规范和维护入口；应由实际已发布且被客户端采用的政策决定适用规则。**文档制定规则，受保护 PR/CI 与执行宿主承担实际约束**；未真实配置或验证的强制能力不得声称 ENFORCED；本 README 不授予项目 writer 或执行权限。

## 一个治理权威、多个可替换实例
GOVERNANCE.md 按 G0—G6 归并稳定原则和职责；Global Controller Governance 是体系内规则权威，ChatGPT 实例负责有来源的治理判断，插件只是同步入口。项目账本与运行证据各守其事实领域。

| 规范 | 唯一负责的细则 |
| --- | --- |
| GOVERNANCE.md | 正式 HAG-CORE-001 核心合同；G0宪章、G1组织、G2版本、G3项目、G4授权、G5恢复、G6审计总原则 |
| REGISTRY-PROTOCOL.md | 索引Schema、连续历史、A/B回执与时序 |
| HANDOFF.md | 新窗口实际读取与状态解释、写口交接 |
| CODEX-PROTOCOL.md | 有授权执行、INTENT、去重、回执及安全收口 |
| CLIENT-CONTRACT.md | 可信同步、能力协商、分层报告与降级 |
| REVIEW-CHECKLIST.md | 按规范检验，不另建审批规则 |
| RULE-MAP.md | 非授权迁移对应及语义变更说明 |
| AGENTS.md | 仅约束本仓库实际适用范围内的维护；不自动影响其他项目或实例；旧正式版本保持原字节 |

## 实现与测试
`registry/GENESIS.json` 记录与固定政策版本绑定的发行锚点和初始索引；`registry/validate_registry.py` 在授权范围内用 GET 核验。`MANIFEST.sha256` 覆盖固定政策及测试，不包含动态 `projects.yaml`；现行动态目录须按当前 `main` 和相应历史审计单独核真。新的政策候选必须走独立评审、准确批准和正式发布流程，不得用本 README 自行激活。

复现（使用已有隔离环境或经批准创建项目局部环境，不改全局依赖）：
```sh
python -m pytest -q -p no:cacheprovider
python -m registry.validate_registry --root . validate-local
python -m registry.validate_registry --root . validate-candidate
git diff --check
```
发布后的 audit-main/pre/post/audit-chain 必须给准确外部 `--expected-policy-commit`；候选 Tag 不存在时 LIVE 验证必须 HOLD。B 是 owner所发布AI证明的较低保证等级，不是第二GitHub actor或真人签名。

## 插件覆盖包
本仓库 `clients/chatgpt-plugin` 存放的是早期版本的历史候选覆盖包，并不代表当前已安装插件。当前运行实例须从真实插件元数据及来源锁核对，不能凭本目录或旧 README 自动推定其版本、授权或采用。任何新政策发布后仍需独立执行插件采用和新窗口验收。
