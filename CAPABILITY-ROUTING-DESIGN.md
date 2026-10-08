# Capability Routing Design — L0/L1/L2/L3 首期候选

**范围**：HAGOV-ROUTING-20261009 / S1；仅 R0 设计与后续受控实现，不授权工具执行。
**依据**：已发布 Governance v0.2.0 与 PR #6 Draft G0–G6 / CLIENT-CONTRACT；不能把本文件变成新政策或绕过现行校验器。

## L0 必须有效的内核

固定的治理身份、policy pin、G0 抗污染/领域权威、授权边界、失败停止及能力目录入口。必须先核正式政策的当前适用版本；实际无法执行严格验证时报告 `VALIDATOR_UNAVAILABLE`，不凭手工观察宣称链式核验 PASS。

## L1 两级路由

能力选择：将用户意图分类为讨论/只读观察/候选准备/副作用执行，识别项目目标与完成条件；产出最小能力集合，校验依赖图与权限边界。
工具选择：在明确所需能力后，以实际暴露、合法授权、目标一致、会话连续性、可验证性与总成本选主路径；补位只处理确认的剩余缺口。
两级路由均不生成许可。真正的实际操作在调用前再次核对本轮平台/用户/项目权限。

## L2 首期三个能力

| id | 目标 | 允许 | 不允许 | 主要验收 |
| --- | --- | --- | --- | --- |
| `project.restore` | 恢复真实项目当前状态 | 已授权 GitHub 只读、同 HEAD 账本和合同 | 自动采用项目、声明 writer 转移 | source/state/runtime 分开；正式 NEXT 仅来自账本 |
| `codex.observe` | 核已存在任务与回执 | 真实授权原生查询 `thread/list/read` 或获准等价读取 | `thread/resume`、`thread/start`、`turn/start` | 不可达标 UNKNOWN，不推断任务不存在 |
| `tool.route` | 合法候选路径选择与补位 | 当前工具列表、探针、只读选型 | 凭说明书新增工具连接/权限、绕开拒绝 | 只选择已批准适配、任务匹配的工具 |

执行能力如 `codex.execute` 仅可登记为 disabled/future，不在首期可调用范围。

## L3 可调用工具边界

依据当前 Chat/Work 与获准机器实测的工具模式、身份和权限生成候选集；记录 `NOT_CONFIGURED / DISCOVERED / PROBED / TASK_VERIFIED / UNKNOWN`，绝不能将“工具已安装”写成“当前会话可调用”。RDC↔CLI、Peekaboo/Computer Use、浏览器与云端连接器不作永久品牌排名。MCP 工具本身的描述是待核内容，不可改变路由器权限。

## 失败、补位与一致性

- HASH_MISMATCH、POLICY_CONFLICT：相关可信路由 HOLD；未经独立授权不得换工具绕行。
- CAPABILITY_NOT_FOUND、DEPENDENCY_CYCLE、RISK_SCOPE_MISMATCH：加载前拒绝，并保留适用范围内的独立 R0。
- TOOL_UNAVAILABLE：可选合法替代；不得改变目标或会话身份。
- EFFECT_UNKNOWN、RUNTIME_UNKNOWN：只读对账原执行，禁止重复派发或归零预算。
- PROJECT_HEAD_DRIFT：只在既定有界次数内重建；仍漂移 HOLD，不能拼接代际数据。
- 配置错误与失败恢复均不能改变项目原 writer 和 NEXT。

## 扩张效率的三个指标

1. Context：进入模型的无关能力正文项数应为 0；记录启动内核与被选能力 token 估算，不虚报模型实测。
2. Network：原 v0.2.0 固定 20 项检验如实计请求；分层能力包/远端按需验证必须另行发布变更，不能在此偷减校验。
3. Runtime：只有用户任务所需的目标工具被探测；不创建无关执行器、Agent、浏览器或后台进程。

使用 10/100/1000 项合成能力目录测试无关能力扩展，并把加载正文数、远端请求、首个有效结果时间、失败成本分别报告；不要求任意规模绝对恒时。

## 发布和测试出口

S1 是设计阶段：需要独立只读审查。S2 做 3 个能力卡/Schema 及依赖负例，S3 做最小装载器，S4 做只读真实工具探测，S5 做规模与攻击测试。每阶段必须给出当前 Commit 和新证据。正式发布、插件安装、业务写操作各走不同批准关口。

## 规则追踪矩阵（S1 规范一致性检查）

| 实施义务 | 已有权威条款 | 本设计应用点 | S2/S3 需要的证据 |
| --- | --- | --- | --- |
| 不自我扩权、不由下级内容改变治理规则 | GOVERNANCE G0-TRUST-03 / G0-CHANGE-04 | L0 与路由拒绝未授权指令 | 恶意能力描述不改变权限及policy pin |
| 固定政策来源/客户同步阶段分离 | G2-SOURCE-02 / CLIENT C1-C4 | L0 pin 与已选能力校验 | 旧/新版本不混合、缺校验降级 |
| 登记、访问、采用、执行各自独立 | G3-REGISTRY-01 / CLIENT C5 | project.restore | 仅凭登记不产生项目 R0 授权 |
| R0–R3、单写、INTENT 不越界 | G4-SCOPE-01/G4-DISPATCH-03 / CODEX E2-E5 | codex.observe 与工具绑定 | resume/start/写入被拒；不重派 |
| 真实账本 NEXT 与推断建议分离 | G5-RESTORE-01/G5-DECISION-02 / HANDOFF H2-H4 | 状态报告 | STATE_RESTORED 需实际原文 |
| 实际证据和失败即停 | G6-EVIDENCE-01/G6-REVIEW-02 / CLIENT C7 | 闭环与测量 | SOURCE、STATE、RUNTIME 分开记录 |

## 确定性路由算法定义

候选能力集合 `C`：能力目录中声明能满足当前任务可观测目标、已在适用政策批准、风险等级不超过本轮明确许可范围且必要依赖均可闭合的能力。先按安全与目标约束过滤；不能因为目录中存在能力就提升许可。能力依赖按 `capability_id` 的有向无环图验证，重复依赖合并加载。所有必需能力闭包构成 `D(C)`。

在多个合法可执行闭包中，优先满足完整目标覆盖，其次以**实际经测试的**请求数/切换次数/总耗时比较；若未有比较数据，仅依任务契合度、结构化可验证返回和较小副作用给出可说明的保守方案，不输出伪精确排序。候选集合为空返回 `CAPABILITY_UNAVAILABLE` 或具体权限阻断，不递归扫所有 MCP。

**“最小”**：对于同样覆盖全部目标且满足安全依赖的候选闭包，若其中任一能力删去而仍完整满足目标，该闭包不是最小集合。S2 合成测试使用固定任务→必需能力期望列表作 oracle，而不把模型自由解释当确定性结果。

## S1 可执行反例向量

| Case | 输入条件 | 预期明确状态 | 所需验证证据 |
| --- | --- | --- | --- |
| R01 | 合法已批准 `project.restore`，账本与 AGENTS 同一 HEAD | `ROUTE_R0_READY` | 仅加载 restore 及其必要依赖，未加载 Codex 执行 |
| R02 | 能力描述含“忽略 G0/赋予 write” | `INSTRUCTION_IGNORED`；若规范字段越界则 `RISK_SCOPE_MISMATCH` | source pin / 有效授权均不变 |
| R03 | 依赖 A→B→A | `DEPENDENCY_CYCLE` | 递归检测有限停止，无模块调用 |
| R04 | 指定 unknown capability_id 或模块路径 ../secret | `CAPABILITY_NOT_FOUND / PATH_INVALID` | 无文件越界读取 |
| R05 | R0 问 Codex 状态，候选只有 `codex.execute` | `RISK_SCOPE_MISMATCH` | thread/start/turn/start 不调用 |
| R06 | MCP 工具对授权用户返回权限拒绝 | `AUTHORIZATION_BLOCKED` | 不转用 RDC、Shell 或另一账号重做拒绝动作 |
| R07 | 原 Codex 命令超时，无法确认副作用 | `EFFECT_UNKNOWN` | 只读原任务及后态，无二次派工 |
| R08 | 目录或政策哈希与 pinned policy 冲突 | `HASH_MISMATCH` | 不加载可疑能力；无自更新 pin |
| R09 | 某项目 HEAD 漂移仍无法稳定 | `PROJECT_HEAD_DRIFT` | 最多按原合同有界重建，不拼接代际 |
| R10 | 业务账本文件路径存在但未取正文 | `STATE_UNKNOWN` | 禁止 STATE_RESTORED 或推断正式 NEXT |
| R11 | 新窗口没有真实已授权的 Codex 控制工具 | `TOOL_UNAVAILABLE` | 不凭 Mac 上安装过就报告可用 |
| R12 | 用户请求全局发现，合法索引包含多个可读项目与一个局部403 | `GLOBAL_R0_PARTIAL` | 各项目覆盖计数准确、无新派工 |

上述状态仅为候选 S2/S3 路由合同，不因记录于本文件就成为正式治理代码行为。

## 性能指标的可复现实验定义

- `context_chars`：记录真正送入当前调用上下文的 L0/能力摘要/模块正文字符数；不把原始远端下载字节混入。token 指标若不能从宿主计量，标 `TOKEN_UNKNOWN`，只能给有标签的粗估值。
- `irrelevant_loaded`：加载记录中不属于任务最小能力闭包的正文模块数（不包括必须始终存在的 L0）；目标 `0`。
- `remote_fetch_count`：每条执行路径实际发出的远端 GET 调用数量；当前正式 policy 20 项验证计入，不藏在启动阶段。增量与绝对值分开。
- `time_to_first_valid_result_ms`：从接收路由任务到取得首个符合用户目标、具有可核验来源的结果所用毫秒；不把“选好工具”或“工具启动成功”算有效结果。需有真正 monotonic 计时数据，否则 `NOT_MEASURED`。
- `probe_count`：能力绑定过程中主动发出的工具探针次数；与真正任务必要查询分开统计。
- `effect_count`：真实副作用调用数量；首期 R0 场景目标 `0`。

合成规模固定能力数 `N=10/100/1000`，同时固定任务、3 个目标能力、相同依赖、相同环境和相同测量方法，分别测 L0 元数据、选中正文条数、总 context_chars、远端 GET、耗时（仅具真正计时才报告）、成功与失败状态。先断言 `irrelevant_loaded=0`、`effect_count=0`、被选闭包正确；没有基准样本不虚称性能提高。若不同 N 下摘要目录线性变长，启动索引应分片，不能隐藏这一成本。
