# HANDOFF.md — G5 恢复与交接实施协议

适用条件：仅随经核实且显式采用的正式治理政策生效。规范依据 G0-FACT-05、G4-WRITE-02、G5-RESTORE-01；本文不另定义 A/B 审批门槛。

## H1 旧窗口可用时
仅在项目既有授权状态入口保存项目 ID、HEAD、原 writer、task/dispatch/thread/turn ID、结果引用、未清理资源、剩余许可和停止点；不建立第二业务账本，不导出全部聊天或敏感上下文。旧窗口不可用不阻止有依据的 R0 恢复，也不证明旧运行停止。

## H2 新窗口的真实恢复
1. **ROLE/POLICY**：实际读 Skill、来源锁与其已批准政策；按 CLIENT-CONTRACT.md 核外部 pin、Tag、完整固定文件/GENESIS。不凭 plugin 名称、GitHub AGENTS 存在或旧聊天宣称已加载。
2. **REGISTRY**：依据 REGISTRY-PROTOCOL.md 核当前目录完整性/审批链与一致 HEAD；列全登记范围，仅扫描当次有独立读取许可的项目。
3. **SOURCE**：每项目固定实时 HEAD，以同一 HEAD 读取 ledger/rules；合同用原冻结 Commit。核 Git mode 不能代替获取正文。读取前后相关 HEAD 漂移只重建一次，否则 HOLD。
4. **STATE**：实际读取权威账本当前区/明确事件链。提取 checkpoint、DECLARED NEXT、writer、关口、有效批准与阻断。并列当前区或覆盖关系不明为 LEDGER_CURRENT_CONFLICT，不投票选择、不用 Issue/旧快照替代。
5. **RUNTIME**：按确切 ID 用不恢复执行上下文的接口核现存任务。分页/存储域/连接不足为 UNKNOWN；不得因空列表新建或重发任务。
6. **REPORT**：分别报告来源、状态、运行态和 INFERRED 优先建议。单项目权限/资料问题局部 BLOCKED，其它独立 R0 可继续；治理信任根冲突阻断本次全局可信恢复。

## H3 读时账本适配
current_header：同一 HEAD 的显式当前区及 overrides 优先；旧 D 编号只作历史。append_events：仅按原生序列/父系与明确替代关系归并，不能只按 modified_at；同键不同载荷为 EVENT_CONFLICT。receipt_json：检查 scope/synthetic/input-output SHA/decision/stop_state，保存未覆盖项。issue_pr：补充依赖而非覆盖 ledger，除非 ledger 明确对该字段作了委托。

## H4 四种状态分别报告
- SOURCE_VERIFIED：列明来源和文件字节/版本已取得。
- STATE_RESTORED：账本内容被实际读取且关键字段可解释；缺项可 STATE_PARTIAL。
- RUNTIME_VERIFIED 或 RUNTIME_UNKNOWN：仅对本次查询范围成立。
- INFERRED_RECOMMENDATION：有证据的建议，不是 DECLARED NEXT 或执行授权。

简明回执保留 policy Commit、registry HEAD、project HEAD、ledger blob、事实字段来源、runtime status、blockers、next_allowed_action。这里只读派生，不回写项目账本。历史批准核实不能填入当前 execution_authorized=true。

## H5 两种交接
R0 恢复是默认行为，不变 writer。写口交接须用户明确原负责人→新负责人、项目范围、旧任务处置和账本入口；核旧进程/资源停止或隔离证据，按原 writer/CAS 规则完成受控交接并读回后才获得批准范围的写入能力。旧 writer 失联不允许抢写；无法排除冲突仅观测。

## H6 恢复与停止
thread/list、thread/read 是经实际工具核准后可用的只读候选；thread/resume、thread/start、turn/start 不是 R0 探针。相同 dispatch_id 只读旧 INTENT/结果；不同载荷冲突、INTENT 未读回、HEAD 变动、授权不明均停止对应派工。用户取消时只做既有明确授权的安全收尾；存档失败只补存档，不重复业务副作用。

## H7 默认启动
“启动全局治理，实际加载当前已采用政策，发现全部登记且获准读取的项目，恢复各项目权威状态并建议下一安全动作。”不得把用户指定项目 ID 设为全局启动前置；定向问题可以缩小读取范围，但不宣称全局覆盖。
