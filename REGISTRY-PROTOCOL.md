# REGISTRY-PROTOCOL.md — G2/G3 受控发现与审批实施

v0.2.2 候选；v0.2.1 已正式发布且来源固定，v0.2.2 仅增强仓库版本管理，生效条件见 G2-RELEASE-01。本协议是目录及 A/B 规则的唯一规范出处，不自动授予共享写入或项目访问。历史语义变更见 RULE-MAP.md；未发布前运行端仍使用自己的已批准旧policy。

## R1 三轨来源与初始化
固定政策：外部 exact Commit pin → annotated Tag 解引用 → 完整 Manifest 文件集合及逐项原始 SHA256 → 当前运行 validator/Schema/GENESIS 比对。三个公开 pre-merge/post-merge/audit-chain 与 audit-main 都要求独立 pin；先固定传入对象的副本，caller 后改 A/B 不生效。候选 v0.2.1 Tag 缺失必须 HOLD；不移动 v0.2.0 Tag、不自动采用新代码。
动态目录：main/projects.yaml 从正式 genesis 起验证连续 first-parent；初始原始字节由 GENESIS.initial_index_sha256 绑定，Manifest 不含以后会变化的索引。业务事实：项目实时HEAD账本、原冻结合同、原生运行证据；不复制到目录。
GENESIS 固定仓库、owner、release_tag、初始身份集、branch/path、approval mode。当前候选以未变化的原目录作为初始快照，发布前若 main/目录已变，须重新对账和审查，不能重置登记历史来漏项目。加载器可识别旧格式供测试/迁移，但正式执行还必须匹配外部政策pin及所有字节，不能用候选代码替代旧正式代码。

## R2 严格输入和身份
UTF-8 严格解析，拒绝 BOM、控制字符、重复键、非字符串键、alias/anchor/custom tag/directive/merge key、超大/超深输入及未知字段。仓库只取明确 owner/repo；路径为非敏感POSIX相对文档路径，拒绝绝对/..、通配、URL/鉴权查询、home/profile/cache/log/secret/token等材料。分支及每个Git树层级实际验证；symlink/submodule/非正规blob、截断或缺失不能通过。路径可读不等于用户授予访问权。
Schema 固定 discovery_only、reference_only、dispatch_enabled:false、writer_source:current_project_ledger_only。项目ID/仓库/身份摘要不能改用途；暂停/退役保留墓碑、身份、前序索引Commit与时间、追加历史；恢复同身份只能追加事件。新身份需要独立受控登记和现行R0访问许可。

## R3 普通登记 PR 的共同门禁
所有共享变更都须用户准确范围授权；本协议不自行发布。PR必须仅包含原有 projects.yaml 的 status=modified 且无 previous_filename，拒绝 rename/copy/add/其它路径。核候选HEAD、前序base、原始index SHA256、规范化语义diff SHA256、changed IDs；空变化拒绝。合并前不得预知merge SHA。policy bootstrap 是多文件发布，必须遵守先前有效的发布规则，不能由自身新B流程批准。

## R4 模式 A：EXTERNAL_GITHUB_REVIEW
正式GENESIS明确选择A时，独立于owner与PR作者的真实GitHub reviewer，在准确HEAD上最新有效APPROVED须早于owner批准；同一reviewer的更新状态/撤销不能被旧APPROVED掩盖。Owner评论要求相同对象/diff/范围，真实ID，created_at=updated_at，严格 review < owner < merge。独立AI会话不能冒充第二GitHub身份。A不可用时HOLD，不自动降级。

## R5 模式 B：SINGLE_OWNER_AI_R0_ATTESTED
正式GENESIS明确选择B时，独立AI先做R0设计审查，由owner账号发布证明；使用**最新准确HEAD**的GitHub Actions validate：原生check ID/name/head/status=completed/conclusion=success/app.slug=github-actions/关联PR均匹配。CI完成早于AI证明；owner另发批准评论，全文精确绑定AI评论ID及UTF-8原文SHA256。owner不得用旧批准覆盖最新不合格/否决证明。
两个不同ID的评论必须owner账号归属，服务器时间合法且created_at=updated_at，CI < AI证明 < owner批准 < merge；摘要至少10字、不含换行，source/session字段合法但不是独立作者证明。原始回执缺失、编辑、head/diff不同、范围越权、过期CI均HOLD，不从YAML自述或caller boolean推断权限。

AI原生PR评论模板（实际独立审查后才生成，模板不是证据）：
```text
HAGOV-AI-R0-ATTESTATION-V1
candidate_head=<40hex>
previous_index_commit=<40hex>
index_sha256=<64hex>
normalized_diff_sha256=<64hex>
changed_ids=<sorted-comma-separated-ids>
review_scope=DISCOVERY_METADATA_ONLY
decision=APPROVE_DESIGN
assurance_level=OWNER_POSTED_AI_R0_NOT_GITHUB_REVIEW
open_blockers=0
review_engine=<engine>
review_session_ref=<reference>
summary=<10-to-500-chars>
ci_check_run_id=<native-id>
```
Owner另一次批准模板（A模式不含B专属profile、AI引用、CI及effect字段；其共同字段仍须准确）：
```text
HAGOV-REGISTRY-OWNER-APPROVAL-V1
candidate_head=<40hex>
previous_index_commit=<40hex>
index_sha256=<64hex>
normalized_diff_sha256=<64hex>
changed_ids=<sorted-comma-separated-ids>
authorized_action=APPROVE_DISCOVERY_REGISTRY_UPDATE
approval_scope=GOVERNANCE_REGISTRY_ONLY
approval_profile=SINGLE_OWNER_AI_R0_ATTESTED
ai_review_comment_id=<native-id>
ai_review_comment_sha256=<64hex>
ci_check_run_id=<native-id>
project_authority_effect=NONE
```
B仅证明GitHub记载owner账号发布的证明和CI；不证明第二GitHub actor、AI密码学独立性或真人亲手发布。仍需真实独立AI过程与人类明确批准，保证等级低于A且不是平台分支保护；不能抵抗有owner凭据的恶意进程。

## R6 历史合法性与当前健康分离（v0.2.1 的显式语义变更）
**合并前**继续要求当前最新准确HEAD CI成功、最新适用Review/AI/owner证据；缺字段或新失败拒绝，绝不靠“历史PASS”授权合并。
**合并后**从真实merge Commit取得first parent和merged_at，以真实合并时间为历史截点。只使用创建/提交时间严格早于该截点的Review和两份评论；原证据被编辑、删除、原CI不再能证明成功或时序不足仍HOLD。之后的新评论不是合并前批准，也不会凭空取消已证历史。
历史CI：按明确绑定的check ID核原完成结果，并取同HEAD完整有界 filter=all 列表，确认该检查是合并前已经存在的最新合格检查；已在合并前开始的较新失败/未完成检查阻断。明确在合并后开始的新run，不倒写为当时未批准。只有完成时间、无法证明开始时点的跨截点run或历史分页无法完整取得为HOLD，不猜测。当前实现单次历史列表上限100，超限明确AI_B_CI_HISTORY_UNAVAILABLE，不宣称完整历史。
后验报告标 verification_scope:HISTORICAL_APPROVAL_ONLY、current_health:NOT_EVALUATED、current_execution_authorized:false。后来风险/撤销可以阻断新的操作，但需按当前权限和风险另行判断；历史通过不等于当前可执行。现在的元数据不足以还原当时事实时应报告证据不足，不能从未来状态推造历史签名。

## R7 连续链与实际合并
POST_MERGE 独立GET实际merge Commit、first parent、merged_at、原始index；PR base.sha合并后可能移动，不能代替历史parent。candidate原始index与merge字节必须一致。由正式genesis到当前main的每次index变化必须有唯一实际merged PR和对应历史证据；非索引提交不得伪装批准来源，链断裂/无genesis祖先/超出边界HOLD。

## R8 读取与报告
先固定外部policy pin并核完整固定文件，再固定目录H1和完整链；scan_authorized_main在同一次操作内，按独立已授权ID检查项目，逐项读前/读后与结果返回前重查main HEAD。不得返回可复用scan token。初始化只重建一次，仍漂移HOLD；局部项目源失效可报告PARTIAL/BLOCKED，其它已准项目继续，不能合计成全局PASS。
三维lifecycle(active/paused/retired)、registration(verified/unverified)、read(VERIFIED/PARTIAL/BLOCKED/NOT_ATTEMPTED)分别合计total。路径/blob验证只是SOURCE_VERIFIED，NEXT实际正文解释在HANDOFF及客户端完成；未解释保持UNKNOWN_NOT_PARSED_BY_REGISTRY。索引报告dispatch_authorized:false、writer_change_authorized:false。

## R9 本地与正式执行
validate-local仅核初始GENESIS/本地Manifest；validate-candidate是Schema预检且registry_trusted:false/approval_verified:false，不赋权。真实审计必须使用对应正式发布代码与外部--expected-policy-commit，授权GitHub GET；无工具/权限/证据HOLD，不创建登录或调用thread/resume探测。reviewer-readiness是诊断，不是授权。动态登记、policy bootstrap、插件采用与业务采用分别验收。
