# boss-hiring reference

## 数据文件 schema

所有文件在 per-job 目录 `~/.boss-recommend-mcp/boss-chat/greeting-rank/<job_slug>/`。

### rubric.json

```json
{
  "job_slug": "java-backend",
  "job_label": "Java后端工程师",
  "created_at": "2026-06-01T12:00:00Z",
  "updated_at": "2026-06-01T12:00:00Z",
  "dimensions": [
    { "key": "experience", "label": "相关经验", "weight": 35 },
    { "key": "skill_match", "label": "技能匹配", "weight": 30 },
    { "key": "education", "label": "学历院校", "weight": 15 },
    { "key": "greeting", "label": "打招呼内容", "weight": 20 }
  ],
  "must_have": ["3年以上Java", "本科及以上"],
  "dealbreaker": ["仅外包经历", "频繁跳槽(1年内3次)"],
  "greeting_weight": 20,
  "criteria": "重点考察相关经验与技能匹配……并重点考察候选人主动打招呼/首条消息内容并纳入评分。"
}
```

- `dimensions[].weight` 合计 100，且必须含一条 `key=greeting`，其 weight = `greeting_weight`。
- `criteria` 是传给 boss-chat 的自由文本，必须显式包含打招呼文本评分要求。

### ranking.json

```json
{
  "job_slug": "java-backend",
  "updated_at": "2026-06-01T12:30:00Z",
  "candidates": [
    {
      "candidate_key": "chat:id:65113687-0",
      "display": "张三 · Java后端工程师",
      "name": "张三",
      "total_score": 86.5,
      "dimension_scores": { "experience": 30, "skill_match": 28, "education": 12, "greeting": 16.5 },
      "greeting_score": 16.5,
      "resume_score": 70,
      "reasons": ["5年电商后端", "招呼里主动说明到岗时间"],
      "skipped": false,
      "skip_reason": null,
      "skip_category": null,
      "greeting_text_missing": false,
      "first_seen_run_id": "mcp_chat_aaa",
      "last_run_id": "mcp_chat_bbb"
    }
  ]
}
```

按 `total_score` 降序。`candidate_key` 是去重主键。

### seen.json

```json
{ "job_slug": "java-backend", "seen_candidate_keys": ["chat:id:65113687-0"], "runs": ["mcp_chat_aaa"] }
```

## report.json 字段映射（boss-chat 产物 → 候选记录）

run JSON：`~/.boss-recommend-mcp/boss-chat/runs/<run_id>.json`

- `result.report_json` → 逐人明细文件路径。
- `progress.processed` / `progress.passed` / `progress.skipped` → stuck/进度判定。
- `heartbeat_at` → stuck 判定。

report.json → `summary.results[]`，每项：

| 字段 | 含义 | 用途 |
|------|------|------|
| `candidate_key` | 稳定标识（如 `chat:id:65113687-0`） | 去重主键 |
| `candidate.identity.name` | 姓名（可能为空或脏值如 "1"） | 展示用，不做主键 |
| `candidate.identity.{title,school,major,degree,years_experience,...}` | 简历画像 | 维度打分证据 |
| `candidate.text_length` | 卡片文本长度 | 招呼/卡片文本是否存在的线索 |
| `candidate.greeting_text` | 候选人首条招呼（boss-recommend-mcp ≥2.0.57） | 打招呼维度首选 |
| `candidate.greeting_text_source` | `network_history_msg` / `dom_message_list` / `card_preview` | 来源追溯 |
| `conversation_preview` | 会话摘要（含 `messages[]` 最近若干条） | 招呼缺失时的补充证据 |
| `candidate.card_preview_text` | 左侧列表最后一条预览 | 招呼降级来源 |
| `screening.status` | `pass`/`skip` 等 | skip 判定 |
| `screening.passed` / `screening.score` / `screening.reasons` | MCP 自评（参考，不直接用） | reasons 可纳入证据 |
| `llm_screening` | LLM 明细（可能为 null） | 证据 |
| `detail.cv_acquisition` | 简历获取情况（含 `skipped`/`source`/`error_code`） | 异常跳过判定 |
| `pre_action_state` | 在线简历/求简历/已发简历等按钮状态 | 判断是否"已联系=有意跳过" |

简历截图证据：report 同名子目录下 `chat-candidate-XXX-page-*.jpg` / `-llm-*.jpg`。

## 打招呼文本纳入打分

- 首选：`candidate.greeting_text`（MCP 在点开候选人后从 `historyMsg` 网络包或 `.chat-message-list` DOM 持久化）。
- 次选：`conversation_preview.greeting_text` / `candidate.card_preview_text`（左侧列表预览）。
- 取不到原文：该候选记录置 `greeting_text_missing=true`，greeting 维度按"信息不足"给保守分，并在输出里提示该项降级（不静默）。
- **旧版 report**（无 `greeting_text` 字段）需重新跑一轮 boss-chat 才有完整招呼原文。
- criteria 同时显式强调招呼内容，作为 MCP 侧的第二重保障。

## skip 类别（跳人不静默）

`extract_candidates.py` 依据 `screening.status` + `detail.cv_acquisition` + `pre_action_state` 归类：

| skip_category | 触发线索 | 处理 |
|---------------|----------|------|
| `intentional_already_contacted` | `pre_action_state.already_requested_resume=true` / `requested_resume` 存在 | 正常，进排名标 skip |
| `cv_unavailable` | `cv_acquisition.error_code` 非空、简历打不开 | 进排名标 skip，提示 |
| `detail_budget` | 达到 `detail_limit` 未开详情 | 异常跳过，提示调大 `detail_limit` 后补扫 |
| `list_truncated` | 列表滚动上限导致漏扫 | 异常跳过，提示调大 `list_max_scrolls`/`max_candidates` |
| `timeout` | 在线简历按钮/LLM 超时 | 异常跳过，提示调大超时或重试 |
| `unknown` | 其他 | 进排名标 skip，原样保留原因 |

异常跳过（`detail_budget`/`list_truncated`/`timeout`）需计数并提示用户，必要时补扫 `unread`。

## stuck 判定窗口

- 默认：`progress.processed` 在 **5 分钟**内无增长，或 `heartbeat_at` 距现在 > **3 分钟**，判定 stuck。
- 恢复：`pause_boss_chat_run` → `cancel_boss_chat_run`（复用同一 `run_id`）→ 重新 `start_boss_chat_run` 且 `start_from=unread`，跳过卡住者继续。
- stuck 观察允许短间隔轮询，但要让用户知情；非 stuck 场景默认 30 分钟一次。

## criteria 生成模板

```
岗位：{job_label}。
按以下维度与权重筛选（合计100）：{dim1}{w1}分、{dim2}{w2}分……。
硬性条件（缺一淘汰）：{must_have}。
一票否决：{dealbreaker}。
重点考察候选人主动打招呼/首条消息内容，并将其纳入评分（占{greeting_weight}分）。
只做筛选打分，不要发送任何消息，不要点击求简历。
```

## 模型选型与端点兼容（视觉硬约束）

简历以**截图**形式喂给 LLM，必须用视觉模型。三道独立关卡都要过：

1. 视觉能力：支持 `image_url`（纯文本模型会静默漏读简历）。
2. allowlist：在所用平台的 models 白名单内。
3. 端点兼容：在所配端点上可用（同模型换端点可能 404）。

`screening-config.json` 关键字段：

| 字段 | 含义 |
|------|------|
| `model` | 主模型（如 `GLM-5.1`） |
| `baseUrl` | LLM 端点（如 `https://ark.cn-beijing.volces.com/api/coding/v3`） |
| `llmModels` | 有序 failover 链；每项可覆盖 `model`/`baseUrl`/`apiKey`，缺省继承顶层；**全部失败**才报 `All configured LLM models failed` |
| `llmImageLimit` / `llmImageDetail` | 单候选送审图片数 / 清晰度 |

failover 写法（只放已验证的视觉模型）：

```json
"llmModels": [
  { "name": "primary-glm-5.1-vision", "baseUrl": "https://ark.cn-beijing.volces.com/api/coding/v3", "apiKey": "<key>", "model": "GLM-5.1" }
]
```

已知坏样例：`doubao-seed-2-0-lite`（不在 allowlist）、`huoshan/...-vision`（coding 端点 404）、`deepseek-v4-pro`（纯文本）。已知可用：`GLM-5.1`（ark coding/v3）。

超时：run 级 `timeoutSeconds` 建议 **≥1200s**（浏览器+开简历+截图+LLM 串行，900s 易中途超时）。运行环境/浏览器/cron 模板见 [docs/runbook-boss-greeting-ops.md](docs/runbook-boss-greeting-ops.md)。
