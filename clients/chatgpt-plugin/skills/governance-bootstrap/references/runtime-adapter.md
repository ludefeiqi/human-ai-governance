# 实际校验与正文读取适配

本插件skills本身不执行Python、不携带凭据。只有当前窗口实际可用且用户获准的既有执行环境才可运行。严禁调用本分支候选registry模块去冒充已发布v0.2.0模块；须先核工作树全部固定文件与source-lock的正式Manifest一致。

只读目录验证的正式命令：
```sh
python -m registry.validate_registry --root <VERIFIED_RELEASE_ROOT> audit-main --expected-policy-commit 7aced01a8c12e1bba5e810ce91ab425f4615d4a7
```
正式模块的项目来源函数调用（不是新增CLI）：
```python
# 在已核原始字节的正式release目录，以该模块的load_schema/load_genesis读取对应文件
from registry.validate_registry import GhApi, load_schema, load_genesis, scan_authorized_main
result = scan_authorized_main(GhApi(), genesis, schema,
    expected_policy_commit=policy_commit, authorized_project_ids=explicit_read_scope)
```
genesis/schema必须来自核准目录，policy_commit为来源锁中的精确值；explicit_read_scope必须从本轮真实权限得出。无环境返回VALIDATOR_UNAVAILABLE，权限拒绝不换路径绕行。
返回source verified只给project_head、blob与mode等证据。随后通过已有授权GitHub fetch_file接口以同HEAD取ledger/rules正文，按ledger-adapters解释；读取前后核目录和项目HEAD未变。固定合同用其冻结Commit。把当前执行权与原审批/来源验证分开。
正式v0.2.0历史CI回查若HOLD，标原政策限制；不能偷用未发布修复或伪造PASS。未读正文不得恢复NEXT。
