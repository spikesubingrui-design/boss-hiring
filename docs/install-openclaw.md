# OpenClaw 安装指南

## 1. 安装本 Skill

```bash
git clone https://github.com/spikesubingrui-design/boss-greeting-rank.git
cd boss-greeting-rank
./install.sh openclaw
```

安装位置：`~/.openclaw/skills/boss-greeting-rank`（符号链接到仓库目录）。

## 2. 确认 Boss 运行时

OpenClaw 会话中应能看到工具（名称可能带前缀）：

- `boss-recommend__prepare_boss_chat_run`
- `boss-recommend__start_boss_chat_run`
- `boss-recommend__get_boss_chat_run`
- …

若没有，请先安装/启用 **boss-recommend-mcp**（与 `boss-chat` skill 相同依赖）。

## 3. 运行时版本（招呼原文）

完整打招呼打分需要 **`@reconcrap/boss-recommend-mcp` ≥ 2.0.57**，会在 `report.json` 写入 `candidate.greeting_text`。

```bash
npm list -g @reconcrap/boss-recommend-mcp
# 若 < 2.0.57，见仓库 runtime/README.md
```

## 4. LLM 配置

复用 `~/.boss-recommend-mcp/screening-config.json`，不要在本 skill 内向用户重复索要 API Key。

## 5. 触发话术

对 Agent 说例如：

- 「用 boss-greeting-rank 给 **Java 后端** 岗位打招呼排名」
- 「只扫新招呼，合并进已有排名」

## 6. 云端 OpenClaw

若在服务器（如 `~/.openclaw` 部署在 VPS）上使用，需在**该机器**同样：

1. `./install.sh openclaw`
2. 升级 boss-recommend-mcp ≥ 2.0.57
3. 配置 screening-config 与可访问的 Chrome/Boss 登录态

数据与本地共用路径 `~/.boss-recommend-mcp/` 时，排名文件可同步该目录。
