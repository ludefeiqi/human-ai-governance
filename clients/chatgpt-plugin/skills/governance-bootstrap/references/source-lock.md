# 外部来源锁 · 目标正式政策 v0.2.0

此处是待验证期望值，不是已连接或已加载的证明。插件0.3.0-rc.1与政策v0.2.0是独立版本。
- repository: ludefeiqi/human-ai-governance
- policy_tag: v0.2.0
- annotated_tag_object: 093eb9cf706d46268118c2a877906b24fc9ce391
- policy_commit: 7aced01a8c12e1bba5e810ce91ab425f4615d4a7
- manifest_sha256: 47c8e8c14245c996363e9bdc50e8c8889a3e9a8dea8ff243db44b5ba629f0ff4
- genesis_index_sha256: 2908104618827faa35d05c87cb9e3dc3aa28c4dd45d4658ed9163553b3d6cbbc
- manifest_files: 20
- registry: main/projects.yaml；从已发布GENESIS起按完整first-parent与审批证据验证
- tag_signature: unsigned；不得宣称独立签名认证

按精确Commit实读MANIFEST.sha256、GENESIS及其全部20项固定原始文件，验证代码/Schema和执行实例一致。索引不在静态Manifest，以GENESIS初始哈希及动态变更链核验。发布/批准回执以官方Tag message的来源在授权连接内读回；回执不是业务授权。
本包仅兼容此正式快照。更新可被发现但必须经用户采用批准和插件更新读回；不能跟随main替换policy。旧正式政策v0.1.0不是失败时的静默降级；回退必须明确并如实标过期覆盖范围。未发布v0.2.1不是本包信任源。
