# 长任务与「始终允许」说明

Boss 招呼排名会跑 **几十分钟** 的 boss-chat（滚动列表、开简历、LLM）。若每一步都要点批准，体验很差。下面分 **Cursor** 与 **OpenClaw** 说明。

## Cursor：`Dangerously always allow`

在 Agent 执行终端 / 工具时，Cursor 可能弹出：

- Allow once  
- **Dangerously always allow**（始终允许，不再询问）

### 适合做什么

- 本 skill 流程里反复出现的：`python3 scripts/extract_candidates.py`、`merge_ranking.py`
- 轮询 `get_boss_chat_run`、读 `~/.boss-recommend-mcp/` 下 JSON
- 调用 `boss-recommend__start_boss_chat_run` 等 MCP 工具

### 风险（必须知情）

「始终允许」作用于 **整个 Agent 会话**，不只限于本 skill。之后 Agent 也可能执行你未预期的删除、改配置、装包等命令。

**建议：**

1. 仅在跑 **boss-greeting-rank / boss-chat 只读扫招呼** 的专用会话里开。  
2. 本 skill 已禁止自动打招呼、自动求简历；但 **无法阻止** Agent 执行其它 shell 命令。  
3. 扫完后可新开会话，或改回「每次询问」。

### 设置入口（若要在设置里改）

`Cursor Settings` → **Agents** → **Auto-run** / 命令批准相关项（文案随版本可能为 *Run everything* / *Dangerously allow*）。

---

## OpenClaw：不是 Cursor 那个开关

OpenClaw 不用 Cursor 的 MCP 面板；Boss 能力是内置的 `boss-recommend__*` 工具。

长任务相关的是 **Exec approvals**（本机执行 `system.run` / shell）：

| 模式 | 含义 |
|------|------|
| 每次询问 | `ask: always` |
| 缺省询问 | `ask: on-miss` |
| **YOLO / 不询问** | `ask: off` + `security: full`（类似「始终允许」） |

查看当前策略：

```bash
openclaw exec-policy show
openclaw approvals get
```

一键放宽本机（**有风险，仅在你信任的环境**）：

```bash
openclaw exec-policy preset yolo
```

Matrix/聊天里也可能有 **♾️ allow always** 反应，只作用于该条批准。

---

## 与「只读排名」的关系

| 层 | 能否靠「始终允许」解决 |
|----|----------------------|
| 不发招呼、不求简历 | ✅ 由 skill 参数块保证，与批准无关 |
| boss-chat 自动扫列表 | ✅ 需 MCP/runtime + 可选「始终允许」减少打断 |
| Agent 不会跑危险 shell | ❌ 「始终允许」反而扩大 Agent 自主权，需你选会话/改回 |

---

## 推荐实践

1. **OpenClaw 跑招呼排名**：专用会话 + 需要时 `exec-policy preset yolo`，或对白名单命令用 allow always。  
2. **Cursor 调试 skill**：可对当前仓库路径开 always allow，跑完关。  
3. **云端 OpenClaw**：同样在服务器上检查 `exec-approvals.json`，否则长任务会卡在 `SYSTEM_RUN_DENIED: approval required`。
