---
name: boss-hiring
description: "Interview hiring requirements into a weighted scoring rubric for Boss直聘 recruitment."
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
- [ ] 0. 需求校准（复用 rubric 前必须走这一步）
- [ ] 1. 需求访谈 → 生成/复用 rubric
- [ ] 2. prepare 取岗位列表，用户选 job
- [ ] 3. plan：首次全量 / 之后只扫未读 + 只评未打分
- [ ] 4. 启动 boss-chat（只读参数块）
- [ ] 5. run 完成后只对「未 v7 打分」的人按 rubric 打分
- [ ] 6. merge_ranking 合并进历史全员榜，输出全局排名
```

### 0. 需求校准（硬规则）

**即使已有 rubric，重新评分或新 session 时必须先跟用户过一遍需求定位**，不要假设旧 rubric 仍然准确。

流程：
1. 读出当前 rubric 的维度/权重/硬条件，展示给用户
2. 问清楚岗位本质变化（做什么、阶段路线、技术栈偏好、工作方式硬性条件）
3. 用户确认或修正后，才进入 step 1

反模式：直接启动 boss-chat 用旧 rubric → 打分维度跟用户实际想找的人不匹配 → 排名无意义。

教训来源：v7→v8.1 升级过程中发现 rubric 定位严重偏离用户实际需求（缺少工程能力维度、薪资基线不匹配、硬条件过严、缺少"不弃养"维度等）。

### 1. 需求访谈 → rubric

**推荐用 `matt-grill-me` skill**：一次只问一个问题，每题给推荐答案，走通决策树后再落盘。禁止 agent 代填权重或代确认。

逐项问（一次一个），不要替用户预设：

- `job`：目标岗位（稍后从 boss-chat 岗位列表确认真实值）。
- 核心着重点：开放文本，用户最看重什么（例：多 AI 工具 workflow，不是单模型写代码）。
- 维度与权重：把着重点拆成若干维度并给权重（合计 100）。
- 硬性条件 / 一票否决 / 软门槛：哪些直接淘汰、哪些只降分（如薪资超预算）。
- 打招呼文本权重：候选人主动打招呼/首条消息内容占比多少。
- **Boss 证据映射**：打分依据 Boss 上实际可见内容——`greeting_text`、在线简历截图（个人优势/项目/工作经历）、期望薪资；学历通常不卡。

产出两样：

- `rubric.json`（结构见 [reference.md](reference.md)），保存到 per-job 目录。Live 范例：`~/.boss-recommend-mcp/boss-chat/greeting-rank/超级个体-杭州/rubric.json`（v7）。
- `criteria` 自由文本（boss-chat 的 LLM 只吃 criteria）。用人话写，绑定 Boss 字段；必须显式写入打招呼纳入评分。Boss 岗位 JD 可另存 `docs/boss-jd-<job_slug>-vN.md`。

同岗位再次运行时，先复用已存在的 `rubric.json`，询问是否调整后再继续。cron **只读 `rubric.json` 的 criteria**，不要内联旧版文本（见 [runbook](docs/runbook-boss-greeting-ops.md)）。

### 2. 选岗位

先用空参 `prepare_boss_chat_run` 取 `job_options`，让用户从列表选 `job`。页面未就绪不要问岗位。

### 3. 首次全量 vs 增量（硬规则）

先跑规划脚本（不要猜）：

```bash
python3 /Users/spikescp/.openclaw/workspace/boss-hiring/scripts/boss-hiring-flow.py plan <job_slug>
```

| 阶段 | boss-chat `start_from` | v7 打分范围 | 合并目标 |
|------|------------------------|-------------|----------|
| **首次**（`ranking.json` 里无人带 `scored_at`） | `all` 全量扫招呼 | 本 run **全部**候选人 | 写入 `ranking.json` |
| **之后每次** | `unread` 只扫新未读 | 仅 **`scored_at` 为空** 的 `candidate_key` | **合并进历史已打分全员榜** |

判定「已打分」：`ranking.json` 里该人有 `scored_at` + `dimension_scores`（不是 MCP 的 `screening.score`）。

`seen.json` 的 `scored_candidate_keys` 与上同义；`seen_candidate_keys` 是榜内出现过的所有人（含仅 MCP、待补 v7）。

### 4. 启动 boss-chat（只读参数块）

`start_boss_chat_run` 必带：

- `job`、`start_from`（`all`|`unread`）、`criteria`（来自 rubric）。
- `target_count`：默认 `"all"`（字面量字符串）；用户给正整数时按正整数。
- `use_llm=true`。
- 只读护栏：`request_cv=false`、`request_resume=false`、`ask_cv=false`、`execute_post_action=false`，**不传** `post_action`、`greeting_text`、`greetingText`。
- 防漏人：`target_count="all"` 时配较大的 `list_max_scrolls` 与 `max_candidates`；`detail_limit` 不低于预期候选数。
- 抗卡死：`online_resume_button_timeout_ms`（慢网默认 30000）、设 `llm_timeout_ms`、`delay_ms`，`detail_source=cascade`。

拿到 `ACCEPTED + run_id` 后：
- **不要让用户来告诉你 run 跑完了**。在 `poll_after_sec`（通常 10s）过后主动调一次 `get_boss_chat_run` 确认状态，之后按 30 分钟间隔检查。
- 如果用户说"已经跑完了"或"我看已经全量读取完了"，立即查状态并开始 post-run 流程，不要反问。

### 5. 解析 + 只评「未打分」（含 MCP fail）

run 完成后：

```bash
python3 scripts/boss-hiring-flow.py post-run <job_slug> <run_id>
```

会生成 `extract-<run_id>.json` 与 **`unscored-<run_id>.json`**（已 v7 打过分的人自动剔除）。

**关键变更（v8）**：`unscored` 列表**包含 MCP fail 的人**。MCP screening score=0 不意味着不需要 v7 打分——MCP 只是粗筛，v7 rubric 是独立评估。

只对 `unscored-*.json` 里的人按 `rubric.json` 打 v7 分；每人落盘字段必须含：`scored_at`、`dimension_scores`、`total_score`（及可选 `score_notes`）。

**v7 打分硬规则**：
- `score_notes` **禁止**写 "自动从MCP CoT估算"——必须基于简历截图实际内容
- 每个人必须有**不同的维度分组合**——如果连续 5 人维度分完全一样，说明打分没在看简历
- `dimension_scores` 里每个维度的分数必须与该维度的 `scoring` 描述对应（0-5 档位 × weight）

```bash
# 可选：手动过滤
python3 scripts/extract_candidates.py <report_json> > all.json
python3 scripts/boss-hiring-flow.py filter-unscored <job_slug> all.json -o unscored.json
```

### 6. 合并进全量榜 + 输出

```bash
python3 scripts/merge_ranking.py <job_slug> scored_candidates.json
python3 scripts/boss-hiring-flow.py show-ranking <job_slug>
```

`merge_ranking` 按 `candidate_key` 去重合并：**新分覆盖旧分，未出现在本 run 的历史候选人保留**，全表按 `total_score` 降序。输出的是**截至目前所有已打分的人**的全局排名，不是「仅本 run 子集」。

## 数据位置

per-job 目录：`~/.boss-recommend-mcp/boss-chat/greeting-rank/<job_slug>/`

- `rubric.json`：维度/权重/硬性项/greeting 权重/criteria。
- `ranking.json`：全员合并榜（按 `total_score` 排序）。
- `seen.json`：`scored_candidate_keys`（已 v7 打分）+ `seen_candidate_keys`（榜内所有人）。

`<job_slug>`：岗位名小写、空格与符号转 `-`。

## 模型选型（视觉筛选硬约束）

打分要看简历**截图**，属于视觉任务。模型不是随便选的，**allowlist 限制**与**端点兼容性**是两道**独立关卡**，过了一道不代表过另一道。

完整已知好/坏模型列表与验证清单见 [references/screening-model-config.md](references/screening-model-config.md)。

当前推荐：`qwen-vl-max` on `https://dashscope.aliyuncs.com/compatible-mode/v1`（百炼视觉模型，OpenAI 兼容，已验证可用）。降级备选 `qwen-vl-plus`。

## 已知 bug 与防护（默认开启的硬规则）

| 坑 | 规则 |
|----|------|
| 自动打招呼 | 禁传 `greeting_text`/`greetingText`；任何分支不发首条消息 |
| 自动求简历 | `request_cv`/`request_resume`/`ask_cv`/`execute_post_action`=false，不传 `post_action` |
| 卡在一个人不动 | 看 `progress.processed` 与 `heartbeat_at`；停滞超阈值 → `pause` → `cancel`（复用同一 `run_id`）→ 以 `start_from=unread` 重启跳过卡住者 |
| 跳人（skip） | 跳过者不静默丢失，进 `ranking.json` 带 `skipped=true`+原因；区分有意跳过 vs 异常跳过（预算/滚动/超时），异常跳过计数并提示，必要时调大 `detail_limit`/`list_max_scrolls`/`max_candidates` 后补扫 |
| **打分无区分度** | v7 打分**必须**基于简历截图视觉分析；禁止从 MCP screening 二元结果（pass/fail + score=0/100）"估算"分数。如果 `score_notes` 出现 "自动从MCP CoT估算"，说明打分流程有 bug，需要重新打分 |
| **候选人重复** | `merge_ranking.py` 按 `candidate_key` 去重。如果同一人出现多个 `candidate_key`（如跨 run 的 chat ID 不同），需在 post-run 阶段做 name+identity 二次去重 |
| **greeting_text 全丢** | 如果 100% 候选人 `greeting_text_missing=true`，说明 boss-chat 未抓取打招呼文本。此时打招呼维度给保守中位 3 分（不是 0），标 `greeting_source=fallback` |
| **MCP 过度淘汰** | MCP screening score=0 不应直接跳过 v7 打分。所有 MCP fail 的人也应该进 `unscored` 列表，由 v7 rubric 独立判断。MCP 只是第一层筛，不是终审 |

| **MCP LLM 全量失败** | 如果 run 完成后所有候选人 `screening.reasons` 包含 `llm_invalid_response`，说明 LLM 端点有问题（模型名/端点/API Key 不匹配）。此时：1) 检查 `screening-config.json` 的 `llmModels[0].baseUrl` 是否与模型兼容；2) 用 identity-only 做降级打分（score_notes 标注）；3) 对 top 候选人手动看截图二次评估 |
| **模型端点不兼容** | GLM-5.1 在 `/api/coding/v3` 端点可能 404，应统一用 `/api/v3`。doubao-seed-1-8-251228 是纯文本模型不支持视觉，不能作为 vision 筛选主模型。详见 [references/screening-model-config.md](references/screening-model-config.md) |
| **用户说不想重复看** | boss-chat 没有"跳过已处理"选项。用户说"已经看过的别再重复了"时：1) 如果旧 run 的数据可用（report 里已有候选人数据），直接用旧数据打分，新 run 只扫 `unread`；2) 如果旧数据不可用（MCP LLM 全失败），必须全量重扫才能拿到简历截图，需向用户解释并接受 |
| **不要让用户监控任务** | 启动 boss-chat 后**主动**检查进度，不要等用户来告诉你"跑完了"。`poll_after_sec` 过后查一次，之后 30 分钟一次 |

stuck 判定窗口与 skip 类别见 [reference.md](reference.md)。

## 路由护栏（对齐 boss-chat）

- 仅 chat-only / 聊天页 / 招呼 / 求简历列表场景用本 skill。
- 用户说推荐页 / recommend → 交回 `boss-recommend-pipeline`；说搜索页 / search / recruit → 交回 `boss-recruit-pipeline`。
- 复用 `screening-config.json` 的 LLM 配置，不另向用户要 `baseUrl/apiKey/model`。
- `job`/`start_from`/`criteria` 缺一不可；`target_count` 必填，"全部/扫到底"字面传 `"all"`。
- 不替用户代填或代确认 boss-chat 参数。
- 长任务：启动后 `poll_after_sec` 过后主动查一次状态，之后 30 分钟一次；**不要让用户来告诉你跑完了**。
- `pause`/`resume`/`cancel` 必须复用同一 `run_id`。

## OpenClaw / Shell-only 兜底

当 OpenClaw/QClaw 只暴露 shell、没有原生 MCP tool list 时，不得停在"请使用 MCP 工具"。按 `boss-recommend-pipeline` 既有的 detached CLI 方式启动 boss-chat，并保持上面的只读参数块（不发消息、不求简历）。

## 响应风格

- 结构化中文。
- 缺参只补缺口，不改写用户的 criteria。
- 输出排名时标明：总分、各维度分、greeting 分、是否 skip 及原因、首次/最近出现 run。
