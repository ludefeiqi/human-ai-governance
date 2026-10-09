# Human–AI Governance

## 当前交付状态
截至 2026-10-09，正式公开政策为 **v0.2.2 Immutable Release**，固定 Commit `b125c54af9f178c2607238c792bca72d2569e4b5`。本开发分支提议把 **HAG-CORE-001** 作为 `GOVERNANCE.md` 的唯一核心章程；本次文本尚未获准确候选批准、合并、发布或被插件采用，不自动获得业务权限、writer、执行令或生产访问。旧正式 Tag 和原历史证据保持原样。

## 项目开发的唯一核心边界（候选）

**总章程唯一正本：根目录 [GOVERNANCE.md](GOVERNANCE.md) 的 HAG-CORE-001 章。** 五职责域固定，普通开发必须在 N1—N6 准入后挂接原域，保持 K01—K12 不变量；开发指导见 [AGENTS.md](AGENTS.md)，独立验收见 [REVIEW-CHECKLIST.md](REVIEW-CHECKLIST.md)。PR 应记录具体必要性、owner_node、准确差分、证据、权限、停用及待批准项。

本段是候选开发指引，不是现行生效许可。**文档制定规则，受保护 PR/CI 与执行宿主承担实际约束**；未真实配置或验证的强制能力不得声称 ENFORCED。

## 一个治理权威、多个可替换实例
GOVERNANCE.md 按 G0—G6 归并稳定原则和职责；Global Controller Governance 是体系内规则权威，ChatGPT 实例负责有来源的治理判断，插件只是同步入口。项目账本与运行证据各守其事实领域。

| 规范 | 唯一负责的细则 |
| --- | --- |
| GOVERNANCE.md | 拟议 HAG-CORE-001 核心合同；现有 G0宪章、G1组织、G2版本、G3项目、G4授权、G5恢复、G6审计总原则 |
| REGISTRY-PROTOCOL.md | 索引Schema、连续历史、A/B回执与时序 |
| HANDOFF.md | 新窗口实际读取与状态解释、写口交接 |
| CODEX-PROTOCOL.md | 有授权执行、INTENT、去重、回执及安全收口 |
| CLIENT-CONTRACT.md | 可信同步、能力协商、分层报告与降级 |
| REVIEW-CHECKLIST.md | 按规范检验，不另建审批规则 |
| RULE-MAP.md | 非授权迁移对应及语义变更说明 |
| AGENTS.md | 仅约束本仓库维护，拟议增加候选核心合同开发检查；已发布旧版保持原字节 |

## 实现与测试
registry/GENESIS.json 固定候选发布身份与初始索引；registry/validate_registry.py 只从授权 GET 核验；Manifest 包含固定政策及测试，不包含动态 projects.yaml。候选的初始项目列表没有改变；发布前须再次核 main 未漂移及列表没有遗漏。

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
