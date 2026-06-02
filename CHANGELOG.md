# Changelog

## [1.1.0] - 2026-06-02

### Added

- `docs/runbook-boss-greeting-ops.md`：运行环境运维手册（stealth 浏览器 / 扫码登录 / 模型关卡 / 超时 / canonical v6 cron 模板 / MCP 版本）
- SKILL.md + reference.md 新增「模型选型（视觉筛选硬约束）」：必须支持 `image_url`，且 **allowlist 与 端点兼容是两道独立关卡**
- `screening-config.json` 的 `llmModels` 改为显式有序 failover 链（仅放已验证的视觉模型）

### Fixed

- MCP 启动指向带招呼持久化能力的安装（≥2.0.57），不再用旧版 `@2.0.56`，修复 `greeting_text` 全 `missing`

### 踩坑档案（从下载到跑通的 7 个坑 + 核心教训）

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | `doubao-seed-2-0-lite` 被拒 | 不在 models allowlist | 换模型 |
| 2 | `huoshan/...-vision` 404 | 不支持 coding plan 端点 | 换模型 |
| 3 | `deepseek-v4-pro` 看不了简历截图 | 纯文本模型，不支持 `image_url` | 换 GLM-5.1（视觉） |
| 4 | 900s 超时 | 浏览器操作 + LLM 筛选耗时长 | run 级超时改 1200s |
| 5 | 普通 Chrome 被反爬检测 | 非 stealth 浏览器 | CloakBrowser stealth |
| 6 | CloakBrowser 无登录态 | 新浏览器 cookies 不互通 | 手动扫码登录一次 |
| 7 | cron prompt 仍写 v5 criteria | 模板文本没更新 | 改 v6 + 指向 rubric.json |

**核心教训：** 视觉筛选任务必须用支持 `image_url` 的模型；且 **allowlist 限制** 与 **端点兼容性** 是两道独立关卡，不是所有视觉模型都能用。

## [1.0.0] - 2026-06-01

### Added

- Open-source **boss-hiring** agent skill (MIT)
- Workflow: rubric interview → read-only boss-chat scan → extract → merge ranking
- Python tools: `extract_candidates.py`, `merge_ranking.py`
- Install script for OpenClaw (`~/.openclaw/skills`) and Cursor (`~/.cursor/skills`)
- Docs: OpenClaw / Cursor install guides
- Runtime notes for `@reconcrap/boss-recommend-mcp` ≥ 2.0.57 (greeting text persistence)
- Patch reference: `runtime/patches/2.0.57/conversation-greeting.js`

### Safety

- Read-only defaults: no auto greeting, no resume request
- Skip candidates kept in ranking with reasons; stuck recovery playbook
