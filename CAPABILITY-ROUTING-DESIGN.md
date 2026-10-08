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
