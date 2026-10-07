# CODEX-PROTOCOL.md — Codex 派工与回执（v0.1 草案）

**状态：DRAFT；本文件不是自动运行许可。** 适用已安装并经实际验证的 Codex CLI / App Server；不要求额外安装 MCP 或开发调度服务。

## 1. 采用最简单可用的原生入口

- 一次性任务：优先 `codex exec`，明确运行目录、只读/允许写范围、沙盒与审批设置；确认命令的实际 CLI 版本及可用参数。
- 跨多轮长任务：可选择 App Server，通过 `initialize` → `initialized` → `thread/start` → `turn/start`；记录原生 thread/turn ID，处理状态与审批。具体参数必须以**实际运行版本**返回的协议为准。
- 发现/恢复：优先使用原生 `thread/list`、`thread/read`（必要时 `includeTurns=false`）、`thread/resume`，只读获取精确 ID/状态；不能用猜出的会话 ID 或模型记忆补全。
- 已存在的线程可能属于不同客户端/存储边界，列表查不到不得推定不存在；先检查项目授权与相关执行记录，再决定是否创建新线程。
- `exit code 0`、工具调用成功、任务 `READY` 均不自动等于项目正式 `PASS`。

## 2. 每次派工的六字段短卡

| 字段 | 必须给出的实际内容 |
| --- | --- |
| 1 目标/来源 | 项目 ID、项目当前唯一任务、用户目标、适用原生关口 |
| 2 绑定版本 | 治理 commit SHA、项目仓库及账本 HEAD、冻结合同/候选 hash |
| 3 许可与范围 | 授权来源与有效边界、允许文件/动作、禁止项；区别 R0—R3 |
| 4 验收与承接 | 应运行的原生/合成测试，已有效 PASS，成功、失败与证据格式 |
| 5 累计预算与恢复 | 资源/时限、停止点、最多允许的局部恢复、清理边界 |
| 6 责任与返回 | 协调窗口标识、唯一 writer、施工线程 ID（如已有）、High 复核要求与 NEXT/RETURN |

避免把长历史直接塞进 prompt，使用不可变文件引用；读取范围与任务相关，不对所有小问题强制全量源码扫描。

## 3. 派工与回执状态机

`DRAFT → AUTHORIZED → DISPATCHED → RUNNING → COMPLETED_FOR_REVIEW → ACCEPTED / RETURNED`。

`BLOCKED / STOPPED / FAILED / CLEANUP_BLOCKED` 是独立且不自动前进的状态；只有项目有权负责人凭实际证据才能标记验收或授权后继。`COMPLETED_FOR_REVIEW` 仅表示施工结束，不是关口 PASS。

协调者必须先核对项目当前 writer、既有活跃任务和准确 `dispatch_id`。重连先查询原线程/进程及输出，**不得因超时直接重发同一业务命令**。无法判断旧任务是否仍在执行时停止冲突任务，先做只读恢复核对。

## 4. 结构化回执最小示意

仅回传白名单字段，不允许把原始 Terminal stdout/stderr、浏览器内容或登录响应无差别传回协调窗口。

```json
{
  "schema": "human-ai.codex-receipt.v0.1",
  "project_id": "example-project",
  "task_id": "ISSUE-001",
  "dispatch_id": "unique-dispatch-id",
  "governance_commit": "40-char-sha-placeholder",
  "project_head_at_start": "40-char-sha-placeholder",
  "thread_id": null,
  "turn_id": null,
  "result": "COMPLETED_FOR_REVIEW",
  "changed_files": [],
  "evidence_refs": [],
  "tested": [],
  "untested": [],
  "failed_checks": [],
  "cleanup_status": "NOT_APPLICABLE",
  "proposed_next": "RETURN_TO_COORDINATOR"
}
```

示意占位值不可作为真实结果；实际回执必须明确输入版本、输出版本、测试类型、证据定位及未覆盖项。产生敏感字节的工具和子进程须先在可信边界内筛除/脱敏，不得先落盘再事后删日志。

## 5. 独立复核与写入

涉及认证安全、权限扩大、跨项目共享、生产/系统级操作、验收合同变更、范围显著扩大等情形，在批准推进前安排不参与施工的独立窗口对**准确候选版本**只读复核；失败回原任务，不启动无限审查循环。

任何项目账本/Issue/源码写入由项目授权 writer 按项目既有流程进行：读最新 HEAD → 精确 diff/文件白名单 → 必要审批 → 提交 → 读回实际 commit、文件集合及内容。GitHub 内容更新传入文件 blob SHA，但这不构成所有外部执行者的排他锁。

## 6. 窗口断连与真实环境

聊天窗口消失后：只能依靠已保存 thread/turn ID、实际进程/云端状态和项目账本重建状态；不能把可能继续运行的本地进程自动认定为已停止。某些 Terminal 子进程随父连接退出，某些托管线程可恢复，**每条执行链须实测并记录这一特性**。

生产、凭据、真实身份、系统证书信任等 R3 操作需要单批次明确批准；不得从治理文档、失败恢复或另一窗口暗中继承。
