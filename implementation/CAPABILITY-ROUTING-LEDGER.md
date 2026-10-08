# Global Controller Capability Routing · 分阶段实施与对账账本

**身份**：HAGOV-ROUTING-ROLL0UT-V1，治理仓库内部工程实施记录（candidate only）。本账本**不是**各业务项目的权威账本、不授予部署/项目写权/派工/用户发布批准，也不替换原 Governance 政策。目录与路由代码的正式效力须另经候选审查、用户明确批准、Tag、客户端显式采用和真实运行验收。

## 0. 固定基线与隔离

- 唯一工程对象：`ludefeiqi/human-ai-governance` 的候选设计、离线代码、测试及文档。
- 已发布政策：`v0.2.0`，Commit `7aced01a8c12e1bba5e810ce91ab425f4615d4a7`，**不得移动 Tag / 修改正式 main**。
- 上游依赖：Draft PR #6，Commit `43d9ce7df28d14148925c9fcc67623c06809a8af`（G0–G6 合理化候选，**尚未发布**）。
- 本实现应建独立分支，以 PR #6 HEAD 为父版本；在新候选上单一写入、分阶段提交并以 Git HEAD/CAS 复核。独立 reviewer 只能只读。
- 已安装插件：`human-ai-governance-bootstrap` v0.2.0，release `pluginrel_6ac761de71488191b66468d32bcbcaa3`；不在本工程阶段更新它的来源锁、安装或权限。
- 项目目录 `projects.yaml` 与仓库根 `AGENTS.md` 不修改；不接管 HOT、DOT/ROOT、Codex 在途任务或生产环境。
- 唯一最新工程 NEXT：**S4-CI-RECHECK — 核验三场景适配准确候选的真实 GitHub CI**。任何后续阶段必须按下表关口对账。
- 每次状态修改：先核候选分支实际远端 HEAD 与本地父系，单写提交、不强推；提交后重新 GET HEAD、文件差分与 CI。文档中的状态以**提交时可证明的事实**为准；PR 设计回执不代替用户授权。

## 1. 分阶段闭环

| 阶段 | 目标与最小范围 | 完成判据 / 证据 | 当前状态 | 后继 |
| --- | --- | --- | --- | --- |
| **S0 基线核对** | 核正式 Tag、PR #6、插件 release、根 AGENTS/作用域、既有测试基线 | 有精确 SHA、仓库/插件本轮实际读回，主分支未变 | **PASS**：见第0节 | S1 |
| **S1 立账本** | 在独立候选分支记录唯一 NEXT、范围、权限、步骤和回退 | 仓库候选提交及远端 HEAD 读回、准确账本原文 | **PASS**：远端提交 `71f11ca3067505a567187ec885d747e5928f82b0` 已验证；本地 HEAD/父提交复核为 `71f11ca…` / `43d9ce7…` | S2 |
| **S2 目录与合同** | `CAPABILITY-ROUTING.md`、可信能力目录、Schema、三项能力元数据；固定 0 写权 | Schema/依赖/来源绑定校验、未登记/异常输入拒绝、文档引用清晰 | **PASS**：远端提交 `7174c9235ab2e6e3c2724a4a1a42a38bbe5e7487` 已读回；本轮入口核对的本地 HEAD 精确相同且初始 worktree clean；见第5节 | S3 |
| **S3 安全加载器** | 确定性选择器、依赖有界展开、模块只读装载、来源哈希检查；不执行外部动作 | 单元与负例：路径/遍历/循环/未知能力/缺包/篡改一律拒绝；无授权产出 | **PASS（LOCAL + REMOTE_CI）**：已保留首次失败、修补提交 4792166577e6a3de718263a1360b26e27b020c39、GitHub 298/298 成功；见第7节 | S4 |
| **S4 三场景适配** | `project.restore`、`codex.observe`、`tool.route` 三个 R0 能力包，保留能力与工具两级选型 | 用户意图映射可复现；运行时只报告当次能力；不存在真实派工或写入 | **PASS（LOCAL）/ REMOTE_CI_PENDING**：17项场景测试、全套315项、53项Manifest通过；见第8节 | S5 |
| **S5 验收与性能** | 10/100/1000 合成规模，恶意输入、拒绝/降级/超时/UNKNOWN、状态一致性测试 | 记录目录读取次数、字节、所选正文数及耗时；无关能力规模扩大不引发正文全量加载；全 pytest、Manifest、diff 检查 | TODO | S6 |
| **S6 插件入口候选** | 更新**候选源码**的短入口/能力目录指引、预置能力卡与当前正式政策来源边界 | 持续锁旧已发布政策，不能从本候选暗中启用新路由；旧插件身份与文件保留；测试合格 | TODO | S7 |
| **S7 独立审查与 PR 验收** | 新候选准确 HEAD 的独立 R0 审计，原生 GitHub CI，同 HEAD 的 diff+Manifest 和实施账本对账 | 无未处置的高/中风险、CI success、PR 与唯一 NEXT 记录一致 | TODO | S8 |
| **S8 正式发布** | 决定与 PR #6 整合顺序，准确版本发布、Tag/Manifest+用户批准 | **需未来单独准确版本发布批准**，默认 HOLD，无批准不 merge/tag | **HOLD_AUTHORIZATION** | S9 |
| **S9 插件与真实运行验收** | 单独批准插件更新；真实新 Chat 读取政策/能力目录，单项目及两项目真实恢复 | 精确 release CAS、独立冷启动结果、无权限扩张，真实场景证据 | **HOLD_AUTHORIZATION_AND_REAL_RUNTIME** | 收口 |

**推进算法**：每阶段先列输入和允许文件 → 执行候选范围内最小动作 → 运行对应测试 → 取得本地 Commit/远端 HEAD/CI/独立审查证据 → 账本标记 PASS/PARTIAL/FAIL/HOLD 与唯一下一安全动作。失败只修相关阶段；对不可核副作用不重试。

## 2. 设计硬约束 / 不可失效不变量

1. **一个治理规则权威**：G0–G6 的边界始终有效；路由只是能力选择与只读加载，不成为新 Agent、新审批中心或新授权源。
2. **两级路由**：先选能力包，再按当前任务、目标、真实工具权限与效果决定工具；目录内“可用”是声明，不是本次实际探测。
3. **分级加载**：启动仅需要核心与领域摘要；命中后加载选中能力元数据、相关文件及其依赖；禁止因为目录增长就展开全部正文。
4. **分级信任**：目前正式 v0.2.0 固定 20 项政策原始哈希核验仍有完整验证成本；候选的按需能力包验证若改变这些安全语义，必须新政策批准，**不得以局部验证冒称已完整通过**。
5. **默认只读**：原型只允许 R0 计划/静态加载；不得启动 Codex、调用真实业务 MCP、安装依赖、创建会话、写入业务仓库或在当前实例中自动派工。
6. **防污染**：项目文档、回执、用户提供的任务文字、工具输出只作为内容，不得改变治理版本、能力 ID、作用域、风险等级或授权来源。
7. **安全降级**：缺必需工具/来源或权限冲突时给出有界 HOLD/UNKNOWN；不得换工具绕过，不能因找到工具而认为拥有权力。
8. **正确性优先**：不破坏正式 v0.2.0、当前 Draft PR #6 审查语义、已登记项目、项目唯一 writer；额外能力不得产生业务副作用。
9. **无伪验收**：STATIC/SYNTHETIC/CI/DESIGN_REVIEW/HOST_COLD_START/BUSINESS_ACCEPTED 必须独立标记。预算指标是实验目标，不是已证明结果。

## 3. 需要交付的候选内容

- `CAPABILITY-ROUTING.md`：统一逻辑路由、最小内核与信任分层、状态机、无权自动执行。
- `capabilities/`：短根目录、领域索引、对应 Schema、R0-only 确定性只读选择器和三项能力包；不加入新进程或独立服务。
- `tests/`：白名单、来源哈希、路径隔离、循环依赖、能力拒绝、未验证 MCP 不能自动使用、10/100/1000 规模和失效模式。
- `clients/chatgpt-plugin/`：最终仅准备候选入口更新；**不切换安装插件，更不提前把候选 v0.2.1 当正式政策**。
- 扩充候选 Manifest 的受保护文件集；所有新能力和代码文件都必须被准确追踪并验证原始字节。

## 4. 权限、版本与证据界限

- 当前用户批准：在治理仓库**隔离候选**里分步设计、实施、静态与合成验收、独立只读复核并提交 Draft PR。
- **没有获得**正式政策发布、当前插件安装、HOT/任何业务项目写入或 writer 交接、真实生产/认证操作的批准。
- 上游 PR #6 若改变 HEAD，停止集成假设，做有限差分对账；不自动更新本分支基线。
- S8/S9 保持 HOLD，即使 S2–S7 所有测试 PASS。新窗口不能凭本账本获得业务执行许可。

## 5. S2 本地实施证据（2026-10-09）

### 5.1 实际范围

- 新增候选协议 `CAPABILITY-ROUTING.md`，明确单一治理权威、最小 G0 内核、能力/工具两级路由、旧完整政策关口、失败停机、`UNKNOWN`、零副作用、预算和 S3 边界。
- 新增 Draft 2020-12 `capabilities/catalog.schema.json`、轻量根目录、`project`/`codex`/`tools` 三个领域清单，以及 `project.restore`/`codex.observe`/`tool.route` 三个 R0-only 可读能力说明。
- 逐级按原始字节绑定 SHA256：能力说明绑定到领域清单，领域清单绑定到根目录；引用路径均为精确仓库相对路径。
- 新增 `tests/test_capability_catalog.py`，覆盖 Schema 自检与封闭结构、候选目录身份、三个领域/能力/意图精确集合、领域与能力包原始 SHA256、R0/无副作用、路径不越界/非符号链接、无外部文件，以及单意图只需一个领域和一个能力包的静态加载合同。
- 仅扩充 `registry/validate_registry.py` 的 `OPTIMIZATION_POLICY_FILES` 和 `MANIFEST.sha256`；候选固定集合由 37 项增至 48 项。未修改 GENESIS、旧 Tag、A/B 审批逻辑、`projects.yaml`、注册/派工门禁、旧测试语义或 `clients/chatgpt-plugin/`。

### 5.2 已执行验证

1. `/private/tmp/hagov-p2-venv/bin/python -m pytest -q -p no:cacheprovider tests/test_capability_catalog.py` → `5 passed`。
2. `/private/tmp/hagov-p2-venv/bin/python -m pytest -q -p no:cacheprovider` → `269 passed`。
3. `/private/tmp/hagov-p2-venv/bin/python -m registry.validate_registry --root . validate-local` → `status=VERIFIED`、`phase=LOCAL_GENESIS`、`manifest_entries=48`、`dispatch_authorized=false`、`writer_change_authorized=false`。
4. `/private/tmp/hagov-p2-venv/bin/python -m registry.validate_registry --root . validate-candidate` → `status=SCHEMA_PRECHECK_PASS`、`phase=GENESIS_SCHEMA_PRECHECK`、`manifest_entries=48`、`approval_verified=false`、`registry_trusted=false`、`dispatch_authorized=false`、`writer_change_authorized=false`。
5. `git diff --check` → PASS（无输出，退出码 0）。

以上是 S2 提交前的本地证据；其候选提交 `7174c9235ab2e6e3c2724a4a1a42a38bbe5e7487` 后续已远端读回，本轮入口也核得本地 HEAD 精确相同。它仍不证明真实 Codex 任务、MCP、业务验收、正式发布、插件安装或客户端冷启动。

## 6. S3 本地实施证据（2026-10-09）

### 6.1 实际范围与固定接口

- 新增 `capabilities/router.py`，公开 `route_capability(root: Path, intent: str, expected_catalog_sha256: str, budgets: Mapping[str, int] | None = None) -> RouteResult` 和带稳定 `code`/`as_dict()` HOLD 回执的 `RouterError`；没有 CLI、网络、shell、文件写入、工具调用或执行入口。
- 输入只接受精确声明 intent 和独立传入的 64 位小写十六进制 catalog 原始字节 SHA256。加载顺序固定为 Schema、外部 pin 锚定的 root catalog、唯一命中 domain、选中能力及同 domain 依赖闭包；不会读取其它 domain 或能力正文。
- 返回结构固定包含 `status`、验证/权限布尔值、`intent`、`domain_id`、`selected_capability_id`、依赖优先的 `capability_ids`、`loaded_paths`、含所有已读原始字节的 `raw_bytes`、逐能力 `modules[{capability_id,path,sha256,module_text,requires,required_tools}]`、合并后的 `required_tools` 及其声明状态。
- 所有成功结果固定为 `verification_level: CATALOG_CHAIN_ONLY_NOT_POLICY_VERIFIED`、`policy_verified:false`、`authority_effect:NONE`、`dispatch_authorized:false`、`writer_change_authorized:false`、`tools_checked:false`、`candidate_only:true`；工具需求仅为 `DECLARED_ONLY_NOT_CHECKED`。
- 路径限定为三段式 `capabilities/domains/*.json` 或 `capabilities/packs/*.md` 的 canonical POSIX 相对路径，逐级拒绝 symlink、目录、缺失、越界、反斜线和非法扩展。原始字节在 SHA256 前后均受限；硬上限为 Schema/root 各 16 KiB、domain 32 KiB、单 pack 24 KiB、总量 80 KiB、依赖 8、深度 8，调用方只能收紧不能放宽。
- 新增 `tests/test_capability_loader.py` 的 24 项测试，覆盖四种成功 intent、未命中、pin 缺失/错误、domain/pack 篡改、重复身份/意图、遍历与非 POSIX 路径、逐级 symlink、单项/总量超限、循环/未知/跨域依赖、依赖计数、R2/副作用拒绝，以及精确只读所需四文件并禁止 socket/subprocess 行为。
- 固定政策文件集合从 48 项增至 50 项，加入加载器和新测试；`MANIFEST.sha256` 对整个既有固定集合保留并更新受影响文件真实原始 SHA。未新增 `capabilities/__init__.py`，Python namespace package 已足够公开该模块。

### 6.2 已执行验证

1. `PYTHONDONTWRITEBYTECODE=1 /private/tmp/hagov-p2-venv/bin/python -m pytest -q -p no:cacheprovider tests/test_capability_loader.py` → 首轮因测试断言自身二次读取被追踪 pack 而为 `4 failed, 20 passed`；修正为先缓存预期 SHA/正文后重跑 → `24 passed in 1.31s`。失败没有被隐藏，也未改变加载器安全边界。
2. `PYTHONDONTWRITEBYTECODE=1 /private/tmp/hagov-p2-venv/bin/python -m pytest -q -p no:cacheprovider` → `293 passed in 11.13s`。
3. `PYTHONDONTWRITEBYTECODE=1 /private/tmp/hagov-p2-venv/bin/python -m registry.validate_registry --root . validate-local` → `status=VERIFIED`、`phase=LOCAL_GENESIS`、`manifest_entries=50`、`dispatch_authorized=false`、`writer_change_authorized=false`。
4. `PYTHONDONTWRITEBYTECODE=1 /private/tmp/hagov-p2-venv/bin/python -m registry.validate_registry --root . validate-candidate` → `status=SCHEMA_PRECHECK_PASS`、`phase=GENESIS_SCHEMA_PRECHECK`、`manifest_entries=50`、`approval_verified=false`、`registry_trusted=false`、`dispatch_authorized=false`、`writer_change_authorized=false`。
5. `git diff --check` → PASS（无输出，退出码 0）。
6. `git diff --exit-code HEAD -- AGENTS.md projects.yaml registry/GENESIS.json CLIENT-CONTRACT.md clients releases drafts` → PASS（无输出，退出码 0）；根 AGENTS、项目索引、GENESIS、CLIENT 合同/元数据、已发布版本和历史草案均未改变。
7. 验证底座为指定 venv 的 Python `3.14.7`；测试前磁盘可用约 `88 GiB`。沙箱拒绝 `sysctl -n hw.memsize`，故物理内存数值为 `UNKNOWN`；新增套件约 1.3 秒、全套约 11 秒，未观察到资源失败。

### 6.3 未覆盖与停止边界

本地 PASS 只覆盖静态候选代码、合成 `tmp_path` 文件和本地完整固定集合。没有执行网络、真实外部 MCP、Codex 业务任务、业务仓库读写、插件安装、Git commit/push/PR、远端 CI、独立外审、正式 main/Tag、客户端冷启动或业务验收；未验证项不得从本地链验证推导。S4–S9 未提前标 PASS，S8/S9 继续 HOLD。本轮在 S3 完成和本地证据读回后停止，不自动开始 S4。

## 7. S3 远端 CI 差异与精确纠正（2026-10-09）

- 原 S3 Commit：4f0874be27a71a2a6588da595516e5c2d9a469ed，已远端读回。
- 实际 GitHub Actions 37809698471 / check 113423035540：297 passed、1 failed。失败项 tests/test_capability_catalog.py::test_references_stay_inside_the_static_capability_file_set 将正常生成的 capabilities/__pycache__/router.cpython-312.pyc 当作额外政策源码；本地此前用 PYTHONDONTWRITEBYTECODE=1 掩盖了差异。
- 已停止 S4 施工；局部未提交 S4 候选源码封存于本机隔离 git stash；不触发业务副作用。
- 最小修补：依 RELEASE_POLICY_FILESET 比对能力目录中的源码集合，只忽略 __pycache__ 下自动生成的 Python 缓存；未登记源码文件仍应阻断。
- 再验要求：不禁用 Python 字节码，完整 pytest/Manifest/保护文件核验，推送准确修补 Commit，核 GitHub 新 CI success。远端原失败回执不抹除。
- 当前状态 REMOTE_CI_PASS（仅本工程 S3）。纠正提交 4792166577e6a3de718263a1360b26e27b020c39 经 GitHub Actions 37810535389 / check 113425927102 真实读回 completed/success，原生日志 298 passed in 4.58s；候选预检 SCHEMA_PRECHECK_PASS、registry_trusted=false、dispatch_authorized=false。已经满足 S3 到 S4 的候选阶段转移，不涉及正式 Tag、插件安装、项目或生产许可。

## 8. S4 本地场景验收（2026-10-09）

- 前置 S3：GitHub CI 原始失败297/298，精确修补4792166577e6a3de718263a1360b26e27b020c39 后新CI 37810535389 / check 113425927102 实际298/298 success；S3关闭账本提交 159cce26c53eb6d4d2afa11ba06e08c299355eba 已远端读回。
- 本轮新增 capabilities/scenarios.py、capabilities/SCENARIO-CONTRACT.md、tests/test_capability_scenarios.py；只改候选固定文件集与Manifest，不更改G0宪章、GENESIS、projects.yaml、AGENTS或已安装插件。
- 四种任务：global_restore（已登记且获准的完整项目覆盖，逐项目HEAD/账本与必要运行态计划）、project_restore（单项目精确ID）、codex_observe（仅既有ID、规划thread/list/read而无start/resume）、tool_select（目标/会话/风险约束，调用方候选资料绝不代替实际探测）。
- 无工具调用、无网络、无进程或副作用；所有结果PLAN_ONLY、policy_verified=false、authority_effect=NONE、dispatch=false、writer=false；同分候选保持AMBIGUOUS，不设品牌固定排行。补位只有此前目标相同且经调用方声明无副作用时仅作为计划，不授予执行权。
- S4专项：17 passed；整套269+29+17=315 passed（Python默认字节码路径）；validate-local VERIFIED、validate-candidate SCHEMA_PRECHECK_PASS、53项候选Manifest，registry_trusted=false且无dispatch/writer权。
- 本轮仅本地验证，真实GitHub CI须在S4实际提交后再检查；不能把专项测试当真实MCP运行、Codex业务执行或正式全局恢复。
