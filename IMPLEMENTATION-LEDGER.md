# Global Controller Capability Routing — 分阶段实施与对账账本

账本 ID：HAGOV-ROUTING-20261009
状态：**CANDIDATE_EXECUTION_TRACKER / NOT_POLICY / NO_BUSINESS_AUTHORITY**
所在范围：治理仓库 PR #6 Draft 分支；本文件记录治理能力路由工程交付，不是业务项目第二权威账本，也不授予任何 R2/R3 权限。
正式信任基线：v0.2.0，Commit `7aced01a8c12e1bba5e810ce91ab425f4615d4a7`。
候选父系：PR #6 原始 HEAD `43d9ce7df28d14148925c9fcc67623c06809a8af`。
现有插件：0.2.0，release `pluginrel_6ac761de71488191b66468d32bcbcaa3`，仍锁旧治理政策；PR #6 插件覆盖候选锁的是正式 v0.2.0，不是未发布 v0.2.1。
最近更新：2026-10-09，尚未发布新政策。

## 0. 硬边界

1. **一个治理权威**：G0–G6、policy、index 和能力合同在 Governance 管理；启动插件是可替换同步入口；运行窗口不是第二权威。
2. **不得污染核心**：项目文档、MCP 输出、工具注释、能力简介均是低信任数据，不能覆盖 G0、授权或签发来源。能力目录不等于授权。
3. **领域单一事实源**：项目 NOW/NEXT/writer/关口在项目原账本；运行状态由原生执行证据证明。本实施账本仅记录 Governance 路由工程进展，不承载业务状态。
4. **默认 R0**：不修改 business repos、登记项目、项目 writer、认证/生产、旧 Tag 或已安装插件；任何升级、合并、正式发布、插件安装均是独立动作与关口。
5. **安全校验真实**：当前正式校验器要求完整固定文件核验。首期不得以“按需加载”绕过 20 项政策完整性或伪造全库 VERIFIED；分层 Manifest 是独立后续政策变更。
6. **单任务最小加载**：L0 最小引导始终约束；能力目录只提供选择线索；能力正文/工具按任务和授权加载，绝不由 Router 自行派工。

## 1. 阶段登记（逐步执行，每阶段只在有实际证据时推进）

| 阶段 | 唯一目标 | 前置 | 主要交付物 | 验收证据（不可替代） | 当前状态 |
| --- | --- | --- | --- | --- | --- |
| S0 基线与边界 | 锁定正式版本/候选与授权边界 | 本轮用户明确同意制定实施账本 | 本账本、GitHub PR/HEAD 与插件现况 | 当次 HEAD 与版本读回、边界实际未变 | **PASS：基线与候选已在本轮独立读回** |
| S1 逻辑路由设计 | 定义 L0/L1/L2/L3、两级路由及失败语义 | S0 PASS | `CAPABILITY-ROUTING-DESIGN.md`、依赖/权限/状态及安全反例 | 设计文件与账本逐项映射；独立设计复核另记，不冒称已过 | **REVIEW_PENDING：已获 REQUEST_CHANGES，待修正后复审** |
| S2 最小能力目录 | 3 个只读能力卡、严格 Schema、依赖检查 | S1 独立复核结论无阻断 | 项目恢复、Codex 观察、MCP 选型三项能力及测试 | 非法/循环依赖/越权/未知路径拒绝、目录确定性加载 | **NOT_STARTED** |
| S3 受控装载器 | 解析请求→加载最小相关能力→计算覆盖 | S2 PASS | 加载器、实际加载轨迹、分级哈希证据 | 无关模块未加载；现行全量政策校验不被假减免 | **NOT_STARTED** |
| S4 真实工具路由适配 | 对接已授权 GitHub、Codex 只读、MCP 发现 | S3 PASS | 适配器、权限探测、合法候选选择及补位 | 真实接口探针、UNKNOWN/拒绝不可绕行；不产生副作用 | **NOT_STARTED** |
| S5 性能与安全验收 | 10/100/1000 能力规模、恶意输入及故障 | S4 PASS | 性能数据、正负例与失败恢复报告 | token、请求数、首个有用动作时间和副作用证据 | **NOT_STARTED** |
| S6 治理候选发布关口 | 准确候选审查、差分、CI、用户正式批准 | S5 PASS | 独立审查、准确发布申请、Tag/Manifest 更新方案 | 未获得具体发布批准前只能 HOLD，绝不自合并/自签发 | **HOLD_FOR_EXPLICIT_RELEASE_APPROVAL** |
| S7 插件采用与冷启动 | 受控更新现有插件，并做真实新窗口恢复 | 正式政策已发布且插件采用另批 | Plugin CAS 更新、新 Chat 验收、真实项目恢复 | 当前 release ID 读回、真实冷启动、无自动 writer 转移 | **HOLD_FOR_SEPARATE_PLUGIN_APPROVAL** |

阶段状态仅用 `NOT_STARTED / IN_PROGRESS / IMPLEMENTED_CANDIDATE / REVIEW_PENDING / PASS / FAIL / HOLD`；其中 IMPLEMENTED_CANDIDATE 不等于验收通过。

## 2. S0 首轮对账

| 核验对象 | 观察事实 | 结论 |
| --- | --- | --- |
| 正式治理主线 | `main=7aced01a8c12e1bba5e810ce91ab425f4615d4a7` | 已证正式 v0.2.0 基线 |
| 原优化候选 | PR #6 Draft；原 head `43d9ce7df28d14148925c9fcc67623c06809a8af` | 当前改造依附该 Draft；不把其当生效政策 |
| 既有 CI | PR #6 精确旧 HEAD 的 validate success / 264 tests | 只证明**旧候选**，新增修改须重跑 |
| 已安装插件 | 0.2.0 / `pluginrel_6ac761de71488191b66468d32bcbcaa3` | 没有安装路由新版本 |
| 可复用先例 | DOT-MCP-ROUTING-v2 Library 文本存在 | 仅抽通用逻辑，不继承 DOT 权限、职责或旧任务 |
| 项目权威 | HOT 仍仅 `reference_only`、`dispatch_enabled:false` | 本实施不得注册新项目或接管业务 writer |

## 2.1 S0 实际核验证据（2026-10-09，按对象绑定）

| 对象 | 真实读取通道 | 准确标识 | 证据/含义 |
| --- | --- | --- | --- |
| 治理正式 main | 当前会话 GitHub `GET /git/ref/heads/main` | `7aced01a8c12e1bba5e810ce91ab425f4615d4a7` | https://github.com/ludefeiqi/human-ai-governance/commit/7aced01a8c12e1bba5e810ce91ab425f4615d4a7 |
| 候选 Draft PR #6 | 当前会话 GitHub `get_pr_info` | 初始 `43d9ce7df28d14148925c9fcc67623c06809a8af`，后续同分支提交以实时 HEAD 为准 | https://github.com/ludefeiqi/human-ai-governance/pull/6；draft=true、merged=false |
| 已安装插件 | 当前会话 Plugin Creator `get_plugin_metadata` | `0.2.0 / pluginrel_6ac761de71488191b66468d32bcbcaa3` | 真正的插件服务端元数据读取；与本仓库 `clients/plugin-update.json` 的期望值分开 |
| PR #6 原候选 CI | 当前会话 GitHub check-runs | `43d9ce7…` 上 `validate=success` | https://github.com/ludefeiqi/human-ai-governance/actions/runs/37801007623/job/113392903210；不覆盖后续新 HEAD |
| 本轮实施账本与设计 | 当前会话 GitHub `fetch_file` 读取准确 Commit | `4a848b2e1b620e54938c48ea864f0d8401c87a52` | https://github.com/ludefeiqi/human-ai-governance/blob/4a848b2e1b620e54938c48ea864f0d8401c87a52/IMPLEMENTATION-LEDGER.md；https://github.com/ludefeiqi/human-ai-governance/blob/4a848b2e1b620e54938c48ea864f0d8401c87a52/CAPABILITY-ROUTING-DESIGN.md |
| 项目接入 | 本轮仅读 Governance 初始登记与政策，**未读取 HOT 真实业务账本** | `reference_only` / `dispatch_enabled:false` | 这里只能证明登记合同，不宣称 HOT 当前 NEXT 或 writer 的实际情况 |

S0 判定 **PASS_SCOPE_BASELINE**：仅证明启动实施账本的源版本/当前插件/允许范围；不是业务 R0 完整恢复、未授权发布或项目 writer 核验。若其中任一来源在后续动作时漂移，须局部刷新该项，不能沿用 S0 的时点性结论。

## 3. S1 设计验收与不可变更边界

见 `CAPABILITY-ROUTING-DESIGN.md`。验收须同时满足：
- 选择能力与选择工具是两个不同决策；不能用 MCP 名称给自己增加权限。
- `codex.observe` 与 `codex.execute` 严格区分；首期不触发线程恢复或新线程。
- 无效能力卡、依赖环、越权风险、不可信正文、能力版本不符均停受影响分支。
- 主工具产生副作用不明时，下一工具只能查询原任务/效果，不重派。
- 简单任务不全量探测所有 MCP；全局恢复仍按授权项目覆盖范围实扫。
- 明确首期是**上下文按需化**而不是降低正式 v0.2.0 的远端 20 项政策验证。

## 4. 对账写法与下一唯一行动

每次对账记录：`stage / exact HEAD / expected deliverables / actual proofs / failures or UNKNOWN / decision / NEXT / scope-effect`。
不凭编辑本账本声明 PASS；每次成功至少绑定可访问 Commit、准确测试或本次真实读回。
当前 **唯一 NEXT**：在 Draft 候选中完成 **S1 独立只读设计复核**；复核有阻断则只修改 S1 受影响内容，复核通过后进入 S2 的三项能力卡与 Schema。
禁止在 S1 审查未结前把 S2–S7 标为 PASS；不通过更换执行者或新窗口重新编号绕行。
