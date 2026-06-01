---
name: boss-greeting-rank
description: >-
  Interview hiring requirements into a weighted scoring rubric, then drive the
  boss-chat runtime on the Boss Zhipin chat page to rank candidate greetings:
  first run scores ALL greetings, later runs score only NEW greetings and merge
  into the saved ranking. Scoring folds in the candidate's greeting/chat message
  text alongside the resume. Read-only by default (never sends a greeting, never
  requests a resume). Use when the user wants to 自动问需求打分 / rank Boss 招呼 /
  给 boss 直聘打招呼排名 / 合并新招呼 / 按着重点给候选人打分.
disable-model-invocation: true
---

# Boss Greeting Rank

在 Boss 直聘**聊天页**把"收到的打招呼"按招聘需求排序。建立在 `boss-chat` runtime（`@reconcrap/boss-recommend-mcp` **≥ 2.0.57**，会持久化 `candidate.greeting_text`）之上，本 skill 负责：需求访谈→加权 rubric、跨运行排名合并、把打招呼文本与简历一起纳入打分。boss-chat 只负责开浏览器/抓简历。

安装与依赖见仓库 [README.md](README.md) 与 [docs/install-openclaw.md](docs/install-openclaw.md)。

## 只读铁律（最高优先级）

本 skill 默认是**只读排名**：全程只看、只打分，绝不发任何消息。

- 不自动打招呼：禁止传 `greeting_text` / `greetingText`。任何分支都不得发送首条消息，即使 boss-chat 有 profile 历史招呼语回退也不触发发送。
- 不自动求简历：`request_cv` / `request_resume` / `ask_cv` / `execute_post_action` 一律 `false`，不传 `post_action`。打开在线简历仅用于打分，绝不点击"求简历"。
- 求简历 / 打招呼是**独立动作**，只有用户在另一个明确任务里确认后才允许，且不在本 skill 内执行。

## 工作流

复制此清单跟踪进度：

```
- [ ] 1. 需求访谈 → 生成/复用 rubric
- [ ] 2. prepare 取岗位列表，用户选 job
- [ ] 3. 判定首次/再次（看 ranking.json 是否存在）
- [ ] 4. 启动 boss-chat（只读参数块）
- [ ] 5. run 完成后解析 report.json → 按 rubric 打分
- [ ] 6. 写入/合并 ranking.json，输出排名
```

### 1. 需求访谈 → rubric

逐项问（一次一个），不要替用户预设：

- `job`：目标岗位（稍后从 boss-chat 岗位列表确认真实值）。
- 核心着重点：开放文本，用户最看重什么。
- 维度与权重：把着重点拆成若干维度并给权重（合计 100）。
- 硬性条件 / 一票否决：缺哪些直接判 0 或淘汰。
- 打招呼文本权重：候选人主动打招呼/首条消息内容占比多少。

产出两样：

- `rubric.json`（结构见 [reference.md](reference.md)），保存到 per-job 目录。
- `criteria` 自由文本（boss-chat 的 LLM 只吃 criteria）。criteria 内必须显式写入"重点考察候选人主动打招呼/首条消息内容并纳入评分"。

同岗位再次运行时，先复用已存在的 `rubric.json`，询问是否调整后再继续。

### 2. 选岗位

先用空参 `prepare_boss_chat_run` 取 `job_options`，让用户从列表选 `job`。页面未就绪不要问岗位。

### 3. 判定首次 / 再次

按 `<job_slug>/ranking.json` 是否存在：

- 不存在 → 首次 → `start_from=all`（扫全部招呼）。
- 已存在 → 再次 → `start_from=unread`（只扫新招呼），完成后合并。

### 4. 启动 boss-chat（只读参数块）

`start_boss_chat_run` 必带：

- `job`、`start_from`（`all`|`unread`）、`criteria`（来自 rubric）。
- `target_count`：默认 `"all"`（字面量字符串）；用户给正整数时按正整数。
- `use_llm=true`。
- 只读护栏：`request_cv=false`、`request_resume=false`、`ask_cv=false`、`execute_post_action=false`，**不传** `post_action`、`greeting_text`、`greetingText`。
- 防漏人：`target_count="all"` 时配较大的 `list_max_scrolls` 与 `max_candidates`；`detail_limit` 不低于预期候选数。
- 抗卡死：`online_resume_button_timeout_ms`（慢网默认 30000）、设 `llm_timeout_ms`、`delay_ms`，`detail_source=cascade`。

拿到 `ACCEPTED + run_id` 后默认结束本轮，不主动高频轮询。

### 5. 解析 + 打分

run 完成后（用户确认或 `get_boss_chat_run` 显示完成）：

```bash
python3 scripts/extract_candidates.py <report_json_path> > candidates.json
```

`report_json_path` 取自 run JSON 的 `result.report_json`（位于 `~/.boss-recommend-mcp/boss-chat/runs/<run_id>.json`）。

对每位候选，agent 依据 `rubric.json` 打分：总分 = 简历维度加权分 +（greeting 维度分 × 权重）。不要直接采用 MCP 的 `screening.score`，以保证跨 run 口径一致。

### 6. 合并 + 输出

```bash
python3 scripts/merge_ranking.py <job_slug> <scored_candidates.json>
```

按 `candidate_key` 去重（新覆盖旧、保留首次出现 `run_id`），按总分降序写回 `ranking.json`，输出 Top 排名给用户。

## 数据位置

per-job 目录：`~/.boss-recommend-mcp/boss-chat/greeting-rank/<job_slug>/`

- `rubric.json`：维度/权重/硬性项/greeting 权重/criteria。
- `ranking.json`：合并后的排名数组。
- `seen.json`：已处理过的 `candidate_key`，支撑"只算新招呼"。

`<job_slug>`：岗位名小写、空格与符号转 `-`。

## 已知 bug 与防护（默认开启的硬规则）

| 坑 | 规则 |
|----|------|
| 自动打招呼 | 禁传 `greeting_text`/`greetingText`；任何分支不发首条消息 |
| 自动求简历 | `request_cv`/`request_resume`/`ask_cv`/`execute_post_action`=false，不传 `post_action` |
| 卡在一个人不动 | 看 `progress.processed` 与 `heartbeat_at`；停滞超阈值 → `pause` → `cancel`（复用同一 `run_id`）→ 以 `start_from=unread` 重启跳过卡住者 |
| 跳人（skip） | 跳过者不静默丢失，进 `ranking.json` 带 `skipped=true`+原因；区分有意跳过 vs 异常跳过（预算/滚动/超时），异常跳过计数并提示，必要时调大 `detail_limit`/`list_max_scrolls`/`max_candidates` 后补扫 |

stuck 判定窗口与 skip 类别见 [reference.md](reference.md)。

## 路由护栏（对齐 boss-chat）

- 仅 chat-only / 聊天页 / 招呼 / 求简历列表场景用本 skill。
- 用户说推荐页 / recommend → 交回 `boss-recommend-pipeline`；说搜索页 / search / recruit → 交回 `boss-recruit-pipeline`。
- 复用 `screening-config.json` 的 LLM 配置，不另向用户要 `baseUrl/apiKey/model`。
- `job`/`start_from`/`criteria` 缺一不可；`target_count` 必填，"全部/扫到底"字面传 `"all"`。
- 不替用户代填或代确认 boss-chat 参数。
- 长任务默认不轮询；需 stuck 检测时可短间隔但要让用户知情，否则默认 30 分钟一次。
- `pause`/`resume`/`cancel` 必须复用同一 `run_id`。

## OpenClaw / Shell-only 兜底

当 OpenClaw/QClaw 只暴露 shell、没有原生 MCP tool list 时，不得停在"请使用 MCP 工具"。按 `boss-recommend-pipeline` 既有的 detached CLI 方式启动 boss-chat，并保持上面的只读参数块（不发消息、不求简历）。

## 响应风格

- 结构化中文。
- 缺参只补缺口，不改写用户的 criteria。
- 输出排名时标明：总分、各维度分、greeting 分、是否 skip 及原因、首次/最近出现 run。
