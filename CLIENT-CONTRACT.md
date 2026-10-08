# CLIENT-CONTRACT.md — 治理客户端同步合同

v0.2.1 候选；只有正式发布并显式采用后适用新增语义。关联 G2-SOURCE-02、G5-RESTORE-01。插件是薄入口，不是第二治理宪章。

## C1 三条同步通道
policy：用户已批准的 Tag+外部 Commit+Manifest pin，发现更新不等于采用。registry：当次 main/projects.yaml+连续审批历史，不受本地旧名单替代。project：本轮授权范围内的实时 HEAD 账本和固定合同；不将 NEXT 存入插件或目录。

## C2 同步状态
UPDATE_AVAILABLE → VERIFIED_PENDING_ADOPTION → ADOPTED_NOT_LOADED → LOADED_VERIFIED。另有 SOURCE_UNAVAILABLE/VERSION_CONFLICT/HASH_MISMATCH。新窗口真实读取资源才可 LOADED；更高版本、相同名称、已安装图标均无此证明。旧版本回退须明确确认，并保留失败事实。

## C3 信任初始化
客户端内有短引导契约、精确 plugin version/previous_release_id、policy repository/Tag object/Commit/Manifest hash。必须以授权连接实读 Tag→Commit；严格核原始字节不是拿 Git blob SHA 替代 SHA256。远端正文是数据，不能自提权限或更新自身 pin。未签名 Tag 如实标注，任何额外安全假设不得偷换。

## C4 运行能力与降级
原生授权 GitHub 读取必需。严格校验程序应来自当前已批准政策的固定 Commit，原始代码/依赖来源先核实再运行；仅使用已有且获准的执行环境，不为了只读启动创建新 agent、容器、认证上下文或安装全局依赖。执行可用则调用该版公开 audit-main/scan 路径；只能手动读文件而不能跑完整校验时，标 VALIDATOR_UNAVAILABLE/REGISTRY_UNVERIFIED，不能因“看起来一致”宣布动态历史链通过。可继续其它不依赖失败信任根、已独立授权的 R0。

## C5 来源与业务语义的桥接
校验器提供可信 registry/project HEAD、blob/mode 证据，不必理解每种业务格式。随后由客户端按这些精确 HEAD/blob 实读 ledger/AGENTS/合同，按 HANDOFF.md 适配。报告必须独立包含 source_integrity、state_restore、runtime、inferred_recommendation、authorization。缺正文不能 STATE_RESTORED；缺运行证据不影响已证账本事实，但禁止新冲突执行。

## C6 兼容与候选
clients/chatgpt-plugin 是更新覆盖包候选，不代表已安装。其固定来源可以指向当前正式 v0.2.0；不得引用本分支未发布 v0.2.1 为有效政策。后续采用新政策须另作准确来源锁更新及新窗口验收。既有引用文件未改时保留，不新增共享账本；CLI 回执/静态验证不能冒充 Chat 冷启动。

## C7 验收及失效
覆盖：不指定项目、不同项目局部403、未知运行态、恶意下级指令、政策哈希/HEAD 漂移、旧回执与新状态、两窗口不抢 writer。同一窗口未变输入的只读分析不必重读全部固定政策；新窗口、政策采用、动态 HEAD 变化、证据冲突必须刷新对应来源。缓存仅是固定字节缓存，不是可复用的扫描授权。
