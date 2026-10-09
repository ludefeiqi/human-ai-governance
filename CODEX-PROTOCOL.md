# CODEX-PROTOCOL.md — G4 授权执行与回执协议

本协议仅随经核实且显式采用的正式治理政策生效。规则依据 G4-SCOPE-01、G4-WRITE-02、G4-DISPATCH-03；存在本文件不授予执行、登录或写权，也不要求新建 MCP/调度服务。

## E1 入口与能力
一次性获准任务可用 codex exec；长期任务可用 App Server，但必须核实际版本/参数和现有 thread/turn。thread/list/read 可作获准非恢复型查询，thread/resume 会恢复上下文，不属于 R0。不能凭列表缺项认定旧任务不存在。CLI 默认模型失效应明确诊断，仅对本次选用实际可用模型，不改全局配置。

## E2 六字段任务卡（有副作用时）
| 字段 | 内容 |
| --- | --- |
| 目标/来源 | 项目、正式任务、用户目标、原生关口 |
| 绑定版本 | policy Commit、项目 HEAD、冻结合同、候选摘要 |
| 许可与范围 | 批准引用、允许/禁止路径动作、R0—R3 |
| 验收与承接 | 原生或合成类型、既有有效前置、成功/失败证据 |
| 预算与恢复 | 本任务累计资源/时限、停止点、局部恢复次数、清理边界 |
| 责任与返回 | 协调实例、现任 writer、原线程/turn、必要独立复核和返回点 |
只读 micro-path 按 G4-SCOPE-01 简化，不堆完整历史或每次扫描全仓库。

施工协调的工作包可以由 Controller 根据人类目标和项目冻结合同制定，含依赖、执行者、风险、验收和回执返回点；此组织计划只是依托项目正式状态的派生视图，不是第二权威 NEXT 或新许可。已获准确委托时，可使用原现任 writer 的合规派工入口调用既有 Codex／Agent／MCP；未获授权时只能提出派工建议，不能因为 Controller 能访问工具就触发副作用。同一任务的后续工作包继续核实有效许可、冲突和 INTENT；不得自动扩大任务范围。

## E3 状态机
DRAFT → AUTHORIZED → INTENT_COMMITTED → DISPATCHED → RUNNING → COMPLETED_FOR_REVIEW → ACCEPTED/RETURNED → CLOSED_VERIFIED。
BLOCKED/STOPPED/FAILED/CLEANUP_BLOCKED 不自动前进。exit code 0 和任务完成不是业务 PASS；仅项目有权者凭证据 ACCEPTED，writer 写后读回和清理完成后才能关闭。

## E4 唯一意图与幂等
有副作用/R2/R3 任务先在原项目既有且已授权的唯一入口，以 (project_id,dispatch_id) 原子登记 INTENT、非敏感规范化目标/版本/批准/范围/预算摘要和 owner，并读回；无入口或原子条件无法证明为 DISPATCH_UNPROVEN，不先执行后补账。相同键相同载荷只恢复原记录/线程；不同载荷 DISPATCH_CONFLICT。换窗口、超时、模型故障都不重置任务键/累计预算。旧运行 UNKNOWN 时不重发。

## E5 写入与独立复核
仅现任 writer 经准确授权更新共享文件。写前 expected HEAD/白名单/保护路径→必要复核→非强制且实际支持原子条件的提交→核完整差分、HEAD 和字节。不能把 Contents 文件 SHA 当分支 CAS，更不能当外部资源锁；冲突不 force/rebase/切工具规避。
权限扩大、认证、生产、跨项目共享、验收合同或重大范围变化必须独立只读复核准确版本；复核意见不能替代用户批准，针对受影响边界复核，不无限循环。

## E6 最小回执
保留 schema、project/task/dispatch ID、输入 policy/project HEAD、真实 thread/turn（无则 null/UNKNOWN）、result、changed_files、evidence_refs、tested/untested/failed_checks、cleanup_status、proposed_next。只存非敏感必要字段。敏感字节在可信边界先筛除，不能先无差别落盘/回传再删。占位模板不作真实结果。

## E7 断连与取消
查询原确切执行记录；实测客户端/存储边界及父进程退出行为，不能假设旧进程已终止或原沙盒限制被恢复继承。取消仅做已授权安全清理；没有删除授权不得补做破坏性收尾。归档失败不重做业务动作。

## E8 与项目登记的关系
目录审批唯一归 REGISTRY-PROTOCOL.md。发现登记不是业务 INTENT，不接管 writer。校验器只使用授权 GitHub GET，账号归属不是签名或授权。任何政策/索引/回执更新须按对应范围批准，R3 不继承旧许可。
