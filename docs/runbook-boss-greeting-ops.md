# Runbook：Boss 招呼排名运行环境（浏览器 / 登录 / 模型 / cron）

本手册沉淀「从下载到跑通」踩过的运维坑，避免重装或换机重蹈。配套硬规则见 [SKILL.md](../SKILL.md) 与 [reference.md](../reference.md)。

## 1. 浏览器：必须用 stealth（反爬）

普通 Chrome 直接被 Boss 直聘反爬检测拦截。boss-chat runtime 通过 CDP 连接一个**已经在跑**的浏览器，所以要先启动一个 stealth 浏览器并打开远程调试端口。

- 用 **CloakBrowser**（或等价 stealth Chromium），不要用系统普通 Chrome。
- 启动时必须带远程调试端口，且端口要与 `screening-config.json` 的 `debugPort` 一致（当前 `9333`）：

```bash
# 端口必须 == screening-config.json 的 debugPort（当前 9333）
CloakBrowser --remote-debugging-port=9333
```

- 校验端口已开：

```bash
curl -s http://127.0.0.1:9333/json/version | head
```

> 若用别的浏览器/路径，runtime 也支持环境变量指定可执行文件：`BOSS_MCP_CHROME_PATH` / `BOSS_RECOMMEND_CHROME_PATH`。

## 2. 登录态：手动扫码一次

CloakBrowser 是**全新浏览器实例**，cookies 与系统 Chrome **不互通**，第一次没有 Boss 登录态。

- 在该 stealth 浏览器里手动打开 Boss 直聘，**扫码登录一次**。
- 登录态保存在该浏览器的 user-data 目录里，之后复用，不必每次重扫（除非清了 profile 或登录过期）。
- 登录后再启动 boss-chat run，否则会停在登录页抓不到招呼。

## 3. 模型：两道独立关卡

视觉筛选模型选型详见 [reference.md](../reference.md)。一句话：**支持 `image_url` + 在 allowlist + 端点兼容**，三者缺一不可；`allowlist` 与 `端点兼容` 是两道独立关卡。当前可用主模型 `GLM-5.1`（ark coding/v3）。

## 4. 超时

一次 run 串行做「滚动列表 + 开简历 + 截图 + LLM 打分」，耗时长。run 级超时设 **≥1200s**（900s 易中途超时）。

## 4.1 速度优先配置（不改 runtime 代码）

你要的目标是：**少卡顿、少脱节、整体更快**。在不改 runtime 代码的情况下，最快的杠杆只有两类：**节奏**与**每人图片成本**。

### A. 拟人节奏：用轻档（推荐 baseline）

`boss-recommend-mcp` 的人类节奏会在动作间插入随机停顿（尤其 `paced_with_rests` 会有 8–45s 短休 / 60–180s 长休），导致“下拉卡一下就停”“动作脱节”“整体慢”。

建议在 `~/.boss-recommend-mcp/screening-config.json`：

- `humanBehavior.profile`: `baseline`
- 关闭：`shortRest` / `batchRest` / `actionCooldown` / `listScrollJitter`
- 只保留（可选）：`clickMovement=true`（轻微鼠标拟真）

### B. 每人图片成本：优先降 `llmImageLimit`

默认一人最多送审 8 张图，速度会被“截图页数 + 视觉推理”放大。建议按梯度试：

- `llmImageLimit`: 先从 `8 → 5`（通常已经明显提速）
- 若覆盖仍足够，再降到 `3`
- `llmImageDetail`: 维持 `low`

### C. “为妥善保护…”是天然 stop boundary（减少无效内容）

Boss 简历页常在简历主体后出现推荐/分析/隐私声明模块（如「为妥善保护牛人在BOSS直聘平台提交、发布…」）。这些内容对打分无价值，反而会：

- 增加截图页数
- 增加 OCR 文本噪音
- 增加 LLM 推理 token

因此在截图滚动/归档时，把「为妥善保护…」作为 stop boundary 是推荐策略：**遇到它就该停**。

## 5. Canonical cron prompt（v6，指向 rubric.json）

cron 模板**不要内联旧 criteria 文本**（曾因模板没更新仍写 v5 而踩坑），统一指向 per-job 的 `rubric.json`，rubric 升级后 cron 自动跟随。

下为当前 live 的 v6 模板（OpenClaw cron `payload.message`，岗位「超级个体 _ 杭州」）：

```text
## Boss 直聘新招呼筛选 + 排名 + 归档

### 步骤 1: 筛选未读新招呼
使用 start_boss_chat_run：job=超级个体 _ 杭州, start_from=unread, criteria 基于 v6 体系（读取 ~/.boss-recommend-mcp/boss-chat/greeting-rank/超级个体-杭州/rubric.json）, post_action=favorite

### 步骤 2: 轮询完成
使用 get_boss_chat_run 轮询直到 completed

### 步骤 3: OCR 归档
运行 python3 /Users/spikescp/.openclaw/workspace/scripts/boss-resume-archive.py 自动 OCR 截图并存入 OpenPike/招聘/简历文本/

### 步骤 4: v6 排名
逐份阅读 OCR 文本，用 v6 评分体系打分（7维度：AI驱动开发25/前沿技术追踪20/自驱力20/问题解决15/AI架构10/工程基础5/打招呼5）。输出排名到 OpenPike/招聘/已排名/

### 步骤 5: 通知
🟢第一梯队 → 飞书私聊推送 Spike
```

cron `payload` 关键字段：`model: "volc-plan/GLM-5.1"`（视觉）、`timeoutSeconds: 1200`、`schedule.expr: "0 9 * * 1-5"`。

> 注意：该 cron 带 `post_action=favorite`（收藏候选人）属于**写动作**，是该招聘自动化的主动选择，**超出** skill 的只读默认。本 skill 默认仍是只读排名（不发招呼、不求简历）；如需收藏/求简历须显式开启并知情。

## 5.1 OCR 归档（推荐默认流程：一次取证，多次复用）

你的经验是对的：**把简历沉淀为本地文本**，后续“调取文档再打分”会比每次都开简历、截图、走视觉模型快很多。

推荐把 OCR 归档当作默认流程的一部分，而不是“可选后处理”：

- **第一次跑某岗位**：允许截图页数稍多一点，拿到足够证据 → OCR → 写入本地文本目录。
- **后续增量跑**：对新候选只做“最小截图页数 + OCR 文本”，LLM 主要读 OCR 文本（更快更便宜）；必要时再回退视觉读图兜底。

这样做的收益：

- 把最慢的“开简历/滚动/截图/视觉推理”转化为一次性成本
- 复盘、二次评审、多人协作都可以直接读文本
- 更容易做离线比较（差分/标注/版本化）

## 6. MCP 版本（招呼持久化）

候选人首条招呼 `candidate.greeting_text` 需 runtime **≥ 2.0.57** 才会持久化。启动命令应指向带该能力的安装，而不是 `npx -y ...@2.0.56`（旧版抓不到招呼，report 里全是 `greeting_text_missing`）。当前三处 launcher（`~/.cursor/mcp.json`、`~/.openclaw/mcp.json`、`~/.openclaw/openclaw.json`）改为 `command: "boss-recommend-mcp"` + `args: ["start"]`，使用本机已带该能力的全局安装。
