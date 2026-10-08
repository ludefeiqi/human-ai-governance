# Human–AI Governance

## 当前交付状态
本分支是 **v0.2.1 合理化优化候选**，不是正式发布。基线为正式 v0.2.0 Commit `7aced01a8c12e1bba5e810ce91ab425f4615d4a7`；已发布 Tag 不移动。本次不采用任何业务项目、不转移 writer、不派工、不自动升级已安装插件。

## 一个治理权威、多个可替换实例
GOVERNANCE.md 按 G0—G6 归并稳定原则和职责；Global Controller Governance 是体系内规则权威，ChatGPT 实例负责有来源的治理判断，插件只是同步入口。项目账本与运行证据各守其事实领域。

| 规范 | 唯一负责的细则 |
| --- | --- |
| GOVERNANCE.md | G0宪章、G1组织、G2版本、G3项目、G4授权、G5恢复、G6审计总原则 |
| REGISTRY-PROTOCOL.md | 索引Schema、连续历史、A/B回执与时序 |
| HANDOFF.md | 新窗口实际读取与状态解释、写口交接 |
| CODEX-PROTOCOL.md | 有授权执行、INTENT、去重、回执及安全收口 |
| CLIENT-CONTRACT.md | 可信同步、能力协商、分层报告与降级 |
| REVIEW-CHECKLIST.md | 按规范检验，不另建审批规则 |
| RULE-MAP.md | 非授权迁移对应及语义变更说明 |
| AGENTS.md | 仅本仓库维护约束，保持原字节 |

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
clients/chatgpt-plugin 为同一现有插件的更新候选，不创建新插件/不改受众。升级前核 expected_release_id，使用正式v0.2.0的固定来源锁；不把未发布v0.2.1代码用于正式校验。附适配规则与静态/合成测试，未安装及未跑新窗口不能宣称同步完成。保留已有未替换文件。
