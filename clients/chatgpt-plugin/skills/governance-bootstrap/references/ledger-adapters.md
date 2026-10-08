# 账本读时适配：原有方法保留、结果分层

不修改业务账本，不建立新永久业务数据库。所有事实包含source URL、project HEAD、blob及本次范围。
current_header：同一HEAD中显式“当前唯一执行入口”及overrides确定当前区，旧D/Issue不覆盖。两个现行入口不明则LEDGER_CURRENT_CONFLICT，禁止猜选。
append_events：同一权威对象按event sequence/父系/显式替代归并；不能只按modified_at；同键不同payload为EVENT_CONFLICT。新事件只覆盖自身字段，未覆盖保留UNKNOWN，批准/执行/验收/存档分别记录。
receipt_json：核schema、scope、synthetic、input/output Commit、decision、stop_state、cleanup和未覆盖项目。合成PASS只能证明合成输入；RESULT_RECORDED≠BUSINESS_ACCEPTED。未知状态不触发重做副作用。
issue_pr：任务依赖和历史线索，不覆盖ledger；只有ledger明确委托该字段时才按准确范围视为权威。
输出checkpoint、DECLARED NEXT、writer、gates、approval、blockers的引用与解释。拿到路径/blob但没读正文只SOURCE_VERIFIED；关键字段完整且无歧义才STATE_RESTORED，否则STATE_PARTIAL/UNKNOWN。依据这些事实生成的治理排序仅INFERRED，不写回为执行令。
