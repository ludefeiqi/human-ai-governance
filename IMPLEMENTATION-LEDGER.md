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
| S1 逻辑路由设计 | 定义 L0/L1/L2/L3、两级路由及失败语义 | S0 PASS | `CAPABILITY-ROUTING-DESIGN.md`、依赖/权限/状态及安全反例 | 设计文件与账本逐项映射；独立设计复核另记，不冒称已过 | **PASS_DESIGN：修订后独立只读 APPROVE_DESIGN** |
| S2 最小能力目录 | 3 个只读能力卡、严格 Schema、依赖检查 | S1 独立复核结论无阻断 | 项目恢复、Codex 观察、MCP 选型三项能力及测试 | 非法/循环依赖/越权/未知路径拒绝、目录确定性加载 | **PASS**（仅静态候选，不授权运行） |
| S3 受控装载器 | 解析请求→加载最小相关能力→计算覆盖 | S2 PASS | 加载器、实际加载轨迹、分级哈希证据 | 无关模块未加载；现行全量政策校验不被假减免 | **PASS**（仅候选纯静态上下文） |
| S4 真实工具路由适配 | 对接已授权 GitHub、Codex 只读、MCP 发现 | S3 PASS | 适配器、权限探测、合法候选选择及补位 | 真实接口探针、UNKNOWN/拒绝不可绕行；不产生副作用 | **PASS**（仅 R0 观测及禁用路由候选） |
| S5 性能与安全验收 | 10/100/1000 能力规模、恶意输入及故障 | S4 PASS | 性能数据、正负例与失败恢复报告 | token、请求数、首个有用动作时间和副作用证据 | **IMPLEMENTED_CANDIDATE / REVIEW_PENDING** |
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
当前 **唯一 NEXT**：先对 S5 已实现的 10/100/1000 合成规模与安全验收候选核准确 GitHub CI、原始测量及独立只读审查；有阻断只返修实际命中范围。S5 未经独立 PASS 不得推进 S6；即便 S5 PASS，S6 发布与 S7 插件采用仍各须用户另行明确批准。
禁止在 S1 审查未结前把 S2–S7 标为 PASS；不通过更换执行者或新窗口重新编号绕行。

## 5. S1 两轮独立设计审查（2026-10-09）

- 首轮 HEAD `4a848b2e1b620e54938c48ea864f0d8401c87a52`：REQUEST_CHANGES，S0 缺真实来源、S1 缺矩阵/向量/计量。保留否决记录。
- 复审 HEAD `272906c1210f2ce13eb190f8cd7057175d3db5c2`：独立 Codex gpt-5.6-sol R0 只读 APPROVE_DESIGN；四处缺口已补齐，未见本范围内设计阻断。复审核了真实 GitHub HEAD 和插件服务端元数据，未运行测试。
- 修订前一次 GitHub Actions success（job 113438420369）不可代替后续 Commit CI；每次有新 Head 都重新检查。
- 效力：S0 PASS_SCOPE_BASELINE；S1 PASS_DESIGN；唯一 NEXT=S2。此批准仅为候选设计阶段，不是正式政策/业务授权。

## 6. S2 静态能力目录候选实施记录（2026-10-09）

- 新增 registry/capabilities/ 四项 JSON（Schema + 3 张禁用态只读能力卡），registry/validate_capabilities.py 静态验证器，以及 tests/test_capability_catalog.py 的 19 项覆盖；更新 registry/validate_registry.py 的本地验证入口与 MANIFEST.sha256。
- 当前只定义，不调用：enabled=false / invocation=FORBIDDEN / implementation=NONE；source policy pin 仍为已发布 v0.2.0；不加载未发布 v0.2.1 作为运行政策。
- 协调者本人复验：全套 pytest **283 passed**；validate-local status VERIFIED，固定候选 Manifest=43；validate-candidate status SCHEMA_PRECHECK_PASS、approval_verified=false、registry_trusted=false；git diff --check 通过。
- 已定义依赖顺序 tool.route → codex.observe → project.restore；真实 MCP、Codex 调用=0；新增能力均不授权调用。
- 阶段裁定：**S2 IMPLEMENTED_CANDIDATE / REVIEW_PENDING**。该测试仅证明静态候选和合成覆盖，未取得独立设计复核及准确新 HEAD 的原生 GitHub CI，不能标 S2 PASS。

## 7. S2 首次独立复核阻断（2026-10-09）

- 精确候选：`da83ad52e3bd82041748bf063fc0b921d52dbc7a`。GitHub PR #6 仍 Draft，实际 CI `validate` completed/success，job `113443441112`；协调者本地 283 tests PASS、validate-local/validate-candidate PASS。
- 独立 Codex gpt-5.6-sol R0 只读结论 **REQUEST_CHANGES**。阻断①：strict Schema、禁用态、无副作用和 source policy lock 不得只依赖同候选可变 Schema，必须在验证器中独立核不可放宽不变量。阻断②：路径链父目录 symlink 未充分拒绝。阻断③：固定政策远端核验未证明能力源文件的 Git mode；Manifest raw SHA 不证明文件模式。
- 裁定：**S2 HOLD / NOT ACCEPTED**，旧 PASS 测试不得覆盖此审查；仅修上述安全范围并加对应负例，准确新 HEAD 复核后才转 PASS。S3–S7 均不可前进。


## 8. S2 阻断修复候选（2026-10-09，待独立复审）

- 前置精确远端 HEAD `1c91da6091d7b04bafa41efc86edbaa4d8839475`；此前 S2 `REQUEST_CHANGES` 保留历史，不能拿此前 283 PASS/旧 CI 抵消阻断。
- 修复①：Python 静态守卫独立于同候选 JSON Schema 强制卡字段、版本、禁用态、R0/无副作用、policy lock、合同形状和类型；即便 JSON Schema 同时放宽，非法卡仍拒绝。
- 修复②：能力文件、能力目录、source-lock 逐级检查内部父目录真实类型，禁止 symlink（包括指向仓库内部的 symlink）；保留叶文件普通/不可执行要求。
- 修复③：远端固定政策完整字节哈希核对后，追加绑定准确 pinned Commit 的完整 Git Tree 只读校验；覆盖全部固定文件和 MANIFEST，要求 blob/100644，拒绝 executable、symlink、submodule、缺项、重复项、truncated/漂移树。
- 对应负例已扩充；协调者本地 `pytest -q -p no:cacheprovider` **309 passed**；`validate-local` status VERIFIED、`validate-candidate` status SCHEMA_PRECHECK_PASS（approval_verified=false、registry_trusted=false）；Manifest 43 且全文件重算；`git diff --check` 通过。
- 阶段裁定：**IMPLEMENTED_CANDIDATE / REVIEW_PENDING**。本节测试不构成独立复核/正式发布/业务授权。准确新 HEAD、原生 GitHub CI 和独立只读审查须另行读回记录。


## 9. S2 精确候选独立通过（2026-10-09）

- 修复完整候选/原生 GitHub Draft PR #6：`258c786223eb64d83d0869b3d578bb4029068683`。CI 工作流 `P2 Registry Candidate Verification` 的 `validate` completed/success，job `113454657835`，https://github.com/ludefeiqi/human-ai-governance/actions/runs/37818935312/job/113454657835。
- 协调者基于同一修复提交的本地全量 `309 passed`、`validate-local VERIFIED`、`validate-candidate SCHEMA_PRECHECK_PASS`（无审批/派工能力）；Manifest 文件集 43，全量哈希；真实 GitHub Git Tree `5d654b7d74b35332e960582f6613ebdf166523ec` 读取 `truncated=false`，能力 JSON、Schema、两个验证器与 Manifest 均 `blob/100644`。
- 独立 Codex `gpt-5.6-sol` / read-only / ephemeral 对准确修复 HEAD、原先三个阻断及本次差分进行只读设计复审，结论 **APPROVE_DESIGN**，未发现本范围的新阻断；独立审查不是人类签发、运行授权或 GitHub 的第二个审批账号。
- 结论：**S2 PASS_STATIC_CANDIDATE**。旧 `REQUEST_CHANGES` 保留历史；本节只对 S2 静态规范、代码和合成/远端证据有效。S3 尚未实施；S6 正式政策发布及 S7 插件采用均维持原审批关口。


## 10. S3 最小上下文装载候选（2026-10-09，待独立审查）

- 已核前置：S2 精确已审提交 `258c786223eb64d83d0869b3d578bb4029068683` 的真实 CI 与独立 `APPROVE_DESIGN`；S2 账本接受提交 `8fb05096c98a615b0326f8db72ce6b4c4b632554` 已推送原 PR #6 Draft，`validate` completed/success，job `113455921412`。原 `main` 仍锁 v0.2.0。
- S3 新增纯函数式 `registry/route_capabilities.py`，输入只接受三个规范化意图（PROJECT_RESTORE_READ_ONLY / CODEX_OBSERVE_EXISTING_READ_ONLY / TOOL_ROUTE_PLAN_ONLY）；固定目录先完整预检 3 个能力卡，再只把依赖闭包关联正文送入候选上下文。未列出任务直接拒绝，不由自由文字、能力卡目的文本或可变 Schema 授权。
- 返回字段显式分离 `catalog_preflight_scope=ALL_FIXED_CARDS` 与 `context_loaded_ids`；未把读取全目录说成按需免核验。纯本地静态候选未运行远端已发布政策核验，明确报告 `full_released_policy_verification=NOT_PERFORMED_REQUIRED_FOR_REAL_LAUNCH`、`activation=DISABLED`、`dispatch_authorized=false`、`registry_trusted=false`、`tools_invoked=0`；未引入实际工具路由、网络或业务侧效果。
- 真实目录只读试载（每次完整预检三卡）：项目恢复 `tool.route+project.restore`，context_chars=2361；Codex 只读观察 `tool.route+codex.observe`，context_chars=2211；工具候选计划 `tool.route`，context_chars=1122；无关上下文模块=0、工具调用=0。该指标为结构化 JSON 字符数，不是模型 Token 或实际工作耗时。
- 扩增 18 项 S3 测试，覆盖三类闭包、零越权、恶意任务、未选卡异常、提示注入、preflight 后文件漂移、symlink、确定性、source-lock 拒绝；全量 `327 passed`、`validate-local VERIFIED`、`validate-candidate SCHEMA_PRECHECK_PASS`，Manifest 固定候选 45 项。
- 当前裁定：**S3 IMPLEMENTED_CANDIDATE / REVIEW_PENDING**，只有 CI、准确 HEAD 的独立只读审查均过且无阻断，才能标 S3 PASS 并进入 S4。


## 11. S3 准确候选独立通过（2026-10-09）

- S3 原生 GitHub Draft PR #6 精确候选 `56437b42c115b3b0544fcaeaaa6015c24d4b8a21`；GitHub Actions `P2 Registry Candidate Verification/validate` completed/success，job `113458226172`，https://github.com/ludefeiqi/human-ai-governance/actions/runs/37819985235/job/113458226172；该 Commit 真实 Git Tree `8c7ce118c043d10b8c11f69b5f6a02dab5f35671`，truncated=false，新 Router、新测试和 Manifest 都是 blob/100644。
- 专用本地已装依赖 Python 环境 `327 passed`、`validate-local VERIFIED`、`validate-candidate SCHEMA_PRECHECK_PASS`，并做三类真实候选目录静态试载。独立 Codex `gpt-5.6-sol` / read-only / ephemeral 针对准确候选差分及 S3 设计返回 **APPROVE_DESIGN**，未发现本范围新阻断；审查者在其沙盒尝试用系统 Python 直接试载时缺少 jsonschema，未独立复跑测试，因此其结论是设计复核，不是测试复验。
- **S3 PASS_STATIC_CONTEXT_CANDIDATE**：本候选仅提供结构化装载计划；没有正式政策远端完整验证、已授权工具实际调用、真实模型上下文 token/耗时实测、业务能力执行或插件采用。前述上下文字符数仅是序列化候选正文的精确字符计数。
- 唯一 NEXT 转 S4；S4 不因本结论自动派工或授权。S6/S7 发布和采用关口维持 HOLD。


## 12. S4 R0 真实工具路由候选（2026-10-09，待独立复审）

- 当前基础：S3 已审并通过的候选 `56437b42c115b3b0544fcaeaaa6015c24d4b8a21`；S3 通过账本 `c0fbb0b92f0557164b8235c2ce1d6a2ab7dcee60`，CI job `113459645411` completed/success；该时点本地分支 HEAD 与 PR #6 远端 Draft HEAD 相同，正式 main `7aced01a8c12e1bba5e810ce91ab425f4615d4a7` 未变。
- **真实 GitHub R0**：本次会话通过已连接 GitHub 的 `get_pr_info`、`fetch_file` 读取私有 Governance PR #6 和同分支 `IMPLEMENTATION-LEDGER.md`；Mac 上 `gh api --method GET repos/ludefeiqi/human-ai-governance` 返回实际私库元数据。只证明此范围当前真实只读能力，不推断其它项目的读取或业务写权限。
- **真实 Codex R0**：Mac 已装 `codex-cli 0.161.0`、实际存在 App Server 进程。按本机 CLI 生成协议 Schema 读取 `InitializeParams` / `ThreadListParams`；启动临时 stdio 只读观察端，真实 `initialize`、`thread/list` RPC 成功，限定治理工作目录及 /tmp 与 /private/tmp 别名，记录数 0，nextCursor=false，并已停止临时观察端。**现存特定线程或执行后态为 RUNTIME_UNKNOWN**，没有调用 `thread/read`（无匹配 ID）、`thread/resume`、`thread/start`、`turn/start`，也未新建工作线程或重派原任务；真实进程存在不等于原线程有效。
- **真实 MCP 暴露**：当前 Chat host 可枚举 GitHub、Remote Desktop Commander 和 PENEE Multica MCP 的暴露方法；GitHub 与 RDC 实际 R0 方法已经返回。只从当次 tool metadata 发现，不把工具说明或安装记录当权限，未连接新工具；无直接 Codex MCP 暴露，Codex 探针来自 Mac 原生 App Server。
- 新增 `registry/route_tool_adapters.py`：硬编码三类 S3 固定任务到五个只读方法的候选路由，并以 scope+方法+权限证据的确定结构生成 **R0_ROUTE_PROPOSAL**；仅消费来自宿主已核只读探针的观测记录，不主动调用、重连、授权或探测工具。自然语言、MCP 描述、非法 method、错误 scope、未知工具、字段注入及含控制字符的字段一律拒绝。候选输出永远 `invocation=FORBIDDEN_IN_CANDIDATE`、`dispatch_authorized=false`、`runtime_permission_granted=false`、`tools_invoked=0`，报告外部 TASK_VERIFIED 只表示待宿主再校验证据，不能自行提升权限。
- 后备工具只在主路径 `TOOL_UNAVAILABLE / NOT_CONFIGURED` 且宿主明确允许、备选同 scope 已读探针可用时形成 **候选**；遇 `AUTHORIZATION_BLOCKED / RUNTIME_UNKNOWN / EFFECT_UNKNOWN` 或未探测均 HOLD，不改用 RDC/执行接口绕过。Codex 当前仅规划 `thread/list`；`thread/read includeTurns=false` 被登记为严格只读候选但无既有线程 ID，未宣称真实读取验收完成。
- 对应 41 项 S4 定向测试；全量 `368 passed`、`validate-local VERIFIED`、`validate-candidate SCHEMA_PRECHECK_PASS`（approval_verified=false、registry_trusted=false）；Manifest 47 项且变动文件 raw SHA 重算；实际试载三个候选路由均零内部工具调用和零派工。实际 R0 探针由宿主/短命只读进程执行，因此**不能**把候选适配器的 tools_invoked=0 误读为整个验收阶段零只读查询。
- 阶段裁定：**S4 IMPLEMENTED_CANDIDATE / REVIEW_PENDING**。本段仅为候选和当次观察事实；真实权限和特定工作运行状态必须在使用时再核。准确新 HEAD GitHub CI 与独立 R0 审查通过后才能判 S4 PASS；未完成独立复核前 S5–S7 不推进。


## 13. S4 精确候选独立通过（2026-10-09）

- S4 准确候选 HEAD：`80c55030fc56ca81b673c5d9a3f13355124a851c`，原 GitHub Draft PR #6。GitHub Actions `P2 Registry Candidate Verification/validate` completed/success，job `113470716724`，https://github.com/ludefeiqi/human-ai-governance/actions/runs/37823634185/job/113470716724；远端固定 Git Tree `2f0780a391b9fe2439752f600c650ea1857a37c0` truncated=false，新增适配器/测试及 Manifest 均 `blob/100644`。
- 准确 HEAD 的独立 `codex exec --ephemeral -m gpt-5.6-sol --sandbox read-only` 对 S4 差分、安全合同、真实 R0 观察限制和 47 项 Manifest 完整性进行只读设计复核，结论 **APPROVE_DESIGN**，未见 S4 范围内阻断；复核者未替代本地 368 tests 或原生 GitHub CI。
- **S4 PASS_R0_PROBED_ROUTE_CANDIDATE**：已验证 GitHub 私库只读、Codex App Server 真实 `thread/list`、本会话 MCP 暴露方法；路由器仅是被禁用的提案生成器，仍未在正式插件生效或执行实际受控选中工具。治理目录业务采用、身份/权限、生产、writer、原工作线程后态均未改变；对 Codex 已存在任务没有可匹配 ID，故原任务运行态保持 `RUNTIME_UNKNOWN`，`thread/read` 未实测。
- 当前唯一 NEXT=S5。此 S4 通过不授予 R2/R3、候选策略发布或插件升级，亦不替代 S5 的 10/100/1000 性能与攻击负例。


## 14. S5 性能/安全合成验收候选（2026-10-09，待独立复审）

- S4 前置：原 GitHub Draft PR #6 `80c55030fc56ca81b673c5d9a3f13355124a851c` 的 GitHub CI completed/success job `113470716724` 及独立 Codex R0 `APPROVE_DESIGN`；接受账本 HEAD `08385e410d127247467c1c07cc01d12b66793efe` 的 validate job `113471764056` completed/success；未修改正式 main v0.2.0 / Tag / Plugin / 业务仓库。
- 新增 `registry/benchmark_route_scaling.py` 与 `tests/test_route_scaling.py`，三组 **10/100/1000 合成能力元数据**固定同一请求 `codex.observe + project.restore`、同一三项相关能力与依赖图、同一 Python 会话及 30 次测量。**先完整检查所有合成 N 项依赖图**（未选中的坏依赖/环也要 fail-closed），再单独计最小闭包选择时间；所选上下文来自真实 S2 已禁用三张卡的序列化正文，不把全部合成目录冒充模型正文。
- 单轮结果（仅此环境/样本，含性能噪声）：

  | 合成 N | 全目录元数据字符 | 合成根分片索引字符 | 所选三卡正文字符 | 无关正文数 |
  | ---: | ---: | ---: | ---: | ---: |
  | 10 | 209 | 150 | 3450 | 0 |
  | 100 | 2279 | 151 | 3450 | 0 |
  | 1000 | 22979 | 152 | 3450 | 0 |

- 对同一个 synthetic.extra 前缀的**假设性**二级目录分片，根摘要维持四个分组，选中分片索引为 48 字符；这是合成 taxonomy 的实验，不是现有 S3 真实分片装载已部署，也不证明任意类别增长都恒时或无需完整政策完整性校验。若实际类别数量增长，必须另行独立实施分片与实测。全量原目录索引字符会随 N 增长，成本明确未隐瞒。
- 单次 Python monotonic 本地微测量：N=1000 全合成元数据依赖预检约 1.51 ms；仅最小选择 30 次中位数约 0.0033 ms（对模型/远端延迟毫无代表性）。`TOKEN_UNKNOWN`，正式启动时 `real_remote_fetch_count`、`real_probe_count`、`real_time_to_first_valid_result_ms` 均 `NOT_MEASURED`；本合成实验 `synthetic_network_calls=0`、`external_side_effects=0`。
- **单独真实 R0 GitHub 读取**：对精确已验证 Commit `08385e410d127247467c1c07cc01d12b66793efe` 的 `IMPLEMENTATION-LEDGER.md` 发起 `gh api --method GET`，真实返回 Blob `e9c17006cb41de12aaa6d9dd980656159831c485` 与 Git 树预期一致、正文含 S4 PASS 与 S5 NEXT；本机单次从请求到核真正文 **1837.34 ms**，已知 GitHub GET 计数 1、无业务写操作。该数字是 GitHub 读取探针耗时，**不是**完整 Global Controller / ChatGPT 的 time-to-first-valid-result，也不代替正式政策完整文件远端校验。
- 27 项新增 S5 安全/规模测试覆盖 N/重复次数边界、上下文最小加载、metadata 线性增长、合成分片局限、未选中依赖环/未知模块完整预检、S2 未授权卡/Source Lock 篡改、明确禁止网络/子进程/真实副作用以及返回状态的真实类型；继续保留 S2/S3/S4 既有拒绝与失败恢复测试。全量 **395 passed**，`validate-local VERIFIED`、`validate-candidate SCHEMA_PRECHECK_PASS`（approval_verified=false、registry_trusted=false）；Manifest 固定文件 49 项且原字节摘要重算。
- 阶段裁定：**S5 IMPLEMENTED_CANDIDATE / REVIEW_PENDING**。必须对准确新 HEAD GitHub CI 和独立设计复核再核对；证据边界以合成规模安全、候选本地计算与一次真实 GitHub R0 为止。不得冒称正式 plugin 容量/平均速度或模型 token 实测。
