# S4 Scenario Planning Contract — 候选协议

状态：**candidate only / PLAN_ONLY / 未发布**。`capabilities.scenarios.plan_scenario` 只在调用方提供独立 catalog 原始 SHA256 pin 后，调用 S3 `route_capability` 核选中目录链，再返回惰性数据计划。它不验证完整政策、不恢复业务状态，也没有执行器。

## 输入合同

只接受 `global_restore`、`project_restore`、`codex_observe`、`tool_select`。每种上下文都是封闭白名单的普通 Python `dict`；未知字段、非普通容器、非规范标识、缺字段和非 R0 效果均拒绝。`untrusted_text` 只记录“存在但不参与控制”，不能改变政策、授权、风险、阶段、能力或输出常量。

- global_restore 不要求项目 ID：必须规划全部已登记且本轮获准读取项目的清单与覆盖统计、逐项目同一 HEAD 的账本恢复、必要的既有运行态只读核对。单项目无法读取只标局部 PARTIAL/HOLD，不得把只查首项冒充全量；本模块不实际读取。
- `project_restore` 要求准确 `project_id`，依次规划政策、索引条目、项目 HEAD、同 HEAD 账本及分层报告。
- `codex_observe` 要求已存在的准确 task/thread 标识，只规划 `thread/list` 和 `thread/read`；不规划 resume/start/turn/start。
- `tool_select` 要求准确目标引用、目标语义、匹配的候选能力和封闭的合成候选观测。输出不含 shell、URL 或自动调用字段。

## 固定无权输出

成功、HOLD 或 AMBIGUOUS 回执均保持 `status: PLAN_ONLY`、`authority_effect: NONE`、`dispatch: false`、`writer: false`、`policy_verified: false`、`business_state_restored: false`、`runtime_tool_permission_required: true`。目录局部链通过只表示 `CATALOG_CHAIN_ONLY_NOT_POLICY_VERIFIED`；运行时仍须重新核工具存在性、当前许可、目标和副作用。

## 工具比较

候选资料始终标记 `CALLER_SUPPLIED_UNVERIFIED`，不得据此报告真实 MCP 健康、安装或授权。先排除目标/会话/能力不匹配、权限不合格、范围不符、有副作用或效果未知、工具类型未知、目标不连续和结果不可验证的候选；随后只按目标连续性、精确范围覆盖和可验证性形成建议，不设品牌排行榜或数字速度评分。多个同等候选保持 `AMBIGUOUS` 并列出候选，不强选。

替代/补位只有在先前尝试目标完全相同且 `side_effect_status: NONE_VERIFIED` 时才继续比较；此前副作用存在或不可核一律 `HOLD`。任何建议仍需独立运行时许可关口，本模块不会探测或安装 MCP、启动进程、联网、写文件、建线程、派任务或执行调用。
